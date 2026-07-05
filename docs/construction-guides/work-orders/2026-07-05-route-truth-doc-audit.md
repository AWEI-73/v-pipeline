# Route Truth Documentation Audit

Date: 2026-07-05
Status: Phase D audit report / minimal patch record

## Scope

This audit classifies current route-truth documentation, identifies stale
command or artifact references that could mislead a new agent, and records
minimal corrections. It does not reorganize docs, delete historical files, or
rewrite the docs index.

## Route Truth Documents

- `docs/START_HERE_VIDEO_PIPELINE.md`: canonical entrypoint and Rule Zero.
- `docs/branch-contract-registry.json`: machine-readable branch ownership,
  canonical artifacts, forbidden writes, stop gates, and return routes.
- `docs/pipeline-decision-tree.md`: current operator decision tree for branch
  selection, stop gates, and return loops.
- `docs/video-pipeline-operating-map.md`: stage-by-stage tool and artifact map.
- `docs/interface-contracts/README.md` plus
  `docs/interface-contracts/pipeline-api-dictionary.json`: branch interface
  dictionary and audit/discovery contract.

## Supporting / Operational Documents

- `RUNBOOK.md`: Windows-local command examples and tiered verification.
- `docs/agent-ops/work-order-sop.md`: multi-agent work-order discipline and
  common acceptance instruments.
- `docs/artifact-reviewer-map.md`: reviewer policy and roles.
- `docs/build-capability-alignment.md`: which capabilities currently affect
  BUILD/render.
- `docs/stage-boundary-matrix.md`: route and worker boundary matrix.

## Historical / Construction Documents

- `docs/construction-guides/work-orders/2026-07-04-probe-repair-round.md`:
  accepted repair round and evidence, not route truth by itself.
- `docs/construction-guides/work-orders/2026-07-05-stock-semantic-fit-honesty-plan.md`:
  next-round design work order, not implemented behavior.
- `docs/construction-guides/work-orders/2026-07-04-mini-stress-probes.md`:
  probe findings and stress evidence, useful background only.
- `docs/construction-guides/work-orders/2026-07-04-storybook-stock-story.md`:
  storybook probe evidence, useful background only.
- `docs/archive/`: historical archive unless a current route-truth doc links it
  for a specific reason.

## Stale Command References

Corrected in this phase:

- `docs/interface-contracts/README.md` used direct
  `python tools/pipeline_interface_audit.py` examples. The current agent-facing
  hard gate is `python video_tools.py interface-audit`; JSON output should use
  `--out .tmp/interface_audit.json`.

Already corrected in Phase A:

- `docs/agent-ops/work-order-sop.md` now includes
  `python video_tools.py interface-audit` and
  `python video_tools.py acceptance-contract`.

Allowed compatibility references:

- Tests may still import or execute `tools/pipeline_interface_audit.py` because
  the underlying audit script remains part of compatibility coverage.
- Historical work-order reports may quote old commands as evidence from that
  date.

## Stale Artifact Names

- `route_decision.json` appears only as legacy/compat language in
  `START_HERE` and the operating map. Current route truth is
  `video_intent.json`.
- `delivery_gate.json` appears in the branch registry as a verify/delivery
  output, while current prose and tests often use `delivery_gate_report.json`.
  This should be normalized in a separate registry/interface contract pass
  because changing registry artifact names can affect tests and downstream
  readers.
- `route_judgment.json` appears as an explicit anti-pattern in `RUNBOOK.md` and
  the decision tree; it is not current truth.

## Interface / Registry / Workflow Relationship

- The branch registry defines branch owners, canonical outputs, forbidden
  writes, next actions, and return routes.
- The interface dictionary defines request/handoff/repair interfaces between
  those branches.
- The workflow manifest groups `video_tools.py` commands into executable route
  steps.
- `video_tools.py interface-audit` is the current wrapper that checks command
  surface, workflow refs, capability refs, and acceptance command refs. The
  lower `tools/pipeline_interface_audit.py` remains compatibility machinery,
  not the command new agents should memorize.

## Recommended New-Agent Read Set

Read these five files first:

1. `docs/START_HERE_VIDEO_PIPELINE.md`
2. `RUNBOOK.md`
3. `docs/branch-contract-registry.json`
4. `docs/pipeline-decision-tree.md`
5. `docs/video-pipeline-operating-map.md`

Then read branch-specific docs only after the current owner route is known.

## Deferred Cleanup List

- Decide whether `delivery_gate.json` and `delivery_gate_report.json` should be
  formally aliased or normalized in registry/interface docs.
- Consider shortening the Tier 1 read list in `START_HERE` after the interface
  audit and acceptance contract remain stable for another work-order round.
- Add a small docs lint for current acceptance command names if stale command
  references recur.
- Keep historical work-order reports intact; add compatibility notes instead of
  rewriting old evidence.

## Minimal Patch Record

- Updated `docs/interface-contracts/README.md` to point at
  `python video_tools.py interface-audit` and `--out .tmp/interface_audit.json`.

## Verification

Required Phase D commands:

- `python video_tools.py interface-audit`
- `python video_tools.py acceptance-contract --out .tmp/acceptance_contract.json`
- `python video_tools.py registry-audit`
- `python video_tools.py test-tiers --tier work-order-acceptance --dry-run`
- `python -m unittest discover -s tests`
