# spotify-playlist-sorter

A command-line tool that sorts one of your Spotify playlists by **Camelot key then BPM**
and writes the result to a **new** playlist (the source is never modified). Track key/BPM
come from the free [ReccoBeats](https://reccobeats.com) API; the sorted playlist is a
harmonic-mixing "library" to pick tracks from.

## Usage

### One-time setup

1. Create a Spotify app at the [developer dashboard](https://developer.spotify.com/dashboard)
   and add the redirect URI **`http://127.0.0.1:8080/callback`** (must match exactly).
2. Export its client id and install the tool:

   ```sh
   export SPOTIFY_CLIENT_ID=<your app client id>
   uv sync
   uv run spotify-playlist-sorter login   # opens a browser; caches a refresh token
   ```

The refresh token is stored in a user-only (`0600`) file under your OS config directory
(`platformdirs`), never in the repo and never printed.

### Sorting a playlist

```sh
uv run spotify-playlist-sorter sort <playlist-url|uri|id>
```

It prints the proposed order (Camelot + BPM, unsortable tracks listed last) and asks for
confirmation before creating the new playlist. Options: `--yes` (skip the prompt),
`--name <text>` (name the new playlist), `--public` (default is private).

Exit codes: `0` ok, `2` bad input, `3` not logged in, `4` not your playlist, `5` nothing
sortable, `6` write failed (source untouched), `7` fewer than 2 tracks.

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
