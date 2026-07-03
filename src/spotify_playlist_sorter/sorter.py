"""Build the proposed Camelot-then-BPM order from a list of tracks."""

from __future__ import annotations

from .models import ProposedOrder, Track


def _sort_key(track: Track) -> tuple[int, int, float, int]:
    features = track.features
    if features is None:  # pragma: no cover - guarded by caller
        msg = "sortable track must have features"
        raise ValueError(msg)
    return (*features.camelot.order, features.tempo, track.position)


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
