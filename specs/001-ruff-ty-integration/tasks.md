---
description: "Task list for Strict Linting, Formatting & Type Checking Integration"
---

# Tasks: Strict Linting, Formatting & Type Checking Integration

**Input**: Design documents from `/specs/001-ruff-ty-integration/`

**Prerequisites**: plan.md, spec.md, research.md, contracts/quality-commands.md, quickstart.md

**Tests**: No automated test tasks are generated. Per spec.md, this feature is verified
**behaviorally** (run checks against deliberate violations and assert exit codes / reported
codes) rather than via a unit-test framework. Verification tasks reference the scenarios in
`quickstart.md`.

**Organization**: Tasks are grouped by user story. Note a structural caveat specific to this
feature: the stories share two files (`pyproject.toml`, `Justfile`), so tasks that edit those
files **serialize** across stories and are not marked `[P]` even though the stories are
functionally independent.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1 / US2 / US3 (user-story phase tasks only)
- All paths are repository-root relative.

## Path Conventions

Repository-root tooling artifacts: `pyproject.toml`, `uv.lock`, `Justfile`,
`.pre-commit-config.yaml`, `README.md`. No application `src/` is created by this feature
(see plan.md Structure Decision).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Declare and pin the tools every check depends on.

- [X] T001 Declare dev tool dependencies (`ruff`, `ty`, `pre-commit`) in a PEP 735 `[dependency-groups]` `dev` group in `pyproject.toml` using floor (`>=`) specifiers with the versions validated in research.md (ruff >= 0.15, ty >= 0.0.56, pre-commit >= 4) — research.md D4, FR-012
- [X] T002 Generate and commit `uv.lock` via `uv sync` and confirm `uv run ruff --version` / `uv run ty --version` resolve to the locked versions (depends on T001) — research.md D4, FR-012, SC-006

**Checkpoint**: Tools install reproducibly from `uv.lock` in any environment.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared files that each user story appends to. MUST complete before story recipe/doc tasks.

- [X] T003 [P] Create root `Justfile` scaffold: `set shell`, a `default` recipe that lists available recipes, and a header comment noting recipes wrap `uv run` for a single version source — research.md D5, FR-015
- [X] T004 [P] Create `README.md` with a "Quality tooling" section covering prerequisites (`uv`, `just` install) and setup (`uv sync`, `uv run pre-commit install`) per quickstart.md — FR-013, SC-005

**Checkpoint**: `Justfile` and `README.md` exist for stories to extend; onboarding setup is documented.

---

## Phase 3: User Story 1 - Lint and format from a single shared config (Priority: P1) 🎯 MVP

**Goal**: Strict Ruff linting and deterministic formatting driven entirely from
`pyproject.toml`, with independent lint/format recipes and an auto-fix recipe.

**Independent Test**: On the clean repo, `just lint` and `just format-check` exit 0.
Introduce an unused import + inconsistent indentation → `just lint` / `just format-check`
report rule codes and exit non-zero; `just fix` resolves the auto-fixable ones and the file
then passes, with no linter/formatter oscillation.

- [X] T005 [US1] Add `[tool.ruff]` (`target-version = "py314"`, `exclude` for `.venv`/caches/build/generated), `[tool.ruff.lint]` (`select = ["ALL"]`, `ignore` = the formatter-conflict set from research.md D1 plus any justified project exclusions, each with a comment), and `[tool.ruff.format]` to `pyproject.toml` (depends on T001; same file, so after T001) — research.md D1/D2/D7, FR-001/002/003/008/009/010
- [X] T006 [US1] Add Ruff recipes to `Justfile`: `lint` (`uv run ruff check .`), `format-check` (`uv run ruff format --check .`), `format` (`uv run ruff format .`), and `fix` (`uv run ruff check --fix .` then `uv run ruff format .`) (depends on T003) — research.md D5, FR-005/FR-007, contracts/quality-commands.md
- [X] T007 [US1] Verify US1 against quickstart.md Scenarios 2–4 from repository root: clean baseline passes; a deliberate unused import (`F401`) and bad formatting are reported with codes and exit non-zero; `just fix` converges with no oscillation (depends on T005, T006) — SC-003 (lint/format checks), FR-003, NFR-002

**Checkpoint**: MVP — linting and formatting are fully functional and independently testable.

---

## Phase 4: User Story 2 - Strict static type checking (Priority: P2)

**Goal**: Strict `ty` type checking configured in `pyproject.toml`, invokable via its own recipe.

**Independent Test**: `just typecheck` exits 0 on the clean repo. Introduce a type error
(e.g. `x: str = 1`) → the error is reported with location and error code, exit non-zero;
remove it → passes.

- [X] T008 [US2] Add `[tool.ty.rules]` (all rules at `error` severity; individual downgrades only with a justification comment), `[tool.ty.environment]` (`python-version = "3.14"`), and `[tool.ty.src]` (`exclude` for non-source paths) to `pyproject.toml` (depends on T001; same file as T005, so serialize) — research.md D3/D7, FR-001/004/008/009/010
- [X] T009 [US2] Add `typecheck` recipe (`uv run ty check --error-on-warning`) to `Justfile` (depends on T003; same file as T006, so serialize) — research.md D3/D5, FR-005, contracts/quality-commands.md
- [X] T010 [US2] Verify US2 against quickstart.md Scenario 3 from repository root: clean baseline passes; a deliberate `invalid-assignment` type error is reported with code + location and exits non-zero; removal passes (depends on T008, T009) — SC-003, FR-004, NFR-002

**Checkpoint**: US1 (lint/format) and US2 (type check) both work independently.

---

## Phase 5: User Story 3 - Aggregate gate + automated enforcement (Priority: P3)

**Goal**: A single aggregate quality command and a committed pre-commit configuration that
runs the checks automatically on staged changes.

**Independent Test**: `just check` exits 0 on the clean repo and non-zero when any one of
lint/format/type fails (failing check identifiable). With hooks installed, a staged fixable
issue is auto-corrected and an unfixable/type violation blocks the commit.

- [X] T011 [US3] Add composite `check` recipe to `Justfile` that runs `lint`, `format-check`, then `typecheck`, returning non-zero if any fails (depends on T006, T009 — those recipes must exist) — research.md D5, FR-006, SC-004, contracts/quality-commands.md
- [X] T012 [P] [US3] Create `.pre-commit-config.yaml` with `repo: local` hooks invoking `uv run ruff check --fix`, `uv run ruff format`, and `uv run ty check --error-on-warning` on staged files (depends on T002, T005, T008; different file from T011 so parallel) — research.md D6, FR-014, contracts/quality-commands.md
- [X] T013 [US3] Verify US3 against quickstart.md Scenarios 1 & 5 from repository root: `just check` exits 0 clean and non-zero on any single failing check (identifiable); after `uv run pre-commit install`, a staged fixable change is auto-corrected and a type/unfixable violation blocks the commit (depends on T011, T012) — SC-004, FR-006/FR-014

**Checkpoint**: All three checks run individually, aggregate under one command, and enforce automatically on commit.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation completeness and the committed clean baseline.

- [X] T014 [P] Extend `README.md` with running each check (`just lint`/`format-check`/`typecheck`), applying fixes (`just fix`), interpreting output, and how/when to suppress a finding (narrow, rule/error-code-scoped, with justification) — FR-008/FR-013, SC-005
- [X] T015 Establish the clean committed baseline: run `just fix` then `just check` so the repository passes all three checks in its committed state, and confirm `pyproject.toml` holds 100% of tool config (no standalone tool config files) (depends on T007, T010, T013) — FR-001/FR-011, SC-001/SC-002
- [X] T016 Run the full `quickstart.md` validation end-to-end (Scenarios 1–5) and confirm each check and `just check` complete within a few seconds on the current codebase (depends on T015) — NFR-001, SC-005/SC-007

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately. T002 depends on T001.
- **Foundational (Phase 2)**: T003/T004 create shared files; no dependency on Setup content (but recipes only *run* after T002 installs tools). BLOCKS story recipe/doc tasks.
- **User Stories (Phase 3–5)**: Depend on Setup + Foundational.
  - **US1 (P1)** and **US2 (P2)** are functionally independent but **serialize on `pyproject.toml`** (T005 before/after T008) and on `Justfile` (T006 vs T009).
  - **US3 (P3)** depends on US1 + US2 (its aggregate recipe composes their recipes; pre-commit exercises both tools).
- **Polish (Phase 6)**: Depends on all story verifications (T007, T010, T013).

### Shared-File Serialization (important)

- `pyproject.toml`: T001 → T005 → T008 (sequential; different sections, same file)
- `Justfile`: T003 → T006 → T009 → T011 (sequential)
- `README.md`: T004 → T014 (sequential)
- `uv.lock`: T002 · `.pre-commit-config.yaml`: T012 (standalone files)

### Parallel Opportunities

- **T003 ∥ T004** (Foundational — different files).
- **T011 ∥ T012** (US3 — `Justfile` vs `.pre-commit-config.yaml`).
- **T014** can proceed in parallel with T015 setup work only after story verifications; it edits `README.md`, a different file from the baseline commit.
- Cross-story parallelism is otherwise limited by the shared-file serialization above — this is expected for a config-centric feature.

---

## Parallel Example: Foundational Phase

```bash
# T003 and T004 touch different files and can run together:
Task: "Create root Justfile scaffold with a default/help recipe"
Task: "Create README.md with prerequisites and setup (uv sync, pre-commit install)"
```

## Parallel Example: User Story 3

```bash
# T011 (Justfile aggregate recipe) and T012 (.pre-commit-config.yaml) are different files:
Task: "Add composite `check` recipe to Justfile"
Task: "Create .pre-commit-config.yaml with local ruff + ty hooks"
```

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Phase 1: Setup (T001–T002) — declare + lock tools.
2. Phase 2: Foundational (T003–T004) — Justfile + README scaffolds.
3. Phase 3: User Story 1 (T005–T007) — Ruff lint + format + fix.
4. **STOP and VALIDATE**: `just lint`, `just format-check`, `just fix` behave per quickstart.md Scenarios 2–4. This alone delivers the highest-frequency quality controls.

### Incremental Delivery

1. Setup + Foundational → tooling installs reproducibly.
2. US1 → lint + format (MVP) → validate → commit.
3. US2 → strict type checking → validate → commit.
4. US3 → aggregate `just check` + pre-commit enforcement → validate → commit.
5. Polish → full docs + clean committed baseline + end-to-end quickstart.

### Notes

- [P] = different files, no incomplete dependency.
- No automated test tasks (behavioral verification per spec.md); verification tasks map to quickstart.md scenarios and success criteria.
- Commit after each story checkpoint; the repository must remain in a passing state (FR-011).
- All suppressions added during T005/T008 must be narrow (rule/error-code-scoped) and carry a justification (FR-008, Constitution III & IV).
