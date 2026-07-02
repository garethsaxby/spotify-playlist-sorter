# Implementation Plan: Strict Linting, Formatting & Type Checking Integration

**Branch**: `001-ruff-ty-integration` | **Date**: 2026-07-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-ruff-ty-integration/spec.md`

**Note**: This plan was produced by `/speckit-plan`. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Establish a strict, centrally-configured code-quality toolchain for the repository: Ruff
for linting and deterministic formatting, and `ty` for strict static type checking — all
configured in `pyproject.toml` as the single source of truth. Commands are delivered as
`just` recipes (individual per-check recipes plus composite recipes, including an
aggregate `check` that gates on exit code), tool versions are declared as `uv`
development dependencies with floor specifiers and pinned by a committed `uv.lock`, and a
committed pre-commit configuration runs the checks automatically on staged changes. The
repository must install and **pass** all three checks against its current near-empty
baseline and remain valid as real source is added.

## Technical Context

**Language/Version**: Python 3.14 (`requires-python = ">=3.14"`; `.venv` is CPython 3.14.0, uv-managed)

**Primary Dependencies**: Ruff 0.15.x (lint + format), `ty` 0.0.x (strict type check, preview-stage); `pre-commit` 4.x (dev dependency). `just` 1.55.x and `uv` 0.11.x are system prerequisites, not Python packages.

**Storage**: N/A (developer-tooling configuration; no runtime persistence)

**Testing**: No runtime unit-test framework is introduced by this feature. Verification is behavioral: run each check and the aggregate command against the repo and against deliberately-introduced violations, asserting exit codes and reported rule/error codes (see `quickstart.md`).

**Target Platform**: Developer workstations (macOS/Linux) and automated/CI environments; checks are cross-platform via `uv run`.

**Project Type**: Single project — repository-level tooling/infrastructure for a future Python CLI/application.

**Performance Goals**: Each individual check and the aggregate command complete within a few seconds on the current codebase (NFR-001, SC-007), keeping the feedback loop interactive.

**Constraints**: All tool configuration lives in `pyproject.toml` (FR-001); the formatter is authoritative for layout and conflicting lint rules are disabled (FR-003); strict linting (broad rule set) and strict type checking; suppressions must be narrow and justified (FR-008); non-source paths excluded (FR-010); the committed baseline must pass all three checks (FR-011, SC-002).

**Scale/Scope**: Near-empty baseline (no meaningful application source at present). Tooling must pass now and remain correct as `src/` and `tests/` are populated by later features.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Evaluated against `.specify/memory/constitution.md` v1.0.1:

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Reliability & Deterministic Behavior | N/A (this scope) | No runtime code exists yet; this feature adds no external interactions. It *enables* future reliability by making defects detectable early. |
| II. Consistent Code Structure | **Supports** | Formatting + linting mechanically enforce structural and stylistic consistency this principle demands. |
| III. Automated Formatting & Linting (NON-NEGOTIABLE) | **Implements** | This feature *is* the machine-enforced formatting/linting mandate: Ruff canonical, config in `pyproject.toml`, narrow justified suppressions. |
| IV. Type Safety & Static Verification (NON-NEGOTIABLE) | **Implements** | Strict `ty` in the aggregate gate; targets Python 3.14; suppressions narrow and justified. |
| V. Code Safety & Defensive Practices | Partial / N/A (this scope) | Runtime/secret aspects are N/A (no runtime code); the *pinned-dependency* clause is directly satisfied via floor specifiers + committed `uv.lock` — literal under the v1.0.1 wording clarification (analyze finding C1 resolved). |
| Quality Gates (section) | **Implements** | Aggregate `just check` recipe (lint + format-check + type-check, zero-exit contract); pinned dev deps; config centralized in `pyproject.toml`; non-source paths excluded. |
| Development Workflow (section) | **Supports** | Pre-commit config runs the same checks locally; review is freed from style. |

**Result**: PASS. No principle is violated; the feature directly implements the two
NON-NEGOTIABLE principles and the Quality Gates section. **Complexity Tracking is empty**
— no deviations to justify.

**Post-design re-check (after Phase 1)**: Still PASS. The design adds only tooling artifacts
(`pyproject.toml` config, `uv.lock`, `Justfile`, `.pre-commit-config.yaml`, `README.md`),
introduces no runtime code, and adds no new dependencies beyond pinned dev tools. No new
constitutional considerations arose; Complexity Tracking remains empty.

## Project Structure

### Documentation (this feature)

```text
specs/001-ruff-ty-integration/
├── plan.md              # This file (/speckit-plan output)
├── research.md          # Phase 0 output — tool-configuration decisions
├── data-model.md        # Phase 1 output — N/A rationale (no runtime data model)
├── quickstart.md        # Phase 1 output — verification & onboarding scenarios
├── contracts/           # Phase 1 output — command & exit-code contracts
│   └── quality-commands.md
└── tasks.md             # /speckit-tasks output (NOT created by /speckit-plan)
```

### Source Code (repository root)

This feature adds repository-level tooling artifacts, not application source. The
concrete files created/modified during implementation are:

```text
pyproject.toml            # [tool.ruff], [tool.ruff.lint], [tool.ruff.format],
                          # [tool.ty.*], [dependency-groups] dev  (MODIFIED)
uv.lock                   # committed lockfile pinning exact tool versions  (NEW)
Justfile                  # individual + composite recipes  (NEW)
.pre-commit-config.yaml   # local hooks running the checks on staged files  (NEW)
README.md                 # install / run / fix / suppress documentation  (NEW)
```

**Intended future application layout** (informational — *not* created by this feature,
and the tooling MUST NOT hard-code these as required paths yet):

```text
src/spotify_playlist_sorter/   # package: api client, domain (sorting), entry points
tests/                         # unit / integration tests
```

**Structure Decision**: Single-project layout. The quality tooling targets the
repository (project root) with explicit exclusions for non-source paths (`.venv`, caches,
build/generated artifacts) rather than an `include` list bound to a `src/` directory that
does not exist yet. This keeps the current near-empty baseline **passing** (verified: ty,
`ruff check`, and `ruff format --check` all exit 0 on an empty baseline) while
automatically covering `src/` and `tests/` as later features create them.

## Complexity Tracking

> No Constitution Check violations. No entries.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
