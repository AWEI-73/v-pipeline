# 2026-07-08 Copyedit Script Pipeline Alignment Rehearsal

## Goal

Run the current video pipeline against the copyedited script package and determine whether it can produce a coherent `music_subtitle_only` technical review candidate.

This is a pipeline-alignment rehearsal, not final delivery. Produce `final_copyedit_rehearsal.mp4` only if the evidence supports it. Otherwise stop with a precise blocker.

## Construction Basis

Read-only inputs:

- `.tmp\reference_aligned_script_copyedit_20260708-171900\deliverable_safe_script.json`
- `.tmp\reference_aligned_script_copyedit_20260708-171900\deliverable_safe_script.md`
- `.tmp\reference_aligned_script_copyedit_20260708-171900\revised_subtitle_pockets.json`
- `.tmp\reference_aligned_script_copyedit_20260708-171900\copyedit_decisions.json`
- `.tmp\reference_aligned_script_copyedit_20260708-171900\final_artifact_check.json`
- `.tmp\shot_level_material_proof_completion_20260708-080727\render_rehearsal_entry_packet.json`
- `.tmp\shot_level_material_proof_completion_20260708-080727\shot_level_material_proof_plan.json`
- `.tmp\shot_level_material_proof_completion_20260708-080727\shot_pool_inventory.json`
- `.tmp\effect_factory_integration_completion_20260708-154117\effect_handoff.json`

The copyedited script is the story basis. The shot-level proof package is the material evidence basis. The effect handoff is effect evidence, not final animation proof.

## Owner Zone

Editable paths:

- Fresh output root under `.tmp\copyedit_script_pipeline_alignment_rehearsal_*`
- Run-local artifacts inside that fresh output root
- `docs/construction-guides/work-orders/2026-07-08-copyedit-script-pipeline-alignment-rehearsal-report.md`

## Forbidden Zone

Read-only paths:

- `C:\Users\user\Downloads\微電影素材\_整理後`
- `.tmp\reference_aligned_script_copyedit_20260708-171900`
- `.tmp\shot_level_material_proof_completion_20260708-080727`
- `.tmp\effect_factory_integration_completion_20260708-154117`
- Existing `.tmp\graduation_v*`, `.tmp\v6_*`, `.tmp\v7_*`, and prior rehearsal runs
- `deliveries\`
- Existing final media artifacts
- `.env`, `.env.*`
- `.venv_voxcpm\`
- `reference repo\`
- VoxCPM reference/source repository
- Repo code, tests, tools, and skills
- `story_human_review_decision.json`
- `human_transcript_review_decision.json`
- Git branch/commit/push operations

## Required Route

1. Create a fresh output root and run folder.
2. Verify construction inputs exist and decode as UTF-8.
3. Confirm `music_subtitle_only` profile and no VoxCPM/narration requirement.
4. Build a render-facing alignment plan from the copyedited script.
5. Run or produce run-local visual-selection evidence for each render-facing beat.
6. If a suspicious safety/newcomer/basic-skill ref such as `工安早會/IMG_2120.JPG` or `工安早會/IMG_2124.JPG` is used, it must be explicitly accepted with visual evidence or replaced. Do not silently use it.
7. Use certification/check only as a bridge, not primary proof.
8. Exclude formal supervisor source speech unless transcript approval exists. It should not exist in this run.
9. Use `human_declared_allowed` internal music-use basis. Do not claim legal approval.
10. Use effect handoff as title/effect guidance. Titles must enter, hold briefly, and exit; no persistent side rail.
11. First target the 210-230 second current-capacity cut. Attempt 240-300 seconds only if the evidence can support extension without thin/compiled proof abuse.
12. Render `final_copyedit_rehearsal.mp4` only after the plan passes the above checks.
13. If render succeeds, write review artifacts and run ffprobe, pipeline_home, and delivery gate.
14. If any required evidence is missing, stop and write stop-loss artifacts.

## Required Artifacts

Always write:

- `source_run_manifest.json`
- `copyedit_script_alignment_plan.json`
- `visual_selection_review.json`
- `visual_selection_gate.json`
- `used_shot_manifest.json`
- `section_timing_plan.json`
- `subtitle_title_plan.json`
- `title_effect_lifecycle_plan.json`
- `music_use_basis.json`
- `compiled_risk_usage_report.json`
- `certification_bridge_decision.json`
- `review_packet.md`
- `review_packet.json`
- `final_artifact_check.json`

If render succeeds, also write:

- `final_copyedit_rehearsal.mp4`
- `ffprobe_final_copyedit_rehearsal.json`
- `audio_mix_report.json`
- `title_effect_lifecycle_qa.json`
- `delivery_gate.json`
- `pipeline_home.json`

If stop-loss happens, write:

- `stop_loss_report.json`
- `final_absence_evidence.json`

## Red-First Verification

Before planning, record failing/precondition evidence that the copyedit package has no final media and is not already render-ready:

- `final_artifact_check.json` says `ready_for_render=false`
- no `final_copyedit_rehearsal.mp4` exists in the fresh output root

Use pinned Python and record command/exit code/output in the report.

## Acceptance Commands

Use the pinned interpreter:

```powershell
C:\Users\user\miniconda3\python.exe
```

Run a final artifact check for the fresh output root. It must verify:

- all required artifacts exist;
- generated JSON/Markdown/SRT decodes as UTF-8 with no `\ufffd` and no suspicious repeated literal question-mark runs;
- no `story_human_review_decision.json`;
- no `human_transcript_review_decision.json`;
- no VoxCPM artifacts;
- no legal approval claim;
- prior input roots were not modified;
- if final exists, ffprobe shows video and audio and duration is either 210-230 seconds or 240-300 seconds;
- if final is absent, `stop_loss_report.json` exists.

If final media exists, run:

```powershell
ffprobe -v error -show_entries stream=codec_type,codec_name,duration -show_entries format=duration -of json ".tmp\<fresh_root>\run\final_copyedit_rehearsal.mp4"
```

If final media exists, run:

```powershell
C:\Users\user\miniconda3\python.exe tools\pipeline_home.py --run ".tmp\<fresh_root>\run" --json
```

If final media exists, run:

```powershell
C:\Users\user\miniconda3\python.exe tools\write_delivery_gate_report.py --run ".tmp\<fresh_root>\run" --json
```

Always run:

```powershell
git diff --check
```

Expected exit code: `0`, except a stop-loss final absence check may intentionally produce a non-zero ffprobe if recorded as evidence.

## Stop-Loss Limits

Stop and report instead of forcing a render if:

- construction inputs are missing or corrupted;
- the plan cannot reach at least 210 seconds without abusing thin/compiled/reference proof;
- visual selection cannot accept or replace suspicious safety/basic-skill refs;
- certification bridge would be presented as primary proof;
- source speech or transcript approval would be needed;
- music basis is missing or would claim legal approval;
- titles/effects cannot be represented with enter/hold/exit lifecycle;
- render fails or final media lacks video/audio;
- any step would require editing forbidden zones.

## Delegated Decisions

- Exact output root suffix.
- Exact replacement shots when suspicious refs fail, as long as visual evidence is recorded.
- Whether to stop at 210-230 seconds or extend to 240-300 seconds.
- Exact title/subtitle timings, as long as they follow the copyedited script and lifecycle rules.
- Exact ffmpeg assembly details, as long as no forbidden evidence is used.

## Final Report Requirements

Write:

```text
docs/construction-guides/work-orders/2026-07-08-copyedit-script-pipeline-alignment-rehearsal-report.md
```

Include:

- Output root and run path.
- Commands and exit codes.
- Red-first/precondition evidence.
- Whether final media was produced.
- If final exists: path, duration, streams, pipeline_home, and delivery gate result.
- If stop-loss: precise blocker and next action.
- Visual-selection decisions, including suspicious refs accepted/replaced/stopped.
- Used shot summary and compiled-risk usage.
- Effect/title lifecycle summary.
- Music-use basis and confirmation that legal approval is not claimed.
- Confirmation that no VoxCPM, story approval, transcript approval, legal approval, Downloads edit, prior run edit, repo code/test edit, or delivery package edit occurred.
- Deviations, blockers, and next recommended work.
