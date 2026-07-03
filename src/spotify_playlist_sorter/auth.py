"""Spotify OAuth (Authorization Code + PKCE) and refresh-token cache."""

from __future__ import annotations

import base64
import hashlib
import http.server
import json
import os
import secrets
import time
import urllib.parse
import webbrowser
from typing import ClassVar

import httpx

from . import config
from .models import AuthToken

_AUTHORIZE_URL = "https://accounts.spotify.com/authorize"
_TOKEN_URL = "https://accounts.spotify.com/api/token"  # noqa: S105 - endpoint, not a secret
_EXPIRY_MARGIN_SECONDS = 30.0
_HTTP_OK = 200
_HTTP_NOT_FOUND = 404
_TOKEN_FILE_MODE = 0o600
_STATE_BYTES = 16
_VERIFIER_BYTES = 64


class AuthError(RuntimeError):
    """Authentication failed."""


def _pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(_VERIFIER_BYTES)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


def _authorize_url(client_id: str, challenge: str, state: str) -> str:
    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": config.REDIRECT_URI,
        "scope": " ".join(config.SCOPES),
        "code_challenge_method": "S256",
        "code_challenge": challenge,
        "state": state,
        # Force the consent screen so the current scopes are always granted
        # (Spotify otherwise silently reuses a prior, possibly narrower, grant).
        "show_dialog": "true",
    }
    query = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    return f"{_AUTHORIZE_URL}?{query}"


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    result: ClassVar[dict[str, str]] = {}

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != config.REDIRECT_PATH:
            self.send_response(_HTTP_NOT_FOUND)
            self.end_headers()
            return
        query = urllib.parse.parse_qs(parsed.query)
        _CallbackHandler.result = {key: values[0] for key, values in query.items()}
        self.send_response(_HTTP_OK)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(
            b"Authorized. You can close this tab and return to the terminal."
        )

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002, ARG002
        return


def _await_callback(expected_state: str) -> str:
    server = http.server.HTTPServer(
        (config.REDIRECT_HOST, config.REDIRECT_PORT), _CallbackHandler
    )
    _CallbackHandler.result = {}
    try:
        while not _CallbackHandler.result:
            server.handle_request()
    finally:
        server.server_close()
    result = _CallbackHandler.result
    if result.get("state") != expected_state:
        raise AuthError("OAuth state mismatch")
    code = result.get("code")
    if not code:
        raise AuthError(f"authorization failed: {result.get('error', 'no code')}")
    return code


def _post_token(data: dict[str, str]) -> tuple[AuthToken, str]:
    try:
        response = httpx.post(_TOKEN_URL, data=data, timeout=30.0)
    except httpx.HTTPError as exc:
        raise AuthError(f"token request failed: {exc}") from exc
    if response.is_error:
        raise AuthError(
            f"token endpoint -> {response.status_code}: {response.text[:200]}"
        )
    payload = response.json()
    if not isinstance(payload, dict):
        raise AuthError("unexpected token response")
    access = payload.get("access_token")
    expires_in = payload.get("expires_in")
    if not isinstance(access, str) or not isinstance(expires_in, int | float):
        raise AuthError("malformed token response")
    refresh = payload.get("refresh_token")
    refresh_token = (
        refresh if isinstance(refresh, str) else data.get("refresh_token", "")
    )
    granted = payload.get("scope")
    scope_str = granted if isinstance(granted, str) else ""
    token = AuthToken(
        access_token=access,
        refresh_token=refresh_token,
        expires_at=time.time() + float(expires_in),
    )
    return token, scope_str


def _save_refresh_token(refresh_token: str, client_id: str) -> None:
    path = config.token_file()
    payload = json.dumps({"refresh_token": refresh_token, "client_id": client_id})
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, _TOKEN_FILE_MODE)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(payload)


def _load_cached() -> tuple[str, str] | None:
    path = config.token_file()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError, json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    refresh = data.get("refresh_token")
    client = data.get("client_id")
    if isinstance(refresh, str) and isinstance(client, str):
        return refresh, client
    return None


def login(client_id: str) -> str:
    """Run the full PKCE flow, cache the refresh token, return granted scopes."""
    verifier, challenge = _pkce_pair()
    state = secrets.token_urlsafe(_STATE_BYTES)
    webbrowser.open(_authorize_url(client_id, challenge, state))
    code = _await_callback(state)
    token, granted = _post_token(
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": config.REDIRECT_URI,
            "client_id": client_id,
            "code_verifier": verifier,
        }
    )
    _save_refresh_token(token.refresh_token, client_id)
    return granted


class Session:
    """Holds a refresh token and lazily provides a fresh access token."""

    def __init__(self, client_id: str, refresh_token: str) -> None:
        self._client_id = client_id
        self._refresh_token = refresh_token
        self._access_token = ""
        self._expires_at = 0.0

    def access_token(self) -> str:
        if (
            not self._access_token
            or time.time() >= self._expires_at - _EXPIRY_MARGIN_SECONDS
        ):
            self._refresh()
        return self._access_token

    def _refresh(self) -> None:
        token, _ = _post_token(
            {
                "grant_type": "refresh_token",
                "refresh_token": self._refresh_token,
                "client_id": self._client_id,
            }
        )
        self._access_token = token.access_token
        self._expires_at = token.expires_at
        # Spotify PKCE rotates the refresh token each refresh; persist the new one
        # so the next run doesn't try to reuse an invalidated token.
        if token.refresh_token and token.refresh_token != self._refresh_token:
            self._refresh_token = token.refresh_token
            _save_refresh_token(self._refresh_token, self._client_id)


def load_session() -> Session | None:
    """Return a Session from the cached token, or None if not logged in."""
    cached = _load_cached()
    if cached is None:
        return None
    refresh, client_id = cached
    return Session(client_id=client_id, refresh_token=refresh)
