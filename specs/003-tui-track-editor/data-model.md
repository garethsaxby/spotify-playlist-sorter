# Phase 1 Data Model: Interactive Track Editor

Runtime types (dataclasses in `models.py`) plus two persisted stores. Reuses feature 002's
`Track`, `CamelotKey`, `AudioFeatures`.

## Persisted entities

### Correction (global)
A user-supplied override for one track, reused wherever that track appears.
- key: `spotify_track_id: str`
- `camelot: str` — a valid Camelot code (1A–12B)
- `bpm: float` — > 0

Store: `corrections.json` = `{ "version": 1, "corrections": { "<spotify_id>": {"camelot": "8B",
"bpm": 120.0}, … } }` (top-level `version` per FR-021; shape pinned in
[contracts/storage.md](./contracts/storage.md)). Validation: `camelot` parses
to a `CamelotKey`; `bpm > 0`. Invalid entries are never written.

### Arrangement (per playlist)
The saved order and pin set for one source playlist.
- `version: int` — store format version (FR-021)
- `order: list[str]` — Spotify track ids in arranged order (a duplicated track's id repeats)
- `pinned: list[int]` — the **positions** (indices into `order`) that are pinned, so a specific
  occurrence of a duplicated track is unambiguous (FR-020)

Store: one file per playlist.

## Runtime entities

### EditableTrack
- `spotify_id: str`, `uri: str`, `title: str`, `artists: tuple[str, ...]`
- `source_position: int` — original index in the source playlist (stable tiebreaker)
- `camelot: CamelotKey | None`, `bpm: float | None` — resolved value (see precedence)
- `provenance: "corrected" | "estimated" | "unknown"`
- `pinned: bool`

**Value precedence** (highest first): user **Correction** → ReccoBeats **estimate** →
**unknown** (both `None`). A track is *sortable* iff both `camelot` and `bpm` are set.

### EditorState
- `playlist_id: str`, `source_name: str`
- `tracks: list[EditableTrack]` — the current arrangement (order matters)
- `dirty: bool` — unsaved changes present (set on any edit/move, cleared on save)

## The pin-aware ordering — `rebuild(tracks)`

Called after a **data edit/add** (not after a manual move, which only sets a pin). Non-pinned
tracks are (re)placed in Camelot→BPM order; pinned tracks keep their absolute index.

```text
rebuild(tracks: list[EditableTrack]) -> list[EditableTrack]:
    n = len(tracks)
    pinned_at = { index: t for index, t in enumerate(tracks) if t.pinned }   # absolute slots
    free = [t for t in tracks if not t.pinned]
    sortable   = [t for t in free if t.camelot is not None and t.bpm is not None]
    unsortable = [t for t in free if t.camelot is None or t.bpm is None]
    # sort_key(camelot, bpm, position) from sorter.py — never receives None; unsortable stay last (stable)
    free_sorted = sorted(sortable, key=lambda t: sort_key(t.camelot, t.bpm, t.source_position)) + unsortable
    result = [None] * n
    for index, t in pinned_at.items():            # place pins first
        result[index] = t
    it = iter(free_sorted)                         # fill remaining slots in order
    for index in range(n):
        if result[index] is None:
            result[index] = next(it)
    return result
```

`sort_key` is exactly feature 002's `(camelot.order, bpm, source_position)` with tracks lacking
data ordered last — **reused from `sorter.py`, not re-implemented**.

### Required properties (the highest-value unit tests)

1. **Multiset preserved** — `rebuild` output contains exactly the input tracks (0 lost, 0
   duplicated). Same invariant as 002's sorter and the export.
2. **Pins honoured** — every pinned track appears at the same index it held in the input.
3. **Non-pinned sorted** — reading only the non-pinned tracks in output order yields
   Camelot→BPM order (unsortable ones last), independent of the pins around them.
4. **Idempotent** — `rebuild(rebuild(tracks)) == rebuild(tracks)`.

### Move / pin / re-sort operations
- **Move a track** to index *k*: set `pinned = True`, place it at *k* (shifting others); the
  moved track is now a fixed pin. (A move does not trigger `rebuild`.)
- **Edit/add key or BPM**: update the track's value + `provenance = "corrected"`, then
  `rebuild` (the edited track flows to its sorted slot unless pinned). Also records a global
  `Correction`.
- **Full re-sort**: clear all pins, then `rebuild` → pure Camelot→BPM order (FR-006/FR-012).

## Drift reconciliation — opening a saved playlist whose tracks changed

```text
reconcile(current_tracks, saved_order, saved_pinned_positions, corrections) -> list[EditableTrack]:
    apply corrections + estimates to each current track  (precedence above)
    match saved_order entries to surviving occurrences positionally (by id, nth occurrence);
        drop entries whose track occurrence is gone
    order = surviving occurrences (in saved order) + newly-added occurrences appended
    pins  = saved_pinned_positions carried to their surviving occurrences (dropped if gone)
    build EditableTracks in `order`, mark the pinned occurrences, then rebuild()
```

Duplicate track ids are handled as distinct occurrences throughout (matched positionally on
reload); a `Correction` still keys on the track id and so applies to every occurrence (FR-020).

Because non-pinned tracks are always sorted, restoring the pin set and running `rebuild()`
reproduces the saved arrangement and slots any newly-added tracks into place — no bespoke merge
(FR-013). Removed tracks simply drop; their global corrections remain for future reuse.

## Flow

```text
edit <url> → auth → get_playlist (002) → reccobeats estimates (002)
   → load corrections + saved arrangement → reconcile()/initial rebuild()
   → Textual app: navigate / edit (modal) / move (pin) / re-sort / save / export
   → save: atomic write corrections.json + arrangement file (on explicit save)
   → export: create new playlist + add tracks in current order (002); source untouched
```
