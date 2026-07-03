<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan:
`specs/002-playlist-camelot-sort/plan.md`
<!-- SPECKIT END -->

## Project

Spotify playlist sorter — Python 3.14, managed with `uv`. Application source will live
under `src/`, tests under `tests/`, as features land.

## Commands

Run `just` to list recipes (quality recipes are in the `qa` group). Setup:
`uv sync` then `uv run pre-commit install`. Run any tool ad hoc with `uv run <tool>`.

| Command | Purpose |
|---------|---------|
| `just check` | **Aggregate gate**: lint + format-check + typecheck (fail-fast, CI-gateable) |
| `just lint` | Ruff strict lint check |
| `just format-check` | Verify canonical formatting |
| `just format` / `just fix` | Apply formatting / apply safe lint fixes + formatting |
| `just typecheck` | `ty` strict type check |

## Python development

- All Ruff and `ty` configuration lives in `pyproject.toml` — no standalone tool config files.
- Dev tools are pinned via committed `uv.lock`; add tools with `uv add --dev <pkg>`.

### Mandatory quality gates (NON-NEGOTIABLE)

Every change MUST pass all three checks before it is complete, committed, or reported as
done — run `just check`:

1. **Ruff lint** (`just lint`) — strict `select = ["ALL"]` rule set must pass.
2. **Ruff format** (`just format-check`) — code must be canonically formatted; use
   `just fix` (or `just format`) to apply.
3. **ty type check** (`just typecheck`) — strict, `--error-on-warning` (warnings are fatal).

`just check` runs all three fail-fast; the installed pre-commit hook (and CI, when wired)
runs the same checks. Never declare work finished while `just check` is red.

### Suppressions

Narrow and justified only — never blanket-disable a category or file:
- Ruff: `code()  # noqa: <CODE>  # reason`
- ty: `x = f()  # ty: ignore[<rule>]  # reason`

Project-wide exclusions go in the `ignore` list under `[tool.ruff.lint]` (or a downgrade
under `[tool.ty.rules]`) in `pyproject.toml`, each with an inline reason.

## Governance

Binding project principles (reliability, consistent structure, formatting, type safety,
code safety) are defined in `.specify/memory/constitution.md`.
