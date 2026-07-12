# Single Entry And Forward-Only Capability Accountability Design

Date: 2026-07-13
Status: proposed for written-spec review
Scope: new runs only; one operational entry, non-orphan capability execution,
evidence-bearing agent/owner decisions, gate purity, and fail-closed closure

## 1. Decision Summary

Hermes keeps one operational entry and extends existing accountability
mechanisms instead of adding another orchestrator, registry, database, or
journal.

The canonical chain is:

```text
AGENTS.md (always-loaded pointer)
  -> RUNBOOK.md (the only operational entry)
  -> HANDOFF_CURRENT.md (current state, not another entry)
  -> dispatch-capabilities (read-only machine lookup)
  -> Domain Skill / Capability / Tool / Workbench
  -> pipeline_execution_trace.json (planned steps plus receipts)
  -> no_skip_contract_decision.json (fail-closed closure)
  -> owner verdict or STOPPED_<STEP>_<REASON>
```

This design guarantees a narrower and honest property:

> A run is not guaranteed to succeed, but a run that did not complete its
> authorized process cannot legally claim completion.

It does not automate creative taste or final delivery approval.

## 2. Why This Is Needed Now

The repository already proves that the underlying factory is real:

- 51 live Capability Cards;
- 107/107 Python tools have owners;
- 150 commands are classified;
- `dispatch-capabilities` resolves by capability ID, owner, loop, and text;
- `pipeline_execution_trace.json` already records bounded route execution;
- `no_skip_execution_trace` already blocks missing traces, copied gates,
  run-local self-authored gates, and rendered QA without frame evidence;
- `route_closure_integrity` validates route owners, artifacts, review kinds,
  and next actions;
- `doc_reference_hygiene` already detects unclassified canonical documents.

The missing integration is observable:

1. `RUNBOOK.md`, `HANDOFF_CURRENT.md`, and `docs/INDEX.md` can disagree about
   the active campaign and legal stop.
2. Tool registration proves that a capability exists, but not that an
   individual work-order step actually ran.
3. Agent review, deterministic tool execution, gate judgment, and owner
   verdict are described in doctrine but are not enforced uniformly at
   closure.
4. A gate can be technically green without proving that the required upstream
   actor did its work.
5. The current safeguards apply mainly to selected rendered routes rather than
   every new run that claims accountable closure.

These are forward-growth risks. Historical artifacts do not need migration.

## 3. Goals

1. Give every agent one unmistakable operational entry.
2. Keep Capability Cards and `dispatch-capabilities` as the only machine
   capability lookup; do not create a second catalog.
3. Prevent new tools, commands, capabilities, Skills, or decision artifacts
   from becoming unowned or undiscoverable.
4. Bind every required work-order step to a registered capability and an
   allowed actor class.
5. Record deterministic execution with command, exit, inputs, outputs, hashes,
   and verification references.
6. Record agent review as evidence-bearing attestation, not as a machine PASS.
7. Preserve explicit owner authority for taste, facts, rights, and delivery.
8. Make gates read-and-judge components; a gate may not manufacture the
   evidence that makes itself pass.
9. Fail closure when steps are missing, substituted, self-authored, stale,
   unregistered, out of scope, or actor-incompatible.
10. Apply the contract only to new runs that opt into version 1.

## 4. Non-Goals

- No historical artifact backfill.
- No deletion or mass rewrite of historical work orders.
- No central route orchestrator, persistent daemon, event bus, database, or
  append-only journal engine.
- No automatic creative approval or final delivery claim.
- No automatic retry-until-PASS loop.
- No new static Capability Catalog file.
- No requirement to modify all 107 tools so that each writes its own receipt.
- No Workbench UI redesign in this project.
- No L1 diversity algorithm, L3 audio-balance, or L5 quality fix in this
  project; those remain separate owner-zone changes that can serve as the first
  forward test.
- No long-form certification claim.
- No model-specific authority rule. Model name may be runtime metadata only
  when the dispatch surface proves it.

## 5. One Operational Entry

### 5.1 Entry roles

Only `RUNBOOK.md` may call itself the operator or operational entry.

| Surface | Fixed role |
| --- | --- |
| `AGENTS.md` | Always-loaded one-line pointer to `RUNBOOK.md`; no workflow duplication. |
| `RUNBOOK.md` | The single operational entry and stable routing doctrine. |
| `HANDOFF_CURRENT.md` | Current state payload and next action; never a second entry. |
| `docs/START_HERE_VIDEO_PIPELINE.md` | Concept orientation only. |
| `docs/INDEX.md` | Document map only; explicitly not an entry. |
| `skills/INDEX.md` | Skill ownership map only. |
| `dispatch-capabilities` | Read-only machine capability lookup. |
| Workbench | Human contract-adjustment surface, not a documentation entry. |

### 5.2 Stable RUNBOOK content

`RUNBOOK.md` must not duplicate a campaign-specific state or owner-gate
literal. It points to `HANDOFF_CURRENT.md` for volatile state and contains:

- the canonical read order;
- semantic route precedence;
- the instruction to resume an existing run before starting a branch;
- the four `dispatch-capabilities` lookup forms;
- the rule that historical work orders are not current authority;
- the rule that closure is decided by machine evidence plus required
  agent/owner decisions.

The stable lookup examples are:

```powershell
C:/Users/user/miniconda3/python.exe video_tools.py dispatch-capabilities --id <CAPABILITY_ID> --json
C:/Users/user/miniconda3/python.exe video_tools.py dispatch-capabilities --owner <OWNER> --json
C:/Users/user/miniconda3/python.exe video_tools.py dispatch-capabilities --loop <L0-L5> --json
C:/Users/user/miniconda3/python.exe video_tools.py dispatch-capabilities --query "<TERMS>" --json
```

### 5.3 Machine-readable HANDOFF block

`HANDOFF_CURRENT.md` remains human-readable and gains exactly one parseable
block:

```text
<!-- HANDOFF_STATE_START -->
{
  "artifact_role": "current_handoff_state",
  "version": 1,
  "updated_at": "RFC3339 timestamp",
  "state": "WAITING_* | STOPPED_* | ACTIVE",
  "active_work_order": "repo-relative path or null",
  "active_spec": "repo-relative path or null",
  "active_skill": "repo-relative path or null",
  "active_run_root": "repo-relative path or null",
  "owner_packet": "repo-relative path or null",
  "next_actions": ["bounded actions"],
  "do_not_do": ["explicit prohibitions"],
  "human_creative_approval": false,
  "final_delivery_claimed": false
}
<!-- HANDOFF_STATE_END -->
```

There is no second current-state JSON file. The block is the machine-readable
part of the existing handoff document.

### 5.4 Entry audit

Extend the existing document/reference hygiene surface. The entry audit fails
when:

- more than one document claims to be the operational entry;
- `AGENTS.md` does not point to `RUNBOOK.md`;
- `RUNBOOK.md` does not point to `HANDOFF_CURRENT.md`;
- `RUNBOOK.md` contains a campaign-specific current-state literal;
- the HANDOFF block is missing, duplicated, invalid JSON, or invalid UTF-8;
- a non-null HANDOFF path does not exist;
- the HANDOFF state contradicts its owner packet or campaign state;
- `docs/INDEX.md` or START_HERE claims to be the operational entry;
- current anchors classify a historical work order as active.

The audit extends `doc_reference_hygiene`; it does not create a new entry
registry.

## 6. Capability Actor And Role Contract

Every canonical Capability Card gains two required fields for forward-only
accountability:

```json
{
  "execution_class": "deterministic | agentic | owner | hybrid",
  "capability_role": "operation | review | gate | adapter"
}
```

Definitions:

| execution class | Required evidence |
| --- | --- |
| `deterministic` | Trusted single-step execution receipt. |
| `agentic` | Agent attestation with evidence refs, judgment, and blind spots. |
| `owner` | Explicit owner decision artifact. |
| `hybrid` | Deterministic receipt plus agent attestation; owner decision when the step declares one. |

Roles are orthogonal:

- `operation`: changes an authorized run artifact.
- `review`: reads evidence and proposes findings or decisions.
- `gate`: reads evidence and returns PASS/FAIL/UNKNOWN plus findings.
- `adapter`: deterministic format conversion without route or taste judgment.

The live catalog and query response expose these two fields. Static audit fails
an unknown or missing value on canonical capabilities after migration.

## 7. Forward-Only Work-Order Execution Contract

### 7.1 Opt-in boundary

A new accountable run contains:

```json
{
  "accountability_contract_version": 1
}
```

The version may live in the execution contract and trace. Absence means legacy
behavior. Presence activates strict closure; it is not a waiverable flag.

### 7.2 Execution contract

Before a worker mutates an owner zone, the integrator freezes
`work_order_execution_contract.json` under the new run root:

```json
{
  "artifact_role": "work_order_execution_contract",
  "version": 1,
  "accountability_contract_version": 1,
  "work_order_id": "stable ID",
  "work_order_path": "repo-relative path",
  "work_order_sha256": "SHA-256",
  "steps": [
    {
      "step_id": "L1.picture.revise",
      "loop": "L1",
      "capability_id": "cap.material-map.material-rough-cut.v1",
      "depends_on": [],
      "required_outputs": ["repo-relative or run-relative paths"],
      "required_verifiers": ["registered capability IDs"],
      "owner_verdict_required": false
    }
  ],
  "allowed_owner_zones": ["repo-relative path patterns"],
  "forbidden_paths": ["repo-relative path patterns"],
  "human_creative_approval": false,
  "final_delivery_claimed": false
}
```

The contract is a machine companion to a formal work order, not a second
product spec. Its hash is frozen before execution. A changed contract requires
an integrator-authored amendment and a new hash; workers cannot silently widen
it.

### 7.3 Plan completeness

The execution contract describes only required accountable steps, not every
read-only shell inspection. A required step must be a registered capability.
Diagnostic reads may remain unplanned when they do not write state or make a
closure claim.

## 8. Trusted Single-Step Capability Execution

### 8.1 Thin boundary

Add one command to the existing `video_tools.py` surface:

```text
capability-run
```

It is a single-step executor, not a router:

- accepts one execution contract, one step ID, and an argv array;
- resolves the step's Capability Card from the live catalog;
- verifies the command prefix matches the capability's registered tool;
- rejects shell strings and uses no `shell=True` behavior;
- verifies the step's dependency receipts before execution;
- snapshots declared inputs, run-root paths, and git/worktree state relevant to
  the allowed owner zone;
- executes exactly one command;
- records exit code, duration, declared output hashes, changed paths, and
  verifier references;
- does not choose a next capability;
- does not retry;
- does not transform FAIL into PASS;
- does not mutate the work-order contract.

The implementation lives in one shared core module and one existing
`video_tools.py` command. No per-tool receipt code is required.

### 8.2 Command matching

The exact executable may vary by environment, but the repo-relative tool or
`video_tools.py` subcommand must match the Capability Card's normalized tool
reference. A worker cannot declare one capability and run another command.

### 8.3 Receipt entry

`pipeline_execution_trace.json` becomes version 2 for accountable runs:

```json
{
  "artifact_role": "pipeline_execution_trace",
  "version": 2,
  "accountability_contract_version": 1,
  "work_order_execution_contract": "work_order_execution_contract.json",
  "work_order_execution_contract_sha256": "SHA-256",
  "entries": [
    {
      "step_id": "L1.picture.revise",
      "capability_id": "cap.material-map.material-rough-cut.v1",
      "execution_class": "hybrid",
      "capability_role": "operation",
      "actor_type": "tool",
      "actor_id": "normalized registered tool",
      "command_argv": [],
      "started_at": "RFC3339",
      "completed_at": "RFC3339",
      "duration_sec": 0.0,
      "exit_code": 0,
      "status": "pass | fail | unknown | stopped",
      "input_hashes": {},
      "output_hashes": {},
      "changed_paths": [],
      "verify_refs": [],
      "source_tool": "video_tools.py capability-run"
    }
  ],
  "human_creative_approval": false,
  "final_delivery_claimed": false
}
```

Version 1 traces remain readable and keep their existing meaning. They do not
satisfy a version 1 accountability contract.

## 9. Agent Attestation And Owner Verdict

### 9.1 Agent attestation

Agent cognition cannot be proven cryptographically. The enforceable promise is
that an agentic claim must be evidence-bearing and tamper-evident.

An `agentic` or `hybrid` step references an attestation artifact:

```json
{
  "artifact_role": "agent_attestation",
  "version": 1,
  "step_id": "L1.picture.review",
  "capability_id": "registered capability ID",
  "actor_type": "agent",
  "agent_run_id": "runtime/session identifier",
  "model": null,
  "reviewed_evidence": [
    {"path": "repo-relative path", "sha256": "SHA-256", "locator": "time/cell/check"}
  ],
  "judgment": "bounded conclusion",
  "blind_spots": ["explicit limitations"],
  "proposed_findings": ["finding artifact IDs or paths"],
  "attested_at": "RFC3339",
  "content_sha256": "hash of canonical content excluding this field"
}
```

The model field is optional and may be populated only when the runtime proves
the selected model. A prose statement such as "reviewed" without evidence,
judgment, blind spots, and hashes does not satisfy the step.

### 9.2 Owner verdict

Owner-required steps reference an existing explicit owner decision artifact.
The trace binds its path and hash; the accountability layer does not invent a
new creative-verdict system.

An owner decision must state the bounded scope and one of approve, revise,
reject, or delegate. Owner silence is never approval. Tool or agent output
cannot set `human_creative_approval=true` or `final_delivery_claimed=true`.

### 9.3 Actor substitution rules

- A deterministic receipt cannot satisfy an agentic step.
- Agent attestation cannot satisfy an owner step.
- Gate PASS cannot satisfy a missing operation, review, or owner verdict.
- A hybrid step is complete only when every declared evidence part exists.
- An agent may propose findings but may not convert taste to objective PASS.

## 10. Gate Purity

A capability with `capability_role=gate` may:

- read declared inputs;
- write only its declared report/findings outputs under the run root;
- return PASS, FAIL, or UNKNOWN;
- recommend a registered next action.

It may not:

- write or replace video/audio/media;
- write or modify timeline, script, subtitle, material-map, mix-plan, effect,
  or owner-verdict truth;
- call an undeclared production capability;
- generate an input that it then uses to clear itself;
- copy a gate artifact from another run;
- use a run-local helper to impersonate the registered owner tool;
- waive a missing upstream step.

`capability-run` records a before/after run-root manifest and relevant git diff.
For a gate, changed paths must be a subset of the card's declared outputs. A
production-truth or media write makes the gate receipt FAIL even when the gate
process exits zero.

The existing gate-authenticity classifications remain authoritative:

- `pipeline_tool_generated` may be accepted;
- `run_local_worker_generated`, `copied_from_prior`, and unknown authenticity
  block closure.

## 11. Fail-Closed Closure

Extend `no_skip_execution_trace` rather than creating another closure engine.

When `accountability_contract_version=1`, closure verifies:

1. execution-contract hash and work-order hash;
2. every required step has exactly one terminal receipt or an explicit stopped
   receipt;
3. all dependency ordering constraints;
4. capability ID resolves in the live catalog;
5. command/tool matches the capability;
6. execution class and role match the receipt and evidence;
7. exit/status consistency;
8. required output existence and hashes;
9. required verifier receipts and evidence refs;
10. owner-zone and forbidden-path compliance;
11. no unplanned state-changing capability execution;
12. agent-attestation completeness and hashes;
13. owner-verdict presence when required;
14. gate purity and gate authenticity;
15. state legality and approval flags.

Legal outcomes:

- all objective steps green, owner still required -> `WAITING_OWNER_*`;
- all required objective and owner evidence green -> bounded `PASS` or next
  declared state;
- a required step failed -> `STOPPED_<STEP>_<FAILURE_CLASS>`;
- evidence is missing or unverifiable -> `UNKNOWN` or `STOPPED_*_UNKNOWN`;
- no path may claim COMPLETE solely because a narrative report says so.

The closure decision is itself a gate and may write only
`no_skip_contract_decision.json` plus its declared audit report.

## 12. Static Orphan Prevention

The existing Skill/tool/capability audit remains the static authority. A new
canonical tool or capability is valid only when:

- its file exists;
- its Domain Skill owns it;
- its Capability ID is unique;
- execution class and capability role are valid;
- command registration and command catalog agree when applicable;
- the Skill is indexed with a valid branch owner;
- the capability is discoverable through `dispatch-capabilities`;
- deprecated/legacy IDs are not active consumer references;
- every active Director reference resolves.

New tools may be developed red-first inside an authorized owner zone, but the
campaign cannot close while the audit reports them as orphaned. A waiver cannot
turn an orphan into PASS.

## 13. Workbench Boundary

Workbench remains the human contract-adjustment surface. This project does not
add new UI controls, but it fixes the accountability rules for later controls:

- Workbench writes patch artifacts; it does not silently modify canonical
  source truth.
- A Workbench patch is a registered deterministic or hybrid capability step.
- Human taste changes require an owner decision/attestation reference.
- Re-render and verify steps receive their own receipts.
- Existing legacy Workbench artifacts remain readable without accountability
  fields.

The next L1 picture-diversity and L3 audio-balance revision can use this chain
as the first real forward test, but their algorithms/UI are separate work.

## 14. Compatibility And Migration

### 14.1 Forward-only rule

- Only new runs with `accountability_contract_version=1` are strict.
- Historical runs, traces, work orders, and Workbench artifacts remain
  readable.
- No old artifact is rewritten or backfilled.
- A legacy run cannot be re-labeled accountable without generating fresh
  version-1 contract and fresh evidence.

### 14.2 Existing surfaces reused

Reuse and extend:

- `video_pipeline_core/skill_tool_contract.py`;
- `video_pipeline_core/capability_catalog.py`;
- `tools/skill_tool_contract_audit.py`;
- `video_pipeline_core/no_skip_execution_trace.py`;
- `tools/no_skip_execution_trace.py`;
- `video_pipeline_core/route_closure_integrity.py`;
- `video_pipeline_core/doc_reference_hygiene.py`;
- `video_tools.py` and the existing command catalog;
- `pipeline_execution_trace.json` and `no_skip_contract_decision.json`.

One new shared core module for trusted single-step execution is allowed. No
second registry, closure engine, or route runner is allowed.

### 14.3 Codebase Memory

After stable entry/Skill/contract changes are committed, refresh Codebase
Memory MCP once. The graph remains an index, not route truth. Temporary run
receipts and candidate media are not indexed as durable project memory.

## 15. Error Handling And Stop-Loss

- Contract hash drift: stop before execution.
- Unknown capability or mismatched tool: reject the step; do not guess.
- Missing dependency receipt: stop the step.
- Process timeout: receipt status UNKNOWN; no automatic retry.
- Output missing or hash mismatch: receipt FAIL.
- Forbidden path or undeclared output change: STRUCTURAL stop.
- Gate writes production truth: gate-purity FAIL.
- Agent attestation missing evidence/blind spots: incomplete agentic step.
- Owner verdict missing: WAITING owner, never PASS.
- Entry anchors conflict: entry audit FAIL; do not start new construction from
  a guessed document.
- The same LOCAL failure class recurring after one correction becomes
  STRUCTURAL and stops the campaign at the last green commit.

## 16. Verification Strategy

### 16.1 Focused static tests

Require tests for:

- exactly one operational entry;
- valid HANDOFF block and existing paths;
- stale/contradictory current states;
- valid Capability execution classes and roles;
- live query fields and deterministic output;
- unowned tool, duplicate ID, broken Director reference, and command mismatch;
- legacy cards/traces remain readable where explicitly supported.

### 16.2 Runtime contract tests

Red-first fixtures must cover at least:

- missing required step;
- duplicate terminal receipt;
- wrong capability command;
- unplanned state-changing step;
- dependency order violation;
- missing output and output hash drift;
- deterministic receipt substituted for agentic attestation;
- agent attestation substituted for owner verdict;
- agent attestation with missing evidence or blind spots;
- self-authored, copied, or unknown gate;
- gate that writes production truth;
- gate that manufactures its own prerequisite;
- WAITING/COMPLETE claim with an unresolved required step;
- approval flags changed without owner evidence;
- strict run carrying only a legacy v1 trace;
- legacy run remaining readable without strict closure claims.

### 16.3 Real forward test

Use a fresh bounded run after the infrastructure is green:

1. freeze a version-1 execution contract;
2. route the existing owner picture-diversity finding to L1;
3. route the existing owner audio-balance finding to L3;
4. run only registered capabilities through the single-step boundary;
5. attach agent evidence and owner verdict where required;
6. run focused verifies and no-skip closure;
7. prove an intentionally skipped step and an intentionally self-authored gate
   fail closed in isolated negative fixtures;
8. stop at owner review without delivery claim.

The forward test proves accountability, not that the creative revisions are
universally good.

### 16.4 Regression boundary

- focused/adjacent tests run per behavior change;
- Workbench compatibility tests and frozen legacy hashes run before closure;
- static orphan/entry audits run on the real repo;
- one full suite runs at the end with an explicit timeout longer than the known
  approximately ten-minute baseline;
- UTF-8, JSON, path, hash, and dirty-tree read-back are required;
- `human_creative_approval=false` and `final_delivery_claimed=false` unless a
  real owner decision explicitly changes them.

## 17. Implementation Units And Ownership

The implementation plan must keep these units independently testable:

1. **Entry contract**
   - repo anchors and document audit only.
2. **Capability schema**
   - execution class/role parsing, validation, catalog, and query only.
3. **Single-step executor**
   - one allow-listed capability command and one receipt; no routing.
4. **Accountable trace closure**
   - execution-contract/trace/attestation/gate validation only.
5. **Forward test**
   - bounded run evidence; no unrelated production refactor.

No unit may own creative taste, final delivery, or automatic loop selection.

## 18. Rollout Order

### Phase A - One entry

- reconcile and commit current authority files intentionally;
- make RUNBOOK the sole operational entry;
- add the HANDOFF state block;
- extend doc hygiene and entry tests;
- remove duplicated volatile state from RUNBOOK and docs INDEX.

### Phase B - Static capability accountability

- add execution class/role to canonical cards;
- extend shared parser/catalog/query/audit;
- keep all 51 current capabilities discoverable and owned.

### Phase C - Forward-only runtime accountability

- add execution contract;
- add the single-step executor and trace v2 receipts;
- extend no-skip closure and gate-purity checks;
- preserve trace v1/legacy reads.

### Phase D - Real bounded forward test

- use the next L1/L3 revision work as the test case;
- produce fresh accountable evidence;
- verify Workbench and legacy compatibility;
- refresh Codebase Memory after stable commits.

Each phase has focused tests and a scoped commit. No phase requires a new
orchestrator or historical migration.

## 19. Acceptance Criteria

The design is implemented only when all are true:

1. An always-loaded agent instruction points to one RUNBOOK.
2. Only RUNBOOK claims operational-entry authority.
3. HANDOFF contains one valid current-state block with existing references.
4. Entry audit fails stale, conflicting, duplicated, or historical-as-current
   routing.
5. All canonical capabilities have valid execution class and role.
6. All current tools/capabilities/commands remain owned, classified, and
   queryable.
7. A strict run cannot execute a mismatched or unknown capability command.
8. Required steps have trace receipts with hashes and declared outputs.
9. Agentic and owner evidence cannot be replaced by deterministic or gate
   output.
10. A gate cannot alter production truth or create its own prerequisite.
11. Missing, stale, copied, skipped, or unplanned evidence blocks closure.
12. Legacy traces and Workbench artifacts remain readable and unchanged.
13. A fresh L1/L3 bounded run reaches the correct owner gate with full
    accountability evidence.
14. The final focused, compatibility, real-audit, integrity, and full-suite
    checks pass.

## 20. Explicit Architecture Rejections

Reject any implementation that:

- creates `entry_v2`, `capability_catalog.json`, a second run registry, or a
  second closure decision engine;
- turns the single-step executor into a route selector;
- lets a gate call hidden helpers to repair its own inputs;
- requires editing every tool to emit receipts;
- backfills historical runs;
- places volatile campaign state in RUNBOOK or docs INDEX;
- treats agent attestation as proof of creative correctness;
- treats objective verification as owner taste;
- auto-retries or auto-promotes delivery;
- expands this project into L1/L3 algorithm or Workbench UI construction.

## 21. Product-Level Outcome

After this design is implemented, a new agent can begin at one visible entry,
recover current state, query the registered factory, execute only authorized
capabilities, leave evidence of every required step, preserve the boundary
between tool/agent/gate/owner work, and fail closed when anything is skipped or
fabricated.

The system still permits failure, uncertainty, owner revision, and creative
disagreement. What it no longer permits is an unsupported completion claim.
