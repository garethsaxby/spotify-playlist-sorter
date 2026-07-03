# Contract: Quality Commands & Exit-Code Semantics

The external interface of this feature is a set of `just` recipes plus a pre-commit hook
set. Their **names, behavior, and exit codes** are the contract that automation, CI, and
contributors depend on. Exit-code behavior below is verified against `ruff 0.15.20` and
`ty 0.0.56`.

## `just` recipes

| Recipe | Underlying command | Purpose | Exit 0 when | Exit non-zero when | Spec |
|--------|--------------------|---------|-------------|--------------------|------|
| `lint` | `uv run ruff check .` | Strict lint check (no mutation) | No lint violations | Any violation (reports rule code + location) | FR-005 |
| `format-check` | `uv run ruff format --check .` | Verify canonical formatting (no mutation) | All files formatted | Any file would be reformatted | FR-005 |
| `typecheck` | `uv run ty check --error-on-warning` | Strict type check (no mutation) | No error/warning diagnostics | Any type error or warning (reports error code + location) | FR-004, FR-005 |
| `format` | `uv run ruff format .` | Apply canonical formatting | Always (after applying) | Tool error only | FR-007 |
| `fix` | `uv run ruff check --fix .` then `uv run ruff format .` | Apply safe fixes + formatting | Always (after applying) | Tool error only | FR-007 |
| `check` | runs `lint`, `format-check`, `typecheck` in sequence | **Aggregate quality gate** | All three exit 0 | **Any** of the three exits non-zero; the failing check is identifiable from output | FR-006, SC-003, SC-004 |

**Aggregate contract (`just check`)**: `just` executes recipe lines sequentially and aborts
on the first non-zero exit, so `check` returns non-zero if and only if at least one
sub-check fails, with no output parsing required (SC-004). Suitable for CI gating on exit
code alone.

**Determinism**: `lint`/`format-check`/`typecheck` are read-only (no file mutation).
`format`/`fix` are the only mutating recipes. Running `fix` then `check` on the same tree
must converge (no oscillation between linter and formatter — FR-003).

## Pre-commit hooks

A committed `.pre-commit-config.yaml` defines `repo: local` hooks invoked on staged files:

| Hook | Command | Behavior on staged changes |
|------|---------|----------------------------|
| ruff-lint | `uv run ruff check --fix` | Applies safe fixes; blocks commit if unfixable violations remain |
| ruff-format | `uv run ruff format` | Applies canonical formatting; blocks commit if it had to reformat |
| ty | `uv run ty check --error-on-warning` | Blocks commit on any type error/warning |

**Contract**: With hooks installed (`pre-commit install`), a `git commit` whose staged
changes contain fixable issues has them auto-corrected; a commit with unfixable lint,
formatting, or type violations is blocked (FR-014, US3 acceptance scenario 4). Hook tool
versions resolve from the locked `dev` dependency group (single version source — SC-006).

## Configuration source-of-truth contract

- 100% of Ruff and `ty` configuration resides in `pyproject.toml`; no standalone per-tool
  config files are required for these tools' own settings (FR-001, SC-001).
- Tool versions resolve identically everywhere via the committed `uv.lock` (FR-012, SC-006).
- All three checks exclude non-source paths (`.venv`, caches, build/generated/vendored) and
  pass on the current empty baseline (FR-010, FR-011, SC-002).
