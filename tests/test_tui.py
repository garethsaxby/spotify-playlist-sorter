"""Smoke test for the Textual editor app wiring (pilot; no real Spotify/disk)."""

from __future__ import annotations

import asyncio

from textual.widgets import DataTable

from spotify_playlist_sorter.camelot import to_camelot
from spotify_playlist_sorter.models import EditableTrack, EditorState
from spotify_playlist_sorter.tui import TrackEditorApp


def _editable(name, key, mode, tempo):
    return EditableTrack(
        spotify_id=name,
        uri=f"spotify:track:{name}",
        title=name.title(),
        artists=("artist",),
        source_position=0,
        camelot=to_camelot(key, mode),
        bpm=tempo,
        provenance="estimated",
        pinned=False,
    )


def _make_app():
    state = EditorState(
        playlist_id="p1",
        source_name="Source",
        tracks=[_editable("a", 8, 0, 90.0), _editable("b", 9, 0, 120.0)],
    )
    saves: list[dict[str, object]] = []
    exports: list[list[str]] = []

    def save_fn(editor_state, corrections):
        saves.append(
            {"playlist_id": editor_state.playlist_id, "count": len(corrections)}
        )

    def export_fn(uris):
        exports.append(list(uris))
        return "https://open.spotify.com/playlist/new"

    app = TrackEditorApp(state, {}, save_fn=save_fn, export_fn=export_fn)
    return app, saves, exports


def test_app_mounts_and_populates_table():
    async def scenario():
        app, _saves, _exports = _make_app()
        async with app.run_test():
            assert app.query_one(DataTable).row_count == 2

    asyncio.run(scenario())


def test_save_action_invokes_save_fn_and_clears_dirty():
    async def scenario():
        app, saves, _exports = _make_app()
        app._state.dirty = True
        async with app.run_test() as pilot:
            await pilot.press("s")
            await pilot.pause()
        assert len(saves) == 1
        assert app._state.dirty is False

    asyncio.run(scenario())


def test_edit_action_marks_track_corrected():
    async def scenario():
        app, _saves, _exports = _make_app()
        async with app.run_test() as pilot:
            await pilot.press("e")  # open the edit modal on the first row
            await pilot.pause()
            await pilot.press("enter")  # accept the pre-filled valid values
            await pilot.pause()
        edited = next(t for t in app._state.tracks if t.spotify_id == "a")
        assert edited.provenance == "corrected"
        assert app._state.dirty is True

    asyncio.run(scenario())


def test_export_action_invokes_export_fn_with_current_order():
    async def scenario():
        app, _saves, exports = _make_app()
        async with app.run_test() as pilot:
            await pilot.press("x")
            await app.workers.wait_for_complete()
            await pilot.pause()
        assert len(exports) == 1
        assert len(exports[0]) == 2

    asyncio.run(scenario())
