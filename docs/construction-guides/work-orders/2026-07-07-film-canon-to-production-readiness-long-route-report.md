# Film Canon To Production Readiness Long Route Report

Date: 2026-07-07

## Files Changed

- `video_pipeline_core/film_canon_production_readiness.py`
- `tools/film_canon_readiness.py`
- `tests/test_graduation_film_blueprint_catalog.py`
- `docs/video-pipeline-operating-map.md`
- `docs/pipeline-decision-tree.md`
- `docs/branch-contract-registry.md`
- `docs/branch-contract-registry.json`
- `docs/construction-guides/work-orders/2026-07-07-film-canon-to-production-readiness-long-route-report.md`

## Red-First Evidence

- Command: `C:\Users\user\miniconda3\python.exe -m unittest tests.test_graduation_film_blueprint_catalog`
- Exit code: `1`
- Result: failed with `ModuleNotFoundError: No module named 'video_pipeline_core.film_canon_production_readiness'`.

## Implemented Route Chain

Implemented:

```text
film_canon_route dry-run
  -> product_route_review_decision.json
  -> reviewed_catalog_map.json
  -> story_material_planning_handoff.json
  -> opener_closer_design_handoff.json
  -> audio_subtitle_review_handoff.json
  -> production_readiness_gate.json
  -> production_worker_handoff_prompt.md
  -> product_route_review_packet.md/json
```

New helper:

- `video_pipeline_core.film_canon_production_readiness`

New CLI:

- `tools\film_canon_readiness.py`

## Graduation Real-Source Smoke

- Output root: `.tmp\film_canon_production_readiness_20260707-011141`
- Graduation output: `.tmp\film_canon_production_readiness_20260707-011141\graduation`
- Source root: `C:\Users\user\Downloads\微電影素材\_整理後`
- Source preflight: `exists=true`, `is_dir=true`, `file_count=306`, `media_count=198`
- Review decision: `pending_review`, reviewer `none`
- Readiness: `ready_for_production=false`
- Blockers: `product_route_review_required`
- Warnings: `catalog_has_missing_modules`
- Next owner: `waiting_product_review`
- Safe next command: `review or repair product route before production`

Reviewed catalog status counts:

- `accepted`: 0
- `rejected`: 0
- `needs_reassign`: 0
- `optional`: 0
- `missing`: 2
- `pending_review`: 222

Integrator correction after review:

- Initial worker output counted all unreviewed assignments as `missing`.
- The readiness map now separates real material gaps from unreviewed material: unreviewed assignments are `pending_review`, while `missing` is reserved for modules with no material assignments.
- The graduation smoke still warns `catalog_has_missing_modules` because `certification` and `encouragement_activity` have no matched material in this source-root pass.

## Daily Kids Fixture Smoke

- Daily kids output: `.tmp\film_canon_production_readiness_20260707-011141\daily_kids`
- Fixture-only source root: `.tmp\film_canon_production_readiness_20260707-011141\fixtures\daily_kids_source`
- Review decision: `approved`, reviewer `human`
- Readiness: `ready_for_production=true`
- Blockers: `[]`
- Warnings: `[]`
- Next owner: `production_worker`
- Safe next command: `dispatch production worker from production_worker_handoff_prompt.md`

Reviewed catalog status counts:

- `accepted`: 8
- `rejected`: 0
- `needs_reassign`: 0
- `optional`: 0
- `missing`: 0
- `pending_review`: 0

## Product Review Decision Behavior

- `approved` + `reviewer=human` can make the route production-ready.
- `approved` + non-human reviewer does not make the route production-ready; it routes to `waiting_product_review`.
- `revision_requested` routes to `repair_product_route`.
- `rejected` routes to `repair_product_route`.
- Product-route approval is explicitly not final delivery approval.
- No `story_human_review_decision.json` is written.

## Handoff Summaries

Graduation handoffs:

- `story_material_planning_handoff.json`: selected film type, selected story shell basis, accepted/review-needed module groups, retargeted sections, next owner.
- `opener_closer_design_handoff.json`: `opening_story` and `closing_story` are design/story sections, no plain white-card ending, target duration ranges, Effect Factory return route.
- `audio_subtitle_review_handoff.json`: supervisor/source speech intelligibility required, preserved source speech subtitles required, MV music ducking policy, teacher/class intro readability, owner route `subtitle-voiceover`.

Daily kids handoffs:

- `story_material_planning_handoff.json`: fixture-approved catalog groups and production worker path.
- `opener_closer_design_handoff.json`: `opening_memory_hook` and `closing_memory_note`, warm memory design intent.
- `audio_subtitle_review_handoff.json`: warm/light music, preserve intelligible child speech/laughter when useful, subtitles only as needed.

## Production Readiness Gate Summaries

Graduation:

- `ready_for_production=false`
- `next_owner=waiting_product_review`
- blocker: `product_route_review_required`

Daily kids:

- `ready_for_production=true`
- `next_owner=production_worker`
- no blockers

## No Render / No Final Human Approval

- Graduation `final.mp4` exists: `false`
- Graduation `story_human_review_decision.json` exists: `false`
- Daily kids `final.mp4` exists: `false`
- Daily kids `story_human_review_decision.json` exists: `false`
- No render command was run.
- No final human delivery approval was written.

## UTF-8 / No-Corruption

- Explicit final check result: `utf8_no_corruption=true`
- Bad text artifacts: `[]`
- Checked generated readiness `.json` and `.md` artifacts for UTF-8 decode, replacement characters, and `????` placeholder runs.

## Commands

- `C:\Users\user\miniconda3\python.exe -m unittest tests.test_graduation_film_blueprint_catalog`
  - Exit code: `1`
  - Purpose: red-first evidence.
- `C:\Users\user\miniconda3\python.exe -m unittest tests.test_graduation_film_blueprint_catalog`
  - Exit code: `0`
  - Result after integrator correction: `Ran 15 tests ... OK`
- `C:\Users\user\miniconda3\python.exe -m unittest tests.test_graduation_film_blueprint_catalog tests.test_soundtrack_arranger tests.test_pipeline_home`
  - Exit code: `0`
  - Result: `Ran 109 tests ... OK`
- `C:\Users\user\miniconda3\python.exe tools\film_canon_route.py --list --json`
  - Exit code: `0`
  - Result: listed `graduation_training_film` and `daily_kids_memory_film`.
- `C:\Users\user\miniconda3\python.exe -c "... real source preflight ..."`
  - Exit code: `0`
  - Result: `exists=True`, `is_dir=True`, `file_count=306`, `media_count=198`
- `C:\Users\user\miniconda3\python.exe tools\film_canon_readiness.py --film-type graduation_training_film --source-root "C:\Users\user\Downloads\微電影素材\_整理後" --out-dir ".tmp\film_canon_production_readiness_20260707-011141\graduation" --json`
  - Exit code: `0`
  - Result: wrote readiness artifacts; gate not ready because product-route review is pending.
- `C:\Users\user\miniconda3\python.exe tools\film_canon_readiness.py --film-type daily_kids_memory_film --source-root ".tmp\film_canon_production_readiness_20260707-011141\fixtures\daily_kids_source" --out-dir ".tmp\film_canon_production_readiness_20260707-011141\daily_kids" --json`
  - Exit code: `0`
  - Result: wrote readiness artifacts; fixture human-approved route ready for production worker.
- `C:\Users\user\miniconda3\python.exe -c "... final explicit checks ..."`
  - Exit code: `0`
  - Result: printed output root, readiness states, decisions, status counts, handoff paths, blockers/warnings, no-render/no-approval, and UTF-8 result.
- `C:\Users\user\miniconda3\python.exe -c "import json; json.load(open('docs/branch-contract-registry.json', encoding='utf-8')); print('json ok')"`
  - Exit code: `0`
  - Result: `json ok`
- `git diff --check`
  - Exit code: `0`
  - Result: no whitespace errors; Git printed CRLF warnings for modified tracked docs.

## Deviations

- None.

## Stop-Loss

- Not stopped.
- No render, delivery gate semantics, VoxCPM, soundtrack provider, deliveries, or existing `.tmp` run changes were required.
- Downloads was read-only.

## Next Recommended Work

Create a human product-route review writer for `product_route_review_decision.json` so the real graduation route can move from `waiting_product_review` to either production readiness or a documented repair path without hand-editing JSON.
