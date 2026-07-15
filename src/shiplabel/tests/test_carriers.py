"""DPD / UPS / FedEx spec-driven mappers, exercised with a mocked transport.

Each carrier's declarative spec is validated end-to-end: the payload it builds
(fan-out, unit conversion, conditional blocks) and how it normalizes the label
response — no per-carrier Python.
"""

from __future__ import annotations

import base64
import json
from decimal import Decimal

import httpx
import pytest

from shiplabel import auth
from shiplabel.canonical import (
    CanonicalShipmentRequest,
    CarrierSelection,
    Parcel,
    Party,
    References,
)
from shiplabel.loader import spec_codes
from shiplabel.service import available_carriers, create_label

FAKE_LABEL = base64.b64encode(b"%PDF-1.4 fake").decode()


def _req(code: str, **overrides) -> CanonicalShipmentRequest:
    base = dict(
        carrier=CarrierSelection(code=code),
        sender=Party(
            name="Muster GmbH",
            street="Musterstr.",
            house_number="1",
            postal_code="10115",
            city="Berlin",
            country="DE",
        ),
        recipient=Party(
            name="Erika Beispiel",
            company="Beispiel AG",
            street="Beispielweg",
            house_number="2",
            postal_code="80331",
            city="München",
            country="DE",
        ),
        parcels=[Parcel(id="p1", weight_kg=Decimal("1.5"))],
        references=References(delivery_note="LS-4711"),
    )
    base.update(overrides)
    return CanonicalShipmentRequest(**base)


def _mock(capture: dict, order_path: str, response: dict) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/token"):
            return httpx.Response(200, json={"access_token": "tok", "expires_in": 1700})
        if order_path in request.url.path or request.url.path.endswith(order_path):
            capture["body"] = json.loads(request.content)
            capture["headers"] = dict(request.headers)
            return httpx.Response(200, json=response)
        return httpx.Response(404)

    return httpx.Client(transport=httpx.MockTransport(handler))


@pytest.fixture(autouse=True)
def _clear_token_cache():
    auth._cache.clear()
    yield


def test_all_specs_load():
    expected = {"dhl", "dpd", "ups", "fedex", "gls", "sendcloud", "shipcloud", "dhl_return"}
    assert set(spec_codes()) == expected
    assert set(available_carriers()) == expected


def test_gls_basic_auth_and_shared_label():
    config = {
        "gls_username": "u",
        "gls_password": "p",
        "gls_customer_id": "C1",
        "gls_contact_id": "K1",
    }
    capture: dict = {}
    response = {"parcels": [{"trackId": "GLS123"}], "labels": [FAKE_LABEL]}
    result = create_label(config, _req("gls"), client=_mock(capture, "/shipments", response))

    assert result.parcels[0].tracking_number == "GLS123"
    assert result.parcels[0].label.data == FAKE_LABEL  # from top-level labels[0]
    assert capture["body"]["shipperId"] == "C1 K1"
    assert "authorization" in {k.lower() for k in capture["headers"]}  # HTTP Basic


def test_sendcloud_label_url_fetched_with_auth():
    config = {
        "sendcloud_public_key": "pk",
        "sendcloud_secret_key": "sk",
        "sendcloud_method_id": "8",
    }
    label_calls: list = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/parcels"):
            return httpx.Response(
                200,
                json={
                    "parcel": {
                        "tracking_number": "3SABC",
                        "tracking_url": "https://track/3SABC",
                        "label": {"label_printer": "https://panel.sendcloud.sc/label/1.pdf"},
                    }
                },
            )
        if request.url.path.endswith("/label/1.pdf"):
            label_calls.append(dict(request.headers))
            return httpx.Response(200, content=b"%PDF-1.4 real")
        return httpx.Response(404)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    result = create_label(config, _req("sendcloud"), client=client)

    assert result.parcels[0].tracking_number == "3SABC"
    assert base64.b64decode(result.parcels[0].label.data) == b"%PDF-1.4 real"
    # the label URL GET carried the same Basic auth as the API call
    assert "authorization" in {k.lower() for k in label_calls[0]}


def test_dhl_return_basic_plus_apikey_header():
    config = {
        "dhl_return_username": "u",
        "dhl_return_password": "p",
        "dhl_return_api_key": "KEY",
        "dhl_return_receiver_id": "RX",
        "dhl_return_sandbox": True,
    }
    capture: dict = {}
    response = {"shipmentNo": "RET999", "label": {"b64": FAKE_LABEL}}
    result = create_label(config, _req("dhl_return"), client=_mock(capture, "/orders", response))

    assert result.parcels[0].tracking_number == "RET999"
    assert result.parcels[0].label.data == FAKE_LABEL
    assert capture["headers"]["dhl-api-key"] == "KEY"  # extra header alongside Basic
    assert capture["body"]["shipper"]["country"] == "DEU"


def test_dpd_payload_and_shared_label():
    config = {
        "dpd_partner_name": "PN",
        "dpd_partner_token": "PT",
        "dpd_cloud_user_id": "UID",
        "dpd_user_token": "UT",
    }
    capture: dict = {}
    response = {
        "LabelResponse": {"LabelPDF": FAKE_LABEL, "LabelDataList": [{"ParcelNo": "01111222233"}]}
    }
    result = create_label(config, _req("dpd"), client=_mock(capture, "setOrder", response))

    assert result.parcels[0].tracking_number == "01111222233"
    assert result.parcels[0].label.data == FAKE_LABEL  # shared label attached
    assert capture["headers"]["partnercredentials-name"] == "PN"  # custom-header auth
    order = capture["body"]["OrderDataList"][0]
    assert order["ShipAddress"]["ZipCode"] == "80331"
    assert order["ParcelData"]["Weight"] == "1500"  # grams as string


def test_ups_payload_fan_out_and_label_format():
    config = {
        "ups_client_id": "ci",
        "ups_client_secret": "cs",
        "ups_account_number": "A1234",
        "ups_sandbox": True,
    }
    capture: dict = {}
    response = {
        "ShipmentResponse": {
            "ShipmentResults": {
                "PackageResults": [
                    {
                        "TrackingNumber": "1Z999",
                        "ShippingLabel": {
                            "GraphicImage": FAKE_LABEL,
                            "ImageFormat": {"Code": "GIF"},
                        },
                    },
                ]
            }
        }
    }
    req = _req(
        "ups",
        parcels=[
            Parcel(id="a", weight_kg=Decimal("1.5")),
            Parcel(id="b", weight_kg=Decimal("2.0")),
        ],
    )
    result = create_label(config, req, client=_mock(capture, "/ship", response))

    assert result.parcels[0].tracking_number == "1Z999"
    assert result.parcels[0].label.format == "gif"  # read from ImageFormat.Code
    shipment = capture["body"]["ShipmentRequest"]["Shipment"]
    assert shipment["Shipper"]["ShipperNumber"] == "A1234"
    assert len(shipment["Package"]) == 2  # one package per parcel (fan-out)
    assert shipment["Package"][0]["PackageWeight"]["Weight"] == "1.5"
    assert shipment["ReferenceNumber"][0]["Value"] == "LS-4711"
    assert "Authorization" in capture["headers"] or "authorization" in capture["headers"]


def test_fedex_payload_and_nested_label():
    config = {
        "fedex_client_id": "ci",
        "fedex_client_secret": "cs",
        "fedex_account_number": "F1234",
        "fedex_sandbox": True,
    }
    capture: dict = {}
    response = {
        "output": {
            "transactionShipments": [
                {
                    "masterTrackingNumber": "794123",
                    "pieceResponses": [
                        {
                            "trackingNumber": "794123456",
                            "packageDocuments": [{"docType": "PDF", "encodedLabel": FAKE_LABEL}],
                        }
                    ],
                }
            ]
        }
    }
    result = create_label(config, _req("fedex"), client=_mock(capture, "/shipments", response))

    assert result.parcels[0].tracking_number == "794123456"
    assert result.parcels[0].label.data == FAKE_LABEL  # nested packageDocuments.0.encodedLabel
    shipment = capture["body"]["requestedShipment"]
    assert capture["body"]["accountNumber"]["value"] == "F1234"
    assert shipment["recipients"][0]["address"]["postalCode"] == "80331"
    assert shipment["requestedPackageLineItems"][0]["weight"] == {"units": "KG", "value": 1.5}
