# 2026-06-22 Integrated E2E Review Action Plan

## Classification

- Source inputs:
  - `2026-06-22-gemini-antigravity-runner-feedback.md`
  - `2026-06-22-claude-pexels-retrieval-feedback.md`
- Scope: E2E route correctness, runner orchestration, review gates, material truth.
- Status: active construction review, ready to split into implementation tasks.

This document integrates the generated-material run and the Pexels/stock
retrieval run. It is the current working review for deciding what to fix next.

## Executive Conclusion

The pipeline skeleton is sound: route state is artifact-driven, runs are
resumable, and gates are explicit enough for agents to stop and hand off. The
main failures are not missing output. They are cases where the pipeline produces
a video while the state machine, quality gates, or user-facing correctness checks
quietly disagree.

The biggest category is silent green failure:

- target duration can be ignored;
- subtitles can match script but be unreadable on screen;
- semantic/VLM alignment can fail but disappear before final QA;
- generated material can fail quality review and still be accepted;
- duplicate generated images can count as full material coverage;
- a render can pass but the canonical state can remain incomplete.

The second category is runner lifecycle:

- long-lived monolithic subagents accumulate context and burn tokens;
- long render jobs can become orphaned when owned by a short-lived subagent;
- rerun commands can keep circling the same node/action/artifact state.

## Route-Specific Findings

### Generated / Material-Map Route

Evidence: `fairy-tale-short\runs\20260622-085316-baseline`

Observed:

- `final.mp4` exists and `verify_result.json` passes.
- `material_delta.json` reports `ready_for_build: true`.
- `material_map_lifecycle.json` reports `can_build: true`.
- `state.json` / dashboard still report `next_action: await_material`.
- `material_coverage_map.json` still contains gaps.
- `generated_material_quality_review.json` reports `pass: false`.
- `generated_material_review.json` accepts all 60 generated items.
- Generated images contain large exact duplicate groups and shared prompt
  prefixes.

Assessment:

- This route has a material truth precedence bug.
- It also has a generated material quality/duplicate acceptance bug.
- The system counts accepted quantity too readily as usable coverage.

### Pexels / Stock-First Route

Evidence: `city-dawn-doc\runs\20260622-094200-run-auto`

Observed:

- `final.mp4` exists and final QA passes.
- Retrieval avoids the generated-image duplication failure mode.
- Stock-first sidesteps the `material_delta` vs `material_coverage_map`
  contradiction because coverage is optional on that route.
- Target length was not enforced against the brief.
- On-screen subtitle truncation did not affect `subtitle_accuracy`.
- VLM content-alignment verdicts were not carried into final QA.
- Legacy render output could pass while canonical BUILD-chain artifacts were
  missing until manually backfilled.

Assessment:

- This route is better on material duplication.
- It exposes general correctness gates that are too shallow.
- It also confirms that long-running execution must not be owned by a
  short-lived subagent.

## Cross-Route Findings

### CR1. Subagent Work Must Follow Node/Phase Boundaries

Severity: P0 operational

Both runs confirm that a monolithic subagent is the wrong owner for a node-based
state machine. The parent should orchestrate. Workers should be bounded and
short-lived.

Required protocol:

- Parent reads state.
- Parent dispatches one worker for the current node or phase.
- Worker receives only required artifacts.
- Worker writes artifacts plus a short completion report.
- Worker exits.
- Parent reloads state and dispatches the next worker.

Long render/build execution must run under a parent-managed or dedicated runner
lifetime, not inside a subagent that can hit context or token budget.

Acceptance:

- A full E2E run can be resumed from artifacts without conversation memory.
- No render process is orphaned when a worker ends.
- No worker is expected to inspect the whole run folder repeatedly.

### CR2. Rerun Needs A Repeat-State Guard

Severity: P0 operational

Repeated `rerun --node` calls must not loop on the same blocking condition.

Acceptance:

- Track node label, next_action, blocking reason digest, and relevant artifact
  hashes.
- After a small attempt budget, stop rerunning and emit a compact blocking
  summary.
- The next action should be explicit, for example:
  `regenerate_material`, `revise_prompt`, `waive_quality`, `manual_review`, or
  `fix_canonical_chain`.

### CR3. Final QA Needs User-Visible Correctness Dimensions

Severity: P0/P1 correctness

Current verify can pass technical checks while missing what users care about.

Add dimensions:

- target length fit against the brief;
- subtitle render readability;
- content/semantic alignment using VLM or curator verdicts;
- material quality/duplicate health for generated routes.

Acceptance:

- A 180s target cannot ship as 48s with perfect QA without waiver.
- A clipped subtitle cannot receive a clean final review.
- A segment with `VLM=no` cannot disappear from final QA.
- Failed generated material quality cannot be hidden by accepted counts.

### CR4. Canonical Completion Definition Must Match Render Reality

Severity: P1 state-machine correctness

The state machine must not say "missing build_profile" after a valid delivery
path produced a passable final, unless that artifact is actually required for
delivery.

Acceptance:

- Either all render paths emit the canonical Node 8-11 chain, or the completion
  definition explicitly recognizes route-specific render paths.
- A successful run reaches `complete_review_final` without manual dry-build
  backfill.

### CR5. Progress Must Be Observable

Severity: P1 operations

Operators should not infer progress from file mtimes.

Acceptance:

- Every node emits a compact stdout heartbeat.
- Long loops emit segment progress.
- Example:
  `[node 2][seg 9/17] material fetched`
  `[node 10][seg 12/17] rendered mv segment`

## Prioritized Implementation Plan

### P0: Correctness And Runner Safety

1. Add brief target-length enforcement in spec review.
2. Add long-execution ownership rule and node/phase worker protocol to runner
   docs and task packets.
3. Add rerun repeat-state guard.
4. Add generated-material quality gate enforcement: failed quality cannot be
   silently accepted.
5. Add duplicate generated-asset detection and discount duplicates from material
   coverage.

### P1: State And QA Closure

6. Fix material truth precedence for generated/material-map routes:
   `material_delta` and lifecycle are canonical for build readiness; stale
   coverage maps cannot force generic `await_material`.
7. Wire VLM/content alignment verdicts into final QA/dashboard.
8. Resolve legacy render path vs canonical Node 8-11 completion semantics.
9. Add stdout node/segment heartbeat.

### P2: UX/DX Polish With Real Failure Reduction

10. Add post-render subtitle readability/safe-area check.
11. Default subtitles to explicit narration text for narration/stock-first
    routes instead of `subtitle:auto`.
12. Cache expensive VLM picks by query hash where practical.

## Suggested Task Split

### Task 1: Spec Review Duration Gate

Files likely involved:

- `video_pipeline_core/spec_review.py` or current spec-review owner.
- Contract/brief parsing helpers.
- Tests around spec review and route acceptance.

Acceptance:

- A brief target of 180s with estimated 48s narration emits a warning or block.
- Existing well-sized contracts still pass.

### Task 2: Generated Material Quality And Duplicate Gate

Files likely involved:

- `video_pipeline_core/generated_material_producer.py`
- generated material review owner.
- `video_pipeline_core/material_delta.py`
- tests for generated material review and material delta.

Acceptance:

- Assets with failed quality are not accepted without waiver.
- Four identical files do not satisfy a four-panel need.
- Duplicate groups are surfaced as findings.

### Task 3: Material Truth Precedence And Completion State

Files likely involved:

- `video_pipeline_core/dashboard_state.py`
- `video_pipeline_core/runtime_orchestrator.py`
- `video_pipeline_core/delivery_gate.py`
- dashboard/server state tests.

Acceptance:

- Build-ready `material_delta` and lifecycle are not overridden by stale legacy
  coverage gaps.
- Quality failure routes to material-quality/regeneration action, not generic
  `await_material`.
- Passing route-specific render output can reach a terminal state.

### Task 4: Runner Protocol And Rerun Guard

Files likely involved:

- `video_pipeline_core/runtime_orchestrator.py`
- `docs/route-agent-runner-protocol.md`
- `docs/route-orchestrator-harness.md`
- runtime tests.

Acceptance:

- Repeated rerun on the same node/action/artifact digest stops with a compact
  blocking summary.
- Runner docs explicitly define stateless workers and parent-owned long
  execution.

### Task 5: Final QA Surface

Files likely involved:

- verify/QA owner.
- subtitle render verification owner.
- curator/VLM pick artifacts.
- dashboard QA display.

Acceptance:

- QA includes target duration, subtitle readability, and content alignment.
- Findings appear in dashboard and final review artifacts.

## Non-Goals For This Review

- Do not rebuild the frontend dashboard as part of this review.
- Do not switch renderer architecture.
- Do not rewrite Remotion/Node14 paths.
- Do not replace material-map lifecycle.
- Do not remove route-specific behavior; stock-first and generated/material-map
  routes have different failure modes.

## Working Rule

When a gate and a final video disagree, do not trust the final video alone.
Resolve artifact truth first, then decide whether the output is deliverable,
needs regeneration, needs waiver, or needs human review.

