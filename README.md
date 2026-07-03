# spotify-playlist-sorter

A tool for sorting Spotify playlists.

## Quality tooling

This repository enforces strict, centrally-configured code quality:

- **Ruff** — linting (strict rule set) and deterministic formatting
- **ty** — strict static type checking
- **just** — task runner exposing each check and composite commands
- **pre-commit** — runs the checks automatically on staged changes

All tool configuration lives in `pyproject.toml`; tool versions are declared as `uv`
development dependencies and pinned by the committed `uv.lock`.

### Prerequisites

- [`uv`](https://docs.astral.sh/uv/) (0.11+) — dependency and environment management
- [`just`](https://github.com/casey/just) (1.55+) — command runner
  (`brew install just` or `cargo install just`)

### Setup

```sh
uv sync                       # install the pinned dev tools from uv.lock
uv run pre-commit install     # one-time: enable the checks to run on every commit
```

### Usage

| Command | What it does |
|---------|--------------|
| `just` | List all recipes |
| `just lint` | Strict Ruff lint check (no changes) |
| `just format-check` | Verify canonical formatting (no changes) |
| `just typecheck` | Strict `ty` type check (warnings are fatal) |
| `just format` | Apply canonical formatting |
| `just fix` | Apply safe lint fixes, then formatting |
| `just check` | **Aggregate gate**: lint + format check + type check; non-zero if any fail |

`just check` is the command to run locally before committing and in CI — it exits non-zero
on any violation, so CI can gate on the exit code with no output parsing.

### Interpreting output

Every reported issue identifies the file, line, the offending rule/error code, and a
human-readable message — for example `F401 ... imported but unused` (Ruff) or
`error[invalid-assignment] ...` (`ty`). A zero exit means the check passed.

### Suppressing a finding

Suppressions MUST be narrow (scoped to a specific code) and carry a short justification;
never disable whole rule categories or files silently.

- **Ruff** — `some_code()  # noqa: E501  # justification here`
- **ty** — `x = untyped()  # ty: ignore[possibly-unresolved-reference]  # justification`

For a rule that genuinely should never apply project-wide, add it to the `ignore` list in
`[tool.ruff.lint]` (or downgrade it under `[tool.ty.rules]`) in `pyproject.toml` **with an
inline comment explaining why** — as the existing entries there do.
