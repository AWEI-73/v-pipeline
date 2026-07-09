# 2026-07-08 Graduation V7 Five-Minute Production Rehearsal

## Goal

Produce a five-minute-level graduation film technical review candidate, or stop with a real blocker. This round is the bridge between the current 50-60 second demo path and the future ten-minute product target.

The required user-visible goal is not "make the video longer." It is to prove whether the current video pipeline can hold story structure, visual selection, music, narration, source speech, subtitles, effects, and review artifacts at 240-300 seconds without fake completion.

## Current State

Known working pieces:

- Short technical candidates can be assembled.
- Real source material from `C:\Users\user\Downloads\微電影素材\_整理後` can be indexed and used.
- Visual selection review, title/effect lifecycle QA, montage review, source-speech subtitle QA, voiceover output QA, and delivery gate all exist.
- VoxCPM lead-in artifacts were diagnosed; bounded postprocess repair is the next required route before using regenerated narration.

Known gaps to address in this round:

- 50-60 second candidates hide long-form repetition and pacing problems.
- Voiceover may start with extra lead-in tokens such as `\u6297`, `\u5eb7`, or `\u770b\u6211\u5011`.
- Supervisor/source speech subtitles still need agent repair plus human review packet.
- Opener/closer need designed montage or memory-wall treatment, not plain title-card output.
- Training module title cards must enter and exit; they must not stay as awkward side rails.
- Sensitive visual beats must not be token-only selections.

## Owner Zone

Editable paths:

- New run/output root under `.tmp\graduation_v7_five_minute_production_rehearsal_*`
- Run-local artifacts inside that fresh output root
- `video_pipeline_core/*voiceover*leadin*.py`
- `video_pipeline_core/*voxcpm*leadin*.py`
- `video_pipeline_core/*voiceover*postprocess*.py`
- `video_pipeline_core/*transcript*repair*.py`
- `video_pipeline_core/*source_speech*subtitle*.py`
- `video_pipeline_core/*title*effect*.py`
- `video_pipeline_core/*effect*director*.py`
- `video_pipeline_core/*montage*.py`
- `video_pipeline_core/*visual_selection*.py`
- `tools/*voiceover*leadin*.py`
- `tools/*voxcpm*leadin*.py`
- `tools/*voiceover*postprocess*.py`
- `tools/*transcript*repair*.py`
- `tools/*source_speech*subtitle*.py`
- `tools/*title*effect*.py`
- `tools/*effect*director*.py`
- `tools/*montage*.py`
- `tools/*visual_selection*.py`
- Relevant tests under `tests/`
- `docs/branch-contract-registry.md`
- `docs/branch-contract-registry.json`
- `docs/video-pipeline-operating-map.md`
- `docs/pipeline-decision-tree.md`
- `docs/construction-guides/work-orders/2026-07-08-graduation-v7-five-minute-production-rehearsal-report.md`

## Forbidden Zone

Read-only paths:

- Existing `.tmp\graduation_v*` runs
- Existing `.tmp\v6_*` runs
- Existing `.tmp\voxcpm_provider_leadin_artifact_diagnostic_*` runs
- `deliveries\`
- `.env`, `.env.*`
- `.venv_voxcpm\`
- `reference repo\`
- VoxCPM reference/source repository
- `Downloads\` as a write target
- `story_human_review_decision.json` in any run
- Git branch/commit/push operations

Read-only source input allowed:

- `C:\Users\user\Downloads\微電影素材\_整理後`

## Required Pieces

1. Create a fresh V7 output root. Do not modify V1-V6 or diagnostic source runs.
2. Record source preflight for `C:\Users\user\Downloads\微電影素材\_整理後`: existence, media counts, source-root music candidates, supervisor/source speech candidates, and training module coverage.
3. Build a five-minute production plan targeting 240-300 seconds. Required structure:
   - opener story/memory-wall or designed montage: 20-40 seconds
   - training MV body: 150-210 seconds
   - supervisor/source speech: 20-45 seconds
   - teacher/class intro: 20-45 seconds
   - closing story/payoff: 20-40 seconds
4. The training MV body must cover at least four usable module families from: basic training, advanced training, certification/check, physical/activity, encouragement/activity, daily-life optional, special activity. If any family has insufficient source evidence, record the substitution instead of fabricating coverage.
5. Visual selection must be review-facing before render-facing. Sensitive beats, including newcomer/basic training/supervisor speech, require visual selection review evidence. Token-only selection is not render-facing.
6. Opener and closer must be self-made designed sections from real material, montage, memory wall, generated effect assets, or existing effect-factory route. Plain white-card or static title-only open/close is not acceptable.
7. Title/effect treatments for training modules must have lifecycle timing: enter, readable hold, exit. Persistent side rails or text stuck over unrelated footage must block.
8. Music should not default to the old source-folder training music. Prefer a new external/sourceable music route, or explicitly justify source-folder use. Human/legal music-use review remains required and cannot be claimed complete.
9. Supervisor/source speech must use the source video's original audio. Do not cover it with VoxCPM narration. Source speech must have agent transcript repair suggestions and a human transcript review packet.
10. Voiceover must be sparse and story-supporting, not full-time narration. Before final assembly, run the bounded lead-in repair path:
    - identify failing segments
    - apply safe trim/postprocess only to failing segments, or regenerate with safer segmentation
    - prove the intended first text survives
    - rerun independent ASR and lead-in QA for every narration segment
11. Assemble `final_v7.mp4` only if visual selection, voiceover lead-in, title/effect lifecycle, source speech subtitle, montage/effect review, and media stream checks pass. Otherwise stop before final assembly and report the first real blocker.
12. Produce a review packet for eye/ear/brain review:
    - eye: contact sheet, section timing, visual/module coverage, title/effect lifecycle
    - ear: music source, ducking, narration QA, source speech preservation
    - brain: story structure, opener-to-MV-to-speech-to-intro-to-closing coherence, unresolved human decisions
13. Run `pipeline_home.py` and `write_delivery_gate_report.py` on the fresh V7 run if final media exists. If final media does not exist, run `pipeline_home.py` and record why delivery gate was not reached.
14. Do not write `story_human_review_decision.json`. Delivery can reach technical pass with `story_human_review_required`, but that is not final approval.

## Red-First Verification

Before implementation, capture at least one failing evidence path that proves the old short-demo route is insufficient for this five-minute route. Acceptable red-first evidence includes:

- Lead-in QA fails on unprocessed VoxCPM narration.
- Visual-selection gate blocks token-only sensitive beats.
- Title/effect lifecycle QA blocks a persistent rail or missing exit.
- Production-plan validation rejects duration under 240 seconds or missing MV module coverage.

Use the pinned interpreter:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest <focused_tests_for_changed_modules>
```

Record the exact red command and failure in the report.

## Acceptance Commands

Use `C:\Users\user\miniconda3\python.exe` for every Python command. Do not use bare `python` or `pytest`.

Expected exit code `0`:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_voiceover_leadin_qa tests.test_voiceover_output_qa tests.test_source_speech_transcript_repair tests.test_visual_selection_review_decision tests.test_graduation_film_blueprint_catalog tests.test_pipeline_home
```

If new focused tests are added, also run them explicitly with expected exit code `0`.

If final media exists, expected exit code `0`:

```powershell
ffprobe -v error -show_entries stream=codec_type,codec_name,duration -of json ".tmp\<fresh_v7_root>\run\final_v7.mp4"
```

If final media exists, expected exit code `0`:

```powershell
C:\Users\user\miniconda3\python.exe tools\pipeline_home.py --run ".tmp\<fresh_v7_root>\run" --json
```

If final media exists, expected exit code `0` or explicit expected block:

```powershell
C:\Users\user\miniconda3\python.exe tools\write_delivery_gate_report.py --run ".tmp\<fresh_v7_root>\run" --json
```

Registry parse, if registry JSON is edited:

```powershell
C:\Users\user\miniconda3\python.exe -c "import json; json.load(open('docs/branch-contract-registry.json', encoding='utf-8')); print('json ok')"
```

Expected exit code `0`:

```powershell
git diff --check
```

Final artifact check, run with pinned Python, must verify:

- Fresh V7 output root exists.
- `final_v7.mp4` exists with 240-300 second duration, or a stop-loss report explains why it does not.
- If `final_v7.mp4` exists, ffprobe shows both video and audio streams.
- No `story_human_review_decision.json` was written.
- Existing V1-V6 and diagnostic runs were not modified.
- Generated JSON/Markdown/SRT text decodes with UTF-8 and contains no `\ufffd` or suspicious repeated literal question-mark runs.
- Review packet exists and includes eye/ear/brain sections.
- Human/legal music-use review remains unresolved unless the user explicitly provided separate evidence.

## Stop-Loss Limits

- If source preflight fails, stop.
- If five-minute render is too slow or fails, stop with render evidence; do not shorten below 240 seconds unless reporting a blocker.
- If bounded voiceover repair cannot pass lead-in QA without damaging first text, stop before final assembly.
- If supervisor/source speech subtitle evidence is placeholder-only or not reviewable, stop before claiming candidate status.
- If visual-selection evidence cannot replace token-only sensitive beats, stop before render-facing assembly.
- If final media lacks video or audio stream, stop.
- Do not use waiver to bypass missing narration, subtitle, source speech, visual selection, or music evidence.

## Delegated Decisions

- Exact V7 output root suffix.
- Exact training module ordering, as long as it follows a coherent story arc and records the decision.
- Exact opener/closer effect route: montage, memory wall, effect factory, generated image/effect asset, or mixed route.
- Exact narration count and timing, as long as it stays sparse and QA passes.
- Exact music source, as long as it is not silently the old default and the evidence records source/license caveat.
- Whether to stop at a technical blocker or produce `final_v7.mp4`, based only on acceptance evidence.

## Final Report Requirements

Write `docs/construction-guides/work-orders/2026-07-08-graduation-v7-five-minute-production-rehearsal-report.md` with:

- Output root and run path.
- Whether `final_v7.mp4` exists; if yes, duration and stream evidence.
- Commands and exit codes.
- Red-first evidence.
- Section timing plan vs actual.
- Training module coverage.
- Visual selection review evidence.
- Voiceover lead-in repair evidence and ASR results.
- Supervisor/source speech preservation and transcript repair packet paths.
- Music source and legal-use caveat.
- Eye/ear/brain review packet path.
- Delivery gate and pipeline home results, if reached.
- Confirmation that no final human approval was written.
- Deviations, blockers, and next recommended work toward a future ten-minute production route.
