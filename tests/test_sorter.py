"""Tests for the proposed-order builder."""

from __future__ import annotations

from spotify_playlist_sorter.camelot import to_camelot
from spotify_playlist_sorter.models import AudioFeatures, Track
from spotify_playlist_sorter.sorter import build_proposed_order


def _track(position, *, key=None, mode=None, tempo=0.0, title="t"):
    features = None
    if key is not None and mode is not None:
        features = AudioFeatures(
            key=key, mode=mode, tempo=tempo, camelot=to_camelot(key, mode)
        )
    return Track(
        spotify_id=f"id{position}",
        uri=f"spotify:track:id{position}",
        title=title,
        artists=("a",),
        position=position,
        features=features,
    )


def test_orders_by_camelot_then_bpm():
    tracks = [
        _track(0, key=9, mode=0, tempo=150.0),  # 8A 150
        _track(1, key=0, mode=1, tempo=120.0),  # 8B 120
        _track(2, key=9, mode=0, tempo=120.0),  # 8A 120
        _track(3, key=8, mode=0, tempo=90.0),  # 1A 90
    ]
    order = build_proposed_order(tracks)
    codes: list[tuple[str, float]] = []
    for track in order.sortable:
        assert track.features is not None
        codes.append((track.features.camelot.code, track.features.tempo))
    assert codes == [("1A", 90.0), ("8A", 120.0), ("8A", 150.0), ("8B", 120.0)]


def test_unsortable_grouped_last_in_original_order():
    tracks = [_track(0), _track(1, key=8, mode=0, tempo=100.0), _track(2)]
    order = build_proposed_order(tracks)
    assert [t.position for t in order.unsortable] == [0, 2]
    assert [t.position for t in order.ordered] == [1, 0, 2]


def test_multiset_preserved():
    tracks = [
        _track(0, key=1, mode=1, tempo=128.0),
        _track(1),
        _track(2, key=1, mode=1, tempo=128.0),
    ]
    order = build_proposed_order(tracks)
    assert sorted(t.position for t in order.ordered) == [0, 1, 2]


def test_stable_ties_keep_original_order():
    tracks = [
        _track(0, key=1, mode=1, tempo=128.0),
        _track(1, key=1, mode=1, tempo=128.0),
    ]
    order = build_proposed_order(tracks)
    assert [t.position for t in order.sortable] == [0, 1]


def test_all_unsortable_yields_empty_sortable():
    tracks = [_track(0), _track(1), _track(2)]
    order = build_proposed_order(tracks)
    assert order.sortable == ()
    assert [t.position for t in order.unsortable] == [0, 1, 2]
    assert [t.position for t in order.ordered] == [0, 1, 2]
