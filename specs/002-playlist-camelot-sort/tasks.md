---
description: "Task list for Harmonic Playlist Sort (Camelot Key + BPM)"
---

# Tasks: Harmonic Playlist Sort (Camelot Key + BPM)

**Input**: Design documents from `/specs/002-playlist-camelot-sort/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included — the plan (research D10) requests `pytest` for the pure logic (Camelot
mapping, sorter, URL parsing, ReccoBeats parsing). Network layers are verified via
`quickstart.md`, not mocked-heavy unit tests.

**Organization**: By user story. All new code MUST pass the repo's strict quality gate
(`just check`: Ruff `select=ALL` + strict `ty`) — writing type-annotated, lint-clean code is
part of every implementation task, not a separate step.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: different file, no dependency on an incomplete task
- Paths are repository-root relative; app code under `src/spotify_playlist_sorter/`, tests under `tests/`.

---

## Phase 1: Setup

**Purpose**: Add dependencies and the package skeleton so `just check` runs over real code.

- [ ] T001 Add runtime deps `httpx`, `rich`, `platformdirs` to `[project.dependencies]` and dev dep `pytest` (via `uv add` / `uv add --dev`), and declare the entry point `[project.scripts]` `spotify-playlist-sorter = "spotify_playlist_sorter.cli:main"` in `pyproject.toml` — research.md D6
- [ ] T002 Create the package skeleton: `src/spotify_playlist_sorter/__init__.py`, `src/spotify_playlist_sorter/__main__.py` (calls `cli.main()`), and an empty `tests/` package; confirm `uv sync` and `just check` pass on the skeleton — plan.md Project Structure
- [ ] T003 [P] Add a `check`-adjacent `test` recipe (`uv run pytest`) to the `Justfile` under the `qa` group — research.md D10

**Checkpoint**: `just check` and `just test` run (test suite empty) against the new package.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared domain types, pure logic, config, auth, and the base HTTP/URL layer that every story needs.

- [ ] T004 [P] Define domain dataclasses in `src/spotify_playlist_sorter/models.py`: `Track`, `AudioFeatures`, `CamelotKey`, `ProposedOrder`, `SourcePlaylist`, `NewPlaylist`, `AuthToken` — data-model.md
- [ ] T005 [P] Implement `src/spotify_playlist_sorter/config.py`: per-user config dir via `platformdirs`, `client_id` load (env/config), OAuth scopes, and the `0600` token-file path — research.md D7
- [ ] T006 [P] Implement `src/spotify_playlist_sorter/camelot.py`: `(key, mode) -> CamelotKey` using the 24-entry table, plus the `(number, A<B)` ordering key — data-model.md, research.md D2
- [ ] T007 [P] Write `tests/test_camelot.py`: assert all 24 key/mode → Camelot codes and that ordering yields 1A,1B,…,12B — data-model.md
- [ ] T008 Implement `src/spotify_playlist_sorter/sorter.py`: build the sort key `(camelot order, bpm, position)`, order sortable tracks, append unsortable (features is None/invalid) last in original order, guarantee the output multiset equals the input (depends on T004, T006) — research.md D3, FR-010
- [ ] T009 [P] Write `tests/test_sorter.py`: ordering, BPM-within-key, stable ties, unsortable-to-end, and multiset preservation (property test) (depends on T008) — spec SC-002/SC-004
- [ ] T010 Implement `src/spotify_playlist_sorter/spotify.py` base: playlist URL/URI/bare-ID parsing + a typed `httpx` client wrapper (auth header injection, JSON validation, HTTP error + 429 `Retry-After` backoff); unparseable/non-playlist input is rejected (exit 2) (depends on T004, T005) — research.md D8/D9, contracts/cli.md
- [ ] T011 [P] Write `tests/test_url.py`: parse playlist URL, `spotify:playlist:` URI, and bare ID; reject non-playlist/garbage input (depends on T010) — contracts/cli.md
- [ ] T012 Implement `src/spotify_playlist_sorter/auth.py`: OAuth Authorization Code + PKCE (open browser, loopback listener on `127.0.0.1:{port}/callback`, code→token exchange, refresh), caching the refresh token to the `0600` file; never log tokens (depends on T005) — research.md D4/D7, FR-017
- [ ] T013 Implement `src/spotify_playlist_sorter/cli.py` with the `argparse` skeleton and the `login` command wired to `auth.py`, plus `main()` used by `__main__.py` (depends on T012, T002) — contracts/cli.md

**Checkpoint**: `uv run spotify-playlist-sorter login` completes OAuth and caches a token; domain logic is unit-tested.

---

## Phase 3: User Story 1 - Preview a harmonically sorted order (Priority: P1) 🎯 MVP

**Goal**: Given an owned playlist URL, show the Camelot-then-BPM order in the terminal with no writes.

**Independent Test**: Run `sort <owned-url>` and answer "N" — a correct table prints and the source is unchanged; a non-owned URL is refused.

- [ ] T014 [US1] Implement `src/spotify_playlist_sorter/reccobeats.py`: batch `GET /v1/audio-features?ids=` (≤40 IDs), map results back by `href` → Spotify ID, missing/invalid → `features=None`; handle `content: []` and 429 (depends on T004) — research.md D1, contracts/external-apis.md
- [ ] T015 [P] [US1] Write `tests/test_reccobeats.py`: parse a real-shaped response, and confirm partial results + `content: []` map to the correct tracks/unsortable (depends on T014) — spec SC-007
- [ ] T016 [US1] Add read methods to `src/spotify_playlist_sorter/spotify.py`: `get_me()`, `get_playlist()` (name, owner_id), `get_playlist_tracks()` paginated 100/page (depends on T010) — contracts/external-apis.md, FR-004
- [ ] T017 [P] [US1] Implement `src/spotify_playlist_sorter/display.py`: a `rich` table of a `ProposedOrder` (# , Title — Artists, Camelot, BPM) with unsortable tracks under a clear "unsorted" marker (depends on T004) — contracts/cli.md, NFR-002
- [ ] T018 [US1] Add the `sort <playlist>` preview path to `src/spotify_playlist_sorter/cli.py`: parse → auth → read source → ownership check (refuse if not owned, exit 4; bad input exit 2; not-authenticated exit 3) → if the playlist has < 2 tracks, report "nothing to sort" and exit 7 (no write) → ReccoBeats features → Camelot → sort → display; make NO write (depends on T013, T014, T016, T017, T008) — FR-001/002/003/007/019, US1
- [ ] T019 [US1] Verify US1 against quickstart.md Scenarios 1, 2, 4 (preview order correct; source unchanged; non-owned refused) (depends on T018) — SC-001/SC-002/SC-005

**Checkpoint**: MVP — a correct, read-only harmonic preview works end to end.

---

## Phase 4: User Story 2 - Write the sorted order to a new playlist (Priority: P2)

**Goal**: On confirmation, create a new playlist with the sorted order; source untouched.

**Independent Test**: From a preview, confirm — a new playlist appears with the approved order and the same track set; the source is unchanged; declining writes nothing.

- [ ] T020 [US2] Add write methods to `src/spotify_playlist_sorter/spotify.py`: `create_playlist(user_id, name)` and `add_tracks(playlist_id, uris)` batching 100 URIs/request in order (depends on T016) — contracts/external-apis.md, FR-009
- [ ] T021 [US2] Add the confirmation gate + write path to `src/spotify_playlist_sorter/cli.py`: prompt (`rich` Confirm) unless `--yes`; on confirm, ensure a valid/refreshed token, then create the new playlist (private by default; name `"{source} (Camelot sorted)"`, or `--name`), add tracks in order, print summary (`N sorted, M unsorted`) + new playlist URL; on decline make no change; on a create/add failure, leave the source untouched, report the error and name the incomplete new playlist (exit 6); the write uses the tracks read during this run (depends on T018, T020) — FR-008/009/011/014/015/016, US2
- [ ] T022 [US2] Verify US2 against quickstart.md Scenario 3 (new playlist has same multiset in sorted order; source unchanged; decline = no write; and simulate a create/add failure to confirm the source stays unchanged and the incomplete playlist is named) (depends on T021) — SC-003/SC-004/SC-008

**Checkpoint**: The full preview → confirm → new-playlist flow works non-destructively.

---

## Phase 5: User Story 3 - Graceful handling of tracks without key/BPM (Priority: P3)

**Goal**: Missing/undeterminable tracks are retained and grouped last; if nothing is sortable, report and write nothing.

**Independent Test**: Preview a mixed playlist — unsortable tracks appear last, flagged, and are still copied on confirm; a fully-unsortable playlist reports and creates nothing.

- [ ] T023 [US3] Wire the fully-unsortable case in `src/spotify_playlist_sorter/cli.py`: if no track has determinable key/BPM, report and exit 5 with no write; ensure unsortable tracks are still included (last) when writing (depends on T018, T014, T008) — FR-012/FR-013
- [ ] T024 [P] [US3] Add tests for mixed and all-unsortable inputs (unsortable-to-end retained; all-unsortable → FR-013) in `tests/test_sorter.py`/`tests/test_reccobeats.py` (depends on T008, T014) — SC-007
- [ ] T025 [US3] Verify US3 against quickstart.md Scenario 5 (mixed + all-unsortable) (depends on T023) — SC-007, FR-013

**Checkpoint**: The tool is robust on messy real-world playlists.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T026 [P] Review and harden 429/`Retry-After` backoff and user-facing error messages across `src/spotify_playlist_sorter/spotify.py` and `reccobeats.py` (network/HTTP errors surface clearly; no credential leakage) (depends on T010, T014, T020) — FR-016/FR-017, Principle I/V
- [ ] T027 [P] Document usage in `README.md`: the `login` and `sort` commands, Spotify app setup (register app, `client_id`, loopback redirect URI), and where the token is cached — contracts/cli.md (onboarding/setup)
- [ ] T028 Run `just check` and `just test` green across the feature, then execute the full `quickstart.md` (Scenarios 1–6) end to end, confirming a 100-track preview under 60s (depends on all prior) — SC-006, Constitution III/IV

---

## Dependencies & Execution Order

### Phase order

- **Setup (P1)** → **Foundational (P2)** blocks all stories → **US1 (P3)** → **US2 (P4)** → **US3 (P5)** → **Polish (P6)**.
- **US1** is the MVP. **US2** depends on US1's orchestration (`sort` command) + read client. **US3** refines US1's pipeline (unsortable/FR-013).

### Shared-file serialization

- `pyproject.toml`: T001 only. `Justfile`: T003 only.
- `src/.../cli.py`: T013 → T018 → T021 → T023 (sequential).
- `src/.../spotify.py`: T010 → T016 → T020 (sequential).
- Other modules (`models`, `config`, `camelot`, `sorter`, `auth`, `reccobeats`, `display`) and each `tests/test_*.py` are distinct files.

### Parallel opportunities

- **Foundational**: T004, T005, T006, T007 are independent files → run together; T009/T011 follow their targets.
- **US1**: T015 (test) and T017 (`display.py`) parallel with the `spotify.py`/`cli.py` chain.
- **Polish**: T026 and T027 are different files → parallel.

---

## Parallel Example: Foundational

```bash
# Independent modules/tests can be built together:
Task: "models.py dataclasses"          # T004
Task: "config.py (platformdirs)"       # T005
Task: "camelot.py mapping"             # T006
Task: "tests/test_camelot.py"          # T007
```

## Implementation Strategy

### MVP first (US1)

1. Setup (T001–T003) → Foundational (T004–T013) → US1 (T014–T019).
2. **STOP and validate**: `sort <owned-url>` prints a correct, read-only harmonic preview and refuses non-owned playlists (quickstart S1/S2/S4). This alone is a usable tool.

### Incremental delivery

1. MVP (US1) → preview.
2. US2 → confirm + create new sorted playlist (non-destructive).
3. US3 → robustness for unsortable/not-found tracks.
4. Polish → error/backoff hardening, README, full quickstart + `just check`/`just test`.

### Notes

- Every code task must leave `just check` green (strict Ruff `select=ALL` + `ty`); annotate types and keep suppressions narrow + justified (Constitution III/IV).
- The source playlist is read-only throughout; only the new playlist is written (FR-009).
- Tokens never appear in output/logs (FR-017); the token file lives outside the repo (platformdirs), so no `.gitignore` entry is needed.
