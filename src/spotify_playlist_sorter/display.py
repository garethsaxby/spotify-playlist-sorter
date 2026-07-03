"""Terminal rendering of a proposed order plus a confirmation prompt."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Console
from rich.prompt import Confirm
from rich.table import Table

if TYPE_CHECKING:
    from .models import ProposedOrder, Track

_console = Console()


def _add_row(table: Table, position: int, track: Track) -> None:
    artists = ", ".join(track.artists)
    features = track.features
    if features is None:
        table.add_row(str(position), track.title, artists, "[dim]—[/]", "[dim]—[/]")
        return
    table.add_row(
        str(position),
        track.title,
        artists,
        features.camelot.code,
        f"{features.tempo:.0f}",
    )


def render_order(order: ProposedOrder) -> None:
    table = Table(title="Proposed order (Camelot -> BPM)")
    table.add_column("#", justify="right")
    table.add_column("Title")
    table.add_column("Artists")
    table.add_column("Camelot")
    table.add_column("BPM", justify="right")
    for position, track in enumerate(order.ordered, start=1):
        _add_row(table, position, track)
    _console.print(table)
    if order.unsortable:
        count = len(order.unsortable)
        _console.print(
            f"[yellow]{count} track(s) had no key/BPM and are "
            f"listed last (unsorted).[/]"
        )


def message(text: str) -> None:
    _console.print(text)


def confirm(prompt: str) -> bool:
    return Confirm.ask(prompt, default=False)
