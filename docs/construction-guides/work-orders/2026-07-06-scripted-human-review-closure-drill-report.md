# Scripted Human Review Closure Drill Report

Date: 2026-07-06

## Output

Output root:

`C:\Users\user\Desktop\video_pipeline\.tmp\scripted_human_review_closure_drill_20260706-160751`

Source run, read-only:

`C:\Users\user\Desktop\video_pipeline\.tmp\scripted_real_material_production_run_20260706-131200\run`

Case run paths:

- approved: `C:\Users\user\Desktop\video_pipeline\.tmp\scripted_human_review_closure_drill_20260706-160751\approved\run`
- revision_requested: `C:\Users\user\Desktop\video_pipeline\.tmp\scripted_human_review_closure_drill_20260706-160751\revision_requested\run`
- rejected: `C:\Users\user\Desktop\video_pipeline\.tmp\scripted_human_review_closure_drill_20260706-160751\rejected\run`

## Source preflight

| Artifact | Exists | Size |
|---|---:|---:|
| `final.mp4` | true | 19918456 |
| `delivery_gate.json` | true | 1147 |
| `story_contract.json` | true | 2874 |
| `story_to_material_map.json` | true | 4743 |
| `story_human_review_decision.json` | false | n/a |

Initial source state:

- `pipeline_home`: `WAITING / human_story_review`
- `next`: `human_review_story_to_material_map`
- This confirms source/no decision remains waiting.

## Drill construction

Three new cases were built under the output root.

Copied lightweight evidence:

- delivery/story/audio/subtitle/music JSON and SRT evidence
- `voxcpm_runtime_check.json`
- `voiceover_provider_plan.json`

Linked local media evidence:

- `final.mp4`
- `voiceover/seg01.wav`
- `voiceover/seg02.wav`
- `voiceover/seg03.wav`

`narration_manifest.json` was rewritten only inside each new case run so the audio refs point to local `voiceover/seg*.wav`.

Decision artifacts:

- approved: `decision=approved`, `reviewer=human`, `approved_beat_ids` covers all required story beats.
- revision_requested: `decision=revision_requested`, `reviewer_type=human`, concrete revision note.
- rejected: `decision=rejected`, `reviewer=human`, rejected beat evidence and note.

## Pipeline home states

| State | Command exit | Mode | Cursor | Status | Next |
|---|---:|---|---|---|---|
| source/no decision | 0 | waiting | human_story_review | WAITING | human_review_story_to_material_map |
| approved | 0 | done | complete | DONE | null |
| revision_requested | 0 | repair | human_story_review | REPAIR | revise_story_material_mapping |
| rejected | 0 | repair | human_story_review | REPAIR | repair_rejected_story_material_mapping |

`story_human_review_decision.json` was consumed in all three decision cases; `pipeline_home` included it in `read` for approved, revision_requested, and rejected.

## Delivery gate results

| Case | Command exit | Pass | Blocking | Warnings | Next action |
|---|---:|---:|---|---|---|
| approved | 0 | true | none | none | null |
| revision_requested | 1 | false | `story_human_review_revision_requested` | `story_human_review_required` | `revise_story_material_mapping` |
| rejected | 1 | false | `story_human_review_rejected` | `story_human_review_required` | `repair_rejected_story_material_mapping` |

Exit code 1 is expected for revision_requested and rejected because `write_delivery_gate_report.py` returns non-zero when the delivery gate blocks.

## Commands

`C:\Users\user\miniconda3\python.exe tools\pipeline_home.py --run "C:\Users\user\Desktop\video_pipeline\.tmp\scripted_real_material_production_run_20260706-131200\run" --json`

Exit code: 0.

`C:\Users\user\miniconda3\python.exe tools\pipeline_home.py --run "C:\Users\user\Desktop\video_pipeline\.tmp\scripted_human_review_closure_drill_20260706-160751\approved\run" --json`

Exit code: 0.

`C:\Users\user\miniconda3\python.exe tools\pipeline_home.py --run "C:\Users\user\Desktop\video_pipeline\.tmp\scripted_human_review_closure_drill_20260706-160751\revision_requested\run" --json`

Exit code: 0.

`C:\Users\user\miniconda3\python.exe tools\pipeline_home.py --run "C:\Users\user\Desktop\video_pipeline\.tmp\scripted_human_review_closure_drill_20260706-160751\rejected\run" --json`

Exit code: 0.

`C:\Users\user\miniconda3\python.exe tools\write_delivery_gate_report.py --run "C:\Users\user\Desktop\video_pipeline\.tmp\scripted_human_review_closure_drill_20260706-160751\approved\run" --json`

Exit code: 0.

`C:\Users\user\miniconda3\python.exe tools\write_delivery_gate_report.py --run "C:\Users\user\Desktop\video_pipeline\.tmp\scripted_human_review_closure_drill_20260706-160751\revision_requested\run" --json`

Exit code: 1, expected delivery block.

`C:\Users\user\miniconda3\python.exe tools\write_delivery_gate_report.py --run "C:\Users\user\Desktop\video_pipeline\.tmp\scripted_human_review_closure_drill_20260706-160751\rejected\run" --json`

Exit code: 1, expected delivery block.

Final artifact check:

`@' ... '@ | C:\Users\user\miniconda3\python.exe -`

Exit code: 0.

Result: no missing required drill files; all four pipeline_home states matched expected values; all three delivery gate states matched expected values.

## Deviations

- The first approved fixture run reached `REPAIR / audio_ready` because the fixture initially lacked `delivery_gate.json`. This was corrected inside the new output root by copying the source run's small `delivery_gate.json`; no code or existing `.tmp` run was changed.
- The first approved delivery gate attempt blocked on missing `voxcpm_runtime_check.json` and `voiceover_provider_plan.json`. These small source evidence files were copied into each drill case, then the gate was rerun and recorded as the final result.
- `final.mp4` and the three voiceover WAV files were hardlinked into the new output root instead of byte-copied to avoid unnecessary disk usage. The source run was not modified.

## Blockers

No stop-loss blocker remained. No code, tools, tests, skills, environment, provider/runtime, Downloads, reference repo, or existing run was modified.

## Next recommended work

Add an operator-facing command or documented runbook step for writing `story_human_review_decision.json` from a real human review, so future scripted delivery candidates do not require hand-authored JSON to move from `WAITING / human_story_review` to `DONE` or repair.
