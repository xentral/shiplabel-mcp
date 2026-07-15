"""Exception hierarchy. Fail loud and specific; never silently drop a paid service."""

from __future__ import annotations


class ShipLabelError(Exception):
    """Base for all shiplabel errors."""


class ConfigError(ShipLabelError):
    """Missing/invalid carrier configuration (credentials, product, ...)."""


class AuthError(ShipLabelError):
    """Auth/token acquisition failed (401/403)."""


class UnsupportedServiceError(ShipLabelError):
    """A requested canonical service is not supported by this carrier.

    Raise instead of ignoring — e.g. an age check on a carrier that has none —
    so the caller never believes a paid service was applied when it was not.
    """

    def __init__(self, carrier: str, service: str):
        super().__init__(f"{carrier} does not support service '{service}'")
        self.carrier, self.service = carrier, service


class LabelRequestError(ShipLabelError):
    """Carrier accepted the call but returned no usable label/tracking."""


class CarrierApiError(ShipLabelError):
    """Carrier returned an error response. Carries the parsed messages."""

    def __init__(self, carrier: str, messages: list[str], status: int | None = None):
        super().__init__(f"{carrier} API error ({status}): {'; '.join(messages)}")
        self.carrier, self.messages, self.status = carrier, messages, status
