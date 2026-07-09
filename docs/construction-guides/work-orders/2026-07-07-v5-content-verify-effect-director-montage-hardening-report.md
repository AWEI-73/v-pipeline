# V5 Content Verify, Effect Director Review, And Montage Hardening Report

Date: 2026-07-07

## Summary

- V5 output root: `.tmp\graduation_v5_content_verify_effect_montage_20260707-200659`
- V5 run path: `.tmp\graduation_v5_content_verify_effect_montage_20260707-200659\run`
- Final media: `.tmp\graduation_v5_content_verify_effect_montage_20260707-200659\run\final_v5.mp4`
- V4 unchanged proof: pass, hash comparison true in `final_artifact_check.json`
- Delivery gate: pass with `story_human_review_required` warning
- Pipeline home: `WAITING / human_story_review`
- `story_human_review_decision.json`: not written

## Changed Files

- `video_pipeline_core\voiceover_output_qa.py`
- `video_pipeline_core\source_speech_subtitle_qa.py`
- `video_pipeline_core\effect_director_review.py`
- `video_pipeline_core\montage_design_review.py`
- `tools\independent_voiceover_asr_qa.py`
- `tools\effect_director_review.py`
- `tools\montage_design_review.py`
- `tests\test_voiceover_output_qa.py`
- `tests\test_source_speech_subtitle_qa.py`
- `tests\test_effect_director_review.py`
- `tests\test_montage_design_review.py`
- `docs\branch-contract-registry.json`
- `docs\branch-contract-registry.md`
- `docs\pipeline-decision-tree.md`
- `docs\video-pipeline-operating-map.md`
- `docs\construction-guides\work-orders\2026-07-07-v5-content-verify-effect-director-montage-hardening-report.md`

Existing unrelated dirty files from earlier rounds were not reverted.

## Red-First Evidence

Initial red command:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_voiceover_output_qa tests.test_source_speech_subtitle_qa tests.test_effect_director_review tests.test_montage_design_review
```

Exit code: `1`

Expected failures:

- `ClearNeration` independent ASR transcript was not blocked.
- Provider manifest text alone still passed voiceover output QA.
- Placeholder source-speech subtitles still passed.
- `video_pipeline_core.effect_director_review` was missing.
- `video_pipeline_core.montage_design_review` was missing.

After implementation the same command passed with 21 tests.

## Independent ASR QA

- Tool: `tools\independent_voiceover_asr_qa.py`
- Artifact: `.tmp\graduation_v5_content_verify_effect_montage_20260707-200659\run\voiceover_output_qa.json`
- Probe: `.tmp\graduation_v5_content_verify_effect_montage_20260707-200659\run\voiceover_output_probe.json`
- Method: `faster_whisper`, model `tiny`, CPU int8
- Result: pass
- ASR transcript contains `ClearNeration`: false
- Provider manifest text alone is now blocked by rule `independent_asr_required`.

## Source-Speech Subtitle QA

- Tool: `tools\source_speech_subtitle_qa.py`
- Artifact: `.tmp\graduation_v5_content_verify_effect_montage_20260707-200659\run\source_speech_subtitle_qa.json`
- Result: pass with warning
- Placeholder subtitles present: false
- Source cues: 6 ASR-derived cues from `.tmp\graduation_v5_content_verify_effect_montage_20260707-200659\run\source_speech_asr_probe.json`
- Warning: `needs_human_transcript_review`

The V5 subtitles are ASR-derived actual speech cues, not the V4 marker phrases. Human transcript review remains required before external delivery.

## Effect Director Review

- Tool: `tools\effect_director_review.py`
- Artifact: `.tmp\graduation_v5_content_verify_effect_montage_20260707-200659\run\effect_director_review.json`
- Review basis: `frame_sequence`
- Checked frames: 8
- Checked effects: 6
- Result: pass
- Blocking findings: none

Checks recorded pass for lingering overlays, subject/subtitle obstruction, sticker-like composition, style match, opener/closer story function, and title disappearance.

## Montage Review

- Tool: `tools\montage_design_review.py`
- Artifacts:
  - `.tmp\graduation_v5_content_verify_effect_montage_20260707-200659\run\montage_design_plan.json`
  - `.tmp\graduation_v5_content_verify_effect_montage_20260707-200659\run\montage_timing_map.json`
  - `.tmp\graduation_v5_content_verify_effect_montage_20260707-200659\run\montage_design_review.json`
- Result: pass

V5 opener uses four short shots: roll-call still, basic training motion, advanced training motion, and designed title sync. The plan records story hook, payoff, shot functions, energy timing, title sync, and transition rationale.

## Final Media

- `final_v5.mp4`: exists
- `final.mp4`: copied from `final_v5.mp4` for normal gate/home tooling
- ffprobe:
  - video: `h264`, duration `54.066992`
  - audio: `aac`, duration `53.962993`

Supervisor source speech:

- Preserved original audio: true
- No VoxCPM narration over supervisor section
- Source speech window: `23.0` to `41.0`

## Commands And Exit Codes

| Command | Exit | Result |
| --- | ---: | --- |
| `C:\Users\user\miniconda3\python.exe -m unittest tests.test_voiceover_output_qa tests.test_source_speech_subtitle_qa tests.test_effect_director_review tests.test_montage_design_review` | 1 | red-first expected failures |
| `C:\Users\user\miniconda3\python.exe -m unittest tests.test_voiceover_output_qa tests.test_source_speech_subtitle_qa tests.test_effect_director_review tests.test_montage_design_review` | 0 | 21 tests OK |
| `C:\Users\user\miniconda3\python.exe -m unittest tests.test_voiceover_output_qa tests.test_source_speech_subtitle_qa tests.test_effect_director_review tests.test_montage_design_review tests.test_delivery_gate tests.test_pipeline_home` | 0 | 166 tests OK |
| `C:\Users\user\miniconda3\python.exe tools\voxcpm_voiceover_provider.py ".tmp\graduation_v5_content_verify_effect_montage_20260707-200659\run\v5_narration_script.json" --out-dir ".tmp\graduation_v5_content_verify_effect_montage_20260707-200659\run" --voice-style "calm" --device auto --execute --timeout-sec 1200` | 0 | 4 V5 voiceover wavs generated |
| `C:\Users\user\miniconda3\python.exe tools\independent_voiceover_asr_qa.py --run ".tmp\graduation_v5_content_verify_effect_montage_20260707-200659\run" --model tiny --language zh --json` | 0 | pass true after final assembly |
| `C:\Users\user\miniconda3\python.exe tools\source_speech_subtitle_qa.py --run ".tmp\graduation_v5_content_verify_effect_montage_20260707-200659\run" --json` | 0 | pass true, human transcript warning |
| `C:\Users\user\miniconda3\python.exe tools\effect_director_review.py --run ".tmp\graduation_v5_content_verify_effect_montage_20260707-200659\run" --json` | 0 | pass true |
| `C:\Users\user\miniconda3\python.exe tools\montage_design_review.py --run ".tmp\graduation_v5_content_verify_effect_montage_20260707-200659\run" --json` | 0 | pass true |
| `C:\Users\user\miniconda3\python.exe tools\pipeline_home.py --run ".tmp\graduation_v5_content_verify_effect_montage_20260707-200659\run" --json` | 0 | `WAITING / human_story_review` |
| `C:\Users\user\miniconda3\python.exe tools\write_delivery_gate_report.py --run ".tmp\graduation_v5_content_verify_effect_montage_20260707-200659\run" --json` | 0 | gate pass, story human review warning |
| `ffprobe -v error -show_entries stream=codec_type,codec_name,duration -of json ".tmp\graduation_v5_content_verify_effect_montage_20260707-200659\run\final_v5.mp4"` | 0 | h264 video + aac audio |
| `C:\Users\user\miniconda3\python.exe -c "import json; json.load(open('docs/branch-contract-registry.json', encoding='utf-8')); print('json ok')"` | 0 | `json ok` |
| pinned Python final artifact check | 0 | `.tmp\graduation_v5_content_verify_effect_montage_20260707-200659\final_artifact_check.json` |
| `git diff --check` | 0 | whitespace check passed; CRLF warnings only |
| `git status --short --branch --untracked-files=all` | 0 | dirty tree includes prior unrelated files |

## Pipeline Home And Delivery Gate

Pipeline home:

- status: `WAITING`
- cursor: `human_story_review`
- next: `human_review_story_to_material_map`

Delivery gate:

- pass: true
- blocking: none
- warnings: `story_human_review_required`
- waivers applied: none

## UTF-8 / No Corruption

Final artifact check:

- `utf8_no_corruption=true`
- `story_human_review_decision_exists=false`
- `placeholder_subtitles_present=false`
- `asr_transcript_contains_clearneration=false`

Checked V5 critical artifacts include narration, ASR probe/QA, source-speech subtitle evidence/QA, effect director review, montage design/review, subtitle alignment, audio mix, frame evidence, subtitles, and artifact manifest.

## Deviations / Blockers

- Deviation: V5 still uses ASR-derived supervisor subtitles, not a human transcript. The source-speech QA passes because the cues are actual ASR text and later coverage exists, but it still records `needs_human_transcript_review=true`.
- Deviation: V5 effect director review is evidence-backed by extracted frame sequence/contact sheet, not a human visual-design approval.
- Blockers: none for V5 technical review candidate creation. Human story review and human transcript review remain required before final delivery approval.

## Next Recommended Work

Run real human story-to-material review and human transcript review on V5. If both are approved, write the proper human review decision artifact through the existing writer flow; do not treat this V5 technical candidate as final approval.
