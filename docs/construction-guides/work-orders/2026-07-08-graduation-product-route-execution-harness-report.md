[WORKER REPORT - REVIEW MODE]

## Summary

Implemented the thin Graduation Product Route Execution Harness and the missing
rendered product QA owner tool. The harness records
`pipeline_execution_trace.json`, calls or inspects existing owner tools/artifacts,
and stops at the first truthful route gate instead of inventing upstream
evidence.

The real-source no-render smoke stopped at `pipeline_home` with `UNKNOWN`
because the fresh run has no recognized routing artifact. This is a harness
honesty pass, not a delivery or render success.

## Files Changed

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

## Red-First Evidence

Command:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_graduation_product_route_runner tests.test_rendered_product_qa
```

Exit code: `1`

Expected failure:

- `ModuleNotFoundError: No module named 'video_pipeline_core.graduation_product_route_runner'`
- `ModuleNotFoundError: No module named 'video_pipeline_core.rendered_product_qa'`

## Interface Preflight

- `tools/pipeline_home.py --help`: exit `0`; supports `--run RUN --json`.
- `tools/film_canon_route.py --help`: exit `0`; supports `--list`, `--film-type`, `--source-root`, `--out-dir`, `--json`.
- `tools/film_canon_readiness.py --help`: exit `0`; supports `--film-type`, `--source-root`, `--out-dir`, `--decision`, `--reviewer`, `--decision-path`, `--json`.
- `tools/visual_selection_gate.py --help`: exit `0`; supports `--run`, `--out-dir`, `--json`.
- `tools/no_skip_execution_trace.py --help`: exit `0`; supports `--run`, `--out-dir`, `--json`.
- Registry note: `docs/branch-contract-registry.json` stores `branches` as a list keyed by `branch_id`, not a dict keyed by branch id.

No blocking CLI mismatch was found.

## Artifacts

Fresh smoke output root:

`C:\Users\user\Desktop\video_pipeline\.tmp\graduation_product_route_execution_harness_20260708-231212`

Created artifacts:

- `.tmp/graduation_product_route_execution_harness_20260708-231212/source_preflight.json`
- `.tmp/graduation_product_route_execution_harness_20260708-231212/pipeline_execution_trace.json`
- `.tmp/graduation_product_route_execution_harness_20260708-231212/graduation_product_route_harness_result.json`
- `.tmp/graduation_product_route_execution_harness_20260708-231212/final_artifact_check.json`

Source preflight:

- `exists=true`
- `is_dir=true`
- `file_count=306`

Smoke stop-loss:

- `stop_gate=pipeline_home`
- `stop_reason=UNKNOWN`
- internal `pipeline_home.py` exit code in trace: `2`
- harness CLI exit code: `0`

No rendered candidate existed in the fresh smoke, so `rendered_product_qa.py`
was not run in that smoke.

## Acceptance Commands

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_graduation_product_route_runner tests.test_rendered_product_qa tests.test_no_skip_execution_trace
```

Exit code: `0`; `Ran 13 tests ... OK`.

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_graduation_product_route_runner tests.test_rendered_product_qa tests.test_no_skip_execution_trace tests.test_graduation_film_blueprint_catalog tests.test_pipeline_home
```

Exit code: `0`; `Ran 115 tests ... OK`.

```powershell
C:\Users\user\miniconda3\python.exe tools\run_graduation_product_route.py --help
```

Exit code: `0`.

```powershell
C:\Users\user\miniconda3\python.exe tools\rendered_product_qa.py --help
```

Exit code: `0`.

```powershell
C:\Users\user\miniconda3\python.exe -c "import json; json.load(open('docs/branch-contract-registry.json', encoding='utf-8')); print('json ok')"
```

Exit code: `0`; output: `json ok`.

Final artifact check:

```powershell
C:\Users\user\miniconda3\python.exe -c "<artifact check script>"
```

Exit code: `0`; status: `ok`; trace entry count: `1`; UTF-8 check passed.

```powershell
git diff --check
```

Exit code: `0`; existing CRLF warnings only, no whitespace errors.

## Acceptance Result

PASS for harness implementation and no-render smoke honesty.

This is not a delivery pass and not a render pass. The smoke stopped before
route execution because the fresh run intentionally had no recognized pipeline
routing artifact.

## Blockers / Stop-Loss

- Real-route smoke blocker: `pipeline_home UNKNOWN`.
- The harness did not bypass this by creating route artifacts or copying stale
  evidence.
- No `story_human_review_decision.json` was written.

## Deviations

- The real-route smoke used a fresh empty run plus the real source root. It
  therefore validated source access and stop-loss behavior, not a completed
  graduation route continuation.
- The harness inspects existing route/readiness artifacts where the work order
  allowed `film_canon_route` or existing artifact checks. It does not generate
  product-route artifacts itself.

## Advisory Next Recommended Work

Run the harness against a fresh graduation route run that already contains
product-route review, readiness, shot-level proof, visual-selection gate,
effect handoff, and music/subtitle profile artifacts. That will exercise the
downstream stop gates beyond `pipeline_home` without changing this harness into
a pipeline generator.

## Paste-Back Manager Prompt

Treat this worker report as unverified evidence. Verify the changed files,
acceptance command outputs, smoke artifacts, and `pipeline_execution_trace.json`
before dispatching more work. Keep the product-level objective visible: the goal
is not merely to make the harness pass tests, but to prevent graduation render
rehearsals from skipping route evidence. Classify the current blocker
(`pipeline_home UNKNOWN` on the fresh smoke) as route-state missing evidence,
not as a delivery failure. Align the next dispatch with product-level
done-evidence: use a real route run with product-route approval, readiness,
shot proof, visual review, effect handoff, and music/subtitle evidence so the
harness can verify deeper stop gates.
