# V4 Creative Repair And Initial Pipeline Hardening Report

Date: 2026-07-07

## Summary

- V4 output root: `.tmp\graduation_v4_creative_repair_20260707-180019`
- V4 run path: `.tmp\graduation_v4_creative_repair_20260707-180019\run`
- V4 final media: `.tmp\graduation_v4_creative_repair_20260707-180019\run\final_v4.mp4`
- V3 unchanged proof: pass, hash comparison true in `.tmp\graduation_v4_creative_repair_20260707-180019\final_artifact_check.json`
- Delivery gate: pass with `story_human_review_required` warning
- Pipeline home: `WAITING / human_story_review`
- `story_human_review_decision.json`: not written

## Changed Files

- `video_pipeline_core\voiceover_output_qa.py`
- `video_pipeline_core\title_effect_lifecycle_qa.py`
- `video_pipeline_core\source_speech_subtitle_qa.py`
- `tools\voiceover_output_qa.py`
- `tools\title_effect_lifecycle_qa.py`
- `tools\source_speech_subtitle_qa.py`
- `tests\test_voiceover_output_qa.py`
- `tests\test_title_effect_lifecycle_qa.py`
- `tests\test_source_speech_subtitle_qa.py`
- `docs\branch-contract-registry.json`
- `docs\branch-contract-registry.md`
- `docs\pipeline-decision-tree.md`
- `docs\video-pipeline-operating-map.md`
- `docs\construction-guides\work-orders\2026-07-07-v4-creative-repair-and-initial-pipeline-hardening-report.md`

Working tree note: the repo already contains unrelated modified/untracked files from previous rounds, including graduation route and visual-selection files. They were not reverted.

## Red-First Evidence

Initial red command:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_voiceover_output_qa tests.test_title_effect_lifecycle_qa tests.test_source_speech_subtitle_qa
```

Exit code: `1`

Expected failure:

- `ModuleNotFoundError: No module named 'video_pipeline_core.voiceover_output_qa'`
- `ModuleNotFoundError: No module named 'video_pipeline_core.title_effect_lifecycle_qa'`
- `ModuleNotFoundError: No module named 'video_pipeline_core.source_speech_subtitle_qa'`

After implementation, the same command passed with 15 tests.

## QA Gates Implemented

Voiceover output QA:

- Module: `video_pipeline_core.voiceover_output_qa`
- Tool: `tools\voiceover_output_qa.py`
- V4 artifact: `.tmp\graduation_v4_creative_repair_20260707-180019\run\voiceover_output_qa.json`
- Result: pass
- Leakage result: no blocking leakage terms in checked generated-output evidence
- Limitation: no independent ASR was run; V4 uses recorded provider manifest text and wav evidence in `voiceover_output_probe.json`.

Title/effect lifecycle QA:

- Module: `video_pipeline_core.title_effect_lifecycle_qa`
- Tool: `tools\title_effect_lifecycle_qa.py`
- V4 artifact: `.tmp\graduation_v4_creative_repair_20260707-180019\run\title_effect_lifecycle_qa.json`
- Result: pass
- Checked effects: 7
- Repair summary: title cards/lower labels have explicit start/end timing, max duration, next-section clear policy, and frame evidence.

Source-speech subtitle QA:

- Module: `video_pipeline_core.source_speech_subtitle_qa`
- Tool: `tools\source_speech_subtitle_qa.py`
- V4 artifact: `.tmp\graduation_v4_creative_repair_20260707-180019\run\source_speech_subtitle_qa.json`
- Result: pass with warning
- Warning: `needs_human_transcript_review`
- Supervisor subtitle completeness: later portion is covered by explicit review-marker cue from `32.0` to `42.0`, but true human transcript review remains required.

## V4 Repair Evidence

Final media:

- `final_v4.mp4`: exists
- `final.mp4`: copied from `final_v4.mp4` for normal gate/home tooling
- ffprobe:
  - video: `h264`, duration `55.066992`
  - audio: `aac`, duration `55.008005`

Source audio preservation:

- Artifact: `.tmp\graduation_v4_creative_repair_20260707-180019\run\source_speech_preservation_report.json`
- `original_audio_preserved=true`
- `voxcpm_narration_over_section=false`
- Supervisor window: `24.0` to `42.0`

Review artifacts:

- Contact sheet: `.tmp\graduation_v4_creative_repair_20260707-180019\run\review_artifacts_v4\v4_contact_sheet.jpg`
- Frame list: `.tmp\graduation_v4_creative_repair_20260707-180019\run\v4_review_artifacts_manifest.json`

## Commands And Exit Codes

| Command | Exit | Result |
| --- | ---: | --- |
| `C:\Users\user\miniconda3\python.exe -m unittest tests.test_voiceover_output_qa tests.test_title_effect_lifecycle_qa tests.test_source_speech_subtitle_qa` | 1 | red-first module-missing failure |
| `C:\Users\user\miniconda3\python.exe -m unittest tests.test_voiceover_output_qa tests.test_title_effect_lifecycle_qa tests.test_source_speech_subtitle_qa` | 0 | 15 tests OK |
| `C:\Users\user\miniconda3\python.exe -m unittest tests.test_voiceover_output_qa tests.test_title_effect_lifecycle_qa tests.test_source_speech_subtitle_qa tests.test_delivery_gate tests.test_pipeline_home` | 0 | 160 tests OK |
| `C:\Users\user\miniconda3\python.exe tools\voxcpm_voiceover_provider.py ".tmp\graduation_v4_creative_repair_20260707-180019\run\v4_narration_script.json" --out-dir ".tmp\graduation_v4_creative_repair_20260707-180019\run" --voice-style "clear narration" --device auto --execute --timeout-sec 1200` | 0 | 4 V4 narration wavs generated |
| pinned Python V4 assembly script | 0 | `final_v4.mp4` created |
| `C:\Users\user\miniconda3\python.exe tools\voiceover_output_qa.py --run ".tmp\graduation_v4_creative_repair_20260707-180019\run" --json` | 0 | pass true |
| `C:\Users\user\miniconda3\python.exe tools\title_effect_lifecycle_qa.py --run ".tmp\graduation_v4_creative_repair_20260707-180019\run" --json` | 0 | pass true |
| `C:\Users\user\miniconda3\python.exe tools\source_speech_subtitle_qa.py --run ".tmp\graduation_v4_creative_repair_20260707-180019\run" --json` | 0 | pass true, human transcript review warning |
| `C:\Users\user\miniconda3\python.exe tools\pipeline_home.py --run ".tmp\graduation_v4_creative_repair_20260707-180019\run" --json` | 0 | `WAITING / human_story_review` |
| `C:\Users\user\miniconda3\python.exe tools\write_delivery_gate_report.py --run ".tmp\graduation_v4_creative_repair_20260707-180019\run" --json` | 0 | gate pass, story human review warning |
| `ffprobe -v error -show_entries stream=codec_type,codec_name,duration -of json ".tmp\graduation_v4_creative_repair_20260707-180019\run\final_v4.mp4"` | 0 | h264 video + aac audio |
| `C:\Users\user\miniconda3\python.exe -c "import json; json.load(open('docs/branch-contract-registry.json', encoding='utf-8')); print('json ok')"` | 0 | `json ok` |
| pinned Python final artifact check | 0 | `.tmp\graduation_v4_creative_repair_20260707-180019\final_artifact_check.json` |
| `git diff --check` | 0 | whitespace check passed; CRLF warnings only |
| `git status --short --branch --untracked-files=all` | 0 | dirty tree includes prior unrelated files |

## Pipeline Home And Delivery Gate

Pipeline home:

- status: `WAITING`
- cursor: `human_story_review`
- next: `human_review_story_to_material_map`
- reason: delivery gate passed and final exists, but story-to-material mapping includes agent-filled/inferred choices.

Delivery gate:

- pass: true
- blocking: none
- warnings: `story_human_review_required`
- waivers applied: none

## UTF-8 / No Corruption

Final artifact check result: `utf8_no_corruption=true` for V4 critical artifacts:

- narration script and manifest
- voiceover output probe/QA
- title/effect lifecycle plan/QA
- source-speech subtitle evidence/QA
- subtitle alignment report
- source speech preservation report
- frame evidence
- audio mix report
- subtitles
- artifact manifest and subtitle/voiceover handoff

## Deviations / Blockers

- Deviation: V4 was copied from V3 as the starting point, so old copied V3 logs may still contain prior mojibake display artifacts. V4 critical artifacts were rewritten/checked and passed UTF-8/no-corruption.
- Deviation: no independent ASR was run on generated V4 voiceover; the voiceover output QA uses provider manifest text plus generated wav evidence.
- Limitation: supervisor source-speech subtitles are coverage/review markers, not a final human transcript. Human transcript review remains required.
- Blockers: none for V4 technical review candidate creation. Real human story review is still required before delivery approval.

## Next Recommended Work

Run human story-to-material review and human transcript review on the V4 technical candidate. If both are approved by a real human reviewer, write the appropriate human review decision artifact; do not treat this V4 technical candidate as final creative approval.
