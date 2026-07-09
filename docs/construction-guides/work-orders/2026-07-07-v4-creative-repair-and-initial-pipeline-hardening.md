# Work Order: V4 Creative Repair And Initial Pipeline Hardening

Date: 2026-07-07

## Goal

Produce a Graduation V4 technical review candidate from the existing V3 run,
and harden the initial pipeline so three user-observed V3 defects are caught
before future delivery candidates:

1. Voiceover style/control text leak, e.g. spoken `firm documentary delivery`
   or similar English control words.
2. Title/effect subtitle card lifecycle defect: title cards or side labels
   linger after the intended title moment.
3. Supervisor/source-speech subtitle QA defect: subtitles are wrong or missing
   in the later part of the speaking segment.

V4 is not final creative approval. Do not write
`story_human_review_decision.json`.

## Context Sources

- V3 run:
  `.tmp\graduation_v3_visual_reviewed_creative_repair_20260707-161251\run`
- V3 resume report:
  `docs/construction-guides/work-orders/2026-07-07-voxcpm-3221225477-diagnostic-v3-resume-report.md`
- V3 repair report:
  `docs/construction-guides/work-orders/2026-07-07-graduation-v3-visual-reviewed-creative-repair-report.md`
- Visual review writer report:
  `docs/construction-guides/work-orders/2026-07-07-visual-selection-review-writer-report.md`

User V3 review:

- English voiceover text like `FERN DOUCUMENT DELIVERY` / style-control text
  is still audible and must be removed.
- Title/effect subtitle card can disappear with the title; it should not stay
  on screen.
- Supervisor subtitles have problems; the later part is missing and needs a
  check path.
- Everything else is broadly acceptable for a focused V4 repair.

## Owner Zone

- New or updated focused QA modules under `video_pipeline_core/` for:
  - voiceover output QA
  - title/effect lifecycle QA
  - source-speech subtitle completeness QA
- New or updated CLI tools under `tools/` for those QA checks if useful
- New or updated tests under `tests/`
- New fresh output root under `.tmp\graduation_v4_creative_repair_*`
- Run-local artifacts inside the new V4 run
- `docs/video-pipeline-operating-map.md`
- `docs/pipeline-decision-tree.md`
- `docs/branch-contract-registry.md`
- `docs/branch-contract-registry.json`
- `docs/construction-guides/work-orders/2026-07-07-v4-creative-repair-and-initial-pipeline-hardening-report.md`

## Forbidden Zone

- Existing V1 run:
  `.tmp\real_graduation_production_candidate_v1_20260707-062900\run`
- Existing V2 run:
  `.tmp\graduation_v2_creative_repair_20260707-122858\run`
- Existing V3 run:
  `.tmp\graduation_v3_visual_reviewed_creative_repair_20260707-161251\run`
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

## Required Pipeline Hardening

### 1. Voiceover Output QA

Add a reusable QA contract that checks generated voiceover output artifacts,
not only the input script.

It must fail closed when transcript/ASR/recognized text or provider output
metadata contains control/style leakage terms, including at least:

- `firm documentary delivery`
- `warm clear documentary delivery`
- `documentary delivery`
- `Mandarin narrator`
- `voice`
- `style`
- `prompt`
- `普通話`
- `設定`
- `參數`

If real ASR is unavailable, the check may use existing provider transcripts,
manifest text, subtitles, or a recorded `voiceover_output_probe.json`, but it
must not pass silently without evidence. Missing probe evidence must block or
mark `needs_voiceover_output_probe`.

### 2. Title / Effect Lifecycle QA

Add a reusable QA contract for title/effect overlays.

It must require title/effect artifacts to record:

- section or beat id
- appear/start time
- disappear/end time
- max duration
- whether it must clear before the next section
- evidence frame or timing proof

It must fail closed when a title/effect card is persistent, lacks an end time,
overlaps the next section when `must_clear_before_next_section=true`, or has no
timing evidence.

### 3. Source-Speech Subtitle Completeness QA

Add a reusable QA contract for source-speech subtitle coverage.

It must require:

- source speech segment start/end
- subtitle cue list or subtitle alignment report
- coverage of the later portion of the segment
- last cue end time close enough to the speech segment end, or explicit
  `needs_human_transcript_review`
- ASR-derived subtitles marked as requiring human transcript review unless a
  human transcript artifact is present

It must fail closed when later coverage is missing, cue timing is outside the
source-speech segment, or subtitle evidence is absent.

## Required V4 Repair

Create a fresh V4 run by copying only needed V3 inputs/artifacts. Do not modify
the existing V3 run.

V4 must:

- keep V3 visual-selection decisions unless a hard gate requires otherwise
- remove voiceover style/control leakage from generated narration
- regenerate or repair affected narration/audio artifacts
- repair title/effect lifecycle so title cards clear with their title moment
- repair supervisor subtitle coverage, especially the later portion
- preserve supervisor source speech original audio
- produce `final_v4.mp4`
- create or update run-local QA artifacts:
  - `voiceover_output_qa.json`
  - `title_effect_lifecycle_qa.json`
  - `source_speech_subtitle_qa.json`
- not write `story_human_review_decision.json`

## Red-First Verification

Before implementation, add failing tests proving current gaps:

- voiceover QA fails on transcript text containing `firm documentary delivery`
  or `Mandarin narrator`
- voiceover QA fails when output probe evidence is missing
- title/effect QA fails when a title has no end time or overlaps the next
  section
- source-speech subtitle QA fails when final/later subtitle coverage is absent
- valid fixtures for all three QA contracts pass

## Acceptance Commands

Expected exit code is `0` unless a stop-loss condition is hit and reported.

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_voiceover_output_qa tests.test_title_effect_lifecycle_qa tests.test_source_speech_subtitle_qa
C:\Users\user\miniconda3\python.exe -m unittest tests.test_voiceover_output_qa tests.test_title_effect_lifecycle_qa tests.test_source_speech_subtitle_qa tests.test_delivery_gate tests.test_pipeline_home
C:\Users\user\miniconda3\python.exe <voiceover-qa-tool> --run "<V4_RUN>" --json
C:\Users\user\miniconda3\python.exe <title-effect-qa-tool> --run "<V4_RUN>" --json
C:\Users\user\miniconda3\python.exe <source-speech-subtitle-qa-tool> --run "<V4_RUN>" --json
C:\Users\user\miniconda3\python.exe tools\pipeline_home.py --run "<V4_RUN>" --json
C:\Users\user\miniconda3\python.exe tools\write_delivery_gate_report.py --run "<V4_RUN>" --json
ffprobe -v error -show_entries stream=codec_type,codec_name,duration -of json "<V4_RUN>\final_v4.mp4"
C:\Users\user\miniconda3\python.exe -c "import json; json.load(open('docs/branch-contract-registry.json', encoding='utf-8')); print('json ok')"
git diff --check
```

Add a final artifact check command using the pinned interpreter that prints:

- V4 output root and run path
- V3 unchanged true/false
- `final_v4.mp4` exists true/false
- video/audio streams true/false
- voiceover output QA pass true/false
- title/effect lifecycle QA pass true/false
- source-speech subtitle QA pass true/false
- supervisor source audio preserved true/false
- `story_human_review_decision.json` exists true/false
- UTF-8/no-corruption true/false

## Stop-Loss Limits

Stop and report instead of forcing a pass if:

- clean generated voiceover cannot be produced without style/control leakage
- title/effect lifecycle cannot be represented with timing evidence
- source-speech subtitle later coverage cannot be produced or marked for human
  transcript review
- final media lacks video or audio stream
- passing requires modifying Downloads, deliveries, env/venv, reference repo,
  or existing V1/V2/V3 runs
- passing requires waiving these QA checks

## Delegated Decisions

- Exact module/tool names.
- Exact QA JSON schemas beyond the required fields.
- Whether the QA tools consume run-local artifacts directly or explicit input
  paths.
- Exact V4 folder timestamp/name.
- Exact title/effect timing repair style, as long as cards clear on time.
- Whether supervisor subtitle QA passes via improved ASR coverage or explicit
  `needs_human_transcript_review`, as long as the result is honest and gate
  state is reported.
- Whether delivery gate passes; if it blocks, report the blockers honestly.

## Report Requirements

Write:

```text
docs/construction-guides/work-orders/2026-07-07-v4-creative-repair-and-initial-pipeline-hardening-report.md
```

Include:

- changed files
- red-first evidence
- V4 output root and run path
- V3 unchanged proof
- V4 final media path and ffprobe summary if created
- three QA artifacts and pass/block status
- voiceover leakage check result
- title/effect lifecycle repair summary
- supervisor subtitle completeness result
- supervisor source-audio preservation evidence
- pipeline_home and delivery gate results
- command exit codes
- UTF-8/no-corruption result
- deviations/blockers
- next recommended work

