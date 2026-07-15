"""DHL spec-driven mapper — exercised end-to-end with a mocked transport.

Proves the declarative ``carriers/dhl.yaml`` produces the DHL Parcel DE payload
(fan-out, unit conversion, value maps, conditional blocks) and normalizes the
response, without any per-carrier Python.
"""

from __future__ import annotations

import base64
import json
from decimal import Decimal

import httpx
import pytest

from shiplabel import auth
from shiplabel.canonical import (
    Billing,
    CanonicalShipmentRequest,
    CarrierSelection,
    Cod,
    Dimensions,
    IdentCheck,
    Insurance,
    Parcel,
    Party,
    References,
    Services,
)
from shiplabel.engine import SpecMapper
from shiplabel.errors import CarrierApiError, UnsupportedServiceError
from shiplabel.loader import get_spec
from shiplabel.service import create_label

CONFIG = {
    "dhl_api_key": "k",
    "dhl_api_secret": "s",
    "dhl_username": "u",
    "dhl_password": "p",
    "dhl_accountnumber": "33333333330102",
    "dhl_sandbox": True,
}

FAKE_LABEL = base64.b64encode(b"%PDF-1.4 fake").decode()


def _req(**overrides) -> CanonicalShipmentRequest:
    base = dict(
        carrier=CarrierSelection(code="dhl", product="V01PAK"),
        billing=Billing(account_number="33333333330102"),
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
            street="Beispielweg",
            house_number="2",
            postal_code="80331",
            city="München",
            country="DE",
        ),
        parcels=[
            Parcel(
                id="p1",
                weight_kg=Decimal("1.5"),
                dimensions_cm=Dimensions(length=20, width=15, height=10),
            )
        ],
        references=References(delivery_note="LS-4711"),
    )
    base.update(overrides)
    return CanonicalShipmentRequest(**base)


def _client(capture: dict) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/token"):
            return httpx.Response(200, json={"access_token": "tok", "expires_in": 1700})
        if request.url.path.endswith("/orders"):
            capture["body"] = json.loads(request.content)
            capture["query"] = dict(request.url.params)
            return httpx.Response(
                200,
                json={
                    "items": [{"shipmentNo": "00340434161094015902", "label": {"b64": FAKE_LABEL}}]
                },
            )
        return httpx.Response(404)

    return httpx.Client(transport=httpx.MockTransport(handler))


@pytest.fixture(autouse=True)
def _clear_token_cache():
    auth._cache.clear()
    yield


def test_create_label_happy_path():
    capture: dict = {}
    result = create_label(CONFIG, _req(), client=_client(capture))

    assert result.shipment_number == "00340434161094015902"
    assert result.parcels[0].label.data == FAKE_LABEL
    assert result.parcels[0].tracking_url.endswith("piececode=00340434161094015902")

    ship = capture["body"]["shipments"][0]
    assert ship["product"] == "V01PAK"
    assert ship["billingNumber"] == "33333333330102"
    assert ship["refNo"] == "LS-4711"
    assert ship["consignee"]["postalCode"] == "80331"
    assert ship["consignee"]["country"] == "DEU"  # ISO2 -> ISO3 via value_maps
    assert ship["details"]["weight"] == {"uom": "g", "value": 1500}  # kg -> g, typed int
    assert ship["details"]["dim"] == {"uom": "mm", "height": 100, "length": 200, "width": 150}
    assert "services" not in ship  # no services requested -> block omitted
    assert capture["query"]["docFormat"] == "PDF"


def test_services_and_fan_out():
    capture: dict = {}
    req = _req(
        parcels=[
            Parcel(id="a", weight_kg=Decimal("1.0")),
            Parcel(id="b", weight_kg=Decimal("2.0")),
        ],
        services=Services(
            age_check=18,
            insurance=Insurance(value=Decimal("500")),
            cod=Cod(amount=Decimal("49.90"), iban="DE00", account_owner="Muster GmbH"),
            ident_check=IdentCheck(first_name="Erika", last_name="Beispiel", minimum_age=18),
        ),
    )
    create_label(CONFIG, req, client=_client(capture))

    shipments = capture["body"]["shipments"]
    assert len(shipments) == 2  # one shipment per parcel (fan-out)
    svc = shipments[0]["services"]
    assert svc["visualCheckOfAge"] == "A18"
    assert svc["identCheck"]["minimumAge"] == "A18"
    assert svc["additionalInsurance"] == {"currency": "EUR", "value": 500.0}
    assert svc["cashOnDelivery"]["amount"] == {"currency": "EUR", "value": 49.9}
    assert "dim" not in shipments[1]["details"]  # parcel b has no dimensions -> omitted


def test_unsupported_service_raises():
    req = _req(services=Services(saturday_delivery=True))
    with pytest.raises(UnsupportedServiceError):
        SpecMapper(get_spec("dhl"), CONFIG).to_payload(req)


def test_carrier_error_surfaces_messages():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/token"):
            return httpx.Response(200, json={"access_token": "tok", "expires_in": 1700})
        return httpx.Response(
            400,
            json={
                "detail": "Bad request",
                "items": [{"validationMessages": [{"validationMessage": "postalCode invalid"}]}],
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(CarrierApiError) as exc:
        create_label(CONFIG, _req(), client=client)
    assert "postalCode invalid" in str(exc.value)
    assert exc.value.status == 400
