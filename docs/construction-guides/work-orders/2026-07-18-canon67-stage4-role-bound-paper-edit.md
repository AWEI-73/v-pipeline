# Work Order: Canon 67 Stage 4 role-bound paper edit

Date: 2026-07-18
Owner: `main-pipeline` integrator
Worker profile: one high-capability bounded L1 picture-planning worker
Target state: `WAITING_INTEGRATOR_CANON67_STAGE4_PAPER_EDIT_REVIEW`

## 0. Goal

Construct one truthful, fully traceable **360.34-second paper edit** for the
Canon 67 results-report graduation film. This pass turns the accepted Stage 2
story, accepted Stage 3 Material Map v3, and accepted Stage 3.5 story revision
into a complete picture plan that an owner can review before any render.

This is Stage 4 plus the L1 picture-planning method. It is not Stage 5 compile,
Stage 6 render, music, effects, subtitle burn-in, creative approval, or
delivery. The worker proposes one primary paper edit; it does not reopen the
story direction or create an A/B branch without a newly discovered material
contradiction.

The paper edit succeeds only if every selected clip is role-bound to accepted
material evidence and the whole-film structure is understandable to an
external viewer. A technically valid but repetitive or category-scrambled
sequence is not a successful packet.

## 1. Read and freeze first

Read completely, in order:

1. `AGENTS.md`
2. `RUNBOOK.md`
3. `HANDOFF_CURRENT.md`
4. this work order
5. `skills/editing-loop-director.md`, especially L1
6. `skills/material-map.md`, especially retrieval evidence
7. `docs/decisions/2026-07-18-canon67-stage3-5-story-revision-and-role-bound-retrieval.md`
8. `.tmp/canon67_editorial_reconstruction_v2/stage3_5_role_retrieval_closure_v1/final/closure_report.md`

Freeze and verify:

| Artifact | SHA-256 |
|---|---|
| required ancestor commit | `32aa4ad97f5d482ccf4e1a9f0102996017ac0311` |
| accepted editorial state v2 | `2041e6b9c879aa7737defa0f3d86198836822860a2345b16d2742bf219af25e7` |
| accepted story revision v3 | `230432997756b877f7046133a049cddfa3f0cfa8b79472bf9864975217428e6e` |
| accepted Material Map v3 | `704a1fed801218530d206665bf906f67a60ad28f216e3c954ee195b23775962c` |
| frozen Stage 2 segment contract | `694dd73736645736c4f2e4cb0b031d60294c312f6de4ed143c48f38e5d171735` |
| A09 cue/cutaway map | `dd7880d6f69e976349e31409354dc05af9d3610a60c1a9aad7f9d6db45b1deea` |
| approved transcript decision | `5d40c6ed1555fe9e08e51fa398295fef16f28496efa76e671287ff1efc5dc046` |
| Stage 3.5 retrieval closure | `acd583326a52e3dc0e2d1b99f413e00d8e0ee077f797a16ebf07e8c90c9fc2d5` |

Write `preflight/frozen_input_audit.json`. Stop on a mismatch. Do not use the
old 385-second picture order, source-window order, or BGM placement.

## 2. Owner and forbidden zones

Owner zone:

`.tmp/canon67_editorial_reconstruction_v2/stage4_role_bound_paper_edit_v1/**`

Everything outside that root is read-only, including source media, accepted
artifacts, production code, tests, skills, registry, docs, git index/history,
`HANDOFF_CURRENT.md`, and campaign state.

Do not:

- render or create any MP4;
- run ASR, music analysis, Effect Factory, CapCut, or full-suite tests;
- re-review the complete 283-asset pool;
- modify Material Map v3 or add evidence edges;
- invent course facts, speaker identity, roster facts, placement result, or a
  literal departure;
- pad back to 540 seconds;
- use filename/folder prior as visual truth;
- use an override to conceal a retrieval mismatch;
- set `human_creative_approval` or `final_delivery_claimed` true.

This is an agentic paper-edit construction pass, not a capability-engine
campaign. Do not invent an execution companion or strict receipt DAG. Preserve
frozen hashes, public-tool outputs, a concise agent attestation, and command
log in the owner zone.

## 3. Resolve the accepted segment contract

Create `contract/resolved_segment_contract.stage4.json` by applying only the
accepted Stage 3.5 delta to the frozen Stage 2 contract. Preserve segment IDs,
story purposes, evidence needs, and factual limits. The exact active durations
are:

| Segment | Seconds | Binding |
|---|---:|---|
| A01 | 12.00 | opening/location proposition |
| A02 | 12.00 | one strong cohort portrait plus at most two different contexts |
| A03 | 40.00 | discipline, safety briefing, equipment and safety experience |
| A04 | 55.00 | ground/cable teamwork micro-story |
| A05 | 60.00 | pole/live-line precision and risk progression |
| A06 | 50.00 | height/transmission visual peak |
| A07 | 0.00 | merged/deferred; no independent segment |
| A08 | 50.00 | grouped life events and bonds |
| A09 | 39.34 | complete approved source speech plus bounded cutaways |
| A10 | 18.00 | placement-preference process only |
| A11 | 24.00 | two callbacks, one final group photograph, bounded hold |
| **Total** | **360.34** | exact Decimal sum |

Also create `contract/segment_story_completion.json`. Each active segment must
state one factual purpose, one story function, entry state, exit state, unique
new information, allowed source families, and prohibited claims. A07 records
the merge reason and zero duration rather than disappearing silently.

## 4. Build the role-bound paper edit

Run the registered public rough-cut surface against the resolved contract and
accepted Material Map v3 to create a baseline candidate inventory. Treat that
output as evidence, not as an automatically accepted order.

Construct `selection/l1_picture_plan.stage4.proposed.json`. Every picture clip
must include:

- stable `clip_id`, canonical `segment`, and exact `need_id`;
- `asset_id`, `scene_id`, exact source hash;
- source `start_sec` and `duration_sec` (or explicit still-image hold);
- `timeline_in_sec` and `timeline_out_sec`;
- `selection_mode=ranked_candidate`;
- observable-content note, assigned story function, and selection reason;
- visual/event family and shot scale when available;
- `callback_reason` only when a previously used family is intentionally
  recalled for A09 or A11.

No exact source window may repeat. Overlapping windows from the same source are
forbidden across segments. A still image cannot be held long enough to pretend
that an action progressed; the final A11 group photograph may receive the only
intentional ending hold.

For a multi-role segment, rank every clip against its own `need_id`. A scene
may satisfy more than one accepted need, but being ranked for another role is
not sufficient. Reviewed `accepted` evidence must rank ahead of an equivalent
`candidate` hint. Zero manual overrides are allowed in this first paper edit.

## 5. Whole-film editorial rules

Apply these rules across all 360.34 seconds:

1. Organize related training activities into visible units before changing to
   another activity family. Do not alternate unrelated categories merely for
   visual variety.
2. Each segment must add information not already delivered by the preceding
   segment. A02, A03, A04, A05 and A06 may not all become generic group-action
   montages.
3. Record adjacent and non-adjacent exact-window, asset, event-family, location,
   composition, and semantic repetition. Reuse is allowed only as a declared
   callback with a different story job.
4. A08 groups each life-event family contiguously; it must not scatter one shot
   from every activity in random order.
5. A09 preserves the exact 0.00–39.34 source speech continuously. Cues 03–04
   may use ground/cable teamwork; cues 05–06 may use pole/line height; cues
   08–12 remain on the speaker unless accepted evidence proves a separately
   relevant cutaway. This pass does not rewrite approved text.
6. A10 describes only the visible process of discussing and recording future
   work-unit preferences.
7. A11 uses two distinct callbacks, then one final group photograph. It may not
   replay a condensed version of every preceding chapter.

Write:

- `review/repetition_and_family_report.json`;
- `review/rejected_candidate_log.json` with at least the closest rejected
  alternative for each active story role;
- `review/a09_speech_picture_map.json` with cue ranges, audio continuity, and
  selected picture coverage.

## 6. External-viewer labels and review captions

Create `review/chapter_and_caption_plan.proposed.json`. It is review-only text,
not approved delivery graphics.

Use three act-level chapter entries and segment-level factual labels so an
external viewer can understand what the trainees are doing. Prefer observable
training/activity names supported by pixels and accepted evidence. Plain
language may explain the story job in a separate review-caption field.

Every proposed label must carry:

- `text_status=proposed_owner_review`;
- evidence refs;
- `chapter_number`, `observable_title`, `one_line_story_job`;
- exact timeline window;
- `delivery_graphic=false`.

Do not invent poetic copy or promote a folder name into an official course
title. Uncertain terminology stays `UNKNOWN` and is shown to the owner.

## 7. Public retrieval replay and no-render review packet

Run `tools/picture_plan_retrieval_report.py` against the proposed picture plan,
resolved segment contract, and accepted Material Map v3. It must exit 0 with:

- `ok=true`, `errors=[]`;
- every selected clip source hash matching;
- every selected clip inside its role-specific Top-K;
- `override_count=0`.

Create a human-scale packet without rendering:

- `owner_review/paper_edit_timeline.md` — chronological clip table;
- `owner_review/segment_summary.md` — ten active/merged segment summaries;
- `owner_review/owner_review_index.md` — single entry linking every artifact;
- `owner_review/owner_verdict_template.json` — all decisions `PENDING`;
- reuse existing evidence/contact-sheet paths by reference; do not copy or
  regenerate the whole material wall.

The owner index must highlight: total duration, act/segment boundaries,
external-viewer labels, A09 cue coverage, A11 landing, exact/non-adjacent
repetition findings, and every remaining `UNKNOWN`.

## 8. Validation

Run these focused checks only:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest `
  tests.test_material_retrieval `
  tests.test_material_rough_cut `
  tests.test_picture_plan_retrieval_gate -v
C:\Users\user\miniconda3\python.exe tools\skill_tool_contract_audit.py --json
git diff --check
```

Also verify by read-back:

- all JSON is valid UTF-8 with no replacement characters or suspicious runs
  of literal question marks in Chinese fields;
- exact segment sum is 360.34 seconds;
- timeline is contiguous from 0.00 to 360.34 with no gap/overlap;
- every selected source path exists and source hash matches Material Map v3;
- no selected source window repeats or overlaps another segment;
- public retrieval report is green with zero overrides;
- A09 audio anchor is exactly 39.34 seconds and 12/12 cue references persist;
- no MP4 exists below the owner zone;
- pre/post git status is identical and no tracked file changed.

Write:

- `accountability/agent_attestation.json` listing evidence actually inspected;
- `final/command_log.json` with exact argv and exit codes;
- `final/artifact_sha256.json`;
- `final/worker_report.md` with PASS/FAIL/UNKNOWN, deviations, skips, and blind
  spots.

## 9. Stop-loss and legal state

- One LOCAL correction is allowed per actual failure class. On recurrence,
  classify STRUCTURAL and stop the affected stream at the last green state.
- A read-only shell quoting mistake is not a product defect; change to a
  simpler repo-native command once and record it.
- If the public rough-cut or retrieval surface cannot express the plan, write
  `final/factory_gap.json`; do not create a private helper or modify code.
- If a segment cannot reach its duration without repetition or unsupported
  claims, stop with `story_or_material_gap`; do not pad it.
- Do not run the full suite because production code/tests are read-only.
- Do not commit, stage, push, upload, render, or alter campaign state.
- `human_creative_approval=false` and `final_delivery_claimed=false`.

Legal success state:

`WAITING_INTEGRATOR_CANON67_STAGE4_PAPER_EDIT_REVIEW`

The integrator will independently inspect the paper edit and public retrieval
report. Only an owner picture verdict may authorize Stage 5 compile or any
preview/render.
