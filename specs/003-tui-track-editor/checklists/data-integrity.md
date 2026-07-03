# Data Integrity Checklist: Interactive Track Editor (TUI)

**Purpose**: Validate that the *requirements* governing local persistence, saving, reload, and
data safety are complete, clear, consistent, and measurable — before implementation.
**Created**: 2026-07-03
**Feature**: [spec.md](../spec.md)

**Note**: These are "unit tests for the requirements" — each item checks whether the spec is
written well for data integrity, not whether code works.

## Requirement Completeness

- [x] CHK001 Are requirements defined for reading a **whole-file corrupted or partially-written** store, distinct from ignoring individual malformed entries? [Completeness, Gap]
- [x] CHK002 Is the outcome of a **failed save** (disk full, permission denied, read-only config dir) specified — what the user is told and what state remains? [Completeness, Gap, Spec §FR-011]
- [x] CHK003 Is atomicity specified **across both stores** (corrections + arrangement) — is a save that touches both all-or-nothing, or independent per file? [Completeness, Ambiguity]
- [x] CHK004 Are requirements defined for **orphaned corrections** (a corrected track no longer in any playlist) — retention, cleanup, or unbounded growth? [Completeness, Gap]
- [x] CHK005 Is an on-disk **format version / migration** requirement stated so future format changes cannot silently drop or corrupt saved data? [Completeness, Gap]

## Requirement Clarity

- [x] CHK006 Is "durable / MUST NOT lose saved data on interruption" expressed as a verifiable property (prior saved state always recoverable) rather than a mechanism? [Clarity, Spec §FR-011]
- [x] CHK007 Is "unsaved changes" defined precisely — exactly which actions set the dirty state and which clear it? [Clarity, Spec §FR-016]
- [x] CHK008 Does the drift-merge requirement unambiguously state **where newly-added tracks land** in a reloaded arrangement? [Clarity, Spec §FR-013]
- [x] CHK009 Is correction precedence clear when a saved correction and a fresh estimate **disagree** for the same track? [Clarity, Spec §FR-010]

## Requirement Consistency

- [x] CHK010 Are the "corrections global" and "arrangement per-playlist" requirements consistent about the **identity key** used for each store? [Consistency, Spec §FR-010]
- [x] CHK011 Is "export carries only track order, not harmonic data" consistent with the exact-multiset export requirement? [Consistency, Spec §FR-014]

## Acceptance Criteria Quality (Measurability)

- [x] CHK012 Can "0 silent data loss" be objectively verified — is the complete set of change-triggers enumerable? [Measurability, Spec §SC-007]
- [x] CHK013 Is "100% of saved corrections and arrangement restored" measurable **under drift**, where some saved tracks are gone? [Measurability, Spec §SC-003]
- [x] CHK014 Is there a stated, testable criterion for "no corruption on interrupted save" (e.g., the prior file remains intact)? [Measurability, Spec §FR-011]

## Scenario & Edge Coverage

- [x] CHK015 Are requirements defined distinguishing **missing** store (fresh start) vs **corrupt** store vs **valid** store on open? [Coverage, Gap]
- [x] CHK016 Is a track appearing **multiple times in one playlist** (duplicate ids) specified for corrections, order, and pinning? [Edge Case, Gap]
- [x] CHK017 Is the interaction between a **partially-failed export** and local saved state specified (local state unaffected)? [Coverage, Spec §FR-015]
- [x] CHK018 Are **concurrent-editor** scenarios (two instances editing the same stores) specified or explicitly declared out of scope? [Coverage, Gap]

## Dependencies & Assumptions

- [x] CHK019 Is the assumption that the config directory is **writable** validated, with defined behavior if it is not? [Assumption, Gap]
- [x] CHK020 Is **scale** addressed — many playlists / thousands of global corrections — or explicitly assumed small? [Assumption, Gap]
