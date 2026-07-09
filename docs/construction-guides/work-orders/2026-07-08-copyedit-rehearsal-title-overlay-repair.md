# 2026-07-08 Copyedit Rehearsal Title Overlay Repair

## Goal

Resume the blocked copyedit script pipeline alignment rehearsal and produce `final_copyedit_rehearsal.mp4`, or stop with a narrower blocker.

The prior rehearsal passed material, visual-selection, music-use, certification-bridge, and title lifecycle planning, then failed on the first segment render because the run-local ffmpeg title overlay used an invalid `drawbox` expression:

```text
Error when evaluating the expression 'w'
```

This work order fixes only that render assembly issue. Do not re-author the story, reselect music, change the product route, or broaden into code repairs.

## Construction Basis

Read-only inputs:

- `docs/construction-guides/work-orders/2026-07-08-copyedit-script-pipeline-alignment-rehearsal-report.md`
- `.tmp\copyedit_script_pipeline_alignment_rehearsal_20260708-172339\run`
- `.tmp\reference_aligned_script_copyedit_20260708-171900\deliverable_safe_script.json`
- `.tmp\reference_aligned_script_copyedit_20260708-171900\revised_subtitle_pockets.json`
- `.tmp\shot_level_material_proof_completion_20260708-080727\shot_level_material_proof_plan.json`
- `.tmp\effect_factory_integration_completion_20260708-154117\effect_handoff.json`

The previous run's plan and visual decisions are the alignment basis. Reuse them unless the failed render artifacts are unusable; if unusable, create a fresh continuation output root but keep the same story, shots, timing, music basis, and visual decisions.

## Owner Zone

Editable paths:

- New continuation output root under `.tmp\copyedit_rehearsal_title_overlay_repair_*`
- Run-local artifacts inside that continuation root
- If safer, copied run-local artifacts from `.tmp\copyedit_script_pipeline_alignment_rehearsal_20260708-172339\run`
- `docs/construction-guides/work-orders/2026-07-08-copyedit-rehearsal-title-overlay-repair-report.md`

## Forbidden Zone

Read-only paths:

- `C:\Users\user\Downloads\微電影素材\_整理後`
- `.tmp\copyedit_script_pipeline_alignment_rehearsal_20260708-172339\run`
- `.tmp\reference_aligned_script_copyedit_20260708-171900`
- `.tmp\shot_level_material_proof_completion_20260708-080727`
- `.tmp\effect_factory_integration_completion_20260708-154117`
- Existing `.tmp\graduation_v*`, `.tmp\v6_*`, `.tmp\v7_*`, and other prior runs
- `deliveries\`
- Existing final media artifacts outside the new continuation root
- `.env`, `.env.*`
- `.venv_voxcpm\`
- `reference repo\`
- VoxCPM reference/source repository
- Repo code, tests, tools, and skills
- `story_human_review_decision.json`
- `human_transcript_review_decision.json`
- Git branch/commit/push operations

## Required Route

1. Create a fresh continuation root and run folder.
2. Copy or reconstruct only the prior run-local plan artifacts needed to rerun assembly.
3. Preserve the prior story, section timing, used shot manifest, visual decisions, music-use basis, certification bridge, and no-narration policy.
4. Record red-first evidence from the previous `segment_render_failed` stop-loss and failing stderr.
5. Replace only the failing title overlay assembly.
   - Acceptable options:
     - correct ffmpeg expressions such as `drawbox=w=iw:h=...`, or
     - pre-render title/subtitle PNG overlays and apply them with `overlay`, avoiding ambiguous drawbox/drawtext expression variables.
6. Render segments and assemble `final_copyedit_rehearsal.mp4`.
7. If render succeeds, run ffprobe, pipeline_home, and write_delivery_gate_report.
8. If render fails again, stop and write a new stop-loss report with the exact failed command and stderr tail.

## Required Artifacts

Always write:

- `source_run_manifest.json`
- `overlay_repair_plan.json`
- `render_command_log.json`
- `section_timing_plan.json`
- `used_shot_manifest.json`
- `visual_selection_gate.json`
- `music_use_basis.json`
- `title_effect_lifecycle_plan.json`
- `final_artifact_check.json`

If render succeeds, also write:

- `final_copyedit_rehearsal.mp4`
- `ffprobe_final_copyedit_rehearsal.json`
- `audio_mix_report.json`
- `title_effect_lifecycle_qa.json`
- `delivery_gate.json`
- `pipeline_home.json`
- `review_packet.md`
- `review_packet.json`

If stop-loss happens, write:

- `stop_loss_report.json`
- `final_absence_evidence.json`
- `review_packet.md`
- `review_packet.json`

## Red-First Verification

Before repair, read the prior run's:

- `stop_loss_report.json`
- `render_command_log.json`

Record:

- prior blocker is `segment_render_failed`;
- stderr contains `Error when evaluating the expression 'w'`;
- prior final media is absent.

This is the only red-first evidence required.

## Acceptance Commands

Use the pinned interpreter:

```powershell
C:\Users\user\miniconda3\python.exe
```

Run a final artifact check for the continuation root. It must verify:

- required artifacts exist;
- generated JSON/Markdown/SRT decodes as UTF-8 with no `\ufffd` and no suspicious repeated literal question-mark runs;
- no `story_human_review_decision.json`;
- no `human_transcript_review_decision.json`;
- no VoxCPM artifacts;
- no legal approval claim;
- prior input roots were not modified;
- if final exists, ffprobe shows video and audio and duration is 210-230 seconds;
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

Expected exit code: `0`, except a stop-loss ffprobe on absent final may be recorded as evidence if final is not produced.

## Stop-Loss Limits

Stop and report instead of broadening if:

- the previous run artifacts needed for assembly are missing;
- repairing overlay would require changing story, shots, music, visual decisions, or timing;
- render fails after the overlay repair attempt;
- final media lacks video or audio;
- pipeline_home or delivery gate blocks for a reason unrelated to title overlay;
- any step would require editing forbidden zones or repo code/tests/tools.

## Delegated Decisions

- Exact continuation root suffix.
- Whether to correct ffmpeg filter expressions or use PNG overlays.
- Exact title box dimensions and subtitle positioning, as long as title lifecycle remains enter/hold/exit and no persistent side rail.
- Whether to copy prior run artifacts or reconstruct them from construction basis.

## Final Report Requirements

Write:

```text
docs/construction-guides/work-orders/2026-07-08-copyedit-rehearsal-title-overlay-repair-report.md
```

Include:

- Continuation output root and run path.
- Red-first evidence from prior stop-loss.
- Overlay repair method.
- Commands and exit codes.
- Final path or new stop-loss blocker.
- If final exists: duration, streams, ffprobe path, pipeline_home result, delivery gate result.
- Confirmation that story, shots, music basis, certification bridge, and visual decisions were preserved.
- Confirmation that no VoxCPM, narration, story approval, transcript approval, legal approval, Downloads edit, prior run edit, repo code/test/tool edit, or delivery package edit occurred.
- Deviations, blockers, and next recommended work.
