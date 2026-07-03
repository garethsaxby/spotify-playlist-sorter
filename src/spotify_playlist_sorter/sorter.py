"""Build the proposed Camelot-then-BPM order from a list of tracks."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .models import ProposedOrder, Track

if TYPE_CHECKING:
    from .models import CamelotKey


def sort_key(
    camelot: CamelotKey, tempo: float, position: int
) -> tuple[int, int, float, int]:
    """Camelot-then-BPM ordering key; reused by ``arrange`` (feature 003)."""
    return (*camelot.order, tempo, position)


def _sort_key(track: Track) -> tuple[int, int, float, int]:
    features = track.features
    if features is None:  # pragma: no cover - guarded by caller
        msg = "sortable track must have features"
        raise ValueError(msg)
    return sort_key(features.camelot, features.tempo, track.position)


def build_proposed_order(tracks: list[Track]) -> ProposedOrder:
    """Order sortable tracks by Camelot then BPM; append unsortable ones last.

    A track is sortable iff it has ``features``. Sorting is stable, so ties
    (same Camelot Key and BPM) and the unsortable group keep their original
    relative order. The output multiset equals the input (FR-010).
    """
    sortable = [track for track in tracks if track.features is not None]
    unsortable = [track for track in tracks if track.features is None]
    ordered_sortable = sorted(sortable, key=_sort_key)
    return ProposedOrder(
        sortable=tuple(ordered_sortable),
        unsortable=tuple(unsortable),
    )
