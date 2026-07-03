"""Textual TUI for editing a playlist's per-track key/BPM and arrangement.

A thin view over the pure ``arrange``/``store`` logic: it renders the current tracks,
routes every mutating action through a single table refresh, and holds no domain logic.
Persistence and export are injected as callables so the app is testable in isolation.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, ClassVar

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import DataTable, Footer, Header, Input, Label

from .arrange import full_resort, move_track, parse_edit, rebuild
from .spotify import SpotifyError
from .store import corrections_from_tracks

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from .models import Correction, EditableTrack, EditorState

_PROVENANCE_MARK = {"corrected": "*", "estimated": "~", "unknown": "?"}
_DASH = "—"


def _flags(track: EditableTrack) -> str:
    """A non-colour-only marker for provenance and pin state (FR-023)."""
    mark = _PROVENANCE_MARK[track.provenance]
    return f"{mark} [P]" if track.pinned else mark


class _EditScreen(ModalScreen["tuple[str, str] | None"]):
    """Modal to set a track's Camelot code and BPM; validates before closing.

    Returns the raw (camelot, bpm) text once it parses; the caller re-parses it.
    """

    BINDINGS: ClassVar[list[Binding]] = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, track: EditableTrack) -> None:
        super().__init__(classes="modal")
        self._camelot = track.camelot.code if track.camelot is not None else ""
        self._bpm = f"{track.bpm:g}" if track.bpm is not None else ""
        self._title = track.title

    def compose(self) -> ComposeResult:
        with Vertical(classes="dialog"):
            yield Label(f"Edit: {self._title}")
            yield Input(
                value=self._camelot, placeholder="Camelot, e.g. 8B", id="camelot"
            )
            yield Input(value=self._bpm, placeholder="BPM, e.g. 128", id="bpm")
            yield Label("", id="error")

    def on_mount(self) -> None:
        self.query_one("#camelot", Input).focus()

    def action_cancel(self) -> None:
        self.dismiss(None)

    def on_input_submitted(self) -> None:
        camelot_text = self.query_one("#camelot", Input).value
        bpm_text = self.query_one("#bpm", Input).value
        try:
            parse_edit(camelot_text, bpm_text)
        except ValueError as exc:
            self.query_one("#error", Label).update(str(exc))
            return
        self.dismiss((camelot_text, bpm_text))


class _MoveScreen(ModalScreen["int | None"]):
    """Modal to choose a 1-based target position; returns a 0-based index."""

    BINDINGS: ClassVar[list[Binding]] = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, count: int, current: int) -> None:
        super().__init__(classes="modal")
        self._count = count
        self._current = current

    def compose(self) -> ComposeResult:
        with Vertical(classes="dialog"):
            yield Label(f"Move to position (1-{self._count}):")
            yield Input(value=str(self._current + 1), id="target")
            yield Label("", id="error")

    def on_mount(self) -> None:
        self.query_one("#target", Input).focus()

    def action_cancel(self) -> None:
        self.dismiss(None)

    def on_input_submitted(self) -> None:
        error = self.query_one("#error", Label)
        try:
            position = int(self.query_one("#target", Input).value.strip())
        except ValueError:
            error.update("Enter a whole number.")
            return
        if not 1 <= position <= self._count:
            error.update(f"Out of range 1-{self._count}.")
            return
        self.dismiss(position - 1)


class _ConfirmScreen(ModalScreen["bool"]):
    """Yes/no confirmation modal (used before a pin-clearing full re-sort)."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("y", "yes", "Yes"),
        Binding("n", "cancel", "No"),
        Binding("escape", "cancel", "No"),
    ]

    def __init__(self, prompt: str) -> None:
        super().__init__(classes="modal")
        self._prompt = prompt

    def compose(self) -> ComposeResult:
        with Vertical(classes="dialog"):
            yield Label(self._prompt)
            yield Label("[y] yes    [n] no")

    def action_yes(self) -> None:
        self.dismiss(result=True)

    def action_cancel(self) -> None:
        self.dismiss(result=False)


class _QuitScreen(ModalScreen["str"]):
    """Prompt on quit with unsaved changes: save / discard / cancel (FR-016)."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("s", "save", "Save & quit"),
        Binding("d", "discard", "Discard & quit"),
        Binding("c", "cancel", "Cancel"),
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self) -> None:
        super().__init__(classes="modal")

    def compose(self) -> ComposeResult:
        with Vertical(classes="dialog"):
            yield Label("You have unsaved changes.")
            yield Label("[s] save & quit    [d] discard & quit    [c] cancel")

    def action_save(self) -> None:
        self.dismiss("save")

    def action_discard(self) -> None:
        self.dismiss("discard")

    def action_cancel(self) -> None:
        self.dismiss("cancel")


class TrackEditorApp(App[None]):
    """Interactive editor for a playlist's key/BPM corrections and arrangement."""

    CSS = """
    .modal { align: center middle; }
    .dialog {
        width: 64;
        height: auto;
        padding: 1 2;
        border: thick $accent;
        background: $surface;
    }
    #error { color: $error; }
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("e", "edit", "Edit key/BPM"),
        Binding("m", "move", "Move"),
        Binding("r", "resort", "Re-sort"),
        Binding("s", "save", "Save"),
        Binding("x", "export", "Export"),
        Binding("q", "request_quit", "Quit"),
    ]

    def __init__(
        self,
        state: EditorState,
        corrections: dict[str, Correction],
        *,
        save_fn: Callable[[EditorState, dict[str, Correction]], None],
        export_fn: Callable[[list[str]], str] | None = None,
        warnings: Sequence[str] = (),
    ) -> None:
        super().__init__()
        self._state = state
        self._corrections = dict(corrections)
        self._save_fn = save_fn
        self._export_fn = export_fn
        self._pending_warnings = list(warnings)

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable(cursor_type="row", zebra_stripes=True)
        yield Footer()

    def on_mount(self) -> None:
        self.title = "Track Editor"
        self.sub_title = self._state.source_name
        table = self.query_one(DataTable)
        table.add_columns("#", "Title", "Artist(s)", "Camelot", "BPM", "Flags")
        self._refresh_table(0)
        for warning in self._pending_warnings:
            self.notify(warning, severity="warning")

    def _refresh_table(self, focus_index: int) -> None:
        table = self.query_one(DataTable)
        table.clear()
        for position, track in enumerate(self._state.tracks, start=1):
            table.add_row(
                str(position),
                track.title,
                ", ".join(track.artists),
                track.camelot.code if track.camelot is not None else _DASH,
                f"{track.bpm:.0f}" if track.bpm is not None else _DASH,
                _flags(track),
            )
        if self._state.tracks:
            table.move_cursor(row=min(focus_index, len(self._state.tracks) - 1))

    def _mark_dirty(self, new_tracks: list[EditableTrack], focus_index: int) -> None:
        self._state.tracks = new_tracks
        self._state.dirty = True
        self._refresh_table(focus_index)

    def _persist(self) -> bool:
        merged = {**self._corrections, **corrections_from_tracks(self._state.tracks)}
        try:
            self._save_fn(self._state, merged)
        except OSError as exc:
            self.notify(f"Save failed: {exc}", severity="error")
            return False
        self._corrections = merged
        self._state.dirty = False
        return True

    @work
    async def action_edit(self) -> None:
        if not self._state.tracks:
            return
        row = self.query_one(DataTable).cursor_row
        track = self._state.tracks[row]
        result = await self.push_screen_wait(_EditScreen(track))
        if result is None:
            return
        camelot, bpm = parse_edit(*result)
        updated = replace(track, camelot=camelot, bpm=bpm, provenance="corrected")
        new_tracks = list(self._state.tracks)
        new_tracks[row] = updated
        new_tracks = rebuild(new_tracks)
        focus = next(index for index, t in enumerate(new_tracks) if t is updated)
        self._mark_dirty(new_tracks, focus)

    @work
    async def action_move(self) -> None:
        if not self._state.tracks:
            return
        row = self.query_one(DataTable).cursor_row
        target = await self.push_screen_wait(_MoveScreen(len(self._state.tracks), row))
        if target is None:
            return
        self._mark_dirty(move_track(self._state.tracks, row, target), target)

    @work
    async def action_resort(self) -> None:
        confirmed = await self.push_screen_wait(
            _ConfirmScreen("Re-sort by Camelot/BPM? This clears all manual pins.")
        )
        if not confirmed:
            return
        self._mark_dirty(full_resort(self._state.tracks), 0)

    def action_save(self) -> None:
        if self._persist():
            self.notify("Saved corrections and arrangement.")

    @work(thread=True)
    def action_export(self) -> None:
        export_fn = self._export_fn
        if export_fn is None:
            self.call_from_thread(
                self.notify, "Export is unavailable.", severity="error"
            )
            return
        self.call_from_thread(self.notify, "Exporting to a new playlist…")
        uris = [track.uri for track in self._state.tracks]
        try:
            url = export_fn(uris)
        except SpotifyError as exc:
            self.call_from_thread(
                self.notify, f"Export failed: {exc}", severity="error"
            )
            return
        self.call_from_thread(self.notify, f"Exported to {url}")

    @work
    async def action_request_quit(self) -> None:
        if self._state.dirty:
            choice = await self.push_screen_wait(_QuitScreen())
            if choice == "cancel":
                return
            if choice == "save" and not self._persist():
                return
        self.exit()
