# Graduation Route Harness Deeper Integration Proof

Date: 2026-07-08
Status: ready for worker

## Goal

Prove the new graduation product route harness can execute beyond the empty-run
`pipeline_home UNKNOWN` stop gate and can verify deeper route stages without
skipping evidence.

This round is an integration proof for the existing harness, not a new wrapper
design and not a delivery/render quality round.

## Background Source

The prior harness work produced:

- `tools/run_graduation_product_route.py`
- `tools/rendered_product_qa.py`
- `video_pipeline_core/graduation_product_route_runner.py`
- `video_pipeline_core/rendered_product_qa.py`
- `.tmp/graduation_product_route_execution_harness_20260708-231212`

That smoke correctly stopped at `pipeline_home UNKNOWN`, but it only proved
truthful stop-loss on an empty run. This round must exercise the harness against
route artifacts deep enough to prove stage ordering, rendered QA ordering, and
no-skip evidence behavior.

## Owner Zone

The worker may edit only:

- `docs/construction-guides/work-orders/2026-07-08-graduation-route-harness-deeper-integration-proof-report.md`
- `.tmp/graduation_route_harness_deeper_integration_proof_*`

If and only if the deeper integration proof exposes a harness bug, the worker
may also edit:

- `tools/run_graduation_product_route.py`
- `tools/rendered_product_qa.py`
- `video_pipeline_core/graduation_product_route_runner.py`
- `video_pipeline_core/rendered_product_qa.py`
- `tests/test_graduation_product_route_runner.py`
- `tests/test_rendered_product_qa.py`

## Forbidden Zone

Read-only:

- `tools/pipeline_home.py`
- `tools/film_canon_route.py`
- `tools/film_canon_readiness.py`
- `tools/write_product_route_review_decision.py`
- `tools/visual_selection_gate.py`
- `tools/write_visual_selection_review.py`
- `tools/no_skip_execution_trace.py`
- `tools/write_delivery_gate_report.py`
- `video_pipeline_core/delivery_gate.py`
- `video_pipeline_core/no_skip_execution_trace.py`
- `docs/branch-contract-registry.json` unless a verified wrapper bug requires
  registry wording only
- `Downloads/`
- `deliveries/`
- existing `.tmp/` runs
- `.env`, `.venv*`, reference repos, provider runtimes

## Required Pieces

1. Prior-result verification
   - Read the prior harness report and smoke artifacts.
   - Verify the prior smoke only reached `pipeline_home`.
   - Record this as the starting gap.

2. Candidate source selection
   - Search read-only prior `.tmp` outputs for a graduation route folder with
     product-route artifacts such as `product_route_review_decision.json`,
     `production_readiness_gate.json`, `reviewed_catalog_map.json`, or handoff
     packets.
   - Prefer `.tmp/product_route_review_writer_20260707-061959/graduation_approved`
     if it still exists and passes read-only inspection.
   - If no adequate prior route folder exists, create a fresh minimal fixture
     under this round's `.tmp` output root.
   - Do not modify the selected prior folder.

3. No-render deeper harness proof
   - Create a fresh proof run folder under
     `.tmp/graduation_route_harness_deeper_integration_proof_*`.
   - Copy or synthesize only the minimal artifacts needed to let the harness
     pass product-route decision/readiness and then stop at the next real
     missing stage.
   - Run `tools/run_graduation_product_route.py --mode no-render`.
   - Required result: `pipeline_execution_trace.json` must contain more than
     one stage and must prove the harness got past `pipeline_home`.
   - If it stops, the stop gate must be truthful and supported by trace
     evidence.

4. Render-rehearsal ordering proof
   - Create a separate fresh fixture/run under this round's `.tmp` output root.
   - Include the minimal route artifacts needed to reach a rendered candidate
     check.
   - Use a tiny valid local MP4 fixture generated inside the output root, not a
     copied prior final, unless the work order acceptance cannot be met without
     a prior file. If a prior file is used, hardlink/copy into the fresh output
     root and record why.
   - Run `tools/run_graduation_product_route.py --mode render-rehearsal`.
   - Required result: `rendered_product_qa` appears in
     `pipeline_execution_trace.json` before `no_skip_execution_trace`, or the
     harness truthfully stops at `rendered_product_qa` with executable evidence.

5. No-skip behavior proof
   - Demonstrate that copied/stale/unknown gate evidence remains blocking.
   - Demonstrate that tool-generated rendered product QA is visible to the
     no-skip audit path when the fixture reaches that stage.
   - If current no-skip semantics block the fixture for a valid reason, record
     the exact rule and do not relax it.

6. Bug repair only if needed
   - If the proof exposes a harness bug, write focused failing test evidence
     first, fix only the harness/QA owner files, then rerun the focused tests.
   - Do not change existing branch tools or delivery gate semantics.

## Acceptance Commands

Use only:

```powershell
C:\Users\user\miniconda3\python.exe
```

No bare `python` and no `pytest`.

Required:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_graduation_product_route_runner tests.test_rendered_product_qa tests.test_no_skip_execution_trace
```

Expected exit code: `0`.

If any harness/QA code is changed, also run:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_graduation_product_route_runner tests.test_rendered_product_qa tests.test_no_skip_execution_trace tests.test_graduation_film_blueprint_catalog tests.test_pipeline_home
```

Expected exit code: `0`.

Run both harness CLI proofs:

```powershell
C:\Users\user\miniconda3\python.exe tools\run_graduation_product_route.py --run PROOF_RUN --source-root "C:\Users\user\Downloads\微電影素材\_整理後" --mode no-render --out-dir PROOF_OUT --json
C:\Users\user\miniconda3\python.exe tools\run_graduation_product_route.py --run RENDER_FIXTURE_RUN --source-root "C:\Users\user\Downloads\微電影素材\_整理後" --mode render-rehearsal --out-dir RENDER_OUT --json
```

Expected exit code: `0` for the harness command itself. Truth is in the JSON
result and trace, not the process exit code.

Run:

```powershell
git diff --check
```

Expected exit code: `0`; existing CRLF warnings may appear, but no new
whitespace errors.

Final artifact check with `C:\Users\user\miniconda3\python.exe` must verify:

- no-render proof trace exists and has more than one stage.
- no-render proof got past `pipeline_home`.
- render-rehearsal proof trace exists.
- if both `rendered_product_qa` and `no_skip_execution_trace` appear, rendered
  QA appears first.
- if render-rehearsal stops before no-skip, the stop gate is explicit and has
  evidence.
- no `story_human_review_decision.json` was written.
- existing prior `.tmp` runs were not modified.
- generated JSON/Markdown decode as UTF-8 and contain no `\ufffd` or suspicious
  repeated `????`.

## Stop-Loss Limits

Stop and report rather than bypass when:

- no adequate prior route artifacts exist and a minimal fixture cannot be built
  without inventing business semantics;
- the harness stops at a truthful missing gate;
- rendered QA fails on a valid media/probe/frame-evidence reason;
- no-skip blocks copied/stale/unknown evidence;
- fixing the issue would require modifying forbidden branch tools, delivery
  gate, or prior runs.

## Delegated Decisions

- The worker may choose the minimal fixture shape if it exercises the required
  stage ordering and stop-loss behavior.
- The worker may choose the tiny MP4 generation method if it stays inside the
  output root and is documented.
- If prior artifacts have variant field names, the worker may adapt the fixture
  copy layer, but must not mutate prior runs.

## Final Report Requirements

Write:

`docs/construction-guides/work-orders/2026-07-08-graduation-route-harness-deeper-integration-proof-report.md`

The report and chat final output must start with:

`[WORKER REPORT - REVIEW MODE]`

Include:

- Summary.
- Files changed.
- Artifacts created or updated.
- Commands / exit codes.
- Acceptance results.
- No-render proof root and trace depth.
- Render-rehearsal proof root and stage ordering.
- Blockers / stop-loss.
- Deviations.
- Next recommended work, advisory only.
- A section titled `Final output prompt` that the user can copy back to the
  manager thread. It must tell the manager to treat the report as unverified
  evidence, verify claims, keep the product-level objective visible, classify
  blockers, and align the next step with product-level done-evidence before
  dispatching more work.
