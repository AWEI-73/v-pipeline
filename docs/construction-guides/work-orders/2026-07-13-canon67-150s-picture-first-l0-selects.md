# Work Order: Canon 67 150-Second Picture-First L0 Selects

Date: 2026-07-13
Owner: integrator / main-pipeline
Worker: one fresh long-running Luna session, single writer
Target state: `WAITING_INTEGRATOR_150S_L0_SELECTS_REVIEW`

## Goal And Authorities

Build the first long-duration, evidence-backed L0 picture proposal from the
real Canon 67 material pool. Inspect and order material; do not render the
150-second film.

Read and follow, in order:

1. `AGENTS.md`
2. `RUNBOOK.md`
3. `HANDOFF_CURRENT.md`
4. `docs/superpowers/specs/2026-07-13-canon67-150s-picture-first-longform-design.md`
5. `docs/superpowers/plans/2026-07-13-canon67-150s-picture-first-l0-plan.md`
6. this work order
7. the relevant L0/L1 portions of `skills/editing-loop-director.md` and the
   relevant capability/SOP portions of `skills/material-map.md`

The design decides product boundaries. The plan specifies the ordered work.
This work order controls authority, stop-loss, and acceptance.

## Execution Shape

- Work in `C:/Users/user/Desktop/video_pipeline` in the existing workspace.
- Use one writer sequentially; do not spawn subagents.
- Do not create a worktree, clean, reset, stash, rebase, amend, push, or upload.
- Resume the active state from `HANDOFF_CURRENT.md`; do not start another run.
- Use registered Capability commands for repository tools. Do not write a new
  route runner, selector engine, renderer, private patch tool, or gate.
- A run-local evidence-only source-ledger helper is allowed exactly as defined
  in plan Task 3. It cannot decide selection, mutate source, or enter the
  production registry.

## Delegated Judgment

The worker may decide:

- deterministic inventory and exclusion classification;
- which 72-96 assets receive deep review, subject to stratification rules;
- observed-content descriptions, uncertainty, duplicate proposals, and the
  40-60 clip L0 sequence proposal;
- one LOCAL correction per failure class.

The worker may not decide:

- picture lock, owner taste, human creative approval, or final delivery;
- permission to render L1, add narration/subtitles/audio/effects, or expand the
  source boundary;
- production-code/schema/Skill/registry changes or structural workarounds.

## Owner Zone

The worker may create or update only:

- `.tmp/canon67_150s_picture_first_longform/l0/**`;
- `.tmp/canon67_150s_picture_first_longform/campaign_status.json`;
- the machine-state JSON block and current-work summary in
  `HANDOFF_CURRENT.md` at final state transition.

All source media are read-only. `HANDOFF_CURRENT.md` remains unstaged.

## Forbidden And Protected Zone

Do not modify, stage, or regenerate:

- `video_pipeline_core/**`, `tools/**`, `tests/**`, `skills/**`, `dashboard/**`;
- `RUNBOOK.md`, `AGENTS.md`, `docs/INDEX.md`, Product Spec, the approved design,
  this plan, this work order, or its execution companion;
- source media, previous candidates, historical campaign artifacts,
  `reference repo/**`, or existing dirty/untracked user files.

Do not use `67期結訓影片-終.mp4`, its duplicate final export,
`66期學長音樂檔/**`, `66期學長空拍影片/**`, generated/synthetic material,
prior renders/proxies, `主任勉勵/**`, or `感謝導師/**` in the proposal.

## Required Outcomes

1. The complete-pool inventory executes through the committed accountability
   companion and yields an immutable PASS receipt.
2. The complete source ledger and exclusion ledger are hash-bound.
3. A stratified 72-96 item deep-review pool covers all three sections, at least
   twelve categories, and both media types when usable.
4. Every final still is pixel-reviewed and every final video window has
   multi-timepoint evidence personally reviewed by the agent.
5. The proposal contains 40-60 distinct stable clip IDs, at least six source
   categories, three 45-55 second sections, and 150.0 +/- 0.5 planned seconds.
6. No known duplicate, rejected, excluded, or unreviewed asset enters the
   proposal; any repeated motif is explicit and awaits integrator approval.
7. The agent attestation and strict closure are valid and run-bound.
8. No rendered candidate is created and both approval flags remain false.

## Testing Policy

Run only the focused tests, registry audit, strict closure, source/hash
read-backs, UTF-8/JSON checks, and `git diff --check` specified in the plan.
There is no production-code change, so the full suite is forbidden in this
work order. A timeout or failure must not be hidden by substituting a weaker
check.

## Stop-Loss

Stop at the last valid evidence state when:

- the source root or any protected authority drifts;
- an excluded/reference asset is needed to meet duration or coverage;
- a production change, new public interface, new registry entry, or render is
  required;
- the same failure class repeats after one LOCAL correction;
- a tool would need a private duplicate implementation or a gate would need to
  manufacture missing evidence;
- the agent cannot truthfully prove it viewed real pixels/temporal evidence for
  every proposed selection;
- focused validation or strict closure remains nonzero.

Classify the blocker LOCAL or STRUCTURAL. Do not patch symptoms after a
STRUCTURAL classification. Report PASS/FAIL/UNKNOWN honestly.

## Final Report

Write
`.tmp/canon67_150s_picture_first_longform/l0/final/worker_report.md` with:

- exact commands, exit codes, logs, receipt/trace/attestation paths and hashes;
- actual inventory, candidate, final-select, section, category, media-type,
  duplicate, fresh/reused evidence, and viewed-evidence counts;
- the six-field decision record and links to the integrator packet;
- pre/post HEAD and dirty tree, protected/source hash read-back, corrections,
  deviations, skipped work, blockers, and blind spots;
- final state `WAITING_INTEGRATOR_150S_L0_SELECTS_REVIEW`;
- `human_creative_approval=false` and `final_delivery_claimed=false`.

The worker report is a claim, not acceptance. The integrator will independently
inspect the packet before authorizing any L1 render continuation.
