# Quickstart & Verification: Interactive Track Editor (TUI)

Proves the editor works end-to-end. References [contracts/cli.md](./contracts/cli.md),
[contracts/storage.md](./contracts/storage.md), and [data-model.md](./data-model.md).

## Prerequisites

- Feature 002 working (`login` completed; `sort` reads/exports your playlists).
- `uv sync` (adds `textual`). A terminal that supports a full-screen TUI.

## Setup

```sh
uv sync
uv run spotify-playlist-sorter edit <owned-playlist-url>
```
Expected: the editor opens showing all tracks in Camelot→BPM order, with unknown tracks
(no key/BPM) at the end.

## Scenario 1 — Correct a wrong key (US1, SC-001)

Select a mis-keyed track (e.g. one showing 11A that should be 2B), edit its Camelot key to
`2B`. Expected: the value updates, the track re-places into the 2B group, and it is marked as
user-corrected.

## Scenario 2 — Add data to an unknown track (US1, SC-002)

Select an "unknown" track (blank key/BPM), enter a valid Camelot code and BPM. Expected: it
becomes sortable and joins the ordered list at the right position.

## Scenario 3 — Invalid input rejected (SC-005)

Try to set the key to `13Z` or the BPM to `0`/`abc`. Expected: rejected with a message; the
track's value is unchanged and nothing is stored.

## Scenario 4 — Pin a manual move (US4)

Move a track to a chosen position. Expected: it stays there (pinned). Then edit another track's
key — the pinned track does **not** move; the edited track re-places among the non-pinned.

## Scenario 5 — Save and reload (US2, SC-003)

Save, quit, then re-run `edit <same-url>`. Expected: all corrections and the arrangement
(including pins) are restored exactly.

## Scenario 6 — Correction reuse across playlists (SC-004)

Open a **different** playlist that contains a track you corrected earlier. Expected: that
track shows your corrected key/BPM automatically (no re-entry).

## Scenario 7 — Quit with unsaved changes (SC-007)

Make an edit, then quit without saving. Expected: a prompt to save / discard / cancel — edits
are never lost silently.

## Scenario 8 — Export (US3, SC-006)

Export the arrangement. Expected: a new Spotify playlist is created with the same track set in
the current order; the source playlist is unchanged; corrections stay local (not on Spotify).

## Scenario 9 — Quality gate & tests

```sh
just check     # ruff + strict ty (incl. the Textual app) all pass
just test      # pytest: store round-trip/atomic, pin-aware rebuild (4 properties), drift, validation
```

## Success mapping

| Scenario | Validates |
|----------|-----------|
| 1, 2, 3 | SC-001, SC-002, SC-005 (edit/add/validate) |
| 4 | FR-006/FR-012 (auto-place with pins) |
| 5, 6 | SC-003, SC-004 (persistence + global reuse) |
| 7 | SC-007 (no silent loss) |
| 8 | SC-006 (export, source untouched) |
| 9 | Constitution III/IV + testing |
