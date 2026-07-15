"""Canonical shipment request/response models — the stable contract every carrier maps to.

Build one ``CanonicalShipmentRequest`` from your source data and hand it to any
carrier mapper; get one ``CanonicalLabelResult`` back regardless of carrier.
The carrier-specific translation lives entirely in the mappers.
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class ShipmentType(str, Enum):
    OUTBOUND = "outbound"
    RETURN = "return"


class Party(BaseModel):
    name: str
    company: str | None = None
    contact_person: str | None = None
    street: str
    house_number: str | None = None
    address_line2: str | None = None
    postal_code: str
    city: str
    state: str | None = None
    country: str = Field(..., min_length=2, max_length=2, description="ISO-3166-1 alpha-2")
    email: str | None = None
    phone: str | None = None

    @field_validator("country")
    @classmethod
    def _upper(cls, v: str) -> str:
        return v.upper()


class Dimensions(BaseModel):
    length: int  # cm
    width: int  # cm
    height: int  # cm


class Parcel(BaseModel):
    id: str
    weight_kg: Decimal
    dimensions_cm: Dimensions | None = None
    content: str | None = None
    reference: str | None = None


class References(BaseModel):
    delivery_note: str | None = None
    order: str | None = None
    invoice: str | None = None
    project: str | None = None
    custom1: str | None = None
    custom2: str | None = None


class Cod(BaseModel):
    amount: Decimal
    currency: str = "EUR"
    account_owner: str | None = None
    iban: str | None = None
    bic: str | None = None


class Insurance(BaseModel):
    value: Decimal
    currency: str = "EUR"


class IdentCheck(BaseModel):
    last_name: str
    first_name: str
    date_of_birth: str | None = None  # YYYY-MM-DD
    minimum_age: Literal[16, 18]


class Notification(BaseModel):
    email: str | None = None
    sms: str | None = None


class Services(BaseModel):
    """Normalized cross-carrier capabilities. Omit what you don't need.

    A mapper translates the ones it supports and MUST reject (not silently drop)
    a requested service the carrier can't do — raise ``UnsupportedServiceError``.
    """

    cod: Cod | None = None
    insurance: Insurance | None = None
    age_check: Literal[16, 18] | None = None
    ident_check: IdentCheck | None = None
    notification: Notification | None = None
    premium: bool = False
    saturday_delivery: bool = False
    return_label_with_shipment: bool = False


class CustomsItem(BaseModel):
    description: str
    hs_code: str | None = None
    country_of_origin: str | None = None
    quantity: int = 1
    net_weight_kg: Decimal | None = None
    value: Decimal
    currency: str = "EUR"


class Customs(BaseModel):
    # PRESENT | COMMERCIAL_SAMPLE | DOCUMENT | RETURN_OF_GOODS | OTHER | SALE
    export_type: str = "COMMERCIAL_SAMPLE"
    terms_of_trade: str | None = None  # incoterm, e.g. "DAP"
    invoice_number: str | None = None
    invoice_date: str | None = None
    items: list[CustomsItem] = Field(default_factory=list)


class Label(BaseModel):
    # None -> the carrier's default (its first supported format) is used.
    format: Literal["pdf", "png", "zpl", "gif"] | None = None
    size: str = "A6"
    orientation: Literal["portrait", "landscape"] = "portrait"
    dpi: int = 300


class CarrierOption(BaseModel):
    """Escape hatch for carrier-specific extras with no canonical field."""

    id: str
    value: Any


class CarrierSelection(BaseModel):
    code: str  # internal carrier key: dhl, dpd, ups, fedex, ...
    product: str | None = None  # carrier product/service code
    carrier_options: list[CarrierOption] = Field(default_factory=list)


class Billing(BaseModel):
    account_number: str | None = None


class Metadata(BaseModel):
    order_id: str | None = None
    drop_off_location: dict[str, Any] | None = None


class CanonicalShipmentRequest(BaseModel):
    shipment_type: ShipmentType = ShipmentType.OUTBOUND
    carrier: CarrierSelection
    billing: Billing = Field(default_factory=Billing)
    sender: Party
    recipient: Party
    return_address: Party | None = None
    parcels: list[Parcel] = Field(..., min_length=1)
    references: References = Field(default_factory=References)
    services: Services = Field(default_factory=Services)
    customs: Customs | None = None
    label: Label = Field(default_factory=Label)
    metadata: Metadata = Field(default_factory=Metadata)

    @property
    def is_international(self) -> bool:
        return self.sender.country != self.recipient.country


# ---- Response side (what every mapper returns) ----


class LabelFile(BaseModel):
    format: str  # pdf | png | zpl | gif
    encoding: Literal["base64"] = "base64"  # mappers normalize URL labels to base64
    data: str  # base64 string


class ParcelResult(BaseModel):
    tracking_number: str
    tracking_url: str | None = None
    label: LabelFile


class ExportDocument(BaseModel):
    type: str  # e.g. "CN23"
    data: str  # base64
    encoding: Literal["base64"] = "base64"


class CanonicalLabelResult(BaseModel):
    shipment_number: str  # master/lead tracking number
    parcels: list[ParcelResult]
    export_documents: list[ExportDocument] = Field(default_factory=list)
