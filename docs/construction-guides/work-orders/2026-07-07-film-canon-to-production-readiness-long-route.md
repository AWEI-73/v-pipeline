# Work Order: Film Canon To Production Readiness Long Route

Date: 2026-07-07

## Goal

Extend the Film Canon Product Route from dry-run selection to pre-render
production readiness.

The visible capability to prove: after a film type is selected and a canon /
blueprint / story shell / catalog map dry-run exists, the pipeline can record a
product-route review decision, create a reviewed catalog, prepare story/material
planning and branch handoffs, and decide whether the route is ready for a
production worker.

Do not render a video in this round.

## Current Context

The working tree already contains these not-yet-integrated route layers:

- graduation canon / blueprint / catalog helper
- real-source graduation catalog + A/B story retarget dry-run
- film canon registry and product route selector

Build downward from those layers. Do not start a parallel implementation.

Read first:

- `docs/construction-guides/happy-paths/real-material-scripted-approved-happy-path.md`
- `docs/construction-guides/work-orders/2026-07-06-graduation-film-canon-blueprint-catalog-dry-run.md`
- `docs/construction-guides/work-orders/2026-07-07-graduation-film-real-source-catalog-retarget-dry-run.md`
- `docs/construction-guides/work-orders/2026-07-07-film-canon-registry-product-route-selector.md`

## Owner Zone

- `video_pipeline_core/film_canon_registry.py`
- `video_pipeline_core/graduation_film_blueprint_catalog.py`
- New product-readiness helper under `video_pipeline_core/` if needed
- `tools/film_canon_route.py`
- New product-readiness CLI under `tools/` if needed
- `tests/test_graduation_film_blueprint_catalog.py`
- New focused tests under `tests/` if needed
- `docs/video-pipeline-operating-map.md`
- `docs/pipeline-decision-tree.md`
- `docs/branch-contract-registry.md`
- `docs/branch-contract-registry.json`
- `docs/construction-guides/work-orders/2026-07-07-film-canon-to-production-readiness-long-route-report.md`

## Forbidden Zone

- Render pipeline implementation
- Delivery gate semantics
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

## Required Route Chain

Implement and verify this pre-render chain:

```text
film_canon_route dry-run
  -> product_route_review_decision
  -> reviewed_catalog_map
  -> story_material_planning_handoff
  -> opener_closer_design_handoff
  -> audio_subtitle_review_handoff
  -> production_readiness_gate
```

Minimum artifacts:

- `product_route_review_decision.json`
- `reviewed_catalog_map.json`
- `story_material_planning_handoff.json`
- `opener_closer_design_handoff.json`
- `audio_subtitle_review_handoff.json`
- `production_readiness_gate.json`
- `production_worker_handoff_prompt.md`
- `product_route_review_packet.md`
- `product_route_review_packet.json`

## Product Review Decision

Support decisions:

- `approved`
- `revision_requested`
- `rejected`

Rules:

- A production-ready route requires `decision=approved`.
- `approved` must name `reviewer=human` or `reviewer_type=human`.
- Non-human approval must not make the route production-ready.
- `revision_requested` and `rejected` must route to repair, not production.
- This is product-route approval, not final delivery approval.
- Do not write `story_human_review_decision.json`.

For tests/smoke, it is acceptable to create fixture human decisions inside new
`.tmp/` output roots. For the real graduation source, if no user approval exists
for this product route, produce a review recommendation and keep readiness
blocked or waiting as appropriate.

## Reviewed Catalog Map

Create a review layer over the catalog map.

Each assignment must become one of:

- `accepted`
- `rejected`
- `needs_reassign`
- `optional`
- `missing`

The reviewed catalog must preserve:

- original module id
- source-relative path
- agent-filled flag
- human review status
- review note or reason

Fixture tests may auto-approve known examples. Real-source graduation output
must expose unresolved items and not pretend user review happened.

## Handoffs

`story_material_planning_handoff.json` must state:

- selected film type
- selected story shell
- accepted/review-needed module groups
- story-to-material planning prerequisites
- retargeted sections
- next owner

`opener_closer_design_handoff.json` must state:

- opener and closer are story/design sections
- no plain white-card ending
- target duration ranges
- design intent
- Effect Factory return route

`audio_subtitle_review_handoff.json` must state:

- supervisor/source speech intelligibility required
- source speech subtitles required when speech is preserved
- MV music vs speech-section ducking policy
- teacher/class intro readability requirement
- audio/subtitle owner route

`production_readiness_gate.json` must state:

- `ready_for_production`: true/false
- blockers
- warnings
- next owner
- safe next command or worker prompt basis

## Required Dual-Route Smoke

Run both:

1. `graduation_training_film`
   - use the real source folder read-only:
     `C:\Users\user\Downloads\微電影素材\_整理後`
   - do not write into it
   - do not render
   - do not write final human delivery approval

2. `daily_kids_memory_film`
   - use fixture-only materials
   - prove the same review / handoff / readiness chain works

## Red-First Requirements

Before implementation, add failing tests proving:

- Product-route review decision artifact is missing or not consumed.
- Non-human approval does not make a route production-ready.
- Revision/rejected decisions route to repair.
- Reviewed catalog map is missing accepted/rejected/needs_reassign style status.
- Story/material, opener/closer, and audio/subtitle handoffs are missing.
- Production readiness gate is missing.
- No run writes `final.mp4` or `story_human_review_decision.json`.

## Acceptance Commands

Run and report exit codes:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_graduation_film_blueprint_catalog
C:\Users\user\miniconda3\python.exe -m unittest tests.test_graduation_film_blueprint_catalog tests.test_soundtrack_arranger tests.test_pipeline_home
C:\Users\user\miniconda3\python.exe tools\film_canon_route.py --list --json
C:\Users\user\miniconda3\python.exe <readiness-tool> --film-type graduation_training_film --source-root "C:\Users\user\Downloads\微電影素材\_整理後" --out-dir "<out-root>\graduation" --json
C:\Users\user\miniconda3\python.exe <readiness-tool> --film-type daily_kids_memory_film --source-root "<fixture>" --out-dir "<out-root>\daily_kids" --json
C:\Users\user\miniconda3\python.exe -c "import json; json.load(open('docs/branch-contract-registry.json', encoding='utf-8')); print('json ok')"
git diff --check
```

Also run final checks that print:

- output root
- per-film readiness status
- review decision state
- reviewed catalog status counts
- handoff file paths
- blockers/warnings
- next owner / safe next command
- `final.mp4` exists false
- `story_human_review_decision.json` exists false
- UTF-8/no-corruption result

## Stop-Loss

Stop and report without broad patching if:

- Implementing readiness requires render/gate/provider changes.
- Graduation route compatibility breaks.
- Real source cannot be read.
- The route must fake human approval to become ready.
- The route writes into Downloads, deliveries, or existing `.tmp` runs.
- Chinese output cannot be produced without mojibake.

## Delegated Decisions

- Exact helper/tool names.
- Exact schemas beyond required fields.
- How fixture human product-route approval is represented.
- Whether real graduation route ends `waiting_for_product_review` or
  `blocked_needs_catalog_review`, as long as it does not fake approval.
- Exact production handoff prompt format.

## Final Report Requirements

Write:

`docs/construction-guides/work-orders/2026-07-07-film-canon-to-production-readiness-long-route-report.md`

The report must include:

- Files changed
- Red-first evidence
- Implemented route chain
- Graduation real-source smoke summary
- Daily kids fixture smoke summary
- Product review decision behavior
- Reviewed catalog status counts
- Handoff summaries
- Production readiness gate summaries
- Confirmation that no render or final human delivery approval was written
- UTF-8/no-corruption result
- Commands and exit codes
- Deviations, if any
- Stop-loss reason, if stopped
- Next recommended work grounded only in this round

