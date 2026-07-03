# Contract: On-disk storage formats

Two JSON stores under the per-user config directory (`platformdirs.user_config_dir(
"spotify-playlist-sorter")`). Both are written **atomically** — serialise to a temp file in the
same directory, then `os.replace()` onto the target — so an interrupted save never corrupts the
previous file (FR-011). Files hold no secrets (the OAuth token is separate).

## `corrections.json` — global per-track corrections

```json
{
  "version": 1,
  "corrections": {
    "003vvx7Niy0yvhvHt4a68B": { "camelot": "2B", "bpm": 122.0 },
    "4cOdK2wGLETKBW3PvgPWqT": { "camelot": "8A", "bpm": 128.0 }
  }
}
```

- Keyed by **Spotify track id**; applies to that track in **any** playlist and to **every**
  occurrence of it (FR-010, FR-020).
- `camelot`: a valid Camelot code (1A–12B). `bpm`: a number > 0.
- On read, malformed *entries* (bad code, non-positive BPM, wrong shape) are ignored, not fatal.

## Arrangement — one file per playlist

Path derived from the playlist id (e.g. `arrangements/<playlist_id>.json`).

```json
{
  "version": 1,
  "playlist_id": "7GJjEfYeasKifQuXaOfheM",
  "order": ["<track_id_1>", "<track_id_2>", "…"],
  "pinned": [1]
}
```

- `order`: Spotify track ids in the saved arranged order (a duplicated track's id repeats).
- `pinned`: the **positions** (indices into `order`) the user has pinned — positions, not ids,
  so a specific occurrence of a duplicated track can be pinned unambiguously (FR-020).
- On read with a drifted playlist, reconcile per [data-model.md](../data-model.md): match
  surviving occurrences positionally, append new ids, keep pins on surviving occurrences, then
  `rebuild()`.

## Contract facts

- Each file carries a `version`; an unrecognised/incompatible version is treated as unreadable —
  a fresh start with the file preserved (FR-021, FR-019).
- **Atomic per file**: each store is written to a temp file then `os.replace`d. A save touches
  both files independently (not one transaction); a failed write leaves the prior file intact,
  and edits stay in memory (FR-018).
- A **missing** file means "no saved data" (fresh start); a **present-but-unparseable** file is
  preserved (set aside) and treated as empty, with a warning (FR-019).
- Corrections and arrangement are independent: deleting an arrangement keeps corrections; a
  correction outlives any single playlist and is retained indefinitely.
