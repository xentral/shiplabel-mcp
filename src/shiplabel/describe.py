"""Self-documentation for the shipping service.

Answers "what do I pass to get a label?" without anything being stored: the
canonical request shape (same for every carrier) plus each carrier's credential
keys, supported services and output formats.
"""

from __future__ import annotations

from typing import Any

from .loader import get_spec
from .service import available_carriers

# A minimal, valid canonical request — the shape callers build for create_label.
REQUEST_EXAMPLE: dict[str, Any] = {
    "carrier": {"code": "dhl", "product": "V01PAK"},
    "billing": {"account_number": "33333333330102"},
    "sender": {
        "name": "Muster GmbH",
        "street": "Musterstr.",
        "house_number": "1",
        "postal_code": "10115",
        "city": "Berlin",
        "country": "DE",
    },
    "recipient": {
        "name": "Erika Beispiel",
        "street": "Beispielweg",
        "house_number": "2",
        "postal_code": "80331",
        "city": "München",
        "country": "DE",
        "email": "erika@example.com",
    },
    "parcels": [
        {"id": "p1", "weight_kg": 1.5, "dimensions_cm": {"length": 20, "width": 15, "height": 10}},
    ],
    "references": {"delivery_note": "LS-4711"},
    "label": {"format": "pdf"},
}

REQUEST_FIELDS: dict[str, str] = {
    "carrier.code": "required — carrier key (see `carriers`).",
    "carrier.product": "optional — carrier service/product code.",
    "sender / recipient": "required — name, street, postal_code, city, country (ISO-2); "
    "optional company, house_number, email, phone, state.",
    "parcels[]": "required (>=1) — id, weight_kg; optional dimensions_cm {length,width,height}.",
    "billing.account_number": "carrier account number (some carriers take it from config).",
    "references": "optional — delivery_note, order, invoice.",
    "services": "optional — cod, insurance, age_check, ident_check (only where the carrier supports them).",
    "label.format": "optional — pdf/zpl/png/gif; omitted uses the carrier's default (its first format).",
}


def _carrier_info(code: str) -> dict[str, Any] | None:
    spec = get_spec(code)
    if spec is None:
        return None
    formats = spec.label_formats or sorted(spec.value_maps.get("label_format", {}))
    return {
        "code": spec.code,
        "name": spec.label,
        "config_keys": [ck.model_dump() for ck in spec.config_keys],
        "services": spec.capabilities,
        "label_formats": formats,
        "default_format": (formats[0] if formats else "pdf"),
        "customs_via": spec.customs_via,
        "customs_note": spec.customs_note,
    }


def describe(code: str | None = None) -> dict[str, Any]:
    """Describe the request shape and, if ``code`` is given, one carrier's config."""
    if code:
        info = _carrier_info(code)
        if info is None:
            return {"error": f"unknown carrier '{code}'", "carriers": available_carriers()}
        return {
            "carrier": info,
            "request_example": REQUEST_EXAMPLE,
            "request_fields": REQUEST_FIELDS,
        }
    return {
        "carriers": available_carriers(),
        "request_example": REQUEST_EXAMPLE,
        "request_fields": REQUEST_FIELDS,
        "hint": "Call describe with a `carrier` to see its required config keys and formats.",
    }
