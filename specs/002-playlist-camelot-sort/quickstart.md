# Quickstart & Verification: Harmonic Playlist Sort

Proves the feature works end-to-end and doubles as onboarding. References
[contracts/cli.md](./contracts/cli.md) and [data-model.md](./data-model.md).

## Prerequisites

- `uv`, `just` (repo tooling); run `uv sync`.
- A **Spotify app** (developer dashboard) for a `client_id`, with redirect URI
  `http://127.0.0.1:8080/callback` registered (must exactly match the tool's configured
  port; 8080 default). Export `SPOTIFY_CLIENT_ID=…`.
- An owned Spotify playlist of catalog tracks to test with.

## Setup

```sh
uv sync
export SPOTIFY_CLIENT_ID=<your app client id>
uv run spotify-playlist-sorter login    # one-time OAuth; caches the refresh token
```

Expected: browser opens, you approve, terminal prints "logged in"; a `0600` token file
exists under the per-user config dir.

## Scenario 1 — Preview only, source untouched (US1, SC-001)

```sh
uv run spotify-playlist-sorter sort <owned-playlist-url>
# review the table, then answer "N" at the prompt
```
Expected: a table of tracks in Camelot-then-BPM order (unsorted items last); answering **N**
makes no change. Re-opening the source playlist shows it unchanged.

## Scenario 2 — Correct ordering (SC-002)

Expected in the printed order: Camelot codes are non-decreasing 1A→12B, and within one code
BPM is non-decreasing (e.g. `8A 120`, `8A 128`, `8B 122`). Verify against a couple of known
tracks.

## Scenario 3 — Create the new sorted playlist (US2, SC-004)

```sh
uv run spotify-playlist-sorter sort <owned-playlist-url>   # answer "y"
```
Expected: a **new** playlist is created (name like `… (Camelot sorted)`), its order matches
the preview, its track set equals the source's, and the **source is unchanged**. Summary
prints `N sorted, M unsorted` and the new playlist URL.

## Scenario 4 — Ownership guard (SC-005)

```sh
uv run spotify-playlist-sorter sort <someone-elses-playlist-url>
```
Expected: refused with a clear message; exit code 4; nothing created.

## Scenario 5 — Unsortable tracks handled (US3, SC-007)

Use a playlist including tracks ReccoBeats lacks. Expected: sortable tracks ordered, the
missing ones grouped last under an "unsorted" marker and still copied into the new playlist;
the run completes. If **no** track resolves, the tool reports it and creates nothing (FR-013,
exit 5).

## Scenario 6 — Quality gate & unit tests

```sh
just check     # ruff lint + format + ty (strict) all pass on the new code
just test      # pytest: camelot mapping, sorter, url parsing, reccobeats parsing
```
Expected: both green. The Camelot mapping (all 24), sort ordering/stability/multiset, and
ReccoBeats `content: []` handling are covered.

## Success mapping

| Scenario | Validates |
|----------|-----------|
| 1 | SC-001, FR-008/FR-011 (preview, no unconfirmed write) |
| 2 | SC-002 (ordering) |
| 3 | SC-004, FR-009/FR-010 (new playlist, same multiset, source untouched) |
| 4 | SC-005, FR-003 (ownership) |
| 5 | SC-007, FR-012/FR-013 (unsortable handling) |
| 6 | Constitution III/IV + testing |
