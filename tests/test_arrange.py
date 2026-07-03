"""Tests for the pure editor logic: build, pin-aware rebuild, reconcile, move."""

from __future__ import annotations

import pytest

from spotify_playlist_sorter.arrange import (
    full_resort,
    move_track,
    parse_edit,
    rebuild,
    reconcile,
    to_editable_tracks,
)
from spotify_playlist_sorter.camelot import to_camelot
from spotify_playlist_sorter.models import (
    Arrangement,
    AudioFeatures,
    Correction,
    EditableTrack,
    Track,
)


def _track(index):
    return Track(
        spotify_id=f"id{index}",
        uri=f"spotify:track:id{index}",
        title=f"t{index}",
        artists=("a",),
        position=index,
    )


def _feat(key, mode, tempo):
    return AudioFeatures(key=key, mode=mode, tempo=tempo, camelot=to_camelot(key, mode))


def _editable(name, *, key=None, mode=None, tempo=None, pinned=False):
    has_data = key is not None and mode is not None and tempo is not None
    return EditableTrack(
        spotify_id=name,
        uri=f"spotify:track:{name}",
        title=name,
        artists=("a",),
        source_position=0,
        camelot=to_camelot(key, mode) if has_data else None,
        bpm=tempo,
        provenance="estimated" if has_data else "unknown",
        pinned=pinned,
    )


# Four sortable tracks whose Camelot→BPM order is a, b, c, d.
def _abcd():
    return {
        "a": _editable("a", key=8, mode=0, tempo=90.0),  # 1A 90
        "b": _editable("b", key=9, mode=0, tempo=120.0),  # 8A 120
        "c": _editable("c", key=9, mode=0, tempo=150.0),  # 8A 150
        "d": _editable("d", key=0, mode=1, tempo=120.0),  # 8B 120
    }


def _ids(tracks):
    return [track.spotify_id for track in tracks]


# --- rebuild ---------------------------------------------------------------


def test_rebuild_sorts_non_pinned_camelot_then_bpm():
    tracks = _abcd()
    scrambled = [tracks["d"], tracks["a"], tracks["c"], tracks["b"]]
    assert _ids(rebuild(scrambled)) == ["a", "b", "c", "d"]


def test_rebuild_places_unsortable_last():
    unknown = _editable("z")
    tracks = _abcd()
    result = rebuild([unknown, tracks["b"], tracks["a"]])
    assert _ids(result) == ["a", "b", "z"]


def test_rebuild_honours_pins_at_absolute_index():
    tracks = _abcd()
    pinned_d = _editable("d", key=0, mode=1, tempo=120.0, pinned=True)
    result = rebuild([pinned_d, tracks["a"], tracks["b"], tracks["c"]])
    assert result[0].spotify_id == "d"
    assert result[0].pinned
    assert _ids(result[1:]) == ["a", "b", "c"]


def test_rebuild_preserves_multiset():
    tracks = list(_abcd().values())
    assert sorted(_ids(rebuild(tracks))) == ["a", "b", "c", "d"]


def test_rebuild_is_idempotent():
    tracks = list(_abcd().values())
    once = rebuild(tracks)
    twice = rebuild(once)
    assert [(t.spotify_id, t.pinned) for t in once] == [
        (t.spotify_id, t.pinned) for t in twice
    ]


def test_rebuild_scales_to_200_tracks_preserving_multiset():
    tracks = [
        _editable(f"t{i}", key=i % 12, mode=i % 2, tempo=90.0 + i) for i in range(200)
    ]
    result = rebuild(tracks)
    assert len(result) == 200
    assert {t.spotify_id for t in result} == {t.spotify_id for t in tracks}


# --- to_editable_tracks ----------------------------------------------------


def test_to_editable_tracks_precedence_correction_over_estimate():
    tracks = [_track(0), _track(1), _track(2)]
    estimates = {"id0": _feat(0, 1, 120.0), "id1": _feat(8, 0, 90.0)}
    corrections = {"id0": Correction(camelot=to_camelot(6, 1), bpm=122.0)}  # 2B
    result = to_editable_tracks(tracks, estimates, corrections)
    by_id = {t.spotify_id: t for t in result}
    assert by_id["id0"].provenance == "corrected"
    assert by_id["id0"].camelot is not None
    assert by_id["id0"].camelot.code == "2B"
    assert by_id["id1"].provenance == "estimated"
    assert by_id["id2"].provenance == "unknown"
    assert by_id["id2"].camelot is None


def test_to_editable_tracks_all_unknown_when_no_estimates():
    tracks = [_track(0), _track(1)]
    result = to_editable_tracks(tracks, {})
    assert all(t.provenance == "unknown" for t in result)
    assert all(t.camelot is None and t.bpm is None for t in result)


# --- parse_edit ------------------------------------------------------------


def test_parse_edit_accepts_valid_input():
    camelot, bpm = parse_edit("8b", "122.5")
    assert camelot.code == "8B"
    assert bpm == 122.5


@pytest.mark.parametrize(
    ("camelot_text", "bpm_text"),
    [("13Z", "120"), ("8B", "0"), ("8B", "-5"), ("8B", "abc")],
)
def test_parse_edit_rejects_invalid(camelot_text, bpm_text):
    with pytest.raises(ValueError, match=r"Camelot|BPM"):
        parse_edit(camelot_text, bpm_text)


# --- reconcile -------------------------------------------------------------


def test_reconcile_without_arrangement_is_a_plain_rebuild():
    tracks = [_track(0), _track(1)]
    estimates = {"id0": _feat(0, 1, 120.0), "id1": _feat(8, 0, 90.0)}
    result = reconcile(tracks, None, estimates=estimates)
    assert _ids(result) == ["id1", "id0"]  # 1A before 8B


def test_reconcile_keeps_pins_drops_removed_appends_new():
    current = [_track(0), _track(2), _track(3)]  # id1 removed, id3 added
    estimates = {
        "id0": _feat(0, 1, 120.0),
        "id2": _feat(9, 0, 120.0),
        "id3": _feat(8, 0, 90.0),
    }
    saved = Arrangement(
        version=1,
        playlist_id="p",
        order=("id0", "id1", "id2"),
        pinned=(0,),  # id0 pinned at position 0
    )
    result = reconcile(current, saved, estimates=estimates)
    ids = _ids(result)
    assert result[0].spotify_id == "id0"
    assert result[0].pinned
    assert "id1" not in ids
    assert "id3" in ids
    assert set(ids) == {"id0", "id2", "id3"}


def test_reconcile_applies_corrections():
    current = [_track(0)]
    corrections = {"id0": Correction(camelot=to_camelot(6, 1), bpm=122.0)}  # 2B
    result = reconcile(current, None, corrections=corrections)
    assert result[0].provenance == "corrected"
    assert result[0].camelot is not None
    assert result[0].camelot.code == "2B"


def test_reconcile_matches_duplicate_occurrences_positionally():
    current = [_track(0), _track(0)]  # same id twice
    estimates = {"id0": _feat(0, 1, 120.0)}
    saved = Arrangement(version=1, playlist_id="p", order=("id0", "id0"), pinned=(1,))
    result = reconcile(current, saved, estimates=estimates)
    assert len(result) == 2
    assert sum(1 for t in result if t.pinned) == 1


# --- move / full_resort ----------------------------------------------------


def test_move_track_pins_at_target_and_holds_through_rebuild():
    tracks = [_abcd()[name] for name in ("a", "b", "c", "d")]
    moved = move_track(tracks, index=3, target=1)  # d to position 1
    assert moved[1].spotify_id == "d"
    assert moved[1].pinned
    rebuilt = rebuild(moved)
    assert rebuilt[1].spotify_id == "d"
    assert rebuilt[1].pinned


def test_full_resort_clears_pins_and_sorts():
    tracks = _abcd()
    pinned_d = _editable("d", key=0, mode=1, tempo=120.0, pinned=True)
    arranged = [pinned_d, tracks["a"], tracks["b"], tracks["c"]]
    result = full_resort(arranged)
    assert not any(t.pinned for t in result)
    assert _ids(result) == ["a", "b", "c", "d"]
