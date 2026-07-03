# Implementation Plan: Harmonic Playlist Sort (Camelot Key + BPM)

**Branch**: `002-playlist-camelot-sort` | **Date**: 2026-07-03 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-playlist-camelot-sort/spec.md`

**Note**: Produced by `/speckit-plan`. See `.specify/templates/plan-template.md` for the workflow.

## Summary

A Python CLI that reads a Spotify playlist, fetches each track's musical key, mode, and
tempo (BPM) from the ReccoBeats API, derives each track's Camelot Key, and computes a
proposed order sorted by Camelot Key then BPM (unsortable tracks grouped at the end). It
shows the proposed order in the terminal and, on explicit confirmation, writes it
**non-destructively to a new playlist** — the source playlist is never modified. The tool
authenticates to Spotify via OAuth Authorization Code + PKCE (public client), caching the
refresh token in a protected local file. All code passes the repo's strict quality gate
(`just check`: Ruff + `ty`), so external SDKs that would break strict typing are avoided in
favour of thin, fully-typed `httpx` clients.

## Technical Context

**Language/Version**: Python 3.14 (uv-managed; `requires-python = ">=3.14"`)

**Primary Dependencies**: `httpx` (typed HTTP client for both Spotify and ReccoBeats), `rich` (terminal table + confirmation prompt), `platformdirs` (locate the per-user config/token directory). Dev: `pytest` (+ existing `ruff`, `ty`, `pre-commit`). **Not** using `spotipy` — it is untyped and would violate the strict-`ty` gate (see research D6).

**Storage**: Local per-user config directory (via `platformdirs`): a user-only-readable file caching the OAuth refresh token, plus the Spotify `client_id`. No database.

**Testing**: `pytest` for pure-logic unit/property tests (Camelot mapping, sort comparator, playlist-URL parsing, ReccoBeats response parsing). New `just test` recipe; tests added to the quality workflow.

**Target Platform**: Developer/user workstations (macOS/Linux), Python 3.14 terminal.

**Project Type**: Single-project CLI application (first real application code in the repo).

**Performance Goals**: Preview a 100-track playlist in under 60s (SC-006). ReccoBeats batched 40 IDs/request (a few concurrent); Spotify tracks paginated 100/page; 429 responses honoured with backoff.

**Constraints**: Strict `ty` must pass (no untyped SDKs); the source playlist MUST never be modified (non-destructive copy-to-new); OAuth tokens live only in a protected local file and never in logs/output (Constitution V); all external (Spotify/ReccoBeats) responses validated before use.

**Scale/Scope**: Personal-use tool; playlists typically up to a few hundred tracks.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Evaluated against `.specify/memory/constitution.md` v1.0.1. This feature is where
Principles I and V get real teeth (live OAuth + external APIs + playlist writes):

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Reliability & Deterministic Behavior | **Implements** | Non-destructive (source never modified); explicit handling of Spotify/ReccoBeats errors, pagination, and 429 backoff; unsortable/not-found tracks handled without aborting; same source + same ReccoBeats data → same order (deterministic). |
| II. Consistent Code Structure | **Implements** | Layered: typed API clients (`spotify`, `reccobeats`) / domain logic (`camelot`, `sorter`) / CLI + display — no cross-bleeding. |
| III. Automated Formatting & Linting (NON-NEGOTIABLE) | **Complies** | All code passes `just lint` / `just format-check`. |
| IV. Type Safety & Static Verification (NON-NEGOTIABLE) | **Complies** | Strict `ty` passes; thin typed `httpx` clients chosen specifically to avoid untyped-SDK suppressions; any unavoidable `# ty: ignore[...]` is narrow + justified. |
| V. Code Safety & Defensive Practices | **Implements** | OAuth via PKCE (no client secret to leak); refresh token in a user-only-readable, gitignored file; tokens never logged (FR-017); all remote JSON validated into typed models before use; deps pinned via `uv.lock`. |
| Quality Gates (section) | **Complies** | `just check` covers new code; `pytest`/`just test` added; config stays in `pyproject.toml`. |
| Development Workflow (section) | **Complies** | Pre-commit + review unchanged. |

**Result**: PASS. No violations; **Complexity Tracking empty**. Map FR-014/FR-015/FR-017
directly onto Principles I and V.

**Post-design re-check (after Phase 1)**: Still PASS. The copy-to-new-playlist design makes
the source read-only, which *strengthens* Principle I (no destructive path). The typed-`httpx`
choice keeps Principle IV green with no untyped-SDK suppressions. New runtime deps
(`httpx`, `rich`, `platformdirs`) and dev dep (`pytest`) are pinned via `uv.lock`. No new
constitutional considerations; Complexity Tracking remains empty.

## Project Structure

### Documentation (this feature)

```text
specs/002-playlist-camelot-sort/
├── plan.md              # This file
├── research.md          # Phase 0 — decisions (APIs, auth, Camelot, client choices)
├── data-model.md        # Phase 1 — entities & the Camelot mapping
├── quickstart.md        # Phase 1 — setup + verification scenarios
├── contracts/           # Phase 1
│   ├── cli.md           #   CLI command/exit-code contract
│   └── external-apis.md #   Spotify + ReccoBeats request/response contracts used
└── tasks.md             # /speckit-tasks output (NOT created here)
```

### Source Code (repository root)

```text
src/spotify_playlist_sorter/
├── __init__.py
├── __main__.py          # `python -m spotify_playlist_sorter` → cli.main()
├── cli.py               # argparse commands (`login`, `sort <url>`), orchestration, confirm gate
├── config.py            # config dir/paths (platformdirs), client_id, OAuth scopes
├── auth.py              # OAuth Authorization Code + PKCE flow; token cache (protected file)
├── spotify.py           # typed Spotify client: me, get playlist+tracks (paginated), create playlist, add items
├── reccobeats.py        # typed ReccoBeats client: batch audio-features (40/req), map by href
├── camelot.py           # key(0-11)+mode(0/1) → Camelot code; Camelot ordering
├── sorter.py            # build sort keys; order by Camelot then BPM; unsortable → end; stable
├── models.py            # dataclasses: Track, AudioFeatures, CamelotKey, ProposedOrder
└── display.py           # rich table of proposed order + confirmation prompt

tests/
├── test_camelot.py      # key/mode → Camelot table (all 24) + round-trip
├── test_sorter.py       # ordering, unsortable-to-end, stability, multiset preservation
├── test_url.py          # playlist URL/URI/ID parsing
└── test_reccobeats.py   # response parsing + missing-track (content:[]) handling
```

**Structure Decision**: Single-project `src/` layout — this feature introduces the first
application source. Concerns are separated into typed API clients, pure domain logic
(Camelot + sort, the most-tested code), and the CLI/display layer. Runtime deps
(`httpx`, `rich`, `platformdirs`) are added to `[project.dependencies]`; `pytest` to the
dev group; an entry point via `[project.scripts]`. The existing strict quality gate applies
unchanged, extended with a `just test` recipe.

## Complexity Tracking

> No Constitution Check violations. No entries.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
