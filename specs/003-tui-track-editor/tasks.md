---
description: "Task list for feature 003 — Interactive Track Editor (TUI)"
---

# Tasks: Interactive Track Editor (TUI)

**Input**: Design documents from `/specs/003-tui-track-editor/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ (cli.md, storage.md), quickstart.md

**Tests**: INCLUDED. The plan (Testing) and research D9 explicitly require `pytest` unit tests
for the pure logic (persistence round-trip + atomic write, pin-aware `rebuild()` properties,
drift reconcile, and Camelot/edit validation). TUI smoke tests are optional (Polish).

**Organization**: Tasks are grouped by user story (US1–US4, in priority order) so each story is
an independently implementable, testable increment. Correctness lives in pure modules
(`store.py`, `arrange.py`, `camelot.py`); `tui.py` is a thin Textual view over them.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1 / US2 / US3 / US4 (Setup, Foundational, and Polish carry no story label)
- Every task names an exact file path.

## Path Conventions

Single project, extending feature 002: `src/spotify_playlist_sorter/`, `tests/` at repo root.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add the one new runtime dependency and confirm project hygiene.

- [x] T001 Add `textual` to `[project.dependencies]` in `pyproject.toml`, then run `uv sync` (updates `uv.lock`); confirm `uv run python -c "import textual"` succeeds.
- [x] T002 [P] Verify `.gitignore` still covers Python/TUI artifacts (`__pycache__/`, `.venv/`, `*.pyc`); add any missing pattern (repo `.gitignore`).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared types, the Camelot parser, the reusable sort key, and store paths that every
user story builds on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T003 [P] Extend `src/spotify_playlist_sorter/models.py`: add frozen dataclasses `EditableTrack` (spotify_id, uri, title, artists, source_position, camelot: `CamelotKey | None`, bpm: `float | None`, provenance: `Literal["corrected","estimated","unknown"]`, pinned: bool), `Correction` (camelot: `CamelotKey`, bpm: float), `Arrangement` (version: int, playlist_id: str, order: list[str], pinned: list[int]), and mutable `EditorState` (playlist_id, source_name, tracks: list[EditableTrack], dirty: bool) — per data-model.md.
- [x] T004 [P] Add failing tests for the Camelot parser in `tests/test_camelot.py`: `parse_camelot` round-trips every 1A–12B code, accepts lowercase (`"8b"` → `8B`), and rejects `"13A"`, `"0A"`, `"8Z"`, `""` with `ValueError`.
- [x] T005 Implement `parse_camelot(code: str) -> CamelotKey` in `src/spotify_playlist_sorter/camelot.py`: case-insensitive, normalise to `<1-12><A|B>`, validate range, raise `ValueError` otherwise (FR-005, FR-022). Makes T004 pass.
- [x] T006 Refactor `src/spotify_playlist_sorter/sorter.py`: extract a reusable Camelot→BPM sort key `sort_key(camelot: CamelotKey, bpm: float, position: int) -> tuple[int, int, float, int]` and have `build_proposed_order`/`_sort_key` call it; keep `tests/test_sorter.py` green. `arrange.py` will reuse this (no fork — research D3).
- [x] T007 [P] Add store paths to `src/spotify_playlist_sorter/config.py`: `corrections_file()` → `config_dir()/"corrections.json"` and `arrangement_file(playlist_id: str)` → `config_dir()/"arrangements"/f"{playlist_id}.json"` (create the `arrangements` dir), per contracts/storage.md.

**Checkpoint**: Types, parser, sort key, and paths exist — user stories can begin.

---

## Phase 3: User Story 1 - Correct or add a track's Camelot key and BPM (Priority: P1) 🎯 MVP

**Goal**: Open a playlist in the editor and correct a wrong key or add a missing key+BPM; the
track re-places by Camelot→BPM and invalid input is rejected. The source of truth becomes the
user, not the estimator.

**Independent Test**: `edit` a playlist with one mis-keyed and one unknown track; fix the
mis-keyed track's Camelot code and add the unknown's key+BPM → both take valid values and
re-place correctly; entering `13Z`/`0`/`abc` is rejected with a message and nothing is stored.

### Tests for User Story 1

- [x] T008 [US1] Add failing tests in `tests/test_arrange.py`: (a) `rebuild()` four properties — multiset preserved, pins honoured at their absolute index, non-pinned read in Camelot→BPM order (unsortable last), idempotent, and multiset-preserving on a 200-track input (scale sanity, no timing assertion); (b) `to_editable_tracks` precedence (estimate → unknown) and provenance flags, including the all-unknown case where estimates are empty → every track `unknown` (FR-029); (c) `parse_edit` accepts a valid Camelot+BPM and rejects invalid input.

### Implementation for User Story 1

- [x] T009 [US1] Implement `to_editable_tracks(tracks, estimates, corrections={})` and `parse_edit(camelot_text: str, bpm_text: str) -> tuple[CamelotKey, float]` in `src/spotify_playlist_sorter/arrange.py`: build `EditableTrack`s applying precedence Correction → estimate → unknown and setting provenance; `parse_edit` uses `camelot.parse_camelot` and requires a positive numeric BPM (FR-002, FR-004, FR-005, FR-007, FR-022).
- [x] T010 [US1] Implement `rebuild(tracks: list[EditableTrack]) -> list[EditableTrack]` in `src/spotify_playlist_sorter/arrange.py`: place pinned tracks at their absolute index; partition the non-pinned into sortable (both camelot and bpm set) and unsortable (either None), order the sortable by `sorter.sort_key` and append the unsortable stably last, then fill the free slots — never pass None to `sort_key` — per data-model.md. Makes T008 pass.
- [x] T011 [US1] Create the Textual app skeleton in `src/spotify_playlist_sorter/tui.py`: `App` with a `DataTable` (columns: #, Title, Artist(s), Camelot, BPM, and a non-colour-only provenance+pin marker), row-cursor navigation, a key-binding legend/footer (FR-024), and non-colour-only provenance/pin markers (FR-001, FR-023). (FR-026 loading feedback is the CLI fetch line in T013 plus the in-app export notify in T022.)
- [x] T012 [US1] Add the edit/add modal to `src/spotify_playlist_sorter/tui.py`: an `Input`/modal screen to set the selected track's Camelot+BPM → validate via `parse_edit` → `update_cell` → re-place via `rebuild` → mark provenance `corrected`, set `dirty`; invalid input shows a message and stores nothing (FR-003, FR-004, FR-005, FR-007, research D2).
- [x] T013 [US1] Add the `edit <playlist>` subcommand in `src/spotify_playlist_sorter/cli.py` (register in `_build_parser` + dispatch in `main`): parse the reference (exit `_EXIT_BAD_INPUT`), require a session (exit `_EXIT_NOT_AUTH`), `get_playlist`, ownership guard (exit `_EXIT_NOT_OWNED`), fewer-than-2-tracks guard (`_EXIT_TOO_FEW`, exit 7, matching `sort`), print a fetch-progress line before the network calls (FR-026), fetch ReccoBeats estimates (which may be empty — the editor still opens with all tracks `unknown`, FR-029), build editables via `to_editable_tracks` + initial `rebuild`, then launch the app; close clients in `finally` (FR-028, FR-029, research D8).

**Checkpoint**: A user can open a playlist, correct/add key+BPM, and see re-placement — MVP is independently usable (no persistence or export yet).

---

## Phase 4: User Story 2 - Save the edited structure locally (Priority: P2)

**Goal**: Persist corrections (global) and the arrangement (per playlist) durably; reopening the
same playlist restores everything, reconciling any Spotify-side drift, and corrections reuse
across playlists.

**Independent Test**: Correct several tracks, save, quit, reopen the same playlist → all
corrections and the arrangement (incl. pins) restore exactly; open a *different* playlist
containing a corrected track → the correction is already applied.

### Tests for User Story 2

- [x] T014 [P] [US2] Add failing tests in `tests/test_store.py`: corrections + arrangement round-trip; atomic write leaves the prior file intact when the write is interrupted (simulate failure between temp-write and replace); a malformed *entry* is ignored (not fatal); a present-but-unparseable file is preserved (set aside) and treated as empty with a warning; an unrecognised `version` is treated as unreadable; a correction saved under one playlist is read back for another (global reuse) — FR-011, FR-018, FR-019, FR-021, SC-004, SC-009.
- [x] T015 [P] [US2] Add failing tests in `tests/test_arrange.py` for `reconcile()`: surviving occurrences kept in saved order, removed ids dropped, newly-added ids appended and placed by `rebuild`, pins carried to surviving occurrences (positional match for duplicates) — FR-013, FR-020, SC-003.

### Implementation for User Story 2

- [x] T016 [US2] Implement corrections load/save in `src/spotify_playlist_sorter/store.py`: `{"version":1,"corrections":{id:{camelot,bpm}}}`, atomic write (temp file in same dir + `os.replace`), malformed-entry tolerant on read, unreadable/incompatible-version → preserve file + return empty + warn (FR-010, FR-018, FR-019, FR-021).
- [x] T017 [US2] Implement arrangement load/save per playlist in `src/spotify_playlist_sorter/store.py`: `{"version":1,"playlist_id","order":[ids],"pinned":[positions]}`, atomic write, same version/unreadable handling (contracts/storage.md).
- [x] T018 [US2] Implement `reconcile(current_tracks, saved_order, saved_pinned, corrections) -> list[EditableTrack]` in `src/spotify_playlist_sorter/arrange.py`: apply corrections/estimates, match saved order to surviving occurrences positionally, drop removed, append new as non-pinned, carry pins, then `rebuild` (research D4). Makes T015 pass.
- [x] T019 [US2] Add the save action + dirty tracking to `src/spotify_playlist_sorter/tui.py`: a key action that writes both stores via `store.py` and clears `dirty`; report success/failure (FR-008, FR-018, FR-025); ensure every edit/add sets `dirty` (FR-016).
- [x] T020 [US2] Add the quit-confirm modal to `src/spotify_playlist_sorter/tui.py`: on quit with `dirty`, prompt save / discard / cancel so edits are never lost silently (FR-016, SC-007).
- [x] T021 [US2] Wire persistence into `edit` in `src/spotify_playlist_sorter/cli.py`: load global corrections + the saved arrangement, `reconcile` against the current tracks on open, pass corrections into `to_editable_tracks`, and surface any unreadable-store warning from `store.py` to the user (FR-009, FR-010, FR-013, FR-019).

**Checkpoint**: US1 + US2 work — corrections/arrangement persist and reload with drift handled; corrections reuse across playlists.

---

## Phase 5: User Story 3 - Export the arrangement to a new Spotify playlist (Priority: P3)

**Goal**: Export the current arrangement to a **new** Spotify playlist (source untouched),
reusing feature 002's non-destructive create-and-add; only the order leaves the tool.

**Independent Test**: From an arranged playlist, export → a new Spotify playlist appears with the
same track multiset in the arranged order; the source is unchanged; corrections stay local.

### Implementation for User Story 3

- [x] T022 [US3] Add the export action to `src/spotify_playlist_sorter/tui.py`: reuse `spotify.create_playlist` + `add_tracks` to create a new playlist in the current order; show progress, then success with the new-playlist URL; a failed/partial export leaves local corrections and arrangement unchanged (FR-014, FR-015, FR-025, FR-026, SC-006).
- [x] T023 [US3] Provide the export capability to the app from `src/spotify_playlist_sorter/cli.py`: pass the authenticated `SpotifyClient` (or an export callback) into the app so only the track order (URIs) is written — no harmonic data (FR-014).

**Checkpoint**: All of US1–US3 function independently; the curated result can leave the tool.

---

## Phase 6: User Story 4 - Manually arrange the order (Priority: P4)

**Goal**: Move a track to any chosen position (it becomes pinned and sticks through edits, save,
and export); an explicit full re-sort clears all pins.

**Independent Test**: Move a track from the bottom to a chosen index → it stays there through an
edit of another track, and through save + export; a confirmed full re-sort returns to pure
Camelot→BPM order with all pins cleared.

### Tests for User Story 4

- [x] T024 [P] [US4] Add failing tests in `tests/test_arrange.py`: `move_track` pins a track at the target index and it holds through a subsequent `rebuild`; `full_resort` clears all pins and yields pure Camelot→BPM order (FR-006, FR-012, FR-027).

### Implementation for User Story 4

- [x] T025 [US4] Implement `move_track(tracks, index, target) -> list[EditableTrack]` (set `pinned=True`, place at `target`) and `full_resort(tracks) -> list[EditableTrack]` (clear all pins → `rebuild`) in `src/spotify_playlist_sorter/arrange.py`. Makes T024 pass.
- [x] T026 [US4] Add the move action to `src/spotify_playlist_sorter/tui.py`: move the selected track to a chosen (arbitrary) index via `move_track`, show a pin marker, set `dirty` (FR-012, FR-023).
- [x] T027 [US4] Add the full re-sort action to `src/spotify_playlist_sorter/tui.py`: require an explicit confirmation modal (it clears all pins) before calling `full_resort`, and set `dirty` (FR-006, FR-016, FR-027).

**Checkpoint**: All four user stories are independently functional.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Optional wiring smoke test, docs, and the mandatory quality gates.

- [x] T028 [P] Optional Textual smoke test in `tests/test_tui.py` using `App.run_test()`: open → edit a track → save → export wiring drives the pure layer as expected (research D9).
- [x] T029 [P] Update `README.md`/`specs/003-tui-track-editor/quickstart.md` if anything drifted; ensure the `edit` command and its actions are documented.
- [ ] T030 Run the quickstart.md scenarios 1–9 against a real owned playlist and confirm each expected outcome.
- [x] T031 Run `just check` (Ruff lint + format-check + strict `ty`) and `just test` (pytest) — all green before the feature is considered done (Constitution III & IV, NON-NEGOTIABLE).

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (P1)** → no dependencies.
- **Foundational (P2)** → depends on Setup; **blocks all user stories**.
- **User Stories (P3–P6)** → all depend on Foundational; then proceed in priority order
  (P1 → P2 → P3 → P4) or in parallel where staffed. US3 (export) is most useful once there is an
  arrangement (US1); US4 (pins) exercises `rebuild`'s pin path introduced in US1.
- **Polish (P7)** → depends on the desired user stories being complete.

### Key intra-feature dependencies

- T005 (parse_camelot) ← T004 tests; used by T009 (`parse_edit`).
- T006 (sort key) ← used by T010 (`rebuild`) and T018/T025.
- T003 (models) ← used by T009/T010/T015/T016/T018/T025 and the TUI.
- T009 → T010 (same file, `arrange.py`); T010 before T011–T013 (app needs `rebuild`).
- T016 → T017 (same file, `store.py`); both before T019/T021.
- TUI tasks touching `tui.py` are sequential: T011 → T012 → T019 → T020 → T022 → T026 → T027.

### Parallel opportunities

- Setup: T002 ∥ T001-tail.
- Foundational: T003 ∥ T004 ∥ T007 (distinct files); T005 after T004; T006 after (touches shared sorter).
- US2 tests: T014 (test_store.py) ∥ T015 (test_arrange.py).
- Polish: T028 ∥ T029.

---

## Parallel Example: Foundational

```bash
# Distinct files, no cross-dependency — run together:
Task: "T003 Extend models.py with editor dataclasses"
Task: "T004 Add failing parse_camelot tests in tests/test_camelot.py"
Task: "T007 Add corrections_file()/arrangement_file() to config.py"
```

## Parallel Example: User Story 2 tests

```bash
Task: "T014 Store round-trip/atomic/unreadable tests in tests/test_store.py"
Task: "T015 reconcile() drift tests in tests/test_arrange.py"
```

---

## Implementation Strategy

### MVP first (User Story 1 only)

1. Phase 1 Setup → 2. Phase 2 Foundational → 3. Phase 3 US1.
4. **STOP and VALIDATE**: open a playlist, correct a key, add an unknown, confirm re-placement
   and validation (quickstart scenarios 1–3). This is a demoable MVP with no persistence/export.

### Incremental delivery

- Add **US2** → save/reload + drift + correction reuse (scenarios 5, 6, 7).
- Add **US3** → export to a new playlist (scenario 8).
- Add **US4** → manual pins + full re-sort (scenario 4).
- Finish with **Polish** → smoke test, docs, and `just check` + `just test` (scenario 9).

Each story keeps the pure logic (`store.py`, `arrange.py`) unit-tested independently of the TUI —
the split that kept feature 002 robust under live debugging.

### Notes

- `[P]` = different files, no dependency on an incomplete task.
- `[Story]` labels map each task to a user story for traceability.
- Verify each failing test fails before implementing the code that satisfies it.
- Commit after each task or logical group; keep `just check` green as you go.
