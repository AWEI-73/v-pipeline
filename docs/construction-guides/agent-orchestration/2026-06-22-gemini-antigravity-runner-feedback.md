# 2026-06-22 Gemini Antigravity Runner Feedback

## Classification

- Source: Gemini / Antigravity framework feedback.
- Scope: external agent orchestration, route runner behavior, material gate truth.
- Status: construction feedback, not a canonical route reference yet.
- Related run folder: `C:\Users\user\Desktop\video_project\fairy-tale-short\runs\20260622-085316-baseline`

This note records a real pipeline run where an external runner produced a final
video but also appeared to loop around material-map state. It should be used as
evidence when hardening node-by-node agent dispatch and material quality gates.

## Observed Run Result

The run folder shows that the pipeline did reach final output:

- `final.mp4` exists.
- `verify_result.json` reports `pass: true`, score `95.0`.
- `editor_review.json` reports `status: pass`.
- `timeline_build.json` contains 54 clip entries using generated image files.

At the same time, the run state is contradictory:

- `state.json` reports `pass: false` and `next_action: await_material`.
- dashboard state also reports `next_action: await_material`.
- `material_map_lifecycle.json` reports `can_build: true` and `next_action: build`.
- `material_delta.json` reports `ready_for_build: true`, with summary:
  `covered: 15`, `thin: 0`, `missing: 0`, `excess: 0`.
- `material_coverage_map.json` still contains 15 gaps and 15 weak assignments.

Conclusion: this was not a simple "no product" failure. The product existed,
but artifact truth was split between legacy coverage state and newer material
delta/lifecycle state.

## Material Quality Finding

The generated material path also exposed a separate quality-gate failure:

- `generated_material_quality_review.json` reports `pass: false`.
- Quality summary reports `item_count: 60`, `min_score: 40`, `avg_score: 40.0`.
- The repeated findings are:
  - `visual_family_missing`
  - `angle_scale_missing`
  - `camera_language_weak`
- `generated_material_review.json` nevertheless accepted all 60 generated items.

Additional inspection found heavy duplication:

- Each beat requested 4 generated panels, but all 4 panels in the same beat used
  the same prompt.
- All 60 generated items shared the same broad prompt prefix.
- Exact file hashes showed large duplicate groups:
  - beat 2-5: 16 identical files
  - beat 6-8: 12 identical files
  - beat 9-11: 12 identical files
  - beat 12-14: 12 identical files
  - beat 1: 4 identical files
  - beat 15: 4 identical files
- The prompt prefix also contained unrelated city/courier/rooftop motifs, which
  did not match the squirrel fairy-tale brief.

Conclusion: the generated material review currently accepts low-quality and
duplicated assets too easily. Material delta then counts accepted quantity as
coverage, even when the underlying assets are not meaningfully diverse.

## Antigravity Feedback Summary

Gemini / Antigravity feedback identified the runner structure as a major token
and stability issue:

- A single subagent was asked to run the whole route from Node 0 through Node 13.
- That subagent repeatedly read large JSON artifacts, reasoned, patched, reread,
  and accumulated context.
- The run eventually hit `429 RESOURCE_EXHAUSTED` multiple times.
- A background rerun task, `runtime.py rerun --node 2`, unexpectedly completed
  rendering while the main subagent was stuck or exhausted.

The feedback states that this violated the intended pipeline shape:

- `runtime.py` is a state machine.
- Each node is an independent work unit.
- A parent agent should orchestrate by reading status, dispatching only the next
  required node, collecting the result, then terminating that worker context.

Recommended agent split from the feedback:

- Phase 1 agent: Node 0-3, story and contract.
- Phase 2 agent: Node 2, material curator.
- Phase 3 agent: Node 5 and Node 8-10, audio and build.
- Phase 4 agent: Node 11-13, editor, render, verify.

The exact node grouping may still need adjustment, but the principle is correct:
do not run a complete pipeline inside one long-lived subagent context.

## Codex Assessment

The Antigravity feedback is directionally correct, but the run folder shows two
distinct issues that should not be collapsed into one:

1. Runner orchestration problem:
   a monolithic subagent is an inefficient and fragile way to drive a node-based
   state machine.

2. Artifact truth problem:
   the runtime/dashboard can still treat stale `material_coverage_map.json`
   findings as blocking after `material_delta.json` and
   `material_map_lifecycle.json` say the route is build-ready.

3. Material quality problem:
   generated material quality can fail while generated material review still
   accepts all assets, allowing duplicated/low-quality material to satisfy
   `material_delta`.

All three need hardening. Fixing only subagent dispatch will reduce token
pressure but will not prevent the pipeline from accepting bad generated images.
Fixing only the material gate will not prevent long-running external agents from
burning context on repeated reruns.

## Recommended Adjustments

### 1. Node-by-node external agent dispatch

Add a runner protocol for external agents:

- Parent agent reads `video_tools.py state` or equivalent dashboard state.
- Parent dispatches exactly one bounded worker for the current actionable node or
  phase.
- Worker receives only minimal input artifacts for that node.
- Worker writes expected artifacts and a short completion report.
- Worker terminates.
- Parent reloads state and decides the next worker.

Acceptance target:

- A full story route can be driven by multiple short-lived workers.
- No worker needs to read the full run folder repeatedly.
- Failed workers produce node-local failure reports instead of consuming the
  whole route context.

### 2. Rerun guard for repeated node failures

Add a guard around rerun behavior:

- Track node label, blocking reason digest, and relevant artifact hash.
- If the same node reaches the same blocking state after a small attempt budget,
  stop rerunning.
- Emit a compact blocking summary artifact instead of launching another full
  orchestrator pass.

Acceptance target:

- `runtime.py rerun --node 2` cannot loop on the same material-map conflict.
- The next action becomes explicit, for example:
  `regenerate_material`, `waive_material_quality`, `revise_prompt`, or
  `manual_review_required`.

### 3. Canonical material state precedence

Define precedence between material artifacts:

- `material_delta.json` is the canonical build-readiness gate.
- `material_map_lifecycle.json` is the lifecycle handoff state.
- `material_coverage_map.json` is diagnostic/legacy coverage evidence unless it
  is explicitly newer and designated as canonical for the current route.

Acceptance target:

- If `material_delta.ready_for_build=true` and lifecycle says `can_build=true`,
  stale coverage gaps should not force dashboard/runtime back to
  `await_material`.
- If quality gate fails, state should move to material quality review or
  regeneration, not generic `await_material`.

### 4. Generated material quality must affect acceptance

Generated material review must honor quality review:

- `generated_material_quality_review.pass=false` cannot be ignored.
- Low-score assets should be rejected, quarantined, or require explicit waiver.
- Accepted generated assets should carry quality evidence.

Acceptance target:

- A run with 60 generated images scoring 40 cannot be considered fully covered
  without waiver.
- `generated_material_review.json` cannot accept all failed assets silently.

### 5. Duplicate generated assets must not satisfy coverage

Material delta should discount duplicates:

- Detect exact duplicate file hash.
- Detect near-duplicate perceptual hashes where practical.
- Require diversity within a beat when multiple panels are requested.
- Require shot/function differences for multi-panel needs, such as establish,
  action, detail, and result.

Acceptance target:

- Four identical generated images do not satisfy a need requiring four usable
  panels.
- Cross-beat duplicate groups are surfaced as material quality findings.

## Pending Comparison

Claude is running a related experiment using Pexels retrieval rather than image
generation. Compare that result against this note before finalizing the
implementation plan.

Specific questions for comparison:

- Does Pexels retrieval avoid duplicate assets better than generated material?
- Does it still suffer from stale `material_coverage_map.json` versus
  `material_delta.json` conflict?
- Does a monolithic subagent also exhaust context on retrieval-based runs?
- Are retrieved clips accepted with enough semantic evidence, or does the same
  "quantity counted as coverage" problem appear?

## Proposed Priority

Recommended implementation order after Claude result is available:

1. Add node-by-node external agent dispatch guidance and tests.
2. Add rerun guard for repeated node/action/artifact states.
3. Fix material state precedence in dashboard/runtime.
4. Wire generated material quality into material acceptance.
5. Add duplicate detection to generated material review/material delta.

