"""Tests for the Camelot mapping (all 24 keys + ordering) and code parsing."""

from __future__ import annotations

import pytest

from spotify_playlist_sorter.camelot import parse_camelot, to_camelot

# (key, mode) -> expected Camelot code, from data-model.md.
_EXPECTED = {
    (0, 1): "8B",
    (1, 1): "3B",
    (2, 1): "10B",
    (3, 1): "5B",
    (4, 1): "12B",
    (5, 1): "7B",
    (6, 1): "2B",
    (7, 1): "9B",
    (8, 1): "4B",
    (9, 1): "11B",
    (10, 1): "6B",
    (11, 1): "1B",
    (0, 0): "5A",
    (1, 0): "12A",
    (2, 0): "7A",
    (3, 0): "2A",
    (4, 0): "9A",
    (5, 0): "4A",
    (6, 0): "11A",
    (7, 0): "6A",
    (8, 0): "1A",
    (9, 0): "8A",
    (10, 0): "3A",
    (11, 0): "10A",
}


@pytest.mark.parametrize(
    ("key", "mode", "expected"), [(k, m, code) for (k, m), code in _EXPECTED.items()]
)
def test_to_camelot_all_keys(key, mode, expected):
    assert to_camelot(key, mode).code == expected


def test_order_a_before_b():
    assert to_camelot(9, 0).order < to_camelot(0, 1).order  # 8A before 8B


def test_order_by_number():
    assert to_camelot(11, 1).order < to_camelot(9, 0).order  # 1B before 8A


@pytest.mark.parametrize(("key", "mode"), [(-1, 1), (12, 0), (0, 2), (5, -1)])
def test_invalid_input_raises(key, mode):
    with pytest.raises(ValueError, match=r"range|mode"):
        to_camelot(key, mode)


@pytest.mark.parametrize(
    ("number", "letter"),
    [(n, letter) for n in range(1, 13) for letter in ("A", "B")],
)
def test_parse_camelot_round_trips_every_code(number, letter):
    code = f"{number}{letter}"
    assert parse_camelot(code).code == code


@pytest.mark.parametrize(("text", "expected"), [("8b", "8B"), (" 12a ", "12A")])
def test_parse_camelot_normalises_case_and_whitespace(text, expected):
    assert parse_camelot(text).code == expected


@pytest.mark.parametrize("text", ["13A", "0A", "8Z", "", "8", "A8", "108B"])
def test_parse_camelot_rejects_invalid(text):
    with pytest.raises(ValueError, match=r"Camelot code"):
        parse_camelot(text)
