# Real-Material Full Production Rehearsal After VoxCPM Retry Report

Date: 2026-07-06

## Output root

- Output root: `.tmp/real_material_full_production_rehearsal_after_voxcpm_retry_20260706-124046`
- Run path: `C:\Users\user\Desktop\video_pipeline\.tmp\real_material_full_production_rehearsal_after_voxcpm_retry_20260706-124046\run`
- Report path: `docs/construction-guides/work-orders/2026-07-06-real-material-full-production-rehearsal-after-voxcpm-retry-report.md`

## Source preflight

- Source: `C:\Users\user\Downloads\微電影素材\_整理後`
- `exists=true`, `is_dir=true`, `file_count=306`
- Evidence: `source_preflight.json`

## Visual run

- Fresh material-first run was built from the real source folder, not from the previous blocked run.
- Clip count: 8 real source clips copied into run-local `assets/materials/`.
- Visual duration: 40.0 seconds.
- Silent visual: `final_video_silent.mp4`
- Run-local planning evidence: `materials_db.json`, `rough_cut_plan.json`, `timeline_build.json`, `render_handoff.json`, `real_material_source_intake_report.json`

## VoxCPM

- Runtime check: `ok_to_execute=true`
- Runtime Python: `C:\Users\user\Desktop\video_pipeline\.venv_voxcpm\Scripts\python.exe`
- Missing modules: `[]`
- Segment count: 3
- Rendered file count: 3
- Files:
  - `voiceover\seg01.wav` (`276524` bytes)
  - `voiceover\seg02.wav` (`304684` bytes)
  - `voiceover\seg03.wav` (`401964` bytes)
- CPU retry evidence: no CPU retry occurred in this fresh run. `voiceover_provider_plan.json` shows all three segments rendered and `errors=[]`, `fallback_used=false`.
- Voiceover handoff: `subtitle_voiceover_handoff_acceptance.json` has `ok=true`, `selected_provider=voxcpm`, `fallback_allowed=false`, `fallback_used=false`.

## Music downloads

- Music needs count: 2 (`opening_underlay`, `training_momentum`)
- Real download/import count: 2
- Provider path used branch env bootstrap; `soundtrack_branch_env_probe.json` recorded Jamendo present, Pixabay present, yt-dlp path/version present, and `secrets_redacted=true`.
- Downloaded/imported tracks:
  - `opening_underlay`: Jamendo `jamendo_opening_underlay_2003897`, title `Hopeful Corporate`, URL `https://www.jamendo.com/track/2003897`, local file `audio\sources\jamendo_opening_underlay_2003897.mp3`, size `1848785`, license metadata `http://creativecommons.org/licenses/by-nc-nd/3.0/`
  - `training_momentum`: Jamendo `jamendo_training_momentum_1943774`, title `Energetic Motivational Corporate Pop`, URL `https://www.jamendo.com/track/1943774`, local file `audio\sources\jamendo_training_momentum_1943774.mp3`, size `1985448`, license metadata `http://creativecommons.org/licenses/by-nc-nd/3.0/`
- Synthetic generated music was not counted or used.
- Legal/music-use review is still required because the tracks are sourceable candidates, not final cleared client/legal approvals.

## Music probes

- Combined probe: `soundtrack_probe_report.json`
- Probe result: `pass=true`, `track_count=2`, vocal clearance `blocked=false`
- `opening_underlay`: pass, duration `152.059`, ASR method `faster_whisper`, low vocal density, vocal ratio `0.014`; mix used the instrumental window after `3.68s`.
- `training_momentum`: pass, duration `163.579`, ASR method `faster_whisper`, no vocals, vocal ratio `0.0`.

## Audio mix

- Mix report: `audio_mix_report.json`
- `ok=true`
- Duration: `40.0`
- `narration_included=true`
- `music_included=true`
- Track count: 5
- Mean/peak: `-20.8 dBFS` / `-1.5 dBFS`
- Ducking: applied to music under narration.
- Audio evidence: `review_artifacts/audio_track_mix_evidence.json`

## Final media

- Final media path: `C:\Users\user\Desktop\video_pipeline\.tmp\real_material_full_production_rehearsal_after_voxcpm_retry_20260706-124046\run\final.mp4`
- Final file size: `5633541` bytes
- ffprobe summary: `duration=40.022`, `nb_streams=2`, streams include `video` and `audio`
- Final audio: `final_audio.wav`
- Assembly report: `assembly_report.json`

## Pipeline home

- First post-render check before delivery gate write: `status=RUN`, cursor `subtitle_voiceover_build_handoff`, next `continue_build_or_material_gate`.
- Acceptance rerun after delivery gate write: `status=DONE`, cursor `complete`, reason `delivery gate passed and final.mp4 exists`.

## Delivery gate

- Delivery gate artifact: `delivery_gate.json`
- Result: `pass=true`
- Blocking rules: `[]`
- Warnings: `[]`
- Waivers applied: `[]`
- Summary: audio, narration, music, subtitles required; video and audio streams present; video/audio duration `40.0`.
- This is a technical delivery candidate only. It is not real user approval and not legal/music-use approval.

## Review artifacts

- `review_artifacts/final_media_ffprobe.json`
- `review_artifacts/final_audio_ffprobe.json`
- `review_artifacts/frame_contact_sheet_0_5s.jpg`
- `review_artifacts/review_artifacts_manifest.json`
- `review_artifacts/audio_track_mix_evidence.json`
- `frame_evidence.json`

## Commands and exit codes

| Step | Command summary | Exit |
| --- | --- | --- |
| Source preflight | Unicode-escaped source path preflight using `C:\Users\user\miniconda3\python.exe -` | 0 |
| Fresh visual plan | Run-local real source intake/rough cut/timeline/render handoff artifact build using `C:\Users\user\miniconda3\python.exe -` | 0 |
| Silent visual render | `C:\Users\user\miniconda3\python.exe tools\rough_cut_plan_execute.py --rough-cut-plan ... --out ... --report ... --timeout-sec 600 --fps 24` | 0 |
| Script write | `C:\Users\user\miniconda3\python.exe -` | 0 |
| VoxCPM runtime | `C:\Users\user\miniconda3\python.exe tools\voxcpm_runtime_check.py --out ...\voxcpm_runtime_check.json` | 0 |
| VoxCPM execute | `C:\Users\user\miniconda3\python.exe tools\voxcpm_voiceover_provider.py ...\script.json --out-dir ... --execute` | 0 |
| Music intent/plan | `C:\Users\user\miniconda3\python.exe -` | 0 |
| Soundtrack arranger | `C:\Users\user\miniconda3\python.exe tools\soundtrack_arranger.py --input ... --out-dir ... --json` | 0 |
| Provider search | `C:\Users\user\miniconda3\python.exe video_tools.py soundtrack-provider-search --plan ... --out ... --providers jamendo,pixabay --limit 5` | 0 |
| Download opening | `C:\Users\user\miniconda3\python.exe video_tools.py soundtrack-provider-download --candidate-id jamendo_opening_underlay_2003897 ...` | 0 |
| Download momentum | `C:\Users\user\miniconda3\python.exe video_tools.py soundtrack-provider-download --candidate-id jamendo_training_momentum_1943774 ...` | 0 |
| Music manifest combine | `C:\Users\user\miniconda3\python.exe -` | 0 |
| Probe opening | `C:\Users\user\miniconda3\python.exe tools\soundtrack_probe.py --audio ...jamendo_opening...mp3 --out ... --enable-asr --json` | 0 |
| Probe momentum | `C:\Users\user\miniconda3\python.exe tools\soundtrack_probe.py --audio ...jamendo_training...mp3 --out ... --enable-asr --json` | 0 |
| Probe bundle | `C:\Users\user\miniconda3\python.exe -` | 0 |
| Audio handoff accept | `C:\Users\user\miniconda3\python.exe video_tools.py soundtrack-audio-handoff-accept ...` | 0 |
| Subtitle/voiceover accept | `C:\Users\user\miniconda3\python.exe tools\subtitle_voiceover_handoff_accept.py ... --json` | 0 |
| Audio mix execute | `C:\Users\user\miniconda3\python.exe tools\audio_mix_plan_execute.py --plan ... --acceptance ... --out-dir ... --json` | 0 |
| Final AV assemble | `C:\Users\user\miniconda3\python.exe tools\final_av_assemble.py --video ... --audio ... --out ... --report ... --source-audio-policy mixed --json` | 0 |
| Final ffprobe | `ffprobe -v error -show_streams -show_format -of json ...\final.mp4` | 0 |
| Audio ffprobe | `ffprobe -v error -show_streams -show_format -of json ...\final_audio.wav` | 0 |
| Contact sheet | `ffmpeg -y -hide_banner -loglevel error -i ...\final.mp4 -vf fps=2,scale=320:-1,tile=10x8 -frames:v 1 ...\frame_contact_sheet_0_5s.jpg` | 0 |
| Review artifact prep | `C:\Users\user\miniconda3\python.exe -` | 0 |
| Pipeline home | `C:\Users\user\miniconda3\python.exe tools\pipeline_home.py --run "<RUN_DIR>" --json` | 0 |
| Delivery gate | `C:\Users\user\miniconda3\python.exe tools\write_delivery_gate_report.py --run "<RUN_DIR>" --json` | 0 |
| Acceptance source/run/provenance | Work-order command 1 with `<RUN_DIR>` substituted | 0 |
| Acceptance multiplicity | Work-order command 2 with `<RUN_DIR>` substituted | 0 |
| Acceptance final media | Work-order command 3 with `<RUN_DIR>` substituted | 0 |
| Acceptance pipeline home | Work-order command 4 with `<RUN_DIR>` substituted | 0 |
| Acceptance delivery gate | Work-order command 5 with `<RUN_DIR>` substituted | 0 |

## Deviations

- The first run of `soundtrack-audio-handoff-accept` produced `ok=false` because my run-local `audio_director_handoff.json` initially used `music_sources/tracks` without the required `selected_audio_files` shape. I corrected only fresh-run artifacts and reran acceptance; no code or tests were edited.
- The first subtitle prep attempt failed because I treated `voice_files` as dict entries when the provider wrote a string list. I corrected only fresh-run artifacts.
- The first combined probe bundle lacked per-track `section_fit`, causing audio handoff `ok=false`. I rebuilt the combined run-local probe bundle from the two original probe files.
- The first review artifact prep used PowerShell redirection for ffprobe JSON, producing UTF-16 JSON that a UTF-8 reader rejected. I reran ffprobe through pinned Python subprocess and wrote UTF-8 JSON.
- No CPU retry occurred, so there is no CPU retry event to preserve beyond noting all segments rendered cleanly.

## Blockers

- No stop-loss blocker remained in the final fresh run.
- Remaining non-technical blockers: real user approval and legal/music-use review are still required.

## Next recommended work

Run a human review/legal review pass on this technical delivery candidate, focused on final cut acceptability, subtitle/voiceover wording, Jamendo license suitability for the intended use, and whether the low-density ASR hit on `opening_underlay` should be avoided entirely by selecting a fully instrumental replacement.
