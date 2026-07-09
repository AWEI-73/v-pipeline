# Graduation V2 Creative Repair Contract Report

Date: 2026-07-07

## Output

- Output root: `.tmp/graduation_v2_creative_repair_20260707-122858`
- Repair run: `.tmp/graduation_v2_creative_repair_20260707-122858/run`
- V2 final: `.tmp/graduation_v2_creative_repair_20260707-122858/run/final_v2.mp4`
- Gate alias for existing tools: `.tmp/graduation_v2_creative_repair_20260707-122858/run/final.mp4`
- Review packet: `.tmp/graduation_v2_creative_repair_20260707-122858/run/v2_review_packet.md`
- Review manifest: `.tmp/graduation_v2_creative_repair_20260707-122858/run/v2_review_artifacts_manifest.json`
- Contact sheet: `.tmp/graduation_v2_creative_repair_20260707-122858/run/review_artifacts/v2_contact_sheet.jpg`

## Six Repair Branch Statuses

- Narration rewrite: implemented. V2 narration is sparse story narration, not spoken settings/labels.
- Newcomer material repick: implemented. Primary newcomer visual is `工安早會/IMG_2120.JPG`; supervisor/director imagery is not used as the newcomer primary visual.
- MV title treatment repair: implemented. V2 uses brief chapter/lower-third treatments and no persistent side rail, plain subtitle title, or white card title.
- Music direction repair: implemented by retaining the V1 Jamendo track only as a lively training-momentum bed, with BGM muted during supervisor source speech. Legal/music-use review remains required.
- Designed opener/closer: implemented with self-made dark industrial opener/closer segments in the current ffmpeg route. `v2_effect_handoff.json` records that no external effect handoff was needed for this V2 technical render.
- Supervisor source-audio repair: implemented. `主任勉勵/IMG_2141.MOV` is used as the talking-head/source-speech section, original audio is preserved, no VoxCPM narration is placed over it, and ASR subtitle/alignment evidence is present.

## Voice Variants

- Variants tested: 2 exactly.
- Variant A: warm clear Mandarin narrator, generated under `voice_variant_A/`.
- Variant B: firmer documentary Mandarin narrator, generated under `voice_variant_B/`.
- Selected voice: firmer documentary Mandarin narrator.
- Full selected narration artifacts: `voiceover_provider_plan.json`, `narration_manifest.json`, `subtitle_voiceover_build_handoff.json`, and `voiceover/seg01.wav` through `voiceover/seg04.wav`.

## Source Speech / Subtitles

- Supervisor source clip: `主任勉勵/IMG_2141.MOV`
- Source speech probe: `supervisor_source_speech_probe.json`
- Talking-head frame evidence: `supervisor_candidate_frames/candidate_05.jpg`
- Preservation report: `source_speech_preservation_report.json`
- Subtitle alignment report: `subtitle_audio_alignment_report.json`
- Subtitle file: `subtitles.srt`
- Subtitle cues: 7
- Limitation: subtitles are ASR-derived and still require human review.

## Music Decision

- Old source-folder music remains excluded as final BGM.
- Retained V1 Jamendo file copied into the V2 run: `audio/sources/jamendo_training_mv_main_2252788.mp3`
- Evidence retained/updated: `music_manifest.json`, `soundtrack_probe_report.json`, `music_use_evidence.json`, `sound_license_manifest.json`
- Music caveat: Jamendo license metadata is evidence only. It is not legal approval; legal/music-use review remains required.

## Final / Gate Status

- `final_v2.mp4` exists: yes.
- ffprobe: video stream `h264` duration `59.066992`; audio stream `aac` duration `59.001995`.
- Delivery gate: pass, with warning `story_human_review_required`.
- Pipeline home: `WAITING / human_story_review`, because V2 still has agent-filled/inferred story-material decisions and no human review decision was written.
- `story_human_review_decision.json` exists: false.
- V1 run overwritten: false; run-local snapshot check reported unchanged.
- UTF-8/no-corruption check: pass.

## Commands

- `C:\Users\user\miniconda3\python.exe tools\voxcpm_runtime_check.py --out .tmp\graduation_v2_creative_repair_20260707-122858\run\voxcpm_runtime_check.json` -> exit 0
- `C:\Users\user\miniconda3\python.exe tools\voxcpm_voiceover_provider.py ...v2_voice_variant_A_sample_script.json --out-dir ...\voice_variant_A --voice-style "warm clear Mandarin narrator" --device auto --execute --timeout-sec 1200` -> exit 0
- `C:\Users\user\miniconda3\python.exe tools\voxcpm_voiceover_provider.py ...v2_voice_variant_B_sample_script.json --out-dir ...\voice_variant_B --voice-style "firmer documentary Mandarin narrator" --device auto --execute --timeout-sec 1200` -> exit 0
- `C:\Users\user\miniconda3\python.exe tools\voxcpm_voiceover_provider.py ...v2_narration_script.json --out-dir ...\run --voice-style "firmer documentary Mandarin narrator" --device auto --execute --timeout-sec 1200` -> exit 0
- V2 render script using `C:\Users\user\miniconda3\python.exe -` -> first mix attempt exit 1 because local ffmpeg `amix` does not support `normalize`; continuation without `normalize` exit 0.
- `ffprobe -v error -show_entries stream=codec_type,codec_name,duration -of json ".tmp\graduation_v2_creative_repair_20260707-122858\run\final_v2.mp4"` -> exit 0
- `C:\Users\user\miniconda3\python.exe tools\write_delivery_gate_report.py --run ".tmp\graduation_v2_creative_repair_20260707-122858\run" --json` -> first run exit 1 with missing subtitle/story/frame evidence blocks; after artifact repair exit 0, gate pass true.
- `C:\Users\user\miniconda3\python.exe tools\pipeline_home.py --run ".tmp\graduation_v2_creative_repair_20260707-122858\run" --json` -> exit 0, final status `WAITING / human_story_review`.
- `git status --short --branch --untracked-files=all` -> exit 0
- `git diff --check` -> exit 0

## Deviations / Blockers

- No code, tools, tests, skills, Downloads, deliveries, env, reference repo, or existing `.tmp` runs were edited.
- The first ffmpeg mix command failed due to unsupported `amix normalize`; the continuation used the same inputs without that unsupported option and produced `final_v2.mp4`.
- The first gate report exposed run-local artifact gaps (`subtitles.srt`, opener/closer story coverage, frame evidence shape). Those were repaired inside the V2 run only, then gate passed.
- V2 is still a technical review candidate, not final approved delivery. Human story review and legal/music-use review remain required.

## Next Recommended Work

Run the human creative review on the V2 review packet and contact sheet. If approved, write an explicit human story review decision artifact for this V2 run; if revision is requested, route only the named creative findings instead of opening a new production route.
