# Graduation Film Canon Blueprint Catalog Dry Run Report

Date: 2026-07-07

## Files Changed

- `video_pipeline_core/graduation_film_blueprint_catalog.py`
- `tools/graduation_film_blueprint_catalog.py`
- `tests/test_graduation_film_blueprint_catalog.py`
- `docs/video-pipeline-operating-map.md`
- `docs/pipeline-decision-tree.md`
- `docs/branch-contract-registry.md`
- `docs/branch-contract-registry.json`
- `docs/construction-guides/work-orders/2026-07-06-graduation-film-canon-blueprint-catalog-dry-run-report.md`

## Red-First Evidence

- Command: `C:\Users\user\miniconda3\python.exe -m unittest tests.test_graduation_film_blueprint_catalog`
- Exit code: `1`
- Result: failed with `ModuleNotFoundError: No module named 'video_pipeline_core.graduation_film_blueprint_catalog'`.

## Implemented Artifact Schemas

- `graduation_film_canon.json`
  - fixed section order: `opening_story`, `training_mv_catalog`, `supervisor_speech`, `teacher_class_intro`, `closing_story`
  - `training_mv_catalog` marked as the longest body section
  - training modules: `basic_training`, `advanced_training`, `certification`, `physical_activity`, `encouragement_activity`, `daily_life_optional`, `special_activity`
- `graduation_film_blueprint.json`
  - film type, theme, canon order, section purposes, training MV module order, and evidence requirements
- `story_shell.json`
  - title, theme, opening hook, closing payoff, and retargetable shell marker
- `training_catalog_map.json`
  - module assignments by source-relative file path
  - every agent-filled assignment has `authority=agent_filled` and `needs_human_confirmation=true`
- `story_retargeting_notes.json`
  - stable training catalog core and retargetable story shell / transition / ordering notes
- `graduation_dry_run_review_packet.md`
  - operator-facing dry-run review summary
- `graduation_dry_run_review_packet.json`
  - machine-readable review packet with `rendered=false` and `human_approval_written=false`

## Fixture Dry-Run

- Output root: `.tmp\graduation_film_blueprint_catalog_20260707-001839`
- Dry-run path: `.tmp\graduation_film_blueprint_catalog_20260707-001839\dry_run`

Canon sections:

- `opening_story`
- `training_mv_catalog`
- `supervisor_speech`
- `teacher_class_intro`
- `closing_story`

Blueprint / story shell:

- Blueprint theme: `discipline to confidence`
- Story shell title: `Fixture Graduation Dry Run`
- Story shell hook: `Fixture Graduation Dry Run: discipline to confidence`
- Story shell payoff: `把訓練累積轉成結訓後的前進感`

Training module counts:

- `basic_training`: 2
- `advanced_training`: 1
- `certification`: 1
- `physical_activity`: 1
- `encouragement_activity`: 1
- `daily_life_optional`: 1
- `special_activity`: 2

Agent-filled / human-confirmation counts:

- `agent_filled_count`: 9
- `needs_human_confirmation_count`: 9

No render / no approval:

- `final.mp4` exists: `false`
- `story_human_review_decision.json` exists: `false`

## UTF-8 / No-Corruption

- Command: `C:\Users\user\miniconda3\python.exe -c "..."`
- Exit code: `0`
- Result: `utf8 ok`
- Checked dry-run `.json` and `.md` artifacts for UTF-8 decode, replacement characters, and `????` placeholder runs.

## Commands

- `C:\Users\user\miniconda3\python.exe -m unittest tests.test_graduation_film_blueprint_catalog`
  - Exit code: `1`
  - Purpose: red-first evidence.
- `C:\Users\user\miniconda3\python.exe -m unittest tests.test_graduation_film_blueprint_catalog`
  - Exit code: `0`
  - Result: `Ran 4 tests ... OK`
- `C:\Users\user\miniconda3\python.exe -m unittest tests.test_graduation_film_blueprint_catalog`
  - Exit code: `0`
  - Result after refactor: `Ran 4 tests ... OK`
- `C:\Users\user\miniconda3\python.exe -m unittest tests.test_graduation_film_blueprint_catalog tests.test_soundtrack_arranger tests.test_pipeline_home`
  - Exit code: `0`
  - Result: `Ran 99 tests ... OK`
- `C:\Users\user\miniconda3\python.exe tools\graduation_film_blueprint_catalog.py --brief .tmp\graduation_film_blueprint_catalog_20260707-001839\brief.json --source-root .tmp\graduation_film_blueprint_catalog_20260707-001839\fixture_source --out-dir .tmp\graduation_film_blueprint_catalog_20260707-001839\dry_run --json`
  - Exit code: `0`
  - Result: wrote all required dry-run artifacts.
- `C:\Users\user\miniconda3\python.exe -c "import json; json.load(open('docs/branch-contract-registry.json', encoding='utf-8')); print('json ok')"`
  - Exit code: `0`
  - Result: `json ok`
- `git diff --check`
  - Exit code: `0`
  - Result: no whitespace errors; Git printed CRLF warnings for modified tracked docs.

## Optional Real-Source Smoke

- Not run.
- Reason: this round required fixture dry-run and the user explicitly limited the task to not touch Downloads.

## Deviations

- None.

## Stop-Loss

- Not stopped.
- No render, delivery gate semantics, VoxCPM, soundtrack provider, Downloads, deliveries, or existing `.tmp` run changes were required.

## Next Recommended Work

Run a human product review of `graduation_dry_run_review_packet.md` to confirm or revise the opening/closing story shell, module ordering/emphasis, and agent-filled training catalog assignments before any real-material production or render attempt.
