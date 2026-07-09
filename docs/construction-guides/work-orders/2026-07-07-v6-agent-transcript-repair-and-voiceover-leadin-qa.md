# Work Order: V6 Agent Transcript Repair And Voiceover Lead-In QA

Date: 2026-07-07

## Goal

Add two reusable pipeline branches and optionally produce a focused V6 technical
review candidate from V5:

1. Agent-assisted ASR transcript repair suggestions for human review.
2. Voiceover lead-in mismatch QA that detects extra spoken tokens at the start
   of generated narration, even when they are not recognized as explicit
   control words.

The agent may propose subtitle repairs for any ASR-derived subtitle path. The
agent must not approve the final transcript. Human decision remains required.

## Context Sources

- V5 run:
  `.tmp\graduation_v5_content_verify_effect_montage_20260707-200659\run`
- V5 report:
  `docs/construction-guides/work-orders/2026-07-07-v5-content-verify-effect-director-montage-hardening-report.md`
- V5 source-speech ASR:
  `.tmp\graduation_v5_content_verify_effect_montage_20260707-200659\run\source_speech_asr_probe.json`
- V5 independent voiceover ASR:
  `.tmp\graduation_v5_content_verify_effect_montage_20260707-200659\run\voiceover_output_probe.json`

Observed issues:

- Source-speech subtitles are actual ASR cues but rough and need agent repair
  suggestions before human decision.
- Voiceover ASR shows extra lead-in text at segment starts, such as `抗,` or
  similar non-script tokens, even when `ClearNeration` is absent.

## Owner Zone

- New or updated modules under `video_pipeline_core/`:
  - agent transcript repair suggestions
  - voiceover lead-in mismatch QA
- New or updated CLI tools under `tools/`
- New or updated tests under `tests/`
- New fresh output root under `.tmp\graduation_v6_transcript_repair_leadin_qa_*`
- Run-local V6 artifacts inside that fresh output root
- `docs/video-pipeline-operating-map.md`
- `docs/pipeline-decision-tree.md`
- `docs/branch-contract-registry.md`
- `docs/branch-contract-registry.json`
- `docs/construction-guides/work-orders/2026-07-07-v6-agent-transcript-repair-and-voiceover-leadin-qa-report.md`

## Forbidden Zone

- Existing V1 run:
  `.tmp\real_graduation_production_candidate_v1_20260707-062900\run`
- Existing V2 run:
  `.tmp\graduation_v2_creative_repair_20260707-122858\run`
- Existing V3 run:
  `.tmp\graduation_v3_visual_reviewed_creative_repair_20260707-161251\run`
- Existing V4 run:
  `.tmp\graduation_v4_creative_repair_20260707-180019\run`
- Existing V5 run:
  `.tmp\graduation_v5_content_verify_effect_montage_20260707-200659\run`
- `Downloads/`
- `deliveries/`
- `.env*`
- `.venv*`
- `reference repo/`
- Git branch, commit, push, or PR operations

## Required Environment

Use the pinned interpreter:

```powershell
C:\Users\user\miniconda3\python.exe
```

Do not use bare `python` or `pytest`.

## Required Pipeline Behavior

### 1. Agent Transcript Repair Suggestions

Create a branch that consumes ASR cues and known context, then
writes:

- `agent_transcript_repair_suggestions.json`
- `subtitles.draft.srt`

This branch applies to every ASR-derived subtitle source, including:

- source-speech / supervisor speech ASR
- voiceover ASR when used for subtitle QA
- generated subtitles created from ASR
- future interview, speaker, or original-audio transcript routes

Required fields:

- source type: `source_speech`, `voiceover`, `generated_subtitle`,
  `interview`, or `original_audio`
- original ASR cue text and timing
- suggested repaired text
- confidence: `high`, `medium`, or `low`
- uncertain spans
- reason/context for the suggestion
- `requires_human_transcript_review=true`
- `approval_status=agent_draft_not_approved`

The branch may use deterministic context rules and/or an LLM-style local
heuristic, but it must not mark suggestions as human-approved.

Required transcript review layers:

```text
asr_raw_transcript.json
  -> agent_transcript_repair_suggestions.json
  -> subtitles.draft.srt
  -> human_transcript_review_decision.json
```

`asr_raw_transcript.json` and `subtitles.draft.srt` are never final delivery
approval. `human_transcript_review_decision.json` is the only artifact that can
clear human transcript review.

Add or document a writer/contract for `human_transcript_review_decision.json`.
It must support at least:

- `approved`
- `revision_requested`
- `rejected`

Only `reviewer=human` or `reviewer_type=human` can approve. Agent/self review
must not clear transcript review.

Use current known context to propose likely repairs, including at least:

- `第六四七七楊成班學人們` -> likely `第六十七期養成班學員們`
- `順利節` -> likely `順利結訓`
- `五個班院成成` -> likely `五個半月養成`
- `電力雄兵` may be plausible but must remain reviewable if confidence is not
  high.

### 2. Voiceover Lead-In Mismatch QA

Create a QA branch that compares expected narration text with independent ASR
recognized text for each voiceover segment.

It must fail closed when:

- independent ASR evidence is missing
- expected script/manifests are missing
- recognized text starts with a token or short phrase not present at the start
  of expected narration
- the leading mismatch looks like a non-content sound/control token, e.g.
  `抗`, `看我们` when expected starts with `這一天`, or any other extra lead-in
  not justified by the script

Required output:

- `voiceover_leadin_qa.json`

Required fields:

- segment id
- expected text
- recognized ASR text
- normalized expected prefix
- normalized recognized prefix
- detected extra lead-in token/phrase
- pass/block result
- next action

The QA must catch the current V5 probe pattern where `voiceover/seg02.wav`,
`seg03.wav`, or `seg04.wav` starts with an extra `抗`-like token before the
expected narration.

## Optional V6 Repair Candidate

If the lead-in QA blocks V5, the worker may create a fresh V6 technical review
candidate by regenerating narration with a safer prompt/style and reassembling
from V5 inputs.

V6 must:

- not modify V5
- preserve V5 visual/effect/montage choices unless a hard gate requires repair
- use repaired draft subtitles only as `agent_draft`, not human-approved final
  subtitles
- if final media is produced before human transcript approval, pipeline status
  must remain waiting/repair for `human_transcript_review` or clearly report
  transcript review still required
- not write `story_human_review_decision.json`
- produce `final_v6.mp4` only if voiceover lead-in QA passes

If clean narration cannot be generated, stop after writing the QA and repair
suggestion artifacts.

## Red-First Verification

Before implementation, add failing tests proving current gaps:

- transcript repair suggestion artifact does not exist / is unsupported
- repair suggestions must retain human-review-required status
- ASR-derived subtitle route cannot skip
  `agent_transcript_repair_suggestions.json`
- `human_transcript_review_decision.json` approved by non-human reviewer must
  fail closed
- `approved` human transcript decision clears transcript review only when it
  references the reviewed draft/cue ids
- lead-in QA fails when ASR starts with `抗,基本訓練...` but expected starts
  with `基本訓練...`
- lead-in QA fails when ASR starts with `看我們這一天...` but expected starts
  with `這一天...`, unless explicitly allowed
- lead-in QA passes when ASR and expected text begin with matching content
- lead-in QA fails when independent ASR evidence is missing

## Acceptance Commands

Expected exit code is `0` unless stop-loss is hit and reported.

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_source_speech_transcript_repair tests.test_voiceover_leadin_qa
C:\Users\user\miniconda3\python.exe -m unittest tests.test_source_speech_transcript_repair tests.test_voiceover_leadin_qa tests.test_voiceover_output_qa tests.test_source_speech_subtitle_qa tests.test_pipeline_home
C:\Users\user\miniconda3\python.exe <transcript-repair-tool> --run "<V6_OR_V5_RUN>" --json
C:\Users\user\miniconda3\python.exe <human-transcript-review-writer> --run "<V6_OR_V5_RUN>" --decision revision_requested --reviewer human --note "draft requires human correction" --json
C:\Users\user\miniconda3\python.exe <voiceover-leadin-qa-tool> --run "<V6_OR_V5_RUN>" --json
C:\Users\user\miniconda3\python.exe tools\pipeline_home.py --run "<V6_OR_V5_RUN>" --json
C:\Users\user\miniconda3\python.exe tools\write_delivery_gate_report.py --run "<V6_OR_V5_RUN>" --json
ffprobe -v error -show_entries stream=codec_type,codec_name,duration -of json "<V6_RUN>\final_v6.mp4"
C:\Users\user\miniconda3\python.exe -c "import json; json.load(open('docs/branch-contract-registry.json', encoding='utf-8')); print('json ok')"
git diff --check
```

If V6 final media is not produced because lead-in repair remains blocked, the
ffprobe command is expected to fail and must be reported as stop-loss evidence.

Add a final artifact check command using the pinned interpreter that prints:

- output root and run path
- V5 unchanged true/false
- transcript repair suggestions exist true/false
- draft subtitles exist true/false
- suggestions require human review true/false
- human transcript review decision exists true/false
- non-human transcript approval rejected true/false
- voiceover lead-in QA pass true/false
- detected lead-in mismatches
- `final_v6.mp4` exists true/false
- story human review decision exists true/false
- UTF-8/no-corruption true/false

## Stop-Loss Limits

Stop and report instead of forcing a pass if:

- transcript repair suggestions would need to be marked human-approved
- ASR subtitle route can only pass by skipping agent repair suggestions
- non-human transcript review can approve the transcript
- lead-in QA cannot access independent ASR evidence
- clean narration cannot be generated without extra lead-in tokens
- passing requires editing existing V1/V2/V3/V4/V5 runs
- passing requires modifying Downloads, deliveries, env/venv, or reference repo
- passing requires waiving transcript or lead-in QA

## Delegated Decisions

- Exact module/tool names.
- Exact normalization rules for Chinese/English punctuation and traditional vs
  simplified characters, as long as red-first cases are covered.
- Exact confidence thresholds for transcript suggestions.
- Exact schema for `human_transcript_review_decision.json`, provided it
  fail-closes non-human approval and records reviewed cue ids.
- Whether to attempt V6 final media after V5 lead-in QA blocks.
- Exact V6 output folder timestamp/name.
- Exact narration regeneration strategy if V6 is attempted.

## Report Requirements

Write:

```text
docs/construction-guides/work-orders/2026-07-07-v6-agent-transcript-repair-and-voiceover-leadin-qa-report.md
```

Include:

- changed files
- red-first evidence
- output root and run path
- V5 unchanged proof
- transcript repair suggestions summary
- draft subtitle path
- human-review-required status
- human transcript review decision writer/contract behavior
- voiceover lead-in QA result and detected mismatches
- V6 final media path and ffprobe summary if created
- pipeline_home and delivery gate results
- command exit codes
- UTF-8/no-corruption result
- deviations/blockers
- next recommended work
