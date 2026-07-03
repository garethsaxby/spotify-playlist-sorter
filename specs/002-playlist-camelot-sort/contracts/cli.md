# Contract: CLI

Command name: `spotify-playlist-sorter` (also `python -m spotify_playlist_sorter`).
Interface is a terminal CLI with an explicit confirmation gate before any write.

## Commands

### `login`
Run the Spotify OAuth (Authorization Code + PKCE) flow and cache the refresh token.

- **Input**: `SPOTIFY_CLIENT_ID` (env or config). Opens the browser; captures the loopback callback.
- **Exit 0**: token cached to the protected config file.
- **Exit non-zero**: auth failed/denied/timed out — clear message; nothing cached.

### `sort <playlist>`
Preview the Camelot+BPM order and, on confirmation, write a new sorted playlist.

- **Input**: `<playlist>` — a Spotify playlist URL, URI, or bare ID. Options: `--yes` (skip
  the prompt and write immediately), `--name <text>` (override the new playlist name).
- **Behaviour**:
  1. Authenticate (using cached token; error if not logged in and not interactive).
  2. Resolve playlist; **verify ownership** (`me.id == owner.id`) — refuse otherwise (FR-003).
  3. Read all tracks (paginated); fetch ReccoBeats features (batched); derive Camelot.
  4. Print the proposed order as a table: `#, Title — Artists, Camelot, BPM`, with
     unsortable tracks listed last under a clear "unsorted" marker.
  5. Prompt `Create new sorted playlist? [y/N]` (unless `--yes`).
  6. On **yes**: create the new playlist, add tracks in order, print the new playlist
     name + URL and a summary (`N sorted, M unsorted`).
  7. On **no**: print "no changes made" and exit.

## Exit codes

| Code | Meaning |
|-----:|---------|
| 0 | Preview shown and declined; or new playlist created successfully |
| 2 | Bad input (unparseable playlist ref, not a playlist) |
| 3 | Not authenticated / auth expired and non-interactive |
| 4 | Playlist not owned by the logged-in user (FR-003) |
| 5 | No track had determinable key/BPM — nothing to sort (FR-013) |
| 6 | Write failed while creating/populating the new playlist (source untouched; incomplete new playlist named) (FR-014) |
| 7 | Playlist has fewer than 2 tracks — nothing to sort (no write) (FR-019) |
| 1 | Unexpected error |

## Invariants (map to spec)

- No new playlist is created without confirmation (or explicit `--yes`) — SC-003.
- The source playlist is never modified — FR-009, SC-004, SC-008.
- The new playlist's track multiset equals the source's — FR-010, SC-004.
- Credentials never appear in output/logs — FR-017.
- Every reported issue names the track and the reason (unsorted/not-found) — NFR-002.
