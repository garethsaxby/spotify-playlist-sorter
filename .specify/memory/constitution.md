<!--
Sync Impact Report
==================
Version change: (unratified template) → 1.0.0
Bump rationale: Initial ratification — placeholder template replaced with concrete,
project-specific governance. First adopted version under semantic versioning.

Modified principles: N/A (initial definition)
Added principles:
  - I. Reliability & Deterministic Behavior
  - II. Consistent Code Structure
  - III. Automated Formatting & Linting (NON-NEGOTIABLE)
  - IV. Type Safety & Static Verification (NON-NEGOTIABLE)
  - V. Code Safety & Defensive Practices
Added sections:
  - Quality Gates (Section 2)
  - Development Workflow (Section 3)
  - Governance
Removed sections: N/A

Templates requiring updates:
  - .specify/templates/plan-template.md ✅ aligned (Constitution Check gate references
    this file dynamically; the five principles above supply the concrete gates)
  - .specify/templates/spec-template.md ✅ no change required (no constitution references)
  - .specify/templates/tasks-template.md ✅ no change required (no constitution references)
  - .specify/templates/checklist-template.md ✅ no change required (no constitution references)

Follow-up TODOs: None. Ratification date set to initial adoption date.
-->

# Spotify Playlist Sorter Constitution

## Core Principles

### I. Reliability & Deterministic Behavior

The tool mutates a user's Spotify playlists through a remote API; it MUST behave
predictably and never leave user data in a corrupted or ambiguous state.

- Every external interaction (Spotify Web API, network, filesystem) MUST handle
  errors, rate limits, timeouts, and partial failures explicitly; unhandled failure
  paths are prohibited.
- Operations that modify user data MUST be idempotent or safely re-runnable, so a
  retry after an interruption cannot duplicate or lose data.
- Errors MUST be surfaced (raised, returned, or logged) and MUST NOT be silently
  swallowed. A bare `except` that hides an error is a defect.
- Given identical inputs and playlist state, a sort operation MUST produce the same
  result; nondeterministic ordering is only acceptable where explicitly specified.

**Rationale**: Users trust the tool with irreplaceable playlist state. Predictable,
fail-explicit behavior is the difference between a helpful tool and one that destroys
data on the first network hiccup.

### II. Consistent Code Structure

There is one canonical way to organize code, and new code follows it rather than
introducing a parallel convention.

- Concerns MUST be separated into distinct layers: API/client access, domain logic
  (sorting rules), and entry points (CLI/UI) do not bleed into one another.
- Modules, functions, and names MUST follow the established naming conventions and
  each unit MUST have a single, clear responsibility.
- New code MUST reuse existing patterns and utilities before adding new ones;
  duplicated or divergent structures require justification in review.

**Rationale**: Structural consistency lowers cognitive load, keeps reviews focused on
substance, and makes defects easier to locate — especially as real source replaces the
near-empty baseline.

### III. Automated Formatting & Linting (NON-NEGOTIABLE)

Style is machine-enforced, never debated or applied by hand.

- All code MUST be formatted by the single canonical formatter (Ruff) and MUST pass
  the strict lint rule set before it is committed.
- All linter and formatter configuration MUST live in `pyproject.toml` as the single
  source of truth; no per-tool config files for these tools' own settings.
- Where the linter and formatter overlap on layout, the formatter is authoritative and
  conflicting lint rules MUST be disabled to prevent oscillation.
- Suppressions MUST reference a specific rule code and carry a written justification.
  Blanket disabling of rule categories or whole files without documented rationale is
  prohibited.

**Rationale**: Mechanical, deterministic style removes an entire class of review
friction and diff churn, so human attention goes to correctness instead of whitespace.

### IV. Type Safety & Static Verification (NON-NEGOTIABLE)

The codebase MUST type-check cleanly in strict mode.

- The project MUST pass strict-mode static type checking (ty) with a zero exit, and
  type errors MUST block merge.
- Public functions and module boundaries MUST carry explicit type annotations.
- Type-check configuration MUST target the project's declared Python version so
  version-specific semantics are correct.
- Suppressions of individual findings MUST be narrowly scoped and justified in a
  comment; globally weakening or disabling type checking is prohibited.

**Rationale**: Static type checking catches a class of defects — wrong argument types,
`None` misuse, incompatible assignments — before runtime, and strictness is only
valuable if it is not allowed to erode one silent ignore at a time.

### V. Code Safety & Defensive Practices

Handling user credentials and untrusted remote data demands defensive-by-default code.

- Secrets and credentials (Spotify client secret, OAuth tokens) MUST NOT be hardcoded
  or committed; they are read from environment or configuration and MUST be kept out of
  logs and error messages.
- External and untrusted input (API responses, user input, files) MUST be validated
  before use; the shape of remote data is never assumed.
- Unsafe constructs MUST be avoided: bare `except`, mutable default arguments,
  `eval`/`exec` on dynamic input, and unchecked `None` access.
- Case handling MUST be explicit and total; prefer immutable data and exhaustive
  branches over implicit fall-through.
- All runtime and development dependencies MUST be pinned so every environment is
  reproducible.

**Rationale**: The tool holds a user's OAuth credentials and acts on their account;
a safety lapse is not a style nit but a security and privacy failure.

## Quality Gates

These gates are objective and machine-checkable; a change that fails any of them is not
merge-ready.

- Every change MUST pass the aggregate quality command — lint, format verification, and
  strict type check — with a zero exit code before merge.
- The main branch MUST remain in a clean, passing baseline at all times; a change may
  not leave any of the three checks failing.
- Linter, formatter, and type-checker versions MUST be declared as pinned development
  dependencies so every developer and automated environment runs identical checks.
- All quality-tooling configuration MUST reside in `pyproject.toml`; non-source paths
  (virtual environments, caches, build/generated/vendored artifacts) MUST be excluded
  from all checks.

## Development Workflow

- Contributors MUST run the aggregate quality command locally before committing; the
  same checks run in the pre-commit/automation integration so nothing merges unchecked.
- Code review verifies compliance with the principles above and the substance of the
  change; it MUST NOT spend effort on style, which is machine-enforced.
- Any deviation from a principle MUST be documented in the plan's Complexity Tracking
  (or equivalent) with an explicit justification and the simpler alternative that was
  rejected — deviations are exceptional, not routine.

## Governance

This constitution supersedes other development practices. When a rule here conflicts with
convenience, the rule wins unless it is formally amended.

- **Amendments**: Changes MUST be proposed with a written rationale, applied to this
  file, versioned per the policy below, and propagated to dependent templates
  (`plan-template.md`, `spec-template.md`, `tasks-template.md`) in the same change.
- **Versioning**: Semantic versioning applies. MAJOR for backward-incompatible principle
  removals or redefinitions; MINOR for a new principle/section or materially expanded
  guidance; PATCH for clarifications and non-semantic wording fixes.
- **Compliance review**: Principle compliance is checked at the Constitution Check gate
  during planning and again at code review. Unjustified violations block progress.
- **Runtime guidance**: Day-to-day technical context (stack, commands, structure) lives
  in `CLAUDE.md` and the active feature plan; this constitution governs the
  non-negotiable rules those documents operate under.

**Version**: 1.0.0 | **Ratified**: 2026-07-02 | **Last Amended**: 2026-07-02
