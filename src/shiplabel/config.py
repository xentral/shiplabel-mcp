"""Carrier account settings for the CLI: named TOML profiles + env overrides.

The engine itself is credential-agnostic — it takes a plain ``config`` dict — so
an embedding caller (an agent, this backend) can build that dict however it
likes. This module is only the convenience layer for driving the CLI.

Resolution order (later wins):
1. ``[profiles.<name>]`` from the TOML file
   (``--config`` path, else ``$SHIPLABEL_CONFIG``, else ``~/.config/shiplabel/carriers.toml``)
2. ``SHIPLABEL_<KEY>`` environment variables -> lowercase ``<key>``
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

from .errors import ConfigError

_ENV_PREFIX = "SHIPLABEL_"
_DEFAULT_PATH = Path.home() / ".config" / "shiplabel" / "carriers.toml"


def _coerce(value: str) -> Any:
    low = value.strip().lower()
    if low in ("true", "false"):
        return low == "true"
    return value


def load_config(
    profile: str | None = None, *, path: str | os.PathLike | None = None
) -> dict[str, Any]:
    config: dict[str, Any] = {}

    if profile:
        file = Path(path or os.environ.get("SHIPLABEL_CONFIG") or _DEFAULT_PATH)
        if not file.exists():
            raise ConfigError(f"profile '{profile}' requested but no config at {file}")
        table = tomllib.loads(file.read_text())
        section = (table.get("profiles") or {}).get(profile)
        if section is None:
            raise ConfigError(f"profile '{profile}' not found in {file}")
        config.update(section)

    for key, value in os.environ.items():
        if key.startswith(_ENV_PREFIX) and key != "SHIPLABEL_CONFIG":
            config[key[len(_ENV_PREFIX) :].lower()] = _coerce(value)

    return config
