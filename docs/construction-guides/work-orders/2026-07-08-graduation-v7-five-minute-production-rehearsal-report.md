# 2026-07-08 Graduation V7 Five-Minute Production Rehearsal Report

## Summary

- Output root: `.tmp\graduation_v7_five_minute_production_rehearsal_20260708-051809`
- Run path: `.tmp\graduation_v7_five_minute_production_rehearsal_20260708-051809\run`
- Final media: not produced
- Stop-loss blocker: `voiceover_leadin_qa_failed_after_bounded_trim_repair`
- First blocking segment: `seg01`
- Detected lead-in: `康`
- `story_human_review_decision.json`: not written
- Existing V1-V6 / diagnostic runs modified: false
- Review packet: `.tmp\graduation_v7_five_minute_production_rehearsal_20260708-051809\run\v7_eye_ear_brain_review_packet.md`

This run stopped before final assembly. No 240-300s `final_v7.mp4` was created, so no delivery candidate is claimed.

## Source Preflight

Artifact: `.tmp\graduation_v7_five_minute_production_rehearsal_20260708-051809\run\source_preflight.json`

- source root: `C:\Users\user\Downloads\微電影素材\_整理後`
- exists: true
- is_dir: true
- file_count: 306
- media_count: 198
- video_count: 88
- image_count: 110

Module coverage counts:

| Module | Count |
| --- | ---: |
| opener | 10 |
| basic_training | 30 |
| advanced_training | 11 |
| certification_check | 1 |
| physical_activity | 1 |
| encouragement | 20 |
| teacher_class_intro | 4 |
| special_activity | 12 |
| closing | 4 |
| source_root_music | 8 |

The source preflight passed. Coverage was enough to plan a 240-300s structure, but final assembly was blocked by voiceover QA.

## Red-First Evidence

Command:

```powershell
C:\Users\user\miniconda3\python.exe tools\voiceover_leadin_qa.py --run ".tmp\v6_voiceover_regeneration_leadin_gate_20260707-234956\run" --json
```

Exit code: `0`

Result:

- pass: false
- blocking tokens: `康`, `抗`
- blocked segments: `seg01`, `seg02`, `seg03`, `seg04`

This proves the old short-demo/regenerated narration route cannot be used for V7 assembly without bounded lead-in repair.

## Section Timing Plan

Artifact: `.tmp\graduation_v7_five_minute_production_rehearsal_20260708-051809\run\v7_section_timing_plan.json`

Planned target total: 300 seconds.

| Section | Target Start | Target Duration | Status |
| --- | ---: | ---: | --- |
| opener_memory_wall | 0s | 30s | planned |
| training_mv_body | 30s | 175s | planned |
| supervisor_source_speech | 205s | 35s | planned, original audio required |
| teacher_class_intro | 240s | 30s | planned |
| closing_story_payoff | 270s | 30s | planned |

Actual final timing: not available because final assembly was blocked before render.

## Training Module Coverage

Artifact: `.tmp\graduation_v7_five_minute_production_rehearsal_20260708-051809\run\v7_module_coverage_plan.json`

Usable planned module families:

- `basic_training`
- `advanced_training`
- `certification_check`
- `physical_activity`
- `special_activity`
- `encouragement`
- `teacher_class_intro`

This satisfies the requirement to plan at least four usable module families. The plan remains pre-render because voiceover QA blocked final assembly.

## Visual Selection Review

Artifacts:

- `.tmp\graduation_v7_five_minute_production_rehearsal_20260708-051809\run\visual_selection_review.json`
- `.tmp\graduation_v7_five_minute_production_rehearsal_20260708-051809\run\visual_selection_gate.json`

Command:

```powershell
C:\Users\user\miniconda3\python.exe tools\visual_selection_gate.py --run ".tmp\graduation_v7_five_minute_production_rehearsal_20260708-051809\run" --out-dir ".tmp\graduation_v7_five_minute_production_rehearsal_20260708-051809\run" --json
```

Exit code: `0`

Result:

- pass: true
- accepted_visual_evidence_count: 6
- blocked_token_only_selections: none
- sensitive beats seen: opening, newcomer, basic, supervisor source speech, teacher intro, closing

Visual selection did not block this run.

## Voiceover Lead-In Repair

Artifacts:

- `.tmp\graduation_v7_five_minute_production_rehearsal_20260708-051809\run\voiceover_postprocess_repair.json`
- `.tmp\graduation_v7_five_minute_production_rehearsal_20260708-051809\run\voiceover_output_probe.json`
- `.tmp\graduation_v7_five_minute_production_rehearsal_20260708-051809\run\voiceover_output_qa.json`
- `.tmp\graduation_v7_five_minute_production_rehearsal_20260708-051809\run\voiceover_leadin_qa.json`

Repair attempts:

| Segment | Trim Attempt |
| --- | --- |
| `seg01` | 200ms, then 300ms |
| `seg02` | 500ms |
| `seg03` | 500ms |
| `seg04` | 500ms |

Independent ASR command:

```powershell
C:\Users\user\miniconda3\python.exe tools\independent_voiceover_asr_qa.py --run ".tmp\graduation_v7_five_minute_production_rehearsal_20260708-051809\run" --model tiny --language zh --json
```

Exit code: `0`

Voiceover output QA:

- pass: true
- no style/control leakage block

Final lead-in QA command:

```powershell
C:\Users\user\miniconda3\python.exe tools\voiceover_leadin_qa.py --run ".tmp\graduation_v7_five_minute_production_rehearsal_20260708-051809\run" --json
```

Exit code: `0`

Final lead-in QA:

- pass: false
- blocking segment: `seg01`
- detected_extra_leadin: `康`
- ASR text: `康,这一天,学员从急何开始,把安全放进每一个动作里`

Because bounded repair did not pass, final assembly was not attempted.

## Supervisor Source Speech And Transcript Packet

Supervisor/source speech candidate:

- `主任勉勵/IMG_2141.MOV`
- original audio required
- no VoxCPM overlap allowed

Transcript repair packet preserved in the V7 run:

- `asr_raw_transcript.json`
- `agent_transcript_repair_suggestions.json`
- `subtitles.draft.srt`
- `human_transcript_review_decision.json`

Status:

- human transcript review remains required
- no final transcript approval was written

## Music Source

Artifact: `.tmp\graduation_v7_five_minute_production_rehearsal_20260708-051809\run\music_manifest.json`

- Planned music source: Jamendo `jamendo_training_mv_main_2252788`
- Local copied source: `audio/sources/jamendo_training_mv_main_2252788.mp3`
- Old source-folder training music used as final BGM: false
- Legal/music-use review: still required

No final mix was created because voiceover lead-in QA blocked assembly.

## Eye / Ear / Brain Packet

Artifacts:

- `.tmp\graduation_v7_five_minute_production_rehearsal_20260708-051809\run\v7_eye_ear_brain_review_packet.md`
- `.tmp\graduation_v7_five_minute_production_rehearsal_20260708-051809\run\v7_eye_ear_brain_review_packet.json`

The packet includes:

- Eye: timing plan, visual selection evidence, title/effect lifecycle planned but not rendered
- Ear: music source, voiceover repair blocker, source speech preservation requirement
- Brain: five-section story structure and unresolved human decisions

## Pipeline Home And Delivery Gate

Pipeline home command:

```powershell
C:\Users\user\miniconda3\python.exe tools\pipeline_home.py --run ".tmp\graduation_v7_five_minute_production_rehearsal_20260708-051809\run" --json
```

Exit code: `1`

Result:

- status: `UNKNOWN`
- reason: `no recognized pipeline routing artifact found`

Delivery gate:

- not run
- reason: final media does not exist; work order says run delivery gate only if final media exists

ffprobe:

- not run
- reason: `final_v7.mp4` does not exist due stop-loss

## Acceptance Commands

| Command | Exit | Result |
| --- | ---: | --- |
| `C:\Users\user\miniconda3\python.exe tools\voiceover_leadin_qa.py --run ".tmp\v6_voiceover_regeneration_leadin_gate_20260707-234956\run" --json` | 0 | red-first pass=false |
| source preflight pinned Python command | 0 | source exists, 198 media files |
| bounded voiceover trim command | 0 | run-local trimmed WAVs written |
| `C:\Users\user\miniconda3\python.exe tools\independent_voiceover_asr_qa.py --run ".tmp\graduation_v7_five_minute_production_rehearsal_20260708-051809\run" --model tiny --language zh --json` | 0 | voiceover output QA pass |
| `C:\Users\user\miniconda3\python.exe tools\voiceover_leadin_qa.py --run ".tmp\graduation_v7_five_minute_production_rehearsal_20260708-051809\run" --json` | 0 | pass=false, `seg01` blocks |
| `C:\Users\user\miniconda3\python.exe tools\visual_selection_gate.py --run ".tmp\graduation_v7_five_minute_production_rehearsal_20260708-051809\run" --out-dir ".tmp\graduation_v7_five_minute_production_rehearsal_20260708-051809\run" --json` | 0 | visual gate pass |
| `C:\Users\user\miniconda3\python.exe -m unittest tests.test_voiceover_leadin_qa tests.test_voiceover_output_qa tests.test_source_speech_transcript_repair tests.test_visual_selection_review_decision tests.test_graduation_film_blueprint_catalog tests.test_pipeline_home` | 0 | 126 tests OK |
| `C:\Users\user\miniconda3\python.exe tools\pipeline_home.py --run ".tmp\graduation_v7_five_minute_production_rehearsal_20260708-051809\run" --json` | 1 | `UNKNOWN`, no final/routing artifact |
| registry JSON parse | 0 | `json ok` |
| final artifact check | 0 | stop-loss verified |
| `git diff --check` | 0 | whitespace check passed; CRLF warnings only |

## Final Artifact Check

Artifact: `.tmp\graduation_v7_five_minute_production_rehearsal_20260708-051809\final_artifact_check.json`

Key results:

- fresh_v7_output_root_exists: true
- final_v7_exists: false
- stop_loss_report_present: true
- stop_loss_reason: `voiceover_leadin_qa_failed_after_bounded_trim_repair`
- story_human_review_decision_exists: false
- existing_v1_v6_diagnostic_runs_modified: false
- utf8_no_corruption: true
- review_packet_exists: true
- review_packet_has_eye_ear_brain: true
- human_legal_music_review_unresolved: true
- visual_selection_gate_pass: true
- voiceover_leadin_qa_pass: false

## Deviations / Blockers

- Blocker: `seg01` voiceover still starts with ASR-recognized `康` after bounded 200ms and 300ms trims.
- Blocker: `final_v7.mp4` was not assembled because voiceover lead-in QA did not pass.
- Deviation: no title/effect lifecycle QA, montage review, source-speech subtitle QA, delivery gate, or ffprobe were run for final media because render-facing assembly was stopped before final.
- Deviation: a first source-preflight attempt had corrupted keyword matching due raw Chinese in a PowerShell here-string; it was discarded and overwritten with a Unicode-escape-based preflight.
- No waiver was used.
- No human story approval or legal/music approval was written.

## Next Recommended Work Toward Ten-Minute Production

Implement a production-safe voiceover postprocess branch before attempting another five-minute or ten-minute assembly. It must support per-segment adaptive trim search, rerun independent ASR and `voiceover_leadin_qa.py`, and require that the intended first syllable survives. Only after that branch passes should V7 proceed to long-form render, title/effect lifecycle QA, source speech subtitle QA, and delivery gate.
