# Feature Specification: Harmonic Playlist Sort (Camelot Key + BPM)

**Feature Branch**: `002-playlist-camelot-sort`

**Created**: 2026-07-03

**Status**: Draft

**Input**: User description: "take a given spotify playlist URL that is owned by the logged in user, find the Camelot Key and BPM of each track, sort the tracks by camelot key and then BPM, show the suggested new order of tracks, and then when confirmed, write the playlist into the new order"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Preview a harmonically sorted order (Priority: P1)

A logged-in user points the tool at one of their own Spotify playlists (by URL). The tool
reads the playlist, determines each track's Camelot Key and BPM, computes a new order
sorted by Camelot Key and then BPM, and shows the suggested new order — **without changing
anything**. The user can see, track by track, how the playlist would be re-sequenced.

**Why this priority**: This read-only preview is the core value and the safest slice: it
delivers the harmonic-sorting insight a DJ/listener wants with zero risk to the playlist.
It is a complete, demonstrable MVP on its own — a user can decide the ordering is useful
even if they never apply it.

**Independent Test**: Provide the URL of an owned playlist with tracks that have known key
and tempo. The tool displays a proposed order in which tracks are grouped/ordered by
Camelot Key and, within a key, ascending by BPM — and the original playlist is verifiably
unchanged.

**Acceptance Scenarios**:

1. **Given** a logged-in user and a URL of a playlist they own, **When** they request a sort preview, **Then** the tool shows each track with its Camelot Key and BPM in the proposed new order, sorted by Camelot Key then BPM, and makes no change to the playlist.
2. **Given** a playlist URL the user does **not** own, **When** they request a preview, **Then** the tool refuses and explains that only playlists owned by the logged-in user can be sorted.
3. **Given** an invalid or non-playlist URL, **When** they request a preview, **Then** the tool reports the input is not a usable owned-playlist reference and makes no change.
4. **Given** the user is not authenticated (or the session has expired), **When** they request a preview, **Then** the tool prompts for/requires authentication before proceeding and makes no change.

---

### User Story 2 - Write the sorted order to a new playlist (Priority: P2)

After reviewing the suggested order, the user confirms, and the tool creates a **new**
playlist (owned by the user) containing the same tracks in the approved sorted order. The
source playlist is left completely untouched.

**Why this priority**: This is the "make it real" step that turns the preview into a
persisted, reusable "library" playlist. It depends on the preview (US1) existing and is
gated behind explicit confirmation. Writing to a new playlist (rather than reordering the
source) is non-destructive — the source can never be corrupted or lose tracks.

**Independent Test**: From a shown preview, confirm; afterwards a new playlist exists whose
track order matches the approved order and whose track set is exactly the source's tracks
(nothing added, dropped, or duplicated), and the source playlist is unchanged.

**Acceptance Scenarios**:

1. **Given** a displayed proposed order, **When** the user confirms, **Then** the tool creates a new playlist containing the tracks in the approved order and reports a success summary (including the new playlist's name/link).
2. **Given** a displayed proposed order, **When** the user declines or cancels, **Then** no new playlist is created and nothing is changed.
3. **Given** a confirmed sort, **When** the tool finishes, **Then** the new playlist contains exactly the same track multiset as the source (same count and membership), only ordered differently, and the source playlist is unchanged.
4. **Given** creating or populating the new playlist fails partway, **When** the failure occurs, **Then** the source playlist is never affected, and the tool reports the failure clearly (identifying the incomplete new playlist so it can be retried or removed).

---

### User Story 3 - Graceful handling of tracks without key/BPM data (Priority: P3)

Some items in a playlist may have no determinable Camelot Key or BPM (for example, local
files, podcast episodes, or tracks with no available audio analysis). The tool completes
the sort anyway, keeping these items rather than dropping them, and clearly identifies
which ones could not be placed by key/BPM.

**Why this priority**: Real playlists are messy; the feature must not fail wholesale because
a few items lack data. This makes the tool trustworthy on real-world playlists but is
secondary to the core sort and apply flow.

**Independent Test**: Preview a playlist that mixes tracks with known key/BPM and items
without. The proposed order sorts the known tracks by Camelot Key then BPM and groups the
undeterminable items together (clearly flagged), and the operation completes without error.

**Acceptance Scenarios**:

1. **Given** a playlist where some tracks lack Camelot Key or BPM, **When** a preview is generated, **Then** sortable tracks are ordered by Camelot Key then BPM and the undeterminable items are grouped together at the end, clearly marked as unsorted.
2. **Given** such a playlist, **When** the user applies the order, **Then** every track — including the undeterminable ones — is still present in the resulting playlist.
3. **Given** a playlist where **no** track has determinable key/BPM, **When** a preview is requested, **Then** the tool reports that it cannot produce a harmonic ordering and makes no change.

---

### Edge Cases

- **Not owned / collaborative**: Playlist owned by another user (including collaborative playlists the user did not create) → refused with a clear message.
- **Invalid input**: URL that is malformed, not a playlist, or references an inaccessible/deleted playlist → reported, no change.
- **Auth expiry mid-flow**: Session expires between preview and apply → the apply step re-checks authentication and does not proceed on an expired session.
- **Empty or single-track playlist**: Nothing to reorder → tool reports there is nothing to sort and makes no change.
- **All tracks identical in sort keys**: Every track shares the same Camelot Key and BPM → order is effectively unchanged (stable), reported as such.
- **Ties**: Two tracks with the same Camelot Key and BPM → their original relative order is preserved (stable sort).
- **Large playlists**: Playlists with many tracks (beyond a single page of results) are fully read and fully reordered.
- **Concurrent modification**: The source is changed by another client between preview and confirmation → since the tool only reads the source and writes a separate new playlist, no data can be lost; the tool may note the source changed and suggest re-running for current contents.
- **Duplicate tracks**: The same track appearing multiple times is preserved (count unchanged) and ordered consistently.
- **Analysis provider gaps/outage**: A track has no match or no analysis in ReccoBeats → treated as unsortable (grouped at end). A full provider outage → reported; if nothing can be sorted, no change is made (per FR-013).

## Clarifications

### Session 2026-07-03

- Q: Where should each track's Camelot Key and BPM come from? → A: From ReccoBeats (reccobeats.com), a third-party audio-analysis API that returns audio features for Spotify tracks (the approach used by the referenced `spotify-playlist-analyzer` project). Tracks ReccoBeats cannot match or analyse are treated as unsortable.
- Q: What kind of application is this? → A: A command-line (CLI) tool — the user runs a command with the playlist URL, reviews the proposed order in the terminal, and confirms via a terminal prompt.
- Q: How should the Camelot keys be ordered? → A: Camelot number ascending then letter (1A, 1B, 2A, 2B, …, 12B), BPM ascending within each key (e.g. 1A → 125, 150, 190; 1B → 80, 90, 112). The output is a sorted "library" playlist to browse and pick tracks from — not intended for continuous/direct listening — so no harmonic/energy-path ordering.
- Q: How should the user's Spotify OAuth token be handled between runs? → A: Cache the OAuth refresh token in a gitignored, user-only-readable local config file so the user logs in once.
- Q: When the user confirms, where is the sorted order written? → A: To a NEW playlist (a copy) in the sorted order; the source playlist is left untouched (non-destructive). This replaces the earlier "reorder in place" wording.
- Q: Will the playlists contain local files or podcast episodes? → A: No — Spotify catalog tracks only (as required for the downstream Soundtrack.io licensing workflow), so copying tracks into a new playlist is fully lossless.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST accept a Spotify playlist reference (URL) as input and resolve it to a specific playlist.
- **FR-002**: The system MUST require the user to be an authenticated Spotify user before performing any read or write action.
- **FR-003**: The system MUST verify the target playlist is owned by the logged-in user and MUST refuse to proceed (with a clear explanation) for any playlist the user does not own.
- **FR-004**: The system MUST retrieve the complete, ordered list of tracks in the playlist, regardless of playlist size.
- **FR-005**: For each track, the system MUST determine its BPM (tempo) and its musical key/mode — from which the Camelot Key is derived — by retrieving audio features from the ReccoBeats API (reccobeats.com), where such data is available.
- **FR-006**: The system MUST compute a proposed track order sorted primarily by Camelot Key and secondarily by ascending BPM, using a deterministic, documented ordering (see Assumptions).
- **FR-007**: The system MUST present the proposed new order to the user in the terminal for review before any change is made, showing per-track detail sufficient to evaluate it (at minimum: proposed position, track identity, Camelot Key, and BPM).
- **FR-008**: The system MUST NOT create the new playlist unless the user explicitly confirms — either via the terminal prompt after the proposed order is shown, or via an explicit non-interactive pre-consent flag (`--yes`). The proposed order is always shown before any write; an explicit `--yes` is itself a confirmation, so SC-003 ("no unconfirmed writes") still holds.
- **FR-009**: Upon explicit confirmation, the system MUST create a new playlist owned by the user containing the tracks in the approved order; the system MUST NOT modify the source playlist.
- **FR-010**: The new playlist MUST contain the exact multiset of tracks from the source — no track added, dropped, or duplicated — differing only in order.
- **FR-011**: If the user declines or cancels at the confirmation step, the system MUST make no change to the playlist.
- **FR-012**: The system MUST handle tracks whose Camelot Key and/or BPM cannot be determined without aborting the whole operation: such items MUST be retained and grouped together at the end of the proposed order, clearly flagged ("unsortable" internally; shown to the user as "unsorted").
- **FR-013**: If **no** track has a determinable Camelot Key/BPM, the system MUST report that a harmonic ordering cannot be produced and make no change.
- **FR-014**: On a write failure or interruption while creating/populating the new playlist, the system MUST NOT affect the source playlist, and MUST report the failure clearly (identifying the incomplete new playlist so it can be retried or removed).
- **FR-015**: The approved order reflects the source playlist as read during the run. Because the source is never modified, concurrent changes cannot cause data loss. The tool operates on that single read and does not re-read to detect concurrent edits — re-running picks up current contents.
- **FR-016**: The system MUST report a clear outcome — a success summary after applying (e.g., how many tracks were reordered and how many were left unsorted) and actionable error messages on any failure.
- **FR-017**: The system MUST NOT expose the user's authentication credentials in its output or logs. It MAY cache the OAuth refresh token to avoid re-authenticating every run, but only in a local, user-only-readable file that is excluded from version control.
- **FR-018**: The system MUST match each Spotify track to its ReccoBeats audio features; a track with no ReccoBeats match or analysis MUST be treated as unsortable (per FR-012) rather than causing the operation to fail, and the system MUST handle provider errors and rate limits gracefully.
- **FR-019**: If the source playlist contains fewer than 2 tracks, the system MUST report that there is nothing to sort and make no change (no new playlist is created).

### Non-Functional / Quality Requirements

- **NFR-001**: Preview (read + analyse + sort) MUST be fast enough for interactive use (target: a 100-track playlist previewed in under 60 seconds — see SC-006).
- **NFR-002**: Output MUST be actionable — each track shows its Camelot Key and BPM, and every unsortable or not-found track is clearly identified with the reason.

### Key Entities *(include if feature involves data)*

- **User (playlist owner)**: The authenticated Spotify account operating the tool. Only playlists owned by this user are eligible for sorting.
- **Playlist**: The target playlist identified by the supplied URL; has an owner and an ordered list of track entries.
- **Track**: An entry in the playlist. Attributes relevant here: identity (title, artist), musical key, mode (major/minor), tempo (BPM), and a derived Camelot Key. A track may be "unsortable" when key and/or BPM are unavailable.
- **Camelot Key**: A harmonic-mixing code (1A–12B) derived from a track's musical key and mode using the standard Camelot Wheel mapping; the primary sort dimension.
- **Proposed Order**: The computed, deterministic sequence of tracks (sorted by Camelot Key then BPM, with unsortable items grouped at the end) that is shown for review and, once confirmed, applied to the playlist.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For an owned playlist, a user can view a proposed harmonically sorted order with the original playlist left 100% unchanged (no writes occur during preview).
- **SC-002**: The proposed order is correctly sorted: for any two consecutive sortable tracks, the earlier track's Camelot Key does not come after the later track's, and within the same Camelot Key, BPM is non-decreasing — verified on 100% of preview runs.
- **SC-003**: No playlist is ever modified without an explicit user confirmation (0 unconfirmed writes across all runs).
- **SC-004**: After a confirmed sort, the new playlist contains exactly the same set and count of tracks as the source — 0 tracks lost, added, or duplicated — and the source playlist is unchanged.
- **SC-005**: Attempting to sort a playlist the user does not own is refused with a clear message 100% of the time, with no change made.
- **SC-006**: A user can generate a preview for a 100-track owned playlist and see the proposed order in under 60 seconds.
- **SC-007**: Playlists containing items without determinable key/BPM still complete successfully, with 100% of such items retained and clearly identified as unsorted.
- **SC-008**: On a simulated write failure, the source playlist is unaffected in 100% of cases, and the failure is reported (with the incomplete new playlist identified).

## Assumptions

- **Camelot derivation**: Each track's Camelot Key is derived from its musical key and mode (major/minor) using the standard Camelot Wheel mapping.
- **Sort ordering**: Camelot Keys are ordered by ascending wheel number (1 → 12), and within a number the minor code ("A") precedes the major code ("B") — i.e. 1A, 1B, 2A, 2B, …, 12A, 12B. BPM ascending is the secondary key (e.g. 1A → 125, 150, 190; 1B → 80, 90, 112). Exact ties (same Camelot Key and BPM) preserve the tracks' original relative order (stable). This literal "Camelot then BPM" ordering is used rather than an energy-based harmonic-mixing path.
- **Purpose**: The sorted playlist is a reference "library" the user browses and picks tracks from, not a set intended for continuous/direct listening — which is why a flat Camelot-then-BPM sort (not a harmonic transition path) is the goal.
- **Output playlist (copy)**: "Write the playlist into the new order" is implemented non-destructively as a **new** playlist containing the tracks in sorted order; the source playlist is never modified.
- **No local files**: Sorted playlists contain only Spotify catalog tracks (no local files or podcast episodes), so every track can be copied into the new playlist without loss.
- **New playlist naming**: The new playlist is given a clear, derived name (e.g. the source playlist's name plus a "Camelot sorted" marker); exact naming/description is a design detail.
- **Unsortable items**: Tracks/items without a determinable Camelot Key or BPM (e.g., local files, podcast episodes, tracks lacking audio analysis) are kept and grouped at the end of the proposed order, clearly flagged — never dropped.
- **Ownership & authorization**: The user has authenticated with Spotify and authorized the tool to read and modify their playlists; the tool only ever acts on the user's own account and owned playlists.
- **Audio data dependency**: Per-track musical key and tempo (BPM) data is sourced from the ReccoBeats API (reccobeats.com), which provides audio features for Spotify tracks (replacing Spotify's restricted audio-features endpoint). Tracks ReccoBeats cannot match or analyse are treated as unsortable. The project has no integration with this API yet — building it is part of this feature.
- **Interaction model**: The tool is a command-line (CLI) application. The user supplies the playlist URL as input, the proposed order is printed to the terminal, and an explicit confirm/decline prompt precedes any write.
- **Credential storage**: The user authenticates once via Spotify OAuth; the refresh token is cached in a local, user-only-readable config file excluded from version control, so subsequent runs do not require re-authentication.
- **Out of scope**: Energy-/transition-based harmonic sequencing beyond the literal Camelot-then-BPM sort; modifying the source playlist's order in place; changing any track metadata; managing or curating the downstream final tracklist; undo/history of previous sorts.
