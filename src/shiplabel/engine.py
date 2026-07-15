"""Generic spec-driven carrier mapper.

Turns a ``CarrierSpec`` (pure data) into a working ``CarrierMapper`` by:
1. rendering the payload template against the canonical request,
2. resolving the declared auth scheme and performing the HTTP call,
3. extracting tracking + label from the response by declared paths.

The template supports three constructs so a spec can express real payloads
without code:
- ``{{ expr }}`` — a Jinja expression on a leaf; a leaf that is *only* an
  expression yields its native Python value (int/dict/None), so numbers and
  nested objects stay typed.
- ``$for: "item in iterable"`` + ``$body`` — fan-out one canonical parcel (or
  customs item) into N carrier objects.
- ``$if: "<expr>"`` on a dict — drop the key when falsy; with ``$value`` it
  becomes a conditional scalar.

Computation the data layer can't express (unit math, value lookups) is done with
Jinja filters (``| int``) and the injected ``vmap()`` helper — not per-carrier code.
"""

from __future__ import annotations

import base64
import os
import re
from typing import Any

import httpx
import jinja2

from .auth import get_client_credentials_token, get_password_grant_token
from .canonical import (
    CanonicalLabelResult,
    CanonicalShipmentRequest,
    LabelFile,
    ParcelResult,
)
from .errors import CarrierApiError, ConfigError, LabelRequestError, UnsupportedServiceError
from .mapper import CarrierMapper
from .spec import CarrierSpec

# Canonical service fields checked against a spec's declared capabilities.
_SERVICE_FIELDS = (
    "cod",
    "insurance",
    "age_check",
    "ident_check",
    "notification",
    "premium",
    "saturday_delivery",
    "return_label_with_shipment",
)

_OMIT = object()  # a rendered node that should be dropped from its parent
# Matches a leaf that is exactly ONE expression (no text or second expression
# around it), so it can yield a native Python value instead of a string.
_SINGLE_EXPR = re.compile(r"^\s*\{\{((?:(?!\}\}).)+)\}\}\s*$", re.S)


def _dig(obj: Any, path: str | None) -> Any:
    """Walk a dotted path through nested dicts/objects/list-indices; None if a hop misses.

    A numeric segment indexes a list ("output.transactionShipments.0.pieceResponses").
    """
    if not path:
        return obj
    cur = obj
    for key in path.split("."):
        if isinstance(cur, list) and key.isdigit():
            idx = int(key)
            cur = cur[idx] if idx < len(cur) else None
        elif isinstance(cur, dict):
            cur = cur.get(key)
        else:
            cur = getattr(cur, key, None)
        if cur is None:
            return None
    return cur


def _flatten(obj: Any, path: str) -> list[Any]:
    """Collect values along a dotted path where a "[]" segment flattens a list."""
    current: list[Any] = [obj]
    for part in path.split("."):
        wildcard = part.endswith("[]")
        key = part[:-2] if wildcard else part
        nxt: list[Any] = []
        for node in current:
            value = node.get(key) if isinstance(node, dict) else getattr(node, key, None)
            if value is None:
                continue
            if wildcard and isinstance(value, list):
                nxt.extend(value)
            else:
                nxt.append(value)
        current = nxt
    return current


class SpecMapper(CarrierMapper):
    def __init__(self, spec: CarrierSpec, config: dict[str, Any]):
        super().__init__(config)
        self.spec = spec
        self.code = spec.code
        self._fill_env_sourced_credentials()
        # autoescape stays off on purpose: templates build carrier JSON payloads,
        # not HTML — HTML-escaping would corrupt values like "Müller & Co".
        self._env = jinja2.Environment(autoescape=False)  # noqa: S701
        self._env.globals["vmap"] = self._vmap
        self._expr_cache: dict[str, Any] = {}
        self._ctx: dict[str, Any] = {}  # set in to_payload, reused by call/from_response
        self._label_format = "pdf"

    def _fill_env_sourced_credentials(self) -> None:
        """Fill platform-owned credentials from the backend environment.

        A ``config_keys`` entry with ``source: "env"`` is not customer input — its
        value lives in the env (e.g. the vendor's DHL developer-app key). ``env``
        is a variable name, or a ``{prod, sandbox}`` map selected by the carrier's
        sandbox flag. An inline value the caller passed still wins. This keeps
        credential sourcing declarative in the spec — no per-carrier code."""
        sandbox = self._sandbox()
        for ck in self.spec.config_keys:
            if ck.source != "env" or not ck.env or self.config.get(ck.key):
                continue
            env_name = (
                ck.env if isinstance(ck.env, str) else ck.env.get("sandbox" if sandbox else "prod")
            )
            if env_name and (value := os.getenv(env_name)):
                self.config[ck.key] = value

    # ---- expression / template rendering ------------------------------------

    def _vmap(self, name: str, key: Any) -> Any:
        return self.spec.value_maps.get(name, {}).get(key, key)

    def _eval(self, expr: str, ctx: dict[str, Any]) -> Any:
        compiled = self._expr_cache.get(expr)
        if compiled is None:
            compiled = self._env.compile_expression(expr, undefined_to_none=True)
            self._expr_cache[expr] = compiled
        return compiled(**ctx)

    def _render_leaf(self, s: str, ctx: dict[str, Any]) -> Any:
        m = _SINGLE_EXPR.match(s)
        if m:  # a bare expression -> keep its native type
            return self._eval(m.group(1).strip(), ctx)
        if "{{" in s or "{%" in s:  # mixed text (e.g. a URL) -> string
            return self._env.from_string(s).render(**ctx)
        return s

    def _render(self, node: Any, ctx: dict[str, Any]) -> Any:
        if isinstance(node, dict):
            if "$for" in node:
                var, _, iterable = node["$for"].partition(" in ")
                items = self._eval(iterable.strip(), ctx) or []
                out = []
                for i, item in enumerate(items):
                    child = dict(ctx)
                    child[var.strip()] = item
                    child["loop"] = {"index0": i, "last": i == len(items) - 1}
                    rendered = self._render(node["$body"], child)
                    if rendered is not _OMIT:
                        out.append(rendered)
                return out
            if "$if" in node:
                if not self._render_leaf(node["$if"], ctx):
                    return _OMIT
                if "$value" in node:
                    return self._render(node["$value"], ctx)
                node = {k: v for k, v in node.items() if k != "$if"}
            return self._render_dict(node, ctx)
        if isinstance(node, list):
            rendered = [self._render(x, ctx) for x in node]
            return [x for x in rendered if x is not _OMIT]
        if isinstance(node, str):
            return self._render_leaf(node, ctx)
        return node  # int/float/bool/None literal

    def _render_dict(self, d: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in d.items():
            rendered = self._render(value, ctx)
            if rendered is not _OMIT:
                out[key] = rendered
        return out

    # ---- CarrierMapper contract ---------------------------------------------

    def to_payload(self, request: CanonicalShipmentRequest) -> Any:
        for field in _SERVICE_FIELDS:
            if getattr(request.services, field) and field not in self.spec.capabilities:
                raise UnsupportedServiceError(self.code, field)
        # Output format is optional: an explicit format is validated against the
        # carrier's set; when omitted, the carrier's first format is the default.
        explicit = request.label.format
        if explicit and self.spec.label_formats and explicit not in self.spec.label_formats:
            raise UnsupportedServiceError(self.code, f"label format '{explicit}'")
        default = self.spec.label_formats[0] if self.spec.label_formats else "pdf"
        request.label.format = explicit or default
        # Kept for the query renderer (call) and the result format (from_response).
        self._ctx = self._context(request)
        self._label_format = request.label.format
        return self._render(self.spec.request, self._ctx)

    def _context(self, request: CanonicalShipmentRequest) -> dict[str, Any]:
        return {
            "config": self.config,
            "carrier": request.carrier,
            "billing": request.billing,
            "sender": request.sender,
            "recipient": request.recipient,
            "return_address": request.return_address,
            "references": request.references,
            "services": request.services,
            "customs": request.customs,
            "parcels": request.parcels,
            "label": request.label,
            "metadata": request.metadata,
            "shipment_type": request.shipment_type.value,
            "is_international": request.is_international,
        }

    def _sandbox(self) -> bool:
        return bool(self.config.get(self.spec.transport.sandbox_key))

    @staticmethod
    def _pick_env(value: dict[str, str] | str, sandbox: bool) -> str:
        if isinstance(value, str):
            return value
        return value["sandbox" if sandbox else "prod"]

    def _auth_headers(self, client: httpx.Client, sandbox: bool) -> dict[str, str]:
        a = self.spec.auth
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        keys = {logical: self.config.get(cfg_key) for logical, cfg_key in a.keys.items()}
        cache_key = f"{self.code}:{keys.get('username') or keys.get('client_id')}:{sandbox}"
        if a.scheme == "oauth2_password":
            token = get_password_grant_token(
                token_url=self._pick_env(a.token_url, sandbox),
                client_id=keys["client_id"],
                client_secret=keys["client_secret"],
                username=keys["username"],
                password=keys["password"],
                client=client,
                cache_key=cache_key,
            )
            headers["Authorization"] = f"Bearer {token}"
        elif a.scheme == "oauth2_client_credentials":
            token = get_client_credentials_token(
                token_url=self._pick_env(a.token_url, sandbox),
                client_id=keys["client_id"],
                client_secret=keys["client_secret"],
                client=client,
                cache_key=cache_key,
                scope=a.scope,
                use_basic_header=a.use_basic_header,
            )
            headers["Authorization"] = f"Bearer {token}"
        elif a.scheme == "bearer":
            headers["Authorization"] = f"Bearer {keys['token']}"
        elif a.scheme == "api_key_header":
            if not a.header:
                raise ConfigError(f"{self.code}: api_key_header auth needs a 'header'")
            headers[a.header] = keys["api_key"]
        elif a.scheme == "basic":
            raw = f"{keys['username']}:{keys['password']}".encode()
            headers["Authorization"] = f"Basic {base64.b64encode(raw).decode()}"
        elif a.scheme != "none":
            raise ConfigError(f"{self.code}: unknown auth scheme '{a.scheme}'")

        # Extra static/templated headers (e.g. DPD's multi-header credentials).
        for name, template in a.headers.items():
            headers[name] = self._render_leaf(template, {"config": self.config})
        return headers

    def call(self, payload: Any, client: httpx.Client) -> Any:
        t = self.spec.transport
        sandbox = self._sandbox()
        url = self._pick_env(t.base_url, sandbox).rstrip("/") + t.endpoint
        # Query values are templated so they can read e.g. label.format.
        query = {k: self._render_leaf(str(v), self._ctx) for k, v in (t.query or {}).items()}
        resp = client.request(
            t.method,
            url,
            params=query or None,
            json=payload,
            headers=self._auth_headers(client, sandbox),
        )
        data = resp.json() if resp.content else {}
        e = self.spec.error
        body_error = bool(e.when_path_nonempty and _dig(data, e.when_path_nonempty))
        if resp.status_code >= e.when_status_ge or body_error:
            raise CarrierApiError(self.code, self._error_messages(data), resp.status_code)
        return data

    def _error_messages(self, data: Any) -> list[str]:
        e = self.spec.error
        msgs: list[str] = []
        if e.list_path:
            for item in _flatten(data, e.list_path):
                if isinstance(item, dict):
                    text = next((item[f] for f in e.message_fields if item.get(f)), None)
                    if text:
                        msgs.append(str(text))
                elif item:
                    msgs.append(str(item))
        if e.detail_path:
            detail = _dig(data, e.detail_path)
            if detail:
                msgs.append(str(detail))
        return msgs or [f"{self.code}: unknown error"]

    def from_response(self, raw: Any, client: httpx.Client) -> CanonicalLabelResult:
        r = self.spec.response
        items = _dig(raw, r.items_path) if r.items_path else [raw]
        if isinstance(items, dict):  # single item returned as an object, not a list
            items = [items]
        if not items:
            raise LabelRequestError(f"{self.code}: response contained no items")
        shared_label = _dig(raw, r.label_shared_path) if r.label_shared_path else None
        parcels: list[ParcelResult] = []
        first: str | None = None
        for item in items:
            tracking = _dig(item, r.tracking)
            label = (_dig(item, r.label) if r.label else None) or shared_label
            if not tracking or not label:
                raise LabelRequestError(f"{self.code}: missing tracking or label in item")
            if r.label_is_url:
                # The label URL usually sits behind the same auth as the API call.
                headers = self._auth_headers(client, self._sandbox())
                label = base64.b64encode(client.get(label, headers=headers).content).decode()
            fmt = _dig(item, r.label_format_path) if r.label_format_path else None
            if fmt is None and r.label_format_from_request:
                fmt = self._label_format
            first = first or str(tracking)
            tracking_url = (
                self._render_leaf(r.tracking_url, {"tracking": tracking})
                if r.tracking_url
                else None
            )
            parcels.append(
                ParcelResult(
                    tracking_number=str(tracking),
                    tracking_url=tracking_url,
                    label=LabelFile(format=str(fmt).lower() if fmt else r.label_format, data=label),
                )
            )
        return CanonicalLabelResult(shipment_number=str(first), parcels=parcels)
