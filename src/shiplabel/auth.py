"""Auth helpers with a shared, thread-safe token cache.

- OAuth2 Resource-Owner-Password grant (DHL Paket, Hermes)
- OAuth2 client_credentials grant (UPS, FedEx, ...)

HTTP-Basic is done inline in each mapper via ``httpx.BasicAuth``.
"""

from __future__ import annotations

import threading
import time

import httpx

from .errors import AuthError

_cache: dict[str, tuple[str, float]] = {}  # key -> (token, expires_at_epoch)
_lock = threading.Lock()


def _cached(cache_key: str) -> str | None:
    with _lock:
        entry = _cache.get(cache_key)
        # 30s skew guard so a token never expires mid-flight.
        if entry and entry[1] > time.time() + 30:
            return entry[0]
    return None


def _store(cache_key: str, token: str, ttl: int) -> None:
    with _lock:
        _cache[cache_key] = (token, time.time() + ttl)


def get_password_grant_token(
    *,
    token_url: str,
    client_id: str,
    client_secret: str,
    username: str,
    password: str,
    client: httpx.Client,
    cache_key: str,
    ttl_fallback: int = 1700,
) -> str:
    """OAuth2 Resource-Owner-Password grant (DHL Paket pattern)."""
    if (tok := _cached(cache_key)) is not None:
        return tok
    resp = client.post(
        token_url,
        data={
            "grant_type": "password",
            "client_id": client_id,
            "client_secret": client_secret,
            "username": username,
            "password": password,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if resp.status_code in (401, 403):
        raise AuthError(f"token endpoint rejected credentials ({resp.status_code})")
    resp.raise_for_status()
    body = resp.json()
    token = body["access_token"]
    _store(cache_key, token, int(body.get("expires_in", ttl_fallback)))
    return token


def get_client_credentials_token(
    *,
    token_url: str,
    client_id: str,
    client_secret: str,
    client: httpx.Client,
    cache_key: str,
    scope: str | None = None,
    audience: str | None = None,
    use_basic_header: bool = False,
    ttl_fallback: int = 3000,
) -> str:
    """OAuth2 client_credentials grant (UPS, FedEx, ...)."""
    if (tok := _cached(cache_key)) is not None:
        return tok
    data: dict[str, str] = {"grant_type": "client_credentials"}
    if scope:
        data["scope"] = scope
    if audience:
        data["audience"] = audience
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    auth = None
    if use_basic_header:
        auth = httpx.BasicAuth(client_id, client_secret)
    else:
        data["client_id"] = client_id
        data["client_secret"] = client_secret
    resp = client.post(token_url, data=data, headers=headers, auth=auth)
    if resp.status_code in (401, 403):
        raise AuthError(f"token endpoint rejected credentials ({resp.status_code})")
    resp.raise_for_status()
    body = resp.json()
    token = body["access_token"]
    _store(cache_key, token, int(body.get("expires_in", ttl_fallback)))
    return token
