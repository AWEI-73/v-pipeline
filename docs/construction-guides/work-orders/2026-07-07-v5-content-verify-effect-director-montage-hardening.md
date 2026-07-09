# Work Order: V5 Content Verify, Effect Director Review, And Montage Hardening

Date: 2026-07-07

## Goal

Produce a focused Graduation V5 technical review candidate and harden the
initial pipeline so future candidates are checked by actual content evidence,
not metadata-only declarations.

This round addresses four observed V4 gaps:

1. Voiceover QA passed even though independent ASR found audible
   `ClearNeration` / control-text leakage.
2. Supervisor subtitles used placeholder coverage markers such as
   `主任勉勵原音` and `後段逐字稿需人工確認`, not usable subtitles.
3. Effect/title QA checked timing metadata but not visual design quality or
   actual frame sequence behavior.
4. Opening montage is still not smooth enough; montage grammar should become
   a reusable design branch, not an ad hoc render choice.

V5 is a technical review candidate only. Do not write
`story_human_review_decision.json`.

## Context Sources

- V4 run:
  `.tmp\graduation_v4_creative_repair_20260707-180019\run`
- V4 report:
  `docs/construction-guides/work-orders/2026-07-07-v4-creative-repair-and-initial-pipeline-hardening-report.md`
- Independent V4 ASR verify artifact:
  `.tmp\verify_v4_content_qa_20260707\v4_independent_asr_probe.json`
- V4 contact sheet:
  `.tmp\graduation_v4_creative_repair_20260707-180019\run\review_artifacts_v4\v4_contact_sheet.jpg`

Important verified evidence:

- Independent ASR found `ClearNeration` in V4 voiceover and final video.
- V4 `voiceover_output_qa.json` passed because it did not run independent ASR.
- V4 `subtitles.srt` contains placeholder subtitles, not a human transcript.
- V4 title/effect lifecycle plan has timing records, but no director-quality
  visual review.

## Owner Zone

- New or updated QA/design modules under `video_pipeline_core/`:
  - independent voiceover ASR QA
  - source-speech transcript/subtitle QA hardening
  - effect director review
  - montage design/review
- New or updated CLI tools under `tools/`
- New or updated tests under `tests/`
- New fresh output root under `.tmp\graduation_v5_content_verify_effect_montage_*`
- Run-local artifacts inside the new V5 run
- `docs/video-pipeline-operating-map.md`
- `docs/pipeline-decision-tree.md`
- `docs/branch-contract-registry.md`
- `docs/branch-contract-registry.json`
- `docs/construction-guides/work-orders/2026-07-07-v5-content-verify-effect-director-montage-hardening-report.md`

## Forbidden Zone

- Existing V1 run:
  `.tmp\real_graduation_production_candidate_v1_20260707-062900\run`
- Existing V2 run:
  `.tmp\graduation_v2_creative_repair_20260707-122858\run`
- Existing V3 run:
  `.tmp\graduation_v3_visual_reviewed_creative_repair_20260707-161251\run`
- Existing V4 run:
  `.tmp\graduation_v4_creative_repair_20260707-180019\run`
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

Use existing faster-whisper support when available. If ASR runtime is missing
or fails, fail closed or stop; do not silently fall back to provider manifest
text.

## Required Pipeline Hardening

### 1. Independent Voiceover ASR QA

Add or harden a reusable QA contract that runs independent ASR on generated
voiceover wav files and/or final video narration windows.

It must fail closed when:

- ASR evidence is missing
- ASR runtime is unavailable
- transcript contains control/style leakage, including at least:
  - `ClearNeration`
  - `clear narration`
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

It must not pass by reading provider manifest text alone.

### 2. Source-Speech Transcript QA Hardening

Harden source-speech subtitle QA so placeholder coverage markers cannot pass
as delivery-quality subtitles.

It must fail closed when subtitle text includes placeholder/review-marker
phrases such as:

- `主任勉勵原音`
- `後段逐字稿需人工確認`
- `需人工確認`
- `原音`
- `review marker`
- `coverage marker`

Acceptable states:

- `pass=true` only with human transcript or ASR transcript cues that contain
  actual speech text and cover the later source-speech segment.
- `pass=false` with next action `human_transcript_review` when only marker
  subtitles exist.

Do not claim delivery subtitle completeness from marker text.

### 3. Effect Director Review

Add a reusable director-review layer for effects/titles, separate from timing
lifecycle QA.

Required input evidence:

- 0.5s contact sheet or frame sequence
- before/active/after frames for title/effect overlays
- title/effect lifecycle plan
- final video path or frame evidence path

Required output:

- `effect_director_review.json`

The review must include:

- review basis: `frame_sequence` or `video_sample`; `metadata_only` cannot pass
- findings with severity
- checks for lingering overlays, subject/face/subtitle obstruction,
  sticker-like composition, style mismatch, opener/closer story function, and
  title disappearance
- `pass=false` if blocking findings exist

### 4. Montage Design Branch

Add a reusable montage design/review contract for opener and training MV
sections.

Required artifacts:

- `montage_design_plan.json`
- `montage_timing_map.json`
- `montage_review_packet.md` or `.json`

The montage plan must record:

- story role: opener, training MV, closer, or transition
- target mood: discipline, growth, energetic training, memory, etc.
- shot count and shot functions
- beat/energy timing
- title sync points
- transitions and why they serve the story
- avoid-long-static-photo rule

The review must fail closed when the opener is only a plain title card, only a
single long static shot, or lacks story hook/payoff.

## Required V5 Repair

Create a fresh V5 run by copying only needed V4 inputs/artifacts. Do not modify
the existing V4 run.

V5 must:

- remove audible `ClearNeration` / style-control leakage
- run independent ASR QA on generated voiceover/final narration
- either produce actual source-speech subtitles or honestly block for human
  transcript review; do not use placeholder marker subtitles as pass evidence
- improve the opener using montage design: several short shots, story hook,
  title sync, and smoother transition into training
- run effect director review on V5 frames/video
- produce `final_v5.mp4` only if stop-loss conditions are not hit
- not write `story_human_review_decision.json`

## Red-First Verification

Before implementation, add failing tests proving current gaps:

- independent ASR QA fails on transcript containing `ClearNeration`
- independent ASR QA fails when only provider manifest text is present
- source-speech subtitle QA fails on placeholder marker subtitles
- effect director review fails when review basis is `metadata_only`
- effect director review fails on lingering overlay / obstruction findings
- montage review fails on plain title-card opener or one long static shot
- valid fixtures for all new/hardened contracts pass

## Acceptance Commands

Expected exit code is `0` unless a stop-loss condition is hit and reported.

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_voiceover_output_qa tests.test_source_speech_subtitle_qa tests.test_effect_director_review tests.test_montage_design_review
C:\Users\user\miniconda3\python.exe -m unittest tests.test_voiceover_output_qa tests.test_source_speech_subtitle_qa tests.test_effect_director_review tests.test_montage_design_review tests.test_delivery_gate tests.test_pipeline_home
C:\Users\user\miniconda3\python.exe <independent-voiceover-asr-qa-tool> --run "<V5_RUN>" --json
C:\Users\user\miniconda3\python.exe <source-speech-subtitle-qa-tool> --run "<V5_RUN>" --json
C:\Users\user\miniconda3\python.exe <effect-director-review-tool> --run "<V5_RUN>" --json
C:\Users\user\miniconda3\python.exe <montage-design-review-tool> --run "<V5_RUN>" --json
C:\Users\user\miniconda3\python.exe tools\pipeline_home.py --run "<V5_RUN>" --json
C:\Users\user\miniconda3\python.exe tools\write_delivery_gate_report.py --run "<V5_RUN>" --json
ffprobe -v error -show_entries stream=codec_type,codec_name,duration -of json "<V5_RUN>\final_v5.mp4"
C:\Users\user\miniconda3\python.exe -c "import json; json.load(open('docs/branch-contract-registry.json', encoding='utf-8')); print('json ok')"
git diff --check
```

Add a final artifact check command using the pinned interpreter that prints:

- V5 output root and run path
- V4 unchanged true/false
- `final_v5.mp4` exists true/false
- video/audio streams true/false
- independent voiceover ASR QA pass true/false
- ASR transcript contains `ClearNeration` true/false
- source-speech subtitle QA pass/block state
- placeholder subtitles present true/false
- effect director review pass true/false
- montage design review pass true/false
- `story_human_review_decision.json` exists true/false
- UTF-8/no-corruption true/false

## Stop-Loss Limits

Stop and report instead of forcing a pass if:

- independent ASR still detects `ClearNeration` or style/control leakage
- independent ASR runtime is unavailable
- source-speech subtitle QA only has placeholder marker subtitles
- effect director review has blocking findings
- montage review cannot produce an opener stronger than a plain title/static
  shot
- final media lacks video or audio stream
- passing requires modifying existing V1/V2/V3/V4 runs, Downloads, deliveries,
  env/venv, or reference repo
- passing requires waiving these QA checks

## Delegated Decisions

- Exact module/tool names.
- Exact ASR model size, provided it uses independent ASR and records method.
- Exact V5 folder timestamp/name.
- Exact opener montage shot choices and timing, provided montage artifacts
  record shot function and story role.
- Exact effect director review schema beyond required fields.
- Whether V5 reaches `final_v5.mp4` or stops at a truthful blocker.
- Whether source-speech subtitles are repaired by ASR transcript or stop at
  human transcript review.

## Report Requirements

Write:

```text
docs/construction-guides/work-orders/2026-07-07-v5-content-verify-effect-director-montage-hardening-report.md
```

Include:

- changed files
- red-first evidence
- V5 output root and run path
- V4 unchanged proof
- V5 final media path and ffprobe summary if created
- independent ASR transcript/probe summary
- source-speech subtitle QA result
- effect director review result and findings
- montage design/review summary
- pipeline_home and delivery gate results
- command exit codes
- UTF-8/no-corruption result
- deviations/blockers
- next recommended work

