# Phase 0 Research: Strict Linting, Formatting & Type Checking Integration

All decisions below are grounded in the actual tool versions probed on 2026-07-02:
`ruff 0.15.20`, `ty 0.0.56 (2026-07-01)`, `just 1.55.1`, `uv 0.11.26`. Config keys and
exit-code behavior were verified by running the tools against scratch projects (including
an empty baseline). No `NEEDS CLARIFICATION` items remain from the spec (the three
clarifications in `spec.md` resolved command delivery, pre-commit scope, and pinning).

---

## D1. Ruff strict lint rule selection

- **Decision**: Enable a broad rule set via `[tool.ruff.lint] select = ["ALL"]`, then
  subtract two categories of exclusions in `ignore`, each listed with a justification
  comment: (a) the formatter-conflict set (below), and (b) the minimal project set
  enumerated below. Strict/safety families (`S` flake8-bandit, `B` bugbear, `ANN`
  annotations, `UP` pyupgrade, `PTH`, `RUF`, …) are **kept** — they align with
  Constitution Principles IV and V.
- **Project `ignore` set** (candidate, minimal; each entry MUST carry a justification
  comment in `pyproject.toml`; adjustable in T005):
  - `D` (pydocstyle) — docstrings-everywhere is premature on a near-empty baseline;
    reconsider once real modules exist.
  - `CPY` (flake8-copyright) — the repo has no copyright-header policy.
  - `TD`, `FIX` (flake8-todos / flake8-fixme) — TODO/FIXME comments are permitted and are
    not merge blockers. (`ERA` eradicate — commented-out code — is **kept**.)
- **Rationale**: The spec defines "strict" as maximal coverage with a small, justified
  exclusion list rather than a curated minimal set (Assumptions; FR-002). `select = ALL`
  makes coverage opt-out (new rules apply by default) instead of opt-in.
- **Formatter-conflict set** (deterministic from Ruff's formatter-compatibility guidance;
  disabled because the formatter owns layout — FR-003): `W191`, `E111`, `E114`, `E117`,
  `D206`, `D300`, `Q000`, `Q001`, `Q002`, `Q003`, `COM812`, `COM819`, `ISC001`, `ISC002`.
- **Alternatives considered**: Curated category list (e.g. `E,F,I,B,UP,SIM`) — rejected as
  narrower than the spec's "broad coverage" mandate and opt-in by nature.

## D2. Ruff formatter configuration & lint/format reconciliation

- **Decision**: Enable `[tool.ruff.format]` with defaults (double quotes, canonical style)
  and treat the formatter as authoritative for all layout; ensure the D1 ignore list
  removes every formatting-related lint rule so `ruff check` and `ruff format` never
  oscillate (FR-003, edge case "linter/formatter overlap"). Set `target-version = "py314"`
  under `[tool.ruff]`.
- **Rationale**: Ruff's own guidance is that its formatter and linter must be reconciled by
  disabling the conflict set; the formatter is deterministic and canonical (FR-003).
- **Alternatives considered**: A separate formatter (e.g. Black) — rejected: the spec names
  Ruff for both roles and a single tool avoids version/behavior drift.

## D3. `ty` strict type-checking model

- **Decision**: `ty` has no single `--strict` flag. Achieve strict checking by
  (a) `[tool.ty.rules]` setting the full rule set to `error` severity (mirroring the
  ruff `select=ALL` philosophy; individual rules downgraded only with justification),
  (b) invoking with `--error-on-warning` in the recipe/gate so any warning is also fatal,
  and (c) targeting Python 3.14. `ty` auto-detects the version from
  `project.requires-python`; pin it explicitly via `[tool.ty.environment] python-version`.
- **Verification**: The keys `[tool.ty.rules]`, `[tool.ty.environment].python-version`, and
  `[tool.ty.src].exclude` were accepted by `ty 0.0.56` (no schema errors). `ty check`
  exited **1** on a genuine type error and **0** on clean code and on an empty baseline.
- **Untyped third-party deps**: `ty` resolves imports from the project's `.venv`; libraries
  without type information are handled by `ty`'s default unresolved-import behavior.
  Any noise is suppressed narrowly per-rule (FR-008), not globally.
- **Suppressions**: Individual findings use inline `# ty: ignore[<rule>]` with a
  justification comment; global weakening is prohibited (Principle IV, FR-008).
- **Alternatives considered**: mypy/pyright — rejected: the spec explicitly names `ty`.

## D4. Dependency declaration & reproducibility

- **Decision**: Declare `ruff`, `ty`, and `pre-commit` in a PEP 735 `[dependency-groups]`
  `dev` group (uv's modern default for `uv add --dev`) using **floor (`>=`) specifiers**,
  and commit `uv.lock`. The lockfile is the reproducibility source of truth; the floor
  specifiers keep pyproject readable while `uv sync` reproduces exact versions.
- **Rationale**: The clarification chose floor + committed lock. For a `0.0.x` preview tool
  (`ty`), the **lock** — not the specifier — does the reproducibility work (SC-006); floor
  specifiers avoid churn while the lock guarantees identical resolution (Principle V:
  pinned dependencies).
- **`just` is not a Python dependency**: it is a standalone binary; document installation
  (`brew install just` / `cargo install just`) as a prerequisite in the README rather than
  adding it to the dev group.
- **Alternatives considered**: Exact `==` pins in pyproject (rejected per clarification:
  noisier and redundant with the lock); `[tool.uv] dev-dependencies` legacy table
  (rejected: `[dependency-groups]` is the current standard uv writes to).

## D5. `just` recipe design

- **Decision**: A root `Justfile` with individual recipes and composite recipes, each
  wrapping `uv run` so tool versions come from the locked dev group:
  - `lint` → `uv run ruff check .`
  - `format-check` → `uv run ruff format --check .`
  - `typecheck` → `uv run ty check --error-on-warning`
  - `format` → `uv run ruff format .`
  - `fix` → `uv run ruff check --fix .` then `uv run ruff format .` (FR-007)
  - `check` (aggregate) → runs `lint`, `format-check`, `typecheck`; non-zero if any fail (FR-006, SC-004)
- **Rationale**: The clarification chose `just` with separate + composite recipes. `just`
  stops on the first failing recipe line, giving the required aggregate exit-code semantics
  for free and identifying the failing check. Wrapping `uv run` keeps a single version
  source (SC-006).
- **Alternatives considered**: Make (rejected per clarification — `just` chosen);
  `poethepoet`/`nox` (rejected: `just` chosen, no extra Python dependency).

## D6. Pre-commit configuration

- **Decision**: Commit `.pre-commit-config.yaml` using `repo: local` hooks that invoke
  `uv run ruff check --fix`, `uv run ruff format`, and `uv run ty check --error-on-warning`
  on staged files. Document the one-time `pre-commit install` (or `uv run pre-commit
  install`) onboarding step (FR-014).
- **Rationale**: Local hooks that call `uv run` keep tool versions in a **single** source
  (the locked dev group) instead of a second pinned `rev` in a mirror repo, preventing
  version drift (SC-006). `ty` also has no established upstream pre-commit mirror; a local
  hook is the reliable path for a preview-stage tool.
- **Alternatives considered**: `astral-sh/ruff-pre-commit` mirror hooks — rejected: they
  pin ruff's version independently of `uv.lock`, creating a second source of truth that can
  drift from the dev group.

## D7. Non-source exclusions & empty-baseline validity

- **Decision**: Exclude non-source paths from all three tools. Ruff excludes `.venv`,
  caches, and build/generated/vendored artifacts (Ruff also respects `.gitignore` by
  default); `ty` uses `[tool.ty.src].exclude` and respects standard ignore files. Do **not**
  bind an `include` list to a `src/` directory that does not exist yet.
- **Rationale**: The committed baseline must install and pass now (FR-010, FR-011, SC-002).
  Verified: on an empty baseline, `ruff check`, `ruff format --check`, and `ty check` all
  exit 0. Targeting the project root minus excludes covers `src/`/`tests/` automatically as
  they are added.
- **Alternatives considered**: Creating `src/`/`tests/` scaffolding now — rejected as out of
  scope for this feature and unnecessary for a passing baseline.
