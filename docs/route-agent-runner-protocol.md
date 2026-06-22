# Route Agent Runner Protocol

Date: 2026-06-21
Status: active protocol for external agents consuming route task packets

This protocol tells a Codex, Claude, Gemini, or human worker how to consume
`route_subagent_task.json` and produce `route_subagent_result.json`.

It is intentionally runner-neutral. The Python harness never calls a model API;
it only issues bounded task packets and validates artifacts.

## Worker Contract

When you receive `route_subagent_task.json`:

1. Read the packet.
2. Read only the files listed in `read_only_inputs`, plus documentation
   explicitly named by the operator.
3. Write only files listed in `allowed_outputs`.
4. Do not modify any path listed in `must_not_touch`.
5. Satisfy `success_criteria` with concrete artifacts, not prose claims.
6. Write `route_subagent_result.json`.
7. Stop.

Workers are bounded workers. They own one node, one phase, or one explicit
artifact handoff. They are not the lifetime owner for a full video route.

The orchestrator will run `route-task-accept`. If artifacts are stale, outside
the whitelist, or if protected files changed, the result is rejected even if the
worker says it succeeded.

## Parent-Owned Long Execution

Long-running render, download, VLM selection, and full BUILD execution must be
owned by the parent orchestrator or a dedicated runner process, not by a
short-lived subagent context.

Rules:

- A worker may decide, prepare, or launch a long task only when the task writes a
  resumable artifact or status record.
- The parent must monitor long-running render jobs across turns.
- state.json and artifacts are the handoff; conversation memory is not.
- If the worker exits, the long-running job must still be observable or
  resumable by the parent.

This prevents background render work from becoming orphaned when a worker hits a
token, context, or wall-clock budget.

Recommended split:

```text
parent orchestrator
  -> bounded worker: current node/phase decision or artifact repair
  -> parent-owned long execution: render/build/download/VLM loop
  -> bounded worker: review next gate
```

## Required Result Shape

```json
{
  "artifact_role": "route_subagent_result",
  "task_id": "copy from route_subagent_task.json",
  "status": "done",
  "outputs": [
    "absolute/or/packet-matching/path/to/output.json"
  ],
  "summary": "short factual summary",
  "next_action": null
}
```

Allowed `status` values:

| Status | Meaning | Route movement |
|---|---|---|
| `done` | Declared outputs were written and should be accepted. | advances if validator passes |
| `blocked` | Worker cannot proceed because an input/gate is missing or contradictory. | does not advance |
| `needs_context` | Worker needs operator/user information. | does not advance |
| `failed` | Worker attempted the task and failed. | does not advance |

For non-`done` statuses, `outputs` may be empty and `next_action` should state
the smallest useful follow-up.

## Worker Prompt Template

```text
You are a bounded Hermes Video Pipeline worker.

Read TASK_PATH = <path to route_subagent_task.json>.

Rules:
- Do not choose a different pipeline route.
- Do not write outside task.allowed_outputs.
- Do not modify task.must_not_touch.
- Use task.success_criteria as the acceptance checklist.
- Write route_subagent_result.json with artifact_role="route_subagent_result".
- If blocked, write status="blocked" and next_action.
- If user/operator information is needed, write status="needs_context".
- Do not claim success unless the declared output files exist.

After writing route_subagent_result.json, stop.
```

## Operator Loop

```powershell
python video_tools.py route-task-next RUN_DIR --out route_subagent_task.json
# hand route_subagent_task.json to the worker
python video_tools.py route-task-accept `
  --task route_subagent_task.json `
  --result route_subagent_result.json `
  --state-out route_orchestrator_state.json
```

For smoke testing the mechanism without a real worker:

```powershell
python video_tools.py route-orchestrator-acceptance RUN_DIR `
  --route story-first `
  --stage-count 5 `
  --out route_orchestrator_acceptance.json
```

## Material-Map Review Gate

When the route is blocked at `material-map-lifecycle` with
`next_action=await_map_review`, dispatch a bounded review worker instead of
asking one worker to run the whole route. The worker writes
`material_map_review_verdict.json`; the parent applies it:

```powershell
python video_tools.py material-map-review-apply `
  --maps-dir maps `
  --needs material_needs.json `
  --verdict material_map_review_verdict.json `
  --out project_material_map.json
```

Then the parent reruns the canonical material-map checks. The concrete packet
and verdict contract are documented in
`docs/construction-guides/parent-subagent-map-review-contract.md`.

## Anti-Patterns

- Do not ask a worker to “run the whole video pipeline” from one packet.
- Do not run the whole video pipeline from one worker packet.
- Rule keyword for tests and downstream prompts: do not run the whole video pipeline.
- Do not let a worker decide that a stale `final.mp4` is current.
- Do not let generated images satisfy material needs without material review.
- Do not let Workbench draft artifacts overwrite canonical outputs.
- Do not use prose completion reports as evidence; validate files.
- Do not background a long-running render inside a worker and then rely on that
  worker's context lifetime to keep it alive.

## Where This Fits

This protocol sits above skills and tools:

```text
operator / orchestrator
  -> route_subagent_task.json
  -> external worker
  -> route_subagent_result.json
  -> route-task-accept
  -> route_orchestrator_state.json
```

It does not replace `material-map-lifecycle`, `contract-run`, reviewer policy,
or Workbench/Brownfield routes.
