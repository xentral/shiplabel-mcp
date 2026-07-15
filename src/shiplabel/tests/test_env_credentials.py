"""Generic ``source: "env"`` credential resolution (spec-driven, any carrier).

A config key marked ``source: "env"`` is platform-owned — filled from the backend
environment, never customer input. Uses a synthetic spec so the test is
independent of any shipped carrier definition.
"""

from __future__ import annotations

import pytest

from shiplabel.engine import SpecMapper
from shiplabel.spec import CarrierSpec

_SPEC = CarrierSpec(
    code="test",
    transport={"base_url": "https://example.test", "endpoint": "/o", "sandbox_key": "test_sandbox"},
    auth={"scheme": "none"},
    config_keys=[
        {
            "key": "api_key",
            "source": "env",
            "env": {"prod": "TEST_PROD_KEY", "sandbox": "TEST_DEV_KEY"},
        },
        {"key": "single", "source": "env", "env": "TEST_SINGLE"},
        {"key": "typed_by_customer"},  # source defaults to "customer" — never env-filled
    ],
    request={},
    response={"tracking": "shipmentNo"},
)


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("TEST_PROD_KEY", "prod-value")
    monkeypatch.setenv("TEST_DEV_KEY", "dev-value")
    monkeypatch.setenv("TEST_SINGLE", "single-value")


def test_sandbox_flag_selects_the_development_variable():
    config = {"test_sandbox": True}
    SpecMapper(_SPEC, config)
    assert config["api_key"] == "dev-value"


def test_without_sandbox_flag_the_production_variable_is_used():
    config: dict = {}
    SpecMapper(_SPEC, config)
    assert config["api_key"] == "prod-value"


def test_plain_string_env_is_read_regardless_of_sandbox():
    config: dict = {}
    SpecMapper(_SPEC, config)
    assert config["single"] == "single-value"


def test_inline_value_wins_over_the_environment():
    config = {"test_sandbox": True, "api_key": "inline"}
    SpecMapper(_SPEC, config)
    assert config["api_key"] == "inline"


def test_customer_source_keys_are_never_filled_from_env(monkeypatch):
    monkeypatch.setenv("TYPED_BY_CUSTOMER", "leaked")
    config: dict = {}
    SpecMapper(_SPEC, config)
    assert "typed_by_customer" not in config
