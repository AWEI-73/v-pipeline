# Work Order: Stage 2-to-10 dynamic input binding continuation

Date: 2026-07-17
Owner: integrator
Worker profile: LUNA high or equivalent bounded implementation worker
Starting HEAD: `31115e5598875f63799079281c430aa2c4008fd2`
Target state: `WAITING_INTEGRATOR_STAGE2_STAGE10_DYNAMIC_LINEAGE_REVIEW`

## 0. Outcome

Complete the existing Stage 2-to-10 technical lineage proof without replacing
its receipt engine or precomputing hashes for files that do not exist when the
execution companion is sealed.

The prior worker stop was correct. The original work order incorrectly said
all inputs and outputs must be frozen with exact hashes. That is valid for
static inputs, but impossible for outputs produced later in the same run.

This continuation must:

1. add one additive dependency-produced input binding to the current execution
   contract;
2. restore legacy delivery-gate compatibility for run directories outside the
   repository;
3. create a fresh immutable `forward_v3` proof from Stage 2 through Stage 10;
4. preserve `forward_v1`, `forward_v2`, their companions, receipts, reports,
   and all four existing commits unchanged.

## 1. Read First

Read completely:

1. `AGENTS.md`
2. `RUNBOOK.md`
3. `docs/decisions/2026-07-17-stage2-stage10-receipt-lineage.md`
4. `docs/decisions/2026-07-17-dependency-produced-input-binding.md`
5. `docs/construction-guides/work-orders/2026-07-17-stage2-stage10-forward-lineage-closure.md`
6. `.tmp/stage2_stage10_forward_lineage_closure/final/worker_report.md`
7. `docs/construction-guides/work-orders/2026-07-17-stage2-stage10-forward-lineage-closure.execution.json`
8. `video_pipeline_core/capability_execution.py`
9. `tools/write_delivery_gate_report.py`
10. the focused tests named below

Do not use probe renders to discover future output hashes. Do not edit the old
work order, old companions, or old run roots.

## 2. Confirmed Baseline

Treat these as evidence to recheck, not as unverified truth:

- S2, S3, and S5 in `forward_v2` have PASS receipts and correct parent receipt
  references.
- S6 was not launched because its static declared SHA for the S5-produced
  `edit_decision_plan.json` differed from the actual S5 receipt output hash.
- The same model defect would recur for `final.mp4` at S6-to-S7 and the verify
  bundle at S7-to-S8.
- Independent adjacent validation after `31115e55` ran 177 tests and returned
  exit 1 with 10 failures/errors. All ten are in
  `tests.test_delivery_gate_report` and arise because an external temp run root
  is passed into repository-only strict companion resolution.
- Full suite has not been run after these commits.

Record the exact pre-work HEAD and status. Preserve unrelated state.

## 3. Task A — Additive dynamic input contract

Use a tagged union in `steps[].inputs[]`:

- static: `{ "path": "...", "sha256": "..." }`
- dependency-produced: `{ "path": "...", "from_step_id": "S5.compile" }`

Rules:

1. Exactly one of `sha256` and `from_step_id` is allowed.
2. `from_step_id` must name a direct member of the consuming step's
   `depends_on` list.
3. The input path must appear verbatim in that producer step's
   `required_outputs`.
4. Before child launch, select the exact latest PASS parent receipt already
   used for `dependency_receipt_hashes`.
5. Require the path in the parent receipt's `output_hashes`.
6. Recompute the current file SHA and require equality with that parent output
   hash before reserving or launching the child.
7. Store the resolved digest in the child receipt's existing `input_hashes`.
8. Do not add a second lineage database or duplicate receipt graph.

Required specific error classes must distinguish at least:

- invalid contract binding;
- missing parent output hash;
- missing dynamic input file;
- current file differing from the parent receipt output hash.

Do not convert any required input to optional data.

### RED/GREEN acceptance for Task A

Add tests proving:

- legacy static input shape is unchanged;
- valid direct-parent dynamic input passes;
- both/neither binding modes fail schema validation;
- unknown, indirect, or non-dependency producer fails;
- producer path not present in `required_outputs` fails;
- child input hash equals the parent output hash;
- tampered produced file fails before child launch;
- missing or altered parent receipt protections remain intact.

## 4. Task B — Restore external delivery-gate compatibility

`tools/write_delivery_gate_report.py` historically accepts arbitrary run
directories, including system temp directories used by its public tests.

Strict companion discovery is meaningful only for a run root that is portable
inside this repository. Preserve strict behavior for in-repo runs, but do not
call repository-only path coercion for an external legacy run.

Required acceptance:

- all existing `tests.test_delivery_gate_report` tests pass;
- add or retain an explicit external-temp-root regression test;
- an in-repo strict run still requires and binds the current no-skip lineage
  closure;
- no broad exception swallowing and no fake PASS.

## 5. Task C — Fresh immutable companion and positive forward test

Create a new work-order execution companion for this continuation and a new
run root:

`.tmp/stage2_stage10_forward_lineage_closure/forward_v3`

The new companion must be committed before initialization. Reuse the existing
registered capability IDs and the committed fixture media. Do not modify or
reuse old receipts.

Required binding modes:

| Consumer | Input | Binding |
|---|---|---|
| S5.compile | `rough_cut_plan.json` | `from_step_id: S3.material-plan` |
| S5.compile | `timeline_build.json` | `from_step_id: S3.material-plan` |
| S6.render | `edit_decision_plan.json` | `from_step_id: S5.compile` |
| S7.verify | `final.mp4` | `from_step_id: S6.render` |
| S8.lineage-closure | `final_product_verify_bundle.json` | `from_step_id: S7.verify` |
| S10.delivery-gate | strict closure, trace, and no-skip decision artifacts | `from_step_id: S8.lineage-closure` |

All pre-existing fixture inputs remain static `{path, sha256}` entries.

Initialize exactly once and execute each step once in dependency order. A
successful positive proof must have PASS receipts from S2 through S10, with
every dynamic child input digest equal to the corresponding parent receipt
output digest.

## 6. Task D — Negative acceptance

Use copied/tamper fixtures. Never mutate the accepted positive run.

Prove all four fail closed with specific evidence:

1. changed Stage 2 accepted artifact;
2. replaced or modified Stage 5 parent receipt after Stage 6 ran;
3. missing strict closure at Stage 10;
4. changed S8 closure artifact or wrong closure binding before Stage 10.

Also prove a dynamic output file changed after its parent receipt was written
prevents the child process from launching.

## 7. Validation Order

Run focused tests first:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest `
  tests.test_capability_execution_contract `
  tests.test_capability_execution_receipts `
  tests.test_no_skip_execution_trace `
  tests.test_compile_edit_decision_plan `
  tests.test_edit_decision_renderer `
  tests.test_delivery_gate `
  tests.test_delivery_gate_report `
  tests.test_skill_tool_contracts `
  tests.test_dispatch_capabilities `
  tests.test_pipeline_skill_boundaries -v
```

Then run:

```powershell
C:\Users\user\miniconda3\python.exe tools\skill_tool_contract_audit.py --skills-dir skills --tools-dir tools --json
git diff --check
```

Only after the positive fixture, all negatives, focused tests, and audits are
green, run the full suite exactly once:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest discover -s tests
```

Timeout: 1,200,000 ms. Preserve stdout, stderr, exit code, duration, test count,
and skipped count. Do not immediately rerun a failed or timed-out full suite.

## 8. Evidence And Report

Write under:

`.tmp/stage2_stage10_forward_lineage_closure/forward_v3/final/`

Required:

- `worker_report.md`
- `command_log.json`
- `receipt_dag.json`
- `dynamic_input_binding_audit.json`
- `negative_fixture_matrix.json`
- focused and full-suite logs
- final exact git status

Every artifact must be UTF-8/JSON readable as applicable and hash-read back.
Report PASS/FAIL/UNKNOWN separately. Technical PASS is not creative approval or
delivery.

Final flags remain:

- `human_creative_approval=false`
- `final_delivery_claimed=false`

## 9. Stop-Loss

- One LOCAL correction per failure class. A repeated class is STRUCTURAL.
- Stop if the fix requires replacing the receipt engine, introducing a second
  orchestrator/lineage store, weakening static hashes, editing old immutable
  evidence, or making external legacy runs falsely strict.
- Do not chase dynamic hashes by pre-running S5/S6 and resealing a companion.
- Do not run the full suite before all bounded acceptance is green.

Legal success state:

`WAITING_INTEGRATOR_STAGE2_STAGE10_DYNAMIC_LINEAGE_REVIEW`
