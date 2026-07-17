# Decision: Bind dynamic step inputs through parent receipts

Date: 2026-07-17
Status: accepted
Scope: accountable capability execution contracts and Stage 2-to-10 lineage
Superpowers phase: review

## SPEC

Requirement:

An immutable execution companion must support both inputs that already exist
when the contract is sealed and inputs that will be produced by an earlier
step in the same accountable run.

Why:

The first Stage 2-to-10 forward test correctly linked child receipts to parent
receipt hashes, but incorrectly pre-sealed the future SHA-256 of Stage 5 output
`edit_decision_plan.json` as a static Stage 6 input. The same failure class
would recur at Stage 6-to-7 and Stage 7-to-8. Rebuilding the companion after a
probe render only chases run-local output hashes and is not durable lineage.

Direction:

- Keep `{path, sha256}` for external or pre-existing static inputs.
- Add `{path, from_step_id}` for a file produced by a declared direct
  dependency.
- At child launch, resolve the exact parent PASS receipt, read the declared
  path from its `output_hashes`, recompute the current file hash, and require
  equality before the child process starts.
- The child receipt keeps the resolved digest in `input_hashes` and the exact
  parent receipt path/hash in `dependency_receipt_hashes`. No second lineage
  store is introduced.

Non-goals:

- No optional-input escape hatch.
- No mutable receipt, companion, or run repair.
- No new orchestrator, renderer engine, route runner, or delivery authority.
- No behavior change for legacy runs without a committed strict companion.

## DO

Files / modules:

- `video_pipeline_core/capability_execution.py`
- `tests/test_capability_execution_contract.py`
- `tests/test_capability_execution_receipts.py`
- `tools/write_delivery_gate_report.py`
- `tests/test_delivery_gate_report.py`
- a new immutable Stage 2-to-10 execution companion and run root

Function-level plan:

- Extend step-input validation to accept exactly one binding mode:
  `sha256` or `from_step_id`.
- Validate that `from_step_id` is a direct dependency and that the input path
  appears in that producer step's `required_outputs`.
- Resolve dependency-produced inputs from the exact parent receipt already
  selected for the child run, then verify file existence and hash equality.
- Preserve arbitrary external run-directory support in the legacy delivery
  gate. Strict companion discovery applies only to repository-portable run
  roots.

Data / interface changes:

`steps[].inputs[]` becomes a tagged union:

```json
{"path": "inputs/source.json", "sha256": "<64 lowercase hex>"}
```

or:

```json
{"path": ".tmp/run/edit_decision_plan.json", "from_step_id": "S5.compile"}
```

Both fields together, neither field, a non-dependency producer, or a path not
declared by the producer are contract errors.

Migration / compatibility:

Existing `{path, sha256}` contracts and receipts retain their behavior. The
failed `forward_v1` and `forward_v2` artifacts remain immutable historical
evidence. The corrected proof uses a new work order companion and `forward_v3`
run root.

## VERIFY

Pre-checks:

- Preserve commits `dd780150`, `a1a2feaf`, `a2f9a657`, and `31115e55`.
- Preserve all existing failed companions, receipts, and worker reports.
- Confirm the independent adjacent test baseline currently fails in
  `tests.test_delivery_gate_report` because an external temp run is passed to
  strict repository-path resolution.

Tests:

- Static input hash behavior remains unchanged.
- Dynamic input schema accepts the valid direct-parent form and rejects
  both/neither fields, indirect or unknown producers, and undeclared outputs.
- Child execution records the parent's output digest as its input digest.
- Missing, tampered, or substituted parent output fails before child launch.
- Existing delivery-gate report tests pass for external temp run roots.
- Strict in-repo delivery binding still requires current lineage closure.
- A fresh 2-to-4-second Stage 2-to-10 fixture completes its full receipt DAG,
  four negative checks, focused suite, audits, and one final full suite.

Manual checks:

- Read the final receipt DAG and verify each dynamic child input digest equals
  the corresponding parent receipt `output_hashes` entry.
- Confirm no probe-generated dynamic SHA appears in the new companion.

Regression risks:

- Treating an arbitrary older ancestor as the producer.
- Trusting the receipt hash without recomputing the current output file.
- Breaking legacy delivery-gate runs outside the repository.
- Quietly weakening strict runs when a dynamic input cannot be resolved.

## Decision Notes

Accepted because:

The repeated mismatch is a contract-model error, not a renderer or fixture
error. Parent receipts already own the exact output hashes; reusing them is the
smallest extension and preserves the existing single-source lineage design.

Tradeoffs:

The execution-contract schema becomes slightly richer, but avoids pre-render
hash probing, companion churn, and duplicated lineage state.

Open questions:

None for this bounded closure. Transitive producer references remain
unsupported until a real use case requires them.

## Git / Retrieval

Related files:

- `docs/construction-guides/work-orders/2026-07-17-stage2-stage10-forward-lineage-closure.md`
- `.tmp/stage2_stage10_forward_lineage_closure/final/worker_report.md`
- `video_pipeline_core/capability_execution.py`
- `tools/write_delivery_gate_report.py`

Related commits:

- `dd780150`
- `a1a2feaf`
- `a2f9a657`
- `31115e55`

Graphify anchors:

- `run_capability_step`
- `_validate_dependency_receipts`
- `_hash_inputs`
- `resolve_strict_contract`
- `write_delivery_gate_report`

Search tags:

`decision-log`, `stage2-stage10`, `dynamic-input`, `dependency-output`,
`accountability-receipt`, `forward-lineage`
