# Contract: `edit` command + TUI key actions

Adds one command to the existing CLI (`login`, `sort`, and now `edit`).

## `edit <playlist>`
Open a playlist in the interactive editor.

- **Input**: `<playlist>` — Spotify playlist URL, URI, or id (same parser as `sort`).
- **Preconditions**: logged in (exit 3 if not); playlist owned by the user (exit 4 if not);
  parseable reference (exit 2 if not) — same guards as `sort`.
- **Behaviour**: authenticate → read the playlist → fetch ReccoBeats estimates → apply saved
  global corrections and the saved arrangement (reconcile on drift) → launch the Textual editor.
- **Exit 0**: the user quits the editor (after optionally saving/exporting).
- **Exit 7**: the playlist has fewer than 2 tracks — nothing to arrange (`_EXIT_TOO_FEW`,
  matching `sort`; note `5` is already `_EXIT_NOTHING_SORTABLE`).
- Other non-zero: same auth/input/ownership/error codes as `sort`.

## In-editor key actions (contract of behaviours, not exact keybindings)

| Action | Effect |
|--------|--------|
| Navigate | Move the row cursor up/down through the track list |
| Edit key/BPM | Open a modal to set the selected track's Camelot code + BPM; validated (1A–12B, BPM > 0); on accept the track re-places by sort (unless pinned) and a global correction is recorded; marks state dirty |
| Add key/BPM | Same modal for an "unknown" track; on accept it becomes sortable and joins the order |
| Move track | Move the selected track to a chosen position (an arbitrary target index, not only one step); the track becomes **pinned** at that index; marks state dirty |
| Full re-sort | Clear all pins and re-order purely by Camelot→BPM; requires explicit confirmation first (FR-027); marks state dirty |
| Save | Atomically write `corrections.json` + the playlist arrangement; clears dirty |
| Export | Create a **new** Spotify playlist with the current order (reuses feature 002 create+add); source unchanged; reports the new playlist URL |
| Quit | If dirty, prompt **save / discard / cancel**; never lose edits silently |

## Invariants (map to spec)

- No estimate/correction is ever written to Spotify — export carries only track order (FR-014).
- Export preserves the exact track multiset of the source; source is untouched (FR-015, SC-006).
- A quit with unsaved changes always prompts (FR-016, SC-007).
- Invalid Camelot/BPM input is rejected and never stored (FR-005, SC-005).
- Corrections persist globally and auto-apply to the same track in other playlists (FR-010, SC-004).
- Camelot input is accepted case-insensitively and normalised (`8b` → `8B`); BPM accepts decimals (FR-022).
- Provenance (corrected/estimated/unknown) and pinned status are shown with distinct, non-colour-only markers (FR-023).
- Available actions/keys are discoverable in-editor (legend or help); open and export show progress feedback (FR-024, FR-026).
- Save and export report their outcome — success (export includes the new playlist link) or a clear failure (FR-025).
