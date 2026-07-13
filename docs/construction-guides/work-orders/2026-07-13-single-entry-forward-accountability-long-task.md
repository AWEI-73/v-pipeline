# Work Order: Single Entry And Forward Accountability Long Task

Date: 2026-07-13
Owner: integrator / main-pipeline
Worker: one long-running implementation worker, single writer at all times
Target state: `WAITING_INTEGRATOR_FINAL_REVIEW`

## Goal And Construction Sources

Implement the approved forward-only foundation so a new run has one visible
entry, every executable step uses a registered Capability, agent/owner
decisions are bound to the current run, gates cannot manufacture their own
evidence, and unsupported completion claims fail closed.

Read and follow, in order:

1. `AGENTS.md`
2. `docs/superpowers/specs/2026-07-13-single-entry-forward-accountability-design.md`
3. `docs/superpowers/plans/2026-07-13-single-entry-forward-accountability-implementation-plan.md`
4. this work order

The design decides architecture. The implementation plan supplies exact tasks,
schemas, commands, and expected results. This work order decides authority,
scope, stop-loss, and report requirements.

## Execution Shape

- Work in `C:/Users/user/Desktop/video_pipeline` in the existing workspace.
- Do not create a worktree: the current dirty authority documents are required
  inputs and must be preserved.
- Use one writer sequentially. No parallel file editors or concurrent
  accountable steps. Sequential helper/subagent review is allowed only when it
  does not create a second writer.
- Execute plan Tasks 1-14 in order. Do not pause at normal owner gates; this
  work order already delegates the deterministic choices listed below.
- The integrator retains architecture, deletion outside the three approved
  document edits, public behavior expansion, product taste, and final
  acceptance.

## Owner Zone

The worker may edit only:

- `AGENTS.md`, `RUNBOOK.md`, `HANDOFF_CURRENT.md`, `docs/INDEX.md`, and
  `docs/START_HERE_VIDEO_PIPELINE.md` under the Phase A dirty-file rules;
- `video_pipeline_core/doc_reference_hygiene.py`;
- `video_pipeline_core/skill_tool_contract.py`;
- `video_pipeline_core/capability_catalog.py`;
- `video_pipeline_core/capability_execution.py` (new);
- `video_pipeline_core/tool_command_catalog.py`;
- `video_pipeline_core/no_skip_execution_trace.py`;
- `video_pipeline_core/route_closure_integrity.py` only if a RED test proves
  bounded strict-closure integration is required;
- `tools/skill_tool_contract_audit.py`;
- `tools/no_skip_execution_trace.py`;
- `video_tools.py` only for `capability-run` registration/handler/parser;
- the eleven Domain Skill files named in the implementation plan;
- the exact focused/new tests named in the implementation plan;
- `tests/fixtures/accountability_forward_v1/**`;
- `docs/construction-guides/work-orders/2026-07-13-single-entry-forward-accountability-acceptance.execution.json`;
- `.tmp/single_entry_forward_accountability_acceptance/**` evidence.

## Forbidden / Read-Only Zone

Do not modify, stage, delete, or regenerate:

- `skills/editing-loop-director.md`;
- `docs/construction-guides/2026-07-10-editing-loop-product-spec.md`;
- `skills/INDEX.md`;
- `docs/branch-contract-registry.json`;
- Workbench production paths and `dashboard/**`;
- `reference repo/**`;
- existing candidate media, raw source media, prior campaign artifacts, or
  historical work orders;
- unrelated dirty/untracked paths present at start.

Do not push, upload, reset, clean, stash, rebase, or amend existing commits.

## Pre-Approved Retirement Boundary

Only these misleading current-authority contents are approved for removal:

1. RUNBOOK `## Current Editing Loop Continuation` volatile campaign section,
   replaced by stable HANDOFF routing.
2. docs/INDEX `Current Editing Loop continuation` current-authority row,
   preserving any historical link only as non-authoritative map content.
3. HANDOFF's old 2026-07-11/2026-07-03 current payload, replaced by this work
   order's machine state block and short human summary.

No code, command, Capability ID, Skill, test, alias, whole document, or route
runner is approved for deletion. Audit discovered candidates, but classify
them `keep` or `legacy_read_only` and report them for later integrator review.

## Ordered Outcomes

1. Baseline and protected hashes frozen; existing focused baseline green.
2. Exact single-entry/HANDOFF contract red-first, then green; Phase A remains
   one unstaged integrator-owned unit because authority files were dirty before
   the task.
3. All 51 pre-change Capability IDs gain class/role fields; live catalog
   exposes command/class/role; no ID disappears in this unattended task.
4. One shared execution core implements committed contracts, safe paths,
   initialization, exclusive reservations, immutable receipts, manifest
   continuity, and run-bound decision validation.
5. `capability-run` becomes one classified public command, not a router.
6. Existing no-skip closure seals strict v2 evidence without breaking legacy
   v1 reads or allowing strict-to-legacy fallback.
7. Committed positive/negative fixtures prove the two real capabilities and
   legal `WAITING_OWNER_ACCOUNTABILITY_FIXTURE` closure.
8. Focused, compatibility, real audits, diff check, and one final full suite
   are green; state stops at integrator review with both approval flags false.

## Red-First And Commit Rules

- Every behavior change needs the plan's RED evidence before implementation.
- One LOCAL correction per failure class. Recurrence is STRUCTURAL.
- Never relax a test, copy a gate, write a run-local substitute, or widen an
  owner zone to turn RED into GREEN.
- Never stage the Phase A authority/evaluator/test unit. Commit only the clean
  Phase B, Task 7, Task 8, Task 9, strict closure, and fixture scopes listed in
  the plan.
- Before every commit, inspect staged paths and exclude pre-existing dirty
  files.

## Acceptance

Run the exact commands in plan Tasks 13-14. Required final evidence:

- combined focused/adjacent suite: exit `0`;
- Workbench compatibility suite: exit `0` and six protected hashes unchanged;
- Skill, doc-reference, and route-closure audits: exit `0`, `ok=true`;
- strict positive forward run: tool receipts PASS and legal
  `WAITING_OWNER_ACCOUNTABILITY_FIXTURE`;
- four negative fixture tests: pass while asserting their blocking codes;
- `git diff --check`: exit `0` (line-ending warnings only are allowed);
- one and only one `unittest discover -s tests` run with timeout 1,200,000 ms:
  exit `0`;
- pre/post user dirty paths preserved; Phase A paths explicitly unstaged;
- `human_creative_approval=false` and `final_delivery_claimed=false`.

## Stop-Loss

Stop at the last green commit when:

- protected or pre-existing authority hashes drift unexpectedly;
- an out-of-zone edit is required;
- the same failure class repeats after one LOCAL correction;
- a structural contract/path/concurrency/gate/actor-binding defect appears;
- any unapproved deletion is required;
- a focused/adjacent command remains nonzero;
- the one final full suite fails or times out.

Do not repair or rerun the full suite under this work order after its one final
attempt. Report PASS/FAIL/UNKNOWN honestly.

## Worker Report

Write
`.tmp/single_entry_forward_accountability_acceptance/final/worker_report.md`
with:

- exact commits and `git show --stat` scopes;
- every RED/GREEN/acceptance command, exit code, and log path;
- contract/reference/receipt/manifest/attestation/trace/decision hashes;
- Capability pre/post ID sets and retirement table;
- pre/post dirty tree and unstaged Phase A paths;
- deviations, LOCAL corrections, skipped items, blockers, and blind spots;
- final state and both approval flags.

A worker report is not final acceptance. The integrator will independently
review diffs, rerun material checks, reconcile Phase A, and decide closure.
