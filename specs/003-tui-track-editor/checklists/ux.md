# TUI UX Checklist: Interactive Track Editor (TUI)

**Purpose**: Validate that the *requirements* governing the interactive editor's UX
(navigation, editing, feedback, state visibility, discoverability) are complete, clear,
consistent, and measurable — before implementation.
**Created**: 2026-07-03
**Feature**: [spec.md](../spec.md)

**Note**: These are "unit tests for the requirements" — each item checks whether the spec is
written well for UX, not whether the interface works.

## Requirement Completeness

- [x] CHK001 Are requirements defined for how the user **distinguishes provenance** — corrected vs estimated vs unknown — for every track state? [Completeness, Spec §FR-007]
- [x] CHK002 Are requirements defined for how a **pinned** track is visually indicated (distinct from unpinned)? [Completeness, Spec §FR-012]
- [x] CHK003 Are requirements defined for how **validation errors** are surfaced when an edit is rejected? [Completeness, Spec §FR-005]
- [x] CHK004 Are requirements for **feedback after save and after export** specified (success confirmation, the new playlist link)? [Completeness, Spec §FR-015]
- [x] CHK005 Are requirements for **discovering the available actions / key bindings** (a legend or help) specified? [Completeness, Gap]
- [x] CHK006 Are requirements for **navigating a large list** (scroll, jump-to, or find a track) specified beyond "remains usable"? [Completeness, Gap, Spec §FR-017]
- [x] CHK007 Is the editor's behavior for an **empty / fewer-than-2-track** playlist specified (message and outcome)? [Completeness, Edge Case]

## Requirement Clarity

- [x] CHK008 Is the **Camelot input format** specified (case sensitivity, accepted forms like "8b" vs "8B")? [Clarity, Spec §FR-005]
- [x] CHK009 Is the **BPM input format** specified (integer vs decimal, accepted range)? [Clarity, Spec §FR-005]
- [x] CHK010 Is "manually move a track to a chosen position" clear on the behaviour (one step at a time vs to an arbitrary index)? [Clarity, Spec §FR-012]
- [x] CHK011 Is "remains usable / responsive" quantified for the TUI (input latency, no freeze during the initial fetch)? [Clarity, Spec §FR-017]

## Requirement Consistency

- [x] CHK012 Are the named actions (edit, move/pin, re-sort, save, export, quit) each mapped to one defined behaviour, used consistently across the spec? [Consistency, Spec §FR-003]
- [x] CHK013 Are the visual treatments for corrected / estimated / unknown / pinned states defined without overlap or conflict? [Consistency, Spec §FR-007]

## Acceptance Criteria Quality (Measurability)

- [x] CHK014 Can "clearly flagged / clearly identified" for unsortable and corrected tracks be objectively measured — what specifically makes it clear? [Measurability, Spec §FR-007]
- [x] CHK015 Is the "responsive on a 200-track playlist" criterion measurable (a stated threshold or observable)? [Measurability, Spec §SC-008]

## Scenario & Edge Coverage

- [x] CHK016 Are requirements for the **loading state** while fetching tracks + estimates specified (progress shown, is input blocked)? [Coverage, Gap]
- [x] CHK017 Is the UX specified when **estimates are unavailable** at open (every track unknown)? [Coverage, Gap]
- [x] CHK018 Is a **confirmation** required before a full re-sort (which clears all pins), and is that requirement stated? [Coverage, Spec §FR-006]
- [x] CHK019 Are requirements defined for the UX during **export** (progress, then the result)? [Coverage, Gap]

## Accessibility & Dependencies

- [x] CHK020 Are requirements that state markers (provenance/pins) **do not rely on colour alone** specified for colour-blind users? [Accessibility, Gap]
- [x] CHK021 Is a **terminal capability assumption** (size, colour support) stated, with fallback or minimum-size behaviour? [Assumption, Gap]
