# Film Canon Registry Product Route Selector Report

Date: 2026-07-07

## Files Changed

- `video_pipeline_core/film_canon_registry.py`
- `tools/film_canon_route.py`
- `tools/graduation_film_blueprint_catalog.py`
- `tests/test_graduation_film_blueprint_catalog.py`
- `docs/video-pipeline-operating-map.md`
- `docs/pipeline-decision-tree.md`
- `docs/branch-contract-registry.md`
- `docs/branch-contract-registry.json`
- `docs/construction-guides/work-orders/2026-07-07-film-canon-registry-product-route-selector-report.md`

## Red-First Evidence

- Command: `C:\Users\user\miniconda3\python.exe -m unittest tests.test_graduation_film_blueprint_catalog`
- Exit code: `1`
- Result: failed with `ModuleNotFoundError: No module named 'video_pipeline_core.film_canon_registry'`.

## Registry Design

- New module: `video_pipeline_core/film_canon_registry.py`
- New selector CLI: `tools/film_canon_route.py`
- Registry functions:
  - `list_supported_film_types()`
  - `get_film_canon_route(film_type)`
  - `write_film_canon_route_dry_run(film_type, source_root, out_dir)`
- `graduation_training_film` delegates to the existing graduation helper and preserves graduation artifact names.
- `daily_kids_memory_film` writes common film-type artifacts:
  - `film_canon.json`
  - `film_blueprint.json`
  - `story_shell.json`
  - `catalog_map.json`
  - `review_packet.md`
  - `review_packet.json`
- Unknown film types fail closed with CLI exit code `2`.

## Supported Film Types

- `graduation_training_film`
- `daily_kids_memory_film`

## Graduation Fixture Smoke

- Output root: `.tmp\film_canon_route_selector_20260707-005446`
- Graduation output: `.tmp\film_canon_route_selector_20260707-005446\graduation`
- Canon sections:
  - `opening_story`
  - `training_mv_catalog`
  - `supervisor_speech`
  - `teacher_class_intro`
  - `closing_story`
- Catalog modules:
  - `basic_training`
  - `advanced_training`
  - `certification`
  - `physical_activity`
  - `encouragement_activity`
  - `daily_life_optional`
  - `supervisor_speech`
  - `teacher_class_intro`
  - `closing_story`
  - `special_activity`
- Review packet: `.tmp\film_canon_route_selector_20260707-005446\graduation\graduation_real_source_review_packet.json`
- `final.mp4` exists: `false`
- `story_human_review_decision.json` exists: `false`

## Daily Kids Fixture Smoke

- Daily kids output: `.tmp\film_canon_route_selector_20260707-005446\daily_kids`
- Canon sections:
  - `opening_memory_hook`
  - `daily_life_montage`
  - `milestone_moments`
  - `cute_funny_moments`
  - `family_interaction`
  - `closing_memory_note`
- Catalog modules:
  - `eating`
  - `playing`
  - `learning`
  - `family`
  - `outdoor`
  - `school`
  - `birthday_or_special_event`
  - `random_cute_optional`
- Catalog summary:
  - `module_count`: 8
  - `material_count`: 8
  - `agent_filled_count`: 8
  - `needs_human_confirmation_count`: 8
- Review packet: `.tmp\film_canon_route_selector_20260707-005446\daily_kids\review_packet.json`
- `final.mp4` exists: `false`
- `story_human_review_decision.json` exists: `false`

## CLI Examples

```powershell
C:\Users\user\miniconda3\python.exe tools\film_canon_route.py --list --json
C:\Users\user\miniconda3\python.exe tools\film_canon_route.py --film-type graduation_training_film --source-root "<fixture>" --out-dir "<out-root>\graduation" --json
C:\Users\user\miniconda3\python.exe tools\film_canon_route.py --film-type daily_kids_memory_film --source-root "<fixture>" --out-dir "<out-root>\daily_kids" --json
```

## UTF-8 / No-Corruption

- Explicit final check result: `utf8_no_corruption=true`
- Bad text artifacts: `[]`
- Checked generated `.json` and `.md` smoke artifacts for UTF-8 decode, replacement characters, and `????` placeholder runs.

## Commands

- `C:\Users\user\miniconda3\python.exe -m unittest tests.test_graduation_film_blueprint_catalog`
  - Exit code: `1`
  - Purpose: red-first evidence.
- `C:\Users\user\miniconda3\python.exe -m unittest tests.test_graduation_film_blueprint_catalog`
  - Exit code: `0`
  - Result: `Ran 11 tests ... OK`
- `C:\Users\user\miniconda3\python.exe -m unittest tests.test_graduation_film_blueprint_catalog tests.test_soundtrack_arranger tests.test_pipeline_home`
  - Exit code: `0`
  - Result: `Ran 106 tests ... OK`
- `C:\Users\user\miniconda3\python.exe tools\film_canon_route.py --list --json`
  - Exit code: `0`
  - Result: listed `graduation_training_film` and `daily_kids_memory_film`.
- `C:\Users\user\miniconda3\python.exe tools\film_canon_route.py --film-type graduation_training_film --source-root ".tmp\film_canon_route_selector_20260707-005446\fixtures\graduation_source" --out-dir ".tmp\film_canon_route_selector_20260707-005446\graduation" --json`
  - Exit code: `0`
  - Result: wrote graduation-compatible dry-run artifacts.
- `C:\Users\user\miniconda3\python.exe tools\film_canon_route.py --film-type daily_kids_memory_film --source-root ".tmp\film_canon_route_selector_20260707-005446\fixtures\daily_kids_source" --out-dir ".tmp\film_canon_route_selector_20260707-005446\daily_kids" --json`
  - Exit code: `0`
  - Result: wrote daily kids fixture dry-run artifacts.
- `C:\Users\user\miniconda3\python.exe tools\film_canon_route.py --film-type unknown_product --source-root ... --out-dir ... --json`
  - Exit code: `2`
  - Result: fail-closed unsupported film type.
- `C:\Users\user\miniconda3\python.exe -c "... final explicit checks ..."`
  - Exit code: `0`
  - Result: printed supported film types, output roots, sections, modules, review packet paths, no-render/no-approval, and UTF-8 result.
- `C:\Users\user\miniconda3\python.exe -c "import json; json.load(open('docs/branch-contract-registry.json', encoding='utf-8')); print('json ok')"`
  - Exit code: `0`
  - Result: `json ok`

## No Render / No Approval

- Graduation smoke: `final.mp4=false`, `story_human_review_decision.json=false`
- Daily kids smoke: `final.mp4=false`, `story_human_review_decision.json=false`
- No render command was run.
- No human approval artifact was written.

## Deviations

- None.

## Stop-Loss

- Not stopped.
- No render, delivery gate semantics, VoxCPM, soundtrack provider, deliveries, Downloads, real family material, or existing `.tmp` run changes were required.

## Next Recommended Work

Add a human-facing product review decision artifact for `film-canon-product-route` so an operator can approve, revise, or reject the selected film type and story/catalog dry-run before any material mapping or render attempt.
