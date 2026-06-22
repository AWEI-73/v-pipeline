# Route Orchestrator Harness

Date: 2026-06-21
Status: active bounded harness for multi-agent route execution

This harness turns the canonical video-pipeline route into deterministic
subagent task packets and deterministic acceptance checks. It does not call any
specific model API. Codex, Claude, Gemini, or a human runner can consume the
packet and write the declared outputs.

Worker-facing instructions live in `docs/route-agent-runner-protocol.md`.

## Purpose

Use this when the pipeline is run by multiple agents and the orchestrator needs
to keep hard boundaries:

```text
route state
  -> route_subagent_task.json
  -> external agent writes allowed outputs
  -> route_subagent_result.json
  -> harness validates outputs and advances or blocks state
```

The harness trusts artifacts, not agent claims.

## Execution Model

The orchestrator is the parent. External agents are bounded workers.

The parent owns:

- route state;
- task issue/acceptance;
- parent-owned long execution for render/build/download/VLM jobs;
- resume monitoring across turns.

Workers own:

- one node, phase, or artifact handoff from `route_subagent_task.json`;
- only the files in `allowed_outputs`;
- a short `route_subagent_result.json` report.

state.json and artifacts are the handoff between workers. A worker should not
depend on conversation memory from a previous worker, and the parent should not
ask one worker to run the whole route end to end.

## Commands

Issue the next task:

```powershell
python video_tools.py route-task-next RUN_DIR `
  --state route_orchestrator_state.json `
  --out route_subagent_task.json
```

Accept or reject a result:

```powershell
python video_tools.py route-task-accept `
  --task route_subagent_task.json `
  --result route_subagent_result.json `
  --state-out route_orchestrator_state.json
```

Inspect route state:

```powershell
python video_tools.py route-orchestrator-report `
  --state route_orchestrator_state.json
```

Replay a deterministic fake-worker route:

```powershell
python video_tools.py route-orchestrator-acceptance RUN_DIR `
  --route existing-material-first `
  --stage-count 4 `
  --out route_orchestrator_acceptance.json
```

## Task Packet Contract

`route_subagent_task.json` contains:

- `stage_index`, `stage`, `role`, `objective`
- `read_only_inputs`
- `allowed_outputs`
- `must_not_touch`
- `success_criteria`
- `issued_at_epoch`
- `snapshot.must_not_touch`

`allowed_outputs` is a write whitelist, not a requirement to produce every
listed file. The result must only claim files from this list.

`must_not_touch` is enforced. The harness snapshots file existence, file type,
and sha256 before the runner starts; acceptance rejects if any protected file is
changed, deleted, or created unexpectedly.

## Result Contract

`route_subagent_result.json` must contain:

```json
{
  "artifact_role": "route_subagent_result",
  "task_id": "...",
  "status": "done | blocked | needs_context | failed",
  "outputs": [],
  "summary": "...",
  "next_action": "..."
}
```

`done` advances to the next stage only if all claimed outputs are:

- inside `allowed_outputs`;
- present files;
- fresher than `issued_at_epoch`;
- accepted while `must_not_touch` hashes still match.

`blocked`, `needs_context`, and `failed` do not advance the route. They write an
explicit state transition and `next_action`.

## Guardrails

1. **No soft boundaries**: `must_not_touch` is checked by hash, not by prompt.
2. **Freshness**: stale outputs older than the task issue time are rejected.
3. **Idempotency**: issuing a task clears stale allowed outputs by default.
4. **Fail-closed smoke**: bad artifacts must be rejected before the route moves.
5. **Runner-neutral**: the harness does not import Codex, Claude, Gemini, or any
   model SDK.
6. **Parent-owned long execution**: long-running render/build jobs must remain
   observable and resumable after any individual worker exits.

## Acceptance Smoke

`route-orchestrator-acceptance` proves two properties without a real LLM
runner:

- happy path: task packet -> fake worker output -> accept -> state advances;
- fail-closed path: injected protected-file mutation is rejected before state
  advances.

Use it after changing route stages, task packet shape, or command wiring.

## Current Boundary

This is an orchestration harness. It does not replace:

- `material-map-lifecycle`
- `contract-run`
- reviewer policy
- Workbench draft patching
- Brownfield edit / effects routing

Those remain the route stages' tools. The harness only packages work and gates
the handoff between agents.
