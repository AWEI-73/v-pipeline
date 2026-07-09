# Work Order: V6 Voiceover Regeneration With Lead-In Gate

Date: 2026-07-07

## Goal

Regenerate only the narration voiceover for the V5/V6 graduation candidate,
using `voiceover_leadin_qa.py` as a hard acceptance gate before any final
assembly.

Do not redo product routing, visual selection, montage, effects, transcript
repair suggestions, music selection, or story structure.

## Context Sources

- V6 run:
  `.tmp\graduation_v6_transcript_repair_leadin_qa_20260707-212257\run`
- V6 report:
  `docs/construction-guides/work-orders/2026-07-07-v6-agent-transcript-repair-and-voiceover-leadin-qa-report.md`
- V5 final candidate source:
  `.tmp\graduation_v5_content_verify_effect_montage_20260707-200659\run`

Known V6 blocker:

- `voiceover_leadin_qa.json` has `pass=false`.
- Detected extra lead-ins:
  - `seg01`: `看我們`
  - `seg02`: `抗`
  - `seg03`: `抗`
  - `seg04`: `抗`

## Owner Zone

- Fresh continuation output root under
  `.tmp\v6_voiceover_regeneration_leadin_gate_*`
- Fresh run folder under that output root
- Run-local regenerated voiceover artifacts
- Run-local final media if the gate passes
- `docs/construction-guides/work-orders/2026-07-07-v6-voiceover-regeneration-leadin-gate-report.md`

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
- Existing V6 run:
  `.tmp\graduation_v6_transcript_repair_leadin_qa_20260707-212257\run`
- `video_pipeline_core/`
- `tools/`
- `tests/`
- `skills/`
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

## Required Pieces

### 1. Fresh Continuation Setup

- Create a fresh continuation output root and run folder.
- Copy only needed V5/V6 inputs; do not modify V5 or V6.
- Preserve V6 transcript repair artifacts:
  - `asr_raw_transcript.json`
  - `agent_transcript_repair_suggestions.json`
  - `subtitles.draft.srt`
  - `human_transcript_review_decision.json`
- Preserve V5 visual/effect/montage/music artifacts unless needed for final
  assembly.
- Record V5 and V6 unchanged proof.

### 2. Regenerate Voiceover Only

- Use the existing V5 narration text as the semantic source unless a lead-in
  repair requires minor punctuation/format changes.
- Do not add style/control words to script text.
- Avoid voice-style strings previously associated with lead-in leakage:
  - `clear narration`
  - `firm documentary delivery`
  - `warm clear documentary delivery`
- Try safer provider settings or script segmentation as needed, but record each
  attempt and its ASR result.
- Do not use fake/silent narration or reuse the failed V5 voiceover.

### 3. Independent ASR And Lead-In Gate

- Run independent ASR on regenerated voiceover outputs.
- Write `voiceover_output_probe.json`.
- Run `tools\voiceover_leadin_qa.py`.
- `voiceover_leadin_qa.json` must pass before final assembly.
- It must show no extra lead-ins such as `看我們`, `抗`, `ClearNeration`,
  or other recognized text before the expected narration prefix.

### 4. Final Assembly Only If Gate Passes

If and only if lead-in QA passes:

- Reassemble final media with regenerated voiceover.
- Preserve supervisor source audio and no VoxCPM over the supervisor section.
- Write `final_v6.mp4` or `final_v7.mp4`; record which name is used.
- Run `pipeline_home.py`, `write_delivery_gate_report.py`, and ffprobe.
- Do not write `story_human_review_decision.json`.
- Do not mark transcript review approved; existing transcript decision remains
  revision/request or human-review-required unless a real human approval exists.

## Stop-Loss Limits

Stop and report instead of forcing a pass if:

- VoxCPM/runtime cannot generate usable voiceover
- independent ASR still detects extra lead-in tokens
- `voiceover_leadin_qa.py` blocks any segment
- passing requires changing `voiceover_leadin_qa.py` or other repo code
- passing requires deleting ASR evidence
- passing requires modifying existing V5/V6 runs
- final media lacks video or audio stream

## Acceptance Commands

Expected exit code is `0` unless stop-loss is hit and reported.

```powershell
C:\Users\user\miniconda3\python.exe tools\voiceover_leadin_qa.py --run "<FRESH_RUN>" --json
C:\Users\user\miniconda3\python.exe tools\independent_voiceover_asr_qa.py --run "<FRESH_RUN>" --model tiny --language zh --json
C:\Users\user\miniconda3\python.exe tools\pipeline_home.py --run "<FRESH_RUN>" --json
C:\Users\user\miniconda3\python.exe tools\write_delivery_gate_report.py --run "<FRESH_RUN>" --json
ffprobe -v error -show_entries stream=codec_type,codec_name,duration -of json "<FRESH_RUN>\final_v6.mp4"
git diff --check
```

If the selected final file is `final_v7.mp4`, run the same ffprobe command for
that file and explain the naming deviation.

Add a final artifact check command using the pinned interpreter that prints:

- output root and run path
- V5 unchanged true/false
- V6 unchanged true/false
- regenerated voiceover files
- independent ASR transcript summary
- lead-in QA pass true/false
- detected lead-in mismatches
- final media path if produced
- video/audio streams true/false
- `story_human_review_decision.json` exists true/false
- transcript review still required true/false
- UTF-8/no-corruption true/false

## Delegated Decisions

- Exact continuation folder timestamp/name.
- Exact VoxCPM voice style, as long as it avoids known leaking style strings.
- Exact punctuation or segmentation adjustments, provided the semantic text is
  preserved.
- Whether final media is named `final_v6.mp4` or `final_v7.mp4`.
- Whether to stop before assembly if clean voiceover cannot be generated.

## Report Requirements

Write:

```text
docs/construction-guides/work-orders/2026-07-07-v6-voiceover-regeneration-leadin-gate-report.md
```

Include:

- output root and fresh run path
- V5/V6 unchanged proof
- regenerated voiceover attempts and settings
- independent ASR transcript summary
- lead-in QA result and mismatches
- final media path and ffprobe summary if created
- pipeline_home and delivery gate results
- transcript review status
- command exit codes
- UTF-8/no-corruption result
- deviations/blockers
- next recommended work

