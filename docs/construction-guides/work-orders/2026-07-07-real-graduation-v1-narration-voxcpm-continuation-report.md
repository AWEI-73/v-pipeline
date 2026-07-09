# Real Graduation V1 Narration / VoxCPM Continuation Report

Date: 2026-07-07

## Scope

- Source run: `.tmp\real_graduation_production_candidate_v1_20260707-062900\run`
- Output mode: continuation on the exact V1 run
- Code/tools/tests edited: `false`
- Story reselected: `false`
- Music reselected: `false`
- `story_human_review_decision.json` written: `false`

## Result

- Final video: `.tmp\real_graduation_production_candidate_v1_20260707-062900\run\final.mp4`
- Final audio: `.tmp\real_graduation_production_candidate_v1_20260707-062900\run\final_audio.wav`
- VoxCPM runtime: `ok_to_execute=true`
- Voiceover provider: `voxcpm`
- Voiceover ready: `true`
- Narration segments rendered: `5`
- Narration mixed into final audio/video: `true`
- Delivery gate: `pass=true`
- Pipeline home: `DONE / complete`

This is now a technical delivery candidate from the pipeline gate perspective, but it still requires real user review and legal/music-use review before external publishing.

## VoxCPM Evidence

Artifacts:

- `voxcpm_runtime_check.json`
- `script.json`
- `voiceover_provider_plan.json`
- `subtitle_voiceover_build_handoff.json`
- `narration_manifest.json`
- `voiceover\seg01.wav`
- `voiceover\seg02.wav`
- `voiceover\seg03.wav`
- `voiceover\seg04.wav`
- `voiceover\seg05.wav`

Runtime check:

- `ok_to_execute=true`
- Python: `.venv_voxcpm\Scripts\python.exe`
- Repo: `reference repo\VoxCPM-main`
- GPU available: `true`
- Required imports available: `torch`, `torchaudio`, `transformers`, `soundfile`, `librosa`, `huggingface_hub`

Narration script:

- Segment count: `5`
- Language: `zh-TW`
- Voice style: `warm clear Mandarin narrator`
- Segments:
  - `opening_story`
  - `basic_training`
  - `advanced_training`
  - `physical_activity`
  - `closing_story`

## Audio / Final Media

The original no-narration final was preserved as:

- `.tmp\real_graduation_production_candidate_v1_20260707-062900\run\final_v1_no_narration.mp4`

Updated final:

- `.tmp\real_graduation_production_candidate_v1_20260707-062900\run\final.mp4`

ffprobe:

- Video: `h264`, duration `42.053646`
- Audio: `aac`, duration `41.962000`

Audio mix:

- `music_included=true`
- `narration_included=true`
- `narration_provider=voxcpm`
- Music bed reduced under narration
- Jamendo music retained from V1; no music reselection

Artifacts:

- `narration_mix_report.json`
- `audio_mix_report.json`
- `final_media_ffprobe.json`
- `review_artifacts_manifest.json`

## Delivery Gate / Pipeline Home

Delivery gate:

- Command: `C:\Users\user\miniconda3\python.exe tools\write_delivery_gate_report.py --run ".tmp\real_graduation_production_candidate_v1_20260707-062900\run" --json`
- Exit code: `0`
- Result: `pass=true`, `blocking=[]`

Pipeline home:

- Command: `C:\Users\user\miniconda3\python.exe tools\pipeline_home.py --run ".tmp\real_graduation_production_candidate_v1_20260707-062900\run" --json`
- Exit code: `0`
- Result: `mode=done`, `status=DONE`, `cursor=complete`, reason `delivery gate passed and final.mp4 exists`

## Commands

- `C:\Users\user\miniconda3\python.exe tools\voxcpm_runtime_check.py --out .tmp\real_graduation_production_candidate_v1_20260707-062900\run\voxcpm_runtime_check.json`
  - Exit code: `0`
  - Result: `ok_to_execute=true`
- `C:\Users\user\miniconda3\python.exe -c "... write script.json ..."`
  - Exit code: `0`
  - Result: wrote 5-segment narration script.
- `C:\Users\user\miniconda3\python.exe tools\voxcpm_voiceover_provider.py .tmp\real_graduation_production_candidate_v1_20260707-062900\run\script.json --out-dir .tmp\real_graduation_production_candidate_v1_20260707-062900\run --voice-style "warm clear Mandarin narrator" --device auto --timeout-sec 1200`
  - Exit code: `0`
  - Result: plan-only artifacts written.
- `C:\Users\user\miniconda3\python.exe tools\voxcpm_voiceover_provider.py .tmp\real_graduation_production_candidate_v1_20260707-062900\run\script.json --out-dir .tmp\real_graduation_production_candidate_v1_20260707-062900\run --voice-style "warm clear Mandarin narrator" --device auto --execute --timeout-sec 1200`
  - Exit code: `0`
  - Result: `voiceover_ready=true`, 5 wav files rendered.
- `C:\Users\user\miniconda3\python.exe -c "... mix VoxCPM narration into final_audio.wav/final.mp4 ..."`
  - Exit code: `0`
  - Result: final video/audio updated with narration.
- `ffprobe -v error -show_entries stream=codec_type,codec_name,duration -of json ".tmp\real_graduation_production_candidate_v1_20260707-062900\run\final.mp4"`
  - Exit code: `0`
  - Result: h264 video + aac audio.
- `C:\Users\user\miniconda3\python.exe tools\write_delivery_gate_report.py --run ".tmp\real_graduation_production_candidate_v1_20260707-062900\run" --json`
  - Exit code before normalization: `1`
  - Result: exposed run-local artifact manifest path/schema issues.
- `C:\Users\user\miniconda3\python.exe -c "... normalize artifact_manifest/subtitle_voiceover/narration refs ..."`
  - Exit code: `0`
  - Result: normalized run-local paths and added narration `audio_ref` / `file` refs.
- `C:\Users\user\miniconda3\python.exe -c "... update delivery_requirements requires_narration=true ..."`
  - Exit code: `0`
  - Result: requirements now truthfully declare VoxCPM narration.
- `C:\Users\user\miniconda3\python.exe tools\write_delivery_gate_report.py --run ".tmp\real_graduation_production_candidate_v1_20260707-062900\run" --json`
  - Exit code: `0`
  - Result: `pass=true`.
- `C:\Users\user\miniconda3\python.exe tools\pipeline_home.py --run ".tmp\real_graduation_production_candidate_v1_20260707-062900\run" --json`
  - Exit code: `0`
  - Result: `DONE / complete`.
- Final artifact check
  - Exit code: `0`
  - Result: narration included, music included, UTF-8 clean, no story approval artifact.
- `git status --short --branch --untracked-files=all`
  - Exit code: `0`
  - Result: only untracked work-order/report docs from this flow are visible.
- `git diff --check`
  - Exit code: `0`
  - Result: no whitespace errors.

## Final Artifact Check

- Delivery gate pass: `true`
- Voice segments: `5`
- Rendered voice files: `5`
- `narration_included=true`
- `music_included=true`
- `story_human_review_decision.json` exists: `false`
- Legal/music review required: `true`
- Old source-folder music final BGM: `false`
- UTF-8/no-corruption: `true`
- Bad text artifacts: `[]`

Integrator follow-up:

- `final_media_ffprobe.json` initially had a trailing literal `\n` after the
  JSON object. The run-local evidence artifact was corrected to valid UTF-8
  JSON, parsed successfully, and `pipeline_home.py` plus
  `write_delivery_gate_report.py` were rerun successfully.

## Remaining Limitations

- Real user story/delivery approval is still required.
- Jamendo `BY-NC-ND 3.0` metadata is recorded, but legal/music-use approval is not granted by this run.
- Title rail treatment remains a technical ffmpeg implementation, not high-end motion graphics.
- VoxCPM narration was generated successfully but still needs human review for tone, pronunciation, pacing, and story fit.

## Next Recommended Work

Run human review packaging for this exact candidate: provide `final.mp4`, contact sheet/frame evidence, narration manifest, music evidence, and delivery gate report to the real reviewer. If approved, write the proper human approval artifact through the existing story/delivery review path and keep legal/music-use review separate.
