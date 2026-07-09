# 2026-07-08 Music-Subtitle-Only Five-Minute Render Rehearsal

## Goal

Produce a 240-300 second `music_subtitle_only` five-minute technical review candidate from the shot-level material proof package, or stop with a real blocker.

This is a render rehearsal, not final delivery. It must prove whether the current shot-level proof package can become a coherent five-minute graduation film without VoxCPM narration and without relying on unapproved supervisor source speech transcript.

## Construction Basis

Use these inputs as read-only evidence:

- `.tmp\shot_level_material_proof_completion_20260708-071727`
- `.tmp\soul_first_real_material_planning_20260708-060509`
- `C:\Users\user\Downloads\微電影素材\_整理後`

The shot-level package is the only render-facing material proof basis. Do not re-decide the story from scratch.

## Owner Zone

Editable paths:

- New output root under `.tmp\music_subtitle_only_five_minute_rehearsal_*`
- Run-local artifacts inside that fresh output root
- Run-local render/review artifacts produced by this rehearsal
- `docs/construction-guides/work-orders/2026-07-08-music-subtitle-only-five-minute-render-rehearsal-report.md`

## Forbidden Zone

Read-only paths:

- `C:\Users\user\Downloads\微電影素材\_整理後`
- `.tmp\shot_level_material_proof_completion_20260708-071727`
- `.tmp\soul_first_real_material_planning_20260708-060509`
- Existing `.tmp\graduation_v*` runs
- Existing `.tmp\v6_*` runs
- Existing `.tmp\voxcpm_provider_leadin_artifact_diagnostic_*` runs
- `deliveries\`
- `.env`, `.env.*`
- `.venv_voxcpm\`
- `reference repo\`
- VoxCPM reference/source repository
- Existing final media artifacts
- `story_human_review_decision.json` in any run
- Git branch/commit/push operations
- Repo code, tests, tools, and skills unless the run hits a blocker that explicitly proves a code defect; do not repair code in this work order

## Required Environment

Use the pinned interpreter for every Python command:

```powershell
C:\Users\user\miniconda3\python.exe
```

Do not use bare `python` or `pytest`.

## Required Route

1. Create a fresh output root and run folder.
2. Read `.tmp\shot_level_material_proof_completion_20260708-071727\render_rehearsal_entry_packet.json`.
3. Confirm the selected profile is `music_subtitle_only`.
4. Confirm this profile does not require VoxCPM.
5. Confirm certification/check is handled by shortening or standards/check bridge language, not by promoting old compiled footage as primary proof.
6. Confirm supervisor source speech remains out of the formal source-speech route unless transcript review is approved. In this rehearsal, do not use supervisor source speech as a formal speech segment.
7. Build a 240-300 second render plan from `shot_level_material_proof_plan.json`.
8. Use only render-facing eligible raw/support shots, or explicitly mark a shot as support/reference with visible caveat.
9. Do not use old compiled/final/music-folder sources as primary proof.
10. Create designed opener and closer sections from approved support/proof shots.
11. Create training module title treatments with enter, readable hold, and exit timing. No persistent side rail.
12. Use music bed with visible `music_use_basis` and legal/music-use caveat. Do not claim legal approval.
13. Create subtitles/title captions for section guidance. Do not create source-speech transcript approval.
14. Render `final_v7.mp4` only if the plan reaches 240-300 seconds and required evidence exists.
15. If final render succeeds, run ffprobe, pipeline_home, and write_delivery_gate_report.
16. If any required evidence is missing or render fails, stop and report the true blocker.

## Hard Rules

- Do not use VoxCPM narration.
- Do not call VoxCPM provider tools.
- Do not write `story_human_review_decision.json`.
- Do not write `human_transcript_review_decision.json`.
- Do not claim supervisor transcript approval.
- Do not claim legal/music approval. Internal rehearsal may use source-folder or human-specified music only when `music_use_basis.status=human_declared_allowed` is recorded.
- Do not use waiver to pass missing narration, subtitle, source speech, visual, or music evidence.
- Do not shorten below 240 seconds and call it a five-minute rehearsal.
- Do not silently use old compiled videos or source-folder music as primary proof.
- Do not mutate the shot-level proof package or prior soul-first package.

## Required Artifacts

Write these run-local artifacts at minimum:

- `source_run_manifest.json`
- `music_subtitle_only_render_plan.json`
- `five_minute_timeline_plan.json`
- `section_timing_actual.json`
- `used_shot_manifest.json`
- `compiled_risk_usage_report.json`
- `certification_shortening_decision.json`
- `music_use_caveat.json`
- `subtitle_title_plan.json`
- `title_effect_lifecycle_plan.json`
- `visual_review_evidence.json`
- `audio_mix_plan.json`
- `review_packet.md`
- `review_packet.json`

If final render succeeds, also write:

- `final_v7.mp4`
- `ffprobe_final_v7.json`
- `title_effect_lifecycle_qa.json`
- `audio_mix_report.json`
- `delivery_gate.json`
- `pipeline_home.json`

If stop-loss happens before final render, write:

- `stop_loss_report.json`
- `final_absence_evidence.json`

## Red-First Verification

Before render planning, capture failing evidence that the previous state was not directly renderable. Acceptable red-first evidence:

- Previous shot-level package says `source_speech_plus_music` is blocked.
- Previous shot-level package says `narrated_optional` is blocked.
- Previous certification/check decision is `thin_blocked_for_primary_proof`.
- Previous output has no `final_v7.mp4`.

Use pinned Python for the precheck and record command, exit code, and output in the report.

## Acceptance Commands

Use pinned Python for every Python command.

Run the render plan/final artifact check command you create for this run. It must verify:

- Fresh output root exists.
- Required run-local artifacts exist.
- `final_v7.mp4` exists only if render succeeded.
- If `final_v7.mp4` exists, duration is 240-300 seconds.
- If `final_v7.mp4` exists, ffprobe shows video and audio streams.
- If `final_v7.mp4` does not exist, `stop_loss_report.json` exists and explains the blocker.
- No `story_human_review_decision.json` exists.
- No `human_transcript_review_decision.json` exists.
- No VoxCPM artifacts were generated by this run.
- Prior shot-level and soul-first outputs were not modified.
- Generated JSON/Markdown/SRT text decodes with UTF-8 and contains no `\ufffd` or suspicious repeated literal question-mark runs.

If final media exists, run:

```powershell
ffprobe -v error -show_entries stream=codec_type,codec_name,duration -show_entries format=duration -of json ".tmp\<fresh_root>\run\final_v7.mp4"
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

Expected exit code is `0` except when a command is intentionally run against an absent final after stop-loss; in that case record the non-zero exit code as stop-loss evidence rather than treating it as pass.

## Stop-Loss Limits

Stop and report instead of forcing a render if:

- Source folder is missing.
- Shot proof package is missing.
- `music_subtitle_only` profile is not allowed.
- The render plan cannot reach 240 seconds without using blocked/compiled footage as primary proof.
- Certification/check cannot be shortened or bridged honestly.
- Subtitles/title plan cannot be produced.
- Music bed/evidence is missing, lacks `music_use_basis` for internal/rehearsal use, or cannot be caveated honestly.
- Render fails or final media lacks video/audio stream.
- Any step would require mutating prior runs, Downloads, env, reference repo, or existing finals.

## Delegated Decisions

- Exact output root suffix.
- Exact shot order and shot durations, as long as the total is 240-300 seconds and shot proof constraints are respected.
- Exact title/subtitle wording, as long as it is truthful and not source-speech transcript approval.
- Exact music bed implementation, as long as `music_use_basis`, source evidence, and legal/music-use caveat are visible.
- Whether to stop before render if the plan cannot satisfy evidence constraints.

## Final Report Requirements

Write:

```text
docs/construction-guides/work-orders/2026-07-08-music-subtitle-only-five-minute-render-rehearsal-report.md
```

Include:

- Output root and run path.
- Commands and exit codes.
- Red-first evidence.
- Selected render profile.
- Final path or blocker.
- If final exists: duration, video/audio stream evidence, and ffprobe path.
- Section timing plan vs actual.
- Used shot summary and compiled-risk usage.
- Certification/check shortening decision.
- Music source, `music_use_basis`, and legal-use caveat.
- Subtitle/title plan and title/effect lifecycle result.
- Review packet path.
- Pipeline home and delivery gate results if reached.
- Confirmation that no VoxCPM, story approval, transcript approval, or legal/music approval was written.
- Deviations, blockers, and next recommended work.
