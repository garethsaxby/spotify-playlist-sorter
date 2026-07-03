"""Tests for local JSON persistence: round-trip, atomic write, corrupt handling."""

from __future__ import annotations

import json

import pytest

from spotify_playlist_sorter import config, store
from spotify_playlist_sorter.camelot import to_camelot
from spotify_playlist_sorter.models import Arrangement, Correction, EditableTrack


@pytest.fixture(autouse=True)
def _store_dir(tmp_path, monkeypatch):
    """Redirect the config directory to a temp dir for every test in this module."""
    monkeypatch.setattr(config, "config_dir", lambda: tmp_path)


def test_corrections_round_trip():
    corrections = {"id0": Correction(camelot=to_camelot(6, 1), bpm=122.0)}  # 2B
    store.save_corrections(corrections)
    loaded = store.load_corrections()
    assert loaded["id0"].camelot.code == "2B"
    assert loaded["id0"].bpm == 122.0


def test_arrangement_round_trip():
    arrangement = Arrangement(
        version=1, playlist_id="p1", order=("a", "b", "a"), pinned=(2,)
    )
    store.save_arrangement(arrangement)
    loaded = store.load_arrangement("p1")
    assert loaded is not None
    assert loaded.order == ("a", "b", "a")
    assert loaded.pinned == (2,)


def test_missing_stores_start_fresh():
    assert store.load_corrections() == {}
    assert store.load_arrangement("nope") is None


def test_corrections_are_global_across_playlists():
    store.save_corrections({"shared": Correction(camelot=to_camelot(8, 0), bpm=100.0)})
    # There is one global store, so any playlist's load sees the same corrections.
    assert "shared" in store.load_corrections()


def test_malformed_correction_entries_are_skipped():
    config.corrections_file().write_text(
        json.dumps(
            {
                "version": 1,
                "corrections": {
                    "good": {"camelot": "8A", "bpm": 120},
                    "bad_key": {"camelot": "99Z", "bpm": 120},
                    "bad_bpm": {"camelot": "8A", "bpm": 0},
                    "wrong_shape": "nope",
                },
            }
        ),
        encoding="utf-8",
    )
    assert set(store.load_corrections()) == {"good"}


def test_unparseable_store_is_preserved_and_warned():
    path = config.corrections_file()
    path.write_text("{ this is not valid json", encoding="utf-8")
    warnings: list[str] = []
    loaded = store.load_corrections(warnings.append)
    assert loaded == {}
    assert warnings  # the user was told
    assert path.with_name(path.name + ".corrupt").exists()  # preserved, set aside
    assert not path.exists()


def test_unrecognised_version_is_set_aside():
    path = config.corrections_file()
    path.write_text(json.dumps({"version": 999, "corrections": {}}), encoding="utf-8")
    warnings: list[str] = []
    assert store.load_corrections(warnings.append) == {}
    assert warnings
    assert path.with_name(path.name + ".corrupt").exists()


def test_interrupted_save_leaves_prior_file_intact(monkeypatch):
    store.save_corrections({"id0": Correction(camelot=to_camelot(6, 1), bpm=122.0)})
    original = config.corrections_file().read_text(encoding="utf-8")

    def boom(*_args, **_kwargs):
        raise OSError("simulated disk full")

    monkeypatch.setattr("pathlib.Path.replace", boom)
    with pytest.raises(OSError, match="disk full"):
        store.save_corrections({"id1": Correction(camelot=to_camelot(8, 0), bpm=90.0)})
    # The previous file is intact and no partial temp file is left behind.
    assert config.corrections_file().read_text(encoding="utf-8") == original
    assert not config.corrections_file().with_name("corrections.json.tmp").exists()


def test_helpers_build_arrangement_and_corrections_from_tracks():
    tracks = [
        EditableTrack(
            "a", "u", "A", ("x",), 0, to_camelot(8, 0), 100.0, "corrected", pinned=False
        ),
        EditableTrack("b", "u", "B", ("x",), 1, None, None, "unknown", pinned=True),
    ]
    arrangement = store.arrangement_from_tracks("p", tracks)
    assert arrangement.order == ("a", "b")
    assert arrangement.pinned == (1,)
    assert set(store.corrections_from_tracks(tracks)) == {"a"}
