# Work Order: Canon 67 all-segment editorial calibration long task

Date: 2026-07-15  
Status: READY_FOR_WORKER  
Recommended worker: Luna, high/maximum reasoning  
Estimated size: medium-large, long-running but bounded  
Integrator: SOL / Codex  

## 1. Goal

Extend the accepted Canon 67 `global_editorial_state` from a two-segment
forward test into a complete ten-segment paper-edit/story-state review package.

This task must deeply calibrate the seven active segments that are still
uncalibrated:

- `seg03_discipline_before_skill`
- `seg04_cable_teamwork`
- `seg05_height_and_pressure`
- `seg06_standards_make_ready`
- `seg07_life_builds_belonging`
- `seg08_supervisor_witness`
- `seg10_departure_with_responsibility`

`seg01` and `seg02` remain accepted PASS evidence. `seg09` remains an explicit
13/13 all-or-none teacher/adviser deferral.

The result is a paper-edit/editorial-state decision package. It is not a
picture lock, render authorization, creative approval, delivery claim, new
story engine, or new orchestrator.

## 2. Product decisions already made

These are fixed inputs, not worker questions:

- Stage owns lifecycle; editing loops improve work inside the current Stage.
- The orchestrator owns canonical editorial state. The worker reads a pinned
  revision, inspects evidence, and returns immutable deltas.
- Canon 67 is a 540-second成果報告／結訓影片, not an AI concept film.
- Story ambition is capped by material truth. Unsupported intent becomes an
  explicit deferral or story risk; it is not filled with invented claims.
- Material provenance remains `curated + unannotated`. Filename/folder hints
  are priors, not ground truth.
- Existing L1 v3 source selection, order, windows, and hashes are frozen in
  this work order. If a story defect requires reselection, record a proposed
  revision finding; do not silently edit the picture plan.
- Teacher/adviser material stays excluded until a complete owner-approved
  13/13 roster exists. Do not invent names, partial coverage, or generated
  substitutes.
- A/B comparison is the preferred review shape for a materially ambiguous
  high-level choice. It is not mandatory for every segment.
- `decision_completeness=PASS` means that the decision and evidence package is
  complete. It does not mean the owner likes the creative result.
- Human creative approval and final delivery remain false.
- Full-suite trust remains `STALE`; this task does not run the full suite.

## 3. Authoritative inputs and frozen hashes

Accepted editorial-state chain:

- `.tmp/canon67_540s_route_acceptance/accepted_chain/revision_0001.json`
  - SHA-256:
    `42ddad5fcd847ff2979ebce0d38b6feed36bfd2f4907b245ac1ff29311a7e571`
- `.tmp/canon67_540s_route_acceptance/accepted_chain/revision_0002.json`
  - SHA-256:
    `def6f41bb75efd981729cbd6524c5798add5e3c089aa8f0a1e81c12d6245194f`

Revision 2 is a valid immutable proof revision and is the technical base for
this task. Revision 1 remains the canonical pointer until the whole new chain
passes validation.

Frozen L1 plan:

- `.tmp/canon67_540s_route_acceptance/stage5/l1_revision_v3/l1_picture_plan_v3.proposed.json`
  - SHA-256:
    `6963c519469081956dceef03a2c79e343f622ac2c7a81fd24471e7a3867c3e71`

Required story/material evidence:

- `.tmp/canon67_540s_route_acceptance/stage1/story_soul_blueprint.json`
- `.tmp/canon67_540s_route_acceptance/stage1/screenplay_beats.json`
- `.tmp/canon67_540s_route_acceptance/stage3/project_material_map_l0_v1.json`
- `.tmp/canon67_540s_route_acceptance/stage3/perception_v1/material_understanding_matrix.json`
- `.tmp/canon67_540s_route_acceptance/stage3/perception_supplemental_v1/material_understanding_matrix.json`
- `.tmp/canon67_540s_route_acceptance/stage3/l0_semantic_review_v1/material_understanding_matrix.json`
- `.tmp/canon67_540s_route_acceptance/stage3/maps_l0_v1/*.map.json`
- `.tmp/canon67_540s_route_acceptance/stage5/l1_revision_v3/retrieval_ranking_report_v3.proposed.json`
- `.tmp/canon67_540s_route_acceptance/stage5/l1_revision_v3/l1_owner_review/storyboard_preview_report_v3.json`
- `.tmp/canon67_540s_route_acceptance/stage5/l1_revision_v3/l1_owner_review/matrix_keyframe_adapter_v3.proposed.json`
- `docs/decisions/2026-07-14-canon67-teacher-all-or-none-memory-ending.md`
- `docs/decisions/2026-07-15-upstream-editorial-discovery-boundary.md`
- `docs/hermes-v-pipeline-honest-capability-map.md`

If an optional evidence path does not exist, record it as unavailable. Do not
rebuild the perception system to satisfy this task.

## 4. Owner zone

The worker may create only:

- new immutable chain files in
  `.tmp/canon67_540s_route_acceptance/accepted_chain/`:
  - `delta_0002_to_0003.json` through `delta_0008_to_0009.json`;
  - `receipt_0002_to_0003.json` through
    `receipt_0008_to_0009.json`;
  - `revision_0003.json` through `revision_0009.json`;
- review-only artifacts under
  `.tmp/canon67_540s_route_acceptance/all_segment_editorial_review/**`;
- bounded final pointer/state updates in:
  - `.tmp/canon67_540s_route_acceptance/campaign_status.json`;
  - the machine-readable block of `HANDOFF_CURRENT.md`.

The worker may read raw media and existing visual evidence, but must not mutate
raw media or canonical inputs.

## 5. Forbidden zone

Do not modify:

- production code, `tools/`, tests, skills, registries, `AGENTS.md`,
  `RUNBOOK.md`, or `docs/INDEX.md`;
- any existing file in `accepted_chain/`, including revision 0/1/2, their
  deltas, receipts, worker contexts, and reports;
- story blueprint, screenplay, Material Map, retrieval report, L1 v1-v3 plan,
  source-window selection, source media, or source hashes;
- CapCut, Remotion, effect, audio, subtitle, ASR, render, Verify, or delivery
  surfaces;
- unrelated dirty/untracked files.

Do not create:

- a new selector, ranker, state engine, route runner, schema migration, gate,
  material map, renderer, or helper script;
- a candidate video, new storyboard render, audio mix, subtitle file, effect
  preview, or Drive upload;
- private Python/PowerShell runners that duplicate the registered state CLI.

If the public `tools/global_editorial_state.py apply-delta` surface cannot
apply a required generic delta, stop and report the bounded capability gap.
Do not patch production code in this work order.

## 6. Calibration contract for each active segment

For every active segment, the worker must inspect the actual selected evidence
and produce a segment decision record containing at least:

1. `factual_purpose`: one factual job unique to this segment;
2. `story_function`: why this segment exists in the full film;
3. `entry_state` and `exit_state`;
4. `new_information`: what the audience learns here that was not already
   established by earlier segments;
5. `source_window_refs`: the frozen L1 v3 clips and windows;
6. `review_caption`: factual review text, not unsupported narration;
7. `selected_visual_families`;
8. `reuse_justifications` for every repeated asset or visual family;
9. `cross_segment_repetition_risks`;
10. `clip_roles` classifying every selected clip as
    `anchor | support | transition`;
11. `decision_authority=agent_proposal`;
12. `decision_mode=single | ab_comparison | delegated`;
13. `decision_completeness=PASS | UNKNOWN`;
14. `decision_reason`.

Rules:

- PASS requires at least one `anchor` backed by direct, resolved visual or
  speech evidence for the segment's factual purpose.
- A `support` or `transition` clip may improve continuity but cannot carry a
  factual claim by itself.
- Filenames and folder names may help retrieval but cannot be the only evidence
  for PASS.
- If evidence is insufficient, contradictory, too generic, or only inferred,
  keep the segment UNKNOWN and give a concrete reason.
- Do not force all seven active segments to PASS.
- Do not rewrite a segment purpose merely to make weak clips appear valid.
- Reuse is allowed only when the second use has a different, stated story job.

## 7. Required full-film checks

The review must evaluate the ten-segment sequence as one film, not ten isolated
records.

### 7.1 Information progression

For each adjacent pair, state whether the later segment contributes new
information or merely restates the previous segment. Specifically inspect:

- seg02 formation/gathering versus seg03 discipline;
- seg04 cable teamwork versus seg05 height/pressure;
- seg06 standards/readiness versus seg08 supervisor witness;
- seg07 life/belonging versus seg10 memory/departure.

### 7.2 Repetition

Detect and record:

- exact source reuse;
- overlapping source windows;
- non-adjacent semantic repetition;
- repeated event families presented as if they were different topics;
- repeated people/location/shot-scale clusters that flatten the film.

Repetition detection creates a `structural_candidate` finding. It is not an
automatic creative FAIL unless the evidence is objectively identical or a
frozen contract is violated.

### 7.3 Story continuity

For every segment boundary, record:

- what state enters;
- what changes;
- what state exits;
- what motivates the next segment.

Do not use abstract taste terms as proof. If the transition depends on text,
music, or an effect that does not yet exist, mark that dependency explicitly.

### 7.4 Material ceiling

When the intended story cannot be supported, create a coverage-ledger item:

- `status=deferred_due_to_material`;
- `reason=not_found | not_present | present_unusable | excluded_by_policy`;
- intended story function;
- search/evidence scope inspected;
- owner verdict required;
- proposed future material need.

This is not permission to generate replacement material in this task.

## 8. A/B comparison policy

Use paper-only A/B comparisons only where two materially different structural
choices remain credible after evidence review.

Good A/B candidates include:

- separating seg02 collective identity from seg03 safety discipline;
- distinguishing seg06 standards/readiness from seg08 supervisor witness;
- choosing whether seg07 prioritizes breadth of activities or one coherent
  micro-story;
- deciding whether seg10 lands on factual departure or symbolic memory, while
  preserving the already accepted teacher deferral.

Each A/B record must contain:

- the exact decision question;
- option A and option B;
- source-bound evidence for both;
- trade-off;
- agent recommendation with reasons;
- `owner_verdict=PENDING`.

Do not create an A/B merely to satisfy the format. If only one option is
supported, use `decision_mode=single` and explain why.

## 9. Finding classification

Every finding uses exactly one class:

- `objective`: measurable contract or factual violation;
- `structural_candidate`: plausible editorial issue requiring owner verdict;
- `taste`: subjective response that cannot become a machine FAIL here.

Only objective findings may fail technical acceptance. Structural candidates
remain advisory. Taste findings remain owner-gated.

## 10. Immutable revision sequence

Apply exactly one segment calibration per revision:

| Transition | Segment |
|---|---|
| revision 2 -> 3 | seg03 |
| revision 3 -> 4 | seg04 |
| revision 4 -> 5 | seg05 |
| revision 5 -> 6 | seg06 |
| revision 6 -> 7 | seg07 |
| revision 7 -> 8 | seg08 |
| revision 8 -> 9 | seg10 |

Each delta may change only:

- its target segment record;
- the directly affected coverage, visual-family, people, or motif ledger;
- full-film repetition/story risks directly discovered by that calibration.

It must not change:

- source artifacts or their hashes;
- material provenance;
- segment order;
- other segment records;
- verification history except final focused-test evidence at closure;
- `human_creative_approval` or `final_delivery_claimed`;
- the editorial thesis.

Author each delta as UTF-8 JSON, then apply it only through:

```powershell
C:\Users\user\miniconda3\python.exe tools\global_editorial_state.py apply-delta `
  --base-state <previous-revision> `
  --delta <current-delta> `
  --output-dir .tmp/canon67_540s_route_acceptance/accepted_chain `
  --json
```

After each transition:

1. validate the new revision with the public CLI;
2. prove semantic diff is limited to the authorized fields;
3. validate delta/receipt/base/payload binding;
4. re-hash all earlier revisions, deltas, and receipts and prove no drift;
5. stop immediately on an immutable collision or stale-base error.

## 11. Required review package

Create under:

`.tmp/canon67_540s_route_acceptance/all_segment_editorial_review/`

Required artifacts:

- `owner_review_index.md`
- `all_segment_story_checklist.json`
- `cross_segment_repetition_matrix.json`
- `story_boundary_matrix.json`
- `structural_candidates.json`
- `material_deferrals.json`
- `story_state_summary.json`
- `owner_verdict_template.json`
- `artifact_manifest.json`
- `final/worker_report.md`
- `final/command_log.json`

The owner review index must be readable without opening every historical
artifact. For each segment, show:

- unique purpose;
- PASS/UNKNOWN and reason;
- anchor/support/transition counts;
- main evidence links;
- repetition risks;
- A/B question if any;
- exact owner verdict requested.

The owner verdict template must allow independent verdicts per segment and per
structural candidate. It must not pre-fill owner approval.

## 12. Ordered execution

### Task 0 — Preflight and freeze

- Read `AGENTS.md`, `RUNBOOK.md`, this work order, and the registered
  `global-editorial-state` Tool Contract.
- Record branch, HEAD, full `git status --short`, and all frozen hashes.
- Validate revision 2 with the public CLI.
- Run the focused state test before creating deltas.
- Stop if revision 0/1/2, L1 v3, or source-artifact hashes do not match.

### Task 1 — Evidence immersion

- Read the 540-second story and L1 v3 plan.
- For every selected asset in seg03–08 and seg10, inspect actual pixel evidence
  from existing keyframes, temporal strips, contact sheets, or source media.
- Record exactly which evidence was inspected.
- Do not certify content from filename or metadata alone.
- If a selected asset has no usable visual evidence, mark that clip unresolved
  and propagate the uncertainty to its segment.

### Task 2 — Segment calibration proposals

- Produce the seven segment decision records.
- Classify every selected clip.
- Build factual captions and source-bound purpose statements.
- Create A/B records only where the evidence supports two real alternatives.
- Keep unsupported statements UNKNOWN.

### Task 3 — Full-film structural review

- Build information progression, story boundary, and repetition matrices.
- Record material-ceiling deferrals.
- Classify findings as objective, structural candidate, or taste.
- Confirm seg09 remains the accepted 13/13 deferral.

### Task 4 — Apply immutable deltas

- Apply revision 2 -> 9 in the required sequence.
- Validate and hash-protect after every transition.
- Do not batch all segments into one delta.

### Task 5 — Owner review packet

- Create the required packet and manifest.
- Link existing storyboard evidence; do not render a new preview.
- Keep all owner verdict fields pending.

### Task 6 — Closure and pointers

Only after the complete chain and packet pass:

- update `campaign_status.json` with:
  - canonical editorial state path/hash for revision 9;
  - `product_state=WAITING_OWNER_CANON67_ALL_SEGMENT_EDITORIAL_REVIEW`;
  - `full_suite.status=STALE`;
  - review packet path/hash;
- update only the machine-readable block of `HANDOFF_CURRENT.md` to the same
  pointers and set worker stop state to
  `WAITING_INTEGRATOR_CANON67_ALL_SEGMENT_EDITORIAL_REVIEW`;
- do not claim picture lock, render authorization, creative approval, or
  delivery.

### Task 7 — Evidence report

Write the worker report with:

- pre/post HEAD and dirty tree;
- all commands and exit codes;
- frozen and final chain hashes;
- per-segment PASS/UNKNOWN outcomes;
- inspected visual evidence ledger;
- semantic diff proof for each transition;
- finding counts by class;
- A/B proposals and pending verdicts;
- deviations, failures, blind spots, skipped checks, and final state.

## 13. Acceptance commands

Preflight focused test:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_global_editorial_state -v
```

For each new revision:

```powershell
C:\Users\user\miniconda3\python.exe tools\global_editorial_state.py validate `
  --state <revision-path> --json
```

Final focused/adjacent suite:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest `
  tests.test_global_editorial_state `
  tests.test_skill_tool_contracts `
  tests.test_dispatch_capabilities `
  tests.test_pipeline_skill_boundaries -v
```

Registry audit:

```powershell
C:\Users\user\miniconda3\python.exe tools\skill_tool_contract_audit.py --json
```

Repository diff hygiene:

```powershell
git diff --check
```

Final read-back must also prove:

- every new JSON parses as UTF-8;
- no `U+FFFD`, suspicious repeated literal question marks, or corrupted
  Chinese text;
- every evidence path exists;
- every manifest hash matches;
- revision 0/1/2 and all source artifacts are unchanged;
- all seven new deltas, receipts, and revisions are immutable and mutually
  bound;
- all 64 L1 v3 clips remain unchanged;
- no render/audio/subtitle/effect/CapCut artifact was created;
- `human_creative_approval=false`;
- `final_delivery_claimed=false`.

Do not run the full suite in this task. Record it as `NOT_RUN` and preserve the
machine-readable `STALE` trust boundary.

## 14. Stop-loss

One LOCAL correction is allowed per failure class for evidence-path typo,
command quoting, output-directory creation, or read-only manifest formatting.

Stop at the last green state when:

- the same failure class recurs after one LOCAL correction;
- a frozen hash drifts;
- an existing immutable chain artifact would be overwritten;
- the public state CLI cannot represent or validate the required delta;
- completing the task requires production code, test, skill, registry, plan,
  Material Map, selector, renderer, CapCut, audio, subtitle, or source changes;
- evidence cannot distinguish a factual anchor from metadata inference;
- owner taste or roster truth is required to continue.

On stop, preserve all evidence and report PASS/FAIL/UNKNOWN separately. Do not
repair outside the owner zone and do not turn uncertainty into approval.

## 15. Legal success state

The only successful worker stop is:

`WAITING_INTEGRATOR_CANON67_ALL_SEGMENT_EDITORIAL_REVIEW`

Success requires:

- revision 2 -> 9 immutable chain validated;
- seven active segment records calibrated, with honest PASS/UNKNOWN outcomes;
- seg09 still deferred with the accepted 13/13 reason;
- complete full-film repetition, boundary, and material-deferral review;
- owner review packet and manifest valid;
- focused tests, registry audit, UTF-8/JSON/hash read-back, and
  `git diff --check` pass;
- no forbidden mutation, render, full suite, upload, approval, or delivery
  claim.

The integrator independently reviews the evidence. Worker completion is not
final acceptance.
