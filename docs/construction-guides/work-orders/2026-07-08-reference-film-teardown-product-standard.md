# 2026-07-08 Reference Film Teardown Product Standard

## Goal

Use the existing graduation finished film as the product reference, then derive a concrete production standard for the pipeline. This round must stop the loop of isolated artifact completion by answering: what does a good graduation film in this source set actually do, and what must the pipeline reproduce before the next render rehearsal?

This is a reference teardown and product-standard round. Do not render a new film.

## User-Approved Basis

The user approved using the finished graduation film as the reference standard. This approval is only for analysis and rehearsal planning. It is not final delivery approval for any future output.

Reference candidates in the real source folder:

- `C:\Users\user\Downloads\微電影素材\_整理後\67期結訓影片-終.mp4`
- `C:\Users\user\Downloads\微電影素材\_整理後\最終版的最終版.mp4`

If both exist and are byte-identical or duration-identical, pick one as the primary reference and record the duplicate relationship. If one is missing, use the one that exists. If neither exists, stop after preflight.

## Source Basis

Use these prior outputs as comparison inputs:

- `.tmp\soul_first_real_material_planning_20260708-060509`
- `.tmp\shot_level_material_proof_completion_20260708-080727`
- `.tmp\effect_factory_integration_completion_20260708-154117`

Real source input remains read-only:

`C:\Users\user\Downloads\微電影素材\_整理後`

## Owner Zone

Editable paths:

- New output root under `.tmp\reference_film_teardown_product_standard_*`
- Run-local artifacts inside that fresh output root
- `video_pipeline_core/*reference*film*.py`
- `video_pipeline_core/*product*standard*.py`
- `video_pipeline_core/*film*teardown*.py`
- `video_pipeline_core/*timeline*analysis*.py`
- `video_pipeline_core/*effect*analysis*.py`
- `video_pipeline_core/*music*analysis*.py`
- `tools/*reference*film*.py`
- `tools/*product*standard*.py`
- `tools/*film*teardown*.py`
- `tools/*timeline*analysis*.py`
- `tools/*effect*analysis*.py`
- `tools/*music*analysis*.py`
- Relevant tests under `tests/`
- `docs/branch-contract-registry.md`
- `docs/branch-contract-registry.json`
- `docs/video-pipeline-operating-map.md`
- `docs/pipeline-decision-tree.md`
- `docs/construction-guides/work-orders/2026-07-08-reference-film-teardown-product-standard-report.md`

## Forbidden Zone

Read-only paths:

- `C:\Users\user\Downloads\微電影素材\_整理後`
- `.tmp\soul_first_real_material_planning_20260708-060509`
- `.tmp\shot_level_material_proof_completion_20260708-080727`
- `.tmp\effect_factory_integration_completion_20260708-154117`
- Existing `.tmp\graduation_v*` runs
- Existing `.tmp\v6_*` runs
- Existing `.tmp\voxcpm_provider_leadin_artifact_diagnostic_*` runs
- `deliveries\`
- `.env`, `.env.*`
- `.venv_voxcpm\`
- `reference repo\`
- VoxCPM reference/source repository
- Existing final media artifacts
- `story_human_review_decision.json` in any run
- Git branch/commit/push operations

## Required Pieces

1. Create a fresh no-render output root. Do not mutate prior outputs or source material.
2. Produce `reference_film_preflight.json`:
   - candidate paths
   - exists/is_file
   - file size
   - ffprobe duration
   - streams
   - primary reference selection
   - duplicate relationship, if any
3. Produce `reference_frame_sampling_plan.json` and frame evidence:
   - at least 0.5s or 1.0s interval sampling for the first 60s, last 60s, and representative middle windows
   - contact sheets for opener, middle/MV, speech/intro, ending
   - do not extract the entire film if disk/time is unreasonable; choose representative windows and record coverage
4. Produce `reference_structure_timeline.json`. It must segment the reference into product sections such as:
   - opener/title hook
   - training MV modules
   - source speech/supervisor or formal remarks
   - teacher/class/person intro
   - activity/emotional montage
   - closing/payoff
   - ending/coda
   Record start/end/duration, evidence frames, audio/music notes, subtitles/title notes, and confidence.
5. Produce `reference_effect_subtitle_music_audit.json`:
   - opener effects
   - transition effects
   - chapter/title treatment behavior
   - subtitle/lower-third design
   - music sections and mood changes
   - source audio / ducking / speech handling
   - closing effect/payoff design
6. Produce `reference_shot_reuse_map.json`:
   - repeated footage or motifs
   - whether repeat acts as callback, rhythm, emphasis, or filler
   - rough unique visual density
   - suspected old compiled/source segment usage if visible
7. Produce `reference_product_standard.json`. This is the key artifact. It must define product-level standards for future graduation film runs:
   - story structure and section order flexibility
   - opener expectations
   - MV module pacing
   - title/subtitle behavior
   - effect line requirements
   - music/source-audio policy
   - acceptable use of repeated footage
   - proof vs support material policy
   - five-minute and ten-minute expectations
8. Produce `gap_against_current_pipeline.json` comparing the reference standard to:
   - soul-first package
   - shot-level proof package
   - effect-factory package
   - current no-narration / source-speech / narrated profiles
   The gap must classify each item as `covered`, `partial`, `blocked`, or `missing`.
9. Produce `next_render_rehearsal_spec.json`. It must convert the teardown into a concrete next render rehearsal spec, including:
   - recommended profile
   - target duration
   - required sections
   - effect assets to use or revise
   - music approach
   - subtitle/title requirements
   - certification/check handling
   - source speech handling
   - stop-loss limits
10. Produce `reference_teardown_review_packet.md` for human review. It should be readable as a director/editor critique, not just a JSON artifact list.
11. If adding/changing tools, write red-first tests. If no code changes are made, run an executable pinned-Python artifact check that verifies required files and fields.

## Red-First Verification

Before implementation, capture failing evidence that the current pipeline lacks a reference-standard teardown. Acceptable red-first evidence:

- No `reference_product_standard.json` exists for the finished graduation film.
- Current render rehearsal spec does not compare against the finished reference.
- Current effect package exists but has no reference-film standard alignment.

Use pinned interpreter:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest <focused_tests_for_changed_modules>
```

If no code changes are made, use a pinned Python precheck that exits non-zero and records missing reference-standard artifacts.

## Acceptance Commands

Use `C:\Users\user\miniconda3\python.exe` for every Python command. Do not use bare `python` or `pytest`.

If code/tests are changed, expected exit code `0`:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest <new_or_changed_focused_tests>
```

Run the reference teardown generator/check with pinned Python. The exact command is delegated, but it must write all required artifacts under the fresh `.tmp\reference_film_teardown_product_standard_*` root and exit `0` unless a real stop-loss is reached.

Registry parse, if registry JSON is edited:

```powershell
C:\Users\user\miniconda3\python.exe -c "import json; json.load(open('docs/branch-contract-registry.json', encoding='utf-8')); print('json ok')"
```

Expected exit code `0`:

```powershell
git diff --check
```

Final artifact check, run with pinned Python, must verify:

- Fresh output root exists.
- No new rendered final film was created.
- Required teardown artifacts exist.
- Primary reference film exists and has ffprobe evidence.
- At least one contact sheet or frame evidence artifact exists for opener, middle/MV, and ending.
- `reference_product_standard.json` exists and contains product standards, not only technical metadata.
- `gap_against_current_pipeline.json` compares against prior soul/shot/effect packages.
- `next_render_rehearsal_spec.json` exists and is actionable.
- Prior source, prior outputs, and existing V-runs were not modified.
- Generated JSON/Markdown text decodes with UTF-8 and contains no `\ufffd` or suspicious repeated literal question-mark runs.

## Stop-Loss Limits

- If no reference candidate exists, stop after preflight.
- If ffprobe fails for the reference, stop and report the media blocker.
- If frame extraction/contact sheet creation fails, stop or reduce sampling window and record the reduced coverage.
- If teardown cannot distinguish sections with reasonable confidence, mark low confidence and do not invent exact section labels.
- Do not render a new film.
- Do not write `story_human_review_decision.json`.
- Do not claim legal/music approval.
- Do not change VoxCPM behavior.
- Do not overwrite or modify the reference film.

## Delegated Decisions

- Exact sampling interval and representative middle windows, as long as coverage is recorded.
- Exact section labels, as long as confidence is recorded.
- Exact product standard schema.
- Whether to add reusable tools or produce run-local artifacts only.
- Whether the next render spec targets five minutes or shorter/longer based on reference evidence.

## Final Report Requirements

Write `docs/construction-guides/work-orders/2026-07-08-reference-film-teardown-product-standard-report.md` with:

- Output root and command/exit-code table.
- Red-first evidence.
- Primary reference film path and ffprobe summary.
- Structure timeline summary.
- Effect/subtitle/music audit summary.
- Shot reuse/product design observations.
- Product standards extracted.
- Gap against current pipeline.
- Next render rehearsal spec.
- Human review packet path.
- Confirmation that no new final render/final approval was written.
- Deviations, blockers, and next recommended work.
