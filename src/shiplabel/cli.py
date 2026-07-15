"""Command-line interface: ``python -m shiplabel <command>``.

    shiplabel carriers
    shiplabel create --from request.json --profile dhl-sandbox --out label.pdf
    echo '{...}' | shiplabel create --carrier dhl --profile dhl-sandbox --json

The request is a JSON document matching ``CanonicalShipmentRequest`` — the same
shape an agent would build — read from a file or stdin.
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path
from typing import Any

from .canonical import CanonicalShipmentRequest
from .config import load_config
from .errors import ShipLabelError
from .service import available_carriers, create_label


def _read_request(source: str) -> dict[str, Any]:
    raw = sys.stdin.read() if source == "-" else Path(source).read_text()
    return json.loads(raw)


def _write_labels(result, out: str) -> list[str]:
    """Write each parcel label to disk; single parcel -> exact ``out`` name."""
    stem = Path(out)
    written = []
    for i, parcel in enumerate(result.parcels):
        target = stem if len(result.parcels) == 1 else stem.with_stem(f"{stem.stem}_{i}")
        target.write_bytes(base64.b64decode(parcel.label.data))
        written.append(str(target))
    return written


def _cmd_carriers(_: argparse.Namespace) -> int:
    for code in available_carriers():
        print(code)
    return 0


def _cmd_create(args: argparse.Namespace) -> int:
    data = _read_request(args.from_)
    request = CanonicalShipmentRequest(**data)
    if args.carrier:
        request.carrier.code = args.carrier
    config = load_config(args.profile, path=args.config)
    if args.sandbox:
        config[f"{request.carrier.code}_sandbox"] = True

    result = create_label(config, request)

    for parcel in result.parcels:
        print(f"tracking: {parcel.tracking_number}  {parcel.tracking_url or ''}".rstrip())
    if args.out:
        for path in _write_labels(result, args.out):
            print(f"label -> {path}")
    if args.json:
        print(result.model_dump_json(indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="shiplabel", description="Create carrier shipping labels."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("carriers", help="List available carriers").set_defaults(func=_cmd_carriers)

    create = sub.add_parser("create", help="Create a shipping label from a canonical request")
    create.add_argument(
        "--from", dest="from_", default="-", help="Request JSON file, or '-' for stdin"
    )
    create.add_argument("--carrier", help="Override the carrier code in the request")
    create.add_argument("--profile", help="Credential profile name from the TOML config")
    create.add_argument(
        "--config", help="Path to the TOML config (else $SHIPLABEL_CONFIG / default)"
    )
    create.add_argument(
        "--sandbox", action="store_true", help="Use the carrier sandbox environment"
    )
    create.add_argument("--out", help="Write the label(s) to this file (base64-decoded)")
    create.add_argument("--json", action="store_true", help="Print the full result as JSON")
    create.set_defaults(func=_cmd_create)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except ShipLabelError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
