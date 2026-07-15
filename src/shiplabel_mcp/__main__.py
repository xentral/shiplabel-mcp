"""Entry point for the shiplabel MCP server.

    python -m shiplabel_mcp                 # stdio (Claude Desktop / Claude Code)
    python -m shiplabel_mcp --http          # streamable HTTP on 127.0.0.1:8000
    python -m shiplabel_mcp --http --host 0.0.0.0 --port 9000

Installed as the ``shiplabel-mcp`` console script (see pyproject.toml).
"""

from __future__ import annotations

import argparse

from .server import mcp


def main() -> None:
    parser = argparse.ArgumentParser(prog="shiplabel-mcp", description="shiplabel MCP server")
    parser.add_argument(
        "--http",
        action="store_true",
        help="Serve over streamable HTTP instead of stdio.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="HTTP bind host (with --http).")
    parser.add_argument("--port", type=int, default=8000, help="HTTP bind port (with --http).")
    args = parser.parse_args()

    if args.http:
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
