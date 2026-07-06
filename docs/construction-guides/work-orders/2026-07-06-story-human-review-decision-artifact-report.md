# Story Human Review Decision Artifact Report

Date: 2026-07-06

## Files changed

- `video_pipeline_core/delivery_gate.py`
- `tools/pipeline_home.py`
- `tests/test_delivery_gate.py`
- `tests/test_pipeline_home.py`
- `docs/video-pipeline-operating-map.md`
- `docs/pipeline-decision-tree.md`
- `docs/branch-contract-registry.md`
- `docs/branch-contract-registry.json`
- `docs/construction-guides/work-orders/2026-07-06-story-human-review-decision-artifact-report.md`

## Decision artifact

Canonical artifact:

`story_human_review_decision.json`

Accepted shape:

- `artifact_role`: `story_human_review_decision`
- `decision`: `approved`, `revision_requested`, or `rejected`
- `reviewer` or `reviewer_type`: must be `human` to affect delivery state
- `approved_beat_ids`: required to cover all required story beats when approving a beat-addressed story contract
- `revision_notes` and `rejected_beat_ids`: preserved as decision evidence
- `reviewed_artifacts` and `created_at`: documented contract fields

Non-human reviewer values such as `agent` or `self` do not clear `story_human_review_required`.

## Red-first evidence

Command:

`C:\Users\user\miniconda3\python.exe -m unittest tests.test_delivery_gate tests.test_pipeline_home`

Exit code: 1.

Observed expected failures:

- `approved`: `story_human_review_required` remained in delivery gate warnings.
- `revision_requested`: delivery gate still returned `pass=true`.
- `rejected`: delivery gate still returned `pass=true`.
- `pipeline_home`: approved still returned `waiting`; revision and rejected still returned `waiting` instead of repair.

## Implemented behavior

### approved

Delivery gate:

- `reviewer="human"` or `reviewer_type="human"` plus `decision="approved"` clears `story_human_review_required`.
- If required story beats exist, every required beat must appear in `approved_beat_ids`.
- Agent/self approval does not clear the warning.

Pipeline home:

- delivery gate pass + final.mp4 + valid human approved decision returns `DONE / complete`.
- `story_human_review_decision.json` is included in `read`.

### revision_requested

Delivery gate:

- Adds blocking rule `story_human_review_revision_requested`.
- `next_action` is `revise_story_material_mapping`.

Pipeline home:

- Routes to `REPAIR / human_story_review`.
- `next` is `revise_story_material_mapping`.
- It does not complete delivery.

### rejected

Delivery gate:

- Adds blocking rule `story_human_review_rejected`.
- `next_action` is `repair_rejected_story_material_mapping`.

Pipeline home:

- Routes to `REPAIR / human_story_review`.
- `next` is `repair_rejected_story_material_mapping`.
- It does not complete delivery.

### missing or non-human decision

Missing, malformed, partial, agent, or self review leaves the existing `story_human_review_required` path intact. A technical candidate remains `WAITING / human_story_review` when the only unresolved issue is human story review.

## Smoke

Smoke command:

`@' ... '@ | C:\Users\user\miniconda3\python.exe -`

Exit code: 0.

Smoke output root:

`C:\Users\user\Desktop\video_pipeline\.tmp\story_human_review_decision_artifact_smoke_20260706-151339`

Results:

- repaired run with no decision, read-only: `WAITING / human_story_review`, `next=human_review_story_to_material_map`.
- approved fixture: `DONE / complete`, `status=DONE`.
- revision_requested fixture: `REPAIR / human_story_review`, `next=revise_story_material_mapping`.
- rejected fixture: `REPAIR / human_story_review`, `next=repair_rejected_story_material_mapping`.

Initial full-copy smoke attempt:

- Exit code: 1.
- Reason: disk space exhausted while copying large media assets from the repaired run.
- Partial temp path was removed after verifying it was under `.tmp`.
- Deviation: switched to read-only repaired-run smoke for missing decision plus lightweight temp fixtures for approved/revision/rejected.

## Acceptance

`C:\Users\user\miniconda3\python.exe -m unittest tests.test_delivery_gate tests.test_pipeline_home`

Exit code: 0.

Tail:

`Ran 145 tests in 6.671s`

`OK`

`C:\Users\user\miniconda3\python.exe -m unittest tests.test_delivery_gate tests.test_delivery_gate_report tests.test_pipeline_home tests.test_final_product_verify`

Exit code: 0.

Tail:

`Ran 158 tests in 8.348s`

`OK`

`git diff --check`

Exit code: 0.

Tail: line-ending warnings only; no whitespace errors.

Report content check:

Exit code: 0.

Tail:

`{'report_exists': True, 'missing': []}`

## Deviations

- `revision_requested` was implemented as `REPAIR`, not `WAITING`, because it requires a concrete story/material mapping change before delivery can complete.
- Full production-run copy smoke was skipped after a real disk-space failure. The replacement smoke did not mutate the source run and still proved the required home states.
- `final_product_verify` was not changed because this artifact is a delivery/home decision boundary, and existing verify tests remained green.

## Blockers

No code blocker remains. The only operational blocker encountered was insufficient disk space for copying the full repaired production run.

## Next recommended work

Add a small operator-facing writer/checker for `story_human_review_decision.json` so future scripted runs can record a real human `approved`, `revision_requested`, or `rejected` decision without hand-authoring JSON.
