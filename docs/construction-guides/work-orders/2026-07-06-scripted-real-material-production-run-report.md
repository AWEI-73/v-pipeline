# Scripted Real-Material Production Run Report

Date: 2026-07-06

## Output root

- Output root: `.tmp/scripted_real_material_production_run_20260706-131200`
- Run path: `C:\Users\user\Desktop\video_pipeline\.tmp\scripted_real_material_production_run_20260706-131200\run`
- Report path: `docs/construction-guides/work-orders/2026-07-06-scripted-real-material-production-run-report.md`

## Story contract

- Contract artifact: `story_contract.json`
- Working title: `訓練現場：從集合到成果`
- Target duration: 45-75 seconds
- Final rendered duration: 65.064 seconds
- Required beats present: 5
- Agent-filled fields:
  - `scenario_note`: simulated client scenario details beyond the work order are provisional and need human confirmation.
  - Several story-to-material beat matches are marked `needs_human_confirmation=true` because clip meaning was inferred from source filenames and visual/story position rather than confirmed by a human.

## Source preflight

- Source: `C:\Users\user\Downloads\微電影素材\_整理後`
- `exists=true`, `is_dir=true`, `file_count=306`
- Evidence: `source_preflight.json`

## Story-to-material map

- Map artifact: `story_to_material_map.json`
- Clip count: 8 real source clips copied into run-local `assets/materials/`
- Timeline duration from plan: 56.0 seconds; rendered silent visual duration: 65.042 seconds.
- Beat coverage:
  - `establish_gathering`: aerial/context clip and team chant clip
  - `source_speech_instruction`: `scripted_003` from the director/instructor speech source
  - `training_process_detail`: `2基本.mp4`, `3丙級.mp4`
  - `group_practice_collaboration`: `6課餘活動.mp4`
  - `concrete_outcome_review`: `7感性收尾.mp4`, `67期結訓影片-終.mp4`

## Source speech

- Source speech status: `preserved`
- Evidence: `source_speech_preservation_report.json`
- Preserved audio: `source_speech_director.wav`
- Timeline placement: 14.0-24.977 seconds
- Source clip: `assets/materials/scripted_003.mp4`
- ASR/probe: `source_speech_probe_report.json`
- ASR preview: `第66期的養成班學員們 大家好 首先恭喜各位順利節業 再經過五個半月的 層層嚴格訓練`
- Source speech was not replaced by VoxCPM.
- Human transcript confirmation remains required.

## Narration mapping

- Narration plan: `narration_plan.json`
- VoxCPM runtime: `voxcpm_runtime_check.json`, `ok_to_execute=true`
- VoxCPM execution: `voiceover_provider_plan.json`, `error_count=0`
- Narration segment count: 3
- Mapping:
  - `opening_bridge`: `establish_gathering`, 1.0-7.0 seconds
  - `process_bridge`: `training_process_detail` and `group_practice_collaboration`, 28.0-38.0 seconds
  - `outcome_bridge`: `concrete_outcome_review`, 51.0-60.0 seconds
- The narration plan avoids the preserved source speech window.

## Subtitle alignment

- Subtitle file: `subtitles.srt`
- Alignment report: `subtitle_audio_alignment_report.json`
- Reported alignment result: `ok=true`
- Subtitle count: 4
- Source speech subtitle uses ASR transcript and is marked as requiring human transcript confirmation.
- Delivery gate later found `subtitles.srt` contains mojibake placeholder question marks in the VoxCPM narration subtitle lines. Therefore the final delivery status is blocked even though the alignment report exists.

## Music evidence

- Music manifest: `music_manifest.json`
- Music needs: 2
- Download/import count: 2
- Tracks:
  - `documentary_opening`: Jamendo `jamendo_documentary_opening_1996352`, `Peaceful Calm Documentary`, `1551988` bytes, license metadata `http://creativecommons.org/licenses/by-nc-nd/3.0/`
  - `process_momentum`: Jamendo `jamendo_process_momentum_1678205`, `FrenchMan - Song (instrumental)`, `2143744` bytes, license metadata `http://creativecommons.org/licenses/by-nc-nd/3.0/`
- Probe report: `soundtrack_probe_report.json`
- Probe result: `pass=true`, `track_count=2`
- Both tracks had only low-density ASR hits and were mixed from instrumental windows/source offsets.
- Legal/music-use review remains required.

## Audio mix

- Audio mix report: `audio_mix_report.json`
- `ok=true`
- `narration_included=true`
- `music_included=true`
- Track count: 6
- Tracks include:
  - 1 preserved source speech track
  - 3 VoxCPM narration tracks
  - 2 ducked music tracks
- Duration alignment: `matches_video_duration`, output duration `65.042`

## Final media

- Final media path: `C:\Users\user\Desktop\video_pipeline\.tmp\scripted_real_material_production_run_20260706-131200\run\final.mp4`
- Final media ffprobe: `review_artifacts/final_media_ffprobe.json`
- Streams: video + audio
- Duration: 65.064 seconds
- Final audio: `final_audio.wav`
- Final audio ffprobe: `review_artifacts/final_audio_ffprobe.json`

## Story-to-final alignment

- Alignment artifact: `story_to_final_alignment_report.json`
- Result: `ok=true`
- Includes story beats, selected timeline spans, narration mapping, and preserved source speech placement.

## Delivery gate

- Delivery gate artifact: `delivery_gate.json`
- Delivery gate result: `pass=false`
- Blocking rules:
  - `corrupt_narration_manifest`: `narration_manifest.json contains mojibake placeholders`
  - `corrupt_subtitles`: `subtitles.srt appears to contain mojibake placeholders`
- Next action from gate: `regenerate_narration_manifest_utf8`
- Waivers applied: `[]`
- Pipeline home after gate: `status=REPAIR`, next `regenerate_narration_manifest_utf8`
- This run is blocked, not a true scripted delivery candidate.

## Verify artifacts

- `review_artifacts/frame_contact_sheet_0_5s.jpg`
- `review_artifacts/final_media_ffprobe.json`
- `review_artifacts/final_audio_ffprobe.json`
- `review_artifacts/audio_track_mix_evidence.json`
- `review_artifacts/review_artifacts_manifest.json`
- `story_to_final_alignment_report.json`
- `source_speech_preservation_report.json`
- `subtitle_audio_alignment_report.json`
- `frame_evidence.json`

## Commands and exit codes

| Step | Command summary | Exit |
| --- | --- | --- |
| Source preflight | Unicode-escaped source path preflight with `C:\Users\user\miniconda3\python.exe -` | 0 |
| Story contract / visual plan | Wrote `story_contract.json`, `story_to_material_map.json`, `rough_cut_plan.json`, `render_handoff.json` using `C:\Users\user\miniconda3\python.exe -` | timed out after artifacts were written |
| Silent visual render | `C:\Users\user\miniconda3\python.exe tools\rough_cut_plan_execute.py --rough-cut-plan ... --out ... --report ... --timeout-sec 900 --fps 24` | 0 |
| Source speech extract | `ffmpeg -ss 0 -t 11 -i ...scripted_003.mp4 -vn -ac 2 -ar 48000 source_speech_director.wav` | 0 |
| Source speech probe | `C:\Users\user\miniconda3\python.exe tools\soundtrack_probe.py --audio source_speech_director.wav --out source_speech_probe_report.json --enable-asr --json` | 0 |
| Script/narration plan | `C:\Users\user\miniconda3\python.exe -` | 0 |
| VoxCPM runtime | `C:\Users\user\miniconda3\python.exe tools\voxcpm_runtime_check.py --out ...` | 0 |
| VoxCPM execute | `C:\Users\user\miniconda3\python.exe tools\voxcpm_voiceover_provider.py script.json --out-dir ... --execute` | 0 |
| Subtitle alignment prep | `C:\Users\user\miniconda3\python.exe -` | 0 |
| Subtitle/voiceover accept | `C:\Users\user\miniconda3\python.exe tools\subtitle_voiceover_handoff_accept.py ... --json` | 0 |
| Music intent / plan | `C:\Users\user\miniconda3\python.exe -` | 0 |
| Soundtrack arranger | `C:\Users\user\miniconda3\python.exe tools\soundtrack_arranger.py --input scripted_music_intent.json --out-dir ... --json` | 0 |
| Provider search | `C:\Users\user\miniconda3\python.exe video_tools.py soundtrack-provider-search --plan ... --providers jamendo,pixabay --limit 5` | 0 |
| Download opening music | `C:\Users\user\miniconda3\python.exe video_tools.py soundtrack-provider-download --candidate-id jamendo_documentary_opening_1996352 ...` | 0 |
| Download process music | `C:\Users\user\miniconda3\python.exe video_tools.py soundtrack-provider-download --candidate-id jamendo_process_momentum_1678205 ...` | 0 |
| Probe opening music | `C:\Users\user\miniconda3\python.exe tools\soundtrack_probe.py --audio ... --enable-asr --json` | 0 |
| Probe process music | `C:\Users\user\miniconda3\python.exe tools\soundtrack_probe.py --audio ... --enable-asr --json` | 0 |
| Audio handoff accept | `C:\Users\user\miniconda3\python.exe video_tools.py soundtrack-audio-handoff-accept ...` | 0 |
| Audio mix execute | `C:\Users\user\miniconda3\python.exe tools\audio_mix_plan_execute.py --plan ... --acceptance ... --out-dir ... --json` | 0 |
| Final assemble | `C:\Users\user\miniconda3\python.exe tools\final_av_assemble.py --video ... --audio ... --out final.mp4 --report ... --source-audio-policy mixed --json` | 0 |
| Contact sheet | `ffmpeg -i final.mp4 -vf fps=2,scale=320:-1,tile=10x14 ...` | 0 |
| Verify artifact prep | `C:\Users\user\miniconda3\python.exe -` | 0 |
| Pipeline home | `C:\Users\user\miniconda3\python.exe tools\pipeline_home.py --run "<RUN_DIR>" --json` | 0 |
| Delivery gate | `C:\Users\user\miniconda3\python.exe tools\write_delivery_gate_report.py --run "<RUN_DIR>" --json` | 1 |
| Acceptance contract/source map | Work-order command 1 with `<RUN_DIR>` substituted | 0 |
| Acceptance speech/narration/subtitle | Work-order command 2 with `<RUN_DIR>` substituted | 0 |
| Acceptance music/final media | Work-order command 3 with `<RUN_DIR>` substituted | 0 |
| Acceptance pipeline home | Work-order command 4 with `<RUN_DIR>` substituted | 0 |
| Acceptance delivery gate | Work-order command 5 with `<RUN_DIR>` substituted | 1 |

## Deviations

- Direct Chinese source filenames in PowerShell/Python here-strings became mojibake, so source selection was changed to use Unicode escapes and filename discovery. This only affected fresh-run artifact creation and did not modify source material.
- The story contract / visual plan command exceeded the shell timeout while copying large run-local assets, but inspection showed the assets and JSON artifacts had been written. Subsequent render and acceptance checks used those run-local artifacts.
- The delivery gate block was not repaired because the work order says to stop at delivery block and report the true breakpoint.

## Blockers

- First true blocker: delivery gate blocked on corrupt UTF-8 content in `narration_manifest.json` and `subtitles.srt`.
- The corruption is visible as `?` placeholders in the VoxCPM narration text and subtitle lines.

## Candidate status

This is blocked. It is not a true scripted delivery candidate. The run does prove a technical path through real source speech preservation, VoxCPM audio generation, real music download/probe, audio mix, final media assembly, and verify artifacts, but delivery is blocked by corrupted narration/subtitle text artifacts.

Real user approval is still required. Legal/music-use review is still required.

## Next recommended work

Run a focused UTF-8 script/subtitle repair round for the scripted path: regenerate `script.json`, `narration_manifest.json`, and `subtitles.srt` from Unicode-safe text construction, rerun subtitle/voiceover acceptance, audio mix if timestamps change, final assembly if needed, then rerun delivery gate on a fresh scripted run.
