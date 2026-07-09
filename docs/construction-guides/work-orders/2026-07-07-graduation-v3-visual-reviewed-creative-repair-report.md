# Graduation V3 Visual-Reviewed Creative Repair Report

Date: 2026-07-07

## Output

- Output root: `.tmp/graduation_v3_visual_reviewed_creative_repair_20260707-161251`
- V3 run path: `.tmp/graduation_v3_visual_reviewed_creative_repair_20260707-161251/run`
- Final media: not created
- Stop-loss artifact: `.tmp/graduation_v3_visual_reviewed_creative_repair_20260707-161251/run/v3_stop_loss_report.json`
- Final artifact check: `.tmp/graduation_v3_visual_reviewed_creative_repair_20260707-161251/run/v3_final_artifact_check.json`

## Changed Files / Artifacts

- Repo report written:
  `docs/construction-guides/work-orders/2026-07-07-graduation-v3-visual-reviewed-creative-repair-report.md`
- Run-local V3 artifacts under:
  `.tmp/graduation_v3_visual_reviewed_creative_repair_20260707-161251/run`
- No repo code, tools, tests, skills, V1/V2 runs, Downloads, deliveries, env/venv,
  reference repo, or git state were modified.

## V2 Unchanged Proof

- Snapshot before: `v2_snapshot_before.json`
- Final artifact check: `v2_unchanged=true`
- V2 run was read only throughout this worker run.

## Visual Selection Review / Gate

- Candidates: `visual_selection_candidates.json`
- Review artifact: `visual_selection_review.json`
- Gate artifact: `visual_selection_gate_check/visual_selection_gate.json`
- Gate result: `pass=true`
- Accepted visual evidence count: 3
- Blocking rules: none

Render-facing accepted selections:

- `newcomer_training_start`: `工安早會/工安早會合照/IMG_1973.JPG`
  - Evidence frame: `candidate_frames/candidate_01.jpg`
  - Reason: wide trainee roll-call frame; officials are side/background, not supervisor/director/portrait-primary.
- `basic_training`: `工安體感/IMG_9544.MOV`
  - Evidence frame: `candidate_frames/candidate_03.jpg`
  - Reason: hands-on safety-experience training with trainees and equipment; not supervisor/director/portrait-primary.
- `supervisor_source_speech`: `主任勉勵/IMG_2141.MOV`
  - Evidence frame: `candidate_frames/candidate_08.jpg`
  - Reason: talking-head supervisor source speech with audio/speech evidence requirement recorded.

Rejected V2 problem candidates:

- `newcomer_training_start`: `工安早會/IMG_2120.JPG`
- `basic_training`: `工安早會/IMG_2124.JPG`

Recorded in `visual_selection_repick_decisions.json`.

## Narration / Voice Variants

- Narration script: `v3_narration_script.json`
- Clean text precheck: `clean=true`
- Forbidden setup/style terms checked:
  `普通話`, `設定`, `參數`, `voice`, `style`, `prompt`, `Mandarin narrator`
- Voice variant A command: failed
  - Style/control: `warm clear documentary delivery`
  - Exit code: 1
  - Provider detail: segment failed with return code `3221225477`; CPU retry also returned `3221225477`.
- Voice variant B command: failed
  - Style/control: `firm documentary delivery`
  - Exit code: 1
  - Provider detail: segment failed with return code `3221225477`; CPU retry also returned `3221225477`.
- Final selected voiceover set: not attempted after both required short variants failed.

Stop-loss reason:

`voxcpm_voice_generation_failed_before_final_render`

No fake narration, fallback audio, or hidden/muted setup text was used.

## Supervisor Source-Audio Evidence

- Selected source speech clip: `主任勉勵/IMG_2141.MOV`
- Visual review accepted the clip as supervisor source speech.
- Original source audio was not mixed because final assembly stopped before render.
- Final artifact check records `supervisor_source_audio_preserved=false` with reason:
  render stopped after VoxCPM voice generation failure.

## Title / Opener / Closer

V3 planned to use the V2 no-side-rail direction and repair further with short
designed treatments, but final title/opener/closer assembly did not run because
the required narration branch stopped first. No final visual claim is made.

## Final Media / Delivery

- `final_v3.mp4`: does not exist.
- `final.mp4`: not created for V3.
- ffprobe result: exit 1, file not found.
- Delivery gate: exit 1, blocked by missing video candidate.
- Pipeline home: exit 0, `REPAIR / subtitle_voiceover_handoff`, reason:
  subtitle/voiceover handoff artifacts are incomplete.
- `story_human_review_decision.json`: not written.

## Commands

- `C:\Users\user\miniconda3\python.exe tools\visual_selection_gate.py --run ".tmp\graduation_v3_visual_reviewed_creative_repair_20260707-161251\run" --out-dir ".tmp\graduation_v3_visual_reviewed_creative_repair_20260707-161251\run\visual_selection_gate_check" --json` -> exit 0, `pass=true`
- `C:\Users\user\miniconda3\python.exe tools\voxcpm_runtime_check.py --out .tmp\graduation_v3_visual_reviewed_creative_repair_20260707-161251\run\voxcpm_runtime_check.json` -> exit 0, `ok_to_execute=true`
- `C:\Users\user\miniconda3\python.exe tools\voxcpm_voiceover_provider.py ...v3_voice_variant_A_sample_script.json --out-dir ...\voice_variant_A --voice-style "warm clear documentary delivery" --device auto --execute --timeout-sec 1200` -> exit 1
- `C:\Users\user\miniconda3\python.exe tools\voxcpm_voiceover_provider.py ...v3_voice_variant_B_sample_script.json --out-dir ...\voice_variant_B --voice-style "firm documentary delivery" --device auto --execute --timeout-sec 1200` -> exit 1
- `C:\Users\user\miniconda3\python.exe tools\pipeline_home.py --run ".tmp\graduation_v3_visual_reviewed_creative_repair_20260707-161251\run" --json` -> exit 0, `status=REPAIR`
- `C:\Users\user\miniconda3\python.exe tools\write_delivery_gate_report.py --run ".tmp\graduation_v3_visual_reviewed_creative_repair_20260707-161251\run" --json` -> exit 1, missing video candidate
- `ffprobe -v error -show_entries stream=codec_type,codec_name,duration -of json ".tmp\graduation_v3_visual_reviewed_creative_repair_20260707-161251\run\final_v3.mp4"` -> exit 1, file not found
- `git diff --check` -> exit 0; Git emitted LF-to-CRLF warnings only.
- Final artifact check with pinned Python -> exit 0

## Final Artifact Check

`v3_final_artifact_check.json` reports:

- `v2_unchanged=true`
- `visual_selection_review_exists=true`
- `visual_selection_gate_pass=true`
- `clean_narration_text_check=true`
- `supervisor_source_audio_preserved=false`
- `final_video_audio_stream_check=false`
- `final_v3_exists=false`
- `story_human_review_decision_exists=false`
- `utf8_no_corruption=true`

## Deviations / Blockers

- Required V3 `final_v3.mp4` was not produced because both required VoxCPM short
  voice variants failed during real generation.
- Delivery gate was run and honestly blocks because no final video candidate
  exists.
- No waiver was used.
- No repo code/tool/test/provider changes were made to force a pass.

## Next Recommended Work

Investigate the VoxCPM runtime crash for this clean V3 narration script,
specifically return code `3221225477` on both CUDA and CPU retry. After the
voiceover provider can generate at least the two required short variants,
resume from this V3 run's visual-selection review artifacts and render the V3
candidate without reusing the rejected V2 newcomer/basic candidates.
