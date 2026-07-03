# Implementation Plan: Interactive Track Editor (TUI)

**Branch**: `003-tui-track-editor` | **Date**: 2026-07-03 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-tui-track-editor/spec.md`

**Note**: Produced by `/speckit-plan`. See `.specify/templates/plan-template.md` for the workflow.

## Summary

Add an interactive terminal (TUI) editor, built with **Textual**, on top of feature 002.
The user opens a playlist, sees each track's Camelot key and BPM (from the ReccoBeats
estimate plus any saved corrections), and can **correct or add** a track's key/BPM and
**reorder** tracks. The order follows an "auto-place but pin manual moves" model: non-pinned
tracks are always sorted by Camelot then BPM; a track the user moves becomes **pinned** at
that position. Corrections are saved **globally** (per Spotify track id, reused across
playlists) and the **arrangement** (order + pins) is saved **per playlist**, durably, on an
explicit save (with a prompt on quit). Finally the arrangement is **exported to a new
Spotify playlist**, reusing 002's non-destructive create-and-add. The bug-prone logic
(pin-aware ordering, drift merge, persistence) is pure and unit-tested; the Textual app is a
thin view over it.

## Technical Context

**Language/Version**: Python 3.14 (uv-managed)

**Primary Dependencies**: **Textual** (TUI; ships `py.typed`, verified to pass strict `ty`) plus the existing `httpx`, `rich` (Textual builds on it), `platformdirs`. Dev: `pytest`.

**Storage**: Local JSON in the per-user config directory (via `platformdirs`), written atomically (temp file + rename): `corrections.json` (global, keyed by Spotify track id) and a per-playlist arrangement file (order + pinned ids). No database.

**Testing**: `pytest` for the pure logic — persistence round-trip, pin-aware `rebuild()` (property tests), drift reconciliation, and edit validation. Optional Textual `App.run_test()` pilot smoke test for the app wiring. Runs under the existing `just test`.

**Target Platform**: Developer/user workstation terminal (macOS/Linux), Python 3.14.

**Project Type**: Single-project CLI/TUI application — extends feature 002.

**Performance Goals**: The editor stays responsive (scroll + edit) on a 200-track playlist (SC-008); a correction re-places a track within a couple of seconds (SC-001).

**Constraints**: Strict `ty` must pass (Textual is confirmed compatible); saves MUST be durable/atomic so a crash never corrupts prior work (FR-011); corrections/arrangement stored locally only, never written to Spotify (FR-014); reuse feature 002's read/sort/auth/export rather than re-implementing them.

**Scale/Scope**: Personal use; playlists up to a few hundred tracks.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Evaluated against `.specify/memory/constitution.md` v1.0.1:

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Reliability & Deterministic Behavior | **Implements** | Atomic durable saves (temp+rename); explicit dirty-state + prompt-on-quit so edits are never lost silently; drift merge keeps corrections without loss; `rebuild()` is deterministic and multiset-preserving. |
| II. Consistent Code Structure | **Implements** | Layered: pure logic (`store`, `arrange`) / reused clients (`spotify`, `reccobeats`, `auth`) / thin Textual view (`tui`) / CLI — the TUI holds no domain logic. |
| III. Automated Formatting & Linting (NON-NEGOTIABLE) | **Complies** | All new code passes `just lint`/`format`. |
| IV. Type Safety & Static Verification (NON-NEGOTIABLE) | **Complies** | Strict `ty` passes; **verified** on a minimal Textual app (no untyped-SDK problem). |
| V. Code Safety & Defensive Practices | **Implements** | Atomic writes prevent file corruption; edit input (Camelot/BPM) validated before storing; local files hold no secrets; remote input still validated by 002's clients. |
| Quality Gates (section) | **Complies** | `just check` + `pytest`/`just test` cover the new code; config stays in `pyproject.toml`. |
| Development Workflow (section) | **Complies** | Pre-commit + review unchanged. |

**Result**: PASS. No violations; **Complexity Tracking empty**. Principle I gets real teeth here
(durable saves + no-silent-loss) — map FR-011/FR-016 straight onto it.

**Post-design re-check (after Phase 1)**: Still PASS. The design keeps correctness in pure,
unit-tested modules (`store`, `arrange`) with the Textual app as a thin view (Principle II);
Textual is confirmed strict-`ty`-clean (Principle IV); atomic writes + explicit dirty-state
satisfy Principles I/V. Only new dependency is `textual` (pinned via `uv.lock`). No new
constitutional considerations; Complexity Tracking remains empty.

## Project Structure

### Documentation (this feature)

```text
specs/003-tui-track-editor/
├── plan.md          # This file
├── research.md      # Phase 0 — decisions (Textual, persistence, pin model, drift)
├── data-model.md    # Phase 1 — entities + the pin-aware ordering algorithm & properties
├── quickstart.md    # Phase 1 — setup + verification scenarios
├── contracts/       # Phase 1
│   ├── cli.md       #   the `edit` command contract
│   └── storage.md   #   on-disk formats (corrections.json, arrangement files)
└── tasks.md         # /speckit-tasks output (NOT created here)
```

### Source Code (repository root)

```text
src/spotify_playlist_sorter/
├── models.py        # MODIFIED — add EditableTrack, Correction, Arrangement
├── store.py         # NEW — load/save corrections (global) + arrangement (per-playlist); atomic writes
├── arrange.py       # NEW — pin-aware rebuild() + drift reconcile; reuses the camelot/sorter ordering
├── tui.py           # NEW — Textual App: DataTable, key bindings, edit modal, quit-confirm, export action
├── cli.py           # MODIFIED — add `edit <playlist>` command that launches the TUI
├── sorter.py        # MODIFIED — expose the (camelot, bpm, position) sort key for reuse by arrange.py
├── camelot.py       # MODIFIED — add parse_camelot() (Camelot code string → CamelotKey)
├── config.py        # MODIFIED — add corrections_file() + arrangement_file() store paths
└── (reused unchanged: spotify, reccobeats, auth, display)

tests/
├── test_store.py    # persistence round-trip, atomic write, correction reuse across playlists
└── test_arrange.py  # pin-aware rebuild (4 properties) + drift reconciliation
```

**Structure Decision**: Single-project `src/` layout, extending feature 002. The
correctness-critical logic lives in two pure modules — `store.py` (persistence) and
`arrange.py` (pin-aware ordering + drift merge) — that are fully unit-tested without launching
the TUI. `tui.py` is a thin Textual view that calls them; `cli.py` gains an `edit` command.
`arrange.py` reuses (does not fork) the existing Camelot/BPM ordering from `sorter.py`. New
runtime deps: `textual` (added to `[project.dependencies]`); no other additions.

## Complexity Tracking

> No Constitution Check violations. No entries.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
