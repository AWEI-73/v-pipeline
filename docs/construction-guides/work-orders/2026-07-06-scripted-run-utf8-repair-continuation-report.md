# Scripted Run UTF-8 Repair Continuation Report

Date: 2026-07-06

## Run path

- Run path: `C:\Users\user\Desktop\video_pipeline\.tmp\scripted_real_material_production_run_20260706-131200\run`
- Repair report: `docs/construction-guides/work-orders/2026-07-06-scripted-run-utf8-repair-continuation-report.md`
- This was a run-local repair continuation, not a new production run.

## Pre-repair blocker snapshot

- Snapshot artifact: `utf8_repair_blocker_snapshot.json`
- Archive folder: `repair_archive_utf8_20260706-134700`
- Pre-repair delivery gate: `pass=false`
- Blocking rules:
  - `corrupt_narration_manifest`
  - `corrupt_subtitles`
- Pre-repair question mark counts:
  - `script.json`: 95, repeated question marks present
  - `narration_manifest.json`: 190, repeated question marks present
  - `subtitles.srt`: 95, repeated question marks present
  - `subtitle_audio_alignment_report.json`: 0

## UTF-8 repair

- Rewrote `script.json` using Unicode escapes, not raw Chinese through PowerShell stdin.
- `utf8_repair_script_check.json`: CJK present, replacement char absent, repeated `????` absent, question mark count 0.
- Rebuilt `narration_manifest.json`, `subtitles.srt`, and `subtitle_audio_alignment_report.json`.
- `utf8_repair_subtitle_check.json`: all checked artifacts have CJK, no replacement char, no repeated `????`, question mark count 0.

## VoxCPM

- Old corrupted VoxCPM artifacts were archived under `repair_archive_utf8_20260706-134700`.
- Runtime check command: `C:\Users\user\miniconda3\python.exe tools\voxcpm_runtime_check.py --out "<RUN_DIR>\voxcpm_runtime_check.json"`
- Runtime result: `ok_to_execute=true`
- VoxCPM rerun command: `C:\Users\user\miniconda3\python.exe tools\voxcpm_voiceover_provider.py "<RUN_DIR>\script.json" --out-dir "<RUN_DIR>" --execute`
- VoxCPM result: `ok=true`, `voiceover_ready=true`, `error_count=0`
- Regenerated voice files:
  - `voiceover\seg01.wav`, 368684 bytes
  - `voiceover\seg02.wav`, 286764 bytes
  - `voiceover\seg03.wav`, 404524 bytes
- `utf8_repair_voxcpm_check.json`: manifest has CJK, no repeated `????`, all three voice files exist and are non-empty.

## Source speech

- Source speech status: `preserved`
- Evidence: `source_speech_preservation_report.json`
- Preserved source speech file: `source_speech_director.wav`
- Source speech was not replaced by VoxCPM.
- Human transcript confirmation remains required for the ASR subtitle.

## Subtitle alignment

- Subtitle file: `subtitles.srt`
- Alignment report: `subtitle_audio_alignment_report.json`
- Result: `ok=true`
- Subtitle/voiceover acceptance: `subtitle_voiceover_handoff_acceptance.json` has `ok=true`
- `subtitle_voiceover_build_handoff.json` restored `voice_files` for the three regenerated VoxCPM files.

## Audio mix and final media

- Audio mix was rebuilt from existing music downloads/probes, preserved source speech, and regenerated VoxCPM files.
- Audio mix report: `audio_mix_report.json`
- Audio mix result: `ok=true`
- `narration_included=true`
- `music_included=true`
- Track count: 6
- Final audio: `final_audio.wav`
- Final media: `final.mp4`
- Final file size: 19918456 bytes
- Final media ffprobe: `review_artifacts/final_media_ffprobe.json`
- Final media streams: video + audio
- Final duration: 65.064 seconds

## Pipeline home

- Before rewriting delivery gate, `pipeline_home` still read the old gate and returned `status=REPAIR`.
- After `write_delivery_gate_report.py`, `pipeline_home` returned `status=DONE`, cursor `complete`, reason `delivery gate passed and final.mp4 exists`.

## Delivery gate

- Delivery gate command: `C:\Users\user\miniconda3\python.exe tools\write_delivery_gate_report.py --run "<RUN_DIR>" --json`
- Result: `pass=true`
- Blocking rules: `[]`
- Warnings: `[]`
- Waivers applied: `[]`
- Summary: audio, narration, music, subtitles required; video and audio streams present; video duration `65.041667`, audio duration `65.042`.

## Verify artifacts

- `utf8_repair_blocker_snapshot.json`
- `utf8_repair_script_check.json`
- `utf8_repair_voxcpm_check.json`
- `utf8_repair_subtitle_check.json`
- `review_artifacts/final_media_ffprobe.json`
- `review_artifacts/final_audio_ffprobe.json`
- `review_artifacts/frame_contact_sheet_0_5s.jpg`
- `review_artifacts/audio_track_mix_evidence.json`
- `review_artifacts/review_artifacts_manifest.json`
- `story_to_final_alignment_report.json`
- `frame_evidence.json`

## Commands and exit codes

| Step | Command summary | Exit |
| --- | --- | --- |
| Blocker snapshot/archive | `C:\Users\user\miniconda3\python.exe -` | 0 |
| Rewrite `script.json` and archive old VoxCPM outputs | `C:\Users\user\miniconda3\python.exe -` | 0 |
| VoxCPM runtime check | `C:\Users\user\miniconda3\python.exe tools\voxcpm_runtime_check.py --out ...` | 0 |
| VoxCPM execute | `C:\Users\user\miniconda3\python.exe tools\voxcpm_voiceover_provider.py ... --execute` | 0 |
| VoxCPM UTF-8/file check | `C:\Users\user\miniconda3\python.exe -` | 0 |
| Rebuild narration/subtitles/alignment | `C:\Users\user\miniconda3\python.exe -` | 0 |
| Subtitle/voiceover acceptance | `C:\Users\user\miniconda3\python.exe tools\subtitle_voiceover_handoff_accept.py ... --json` | 0 |
| Restore build handoff `voice_files` | `C:\Users\user\miniconda3\python.exe -` | 0 |
| Audio mix plan rebuild | `C:\Users\user\miniconda3\python.exe -` | 0 |
| Audio mix execute | `C:\Users\user\miniconda3\python.exe tools\audio_mix_plan_execute.py --plan ... --acceptance ... --out-dir ... --json` | 0 |
| Final AV assemble | `C:\Users\user\miniconda3\python.exe tools\final_av_assemble.py --video ... --audio ... --out ... --report ... --source-audio-policy mixed --json` | 0 |
| Contact sheet refresh | `ffmpeg -y -hide_banner -loglevel error -i final.mp4 -vf fps=2,scale=320:-1,tile=10x14 ...` | 0 |
| Verify artifact refresh | `C:\Users\user\miniconda3\python.exe -` | 0 |
| Pipeline home before gate rewrite | `C:\Users\user\miniconda3\python.exe tools\pipeline_home.py --run "<RUN_DIR>" --json` | 0 |
| Delivery gate | `C:\Users\user\miniconda3\python.exe tools\write_delivery_gate_report.py --run "<RUN_DIR>" --json` | 0 |
| Pipeline home after gate rewrite | `C:\Users\user\miniconda3\python.exe tools\pipeline_home.py --run "<RUN_DIR>" --json` | 0 |
| Acceptance UTF-8/CJK check | Work-order command 1 with `<RUN_DIR>` substituted | 0 |
| Acceptance speech/narration check | Work-order command 2 with `<RUN_DIR>` substituted | 0 |
| Acceptance final media check | Work-order command 3 with `<RUN_DIR>` substituted | 0 |
| Acceptance pipeline home | Work-order command 4 with `<RUN_DIR>` substituted | 0 |
| Acceptance delivery gate | Work-order command 5 with `<RUN_DIR>` substituted | 0 |

## Deviations

- The first `pipeline_home` in this repair still reported the old `REPAIR` state because it read the pre-repair `delivery_gate.json`. After writing the repaired delivery gate, `pipeline_home` reported `DONE`.
- The repair rebuilt the audio mix plan manually from existing run-local accepted music/source speech/narration artifacts because only the narration/subtitle branch changed. Music downloads/probes, story contract, story map, visual timeline, and source speech were preserved.

## Blockers

- No remaining delivery blocker after repair.
- Real user approval is still required.
- Legal/music-use review is still required.

## Candidate status

The result is now a scripted technical candidate. Delivery gate passes with no waivers, but it is not final human approval and not legal/music-use approval.

## Next recommended work

Run human review on the scripted technical candidate: confirm story beat accuracy, source speech transcript, VoxCPM narration wording/timing, subtitle readability, and Jamendo license suitability for the intended use before any formal delivery promotion.
