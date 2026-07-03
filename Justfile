# Justfile — code-quality recipes.
#
# Every recipe wraps `uv run` so tool versions come from the locked `dev` dependency
# group in pyproject.toml / uv.lock (a single source of truth). Requires `just` and `uv`.
# Run `just` (or `just --list`) to see available recipes.

set shell := ["bash", "-uc"]

# List available recipes
default:
    @just --list

# Lint with the strict Ruff rule set (no changes)
[group('qa')]
lint:
    uv run ruff check .

# Verify canonical formatting (no changes)
[group('qa')]
format-check:
    uv run ruff format --check .

# Apply canonical formatting
[group('qa')]
format:
    uv run ruff format .

# Apply safe lint fixes, then canonical formatting
[group('qa')]
fix:
    -uv run ruff check --fix .
    uv run ruff format .

# Strict static type checking (warnings are fatal)
[group('qa')]
typecheck:
    uv run ty check --error-on-warning

# Run the unit tests
[group('qa')]
test:
    uv run pytest

# Aggregate quality gate (lint + format-check + type check); fail-fast, CI-gateable
[group('qa')]
check: lint format-check typecheck
