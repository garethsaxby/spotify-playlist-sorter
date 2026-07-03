"""Domain models (immutable) for the playlist sorter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Provenance = Literal["corrected", "estimated", "unknown"]


@dataclass(frozen=True)
class CamelotKey:
    """A Camelot Wheel position, e.g. 8B."""

    number: int
    letter: str

    @property
    def code(self) -> str:
        return f"{self.number}{self.letter}"

    @property
    def order(self) -> tuple[int, int]:
        """Sort key: wheel number, then minor (A) before major (B)."""
        return (self.number, 0 if self.letter == "A" else 1)


@dataclass(frozen=True)
class AudioFeatures:
    """ReccoBeats-derived features used for sorting."""

    key: int
    mode: int
    tempo: float
    camelot: CamelotKey


@dataclass(frozen=True)
class Track:
    """A source-playlist track. ``features is None`` marks it unsortable."""

    spotify_id: str
    uri: str
    title: str
    artists: tuple[str, ...]
    position: int
    features: AudioFeatures | None = None


@dataclass(frozen=True)
class ProposedOrder:
    """Sorted tracks followed by unsortable ones (original relative order)."""

    sortable: tuple[Track, ...]
    unsortable: tuple[Track, ...]

    @property
    def ordered(self) -> tuple[Track, ...]:
        return self.sortable + self.unsortable


@dataclass(frozen=True)
class SourcePlaylist:
    """A playlist read from Spotify (read-only)."""

    playlist_id: str
    name: str
    owner_id: str
    tracks: tuple[Track, ...]


@dataclass(frozen=True)
class NewPlaylist:
    """A newly created, sorted playlist."""

    playlist_id: str
    name: str
    url: str


@dataclass(frozen=True)
class AuthToken:
    """An OAuth token set. Only the refresh token is persisted."""

    access_token: str
    refresh_token: str
    expires_at: float


@dataclass(frozen=True)
class EditableTrack:
    """A track being edited: resolved key/BPM, provenance, and pin state."""

    spotify_id: str
    uri: str
    title: str
    artists: tuple[str, ...]
    source_position: int
    camelot: CamelotKey | None
    bpm: float | None
    provenance: Provenance
    pinned: bool

    @property
    def sortable(self) -> bool:
        """True iff both key and BPM are set, so the track can be ordered."""
        return self.camelot is not None and self.bpm is not None


@dataclass(frozen=True)
class Correction:
    """A user-supplied key/BPM override for one track, keyed globally by id."""

    camelot: CamelotKey
    bpm: float


@dataclass(frozen=True)
class Arrangement:
    """A saved order (track ids, duplicates repeat) plus pinned positions."""

    version: int
    playlist_id: str
    order: tuple[str, ...]
    pinned: tuple[int, ...]


@dataclass
class EditorState:
    """Mutable in-session editor state: the current tracks and dirty flag."""

    playlist_id: str
    source_name: str
    tracks: list[EditableTrack]
    dirty: bool = False
