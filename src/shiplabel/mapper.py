"""Carrier mapper contract.

Every carrier is a declarative ``carriers/*.yaml`` spec executed by the generic
``SpecMapper`` (see ``engine.py``), which implements this contract. The contract
is kept as an explicit base class so the canonical -> payload -> call ->
canonical pipeline in ``service.py`` has one interface to depend on.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import httpx

from .canonical import CanonicalLabelResult, CanonicalShipmentRequest


class CarrierMapper(ABC):
    """One per carrier. ``code`` must match ``CarrierSelection.code``."""

    code: str

    def __init__(self, config: dict[str, Any]):
        """``config`` = the carrier account settings (credentials, product, ...)."""
        self.config = config

    @abstractmethod
    def to_payload(self, request: CanonicalShipmentRequest) -> Any:
        """Canonical -> carrier-specific request body."""

    @abstractmethod
    def call(self, payload: Any, client: httpx.Client) -> Any:
        """Perform the HTTP call (incl. auth). Return the raw parsed response."""

    @abstractmethod
    def from_response(self, raw: Any, client: httpx.Client) -> CanonicalLabelResult:
        """Carrier response -> canonical result.

        Fetch URL-based labels here and return them base64-encoded so the rest of
        the pipeline stays carrier-agnostic.
        """
