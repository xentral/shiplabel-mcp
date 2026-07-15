"""Orchestrator: the single entrypoint ``create_label(config, request)``.

Resolves the carrier to a mapper — a declarative YAML spec by default, or a
registered code plugin for the rare carrier a spec can't express — runs the
canonical -> payload -> call -> canonical pipeline, and returns a normalized
result with the label as base64.
"""

from __future__ import annotations

from typing import Any

import httpx

from .canonical import CanonicalLabelResult, CanonicalShipmentRequest
from .engine import SpecMapper
from .loader import get_spec, spec_codes
from .mapper import CarrierMapper


def _resolve_mapper(code: str, config: dict[str, Any]) -> CarrierMapper:
    spec = get_spec(code)
    if spec is not None:
        return SpecMapper(spec, config)
    raise KeyError(f"No carrier '{code}'. Known: {available_carriers()}")


def available_carriers() -> list[str]:
    return spec_codes()


def create_label(
    config: dict[str, Any],
    request: CanonicalShipmentRequest,
    *,
    timeout: float = 30.0,
    client: httpx.Client | None = None,
) -> CanonicalLabelResult:
    """Single entrypoint. ``config`` = carrier account settings for the request's carrier.

    Pipeline: canonical -> carrier payload -> auth+HTTP -> canonical result
    (labels normalized to base64).
    """
    mapper = _resolve_mapper(request.carrier.code, config)
    payload = mapper.to_payload(request)
    owns_client = client is None
    client = client or httpx.Client(timeout=timeout)
    try:
        raw = mapper.call(payload, client)
        return mapper.from_response(raw, client)
    finally:
        if owns_client:
            client.close()
