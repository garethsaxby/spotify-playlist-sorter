"""Tests for playlist-reference parsing."""

from __future__ import annotations

import pytest

from spotify_playlist_sorter.spotify import parse_playlist_id

_ID = "37i9dQZF1DXcBWIGoYBM5M"


@pytest.mark.parametrize(
    "reference",
    [
        _ID,
        f"spotify:playlist:{_ID}",
        f"https://open.spotify.com/playlist/{_ID}",
        f"https://open.spotify.com/playlist/{_ID}?si=abc123",
        f"  {_ID}  ",
    ],
)
def test_parses_valid_references(reference):
    assert parse_playlist_id(reference) == _ID


@pytest.mark.parametrize(
    "reference",
    [
        "",
        "not-a-playlist",
        "spotify:track:37i9dQZF1DXcBWIGoYBM5M",
        "https://open.spotify.com/album/37i9dQZF1DXcBWIGoYBM5M",
        "https://example.com/playlist/37i9dQZF1DXcBWIGoYBM5M",
    ],
)
def test_rejects_invalid_references(reference):
    with pytest.raises(ValueError, match="playlist reference"):
        parse_playlist_id(reference)
