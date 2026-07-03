"""ReccoBeats audio-features client (no auth) and response parsing."""

from __future__ import annotations

import re
import time
from typing import TYPE_CHECKING

import httpx

from .camelot import to_camelot
from .models import AudioFeatures

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

_API = "https://api.reccobeats.com/v1"
_BATCH = 40
_MAX_RETRIES = 5
_DEFAULT_BACKOFF_SECONDS = 2.0
_HTTP_TOO_MANY_REQUESTS = 429
_HREF_RE = re.compile(r"/track/([A-Za-z0-9]{22})")


class ReccoBeatsError(RuntimeError):
    """A ReccoBeats interaction failed."""


def _spotify_id_from_href(href: object) -> str | None:
    if not isinstance(href, str):
        return None
    match = _HREF_RE.search(href)
    return match.group(1) if match else None


def _features_from_entry(entry: object) -> AudioFeatures | None:
    if not isinstance(entry, dict):
        return None
    key = entry.get("key")
    mode = entry.get("mode")
    tempo = entry.get("tempo")
    if not isinstance(key, int) or not isinstance(mode, int):
        return None
    if not isinstance(tempo, int | float) or tempo <= 0:
        return None
    try:
        camelot = to_camelot(key, mode)
    except ValueError:
        return None
    return AudioFeatures(key=key, mode=mode, tempo=float(tempo), camelot=camelot)


def _parse_entry(entry: object) -> tuple[str, AudioFeatures] | None:
    if not isinstance(entry, dict):
        return None
    spotify_id = _spotify_id_from_href(entry.get("href"))
    if spotify_id is None:
        return None
    features = _features_from_entry(entry)
    if features is None:
        return None
    return spotify_id, features


def parse_audio_features(payload: object) -> dict[str, AudioFeatures]:
    """Map Spotify id -> features from a ReccoBeats ``content[]`` payload.

    Unmatched or invalid entries are omitted (the caller treats absent tracks as
    unsortable).
    """
    if not isinstance(payload, dict):
        return {}
    content = payload.get("content")
    if not isinstance(content, list):
        return {}
    result: dict[str, AudioFeatures] = {}
    for entry in content:
        parsed = _parse_entry(entry)
        if parsed is not None:
            result[parsed[0]] = parsed[1]
    return result


class ReccoBeatsClient:
    """Fetches audio features for Spotify track ids in batches of 40."""

    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._client = client or httpx.Client(base_url=_API, timeout=30.0)
        self._sleep = sleep

    def fetch_features(self, spotify_ids: Sequence[str]) -> dict[str, AudioFeatures]:
        features: dict[str, AudioFeatures] = {}
        for start in range(0, len(spotify_ids), _BATCH):
            batch = list(spotify_ids[start : start + _BATCH])
            features.update(parse_audio_features(self._get(batch)))
        return features

    def _get(self, ids: list[str]) -> object:
        for attempt in range(_MAX_RETRIES):
            try:
                response = self._client.get(
                    "/audio-features", params={"ids": ",".join(ids)}
                )
            except httpx.HTTPError as exc:
                raise ReccoBeatsError(f"audio-features: {exc}") from exc
            if response.status_code == _HTTP_TOO_MANY_REQUESTS:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else _DEFAULT_BACKOFF_SECONDS
                if attempt < _MAX_RETRIES - 1:
                    self._sleep(delay)
                    continue
            if response.is_error:
                detail = response.text[:200]
                raise ReccoBeatsError(
                    f"audio-features -> {response.status_code}: {detail}"
                )
            return response.json()
        raise ReccoBeatsError("audio-features rate-limited after retries")

    def close(self) -> None:
        self._client.close()
