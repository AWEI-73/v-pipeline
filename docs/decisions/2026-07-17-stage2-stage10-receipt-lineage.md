# Decision: Carry Stage 2 truth to Stage 10 through existing receipts

Date: 2026-07-17
Status: accepted
Scope: Stage 2 ambiguity gate, accountable capability execution, Verify, and Delivery
Superpowers phase: plan

## SPEC

Requirement:

Make a Stage 10 delivery decision mechanically traceable to the accepted Stage 2
ambiguity package without copying the full story payload into every downstream
artifact.

Why:

The Stage 0–2 package is now hash-bound and fail-closed, while the existing
Stage 3–10 factory has its own mature gates. The missing link is forward
lineage: current capability execution verifies that a parent step passed, but a
child receipt does not preserve the exact parent receipt hash. A later audit
therefore cannot prove which accepted upstream revision produced the candidate.

Direction:

- Reuse `capability_execution`, accountability receipts,
  `no_skip_execution_trace`, and the delivery gate.
- Add exact dependency receipt hashes to child receipts.
- Make strict no-skip closure validate the dependency chain recursively.
- In strict runs, make Stage 10 expose and require the validated lineage closure.
- Add only thin public adapters/capability cards where an existing compiler or
  renderer has no accountable public surface.

Non-goals:

- No new lineage engine, orchestrator, Stage, canonical truth store, or creative
  gate.
- No Canon 67 render, story rewrite, owner verdict, upload, or delivery claim.
- No copying full Stage 2 prose through every Stage.
- No behavior change for legacy runs without a committed strict execution
  companion.

## DO

Files / modules:

- `video_pipeline_core/capability_execution.py`: record exact dependency receipt
  paths and hashes in each child receipt.
- `video_pipeline_core/no_skip_execution_trace.py`: validate and surface the
  recursive receipt chain.
- `video_pipeline_core/delivery_gate.py` and
  `tools/write_delivery_gate_report.py`: bind strict lineage closure into Stage
  10 while preserving legacy behavior.
- `tools/compile_edit_decision_plan.py` and the existing
  `video_pipeline_core/edit_decision_renderer.py`: expose existing Stage 5/6
  behavior through registered capability surfaces; add only a thin renderer
  CLI if required.
- Existing owner Skills: register missing public compiler/render/lineage
  capabilities without changing Stage ownership.

Function-level plan:

1. Capture the latest PASS receipt for every declared `depends_on` step before a
   child command starts.
2. Store `depends_on_step_ids` and `dependency_receipt_hashes` in the immutable
   child receipt.
3. Recompute and compare those hashes during strict closure; missing, stale, or
   substituted parents fail closed.
4. Surface the valid root-to-leaf chain in existing trace/closure artifacts.
5. Require the closure only when a committed execution companion activates
   strict mode; otherwise retain the current delivery behavior.

Data / interface changes:

- Additive fields in accountability receipt version 1:
  `depends_on_step_ids` and `dependency_receipt_hashes`.
- Additive lineage summary/reference fields in existing no-skip and delivery
  reports. No new top-level canonical artifact family.

Migration / compatibility:

- New strict contracts require the new dependency fields.
- Legacy runs without strict accountability remain compatible.
- Old immutable receipts are never rewritten or treated as new-chain evidence.

## VERIFY

Pre-checks:

- Confirm the current public capability IDs for Stage 2, 3, 5, 6, 7, and 10.
- Confirm the worktree and frozen Canon 67 evidence remain untouched.

Tests:

- Child receipt records exact parent receipt hashes.
- Missing, failed, stale, or tampered parent receipt fails closed.
- Strict trace reconstructs one unbroken Stage 2→10 fixture chain.
- Strict Stage 10 binds to the closure path/hash.
- Legacy non-strict delivery behavior remains unchanged.
- Focused accountability, route, Verify, and delivery suites pass.
- Full suite runs once after all focused checks are green.

Manual checks:

- Read the final fixture receipt graph and confirm each edge uses the preceding
  receipt hash rather than filenames or prose claims.
- Confirm technical gate PASS does not set human creative approval or claim
  delivery.

Regression risks:

- Accidentally making strict lineage mandatory for legacy runs.
- Recording the latest filename instead of the exact parent receipt hash used by
  the child.
- Adding a second renderer instead of a thin adapter to the existing renderer.
- Treating a complete chain as proof of story quality.

## Decision Notes

Accepted because:

This closes the cross-Stage evidence gap with machinery already present in the
repo. Hash-linked receipts preserve provenance while downstream artifacts stay
compact.

Tradeoffs:

Strict runs become less tolerant of manual artifact replacement. That is
intentional; human revisions must create a new receipt/delta rather than mutate
history.

Open questions:

- Which existing public render command is the smallest true-shape Stage 6
  surface is a Task 0 audit question. If no existing renderer can be exposed by
  a thin adapter, construction must stop rather than create a new engine.

## Git / Retrieval

Related files:

- `docs/decisions/2026-07-17-progressive-editorial-ambiguity-loop.md`
- `video_pipeline_core/capability_execution.py`
- `video_pipeline_core/no_skip_execution_trace.py`
- `video_pipeline_core/delivery_gate.py`
- `docs/construction-guides/work-orders/2026-07-17-stage2-stage10-forward-lineage-closure.md`

Related commits:

- `65179c77` — progressive editorial ambiguity gate

Graphify anchors:

- `run_capability_step`
- `_validate_dependency_receipts`
- `_strict_tool_entries`
- `evaluate_complete_video_delivery`

Search tags:

decision-log, stage2-stage10, forward-lineage, accountability-receipt,
no-skip, delivery-gate, compact-to-next-level
