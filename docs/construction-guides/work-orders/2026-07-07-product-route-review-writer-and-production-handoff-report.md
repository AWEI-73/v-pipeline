# Product Route Review Writer And Production Handoff Report

Date: 2026-07-07

## Files Changed

- `video_pipeline_core/film_canon_production_readiness.py`
- `video_pipeline_core/product_route_review_decision.py`
- `tools/film_canon_readiness.py`
- `tools/write_product_route_review_decision.py`
- `tests/test_graduation_film_blueprint_catalog.py`
- `docs/video-pipeline-operating-map.md`
- `docs/pipeline-decision-tree.md`
- `docs/branch-contract-registry.md`
- `docs/branch-contract-registry.json`
- `docs/construction-guides/work-orders/2026-07-07-product-route-review-writer-and-production-handoff-report.md`

## Red-First Evidence

- Command: `C:\Users\user\miniconda3\python.exe -m unittest tests.test_graduation_film_blueprint_catalog`
- Exit code: `1`
- Failure points:
  - `tools\write_product_route_review_decision.py` missing: Python could not open the file.
  - `build_product_route_review_decision()` did not accept `approve_all_reviewed`.
  - `production_worker_handoff_prompt.md` missed required basis fields such as selected story shell and reviewed status summary.

## Implemented Behavior

- Added `tools\write_product_route_review_decision.py`.
- Added fail-closed writer helper in `video_pipeline_core.product_route_review_decision`.
- `approved` requires `--reviewer human` and `--approve-all-reviewed`.
- `revision_requested` / `rejected` require `--note` or explicit module reason.
- Path-like `--out-name` fails closed.
- Module overrides support `accepted`, `optional`, `needs_reassign`, and `rejected`.
- `tools\film_canon_readiness.py` now accepts `--decision-path`.
- Readiness can consume a written `product_route_review_decision.json`.
- `pending_review` remains distinct from `missing`.
- Optional missing modules remain visible in `reviewed_catalog_map.json` and can clear production readiness.
- Product-route approval remains separate from final story/delivery approval.

## CLI Examples

Approved:

```powershell
C:\Users\user\miniconda3\python.exe tools\write_product_route_review_decision.py --run RUN --decision approved --reviewer human --approve-all-reviewed --module-status "certification=optional:no certification match in this source pass" --json
```

Revision requested:

```powershell
C:\Users\user\miniconda3\python.exe tools\write_product_route_review_decision.py --run RUN --decision revision_requested --reviewer human --note "revise catalog module mapping" --json
```

Rejected:

```powershell
C:\Users\user\miniconda3\python.exe tools\write_product_route_review_decision.py --run RUN --decision rejected --reviewer human --module-status "basic_training=rejected:wrong source material for this route" --json
```

Regenerate readiness from a written decision:

```powershell
C:\Users\user\miniconda3\python.exe tools\film_canon_readiness.py --film-type graduation_training_film --source-root SOURCE --out-dir OUT --decision-path RUN\product_route_review_decision.json --json
```

## Real Graduation Source Smoke

- Output root: `.tmp\product_route_review_writer_20260707-061959`
- Source root: `C:\Users\user\Downloads\微電影素材\_整理後`
- Source preflight: `exists=True`, `is_dir=True`, `file_count=306`, `media_count=198`

Initial readiness:

- Run: `.tmp\product_route_review_writer_20260707-061959\graduation_initial`
- `ready_for_production=false`
- `next_owner=waiting_product_review`
- blockers: `product_route_review_required`
- warnings: `catalog_has_missing_modules`
- status counts: `accepted=0`, `optional=0`, `missing=2`, `pending_review=222`

Writer result:

- Artifact: `.tmp\product_route_review_writer_20260707-061959\graduation_initial\product_route_review_decision.json`
- Decision: `approved`
- Reviewer: `human`
- `approve_all_reviewed=true`
- `is_final_delivery_approval=false`
- `clears_story_human_review=false`
- Module overrides:
  - `certification=optional`
  - `encouragement_activity=optional`

Regenerated readiness:

- Run: `.tmp\product_route_review_writer_20260707-061959\graduation_approved`
- `ready_for_production=true`
- `next_owner=production_worker`
- blockers: `[]`
- warnings: `[]`
- status counts: `accepted=222`, `optional=2`, `missing=0`, `pending_review=0`
- Handoff prompt: `.tmp\product_route_review_writer_20260707-061959\graduation_approved\production_worker_handoff_prompt.md`

## Daily Kids Fixture Smoke

- Fixture root: `.tmp\product_route_review_writer_20260707-061959\fixtures\daily_kids_source`
- Run: `.tmp\product_route_review_writer_20260707-061959\daily_kids_approved`
- `ready_for_production=true`
- `next_owner=production_worker`
- blockers: `[]`
- warnings: `[]`
- status counts: `accepted=8`, `optional=0`, `missing=0`, `pending_review=0`
- Handoff prompt: `.tmp\product_route_review_writer_20260707-061959\daily_kids_approved\production_worker_handoff_prompt.md`

## Handoff Prompt Field Check

Generated prompts include:

- film type
- selected story shell
- reviewed module status summary
- opener/closer design requirements
- training MV music policy
- source speech/subtitle/readability requirements
- no-render precondition reminder when readiness is false

## Final Artifact Check

- Exit code: `0`
- Output root: `.tmp\product_route_review_writer_20260707-061959`
- Writer artifact path: `.tmp\product_route_review_writer_20260707-061959\graduation_initial\product_route_review_decision.json`
- UTF-8/no-corruption: `true`
- Bad text artifacts: `[]`
- `final.mp4` exists: `false` for all smoke runs
- `story_human_review_decision.json` exists: `false` for all smoke runs

## Commands

- `C:\Users\user\miniconda3\python.exe -m unittest tests.test_graduation_film_blueprint_catalog`
  - Exit code: `1`
  - Purpose: red-first evidence.
- `C:\Users\user\miniconda3\python.exe -m unittest tests.test_graduation_film_blueprint_catalog`
  - Exit code: `0`
  - Result: `Ran 18 tests ... OK`
- `C:\Users\user\miniconda3\python.exe -m unittest tests.test_graduation_film_blueprint_catalog tests.test_soundtrack_arranger tests.test_pipeline_home tests.test_delivery_gate tests.test_delivery_gate_report tests.test_final_product_verify`
  - Exit code: `0`
  - Result: `Ran 191 tests ... OK`
- `C:\Users\user\miniconda3\python.exe tools\film_canon_route.py --list --json`
  - Exit code: `0`
  - Result: listed `graduation_training_film` and `daily_kids_memory_film`.
- `C:\Users\user\miniconda3\python.exe -c "... source preflight ..."`
  - Exit code: `0`
  - Result: `exists=True`, `is_dir=True`, `file_count=306`, `media_count=198`.
- `C:\Users\user\miniconda3\python.exe tools\film_canon_readiness.py --film-type graduation_training_film --source-root "C:\Users\user\Downloads\微電影素材\_整理後" --out-dir ".tmp\product_route_review_writer_20260707-061959\graduation_initial" --json`
  - Exit code: `0`
  - Result: initial route not ready, `pending_review=222`, `missing=2`.
- `C:\Users\user\miniconda3\python.exe tools\write_product_route_review_decision.py --run ".tmp\product_route_review_writer_20260707-061959\graduation_initial" --decision approved --reviewer human --approve-all-reviewed --module-status "certification=optional:no certification match in this source pass" --module-status "encouragement_activity=optional:no encouragement match in this source pass" --json`
  - Exit code: `0`
  - Result: wrote product-route decision with two optional module overrides.
- `C:\Users\user\miniconda3\python.exe tools\film_canon_readiness.py --film-type graduation_training_film --source-root "C:\Users\user\Downloads\微電影素材\_整理後" --out-dir ".tmp\product_route_review_writer_20260707-061959\graduation_approved" --decision-path ".tmp\product_route_review_writer_20260707-061959\graduation_initial\product_route_review_decision.json" --json`
  - Exit code: `0`
  - Result: route ready for production worker, `accepted=222`, `optional=2`.
- `C:\Users\user\miniconda3\python.exe tools\film_canon_readiness.py --film-type daily_kids_memory_film --source-root ".tmp\product_route_review_writer_20260707-061959\fixtures\daily_kids_source" --out-dir ".tmp\product_route_review_writer_20260707-061959\daily_kids_approved" --json`
  - Exit code: `0`
  - Result: fixture route ready for production worker, `accepted=8`.
- `C:\Users\user\miniconda3\python.exe tools\write_product_route_review_decision.py --help`
  - Exit code: `0`
  - Result: help lists `--approve-all-reviewed`, `--module-status`, `--note`, `--out-name`, and `--json`.
- `C:\Users\user\miniconda3\python.exe -c "import json; json.load(open('docs/branch-contract-registry.json', encoding='utf-8')); print('json ok')"`
  - Exit code: `0`
  - Result: `json ok`.
- `git diff --check`
  - Exit code: `0`
  - Result: no whitespace errors; Git printed CRLF replacement warnings for edited text files.
- Final artifact check command
  - Exit code: `0`
  - Result: printed output root, writer artifact, readiness states, status counts, module overrides, handoff prompts, blockers/warnings, no-render/no-story-approval, and UTF-8 result.

## No Render / No Final Approval

- No render command was run.
- No provider, soundtrack, delivery gate, or final story approval semantics were changed.
- No `final.mp4` was produced.
- No `story_human_review_decision.json` was written.
- Product-route approval is only a pre-render product-route readiness decision.

## Deviations / Blockers

- Deviations: none.
- Blockers: none.
- Note: the graduation smoke used fixture-style human approval inside the fresh `.tmp` smoke folder, as allowed by the work order. It is not user final delivery approval.

## Next Recommended Work

Use `.tmp\product_route_review_writer_20260707-061959\graduation_approved\production_worker_handoff_prompt.md` as the basis for the next real graduation production worker round. That round should start production from the approved product-route handoff, still preserve source speech and music legality evidence, and still require final story/delivery human review after any rendered candidate.
