# Feature Specification: Strict Linting, Formatting & Type Checking Integration

**Feature Branch**: `001-ruff-ty-integration`

**Created**: 2026-07-02

**Status**: Draft

**Input**: User description: "add strict ruff linting, formatting and ty type checking integration into the repository, including configuration via pyproject.toml"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Lint and format code from a single, shared configuration (Priority: P1)

A developer working in the repository wants to catch code-quality problems (unused imports, undefined names, bug-prone patterns, style inconsistencies) and apply consistent formatting automatically, using a strict rule set that everyone on the team shares. They run one documented command to check the code and another to auto-apply safe fixes and formatting.

**Why this priority**: This is the foundational layer that delivers value immediately. Linting and formatting are the highest-frequency, lowest-friction quality controls; they can be adopted independently of type checking and still meaningfully improve code consistency and catch defects. Without a shared, strict, centrally-configured rule set, contributors produce divergent code that is harder to review.

**Independent Test**: Run the documented lint command and format command against the repository. Introduce a deliberate violation (e.g., an unused import and inconsistent indentation), re-run: the check reports the issues with rule codes and a non-zero result, and the fix command resolves the auto-fixable ones. Clean code produces a passing result.

**Acceptance Scenarios**:

1. **Given** a checkout of the repository, **When** a developer runs the documented lint check, **Then** the strict rule set is applied and any violations are reported with their rule codes and locations, exiting non-zero if violations exist.
2. **Given** code containing auto-fixable issues and inconsistent formatting, **When** the developer runs the documented fix/format command, **Then** safe fixes and canonical formatting are applied and the file is left in a state that passes the lint and format checks.
3. **Given** a fully compliant repository, **When** the developer runs both the lint check and the format check in verify mode, **Then** both report success and exit zero.
4. **Given** the linter and formatter are both configured, **When** they run over the same file, **Then** they do not produce conflicting or oscillating results (formatting-related concerns are owned by the formatter).

---

### User Story 2 - Catch type errors early with strict static type checking (Priority: P2)

A developer wants type mistakes (wrong argument types, missing return values, `None` misuse, incompatible assignments) surfaced before runtime. They run one documented command that type-checks the project in strict mode using the configuration shared by the whole team.

**Why this priority**: Static type checking prevents a distinct class of defects that linting does not catch, and provides the most value once code and functions actually exist. It layers on top of P1 but is independently valuable and independently testable, so it is prioritized second.

**Independent Test**: Introduce a deliberate type error (e.g., passing a `str` where an `int` is required, or a function missing a declared return). Run the documented type-check command: the error is reported with location and cause, exiting non-zero. Remove the error: the check passes.

**Acceptance Scenarios**:

1. **Given** a checkout of the repository, **When** a developer runs the documented type-check command, **Then** the project is analyzed in strict mode and any type errors are reported with location and explanation, exiting non-zero if errors exist.
2. **Given** code with a genuine type error, **When** the type check runs, **Then** the specific error is reported and the command fails.
3. **Given** type-correct code, **When** the type check runs, **Then** it reports success and exits zero.
4. **Given** a case where the type checker reports a limitation or false positive that cannot be reasonably resolved in code, **When** a contributor suppresses it, **Then** the suppression is scoped narrowly and accompanied by a justification, rather than disabling checking broadly.

---

### User Story 3 - Enforce all quality gates consistently across local and automated workflows (Priority: P3)

A maintainer wants every contribution to meet the same standard automatically, so review effort focuses on substance rather than style. They want a single aggregate quality command that runs linting, formatting verification, and type checking together and fails on any violation, suitable for running locally, before a commit, and in an automated pipeline.

**Why this priority**: Consistent enforcement multiplies the value of P1 and P2 by making them non-optional and uniform, but it depends on those checks existing first. It is the "make it stick" layer and is independently testable via the aggregate command's exit behavior.

**Independent Test**: Run the aggregate quality command on the clean repository — it passes and exits zero. Introduce any one of a lint violation, a formatting deviation, or a type error — the aggregate command fails and exits non-zero, identifying which check failed.

**Acceptance Scenarios**:

1. **Given** a clean repository, **When** the aggregate quality command runs, **Then** all three checks (lint, format verification, type check) pass and the command exits zero.
2. **Given** a repository containing at least one violation of any kind, **When** the aggregate quality command runs, **Then** the command exits non-zero and the failing check(s) are identifiable from the output.
3. **Given** the aggregate command's non-zero exit behavior, **When** it is invoked from an automated environment, **Then** the environment can gate on the exit code without special parsing.
4. **Given** a contributor attempts to commit changes with the pre-commit integration enabled, **When** the staged changes contain fixable issues, **Then** the checks run automatically and block or auto-correct the commit per the configured behavior.

---

### Edge Cases

- **Linter/formatter overlap**: Formatting-related lint rules must be reconciled with the formatter so the two tools never fight; the formatter is authoritative for layout concerns.
- **Legitimate rule suppression**: When a strict rule genuinely should not apply to a specific line or block, suppression must reference the specific rule code and carry a justification, rather than disabling whole categories or files silently.
- **Type-checker limitations on a preview-stage tool**: The type checker is early-stage and may lack features or emit false positives; there must be a documented, narrowly-scoped way to suppress an individual finding without weakening checking globally.
- **Third-party libraries without type information**: The configuration must define how untyped/stub-less dependencies are handled so their absence of types does not produce unactionable noise.
- **Non-source paths**: Virtual environments, build artifacts, caches, and generated or vendored code must be excluded from all three checks.
- **Empty/near-empty baseline**: The repository currently has essentially no source code; the tooling must install and run cleanly (and pass) against this baseline and remain valid as real code is added.
- **Python version alignment**: The tools must analyze against the project's declared Python version so version-specific rules and type semantics are correct.

## Clarifications

### Session 2026-07-02

- Q: How should the per-check commands and the aggregate quality command be invoked? → A: As `just` recipes in a root `Justfile` — an individual recipe per check (lint, format verification, type check) and for applying fixes, plus composite recipes that run multiple checks together, including an aggregate recipe over all three.
- Q: Should this feature actually author the pre-commit configuration, or only ship an automation-ready aggregate command? → A: Configure hooks now — a committed pre-commit configuration runs Ruff lint (with safe fixes), format verification, and type checking on staged changes, with a documented one-time install step.
- Q: How should tool versions be pinned for reproducibility (SC-006)? → A: Compatible floor (`>=`) specifiers in the declared development dependencies, with a committed `uv.lock` capturing the exact resolved versions as the reproducibility source of truth.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: All linter, formatter, and type-checker configuration MUST reside in `pyproject.toml` as the single source of truth; no separate per-tool configuration files may be required for the tools' own settings.
- **FR-002**: Linting MUST be enabled with a strict, comprehensive rule set (broad coverage rather than a minimal default), with any excluded rules explicitly listed and justified.
- **FR-003**: Formatting MUST enforce one canonical, deterministic style repository-wide, and MUST be reconciled with the linter so the two never produce conflicting outcomes.
- **FR-004**: Type checking MUST run in strict mode.
- **FR-005**: Developers MUST be able to invoke each check (lint, format verification, type check) independently via a documented command, exposed as an individual `just` recipe.
- **FR-006**: The system MUST provide a single aggregate quality command — a composite `just` recipe — that runs all three checks and returns a non-zero exit code if any check fails, suitable for automated enforcement.
- **FR-007**: The system MUST provide a documented command — a `just` recipe — that applies all safe automatic fixes and canonical formatting.
- **FR-008**: Rule and error suppressions MUST be explicit and narrowly scoped (referencing specific rule/error codes) and MUST be accompanied by a justification; blanket disabling of rule categories or whole files without documented rationale MUST NOT be used.
- **FR-009**: The configuration MUST target the project's declared Python version so language- and version-specific behavior is correct.
- **FR-010**: All three checks MUST exclude non-source paths (virtual environments, caches, build/generated/vendored artifacts).
- **FR-011**: The repository MUST pass all three checks (lint, format, type check) in its committed state, establishing a clean baseline.
- **FR-012**: The linting/formatting and type-checking tools MUST be declared as project development dependencies using compatible floor (`>=`) version specifiers, and a lockfile (`uv.lock`) capturing the exact resolved versions MUST be committed as the reproducibility source of truth, so that every developer and automated environment runs identical versions.
- **FR-013**: The repository MUST document how to install the tooling, run each check, apply fixes, and interpret results (including how and when to suppress a finding).
- **FR-014**: The repository MUST include a committed pre-commit configuration that runs, on staged changes, linting with safe fixes, formatting (auto-applied), and type checking, so the checks run automatically on commit without manual invocation, along with a documented one-time install step. Per US3 acceptance scenario 4, fixable issues are auto-corrected (blocking the commit for re-staging) and unfixable violations block the commit.
- **FR-015**: The documented commands of FR-005 (per-check), FR-006 (aggregate), and FR-007 (fix) MUST be delivered as `just` recipes in a `Justfile` at the repository root — an individual recipe for each check (lint, format verification, type check) and for applying fixes, plus composite recipe(s) that run multiple checks together, including the aggregate recipe covering all three.

### Non-Functional / Quality Requirements

- **NFR-001**: Running any individual check or the aggregate quality command on the current repository MUST complete fast enough to be used interactively during development (target: a few seconds on the present codebase).
- **NFR-002**: Check output MUST be actionable — each reported issue identifies the file, location, offending rule/error code, and a human-readable description.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of the linter, formatter, and type-checker configuration lives in `pyproject.toml`; the repository requires zero additional standalone configuration files for those tools' own settings.
- **SC-002**: From a clean checkout, the repository passes lint, format verification, and type checking with a zero exit code on 100% of runs.
- **SC-003**: In verification testing, 100% of deliberately introduced violations (one lint issue, one formatting deviation, one type error) are detected: each is identifiable by check and rule/error code when its individual check is run, and the aggregate quality command exits non-zero whenever any violation is present (SC-004).
- **SC-004**: The aggregate quality command returns a non-zero exit code on any violation and zero otherwise, enabling automated gating with no output parsing.
- **SC-005**: A new contributor can install the tooling and run the full quality suite by following the documentation in under 5 minutes, with no undocumented steps.
- **SC-006**: Every developer and automated environment runs identical tool versions — enforced by the committed `uv.lock` and verifiable from it together with the declared development dependencies — eliminating "works on my machine" configuration drift.
- **SC-007**: The individual and aggregate checks complete within a few seconds on the current codebase, keeping the feedback loop interactive.

## Assumptions

- **Tool selection**: The linter and formatter are provided by Ruff, and the type checker is `ty`, as explicitly named in the feature request. These names define the feature and are treated as given rather than as implementation choices to be re-decided.
- **Definition of "strict" linting**: A broad, comprehensive rule selection is enabled (favoring maximal coverage) with a small, explicitly enumerated and justified set of exclusions where a rule conflicts with the formatter, is not applicable to the project, or is impractical — rather than a minimal default rule set.
- **Definition of "strict" type checking**: The type checker's strict mode is enabled.
- **Python version**: Configuration targets Python 3.14, matching `requires-python` in the existing `pyproject.toml`.
- **Dependency/environment management**: The project uses `uv` with `pyproject.toml`-declared dependencies and the existing virtual environment; the tools are declared as development dependencies with compatible floor (`>=`) specifiers, and a committed `uv.lock` captures the exact resolved versions for reproducibility.
- **Command runner**: Documented per-check, fix, and aggregate commands are provided as `just` recipes in a root `Justfile`; `just` is the task-runner interface, exposing individual recipes plus composite recipes.
- **Preview-stage type checker**: `ty` is early-stage/pre-1.0; this is accepted per the explicit request. Its limitations are handled via narrowly-scoped, justified suppressions rather than by weakening or omitting type checking.
- **Formatter authority**: Where the linter and formatter overlap on layout/style, the formatter is authoritative and conflicting lint rules are disabled.
- **Scope — included**: Centralized `pyproject.toml` tool configuration; documented per-check, aggregate, and auto-fix/format commands delivered as `just` recipes in a root `Justfile`; dev dependencies declared with floor specifiers plus a committed `uv.lock`; a clean passing baseline; documentation; and a committed pre-commit configuration (with a documented install step) so checks run automatically on commit.
- **Scope — excluded**: Authoring a complete continuous-integration pipeline/workflow definition is out of scope (the aggregate command is made CI-ready via its exit code, but wiring a specific CI provider is a separate concern); remediating a large legacy codebase is not required because the repository is effectively empty at baseline.
- **Baseline state**: The repository currently contains no meaningful application source, so establishing a passing baseline is straightforward and the configuration must remain valid as real source is added.
