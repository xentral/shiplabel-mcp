"""Carrier spec model — the validated shape of a ``carriers/*.yaml`` file.

A spec is pure data: endpoints, auth scheme, a payload *template* (canonical ->
carrier body), and where the tracking number + label sit in the response. The
generic engine (``engine.py``) executes it; there is no per-carrier Python.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

AuthScheme = Literal[
    "none",
    "bearer",
    "basic",
    "api_key_header",
    "oauth2_password",
    "oauth2_client_credentials",
]


class TransportSpec(BaseModel):
    # base_url / token_url are {prod, sandbox} maps, or a single string.
    base_url: dict[str, str] | str
    endpoint: str
    method: str = "POST"
    query: dict[str, Any] = Field(default_factory=dict)
    # Config key whose truthiness selects the sandbox environment.
    sandbox_key: str = "sandbox"


class AuthSpec(BaseModel):
    scheme: AuthScheme
    token_url: dict[str, str] | str | None = None
    # logical name -> config key, e.g. {client_id: dhl_api_key, ...}
    keys: dict[str, str] = Field(default_factory=dict)
    header: str | None = None  # api_key_header: the header name to place the key in
    scope: str | None = None
    use_basic_header: bool = False  # client_credentials: send creds as Basic auth header
    # Extra static/templated headers merged onto every request (e.g. DPD's
    # multi-header partner+user credentials). Values are rendered against {config}.
    headers: dict[str, str] = Field(default_factory=dict)


class ResponseSpec(BaseModel):
    # Dotted path to the per-parcel item list; omit if the body itself is one item.
    # A path segment may be a list index ("0") or end in "[]" to flatten a list.
    items_path: str | None = None
    tracking: str  # dotted path within an item
    label: str | None = None  # dotted path within an item
    # Root-level label shared by all items (carriers that return one combined PDF).
    label_shared_path: str | None = None
    label_format: str = "pdf"
    label_format_path: str | None = None  # per-item dotted path to the label format
    # Report the requested label.format on the result (carriers that honor it in
    # the request rather than echoing it in the response, e.g. DHL/FedEx).
    label_format_from_request: bool = False
    label_is_url: bool = False  # True -> engine GETs the URL and base64-encodes it
    tracking_url: str | None = None  # template with {{ tracking }}


class ConfigKey(BaseModel):
    key: str
    required: bool = True
    note: str = ""
    # Where the value comes from. "customer" = entered in the UI / passed by the
    # caller. "env" = platform-owned, filled from the backend environment and
    # never shown as a user input (e.g. a developer-app key the vendor holds).
    source: Literal["customer", "env"] = "customer"
    # For source="env": the environment variable to read. Either a single name,
    # or a {prod, sandbox} map picked by the carrier's sandbox flag. The engine
    # fills the config key from here when the caller didn't pass it inline.
    env: str | dict[str, str] | None = None


class ErrorSpec(BaseModel):
    when_status_ge: int = 400
    # A non-empty value at this dotted path marks an error even on a 2xx status
    # (carriers that return errors in the body, e.g. DPD's ErrorDataList).
    when_path_nonempty: str | None = None
    detail_path: str | None = None  # dotted path to a single top-level message
    list_path: str | None = None  # dotted path to a message list ("[]" flattens)
    message_fields: list[str] = Field(default_factory=list)  # first non-empty wins


class CarrierSpec(BaseModel):
    code: str
    label: str | None = None  # human-readable carrier name
    transport: TransportSpec
    auth: AuthSpec
    # Canonical service fields this carrier supports; a requested service outside
    # this set raises UnsupportedServiceError instead of being silently dropped.
    capabilities: list[str] = Field(default_factory=list)
    # How this carrier handles customs on export:
    #   label_api — HS code / value go into the label request (mapped in `request`)
    #   document  — HS code goes into a SEPARATE customs document (CN23 / invoice),
    #               NOT the label API — the label call carries no customs data
    #   none      — customs not applicable (e.g. domestic returns)
    customs_via: Literal["label_api", "document", "none"] = "label_api"
    customs_note: str = ""  # free-text hint shown to the user (e.g. for `document`)
    # Output label formats this carrier can return (pdf/zpl/png/gif). A requested
    # label.format outside this set is rejected. Empty = only the default (pdf).
    label_formats: list[str] = Field(default_factory=list)
    # Self-documentation: which config keys this carrier needs (for the MCP
    # `describe` action). Not enforced — the values are read from `config`.
    config_keys: list[ConfigKey] = Field(default_factory=list)
    value_maps: dict[str, dict[str, str]] = Field(default_factory=dict)
    request: Any  # the payload template tree ($for / $if / {{ expr }})
    response: ResponseSpec
    error: ErrorSpec = Field(default_factory=ErrorSpec)
