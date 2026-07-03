# Quickstart & Verification: Strict Quality Toolchain

This guide proves the feature works end-to-end. It doubles as the <5-minute onboarding
path (SC-005). It references the command contract in
[contracts/quality-commands.md](./contracts/quality-commands.md); it does not restate
implementation details (those live in `tasks.md` / implementation).

## Prerequisites

- `uv` (0.11.x+) and `just` (1.55.x+) installed. `just` install:
  `brew install just` (macOS) or `cargo install just`.
- A checkout of the repository on branch `001-ruff-ty-integration`.

## Setup

```sh
uv sync            # installs the pinned dev tools (ruff, ty, pre-commit) from uv.lock
uv run pre-commit install   # one-time: enable automatic checks on commit (FR-014)
```

Expected: `uv sync` resolves tools to the exact versions in `uv.lock` (SC-006).

## Scenario 1 — Clean baseline passes (SC-002)

```sh
just check
```

**Expected**: All three checks (lint, format-check, typecheck) pass; exit code `0`.
On the current near-empty repository this holds (verified: ruff and ty exit 0 on an empty
baseline).

## Scenario 2 — Individual checks are invokable (FR-005)

```sh
just lint
just format-check
just typecheck
```

**Expected**: Each runs independently and exits `0` on the clean baseline.

## Scenario 3 — Deliberate violations are caught (SC-003)

Introduce one violation of each kind in a scratch file, then verify detection:

1. **Lint** — add an unused import (e.g. `import os` unused). `just lint` reports the rule
   code (e.g. `F401`) with location and exits non-zero.
2. **Format** — add inconsistent indentation / spacing. `just format-check` reports the
   file would be reformatted and exits non-zero.
3. **Type** — assign a mismatched type (e.g. `x: str = 1`). `just typecheck` reports an
   `invalid-assignment` error with location and exits non-zero.

Then:

```sh
just check
```

**Expected**: Exits non-zero, and the failing check is identifiable from the output
(SC-004). Each introduced issue is reported with its rule/error code (NFR-002).

## Scenario 4 — Auto-fix converges (FR-007, FR-003)

```sh
just fix          # applies safe lint fixes + canonical formatting
just check        # re-verify
```

**Expected**: Auto-fixable lint issues and all formatting deviations are resolved; the
subsequent `just check` passes with no linter/formatter oscillation. (A genuine type error
is *not* auto-fixed and must be corrected by hand.)

## Scenario 5 — Pre-commit enforces on commit (FR-014, US3 #4)

With hooks installed, stage a change containing a fixable formatting issue and commit.

**Expected**: The ruff hooks auto-correct the staged file (or block the commit if a
violation is unfixable); a type error blocks the commit. Committing clean code succeeds.

## Success mapping

| Scenario | Validates |
|----------|-----------|
| 1 | SC-002 (clean baseline passes), FR-011 |
| 2 | FR-005 (independent checks) |
| 3 | SC-003, SC-004, NFR-002 (detection + identifiable failure) |
| 4 | FR-007, FR-003 (fix + no oscillation) |
| 5 | FR-014 (automated enforcement) |

Any run above should complete within a few seconds on the current codebase (NFR-001,
SC-007).
