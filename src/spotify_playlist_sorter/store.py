"""Local JSON persistence for corrections (global) and arrangements (per playlist).

Both stores are versioned and written atomically (temp file + ``os.replace``), so an
interrupted save never corrupts the previous file (FR-011/FR-018). An unreadable or
wrong-version file is set aside and treated as empty, with a warning (FR-019/FR-021).
"""

from __future__ import annotations

import contextlib
import json
from typing import TYPE_CHECKING, cast

from . import config
from .camelot import parse_camelot
from .models import Arrangement, Correction

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from .models import EditableTrack

_VERSION = 1

# A callback that surfaces a non-fatal store warning (e.g. to the terminal).
type WarnFn = Callable[[str], None]


def _atomic_write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    try:
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp.replace(path)
    finally:
        if tmp.exists():  # pragma: no cover - only on a mid-write failure
            tmp.unlink()


def _set_aside(path: Path, reason: str, on_warning: WarnFn | None) -> None:
    backup = path.with_name(path.name + ".corrupt")
    with contextlib.suppress(OSError):  # best-effort preservation
        path.replace(backup)
    if on_warning is not None:
        on_warning(
            f"{path.name} {reason}; starting fresh "
            f"(previous file kept as {backup.name})."
        )


def _read_versioned(path: Path, on_warning: WarnFn | None) -> dict[str, object] | None:
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError, json.JSONDecodeError:
        _set_aside(path, "could not be read", on_warning)
        return None
    if not isinstance(raw, dict):
        _set_aside(path, "has an unexpected format", on_warning)
        return None
    data = cast("dict[str, object]", raw)
    if data.get("version") != _VERSION:
        _set_aside(path, "has an unrecognised version", on_warning)
        return None
    return data


def _parse_correction(value: object) -> Correction | None:
    if not isinstance(value, dict):
        return None
    mapping = cast("dict[str, object]", value)
    camelot_raw = mapping.get("camelot")
    bpm_raw = mapping.get("bpm")
    if not isinstance(camelot_raw, str):
        return None
    if not isinstance(bpm_raw, int | float) or isinstance(bpm_raw, bool):
        return None
    if bpm_raw <= 0:
        return None
    try:
        camelot = parse_camelot(camelot_raw)
    except ValueError:
        return None
    return Correction(camelot=camelot, bpm=float(bpm_raw))


def load_corrections(on_warning: WarnFn | None = None) -> dict[str, Correction]:
    """Load the global corrections store; malformed entries are skipped (FR-019)."""
    data = _read_versioned(config.corrections_file(), on_warning)
    if data is None:
        return {}
    entries = data.get("corrections")
    if not isinstance(entries, dict):
        return {}
    result: dict[str, Correction] = {}
    for key, value in cast("dict[object, object]", entries).items():
        correction = _parse_correction(value)
        if isinstance(key, str) and correction is not None:
            result[key] = correction
    return result


def save_corrections(corrections: dict[str, Correction]) -> None:
    """Atomically write the global corrections store (FR-018)."""
    payload: dict[str, object] = {
        "version": _VERSION,
        "corrections": {
            track_id: {"camelot": correction.camelot.code, "bpm": correction.bpm}
            for track_id, correction in corrections.items()
        },
    }
    _atomic_write_json(config.corrections_file(), payload)


def _string_tuple(value: object) -> tuple[str, ...] | None:
    if not isinstance(value, list):
        return None
    items = cast("list[object]", value)
    if not all(isinstance(item, str) for item in items):
        return None
    return tuple(cast("list[str]", items))


def _int_tuple(value: object) -> tuple[int, ...]:
    if not isinstance(value, list):
        return ()
    items = cast("list[object]", value)
    return tuple(
        item for item in items if isinstance(item, int) and not isinstance(item, bool)
    )


def load_arrangement(
    playlist_id: str, on_warning: WarnFn | None = None
) -> Arrangement | None:
    """Load a playlist's saved arrangement, or ``None`` if absent/unreadable."""
    data = _read_versioned(config.arrangement_file(playlist_id), on_warning)
    if data is None:
        return None
    order = _string_tuple(data.get("order"))
    if order is None:
        return None
    return Arrangement(
        version=_VERSION,
        playlist_id=playlist_id,
        order=order,
        pinned=_int_tuple(data.get("pinned")),
    )


def save_arrangement(arrangement: Arrangement) -> None:
    """Atomically write one playlist's arrangement (FR-018)."""
    payload: dict[str, object] = {
        "version": _VERSION,
        "playlist_id": arrangement.playlist_id,
        "order": list(arrangement.order),
        "pinned": list(arrangement.pinned),
    }
    _atomic_write_json(config.arrangement_file(arrangement.playlist_id), payload)


def arrangement_from_tracks(
    playlist_id: str, tracks: list[EditableTrack]
) -> Arrangement:
    """Build an ``Arrangement`` (order + pinned positions) from editor state."""
    return Arrangement(
        version=_VERSION,
        playlist_id=playlist_id,
        order=tuple(track.spotify_id for track in tracks),
        pinned=tuple(index for index, track in enumerate(tracks) if track.pinned),
    )


def corrections_from_tracks(tracks: list[EditableTrack]) -> dict[str, Correction]:
    """Extract the user-corrected tracks as global corrections (keyed by id)."""
    result: dict[str, Correction] = {}
    for track in tracks:
        if (
            track.provenance == "corrected"
            and track.camelot is not None
            and track.bpm is not None
        ):
            result[track.spotify_id] = Correction(camelot=track.camelot, bpm=track.bpm)
    return result
