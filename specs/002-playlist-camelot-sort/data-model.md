# Phase 1 Data Model: Harmonic Playlist Sort

These are in-memory domain types (no persistence except the token cache). Types map to
dataclasses in `src/spotify_playlist_sorter/models.py`. All are populated from validated
external responses.

## Entities

### Track
A source playlist entry.
- `spotify_id: str` — Spotify track ID (identity).
- `uri: str` — `spotify:track:{id}` (used when adding to the new playlist).
- `title: str`, `artists: list[str]` — for display.
- `position: int` — original 0-based index in the source (tie-break for stable order).
- `features: AudioFeatures | None` — `None` when ReccoBeats has no match → **unsortable**.

Validation: `spotify_id`/`uri` required and well-formed; a track with `features is None` is
routed to the unsortable group.

### AudioFeatures
ReccoBeats result for a track.
- `key: int` — pitch class 0–11.
- `mode: int` — 0 = minor, 1 = major.
- `tempo: float` — BPM (> 0).
- `camelot: CamelotKey` — derived from `key` + `mode`.

Validation: `0 <= key <= 11`, `mode in {0, 1}`, `tempo > 0`; if a result violates these it is
treated as unsortable rather than trusted.

### CamelotKey
- `number: int` — 1–12 (wheel position).
- `letter: str` — `"A"` (minor) or `"B"` (major).
- `code` (derived): f"{number}{letter}" (e.g. `"8B"`).

Ordering: `(number, 0 if letter == "A" else 1)` → 1A,1B,2A,2B,…,12B.

### ProposedOrder
Result of sorting, shown for review and (on confirm) written.
- `sortable: list[Track]` — ordered by `(camelot ordering, tempo, position)`.
- `unsortable: list[Track]` — original relative order, appended after `sortable`.
- `ordered` (derived): `sortable + unsortable` — the full new-playlist order.

Invariant: `multiset(ordered) == multiset(source tracks)` (FR-010) — no track added, dropped,
or duplicated.

### SourcePlaylist / NewPlaylist
- `SourcePlaylist`: `id`, `name`, `owner_id`, `tracks: list[Track]`. Read-only.
- `NewPlaylist`: `id`, `name`, `url` — created on confirm; `name` derived from the source
  (e.g. `"{source name} (Camelot sorted)"`).

### AuthToken (persisted)
- `refresh_token: str`, `client_id: str` (+ transient in-memory `access_token`, `expires_at`).
- Stored in a `0600` file under the per-user config dir; never logged (FR-017).

## State / Flow

```text
parse URL → authenticate → GET source (owner check FR-003, paginate tracks)
  → batch ReccoBeats audio-features (40/req) → derive Camelot
  → build ProposedOrder (sort + unsortable-to-end)
  → display table → confirm?
       ├─ no  → exit, nothing created (FR-011)
       └─ yes → create NewPlaylist → add URIs in order (100/req) → report summary (FR-016)
```

The source playlist is read-only throughout; only `NewPlaylist` is written (FR-009).

## Camelot mapping (key, mode) → code

| key | note | minor (mode 0) | major (mode 1) |
|----:|------|:--------------:|:--------------:|
| 0 | C | 5A | 8B |
| 1 | C#/Db | 12A | 3B |
| 2 | D | 7A | 10B |
| 3 | D#/Eb | 2A | 5B |
| 4 | E | 9A | 12B |
| 5 | F | 4A | 7B |
| 6 | F#/Gb | 11A | 2B |
| 7 | G | 6A | 9B |
| 8 | G#/Ab | 1A | 4B |
| 9 | A | 8A | 11B |
| 10 | A#/Bb | 3A | 6B |
| 11 | B | 10A | 1B |
