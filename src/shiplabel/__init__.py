"""shiplabel — carrier-agnostic shipping-label service.

Build one ``CanonicalShipmentRequest`` and hand it to ``create_label``; get a
normalized ``CanonicalLabelResult`` (tracking + base64 label) regardless of
carrier. Carriers are defined declaratively in ``carriers/*.json`` and executed
by a generic engine — adding one is a spec file, not code.
"""

from __future__ import annotations

from .canonical import (
    Billing,
    CanonicalLabelResult,
    CanonicalShipmentRequest,
    CarrierSelection,
    Cod,
    Customs,
    CustomsItem,
    Dimensions,
    IdentCheck,
    Insurance,
    Label,
    Parcel,
    Party,
    References,
    Services,
)
from .config import load_config
from .describe import describe
from .errors import (
    AuthError,
    CarrierApiError,
    ConfigError,
    LabelRequestError,
    ShipLabelError,
    UnsupportedServiceError,
)
from .service import available_carriers, create_label

__all__ = [
    "create_label",
    "available_carriers",
    "describe",
    "load_config",
    "CanonicalShipmentRequest",
    "CanonicalLabelResult",
    "CarrierSelection",
    "Billing",
    "Party",
    "Parcel",
    "Dimensions",
    "References",
    "Services",
    "Cod",
    "Insurance",
    "IdentCheck",
    "Customs",
    "CustomsItem",
    "Label",
    "ShipLabelError",
    "ConfigError",
    "AuthError",
    "UnsupportedServiceError",
    "LabelRequestError",
    "CarrierApiError",
]
