# Work Order: Stage 2 To Stage 10 Forward Receipt Lineage Closure

Date: 2026-07-17
Owner: main-pipeline integrator
Worker profile: bounded implementation worker; intended for a fresh Luna
high-reasoning session selected by the operator
Final success state: `WAITING_INTEGRATOR_STAGE2_STAGE10_LINEAGE_REVIEW`

## Goal And Construction Sources

Close the one remaining mechanical gap between the new Stage 2 ambiguity
package and the existing Stage 3–10 factory. A strict Stage 10 gate must be able
to trace its candidate through exact parent receipt hashes back to the accepted
Stage 2 gate. Reuse the existing accountability and no-skip machinery; do not
create a second lineage system.

Read in order:

1. `AGENTS.md`
2. `RUNBOOK.md`
3. `docs/decisions/2026-07-17-progressive-editorial-ambiguity-loop.md`
4. `docs/decisions/2026-07-17-stage2-stage10-receipt-lineage.md`
5. `skills/editorial-ambiguity-loop.md`
6. `skills/video-pipeline-route.md`
7. `skills/editor.md`
8. `skills/verify.md`
9. `video_pipeline_core/capability_execution.py`
10. `video_pipeline_core/no_skip_execution_trace.py`
11. `video_pipeline_core/edit_decision_renderer.py`
12. `video_pipeline_core/delivery_gate.py`
13. `docs/construction-guides/work-orders/2026-07-13-single-entry-forward-accountability-long-task.md`
14. `docs/construction-guides/work-orders/2026-07-13-single-entry-forward-accountability-acceptance.execution.json`

The previous accountability work is a reusable foundation, not a migration
target. Do not rewrite or reuse its immutable run artifacts as fresh evidence.

## Product Boundary

The chain proves execution provenance only:

```text
Stage 2 ambiguity gate receipt
  -> Stage 3 material/retrieval receipt
  -> Stage 5 compile receipt
  -> Stage 6 render receipt
  -> Stage 7 verify receipt
  -> no-skip closure receipt
  -> Stage 10 delivery-gate receipt
```

It does not prove story quality, material adequacy, taste, human approval, or
delivery authorization.

## Owner Zone

The worker may edit only these production surfaces when a failing test requires
the change:

- `video_pipeline_core/capability_execution.py`
- `video_pipeline_core/no_skip_execution_trace.py`
- `video_pipeline_core/delivery_gate.py`
- `tools/no_skip_execution_trace.py`
- `tools/write_delivery_gate_report.py`
- `tools/compile_edit_decision_plan.py`
- `tools/render_edit_decision.py` (new thin adapter only, if Task 0 confirms no
  registered public adapter already exists)
- `skills/editor.md`
- `skills/verify.md`
- `skills/video-pipeline-route.md` only for existing route references; do not
  move Stage ownership
- `tests/test_capability_execution_contract.py`
- `tests/test_no_skip_execution_trace.py`
- `tests/test_delivery_gate.py`
- `tests/test_delivery_gate_report.py`
- `tests/test_compile_edit_decision_plan.py`
- `tests/test_edit_decision_renderer.py`
- `tests/test_skill_tool_contracts.py`
- `tests/test_dispatch_capabilities.py`
- `tests/fixtures/stage2_stage10_lineage_v1/**` (new bounded fixture)
- `docs/construction-guides/work-orders/2026-07-17-stage2-stage10-forward-lineage-closure.execution.json` (new, created and committed only after its paths/hashes are final)
- `.tmp/stage2_stage10_forward_lineage_closure/**`

The work order and both decision logs are read-only construction sources.

## Forbidden / Read-Only Zone

- `.tmp/canon67_editorial_reconstruction_v2/**`
- all Canon 67 source media, candidate videos, accepted state, subtitles, and
  owner verdicts
- `HANDOFF_CURRENT.md`
- `RUNBOOK.md`
- `docs/branch-contract-registry.json`
- `docs/interface-contracts/pipeline-product-artifact-dictionary.json`
- `video_pipeline_core/global_editorial_state.py`
- Material Map selection/ranking semantics
- effect, audio, subtitle, CapCut, Workbench, and reference-repo code
- git history before this work order, remote branches, Drive, and external
  services

Do not set `human_creative_approval=true` or
`final_delivery_claimed=true`. Do not upload, push, reset, clean, or rewrite old
receipts.

## Pinned Architecture Decisions

1. Use existing execution contracts and receipts. Do not add
   `stage_lineage.json`, a lineage database, another orchestrator, or a second
   truth store.
2. Each child receipt records the exact receipt path and SHA-256 for every
   declared `depends_on` step. A filename or step ID alone is insufficient.
3. Strict closure recomputes parent receipt hashes and compares them with the
   child receipt. It must catch post-run parent replacement.
4. New strict runs fail closed when dependency hashes are missing. Legacy runs
   without a committed execution companion retain existing behavior.
5. Stage 6 must call the existing
   `video_pipeline_core.edit_decision_renderer.render_edit_decision`. A new CLI
   may only load validated JSON, build the mechanical timeline view from the
   accepted edit decision, and call that function. It may not implement another
   renderer or reinterpret selection/story/text/audio.
6. Capability cards belong to existing owners:
   - Stage 5 compile and Stage 6 render: `skills/editor.md`;
   - no-skip lineage closure and Stage 10 gate: `skills/verify.md`.
7. A delivery gate may be technically PASS while both approval flags remain
   false. No artifact or report may call that a delivered film.

## Task 0 — Baseline And Public-Surface Audit

Before editing production code:

1. Record branch, HEAD, `git status --short`, Python path, and ffmpeg/ffprobe
   availability.
2. Query the live capability catalog for Stage 2 ambiguity, material rough cut,
   Stage 5 compile, Stage 6 render, final-product verify, no-skip trace, and
   delivery gate.
3. Identify the exact existing public command for each Stage. Save:

   `.tmp/stage2_stage10_forward_lineage_closure/audit/public_surface_audit.json`

4. Confirm the current facts:
   - Stage 2, Stage 3, Stage 7, and Stage 10 have registered capability cards;
   - `run_capability_step` verifies dependency PASS but does not record exact
     dependency receipt hashes;
   - strict tool trace does not currently validate those child-to-parent hashes;
   - any missing Stage 5/6 card can be supplied by the existing compiler or a
     thin adapter to the existing renderer.

If Stage 5 or Stage 6 requires a new render engine, new canonical schema, or
Stage-owner move, classify `STRUCTURAL_PUBLIC_SURFACE_GAP` and stop before Task
1. A missing capability card or thin CLI is not structural.

## Task 1 — Red-First Receipt Dependency Tests

Add failing tests before production changes. Capture the RED command and exit
code under the run root.

Required RED cases:

1. A child receipt must contain:
   - `depends_on_step_ids` in contract order;
   - `dependency_receipt_hashes` mapping each parent step to exact receipt path
     and SHA-256.
2. Missing or non-PASS parent still prevents child execution.
3. Replacing/tampering a parent receipt after the child ran makes strict closure
   fail with a specific dependency hash mismatch code.
4. A child receipt with a missing dependency field in a new strict run fails
   closed.
5. A legacy non-strict run remains accepted by its current behavior.

Do not weaken existing copied/stale receipt protections.

## Task 2 — Capture Exact Parent Receipts

Implement the smallest additive change in
`video_pipeline_core/capability_execution.py`:

1. Resolve each declared dependency to the exact latest PASS receipt before
   reserving/running the child.
2. Return both sorted validation errors and immutable dependency refs.
3. Write the refs into the child receipt as additive version-1 fields.
4. Keep current `input_hashes`, `output_hashes`, attempt reservation, declared
   output, and retry semantics unchanged.

Run the Task 1 focused tests to GREEN before continuing.

## Task 3 — Validate And Surface The Receipt DAG

Extend existing strict no-skip behavior, not its authority:

1. Strict tool entries expose `depends_on_step_ids` and
   `dependency_receipt_hashes`.
2. Closure verifies every declared edge against the actual parent receipt.
3. Missing, substituted, stale, wrong-run, wrong-contract, or hash-drifted
   parents fail closed with stable error codes.
4. The existing `pipeline_execution_trace.json` and
   `no_skip_contract_decision.json` gain an additive lineage summary containing
   root step, leaf step, ordered step IDs, and closure status.
5. Contract dependency cycles or unreachable leaf steps are rejected; do not
   silently sort them into a plausible order.
6. Old immutable traces are never rewritten.

Required negative fixture: execute a valid child, copy the run, tamper only the
parent receipt, and prove the fresh strict audit exits 1. The untouched run must
still exit 0.

## Task 4 — Public Stage 5/6 Capability Surfaces

Use existing implementations:

1. Register `tools/compile_edit_decision_plan.py` as the Stage 5 compiler under
   `skills/editor.md` if no equivalent live card exists.
2. If no public Stage 6 edit-decision adapter exists, add
   `tools/render_edit_decision.py` as a thin CLI over
   `render_edit_decision(...)` and register it under `skills/editor.md`.
3. The adapter inputs must be explicit JSON paths and an output run directory.
   It must preserve accepted source paths/hashes and return nonzero on invalid
   or unsupported composition.
4. Register `tools/no_skip_execution_trace.py` under `skills/verify.md` if no
   equivalent live card exists.
5. Run skill index, capability dispatch, tool ownership, and direct-tool argv
   binding tests. All new Python tools must have one canonical owner.

No new renderer core, selector, or route runner is authorized.

## Task 5 — Strict Stage 10 Binding

For a run activated by a committed strict execution companion:

1. `tools/write_delivery_gate_report.py` resolves the applicable contract using
   the existing strict resolver.
2. It requires a current PASS `no_skip_contract_decision.json` and matching
   `pipeline_execution_trace.json`.
3. `delivery_gate.json` includes an additive `lineage_closure` object with the
   closure path/hash, trace path/hash, root step, leaf step, and status.
4. Missing/stale/failed lineage blocks strict Stage 10 with a stable repair
   action.
5. Runs without a committed strict companion follow existing delivery behavior
   byte-for-byte where practical and semantically unchanged in all cases.

Do not make story quality or human approval machine-PASS requirements.

## Task 6 — Committed True-Shape Execution Companion

Create a tiny deterministic fixture under
`tests/fixtures/stage2_stage10_lineage_v1/`. It may use a 2–4 second ffmpeg
color/sine source materialized once before sealing; record its SHA-256 in the
companion. Do not use Canon 67 media.

Create the companion only after all paths, commands, and fixture hashes are
final:

`docs/construction-guides/work-orders/2026-07-17-stage2-stage10-forward-lineage-closure.execution.json`

The committed contract must use registered capability IDs and include at least:

| Step | Required role |
|---|---|
| `S2.ambiguity-gate` | validate the three hash-bound upstream artifacts |
| `S3.material-plan` | produce evidence-backed rough-cut/material plan |
| `S5.compile` | compile accepted picture/audio/effect/text handoffs |
| `S6.render` | render the tiny candidate through the existing renderer |
| `S7.verify` | produce final-product verification evidence |
| `S8.lineage-closure` | produce current strict trace/closure |
| `S10.delivery-gate` | write the technical delivery gate with lineage binding |

Each step depends on the preceding relevant receipts; S5 may additionally
depend on bounded audio/effect/text fixture steps if required. Inputs and
outputs must be frozen with exact hashes/paths. The companion and work order
must be committed before `capability-run --initialize`.

Execute initialization once, then each step once in dependency order. Do not
repair a sealed receipt in place. If one fixture command is wrong, preserve the
failed run, create a new immutable run root/companion revision, and stay within
the retry/stop-loss limits below.

## Task 7 — Forward And Tamper Acceptance

Positive acceptance must prove:

- all expected receipts exist and are PASS;
- every child receipt carries exact parent receipt refs/hashes;
- the candidate is playable and Verify passes;
- strict no-skip closure reports one connected root-to-leaf chain;
- Stage 10 contains matching lineage closure refs;
- `human_creative_approval=false`;
- `final_delivery_claimed=false`.

Negative acceptance must use copied fixture roots and prove nonzero exits for:

1. changed Stage 2 gate artifact;
2. replaced Stage 5 receipt after Stage 6 ran;
3. missing strict closure at Stage 10;
4. wrong closure hash in Stage 10 input.

Never modify the positive run to create negative evidence.

## Task 8 — Validation And Final Report

Run focused/adjacent tests first:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest `
  tests.test_capability_execution_contract `
  tests.test_no_skip_execution_trace `
  tests.test_compile_edit_decision_plan `
  tests.test_edit_decision_renderer `
  tests.test_delivery_gate `
  tests.test_delivery_gate_report `
  tests.test_skill_tool_contracts `
  tests.test_dispatch_capabilities `
  tests.test_pipeline_skill_boundaries -v
```

Expected: exit 0.

Then run:

```powershell
C:\Users\user\miniconda3\python.exe tools\skill_tool_contract_audit.py --skills-dir skills --tools-dir tools --json
git diff --check
```

Expected: both exit 0; no orphan, duplicate owner, broken command, or whitespace
errors.

Run the full suite exactly once, only after the positive/negative fixture and
all focused checks are green:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest discover -s tests
```

Timeout: 1,200,000 ms. Expected: exit 0. If it times out or fails, preserve the
log and stop; do not immediately rerun the full suite.

Write:

`.tmp/stage2_stage10_forward_lineage_closure/final/worker_report.md`

The report must include:

- pre/post branch, HEAD, exact git status;
- commits and diff stats;
- public-surface audit and capability IDs;
- RED/GREEN commands and exit codes;
- positive receipt graph with every receipt path/hash;
- negative fixture error codes;
- delivery lineage closure path/hash;
- focused, audit, diff, and full-suite results;
- deviations, skipped work, blind spots, and all stop-loss events;
- exact approval flags.

## Acceptance

The worker may report
`WAITING_INTEGRATOR_STAGE2_STAGE10_LINEAGE_REVIEW` only if:

1. receipt dependency capture is additive and tested;
2. strict closure catches post-run parent substitution;
3. Stage 5/6 use registered existing implementations;
4. strict Stage 10 binds to the exact no-skip closure;
5. positive and all four negative fixture checks match expected results;
6. focused tests, audits, `git diff --check`, and the one full-suite run pass;
7. the worktree contains only authorized changes;
8. both approval flags remain false.

Technical PASS is not creative approval or delivery.

## Stop-Loss

- One LOCAL correction per failure class. A repeated class is STRUCTURAL; stop
  at the last green commit.
- Stop on owner-zone conflict, required schema replacement, new renderer engine,
  Stage-owner migration, legacy delivery regression, or need to mutate old
  receipts.
- Do not relax a failing test, drop a dependency edge, convert a required input
  into optional data, or manually fabricate a receipt/closure.
- Do not run the full suite before Task 8 and do not run it twice.
- If the committed companion cannot express the true public commands, stop and
  report the exact capability/argv mismatch instead of using private shell
  shortcuts.

## Worker Authority

The worker may decide reversible fixture details such as colors, duration
within 2–4 seconds, stable IDs, and file placement inside the allowed fixture
root. The worker may not decide creative approval, delivery, Stage ownership,
new canonical schemas, or architecture expansion.
