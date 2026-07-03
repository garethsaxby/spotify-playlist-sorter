"""Derive a Camelot Key from a Spotify (key, mode) pair."""

from __future__ import annotations

from .models import CamelotKey

PITCH_CLASS_COUNT = 12

# Wheel number for each pitch class (index 0=C .. 11=B), by mode.
_MAJOR_NUMBERS = (8, 3, 10, 5, 12, 7, 2, 9, 4, 11, 6, 1)
_MINOR_NUMBERS = (5, 12, 7, 2, 9, 4, 11, 6, 1, 8, 3, 10)

_MODE_MINOR = 0
_MODE_MAJOR = 1


def to_camelot(key: int, mode: int) -> CamelotKey:
    """Map ``key`` (0-11) and ``mode`` (0=minor, 1=major) to a Camelot Key.

    Raises ``ValueError`` for out-of-range input so callers can treat the track
    as unsortable.
    """
    if not 0 <= key < PITCH_CLASS_COUNT:
        msg = f"key out of range 0-11: {key}"
        raise ValueError(msg)
    if mode == _MODE_MAJOR:
        return CamelotKey(number=_MAJOR_NUMBERS[key], letter="B")
    if mode == _MODE_MINOR:
        return CamelotKey(number=_MINOR_NUMBERS[key], letter="A")
    msg = f"mode must be 0 or 1: {mode}"
    raise ValueError(msg)
