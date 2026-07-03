# Phase 0 Research: Interactive Track Editor (TUI)

Grounded by probing the actual tools on 2026-07-03: **Textual 8.2.8** verified to pass strict
`ty`, and the Textual `DataTable` capabilities confirmed from its docs. Builds on feature 002.
No `NEEDS CLARIFICATION` remain (spec clarifications settled behaviour, data model, save,
export, and framework).

---

## D1. TUI framework — Textual

- **Decision**: Build the TUI with **Textual** (8.x).
- **Verification (live)**: A minimal app (`App`, `DataTable`, `BINDINGS`, `compose`,
  `query_one`, `add_columns`/`add_row`) passes `ty check --error-on-warning` cleanly — so the
  strict-`ty` gate (Principle IV) is satisfied without untyped-SDK suppressions. Textual ships
  `py.typed`.
- **Rationale**: Same authors as `rich` (already a dependency; Textual is built on it), typed,
  and purpose-built for interactive scrollable lists — the exact track-editor UI. Confirmed by
  the user (`/speckit-clarify`, 2026-07-03).
- **Alternatives considered**: `urwid` (older, weaker typing); a plain `rich`-only loop (no
  real interactivity); a web app (rejected in discussion — fragments the stack, changes auth).

## D2. DataTable editing pattern

- **Decision**: Use `DataTable` with a **row cursor** for navigation and edit via a **modal
  `Input` screen**, not inline cells. Update cells programmatically with `update_cell` after a
  validated edit.
- **Verification (docs)**: `DataTable` has **no inline cell editing**; it exposes cursor types
  (`row`/`cell`/`column`/`none`), `cursor_coordinate`/`cursor_row`, `coordinate_to_cell_key`,
  and `update_cell`/`update_cell_at`. The documented pattern is: selection message → modal
  input → `update_cell` → return focus.
- **Rationale**: Matches the widget's real capabilities; a modal edit for Camelot + BPM is
  clear and keyboard-driven.

## D3. Order model — "auto-place with absolute-index pins"

- **Decision**: Non-pinned tracks are always ordered by Camelot key then BPM (unsortable last);
  a track the user moves becomes **pinned to its absolute index** and is not re-placed by later
  edits. An explicit full re-sort clears all pins. See `data-model.md` for the exact `rebuild()`
  operation and its four properties.
- **Rationale**: Absolute-index pins are simple, deterministic, and unit-testable — the same
  role the sorter played in 002. Editing/adding a track's data slots it into place while
  deliberate manual moves stick.
- **Alternatives considered**: **Relative anchors** ("keep after track Y") — closer to a DJ's
  mental model but much harder to define, reconcile on drift, and test; **rejected for v1** and
  recorded here as a conscious choice (candidate for a later iteration).
- **Reuse**: `arrange.py` uses `sorter.py`'s `(camelot order, bpm, position)` sort key for the
  non-pinned tracks — it generalizes the existing sorter, it does not fork it.

## D4. Drift reconciliation

- **Decision**: When a saved playlist's tracks changed on Spotify, reconcile = keep the saved
  order for surviving track ids → drop removed ids → treat newly-added ids as non-pinned →
  `rebuild()`. Corrections (global) are applied regardless.
- **Rationale**: Because non-pinned tracks are always sorted, restoring only the pin set +
  running `rebuild()` reproduces the arrangement and slots new tracks into place — no bespoke
  merge logic. Preserves all saved corrections (FR-013).

## D5. Persistence — local JSON, atomic

- **Decision**: Two on-disk stores in the per-user config dir (`platformdirs`):
  - `corrections.json` — **global**, `{version, corrections: {spotify_track_id: {camelot, bpm}}}`.
  - one arrangement file per playlist — `{version, order: [track_id…], pinned: [position…]}`
    (pins are **positions** into `order`, so a specific occurrence of a duplicated track is
    unambiguous — FR-020).
  Both written atomically (write temp file, then `os.replace`), so a crash never corrupts prior
  work (FR-011). Exact shapes are pinned in `contracts/storage.md`.
- **Rationale**: JSON is simple, human-inspectable, and matches the existing token-cache
  approach; atomic replace is the durability mechanism. Corrections are a property of the track
  (global); arrangement is per-playlist.
- **Alternatives considered**: SQLite (overkill for a personal tool, heavier to inspect); a
  single combined file (couples global corrections with per-playlist order — rejected).

## D6. Edit validation

- **Decision**: A Camelot edit MUST parse to a valid wheel code (1A–12B) — reuse/extend the
  `camelot` module with a parser (code string → `CamelotKey`); a BPM edit MUST be a positive
  number. Invalid input is rejected in the modal with a message and nothing is stored (FR-005).
- **Rationale**: Keeps the local store clean and the sort well-defined; validation lives in the
  pure layer so it is unit-tested.

## D7. Dirty-state & save/quit

- **Decision**: The editor state carries an explicit **unsaved-changes** flag, set on any
  edit/move and cleared on save. Save is explicit (a key action); quitting with the flag set
  opens a confirm modal (save / discard / cancel). No auto-save (FR-016).
- **Rationale**: Explicit dirty-state makes "prompt only if there are changes" exact rather than
  guessed, and lets the user discard experiments.

## D8. CLI integration & export

- **Decision**: Add an `edit <playlist>` command that authenticates (reuse `auth`), reads the
  playlist (reuse `spotify.get_playlist`), fetches estimates (reuse `reccobeats`), applies saved
  corrections, builds the initial arrangement, and launches the Textual app. Export from the app
  reuses `spotify.create_playlist` + `add_tracks` (always a new playlist — FR-015).
- **Rationale**: Maximal reuse of feature 002; the new surface is only the editor + persistence.

## D9. Testing

- **Decision**: `pytest` covers the pure logic: persistence round-trip + atomic write +
  correction reuse (`test_store.py`); pin-aware `rebuild()` four properties + drift reconcile
  (`test_arrange.py`); plus Camelot-code parsing/validation. An optional Textual `App.run_test()`
  pilot smoke-tests app wiring. Joins `just test`.
- **Rationale**: The correctness lives in pure functions, testable without launching the TUI —
  the split that made 002 robust under live debugging.
