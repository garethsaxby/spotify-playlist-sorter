"""Configuration: paths, OAuth scopes, and the loopback redirect."""

from __future__ import annotations

import os
from pathlib import Path

import platformdirs

APP_NAME = "spotify-playlist-sorter"

SCOPES = (
    "playlist-read-private",
    "playlist-read-collaborative",
    "playlist-modify-public",
    "playlist-modify-private",
    "user-read-private",  # gives the token a country so playlist tracks aren't nulled
)

# Fixed loopback redirect; MUST match the URI registered in the Spotify app.
REDIRECT_HOST = "127.0.0.1"
REDIRECT_PORT = 8080
REDIRECT_PATH = "/callback"
REDIRECT_URI = f"http://{REDIRECT_HOST}:{REDIRECT_PORT}{REDIRECT_PATH}"

_CLIENT_ID_ENV = "SPOTIFY_CLIENT_ID"


def config_dir() -> Path:
    """Return (creating if needed) the per-user config directory."""
    path = Path(platformdirs.user_config_dir(APP_NAME))
    path.mkdir(parents=True, exist_ok=True)
    return path


def token_file() -> Path:
    """Path to the cached-token file (created 0600 by the writer)."""
    return config_dir() / "token.json"


def client_id() -> str:
    """Return the Spotify client id from the environment, or raise."""
    value = os.environ.get(_CLIENT_ID_ENV)
    if not value:
        msg = f"{_CLIENT_ID_ENV} is not set"
        raise ValueError(msg)
    return value
