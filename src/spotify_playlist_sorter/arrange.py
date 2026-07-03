"""Pure editor logic: build editable tracks, pin-aware ordering, drift reconcile.

Correctness-critical and fully unit-tested without launching the TUI. Reuses the
Camelot-then-BPM ordering from ``sorter`` rather than re-implementing it (research D3).
"""

from __future__ import annotations

from collections import deque
from dataclasses import replace
from typing import TYPE_CHECKING

from . import sorter
from .camelot import parse_camelot
from .models import EditableTrack

if TYPE_CHECKING:
    from .models import (
        Arrangement,
        AudioFeatures,
        CamelotKey,
        Correction,
        Provenance,
        Track,
    )


def to_editable_tracks(
    tracks: list[Track],
    estimates: dict[str, AudioFeatures],
    corrections: dict[str, Correction] | None = None,
) -> list[EditableTrack]:
    """Resolve each track's key/BPM by precedence: correction → estimate → unknown.

    ``estimates`` is passed explicitly (Spotify tracks arrive without harmonic data;
    it is fetched separately), so an empty ``estimates`` yields all-``unknown`` tracks.
    """
    corrections = corrections or {}
    result: list[EditableTrack] = []
    for track in tracks:
        correction = corrections.get(track.spotify_id)
        estimate = estimates.get(track.spotify_id)
        camelot: CamelotKey | None
        bpm: float | None
        provenance: Provenance
        if correction is not None:
            camelot, bpm, provenance = correction.camelot, correction.bpm, "corrected"
        elif estimate is not None:
            camelot, bpm, provenance = estimate.camelot, estimate.tempo, "estimated"
        else:
            camelot, bpm, provenance = None, None, "unknown"
        result.append(
            EditableTrack(
                spotify_id=track.spotify_id,
                uri=track.uri,
                title=track.title,
                artists=track.artists,
                source_position=track.position,
                camelot=camelot,
                bpm=bpm,
                provenance=provenance,
                pinned=False,
            )
        )
    return result


def parse_edit(camelot_text: str, bpm_text: str) -> tuple[CamelotKey, float]:
    """Validate an edit: a Camelot code (1A-12B) and a positive BPM.

    Raises ``ValueError`` with a message for invalid input; stores nothing (FR-005).
    """
    camelot = parse_camelot(camelot_text)
    try:
        bpm = float(bpm_text.strip())
    except ValueError as exc:
        msg = f"BPM must be a number: {bpm_text!r}"
        raise ValueError(msg) from exc
    if bpm <= 0:
        msg = f"BPM must be positive: {bpm_text!r}"
        raise ValueError(msg)
    return camelot, bpm


def _key(track: EditableTrack) -> tuple[int, int, float, int]:
    camelot = track.camelot
    bpm = track.bpm
    if camelot is None or bpm is None:  # pragma: no cover - only sortable are keyed
        msg = "unsortable track cannot be ordered"
        raise ValueError(msg)
    return sorter.sort_key(camelot, bpm, track.source_position)


def rebuild(tracks: list[EditableTrack]) -> list[EditableTrack]:
    """Re-place non-pinned tracks by Camelot→BPM (unsortable last); pins stay put.

    A pinned track keeps its absolute index; the remaining slots are filled, in order,
    by the sorted sortable tracks followed by the unsortable ones (data-model.md).
    """
    free = [track for track in tracks if not track.pinned]
    sortable = [track for track in free if track.sortable]
    unsortable = [track for track in free if not track.sortable]
    ordered_free = iter(sorted(sortable, key=_key) + unsortable)
    return [track if track.pinned else next(ordered_free) for track in tracks]


def reconcile(
    current_tracks: list[Track],
    arrangement: Arrangement | None,
    corrections: dict[str, Correction] | None = None,
    estimates: dict[str, AudioFeatures] | None = None,
) -> list[EditableTrack]:
    """Merge a saved arrangement with the current tracks (playlist drift, FR-013).

    Surviving occurrences keep the saved order and their pins (matched positionally by
    id for duplicates); removed ids drop; newly-added tracks are appended non-pinned and
    slotted into place by ``rebuild``. Corrections apply throughout (global reuse).
    """
    editables = to_editable_tracks(current_tracks, estimates or {}, corrections)
    if arrangement is None:
        return rebuild(editables)
    buckets: dict[str, deque[EditableTrack]] = {}
    for editable in editables:
        buckets.setdefault(editable.spotify_id, deque()).append(editable)
    pinned_positions = set(arrangement.pinned)
    ordered: list[EditableTrack] = []
    for position, track_id in enumerate(arrangement.order):
        bucket = buckets.get(track_id)
        if not bucket:
            continue
        editable = bucket.popleft()
        if position in pinned_positions:
            editable = replace(editable, pinned=True)
        ordered.append(editable)
    for bucket in buckets.values():
        ordered.extend(bucket)
    return rebuild(ordered)


def move_track(
    tracks: list[EditableTrack], index: int, target: int
) -> list[EditableTrack]:
    """Move the track at ``index`` to ``target`` and pin it there (FR-012).

    A move does not re-sort; the moved track becomes a fixed pin at its new position.
    """
    result = list(tracks)
    moved = replace(result.pop(index), pinned=True)
    result.insert(target, moved)
    return result


def full_resort(tracks: list[EditableTrack]) -> list[EditableTrack]:
    """Clear all pins and re-order purely by Camelot→BPM (FR-006/FR-027)."""
    return rebuild([replace(track, pinned=False) for track in tracks])
