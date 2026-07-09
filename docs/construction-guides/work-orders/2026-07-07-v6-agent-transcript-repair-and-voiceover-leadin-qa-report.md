# V6 Agent Transcript Repair And Voiceover Lead-In QA Report

Date: 2026-07-07

## Summary

- Output root: `.tmp\graduation_v6_transcript_repair_leadin_qa_20260707-212257`
- Run path: `.tmp\graduation_v6_transcript_repair_leadin_qa_20260707-212257\run`
- Source run: `.tmp\graduation_v5_content_verify_effect_montage_20260707-200659\run`
- V5 unchanged proof: true in `.tmp\graduation_v6_transcript_repair_leadin_qa_20260707-212257\final_artifact_check.json`
- V6 final media: not produced
- Stop-loss reason: `voiceover_leadin_qa.json` blocks all four V5 voiceover segments for extra lead-in tokens/phrases.
- `story_human_review_decision.json`: not written

## Changed Files

- `video_pipeline_core\agent_transcript_repair.py`
- `video_pipeline_core\human_transcript_review_decision.py`
- `video_pipeline_core\voiceover_leadin_qa.py`
- `tools\agent_transcript_repair.py`
- `tools\write_human_transcript_review_decision.py`
- `tools\voiceover_leadin_qa.py`
- `tests\test_source_speech_transcript_repair.py`
- `tests\test_voiceover_leadin_qa.py`
- `docs\branch-contract-registry.json`
- `docs\branch-contract-registry.md`
- `docs\pipeline-decision-tree.md`
- `docs\video-pipeline-operating-map.md`
- `docs\construction-guides\work-orders\2026-07-07-v6-agent-transcript-repair-and-voiceover-leadin-qa-report.md`

Pre-existing unrelated dirty files were not reverted.

## Red-First Evidence

Initial command:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_source_speech_transcript_repair tests.test_voiceover_leadin_qa
```

Exit code: `1`

Expected failures:

- `ModuleNotFoundError: No module named 'video_pipeline_core.agent_transcript_repair'`
- `ModuleNotFoundError: No module named 'video_pipeline_core.voiceover_leadin_qa'`

## Implemented Behavior

Agent transcript repair:

- Consumes `asr_raw_transcript.json`, or creates it from `source_speech_asr_probe.json` when that is the available run-local ASR evidence.
- Writes `agent_transcript_repair_suggestions.json`.
- Writes `subtitles.draft.srt`.
- Preserves `requires_human_transcript_review=true`.
- Preserves `approval_status=agent_draft_not_approved`.
- Supports `source_speech`, `voiceover`, `generated_subtitle`, `interview`, and `original_audio`.

Human transcript review decision writer:

- Writes `human_transcript_review_decision.json`.
- Supports `approved`, `revision_requested`, and `rejected`.
- Fails closed for non-human reviewer.
- `approved` only clears human transcript review when it has a reviewed draft and reviewed cue ids.
- In this V6 run, the decision is `revision_requested`, so transcript review is not cleared.

Voiceover lead-in QA:

- Writes `voiceover_leadin_qa.json`.
- Compares `narration_manifest.json` expected text with independent ASR in `voiceover_output_probe.json`.
- Blocks missing ASR, missing script, and extra spoken lead-in tokens before expected narration.

## Transcript Suggestions

Artifact: `.tmp\graduation_v6_transcript_repair_leadin_qa_20260707-212257\run\agent_transcript_repair_suggestions.json`

Draft subtitles: `.tmp\graduation_v6_transcript_repair_leadin_qa_20260707-212257\run\subtitles.draft.srt`

Summary:

- suggestion_count: 6
- human-review-required: true
- approval_status: `agent_draft_not_approved`
- known repair suggestions include:
  - `第六四七七楊成班學人們` -> `第六十七期養成班學員們`
  - `順利節` -> `順利結訓`
  - `五個班院成成` -> `五個半月養成`
  - `電力雄兵` remains reviewable rather than treated as final truth.

## Human Review Decision Behavior

Artifact: `.tmp\graduation_v6_transcript_repair_leadin_qa_20260707-212257\run\human_transcript_review_decision.json`

V6 command wrote:

- decision: `revision_requested`
- reviewer: `human`
- clears_human_transcript_review: false
- note_count: 1

Non-human approval smoke:

- command rejected `--reviewer agent`
- exit code: `1`
- error: `human transcript review decision requires reviewer=human`

## Voiceover Lead-In QA

Artifact: `.tmp\graduation_v6_transcript_repair_leadin_qa_20260707-212257\run\voiceover_leadin_qa.json`

Result:

- pass: false
- checked_segment_count: 4
- next_action: `repair_voiceover_leadin`

Detected mismatches:

| Segment | Detected extra lead-in | Expected starts with | ASR starts with |
| --- | --- | --- | --- |
| `seg01` | `看我們` | `這一天...` | `看我们这一天...` |
| `seg02` | `抗` | `基本訓練...` | `抗,基本顺练...` |
| `seg03` | `抗` | `進階訓練...` | `抗、敬開坑鏈...` |
| `seg04` | `抗` | `完成訓練後...` | `抗,完成顺利後...` |

Because this QA blocks, `final_v6.mp4` was not produced.

## Pipeline Home And Delivery Gate

Pipeline home on V6 copied run:

- exit code: `0`
- status: `WAITING`
- cursor: `human_story_review`
- command: `human_review_story_to_material_map`

Delivery gate on V6 copied run:

- exit code: `0`
- pass: true
- blocking: none
- warning: `story_human_review_required`

Important limitation: the existing delivery gate does not yet consume V6 `voiceover_leadin_qa.json`. This report treats lead-in QA as the V6 stop-loss gate and does not claim V6 delivery readiness.

## Final Media

- `final_v6.mp4`: absent
- ffprobe command exit code: `1`
- ffprobe result: `No such file or directory`

This is expected stop-loss evidence because clean V6 narration was not generated and lead-in QA did not pass.

## Commands And Exit Codes

| Command | Exit | Result |
| --- | ---: | --- |
| `C:\Users\user\miniconda3\python.exe -m unittest tests.test_source_speech_transcript_repair tests.test_voiceover_leadin_qa` | 1 | red-first missing modules |
| `C:\Users\user\miniconda3\python.exe -m unittest tests.test_source_speech_transcript_repair tests.test_voiceover_leadin_qa` | 0 | 10 tests OK |
| `C:\Users\user\miniconda3\python.exe -m unittest tests.test_source_speech_transcript_repair tests.test_voiceover_leadin_qa tests.test_voiceover_output_qa tests.test_source_speech_subtitle_qa tests.test_pipeline_home` | 0 | 103 tests OK |
| `C:\Users\user\miniconda3\python.exe tools\agent_transcript_repair.py --run ".tmp\graduation_v6_transcript_repair_leadin_qa_20260707-212257\run" --json` | 0 | suggestions and draft subtitles written |
| `C:\Users\user\miniconda3\python.exe tools\write_human_transcript_review_decision.py --run ".tmp\graduation_v6_transcript_repair_leadin_qa_20260707-212257\run" --decision revision_requested --reviewer human --note "draft requires human correction" --json` | 0 | revision decision written; does not clear review |
| `C:\Users\user\miniconda3\python.exe tools\voiceover_leadin_qa.py --run ".tmp\graduation_v6_transcript_repair_leadin_qa_20260707-212257\run" --json` | 0 | pass false; four lead-in mismatches |
| `C:\Users\user\miniconda3\python.exe tools\pipeline_home.py --run ".tmp\graduation_v6_transcript_repair_leadin_qa_20260707-212257\run" --json` | 0 | `WAITING / human_story_review` |
| `C:\Users\user\miniconda3\python.exe tools\write_delivery_gate_report.py --run ".tmp\graduation_v6_transcript_repair_leadin_qa_20260707-212257\run" --json` | 0 | gate pass with `story_human_review_required` warning |
| `ffprobe -v error -show_entries stream=codec_type,codec_name,duration -of json ".tmp\graduation_v6_transcript_repair_leadin_qa_20260707-212257\run\final_v6.mp4"` | 1 | expected stop-loss; file absent |
| `C:\Users\user\miniconda3\python.exe -c "import json; json.load(open('docs/branch-contract-registry.json', encoding='utf-8')); print('json ok')"` | 0 | `json ok` |
| `C:\Users\user\miniconda3\python.exe tools\write_human_transcript_review_decision.py --run ".tmp\graduation_v6_transcript_repair_leadin_qa_20260707-212257\run" --decision approved --reviewer agent --reviewed-cue-id cue01 --json` | 1 | non-human approval rejected |
| pinned Python final artifact check | 0 | `.tmp\graduation_v6_transcript_repair_leadin_qa_20260707-212257\final_artifact_check.json` |
| `git diff --check` | 0 | whitespace check passed; CRLF warnings only |
| `git status --short --branch --untracked-files=all` | 0 | dirty tree includes prior unrelated files |

## UTF-8 / No Corruption

Final artifact check:

- utf8_no_corruption: true
- utf8_bad_files: []

Checked generated V6 JSON artifacts with explicit UTF-8 read:

- `agent_transcript_repair_suggestions.json`
- `asr_raw_transcript.json`
- `human_transcript_review_decision.json`
- `voiceover_leadin_qa.json`

## Deviations / Blockers

- Deviation: V6 did not attempt narration regeneration. The V5 independent ASR evidence already triggered the work-order stop-loss for lead-in mismatch; regenerating narration would require a new provider execution path and risk another VoxCPM branch without a guarantee of clean lead-in.
- Blocker: `voiceover_leadin_qa.json` blocks `seg01` through `seg04`.
- Blocker: human transcript review remains required; the written decision is `revision_requested`, not `approved`.
- Limitation: current delivery gate does not consume `voiceover_leadin_qa.json`; this was documented rather than bypassed.

## Next Recommended Work

Run a focused voiceover regeneration round for the exact V6/V5 narration segments, with the new `tools\voiceover_leadin_qa.py` as the acceptance gate before any final assembly. After lead-in QA passes, rerun transcript repair suggestions and obtain a real `human_transcript_review_decision.json` approval for reviewed cue ids before treating subtitles/transcript as delivery-ready.
