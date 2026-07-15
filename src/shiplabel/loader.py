"""Discovers and caches carrier specs.

Carrier specs are declarative JSON files bundled with this package under
``shiplabel/carriers/*.json`` — one generic engine (:mod:`shiplabel.engine`)
executes any of them, so adding or tweaking a carrier is a JSON edit, not a code
change.

To add or override a carrier without forking, point ``SHIPLABEL_CARRIERS_DIR``
at a directory of ``*.json`` specs. Files there are loaded after the bundled
ones and win on a code clash, so you can override a shipped carrier or add a new
one purely from config.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from importlib.resources import files
from pathlib import Path

from .spec import CarrierSpec


def _spec_paths() -> list[Path]:
    """Bundled specs first, then any from ``SHIPLABEL_CARRIERS_DIR`` (override)."""
    paths: list[Path] = []
    bundled = files(__package__).joinpath("carriers")
    if bundled.is_dir():
        paths.extend(sorted(Path(str(p)) for p in bundled.iterdir() if p.name.endswith(".json")))
    extra_dir = os.getenv("SHIPLABEL_CARRIERS_DIR")
    if extra_dir:
        extra = Path(extra_dir)
        if extra.is_dir():
            paths.extend(sorted(extra.glob("*.json")))
    return paths


@lru_cache(maxsize=1)
def _load_specs() -> dict[str, CarrierSpec]:
    specs: dict[str, CarrierSpec] = {}
    for path in _spec_paths():
        spec = CarrierSpec(**(json.loads(path.read_text()) or {}))
        specs[spec.code] = spec  # later paths (SHIPLABEL_CARRIERS_DIR) override bundled
    return specs


def get_spec(code: str) -> CarrierSpec | None:
    return _load_specs().get(code)


def spec_codes() -> list[str]:
    return sorted(_load_specs())
