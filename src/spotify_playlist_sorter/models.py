"""Domain models (immutable) for the playlist sorter."""

from __future__ import annotations

from dataclasses import dataclass


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
