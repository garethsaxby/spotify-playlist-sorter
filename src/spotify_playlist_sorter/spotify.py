"""Typed Spotify Web API client and playlist-reference parsing."""

from __future__ import annotations

import re
import time
from typing import TYPE_CHECKING, cast

import httpx

from .models import NewPlaylist, SourcePlaylist, Track

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

_API_BASE = "https://api.spotify.com/v1"
_PAGE_LIMIT = 100
_ADD_BATCH = 100
_MAX_RETRIES = 5
_DEFAULT_BACKOFF_SECONDS = 2.0
_HTTP_TOO_MANY_REQUESTS = 429

_PLAYLIST_ID_RE = re.compile(r"^[A-Za-z0-9]{22}$")
_URL_RE = re.compile(r"open\.spotify\.com/playlist/([A-Za-z0-9]{22})")
_URI_RE = re.compile(r"^spotify:playlist:([A-Za-z0-9]{22})$")


class SpotifyError(RuntimeError):
    """A Spotify API interaction failed."""


def parse_playlist_id(reference: str) -> str:
    """Extract a playlist id from a URL, ``spotify:playlist:`` URI, or bare id.

    Raises ``ValueError`` for anything that is not a playlist reference.
    """
    text = reference.strip()
    for pattern in (_URI_RE, _URL_RE):
        match = pattern.search(text)
        if match:
            return match.group(1)
    if _PLAYLIST_ID_RE.match(text):
        return text
    raise ValueError(f"not a Spotify playlist reference: {reference!r}")


def _require(obj: object, key: str) -> object:
    if not isinstance(obj, dict):
        raise SpotifyError("unexpected response shape")
    mapping = cast("dict[str, object]", obj)
    if key not in mapping:
        available = ", ".join(sorted(str(k) for k in mapping))
        raise SpotifyError(f"missing field {key!r}; response had: [{available}]")
    return mapping[key]


def _as_str(obj: object) -> str:
    if not isinstance(obj, str):
        raise SpotifyError("expected a string field")
    return obj


class SpotifyClient:
    """Minimal Spotify client. ``access_token_provider`` returns a fresh token."""

    def __init__(
        self,
        access_token_provider: Callable[[], str],
        *,
        client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._token = access_token_provider
        self._client = client or httpx.Client(base_url=_API_BASE, timeout=30.0)
        self._sleep = sleep

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        json: dict[str, object] | None = None,
    ) -> httpx.Response:
        for attempt in range(_MAX_RETRIES):
            headers = {"Authorization": f"Bearer {self._token()}"}
            try:
                response = self._client.request(
                    method, path, params=params, json=json, headers=headers
                )
            except httpx.HTTPError as exc:
                raise SpotifyError(f"{method} {path}: {exc}") from exc
            if response.status_code == _HTTP_TOO_MANY_REQUESTS:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else _DEFAULT_BACKOFF_SECONDS
                if attempt < _MAX_RETRIES - 1:
                    self._sleep(delay)
                    continue
            if response.is_error:
                detail = response.text[:200]
                raise SpotifyError(
                    f"{method} {path} -> {response.status_code}: {detail}"
                )
            return response
        raise SpotifyError(f"{method} {path} rate-limited after retries")

    def current_user(self) -> tuple[str, str]:
        """Return ``(user_id, country)``; country is "" if unavailable."""
        data = self._request("GET", "/me").json()
        if not isinstance(data, dict):
            raise SpotifyError("unexpected /me response shape")
        mapping = cast("dict[str, object]", data)
        user_id = _as_str(_require(mapping, "id"))
        country = mapping.get("country")
        return user_id, country if isinstance(country, str) else ""

    def get_playlist(self, playlist_id: str, market: str = "") -> SourcePlaylist:
        """Read name/owner and all tracks for a playlist.

        Metadata comes from GET /playlists/{id} (fields-limited); the tracks come
        from the paginated GET /playlists/{id}/items — Spotify's preferred
        endpoint, whose ``next`` links stay on /items so playlists over 100 tracks
        page correctly (the deprecated /tracks endpoint returns 403 for new apps).
        """
        name, owner_id = self._get_meta(playlist_id, market)
        tracks = self._get_items(playlist_id, market)
        return SourcePlaylist(
            playlist_id=playlist_id, name=name, owner_id=owner_id, tracks=tracks
        )

    def _get_meta(self, playlist_id: str, market: str) -> tuple[str, str]:
        params = {"fields": "name,owner(id)"}
        if market:
            params["market"] = market
        data = self._request("GET", f"/playlists/{playlist_id}", params=params).json()
        if not isinstance(data, dict):
            raise SpotifyError("unexpected playlist response shape")
        mapping = cast("dict[str, object]", data)
        name = _as_str(_require(mapping, "name"))
        owner_id = _as_str(_require(_require(mapping, "owner"), "id"))
        return name, owner_id

    def _get_items(self, playlist_id: str, market: str) -> tuple[Track, ...]:
        params = {"limit": str(_PAGE_LIMIT), "offset": "0"}
        if market:
            params["market"] = market
        first = self._request(
            "GET", f"/playlists/{playlist_id}/items", params=params
        ).json()
        return self._collect_tracks(first)

    def _collect_tracks(self, first_page: object) -> tuple[Track, ...]:
        tracks: list[Track] = []
        page = first_page
        while True:
            items = _require(page, "items")
            if not isinstance(items, list):
                raise SpotifyError("playlist items not a list")
            for item in items:
                track = _parse_track(item, position=len(tracks))
                if track is not None:
                    tracks.append(track)
            next_url = _require(page, "next")
            if not isinstance(next_url, str):
                break
            page = self._request("GET", next_url).json()
        return tuple(tracks)

    def create_playlist(self, name: str, *, public: bool = False) -> NewPlaylist:
        # POST /me/playlists (the /users/{id}/playlists form is deprecated -> 403).
        body: dict[str, object] = {"name": name, "public": public}
        data = self._request("POST", "/me/playlists", json=body).json()
        new_id = _as_str(_require(data, "id"))
        urls = _require(data, "external_urls")
        url = _as_str(_require(urls, "spotify"))
        return NewPlaylist(playlist_id=new_id, name=name, url=url)

    def add_tracks(self, playlist_id: str, uris: Sequence[str]) -> None:
        # POST /playlists/{id}/items (the /tracks form is deprecated).
        for start in range(0, len(uris), _ADD_BATCH):
            batch = list(uris[start : start + _ADD_BATCH])
            self._request(
                "POST", f"/playlists/{playlist_id}/items", json={"uris": batch}
            )

    def close(self) -> None:
        self._client.close()


def _parse_track(item: object, *, position: int) -> Track | None:
    if not isinstance(item, dict):
        return None
    # Spotify deprecated the per-item "track" field in favour of "item"; newer
    # apps get a null "track", so prefer "item".
    track_obj = item.get("item")
    if not isinstance(track_obj, dict):
        track_obj = item.get("track")
    if not isinstance(track_obj, dict):
        return None
    track_id = track_obj.get("id")
    uri = track_obj.get("uri")
    if not isinstance(track_id, str) or not isinstance(uri, str):
        return None
    name = track_obj.get("name")
    title = name if isinstance(name, str) else "(unknown)"
    artists = _parse_artists(track_obj.get("artists"))
    return Track(
        spotify_id=track_id,
        uri=uri,
        title=title,
        artists=artists,
        position=position,
    )


def _parse_artists(obj: object) -> tuple[str, ...]:
    if not isinstance(obj, list):
        return ()
    names: list[str] = []
    for artist in obj:
        if isinstance(artist, dict):
            name = artist.get("name")
            if isinstance(name, str):
                names.append(name)
    return tuple(names)
