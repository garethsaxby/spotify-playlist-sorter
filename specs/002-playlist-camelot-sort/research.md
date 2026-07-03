# Phase 0 Research: Harmonic Playlist Sort (Camelot Key + BPM)

Grounded by a **live probe** of the ReccoBeats API and by reading the reference project's
production code (`juliangalati/spotify-playlist-analyzer`) on 2026-07-03, plus the current
Spotify Web API. Tool baseline: Python 3.14, uv 0.11, the repo's strict `ty`/Ruff gate.

---

## D1. Audio-features source — ReccoBeats (key + mode + tempo)

- **Decision**: Fetch key, mode, and tempo from ReccoBeats:
  `GET https://api.reccobeats.com/v1/audio-features?ids={comma-separated Spotify track IDs}`,
  batched **≤40 IDs/request** (a few requests concurrently), **no authentication**.
- **Verification (live)**: A real request for `003vvx7Niy0yvhvHt4a68B` returned
  `{"href": ".../track/003vvx7Niy0yvhvHt4a68B", "key": 1, "mode": 1, "tempo": 148.033, ...}`
  inside a `content[]` array. So ReccoBeats **does** provide `key` (0–11) and `mode` (0/1),
  despite its docs page listing only 9 features — the docs undersell the response.
- **Matching**: `ids=` accepts Spotify track IDs; each result carries `href` (the Spotify
  URL) → map results back to source tracks by Spotify ID. Order is **not** guaranteed and
  not every requested ID returns.
- **Not-found is common**: The same probe requested 2 IDs and got 1 back (even a hugely
  popular track was absent); a bogus ID yields `{"content": []}` with HTTP 200. Missing
  tracks → treated as **unsortable** (FR-012/FR-018), not errors.
- **Rationale**: Free, no-auth, ID-precise, and the user's chosen source; confirmed to
  supply exactly the fields Camelot needs.
- **Alternatives considered**: Spotify `/v1/audio-features` (has key/mode but returns 403
  for apps created after 2024-11-27 — availability depends on the app's age); GetSongBPM
  (has key+BPM but matches by artist/title, less precise, needs registration + backlink).
  Rejected in favour of ReccoBeats' ID-precise, no-auth access.

## D2. Camelot Key derivation

- **Decision**: Map `(key, mode)` → Camelot code with a static table. `key` is pitch class
  0–11 (0=C … 11=B); `mode` 1=major (Camelot "B"), 0=minor (Camelot "A").
  - Major (mode 1): C→8B, C#/Db→3B, D→10B, D#/Eb→5B, E→12B, F→7B, F#/Gb→2B, G→9B, G#/Ab→4B, A→11B, A#/Bb→6B, B→1B.
  - Minor (mode 0): C→5A, C#/Db→12A, D→7A, D#/Eb→2A, E→9A, F→4A, F#/Gb→11A, G→6A, G#/Ab→1A, A→8A, A#/Bb→3A, B→10A.
- **Rationale**: Standard Camelot Wheel; matches the reference project's derivation. A pure
  function → the single most valuable unit test (all 24 mappings).
- **Alternatives considered**: Computing Camelot from key signatures at runtime — rejected;
  a static table is simpler and unambiguous.

## D3. Sort algorithm

- **Decision**: Sort key = `(camelot_number, camelot_letter_rank, bpm)` where number is
  1–12, letter rank puts "A" before "B", BPM ascending. Order: 1A,1B,2A,2B,…,12B; within a
  key, ascending BPM (e.g. 1A → 125, 150, 190). Python's stable `sorted` preserves original
  order for exact ties. Unsortable tracks (no ReccoBeats key/BPM) are appended **after** all
  sortable tracks, keeping their original relative order.
- **Rationale**: Exactly the user's "Camelot then BPM", literal (not an energy path); the
  output is a browsable library, so a flat deterministic order is the goal.
- **Alternatives considered**: Harmonic/energy path (Camelot adjacency) — explicitly out of
  scope per clarification.

## D4. Spotify authentication — Authorization Code + PKCE

- **Decision**: OAuth **Authorization Code flow with PKCE** (public client — no client
  secret). Scopes: `playlist-read-private`, `playlist-read-collaborative` (read source),
  `playlist-modify-public`, `playlist-modify-private` (create the new playlist). The CLI
  opens the system browser to the authorize URL, runs a temporary loopback HTTP listener on
  a fixed, configurable port (default `http://127.0.0.1:8080/callback`) that MUST match the
  redirect URI registered in the Spotify app, captures the code, exchanges it for tokens,
  and caches the refresh token.
- **Rationale**: PKCE is the correct flow for a CLI/native public client — no secret to
  store or leak (Constitution V). Loopback redirect is Spotify's supported native pattern.
- **Alternatives considered**: Authorization Code with a client secret (rejected: a CLI
  can't keep a secret confidential); device code (Spotify doesn't offer it).
- **Prerequisite**: The user registers a Spotify app for a `client_id` and adds the loopback
  redirect URI; `client_id` is provided via env/config (not secret).

## D5. Apply model — copy to a NEW playlist (non-destructive)

- **Decision**: On confirmation, `POST /v1/users/{user_id}/playlists` to create a new
  playlist, then `POST /v1/playlists/{new_id}/tracks` to add track URIs **in sorted order**,
  batched **100 URIs/request**, sequentially to preserve order. The source playlist is only
  ever read.
- **Rationale**: The user confirmed the output is a "library to pick from" and chose a
  non-destructive copy; playlists are catalog-tracks-only (no local files), so the copy is
  lossless. This eliminates in-place reorder's atomicity/snapshot problem entirely and makes
  FR-010/FR-014 trivially safe (the source is never touched).
- **Alternatives considered**: In-place reorder via `PUT .../tracks` position moves +
  `snapshot_id` (preserves local files but complex, and Spotify offers no transactional
  reorder); URI "replace" (drops local files, multi-batch truncation window). Both rejected
  because copy-to-new is safer and the local-files caveat doesn't apply here.

## D6. HTTP + library choices (strict-`ty` driven)

- **Decision**: Use `httpx` with thin, fully-typed first-party client modules for **both**
  Spotify and ReccoBeats. `rich` for the proposed-order table and confirm prompt;
  `platformdirs` for the config/token directory; stdlib `argparse` for commands (`login`,
  `sort`). Dev: `pytest`.
- **Rationale**: The repo's NON-NEGOTIABLE strict-`ty` gate makes untyped SDKs costly.
  `httpx`, `rich`, and `platformdirs` ship `py.typed`; `spotipy` does not and would force
  broad `# ty: ignore`. Hand-rolling the few Spotify calls we need (me, get playlist/tracks,
  create, add) is ~100 lines and keeps full type coverage and minimal pinned deps.
- **Alternatives considered**: `spotipy` (mature OAuth/pagination but untyped → violates
  Principle IV unless quarantined behind an adapter with justified ignores); `typer`/`click`
  (fine, but `argparse` adds no dependency for a two-command CLI).

## D7. Token storage

- **Decision**: Cache the OAuth **refresh token** in a file under the per-user config dir
  (`platformdirs.user_config_dir("spotify-playlist-sorter")`), created with `0600`
  (user-only) permissions. Never written to logs/output. Access tokens are kept in memory
  and refreshed as needed. The Spotify `client_id` is stored alongside (it is not secret).
- **Rationale**: Matches the clarified decision (local protected file, log in once) and
  Constitution V. The config dir is outside the repo, so it cannot be committed.

## D8. Reading source + writing new playlist

- **Decision**: Ownership check — `GET /v1/me` id vs playlist `owner.id` (FR-003). Read all
  tracks via `GET /v1/playlists/{id}/tracks` paginated 100/page (follow `next`). Parse the
  playlist URL/URI/bare ID up front. Write path per D5.
- **Rationale**: Standard Spotify pagination; ownership check is a cheap gate satisfying the
  spec's owned-playlist constraint.

## D9. Rate limits & failure handling

- **Decision**: On HTTP 429, honour `Retry-After` and back off (both APIs). Wrap Spotify and
  ReccoBeats calls so network/HTTP errors surface as clear messages (Principle I); a
  ReccoBeats gap or partial outage degrades to "unsortable" rather than aborting; a total
  failure to obtain any key/BPM triggers FR-013 (report, no write).
- **Rationale**: Interactive reliability (NFR-001) and non-abortive behaviour on messy real
  playlists.

## D10. Testing

- **Decision**: Add `pytest` (dev) and a `just test` recipe. Focus tests on pure logic:
  Camelot mapping (all 24), sort comparator (ordering, unsortable-to-end, stability,
  multiset preservation), playlist-URL parsing, and ReccoBeats response parsing (including
  `content: []` / missing IDs). Network layers are kept thin and exercised via the
  `quickstart.md` end-to-end run.
- **Rationale**: The domain logic is where a bug would lose or misorder tracks; it is pure
  and cheaply property-testable. `just test` joins the quality workflow.
