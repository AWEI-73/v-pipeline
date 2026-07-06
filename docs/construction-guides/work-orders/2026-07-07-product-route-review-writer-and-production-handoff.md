# Work Order: Product Route Review Writer And Production Handoff

Date: 2026-07-07

## Goal

Add the operator-facing product-route review writer and use it to move the
graduation film route from `pending_review` to a truthful production-readiness
handoff when a human approves or explicitly repairs the route.

Visible capability to prove: after `tools/film_canon_readiness.py` creates a
pre-render product-route packet, an operator can run one command to write
`product_route_review_decision.json`, regenerate readiness, and produce a
production worker handoff prompt that a later worker can use to start the real
graduation film production path.

Do not render a video in this round.

## Current Context

The current `master` has:

- `tools/film_canon_route.py`
- `tools/film_canon_readiness.py`
- `video_pipeline_core/film_canon_registry.py`
- `video_pipeline_core/film_canon_production_readiness.py`
- `video_pipeline_core/graduation_film_blueprint_catalog.py`
- `docs/construction-guides/happy-paths/real-material-scripted-approved-happy-path.md`
- `docs/construction-guides/work-orders/2026-07-07-film-canon-to-production-readiness-long-route-report.md`

The integrator correction already separates:

- `pending_review`: material assignment exists but needs human product-route review
- `missing`: module has no material assignment

Do not collapse these two statuses.

## Owner Zone

- `video_pipeline_core/film_canon_production_readiness.py`
- New helper under `video_pipeline_core/` if needed for product-route review writing
- `tools/film_canon_readiness.py`
- New CLI under `tools/` for product-route review decisions
- `tests/test_graduation_film_blueprint_catalog.py`
- New focused test under `tests/` if needed
- `docs/video-pipeline-operating-map.md`
- `docs/pipeline-decision-tree.md`
- `docs/branch-contract-registry.md`
- `docs/branch-contract-registry.json`
- `docs/construction-guides/work-orders/2026-07-07-product-route-review-writer-and-production-handoff-report.md`

## Forbidden Zone

- Render pipeline implementation
- Delivery gate semantics
- Story final approval writer semantics
- `tools/write_story_human_review_decision.py`, except read-only reference
- VoxCPM / voiceover provider implementation
- Soundtrack provider/download implementation
- Existing approved delivery package under `deliveries/`
- Existing `.tmp/` runs
- `Downloads/` writes
- `.env`
- `.venv_voxcpm/`
- `reference repo/`
- Git commit, branch, push, or PR operations

## Required Interpreter

Use this interpreter for every Python command:

`C:\Users\user\miniconda3\python.exe`

Do not use bare `python`, `pytest`, or another environment.

## Piece 1: Product Route Review Decision Writer

Add an operator-facing CLI, suggested name:

`tools/write_product_route_review_decision.py`

The CLI must write `product_route_review_decision.json` into a run/readiness
folder and fail closed on invalid inputs.

Required behavior:

- Supports `approved`, `revision_requested`, and `rejected`.
- Requires `--reviewer human`.
- Does not write `story_human_review_decision.json`.
- Writes UTF-8 JSON with no replacement characters or repeated `????`.
- Output path must stay run-local; path-like `--out-name` values must fail.
- `approved` can be broad approval only if the operator explicitly asks for it
  with a flag such as `--approve-all-reviewed` or equivalent.
- Supports per-module overrides for real graduation gaps:
  - mark a module `accepted`
  - mark a module `optional`
  - mark a module `needs_reassign`
  - mark a module `rejected`
- `revision_requested` and `rejected` require a note or explicit module reason.

The CLI may read existing route/readiness artifacts from the folder to learn
available module IDs and missing modules.

## Piece 2: Regenerate Readiness From Existing Decision

Extend the readiness path so it can consume an existing
`product_route_review_decision.json` from the target output folder, or accept an
explicit decision path.

Required behavior:

- Human approved decisions can make `production_readiness_gate.ready_for_production=true`.
- Non-human approved decisions remain blocked.
- `revision_requested` and `rejected` route to `repair_product_route`.
- Module-level `optional` for a missing module can clear the missing warning for
  production readiness, but it must remain visible in the reviewed catalog.
- Module-level `needs_reassign` or `rejected` must keep readiness false.
- Product-route approval is not final delivery approval and must not clear
  story/delivery human approval.
- `production_worker_handoff_prompt.md` must include:
  - film type
  - selected story shell A/B or chosen shell
  - reviewed module status summary
  - opener/closer design requirements
  - training MV music policy
  - source speech/subtitle/readability requirements
  - explicit no-render-precondition reminder if readiness is false

## Piece 3: Real Graduation Source Smoke

Use the real source folder read-only:

`C:\Users\user\Downloads\微電影素材\_整理後`

Run a fresh `.tmp/` smoke that proves:

1. Initial readiness is not production-ready and has `pending_review`.
2. The writer can create a human product-route decision.
3. Regenerated readiness consumes that decision.
4. The route either:
   - becomes production-ready with explicit human-approved optional/accepted
     handling for missing graduation modules, or
   - stays repair-blocked with exact `needs_reassign` reasons.
5. `production_worker_handoff_prompt.md` exists and cites the reviewed catalog,
   story/material handoff, opener/closer handoff, and audio/subtitle handoff.

For this smoke only, fixture-style human approval is allowed inside the fresh
`.tmp/` folder to prove the command path. Do not claim it is the user's final
delivery approval.

## Piece 4: Daily Kids Fixture Smoke

Run the same writer/readiness chain on a fixture-only
`daily_kids_memory_film` source tree.

Prove the route works for another product type and does not hard-code
graduation-only assumptions.

## Red-First Requirements

Before implementation, add failing tests or focused smoke evidence proving:

- The writer CLI does not exist or cannot write a product-route decision.
- Non-human reviewer must fail closed.
- Partial/ambiguous approved decision must fail closed.
- Path-like output names must fail closed.
- Existing readiness cannot yet consume a written decision artifact.
- Pending review is not counted as missing material.
- Optional missing module handling is not yet represented.
- The handoff prompt is missing required production-worker basis fields.

## Acceptance Commands

Run and report exit codes:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_graduation_film_blueprint_catalog
C:\Users\user\miniconda3\python.exe -m unittest tests.test_graduation_film_blueprint_catalog tests.test_soundtrack_arranger tests.test_pipeline_home tests.test_delivery_gate tests.test_delivery_gate_report tests.test_final_product_verify
C:\Users\user\miniconda3\python.exe tools\film_canon_route.py --list --json
C:\Users\user\miniconda3\python.exe tools\film_canon_readiness.py --film-type graduation_training_film --source-root "C:\Users\user\Downloads\微電影素材\_整理後" --out-dir "<out-root>\graduation_initial" --json
C:\Users\user\miniconda3\python.exe tools\write_product_route_review_decision.py --run "<out-root>\graduation_initial" --decision approved --reviewer human <module flags> --json
C:\Users\user\miniconda3\python.exe tools\film_canon_readiness.py --film-type graduation_training_film --source-root "C:\Users\user\Downloads\微電影素材\_整理後" --out-dir "<out-root>\graduation_approved" --decision-path "<out-root>\graduation_initial\product_route_review_decision.json" --json
C:\Users\user\miniconda3\python.exe tools\film_canon_readiness.py --film-type daily_kids_memory_film --source-root "<fixture>" --out-dir "<out-root>\daily_kids_approved" --json
C:\Users\user\miniconda3\python.exe -c "import json; json.load(open('docs/branch-contract-registry.json', encoding='utf-8')); print('json ok')"
git diff --check
```

Also run a final artifact check that prints:

- output root
- writer artifact path
- per-film readiness status
- reviewed catalog status counts, including `pending_review` and `missing`
- module override summary
- handoff prompt path
- blockers/warnings
- `final.mp4` exists false
- `story_human_review_decision.json` exists false
- UTF-8/no-corruption result

## Stop-Loss

Stop and report without broad patching if:

- Readiness approval requires render/gate/provider changes.
- The route must fake final story/delivery human approval.
- Real source cannot be read.
- Optional/needs_reassign module semantics conflict with existing gate design.
- The command would write into Downloads, deliveries, or existing `.tmp` runs.
- Chinese artifacts cannot be written without mojibake.

## Delegated Decisions

- Exact CLI flag names for module overrides.
- Exact JSON schema for module review details beyond required behavior.
- Whether the graduation smoke marks `certification` and
  `encouragement_activity` optional or `needs_reassign`; choose the path that
  best proves fail-closed behavior and record it.
- Whether readiness consumes decisions by `--decision-path`, run-local default,
  or both.
- Exact wording of the production worker handoff prompt.
- Whether to keep tests in the existing graduation test file or split a new
  focused test file.

## Final Report Requirements

Write:

`docs/construction-guides/work-orders/2026-07-07-product-route-review-writer-and-production-handoff-report.md`

The report must include:

- Files changed
- Red-first evidence with command, exit code, and failure point
- CLI examples for approved, revision_requested, and rejected
- Real graduation source smoke output root
- Daily kids smoke output root
- Initial and regenerated readiness states
- Module override summary
- Handoff prompt path and required field check
- All acceptance commands with exit codes
- Explicit confirmation that no render/final approval/provider/download work ran
- Deviations / blockers
- Next recommended work grounded in this run

