"""Standalone MCP server exposing the ``shiplabel`` engine.

Three tools — ``list_carriers``, ``describe_carrier``, ``create_label`` — let any
MCP client (Claude Desktop, Claude Code, …) create carrier-agnostic shipping
labels. Carrier-direct: no account with us is required. Credentials come from the
environment (``SHIPLABEL_<KEY>`` / a TOML profile) or an inline ``config`` object
passed with the call.
"""

from __future__ import annotations

import asyncio
import base64
import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from shiplabel import (
    CanonicalShipmentRequest,
    ShipLabelError,
    available_carriers,
    describe,
    load_config,
)
from shiplabel import (
    create_label as _create_label,
)

mcp = FastMCP(
    "shiplabel",
    instructions=(
        "Carrier-agnostic shipping labels (DHL, DPD, UPS, FedEx, GLS, Sendcloud, "
        "Shipcloud, DHL Return). Call `list_carriers` to see what is available, "
        "`describe_carrier` to learn a carrier's config keys and supported "
        "services, then `create_label` with a canonical shipment request. Bring "
        "your own carrier account — set credentials via SHIPLABEL_* env vars or "
        "pass them inline in `config`."
    ),
)


@mcp.tool()
def list_carriers() -> str:
    """List the shipping carriers this server can create labels for."""
    return json.dumps({"carriers": available_carriers()}, ensure_ascii=False, indent=2)


@mcp.tool()
def describe_carrier(carrier: str | None = None) -> str:
    """Describe the canonical shipment request and, if `carrier` is given, that
    carrier's required config keys, supported services and label formats.

    Call this before `create_label` to learn exactly what to pass.
    """
    return json.dumps(describe(carrier), ensure_ascii=False, indent=2)


@mcp.tool()
async def create_label(
    request: dict[str, Any],
    carrier: str | None = None,
    config: dict[str, Any] | None = None,
    include_label: bool = True,
) -> str:
    """Create a shipping label from a canonical shipment request.

    `request` is a canonical shipment request:
    `{carrier: {code, product}, sender, recipient, parcels: [{id, weight_kg,
    dimensions_cm}], references, label: {format}}`. Addresses need
    name/street/postal_code/city/country.

    `carrier` overrides `request.carrier.code` when set. `config` supplies carrier
    credential keys (e.g. `dhl_username`) merged over the environment; use it for
    ad-hoc testing without setting SHIPLABEL_* env vars. `include_label=false`
    returns a compact tracking-only reply without the base64 label.

    Returns the shipment number and, per parcel, the tracking number/URL, label
    format and (unless disabled) the base64-encoded label.
    """
    try:
        shipment = CanonicalShipmentRequest(**request)
    except Exception as exc:  # noqa: BLE001 — surface parse/validation errors to the caller
        return f"Invalid `request`: {exc}"
    if carrier:
        shipment.carrier.code = carrier

    cfg = load_config()  # SHIPLABEL_<KEY> env + TOML profile
    if config:
        if not isinstance(config, dict):
            return "`config` must be an object of carrier credential keys."
        cfg.update(config)

    try:
        # create_label does blocking HTTP; keep it off the event loop.
        result = await asyncio.to_thread(_create_label, cfg, shipment)
    except ShipLabelError as exc:
        return f"error: {exc}"
    except KeyError as exc:  # unknown carrier code
        return f"error: unknown carrier {exc}"

    parcels: list[dict[str, Any]] = []
    for parcel in result.parcels:
        entry: dict[str, Any] = {
            "tracking_number": parcel.tracking_number,
            "tracking_url": parcel.tracking_url,
            "label_format": parcel.label.format,
            "label_bytes": len(base64.b64decode(parcel.label.data)),
        }
        if include_label:
            entry["label_base64"] = parcel.label.data
        parcels.append(entry)
    return json.dumps(
        {"shipment_number": result.shipment_number, "parcels": parcels},
        ensure_ascii=False,
        indent=2,
    )
