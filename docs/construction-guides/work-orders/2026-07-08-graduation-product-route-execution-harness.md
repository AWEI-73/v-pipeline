# Graduation Product Route Execution Harness

Date: 2026-07-08
Status: ready for worker

## Goal

Build a thin graduation product route execution harness that makes the existing
runbook, decision tree, branch registry, and no-skip trace contract executable
for the graduation rehearsal path.

This is not a new pipeline and not a state-machine rewrite. The harness should
call existing tools, record stage execution evidence, stop at real gates, and
prevent workers from jumping straight to a rendered rehearsal without proving
the route stages that led there.

## Background Source

Current repo facts to preserve:

- `tools/pipeline_home.py` already derives run state, cursor, and next action
  from artifacts.
- `docs/pipeline-decision-tree.md` already defines the Graduation Film Product
  Route.
- `docs/branch-contract-registry.json` already defines branch ownership and
  next action contracts.
- `tools/no_skip_execution_trace.py` already audits rendered rehearsal/preview
  candidates for copied or missing gate evidence.
- `tools/rendered_product_qa.py` is currently missing and must be added as the
  product-facing rendered output QA owner tool.

## Owner Zone

The worker may edit only:

- `tools/run_graduation_product_route.py`
- `tools/rendered_product_qa.py`
- `video_pipeline_core/graduation_product_route_runner.py`
- `video_pipeline_core/rendered_product_qa.py`
- `tests/test_graduation_product_route_runner.py`
- `tests/test_rendered_product_qa.py`
- `docs/video-pipeline-operating-map.md`
- `docs/pipeline-decision-tree.md`
- `docs/branch-contract-registry.md`
- `docs/branch-contract-registry.json`
- `docs/construction-guides/work-orders/2026-07-08-graduation-product-route-execution-harness-report.md`
- `.tmp/graduation_product_route_execution_harness_*`

## Forbidden Zone

Read-only, even if they look relevant:

- `tools/pipeline_home.py`
- `tools/film_canon_route.py`
- `tools/film_canon_readiness.py`
- `tools/write_product_route_review_decision.py`
- `tools/visual_selection_gate.py`
- `tools/write_visual_selection_review.py`
- `tools/no_skip_execution_trace.py`
- `tools/write_delivery_gate_report.py`
- `video_pipeline_core/delivery_gate.py`
- `video_pipeline_core/film_canon_registry.py`
- `video_pipeline_core/film_canon_production_readiness.py`
- `video_pipeline_core/no_skip_execution_trace.py`
- `Downloads/`
- `deliveries/`
- existing `.tmp/` runs not created by this work order
- `.env`, `.venv*`, reference repos, provider runtimes

## Required Pieces

1. Interface preflight
   - Inspect the exact CLI behavior of `pipeline_home.py`,
     `film_canon_route.py`, `film_canon_readiness.py`,
     `visual_selection_gate.py`, and `no_skip_execution_trace.py`.
   - Inspect the graduation route section in
     `docs/pipeline-decision-tree.md`.
   - Inspect `docs/branch-contract-registry.json` for
     `film-canon-product-route` and `verify-delivery`.
   - Record any mismatch in the report before implementation.

2. Red-first verification
   - Add focused tests that fail because
     `tools/run_graduation_product_route.py` and
     `tools/rendered_product_qa.py` do not exist yet.
   - Add tests for stop-loss behavior: the harness must stop at
     `WAITING`, `REPAIR`, `UNKNOWN`, human review required, missing rendered
     product QA, or missing no-skip trace evidence.
   - Add tests that copied/stale gate artifacts cannot satisfy the harness.

3. Thin route harness
   - Add `tools/run_graduation_product_route.py`.
   - Support at least:
     - `--run RUN_DIR`
     - `--source-root SOURCE_ROOT`
     - `--mode no-render`
     - `--mode render-rehearsal`
     - `--out-dir OUT_DIR`
     - `--json`
   - The harness must call or inspect existing tools rather than duplicating
     their business logic.
   - It must write `pipeline_execution_trace.json` with one record per real
     stage it ran or inspected. Each record must include stage id, owner tool
     or artifact, inputs, outputs, command when applicable, exit code when
     applicable, status, and stop reason when applicable.
   - It must write a route decision artifact such as
     `graduation_product_route_harness_result.json`.

4. Locked rehearsal path
   - First version locks this order:
     - `pipeline_home` preflight
     - `film_canon_route` or existing route artifact check
     - `film_canon_readiness`
     - `product_route_review_decision` check
     - `shot_level_material_proof` check
     - `visual_selection_gate`
     - `effect_handoff` check
     - music/subtitle profile check
     - compose/render handoff check
     - `rendered_product_qa` when a rendered rehearsal exists
     - `no_skip_execution_trace`
   - If an upstream stage is absent, the harness must stop with a truthful
     stop gate instead of inventing or copying artifacts.

5. Rendered product QA owner tool
   - Add `tools/rendered_product_qa.py` and core helper.
   - It should inspect rendered rehearsal/final candidates with executable
     evidence: file existence, ffprobe stream/duration, sampled frames or
     contact sheet evidence, subtitle/title/effect readability evidence when
     artifacts exist, and explicit missing-evidence blockers when they do not.
   - It must not declare creative approval, legal/music approval, or human
     story approval.

6. No-skip integration
   - When `--mode render-rehearsal` reaches a rendered candidate, run
     `rendered_product_qa.py` before `no_skip_execution_trace.py`.
   - `no_skip_execution_trace` must be able to see tool-generated rendered
     product QA evidence and the current `pipeline_execution_trace.json`.
   - Copied or unknown gate artifacts must remain blocking.

7. Real-route smoke
   - Run `--mode no-render` against the current real graduation/source-root
     context using a fresh `.tmp/graduation_product_route_execution_harness_*`
     output root.
   - If the route reaches a real stop gate, report it as pass for harness
     honesty, not as delivery success.
   - Do not edit existing prior V-runs or Downloads.

## Acceptance Commands

Use only:

```powershell
C:\Users\user\miniconda3\python.exe
```

No bare `python` and no `pytest`.

Required commands:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_graduation_product_route_runner tests.test_rendered_product_qa tests.test_no_skip_execution_trace
```

Expected exit code: `0`.

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_graduation_product_route_runner tests.test_rendered_product_qa tests.test_no_skip_execution_trace tests.test_graduation_film_blueprint_catalog tests.test_pipeline_home
```

Expected exit code: `0`.

```powershell
C:\Users\user\miniconda3\python.exe tools\run_graduation_product_route.py --help
C:\Users\user\miniconda3\python.exe tools\rendered_product_qa.py --help
```

Expected exit code: `0` for both.

```powershell
C:\Users\user\miniconda3\python.exe -c "import json; json.load(open('docs/branch-contract-registry.json', encoding='utf-8')); print('json ok')"
```

Expected exit code: `0`.

```powershell
git diff --check
```

Expected exit code: `0`; existing CRLF warnings may be reported, but no new
whitespace errors.

Also run a final artifact check with
`C:\Users\user\miniconda3\python.exe` that verifies:

- `pipeline_execution_trace.json` exists in the fresh smoke output.
- every harness stage has status, owner, and evidence fields.
- `graduation_product_route_harness_result.json` exists.
- if any rendered candidate exists, `rendered_product_qa.json` exists before
  `no_skip_contract_decision.json`.
- no `story_human_review_decision.json` is written by the harness.
- generated JSON/Markdown decode as UTF-8 and contain no `\ufffd` or suspicious
  repeated `????`.

## Stop-Loss Limits

Stop and report, do not bypass, when:

- `pipeline_home.py` returns `UNKNOWN`, `WAITING`, or `REPAIR`.
- product-route review is missing, rejected, or revision requested.
- shot-level material proof is missing or thin for a required render-facing
  beat.
- visual selection is missing, rejected, needs repick, token-only, or copied.
- effect handoff is missing or not review-accepted when the route needs
  designed opener/closer/title/effect.
- music/subtitle profile is missing required evidence for the selected mode.
- rendered product QA is missing or fails.
- no-skip trace finds copied, stale, unknown, or missing owner evidence.
- human story review or transcript review is still required.

Stop-loss is a valid harness outcome. It is not a delivery pass.

## Delegated Decisions

- Exact internal trace schema field names may follow repo style if all
  acceptance checks can read them.
- The harness may use subprocess calls or direct Python helper calls, but it
  must record which path was used.
- The first smoke fixture shape may be minimal if it proves stop-loss and
  no-skip behavior without touching prior runs.
- The rendered product QA sampling cadence may be conservative; it must produce
  frame/contact-sheet evidence when a video candidate exists.

## Final Report Requirements

Write:

`docs/construction-guides/work-orders/2026-07-08-graduation-product-route-execution-harness-report.md`

The report must include:

- `[WORKER REPORT - REVIEW MODE]` at the start.
- Summary.
- Files changed.
- Artifacts created or updated.
- Commands / exit codes.
- Acceptance results.
- Real-route smoke output root.
- Stop-loss outcome, if any.
- Deviations.
- Next recommended work, advisory only.
- Paste-back manager prompt telling the manager to treat the report as
  unverified evidence, verify claims, keep the product-level objective visible,
  classify blockers, and align the next step with product-level done-evidence
  before dispatching more work.
