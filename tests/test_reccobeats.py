"""Tests for ReccoBeats response parsing and transport errors."""

from __future__ import annotations

import httpx
import pytest

from spotify_playlist_sorter.reccobeats import (
    ReccoBeatsClient,
    ReccoBeatsError,
    parse_audio_features,
)

_ID = "003vvx7Niy0yvhvHt4a68B"


def test_transport_error_becomes_reccobeats_error():
    def _raise(_request):
        raise httpx.ConnectError("boom")

    http_client = httpx.Client(
        transport=httpx.MockTransport(_raise),
        base_url="https://api.reccobeats.com/v1",
    )
    client = ReccoBeatsClient(client=http_client)
    with pytest.raises(ReccoBeatsError):
        client.fetch_features([_ID])


def _entry(spotify_id=_ID, key=1, mode=1, tempo=148.033):
    return {
        "href": f"https://open.spotify.com/track/{spotify_id}",
        "key": key,
        "mode": mode,
        "tempo": tempo,
    }


def test_parses_valid_entry():
    features = parse_audio_features({"content": [_entry()]})
    assert set(features) == {_ID}
    assert features[_ID].camelot.code == "3B"  # key 1 (C#) major -> 3B
    assert features[_ID].tempo == 148.033


def test_empty_content_maps_to_nothing():
    assert parse_audio_features({"content": []}) == {}


def test_partial_results_only_return_present_ids():
    features = parse_audio_features({"content": [_entry()]})
    assert _ID in features
    assert "0000000000000000000000" not in features


def test_invalid_entries_are_skipped():
    bad = [
        {"href": "no-track-here", "key": 1, "mode": 1, "tempo": 120.0},
        _entry(key=99),  # key out of range -> to_camelot raises
        _entry(tempo=0),  # non-positive tempo
    ]
    assert parse_audio_features({"content": bad}) == {}


def test_non_dict_payload_is_safe():
    assert parse_audio_features(None) == {}
    assert parse_audio_features([]) == {}
