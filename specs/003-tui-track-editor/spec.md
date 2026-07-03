# Feature Specification: Interactive Track Editor (TUI)

**Feature Branch**: `003-tui-track-editor`

**Created**: 2026-07-03

**Status**: Draft

**Input**: User description: "add a TUI interface that allows for individual tracks to have their BPM and Camelot Key changed, or added if it is missing, and then have the new structure of the playlist saved locally, and allow it to continue to be exported out to Spotify"

## User Scenarios & Testing *(mandatory)*

Context: The existing tool (feature 002) auto-sorts a playlist by Camelot key then BPM using
estimated data from a third-party analyser, which is sometimes wrong (major/minor errors)
and missing for some tracks. This feature adds a human-in-the-loop editor: the user corrects
or supplies the harmonic data themselves, arranges the result, keeps that work locally, and
still exports the ordering to a new Spotify playlist.

### User Story 1 - Correct or add a track's Camelot key and BPM (Priority: P1)

Opening a playlist in an interactive terminal interface, the user sees every track with its
current Camelot key and BPM. For a track whose key is wrong (e.g. shown as 11A when it is
actually 2B) they edit it; for a track with no data (an "unknown" the analyser missed) they
type in the key and BPM. The arrangement updates to reflect the corrected values.

**Why this priority**: This is the core value and the whole point of the pivot — the user,
not an imperfect estimator, is the source of truth for harmonic data. It is independently
useful even before persistence or export exist: a user can review and fix an ordering in one
session.

**Independent Test**: Open a playlist with at least one mis-keyed track and one unknown
track. Edit the mis-keyed track's Camelot key and edit the unknown track's key + BPM;
observe both take valid values and the ordering re-place them correctly, with clear
rejection of any invalid entry.

**Acceptance Scenarios**:

1. **Given** a track showing an incorrect Camelot key, **When** the user edits it to a valid code, **Then** the track's key updates and its position in the arrangement reflects the new value.
2. **Given** a track with no key/BPM (unknown), **When** the user enters a valid Camelot key and BPM, **Then** the track becomes sortable and joins the ordered arrangement.
3. **Given** the user enters an invalid Camelot key (not 1A–12B) or a non-positive/non-numeric BPM, **When** they confirm the edit, **Then** the input is rejected with a clear message and no invalid value is stored.
4. **Given** a track's data came from the estimator, **When** the user overrides it, **Then** the user's value takes precedence and is visibly marked as user-corrected.

---

### User Story 2 - Save the edited structure locally (Priority: P2)

The user saves their corrections and the current arrangement so the work is not lost and does
not have to be repeated. Reopening the same playlist restores everything.

**Why this priority**: Manual correction is only worthwhile if it persists; without saving,
every session starts from the flawed estimates again. Explicitly requested.

**Independent Test**: Correct several tracks, save, quit, reopen the same playlist — every
correction and the arrangement are restored exactly.

**Acceptance Scenarios**:

1. **Given** unsaved corrections and an arrangement, **When** the user saves, **Then** the corrections and order are written to local storage durably.
2. **Given** a previously-saved playlist, **When** the user reopens it, **Then** the saved corrections and arrangement are reloaded and applied.
3. **Given** a track corrected in one playlist, **When** the same track appears in a different playlist, **Then** the saved correction is applied automatically.
4. **Given** the playlist's tracks changed on Spotify since the last save, **When** the user reopens it, **Then** corrections for still-present tracks are kept, newly-added tracks appear editable, and removed tracks drop from view — without losing other saved data.

---

### User Story 3 - Export the arrangement to a new Spotify playlist (Priority: P3)

Satisfied with the arrangement, the user exports it to a new Spotify playlist so it can be
used downstream (e.g. imported into their licensing/mixing workflow). The source is untouched.

**Why this priority**: This is how the curated result leaves the tool. It reuses the existing
non-destructive export; it depends on there being an arrangement to export (US1).

**Independent Test**: From an arranged playlist, export; a new Spotify playlist appears with
the same track set in the arranged order, and the source playlist is unchanged.

**Acceptance Scenarios**:

1. **Given** a current arrangement, **When** the user exports, **Then** a new Spotify playlist is created with the tracks in that exact order and the source is unchanged.
2. **Given** the export completes, **When** the user checks the new playlist, **Then** it contains exactly the same track multiset as the source (nothing added, dropped, or duplicated).
3. **Given** the user's local corrections, **When** exporting, **Then** only the track order is written to Spotify (Camelot/BPM corrections remain local, as Spotify does not store them).

---

### User Story 4 - Manually arrange the order (Priority: P4)

Beyond key/BPM correction, the user can move individual tracks to a chosen position to
arrange "by feel", overriding the automatic Camelot-then-BPM order. The manual arrangement is
what gets saved and exported.

**Why this priority**: The user curates harmonically "based on feel"; a manual override
completes the human-in-the-loop control. Secondary to getting the data right (US1).

**Independent Test**: Move a track from the bottom to a specific position; it stays there
through save and export.

**Acceptance Scenarios**:

1. **Given** an ordered list, **When** the user moves a track to a new position, **Then** the arrangement reflects the manual order and retains it.
2. **Given** a manually arranged order, **When** the user saves and exports, **Then** the saved and exported order match the manual arrangement.
3. **Given** a manual arrangement with pinned tracks, **When** the user explicitly requests a full re-sort by Camelot/BPM, **Then** the arrangement is regenerated from the corrected data and all manual pins are cleared.

---

### Edge Cases

- **Invalid input**: Camelot key not in 1A–12B, or BPM non-numeric/≤0 → rejected with feedback; nothing stored.
- **Unknown tracks**: tracks with no estimator data show blank key/BPM and are fully editable.
- **Playlist drift**: tracks added/removed on Spotify between sessions → saved corrections merge with the current track list (kept for present tracks, blank for new, removed ones dropped).
- **Quit with unsaved changes**: the user is always prompted to save or discard — edits are never lost silently.
- **Empty or single-track playlist**: fewer than two tracks → the tool reports "nothing to arrange" and exits without entering the editor.
- **No estimates at all**: the estimator returns nothing for any track → the editor still opens with every track marked unknown and fully editable.
- **Large playlist**: a few hundred tracks remain scrollable and editable without the interface becoming unusable.
- **Not authenticated / not owned**: same guards as the existing tool — must be logged in; only owned playlists (source) are read; the export target is a new owned playlist.
- **Corrupt / unreadable local store**: a store file exists but cannot be parsed → treated as "no saved data" (fresh start), the user is warned, and the unreadable file is preserved (set aside), never silently overwritten.
- **Save failure**: a save fails (disk full, permission denied, non-writable config directory) → the user is told, the in-memory edits are kept (state remains unsaved), and the previously-saved data on disk is left intact.
- **Duplicate track in a playlist**: the same track appearing more than once is treated as distinct occurrences for ordering and pinning; a Camelot/BPM correction applies to the track id and therefore to every occurrence.

## Clarifications

### Session 2026-07-03

- Q: When tracks are arranged and a track's key/BPM is edited, how does the order behave? → A: Tracks auto-place by Camelot key then BPM (so fixing an unknown's key slots it into position), EXCEPT tracks the user has explicitly moved, which are "pinned" and retain their manual position.
- Q: What is saved locally? → A: Per-track Camelot/BPM corrections saved globally (auto-applied to that track in any playlist) plus the per-playlist arrangement, including pinned positions.
- Q: How does saving work? → A: Explicit save; quitting with unsaved changes prompts save / discard / cancel (no auto-save).
- Q: On export after editing, what happens to the Spotify playlist? → A: Always create a new playlist (non-destructive); re-exporting after further edits creates an additional new playlist — the tool does not update a previously-exported one.
- Q: Which framework builds the TUI? → A: Textual — chosen for consistency with the existing `rich` dependency (same authors), its type support (fits the strict-`ty` gate), and its fit for an interactive, scrollable, editable track list. Recorded as a confirmed technical decision and carried into the plan; the functional requirements remain framework-agnostic.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide an interactive terminal interface listing a playlist's tracks with each track's Camelot key and BPM.
- **FR-002**: The interface MUST open with tracks in the auto-sorted order (Camelot key then BPM) from the existing sort, with estimator data and any previously-saved corrections already applied.
- **FR-003**: The user MUST be able to edit an existing track's Camelot key and/or BPM.
- **FR-004**: The user MUST be able to add a Camelot key and BPM to a track that has none.
- **FR-005**: The system MUST validate edits — Camelot key is a valid wheel code (1A–12B); BPM is a positive number — and reject invalid input with a clear message, storing nothing invalid.
- **FR-006**: Tracks MUST be placed automatically by Camelot key then BPM, so editing or adding a track's data moves it to its correct position — EXCEPT tracks the user has explicitly moved ("pinned", mechanics in FR-012), which retain their manual position and are not auto-placed.
- **FR-007**: A user correction MUST take precedence over estimator data and be visibly distinguishable as user-supplied.
- **FR-008**: The user MUST be able to save the current corrections and arrangement to durable local storage.
- **FR-009**: On reopening the same playlist, the system MUST reload and apply the saved corrections and arrangement.
- **FR-010**: Saved Camelot/BPM corrections MUST be reusable for the same track wherever it appears (keyed by track identity, not by playlist).
- **FR-011**: The system MUST NOT lose saved corrections or arrangement on interruption or crash.
- **FR-012**: The user MUST be able to manually move a track to any chosen position (an arbitrary target index, not only one step at a time); a manually-moved track becomes "pinned" and retains its position (it is not re-placed by later edits or auto-placement) until the user moves it again, un-pins it, or performs an explicit full re-sort. Pinned positions MUST be preserved in the save and the export.
- **FR-013**: When a playlist's tracks have changed on Spotify since the last save, the system MUST merge: keep corrections for still-present tracks, present new tracks as editable (placed by the auto-sort, as non-pinned), and drop removed tracks — without losing unrelated saved data.
- **FR-014**: Corrections and arrangement MUST be stored locally only; the Spotify export MUST carry only the track order (not the harmonic data).
- **FR-015**: The user MUST be able to export the current arrangement to a new Spotify playlist, non-destructively (source unchanged), reusing the existing export behaviour. Each export creates a new playlist; the tool does not update a previously-exported playlist. A failed or partial export does not alter the local corrections or arrangement.
- **FR-016**: The user MUST be able to quit, and any unsaved changes MUST be surfaced explicitly (save or discard) so edits are never lost silently. An unsaved-changes state exists after any edit, add, move/pin, or full re-sort, and is cleared only by a successful save.
- **FR-017**: The interface MUST remain responsive (scroll and edit) for playlists of at least a few hundred tracks — once data is loaded, navigation and edits are reflected with no perceptible lag (under ~100 ms, per SC-008); the initial data fetch may take longer but MUST show progress (FR-026).
- **FR-018**: Each local store MUST be written atomically (individually all-or-nothing). If a save fails, the system MUST report it clearly, retain the in-memory edits (state remains unsaved), and leave the previously-saved data intact. The two stores are written independently; a save is not a single cross-file transaction, but neither file is ever left partially written, and a re-save reconciles them.
- **FR-019**: On opening, a present-but-unreadable store MUST be treated as "no saved data" (a fresh start) with a warning to the user, and the unreadable file MUST be preserved (set aside) rather than silently overwritten.
- **FR-020**: A track appearing multiple times in a playlist MUST be treated as distinct occurrences for ordering and pinning; a Correction applies to the track id and therefore to all of its occurrences.
- **FR-021**: Each store MUST carry a format version so future format changes can be migrated; an unrecognised or incompatible version MUST be handled without data loss (treated as unreadable, per FR-019).
- **FR-022**: The interface MUST accept Camelot key input case-insensitively and normalise it to the canonical form `<number><A|B>` (e.g. `8b` → `8B`); BPM input MUST accept a positive number with optional decimals. Anything outside these forms is rejected per FR-005.
- **FR-023**: Each track's data provenance (user-corrected / estimated / unknown) and its pinned status MUST be indicated by a distinct, non-colour-only marker (symbol or text label), so the states are unambiguously distinguishable — including for colour-blind users and in terminals without colour.
- **FR-024**: The available actions and their key bindings MUST be discoverable from within the interface (e.g. a persistent legend or a help view).
- **FR-025**: Save and export outcomes MUST be reported: a success confirmation on save; on export, a success confirmation with a reference to the newly-created playlist; and a clear message on any failure.
- **FR-026**: While fetching the playlist and estimates on open, and while exporting, the interface MUST show progress/loading feedback rather than appearing frozen.
- **FR-027**: A full re-sort clears all pinned positions; the system MUST require explicit user confirmation before performing it.
- **FR-028**: Opening a playlist with fewer than two tracks MUST report a clear "nothing to arrange" message and exit without entering the editor (there is nothing to order).
- **FR-029**: When no estimator data is available for any track (all unknown), the editor MUST still open with every track shown as unknown and fully editable.

### Key Entities *(include if feature involves data)*

- **Editable Track**: a playlist track with identity (title, artists, Spotify id), a Camelot key, a BPM, a data provenance (estimated / user-corrected / unknown), and a pinned flag (whether the user has fixed its position).
- **Correction**: a user-supplied Camelot key + BPM for a track, keyed by track identity, persisted globally and reused across playlists; it applies to every occurrence of that track id (including duplicates).
- **Arrangement**: the ordered list of tracks for a specific playlist (auto-placed by Camelot/BPM with any user-pinned positions), persisted per source playlist and used for export. Each occurrence of a duplicated track is a distinct entry (matched positionally on reload). Carries a format version.
- **Local store**: the durable, per-user local persistence holding corrections and arrangements.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can correct a wrong Camelot key and see the track re-placed in the arrangement within a couple of seconds, with no other data lost.
- **SC-002**: 100% of previously-unknown tracks given a valid key + BPM become sortable and join the arrangement.
- **SC-003**: After quitting and reopening an unchanged playlist, 100% of saved corrections and the arrangement are restored; if the playlist drifted, corrections and arrangement for still-present tracks are restored and new tracks are placed by auto-sort.
- **SC-004**: A track corrected once is automatically applied when it later appears in a different playlist (correction reuse verified).
- **SC-005**: 100% of invalid Camelot/BPM entries are rejected with clear feedback and never stored.
- **SC-006**: Exporting produces a new Spotify playlist containing exactly the same track multiset as the source (0 lost/added/duplicated), in the arranged order, with the source unchanged.
- **SC-007**: No user edit is lost on quit — unsaved changes are surfaced 100% of the time (0 silent data loss).
- **SC-008**: On a 200-track playlist, navigation and edit actions are reflected in under ~100 ms (no perceptible lag), and the interface never freezes during the initial fetch (progress is shown throughout).
- **SC-009**: A simulated interrupted save or a corrupt store file never destroys previously-saved data — the prior file remains recoverable in 100% of cases — and the user is informed (0 silent store-level losses).

## Assumptions

- **Builds on feature 002**: reuses the existing playlist read, Camelot mapping, sorter, Spotify (PKCE) auth, and non-destructive "create new playlist" export. This feature adds the interactive editor and local persistence on top.
- **Interaction model**: an interactive terminal (TUI) application, as explicitly requested. The framework is **Textual** (confirmed 2026-07-03) — consistent with the existing `rich` dependency (same authors), typed for the strict-`ty` gate, and well-suited to an editable track list. Functional requirements remain framework-agnostic; the plan formalizes this choice.
- **What "saved locally" means**: per-track Camelot/BPM **corrections** (reusable across playlists, keyed by track identity) plus the per-playlist **arrangement** (order), stored in a per-user local data location.
- **Correction retention**: global corrections are retained indefinitely (no automatic cleanup, including for tracks no longer in any playlist) — acceptable given their small per-track size.
- **Single editor at a time**: the tool assumes one running instance for a given user. Concurrent instances editing the same stores are out of scope; atomic per-file writes prevent corruption, but the last successful save wins (an earlier instance's unsaved changes may be silently overwritten).
- **Personal scale**: the stores hold a personal library — up to a few thousand global corrections and per-playlist arrangements of a few hundred tracks. No explicit scale limits, sharding, or indexing are required; whole-file read/write per save is acceptable at this size.
- **Terminal capability**: assumes a modern terminal of reasonable size (roughly ≥80×24) with Unicode support; colour is enhancement-only (state markers never depend on it, per FR-023). Below a usable size the interface should advise or degrade gracefully rather than corrupt its layout.
- **Spotify has no harmonic data**: Spotify does not store Camelot key or BPM, so "export to Spotify" writes only the track **order** to a new playlist; corrections stay local.
- **Precedence**: user corrections override estimator data. Tracks auto-place by Camelot-then-BPM; explicitly-moved tracks are pinned and keep their position until moved again or an explicit full re-sort (which clears all pins) is invoked.
- **Save model default**: the user saves explicitly, and is prompted on quit if there are unsaved changes (auto-save is not assumed).
- **Streaming-only context**: the user has no local audio files, so importing harmonic data from a DJ library (Mixed In Key / Rekordbox) is **out of scope** here — manual correction is the accuracy mechanism.
- **Out of scope**: improving estimator accuracy automatically; DJ-library import; editing track metadata on Spotify; audio playback/preview; sharing corrections between users; in-list search / jump-to-track (scroll and cursor navigation suffice at the target size).
