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
  -> immutable tool receipts + typed actor decision sidecars
  -> pipeline_execution_trace.json (derived aggregate)
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
10. Apply the contract only to new runs with a committed version-1 execution
    companion.
11. Remove mechanisms made redundant by this project when evidence proves they
    have no live consumer and no required legacy-reader duty; quarantine
    misleading-but-required compatibility surfaces as explicit read-only
    legacy instead of leaving them apparently active.

## 4. Non-Goals

- No historical artifact backfill.
- No deletion or mass rewrite of historical work orders or evidence.
- No repository-wide speculative dead-code cleanup. Retirement is limited to
  surfaces touched or made redundant by this project and requires the evidence
  contract in section 12.
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

Authority is declared with exact markers, not inferred from prose:

```text
AGENTS.md:                         <!-- OPERATIONAL_ENTRY_POINTER: RUNBOOK.md -->
RUNBOOK.md:                        <!-- OPERATIONAL_ENTRY: RUNBOOK -->
RUNBOOK.md:                        <!-- CURRENT_HANDOFF_POINTER: HANDOFF_CURRENT.md -->
HANDOFF_CURRENT.md:                <!-- DOCUMENT_ROLE: CURRENT_HANDOFF -->
docs/START_HERE_VIDEO_PIPELINE.md: <!-- DOCUMENT_ROLE: ORIENTATION -->
docs/INDEX.md:                     <!-- DOCUMENT_ROLE: MAP -->
```

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
  "state": "IDLE | WAITING_* | STOPPED_* | ACTIVE",
  "active_work_order": "repo-relative path or null",
  "active_spec": "repo-relative path or null",
  "active_skill": "repo-relative path or null",
  "active_run_root": "repo-relative path or null",
  "authoritative_state_artifact": "repo-relative JSON path or null",
  "authoritative_state_field": "state or null",
  "next_actions": ["bounded actions"],
  "do_not_do": ["explicit prohibitions"],
  "human_creative_approval": false,
  "final_delivery_claimed": false
}
<!-- HANDOFF_STATE_END -->
```

There is no second current-state JSON file. The block is the machine-readable
pointer carried by the existing handoff document. It does not compete with a
campaign packet for state authority:

- when a run is active, `authoritative_state_artifact` must name one
  machine-readable JSON artifact and `state` must equal the exact string at
  `authoritative_state_field` in that artifact;
- `active_work_order` is the only definition of which work order is current;
- when no run is active, `state` is `IDLE`, all active paths and the state
  artifact/field are null, and no campaign packet is inferred;
- Markdown reports and historical campaign status files may be linked as
  evidence, but cannot be the authoritative state artifact.

### 5.4 Entry audit

Extend the existing document/reference hygiene surface. Its entry-mode scan is
bounded to `AGENTS.md`, `RUNBOOK.md`, `HANDOFF_CURRENT.md`,
`docs/START_HERE_VIDEO_PIPELINE.md`, and `docs/INDEX.md`. It parses exact
markers and machine keys; it does not guess whether prose sounds authoritative.

The entry audit fails when:

- any required marker above is missing, duplicated, has a different value, or
  appears on a different scanned surface;
- any scanned file other than HANDOFF contains the machine key
  `active_work_order`, `authoritative_state_artifact`, or an
  `ACTIVE_WORK_ORDER` marker;
- `RUNBOOK.md` contains a state token matching
  `\b(?:WAITING|STOPPED|ACTIVE)(?:_[A-Z0-9]+)+\b`;
- the HANDOFF block is missing, duplicated, invalid JSON, or invalid UTF-8;
- a non-null HANDOFF path does not exist;
- an active HANDOFF lacks an authoritative JSON state artifact/field;
- the HANDOFF state differs from the exact authoritative JSON field;
- an `IDLE` HANDOFF retains an active path or state authority;
- HANDOFF contains an unknown machine key or a state outside its declared
  grammar.

START_HERE and `docs/INDEX.md` may link historical work orders as orientation
or map content. Without the HANDOFF machine key/marker those links have no
current authority and are not semantically interpreted by the audit.

The audit extends `doc_reference_hygiene`; it does not create a new entry
registry.

## 6. Capability Actor And Role Contract

Every canonical Capability Card gains two required fields for forward-only
accountability:

```json
{
  "execution_class": "deterministic | hybrid",
  "capability_role": "operation | review | gate | adapter"
}
```

Definitions:

| execution class | Required evidence |
| --- | --- |
| `deterministic` | Trusted single-step execution receipt. |
| `hybrid` | Trusted single-step execution receipt plus a contract-bound agent attestation. |

Agent and owner are decision actors, not pretend tool capabilities. They are
declared in work-order `decision_requirements` and produce attestations or
verdicts; they do not need fake `TOOL_CONTRACT.tool` commands or tool receipts.

Roles are orthogonal:

- `operation`: changes an authorized run artifact.
- `review`: reads evidence and proposes findings or decisions.
- `gate`: reads evidence and returns PASS/FAIL/UNKNOWN plus findings.
- `adapter`: deterministic format conversion without route or taste judgment.

Allowed class/role combinations are explicit:

| role | allowed execution class | State-changing boundary |
| --- | --- | --- |
| `operation` | deterministic or hybrid | Only the registered tool may change production truth. |
| `review` | deterministic or hybrid | Tool writes review evidence; hybrid agent writes only an attestation sidecar. |
| `gate` | deterministic or hybrid | Tool writes gate report/findings; hybrid agent writes only an attestation sidecar. |
| `adapter` | deterministic only | Tool performs format conversion only. |

Neither agent attestation nor owner verdict may write production truth. Any
accepted change to timeline, media, subtitles, maps, mix plans, or effects must
be applied by a registered `operation` capability in a later executable step.

The existing Skill `TOOL_CONTRACT` `tool` value remains the stored command
authority. The live catalog derives a normalized `command` from that value and
exposes it with the two new fields; Domain Skills do not store a duplicate
command field:

```json
{
  "command": "video_tools.py material-rough-cut",
  "execution_class": "hybrid",
  "capability_role": "operation"
}
```

For commands dispatched through `video_tools.py`, the registered subcommand is
part of identity. Matching `video_tools.py` while invoking another subcommand
is a mismatch. Static audit fails an unknown or missing value, a missing live
`command`, or disagreement between the normalized Skill `tool` and command
catalog.

## 7. Forward-Only Work-Order Execution Contract

### 7.1 Opt-in boundary

A strict run is activated by exactly one source: a committed machine companion
next to its formal work order:

```text
docs/construction-guides/work-orders/<work-order-id>.execution.json
```

That document contains:

```json
{
  "accountability_contract_version": 1
}
```

The integrator commits the companion before dispatch. That committed path is
authoritative everywhere; no run-root copy is created. The execution trace
repeats the version, source path, source commit, and contract hash only as
observed evidence; it never activates strict mode.

The committed `run_root` is also an activation key. Both executor and closure
scan tracked companions and normalize their `run_root`; if one companion names
the requested run, that run is strict even when a caller omits a CLI contract
argument. Zero matching companions permits legacy only when the run contains
no accountability control root, reference, reservation, receipt, or version-2
trace. More than one match is an activation conflict.

The rules are deterministic:

- no committed companion means legacy behavior;
- a committed companion with supported version 1 means strict behavior;
- duplicate companions, conflicting versions, malformed JSON, an unsupported
  version, dirty working-copy drift at that path, or a worker-authored
  uncommitted companion is `STOPPED_CONTRACT_ACTIVATION_INVALID`;
- an activation error never falls back to legacy behavior;
- changing the committed companion requires an integrator-authored amendment
  commit and a fresh run; a worker cannot amend an active contract.

Duplicate/conflict detection scans only tracked files returned by:

```text
git ls-files docs/construction-guides/work-orders/*.execution.json
```

After parsing, companions are grouped by exact `work_order_id` and normalized
`work_order_path`. More than one current-tree file in either group is a
duplicate. Different `accountability_contract_version` values within a group
are conflicting versions. An unsupported version at the explicitly invoked
companion path is invalid; malformed or unsupported unrelated companions fail
the static contract audit but do not ambiguously activate another run. The
invoked companion path must itself be one unique tracked group member.

### 7.2 Execution contract

Before a worker mutates an owner zone, the integrator freezes expected truth in
the committed execution companion:

```json
{
  "artifact_role": "work_order_execution_contract",
  "version": 1,
  "accountability_contract_version": 1,
  "work_order_id": "stable ID",
  "work_order_path": "repo-relative path",
  "work_order_sha256": "SHA-256",
  "run_root": ".tmp/accountability_run",
  "accountability_root": ".tmp/accountability_run/accountability",
  "initial_run_root_manifest": [],
  "initial_owner_zone_manifest": [],
  "steps": [
    {
      "step_id": "L1.picture.revise",
      "loop": "L1",
      "capability_id": "cap.material-map.material-rough-cut.v1",
      "depends_on": [],
      "command_argv": [
        "{python}",
        "tools/material_rough_cut.py",
        "--contract",
        ".tmp/accountability_fixture/segment_contract.json",
        "--project-map",
        ".tmp/accountability_fixture/project_material_map.json",
        "--out",
        ".tmp/accountability_run/rough_cut_plan.json"
      ],
      "timeout_ms": 120000,
      "inputs": [
        {"path": "repo-relative path", "sha256": "SHA-256"}
      ],
      "required_outputs": ["repo-relative paths"],
      "required_verifier_step_ids": ["verify.picture.rendered"],
      "max_attempts": 1,
      "allowed_retry_failure_classes": []
    }
  ],
  "decision_requirements": [
    {
      "requirement_id": "review.L1.picture.revise",
      "actor_class": "agent",
      "depends_on_step_ids": ["L1.picture.revise"],
      "evidence_path": ".tmp/accountability_run/accountability/attestations/L1.picture.revise.json",
      "missing_state": "UNKNOWN_AGENT_EVIDENCE"
    },
    {
      "requirement_id": "owner.final",
      "actor_class": "owner",
      "depends_on_step_ids": ["L1.picture.revise"],
      "evidence_path": ".tmp/accountability_run/accountability/verdicts/owner.final.json",
      "missing_state": "WAITING_OWNER_FINAL_VERDICT"
    }
  ],
  "allowed_owner_zones": [
    {"path": "repo-relative directory", "match": "directory_prefix"}
  ],
  "forbidden_paths": [
    {"path": "repo-relative path", "match": "exact"}
  ],
  "protected_paths": [
    {"path": "repo-relative read-only path", "sha256": "SHA-256"}
  ],
  "human_creative_approval": false,
  "final_delivery_claimed": false
}
```

`{python}` is the sole environment placeholder. At execution it resolves to
the current `sys.executable`; every repo tool path and `video_tools.py`
subcommand must match literally after normalization. No other argv field is
worker-selectable.

The contract is expected truth, not observed evidence and not a second product
spec. A step freezes its command, timeout, inputs, outputs, verifier step IDs,
dependencies, attempt bound, and owner requirement.
`required_verifier_step_ids` always references contract step IDs, never
capability IDs.

Every capability step has non-null argv/timeout/max-attempts and a tool
receipt. A hybrid step must have exactly one agent decision requirement that
depends on its step ID. Owner requirements may depend on one or more executable
steps but do not alter their capability class. Decision requirement IDs and
evidence paths are unique; agent requirements use `UNKNOWN_AGENT_EVIDENCE`
when absent, while owner requirements use an explicit `WAITING_OWNER_*` state.

`allowed_retry_failure_classes` defaults to empty and may contain only
enumerated `LOCAL_*` classes. Structural failures and STOPPED outcomes are
never retryable.

The initial run-root and owner-zone manifests are complete expected state. The
run root is usually empty; existing dirty owner-zone files are named and
hashed. Undeclared pre-existing files or a baseline mismatch make activation
fail.

`protected_paths` freezes read-only compatibility/fixture files that are not
owner zones. The executor verifies them before the first step and the closure
meta-gate verifies them again at final seal; any drift is structural.

`accountability_root` is a reserved control subtree excluded from production
state manifests. Policy reserves receipts to the executor, exact
attestation/verdict paths to the declared decision actors, and exact
trace/decision/report paths to the closure meta-gate. Enforcement proves that
the wrapped tool did not write decision sidecars and validates every
control-subtree path/schema separately; any extra file is a failure. It does
not cryptographically prove the human or agent identity behind a valid
sidecar.

### 7.3 Canonical path and hash rules

Every contract and evidence path uses repo-relative POSIX spelling:

- reject absolute paths, drive letters, UNC paths, backslashes, empty
  components, and `..`;
- resolve the path and require it to remain inside the repository root;
- reject a symlink, junction, or other reparse-point traversal that escapes
  the repository;
- on Windows, compare containment and equality case-insensitively while
  preserving the canonical POSIX spelling in artifacts;
- owner-zone entries use only `exact` or `directory_prefix`; glob patterns are
  not accepted;
- deleted paths appear in changed-path evidence with `sha256: null` and
  `state: "deleted"` rather than disappearing from the manifest.

Canonical JSON hashing is UTF-8 over JSON serialized with sorted keys,
`ensure_ascii=false`, separators `(',', ':')`, and LF line ending, excluding
only the artifact's declared self-hash field. Hashes prove content consistency,
not author identity or resistance to a malicious process.

### 7.4 Plan completeness

The execution contract describes only required accountable steps, not every
read-only shell inspection. A required step must be a registered capability.
Diagnostic reads may remain unplanned when they do not write state or make a
closure claim.

The git commit is the external trust anchor for expected truth. The executor
resolves `contract_source_commit` as the latest commit returned by
`git rev-list -1 HEAD -- <companion-path>`, requires `git show
<contract_source_commit>:<companion-path>` to equal both index and working-copy
bytes, and records that commit in the receipt/trace. An untracked, staged-only,
or dirty companion is invalid. The companion does not contain its own commit
SHA, avoiding a self-referential hash. `agent_run_id` remains a claimed runtime
identifier unless the dispatch runtime itself supplies a stronger signed
identity.

## 8. Trusted Single-Step Capability Execution

### 8.1 Thin boundary

Add one command to the existing `video_tools.py` surface:

```text
capability-run
```

It is a single-step executor, not a router:

- `--initialize --contract <committed companion>` verifies activation,
  baseline/protected hashes, and an empty reserved control root, then writes
  exactly one immutable contract reference before any capability may run;
- accepts one committed execution contract and one step ID;
- resolves the step's Capability Card from the live catalog;
- materializes the frozen `command_argv`, replacing only `{python}`;
- verifies the exact registered repo tool and, where applicable, exact
  `video_tools.py` subcommand;
- rejects shell strings and executes with an argv list and no shell;
- verifies dependency receipts and frozen input hashes before execution;
- snapshots the monitored repository owner zones and run root before and after;
- snapshots the reserved accountability subtree immediately after its own
  reservation and immediately after the child exits, before writing a receipt;
- executes exactly one command from the repository working directory;
- records exit code, duration, declared output hashes, changed paths, and
  manifest-chain references;
- does not choose a next capability;
- does not retry automatically;
- does not transform FAIL into PASS;
- does not mutate the work-order contract.

The implementation lives in one shared core module and one existing
`video_tools.py` command. No per-tool receipt code is required.

Initialization generates a random UUID `run_instance_id` and writes:

```json
{
  "artifact_role": "accountability_contract_reference",
  "version": 1,
  "run_instance_id": "UUIDv4",
  "run_root": ".tmp/accountability_run",
  "contract_path": "docs/construction-guides/work-orders/example.execution.json",
  "contract_sha256": "SHA-256",
  "contract_source_commit": "full git SHA",
  "initialized_at": "RFC3339"
}
```

The file lives at `<accountability-root>/contract_reference.json`, uses
exclusive creation, and is never edited. Every reservation, receipt,
attestation, verdict, trace, and closure decision must repeat its
`run_instance_id` and contract hash. A normal step refuses to run before this
reference exists and matches the invoked companion.

### 8.2 Command matching

The Python executable may vary only through `{python}`. The repo-relative tool,
subcommand, and remaining argv are frozen by the contract. A worker cannot
declare one capability and run another command or vary arguments at dispatch.

### 8.3 Immutable attempts and receipts

Execution is sequential. Strict runs prohibit parallel accountable steps and
concurrent writers. This removes the need for a lock service and makes attempt
order auditable.

Each invocation writes exactly one immutable receipt:

```text
<accountability-root>/receipts/<step-id>/attempt-<N>.json
```

Before launching the state-changing command, the executor atomically creates
an immutable exclusive reservation:

```text
<accountability-root>/reservations/<step-id>/attempt-<N>.json
```

The reservation binds contract hash, step, attempt, argv hash, process ID, and
start time. Exclusive creation must succeed before the child process starts;
a second invocation therefore fails before production side effects. A stale
reservation without a receipt is UNKNOWN and non-retryable in the same run.

The child-process accountability-subtree snapshots must be identical. Thus the
registered tool cannot create the exact declared attestation/verdict path (or
any other control artifact) and have it mistaken for later actor evidence. The
executor's reservation and later receipt are the only expected executor writes.
An attestation still carries a claimed agent identity rather than cryptographic
identity proof; the enforceable claim is that it was not created by the wrapped
deterministic child process.

Rules:

- attempts start at 1, are consecutive, and cannot exceed `max_attempts`;
- the executor writes a temporary file, fsyncs it where supported, then uses an
  atomic non-overwriting create/rename into a path that must not already exist;
- an existing attempt path, missing prior attempt, or evidence of concurrent
  invocation fails the step and closure;
- a later attempt is permitted only when the previous receipt is FAIL or
  UNKNOWN, its `failure_class` is explicitly listed in
  `allowed_retry_failure_classes`, `retryable=true` is derived from that
  contract list, and attempt capacity remains;
- STOPPED, STRUCTURAL, forbidden-path, concurrency, and stale-reservation
  outcomes cannot be superseded in the same run;
- no reservation or receipt is edited or deleted;
- a PASS attempt is terminal and cannot be superseded;
- the final status for a step is its latest legal receipt.

Each receipt contains observed evidence, including exact argv, input/output
hashes, changed paths, timestamps, exit code, status, and pre/post monitored
manifest hashes, `failure_class`, and contract-derived `retryable`. Receipts
cover registered tool execution only. They do not pretend that a later agent
or owner decision already existed.

For a hybrid step, the immutable tool receipt is written first; the agent then
writes the separately declared decision-requirement attestation. Owner verdicts
are likewise separate. Closure binds tool entries and decision entries without
a mutable pending receipt or second sealing command.

`pipeline_execution_trace.json` becomes a derived version-2 aggregate rather
than a mutable journal:

```json
{
  "artifact_role": "pipeline_execution_trace",
  "version": 2,
  "accountability_contract_version": 1,
  "run_instance_id": "UUID from contract_reference.json",
  "work_order_execution_contract": "docs/construction-guides/work-orders/example.execution.json",
  "work_order_execution_contract_sha256": "SHA-256",
  "tool_entries": [
    {
      "step_id": "L1.picture.revise",
      "capability_id": "cap.material-map.material-rough-cut.v1",
      "attempt": 1,
      "receipt_path": ".tmp/accountability_run/accountability/receipts/L1.picture.revise/attempt-1.json",
      "receipt_sha256": "SHA-256",
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
  "decision_entries": [
    {
      "requirement_id": "review.L1.picture.revise",
      "actor_class": "agent",
      "depends_on_step_ids": ["L1.picture.revise"],
      "dependency_receipt_hashes": {"L1.picture.revise": "SHA-256"},
      "evidence_path": ".tmp/accountability_run/accountability/attestations/L1.picture.revise.json",
      "evidence_sha256": "SHA-256",
      "status": "present | missing | invalid"
    },
    {
      "requirement_id": "owner.final",
      "actor_class": "owner",
      "depends_on_step_ids": ["L1.picture.revise"],
      "dependency_receipt_hashes": {"L1.picture.revise": "SHA-256"},
      "evidence_path": ".tmp/accountability_run/accountability/verdicts/owner.final.json",
      "evidence_sha256": null,
      "status": "present | missing | invalid"
    }
  ],
  "human_creative_approval": false,
  "final_delivery_claimed": false
}
```

The aggregate is created only during closure sealing from the committed
contract, immutable receipts, attestations, verdicts, and live Capability
Catalog. Execution class and capability role are derived from the catalog; a
receipt cannot redefine them. `tool_entries` contains only executable steps;
`decision_entries` contains no receipt fields. Version-1 traces remain
readable and keep their existing meaning, but cannot satisfy a strict contract.

For monitored production state, closure excludes the reserved accountability
subtree, requires the contract's initial run-root and owner-zone manifests to
match the first executable step's pre-manifest, and requires each executable
step's post-manifest to match the next executable step's pre-manifest. It then
audits every reserved control artifact independently. Any other gap is
observable unplanned state change.

## 9. Agent Attestation And Owner Verdict

### 9.1 Agent attestation

Agent cognition cannot be proven cryptographically. The enforceable promise is
only that an agent decision claim must be evidence-bearing and
content-consistent.

A hybrid capability step's agent decision requirement references an
attestation artifact:

```json
{
  "artifact_role": "agent_attestation",
  "version": 1,
  "run_instance_id": "UUID from contract_reference.json",
  "execution_contract_path": "repo-relative committed companion path",
  "execution_contract_sha256": "SHA-256",
  "requirement_id": "review.L1.picture.revise",
  "step_id": "L1.picture.revise",
  "capability_id": "registered capability ID",
  "actor_type": "agent",
  "agent_run_id": "runtime/session identifier",
  "model": null,
  "reviewed_evidence": [
    {"path": "repo-relative path", "sha256": "SHA-256", "locator": "time/cell/check"}
  ],
  "dependency_receipts": [
    {
      "step_id": "L1.picture.revise",
      "path": "repo-relative receipt path",
      "sha256": "SHA-256",
      "completed_at": "RFC3339"
    }
  ],
  "judgment": "bounded conclusion",
  "blind_spots": ["explicit limitations"],
  "proposed_findings": ["finding artifact IDs or paths"],
  "attested_at": "RFC3339"
}
```

The model field is optional and may be populated only when the runtime proves
the selected model. Closure computes and records the whole-file content hash;
it detects drift but does not authenticate who authored it. A prose statement
such as "reviewed" without evidence, judgment, blind spots, and evidence hashes
does not satisfy the requirement.

### 9.2 Owner verdict

Owner decision requirements reference an existing explicit owner decision
artifact. The trace binds requirement ID, path, and hash; the accountability
layer does not invent a new creative-verdict system.

The minimum owner sidecar is:

```json
{
  "artifact_role": "owner_decision",
  "version": 1,
  "run_instance_id": "UUID from contract_reference.json",
  "execution_contract_path": "repo-relative committed companion path",
  "execution_contract_sha256": "SHA-256",
  "requirement_id": "owner.final",
  "dependency_receipts": [
    {
      "step_id": "L1.picture.revise",
      "path": "repo-relative receipt path",
      "sha256": "SHA-256",
      "completed_at": "RFC3339"
    }
  ],
  "scope": "bounded decision scope",
  "decision": "approve | revise | reject | delegate",
  "evidence_refs": [
    {"path": "repo-relative evidence path", "sha256": "SHA-256", "locator": "time/cell/check"}
  ],
  "verbatim_owner_text": "owner-provided wording",
  "decided_at": "RFC3339 after every dependency receipt"
}
```

An owner decision must state the bounded scope and one of approve, revise,
reject, or delegate. Owner silence is never approval. Tool or agent output
cannot set `human_creative_approval=true` or `final_delivery_claimed=true`.

For both sidecar types, closure requires exact contract path/hash and
`run_instance_id`, an exact dependency receipt set matching the requirement,
receipt hashes that read back, and `attested_at`/`decided_at` later than every
dependency `completed_at`. The sidecar path must be absent at initialization
and during wrapped tool execution. A copied prior-run or pre-existing sidecar
is invalid even when requirement IDs happen to match.

### 9.3 Actor substitution rules

- A deterministic receipt cannot satisfy an agent decision requirement.
- Agent attestation cannot satisfy an owner decision requirement.
- Gate PASS cannot satisfy a missing operation, review, or owner verdict.
- A hybrid step is complete only when every declared evidence part exists.
- An agent may propose findings but may not convert taste to objective PASS.

## 10. Gate Purity

This design enforces observable final-state purity inside monitored repository
and run-root paths plus registered command provenance. It does not claim to
detect a write that is restored before the after-snapshot, a write outside the
monitored roots, or a hidden child-process side effect. Preventing those
requires an OS sandbox and is explicitly outside this project.

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

`capability-run` records the exact argv and before/after manifests for the run
root and allowed repository owner zones. Commands are allow-listed, run from
the repository root, and invoked without a shell. For a gate, final changed
paths must be a subset of the card's declared outputs. A production-truth or
media write makes the gate receipt FAIL even when the process exits zero. This
boundary relies on reviewed canonical gate code; it is not a hostile-process
sandbox.

The existing gate-authenticity classifications remain authoritative:

- `pipeline_tool_generated` may be accepted;
- `run_local_worker_generated`, `copied_from_prior`, and unknown authenticity
  block closure.

## 11. Fail-Closed Closure

Extend `no_skip_execution_trace` rather than creating another closure engine.

Closure is a two-phase meta-gate outside the work-order step list:

1. every capability step finishes through `capability-run` and leaves an
   immutable tool receipt; declared agent/owner decision requirements leave
   their separate evidence artifacts;
2. `no_skip_execution_trace` reads the committed contract, receipts,
   attestations, owner verdicts, and live catalog, then writes the derived
   `pipeline_execution_trace.json` and `no_skip_contract_decision.json`.

For strict runs the closure CLI accepts and the pinned workflow always passes
`--contract <committed companion>`. Independently, closure scans tracked
companions for a normalized `run_root` match. A matching companion or any
accountability control artifact activates strict validation; omitting
`--contract`, omitting/mismatching `contract_reference.json`, or supplying a
different companion is `STOPPED_CONTRACT_ACTIVATION_INVALID`, never legacy
fallback.

Before writing those control artifacts, the meta-gate captures a final
production-state manifest. It must equal the last executable step's
post-manifest, or the committed initial manifest when no executable step
exists. Thus writes before the first step, between steps, and after the last
step are checked by one continuous baseline/pre/post/final chain.

The meta-gate has no receipt requirement and cannot consume its own decision as
evidence. This is the only hard-coded exception; it avoids a self-referential
closure step.

When `accountability_contract_version=1`, closure verifies:

1. unique run-root companion resolution plus contract-reference
   path/hash/source-commit/run-instance binding, execution-contract hash, and
   work-order hash;
2. every required capability step has a legal consecutive attempt chain within
   its bound and one derived terminal tool status;
3. every executable attempt has one prior exclusive reservation and no stale,
   duplicate, or concurrent reservation;
4. all dependency ordering constraints;
5. capability ID resolves in the live catalog;
6. command/tool matches the capability;
7. execution class and role derived from the live catalog require the correct
   tool receipt and, for hybrid steps, the bound agent decision requirement;
8. exit/status/failure-class/retry consistency;
9. required output existence and hashes;
10. required verifier evidence and refs;
11. owner-zone and forbidden-path compliance;
12. the baseline/pre/post/final manifest chain has no observable unplanned
    state-changing capability execution in monitored
    roots;
13. agent-attestation contract/run/receipt/timestamp completeness and hashes;
14. owner-verdict contract/run/receipt/timestamp binding when required;
15. gate purity and gate authenticity;
16. state legality and approval flags.

Legal outcomes:

- all objective steps green, owner still required -> `WAITING_OWNER_*`;
- all required objective and owner evidence green -> bounded `PASS` or next
  declared state;
- a required step failed -> `STOPPED_<STEP>_<FAILURE_CLASS>`;
- evidence is missing or unverifiable -> `UNKNOWN` or `STOPPED_*_UNKNOWN`;
- no path may claim COMPLETE solely because a narrative report says so.

The closure meta-gate may write only the derived trace,
`no_skip_contract_decision.json`, and its declared audit report.

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

### 12.1 Evidence-based retirement of obsolete or misleading surfaces

This project may delete an old mechanism instead of preserving it indefinitely
when the new entry/accountability path makes it redundant. Deletion is not
authorized by age, naming, or intuition. Every touched candidate receives one
of three outcomes:

| outcome | Required condition |
| --- | --- |
| `delete` | No live code/command/Skill/doc consumer, no active Capability or Director reference, no required legacy-reader duty, and focused tests stay green after removal. |
| `legacy_read_only` | New runs must not produce or route through it, but historical artifacts still require it for reading or validation. It is marked `legacy`, removed from active consumer lookup, and cannot satisfy strict closure. |
| `keep` | At least one named live consumer, public compatibility duty, or unresolved dynamic use remains. The evidence names it; uncertainty never authorizes deletion. |

The retirement audit is bounded to surfaces modified, replaced, or made
redundant by Phases A-C. For each candidate it checks:

1. Codebase Memory callers/callees where indexed, plus `rg` for CLI strings,
   dynamic imports, configuration, error literals, and non-code references.
2. Skill `TOOL_CONTRACT`, Capability Catalog, command catalog, Director
   consumer blocks, Skill index, and branch/owner registration.
3. RUNBOOK/HANDOFF/START_HERE/docs INDEX and active work orders/specs.
4. Focused tests, integration fixtures, Workbench readers, and legacy artifact
   validation paths.
5. Whether historical data needs a reader even though new production is
   forbidden.

Removal is atomic: code/command registration, active documentation, ownership,
tests, and replacement references change in the same scoped commit. It may not
leave a silent alias, compatibility shim, stale next action, dead Capability
ID, or old entry marker that makes the removed path appear usable. Git history
is the archive; this design does not create a tombstone registry.

The implementation report contains a compact retirement table with candidate,
outcome, live-consumer evidence, legacy-reader evidence, changed paths, and
verification. `UNKNOWN` results in `keep`, not deletion.

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

- Only new runs with a valid committed version-1 execution companion are
  strict.
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

- Missing, malformed, duplicate, conflicting, unsupported, or uncommitted
  strict contract: `STOPPED_CONTRACT_ACTIVATION_INVALID` without legacy
  fallback.
- Contract or input hash drift: stop before execution.
- Missing/mismatched contract reference, run-instance ID, or strict closure
  `--contract`: activation stop with no legacy fallback.
- Unknown capability or mismatched tool: reject the step; do not guess.
- Missing dependency receipt: stop the step.
- Duplicate, non-consecutive, over-bound, or concurrent attempt: structural
  stop.
- Process timeout: receipt status UNKNOWN; another attempt requires remaining
  contract allowance, a matching allowed `LOCAL_*` failure class, and explicit
  worker invocation.
- Output missing or hash mismatch: receipt FAIL.
- Forbidden path or undeclared output change: STRUCTURAL stop.
- Gate writes production truth: gate-purity FAIL.
- Agent attestation missing evidence/blind spots: incomplete agent decision
  requirement.
- Decision sidecar contract/run/receipt/timestamp mismatch: stale or copied
  evidence failure.
- Owner verdict missing: WAITING owner, never PASS.
- Entry anchors conflict: entry audit FAIL; do not start new construction from
  a guessed document.
- The same LOCAL failure class recurring after one correction becomes
  STRUCTURAL and stops the campaign at the last green commit.

## 16. Verification Strategy

All acceptance evidence is written under:

```text
.tmp/single_entry_forward_accountability_acceptance/**
```

### 16.1 Focused static tests

Require tests for:

- exactly one operational entry;
- valid HANDOFF block and existing paths;
- stale/contradictory current states;
- valid Capability execution classes and roles;
- live query fields and deterministic output;
- unowned tool, duplicate ID, broken Director reference, and command mismatch;
- an active reference to a deleted/legacy-only surface, a retired command still
  exposed by the command catalog, and a misleading old entry marker;
- retirement classification that attempts `delete` with a live consumer,
  required legacy reader, or UNKNOWN evidence;
- legacy cards/traces remain readable where explicitly supported.

Pinned command:

```powershell
C:/Users/user/miniconda3/python.exe -m unittest tests.test_pipeline_skill_boundaries tests.test_doc_reference_hygiene tests.test_interactive_skill_flow_docs tests.test_skill_index tests.test_accountability_retirement -v
```

Capability schema/catalog command:

```powershell
C:/Users/user/miniconda3/python.exe -m unittest tests.test_skill_tool_contract_parser tests.test_skill_tool_contracts tests.test_dispatch_capabilities tests.test_video_tools_command_catalog -v
```

### 16.2 Runtime contract tests

Red-first fixtures must cover at least:

- missing, duplicate, malformed, unsupported, and conflicting strict-version
  activation;
- missing required step;
- duplicate, non-consecutive, over-bound, and concurrent attempt receipts;
- stale reservation and forbidden retry of STOPPED/STRUCTURAL outcomes;
- allowed retry of one explicitly listed LOCAL FAIL/UNKNOWN outcome;
- wrong tool and wrong `video_tools.py` subcommand;
- unplanned state-changing step;
- dependency order violation;
- absolute, backslash, `..`, case-collision, and junction-escape paths;
- missing output and output hash drift;
- deterministic receipt substituted for an agent decision requirement;
- agent attestation substituted for owner verdict;
- agent attestation with missing evidence or blind spots;
- stale/copied agent or owner sidecar, wrong run-instance ID, wrong contract
  hash, wrong dependency receipt hash, or pre-dependency decision timestamp;
- self-authored, copied, or unknown gate;
- gate that writes production truth;
- gate that manufactures its own prerequisite;
- WAITING/COMPLETE claim with an unresolved required step;
- approval flags changed without owner evidence;
- closure attempting to require or consume its own receipt/decision;
- strict run carrying only a legacy v1 trace;
- legacy run remaining readable without strict closure claims.

Pinned command after the new test modules exist:

```powershell
C:/Users/user/miniconda3/python.exe -m unittest tests.test_capability_execution_contract tests.test_capability_execution_receipts tests.test_accountability_path_rules tests.test_no_skip_execution_trace tests.test_route_closure_integrity -v
```

### 16.3 Real forward test

Use a fresh bounded technical run after the infrastructure is green:

Committed fixture and contract paths are fixed before Phase D:

```text
tests/fixtures/accountability_forward_v1/fixture_manifest.json
tests/fixtures/accountability_forward_v1/material/segment_contract.json
tests/fixtures/accountability_forward_v1/material/project_material_map.json
tests/fixtures/accountability_forward_v1/audio/audio_mix_plan.json
tests/fixtures/accountability_forward_v1/audio/audio_handoff_acceptance.json
tests/fixtures/accountability_forward_v1/audio/source_speech.wav
tests/fixtures/accountability_forward_v1/audio/background_music.wav
docs/construction-guides/work-orders/2026-07-13-single-entry-forward-accountability-acceptance.execution.json
```

The fixture manifest contains canonical SHA-256 for every fixture file. The
WAVs are short deterministic test assets with no delivery or rights claim. The
execution companion fixes run root to
`.tmp/single_entry_forward_accountability_acceptance/forward` and defines the
two capability steps plus one agent technical-review decision requirement and
one owner decision requirement.

1. freeze a version-1 execution contract;
2. invoke the existing `material-rough-cut` and
   `audio-mix-plan-execute` capabilities against frozen accepted fixtures;
3. run only registered capabilities through the single-step boundary;
4. attach technical agent attestation where the contract requires it;
5. seal the run through no-skip closure;
6. prove that an owner-required fixture legally ends at `WAITING_OWNER_*`
   without creative approval or delivery claim;
7. prove an intentionally skipped step and an intentionally self-authored gate
   fail closed in isolated negative fixtures;
8. preserve frozen fixture and Workbench production-path hashes.

Exact forward commands and expected results:

```powershell
C:/Users/user/miniconda3/python.exe video_tools.py capability-run --initialize --contract docs/construction-guides/work-orders/2026-07-13-single-entry-forward-accountability-acceptance.execution.json --json
C:/Users/user/miniconda3/python.exe video_tools.py capability-run --contract docs/construction-guides/work-orders/2026-07-13-single-entry-forward-accountability-acceptance.execution.json --step-id fixture.material-rough-cut --json
C:/Users/user/miniconda3/python.exe video_tools.py capability-run --contract docs/construction-guides/work-orders/2026-07-13-single-entry-forward-accountability-acceptance.execution.json --step-id fixture.audio-mix-plan-execute --json
C:/Users/user/miniconda3/python.exe tools/no_skip_execution_trace.py --contract docs/construction-guides/work-orders/2026-07-13-single-entry-forward-accountability-acceptance.execution.json --run .tmp/single_entry_forward_accountability_acceptance/forward --out-dir .tmp/single_entry_forward_accountability_acceptance/forward/accountability --json
```

Initialization exits 0 and creates one immutable contract reference. Both
capability commands exit 0 with a PASS tool receipt. After the evidence
worker writes the declared technical attestation, no-skip exits 0 with
`ok=true`, state `WAITING_OWNER_ACCOUNTABILITY_FIXTURE`,
`human_creative_approval=false`, and `final_delivery_claimed=false`. The owner
fixture is deliberately left undecided; that WAITING state is the successful
infrastructure result.

The technical attestation procedure is exact:

1. after both PASS receipts exist, the evidence worker reads the material
   rough-cut output, audio-mix report, both receipts, and their hashes;
2. it copies `run_instance_id` and execution-contract path/hash from the
   contract reference, binds both dependency receipt path/hash/completion
   records, and writes only
   `.tmp/single_entry_forward_accountability_acceptance/forward/accountability/attestations/fixture.technical-review.json`
   with the section-9 schema, requirement ID `fixture.technical-review`, both
   reviewed evidence locators, bounded judgment, and non-empty blind spots;
3. it parses the file with:

```powershell
C:/Users/user/miniconda3/python.exe -m json.tool .tmp/single_entry_forward_accountability_acceptance/forward/accountability/attestations/fixture.technical-review.json
```

   Expected exit is 0. The no-skip meta-gate computes and binds the file hash;
   the worker does not self-certify its identity or creative correctness.

Four committed negative unit fixtures are required:

```text
tests/fixtures/accountability_forward_v1/negative/missing-step
tests/fixtures/accountability_forward_v1/negative/self-authored-gate
tests/fixtures/accountability_forward_v1/negative/stale-agent-sidecar
tests/fixtures/accountability_forward_v1/negative/copied-owner-sidecar
```

They run through the pure closure evaluator in one pinned command:

```powershell
C:/Users/user/miniconda3/python.exe -m unittest tests.test_capability_execution_contract.AccountabilityNegativeFixtureTests.test_missing_required_step tests.test_capability_execution_contract.AccountabilityNegativeFixtureTests.test_self_authored_gate tests.test_capability_execution_contract.AccountabilityNegativeFixtureTests.test_stale_agent_sidecar tests.test_capability_execution_contract.AccountabilityNegativeFixtureTests.test_copied_owner_sidecar -v
```

The command exits 0 with four passing negative tests. Their asserted evaluator
decisions respectively include `missing_required_step`,
`self_authored_gate_artifact` with classification
`run_local_worker_generated`, `stale_agent_decision_sidecar`, and
`copied_owner_decision_sidecar`. Test setup uses isolated temporary git/run
roots and never writes into the committed fixture directories.

Infrastructure acceptance does not depend on an owner liking a picture edit or
audio mix. Actual L1 picture-diversity and L3 audio-balance revisions are an
optional later operational demonstration, not an implementation acceptance
gate. The forward test proves accountability, not creative quality.

### 16.4 Regression boundary

- focused/adjacent tests run per behavior change;
- the design review froze these exact Workbench paths and SHA-256 values before
  Phase A; the acceptance companion copies them into `protected_paths`:

| Path | Frozen SHA-256 |
| --- | --- |
| `tools/workbench_handoff.py` | `92B4FEFA5BA86CAA08A8DB2765F123CA22837935B703AAC1CA5A191DC435B29C` |
| `tools/preview_timeline.py` | `19EB07DD3C4A96D9676622C8FB4060E0B5AEDBF71DC2F61A21716F7D4C8AA7A3` |
| `tools/timeline_patch.py` | `4F9B284524F207A78C22AE7AE7E810354F0512B30A93DE768C1F0404A14E928A` |
| `tools/subtitle_patch.py` | `0659D00C838777375D2496A7794A2ACAF7314987705E948DFE45EC598AFF5685` |
| `tools/audio_cue_patch.py` | `1B1AC2DDBD14361F01A56A8A21F7CE936D0793951DD621D5EAB87B72E7CF2C1C` |
| `tools/effect_patch.py` | `0040E8B3FA6D7AC1DDD947F9EFF099DDBCC2B0C9318E409F883DB3F123BA3AB7` |

Use this read-only command before authoring the companion and after final
closure to confirm the table:

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath @('tools/workbench_handoff.py','tools/preview_timeline.py','tools/timeline_patch.py','tools/subtitle_patch.py','tools/audio_cue_patch.py','tools/effect_patch.py') | Select-Object Path,Hash
```

Both invocations must exit 0; the second six hashes must exactly equal the
committed `protected_paths`. The committed contract, not an ad-hoc baseline
JSON, is the authority. The fixture manifest and every fixture file are also
listed in `protected_paths` and receive the same final-seal comparison.

- Workbench compatibility command is:

```powershell
C:/Users/user/miniconda3/python.exe -m unittest tests.test_workbench_handoff tests.test_preview_timeline tests.test_workbench_contract_sync tests.test_workbench_draft_rerender -v
```

- frozen legacy, Workbench production-path, and real-fixture hashes are read
  before the first test and compared after the final test;
- static real-repo audits run with these exact commands and each must exit 0
  with report `ok=true`:

```powershell
C:/Users/user/miniconda3/python.exe tools/skill_tool_contract_audit.py --skills-dir skills --tools-dir tools --out .tmp/single_entry_forward_accountability_acceptance/audits/skill_tool_contract.json
C:/Users/user/miniconda3/python.exe tools/doc_reference_hygiene.py --repo-root . --out .tmp/single_entry_forward_accountability_acceptance/audits/doc_reference_hygiene.json
C:/Users/user/miniconda3/python.exe tools/route_closure_integrity.py --repo-root . --out .tmp/single_entry_forward_accountability_acceptance/audits/route_closure_integrity.json
```

- the runtime integrity command is the pinned no-skip command in section 16.3;
- one full suite runs exactly once at the end:

```powershell
C:/Users/user/miniconda3/python.exe -m unittest discover -s tests
```

  with timeout at least 1,200,000 ms;
- UTF-8, JSON, path, hash, and dirty-tree read-back are required;
- `human_creative_approval=false` and `final_delivery_claimed=false` unless a
  real owner decision explicitly changes them.

## 17. Implementation Units And Ownership

Implementation is sequential and single-writer. No two workers may edit a hot
shared file concurrently.

1. **Phase A integrator — entry authority**
   - owns only `AGENTS.md`, `RUNBOOK.md`, `HANDOFF_CURRENT.md`,
     `docs/INDEX.md`, optional START_HERE clarification,
     `doc_reference_hygiene`, and their tests;
   - records pre-edit hashes for currently dirty authority files and
     reconciles them intentionally rather than staging unrelated content.
   - classifies and atomically removes or demotes only duplicate entry/current-
     state mechanisms made misleading by the single-entry change.
2. **Phase B capability-schema worker — catalog authority**
   - is the sole writer for the 11 Domain Skill `TOOL_CONTRACT` blocks,
     shared Skill parser/catalog/audit/query code, command catalog, and their
     focused tests;
   - Phase A does not edit these files while Phase B is active.
   - removes stale aliases/active references only after the section-12
     retirement evidence proves no live consumer or legacy-reader duty.
3. **Phase C runtime worker — execution authority**
   - owns the one new shared capability-execution core module,
     `video_tools.py`, `no_skip_execution_trace`, bounded closure integration,
     and their tests;
   - it does not edit Domain Skills, entry documents, or Workbench production
     code.
   - may retire a superseded runtime/accountability helper only when the new
     path is green and the bounded retirement audit classifies it `delete`.
4. **Phase D integrator then evidence worker — read-only production consumer**
   - the integrator authors and commits the work-order companion before
     dispatch;
   - the evidence worker owns only the acceptance run root;
   - Workbench production paths and frozen fixtures are read-only.

Every phase begins by checking the predecessor commit and dirty-tree hashes and
ends with a scoped commit. The integrator alone resolves overlaps. No unit owns
creative taste, final delivery, or automatic loop selection.

## 18. Rollout Order

### Phase A - One entry

- reconcile and commit current authority files intentionally;
- make RUNBOOK the sole operational entry;
- add the HANDOFF state block;
- extend doc hygiene and entry tests;
- remove duplicated volatile state from RUNBOOK and docs INDEX.
- retire misleading duplicate entry/current-state surfaces in the same commit
  when their bounded retirement evidence is `delete`; otherwise mark them
  explicitly non-authoritative/read-only.

### Phase B - Static capability accountability

- add execution class/role to canonical cards;
- extend shared parser/catalog/query/audit;
- keep every non-retired capability discoverable and owned; the post-change
  catalog ID set/count must equal the pre-change set minus only Capability IDs
  whose approved retirement-table outcome is `delete`.
- remove only proven-dead aliases or active legacy references; preserve named
  historical readers as `legacy_read_only`.

### Phase C - Forward-only runtime accountability

- add committed execution-companion parsing and path rules;
- add initialization/contract reference, the single-step executor, immutable
  attempt receipts, run-bound decision sidecars, and derived trace v2;
- extend no-skip closure and gate-purity checks;
- preserve trace v1/legacy reads.
- retire only helpers actually superseded by the new executor/closure path and
  proven consumer-free; do not delete route runners merely because they look
  old.

### Phase D - Real bounded forward test

- use frozen accepted L1/L3-shaped fixtures without changing creative truth;
- produce fresh accountable technical evidence and a legal WAITING_OWNER
  outcome;
- verify Workbench and legacy compatibility;
- refresh Codebase Memory after stable commits.

Each phase has focused tests and a scoped commit. Phases are not parallelized.
No phase requires a new orchestrator or historical migration.

## 19. Acceptance Criteria

The design is implemented only when all are true:

1. An always-loaded agent instruction points to one RUNBOOK.
2. Only RUNBOOK carries the exact `OPERATIONAL_ENTRY` marker; all other entry
   markers match their fixed values and surfaces.
3. HANDOFF contains one valid current-state block with existing references.
4. HANDOFF state exactly matches its named authoritative JSON field; entry
   audit fails stale, conflicting, duplicated, or non-HANDOFF current routing.
5. All canonical capabilities have valid execution class and role.
6. All non-retired tools/capabilities/commands remain owned, classified, and
   queryable; the catalog delta exactly matches approved `delete` rows and no
   `keep`/`legacy_read_only` row disappears unexpectedly.
7. Strict activation is determined only by one valid committed version-1
   companion and its immutable run reference; a matching run root, control
   artifact, malformed/conflicting reference, or omitted CLI argument cannot
   fall back to legacy.
8. A strict run cannot execute altered argv, a mismatched/unknown command, an
   invalid path, or a concurrent/over-bound attempt.
9. Required capability steps have immutable attempt receipts with frozen
   input/output hashes; decision requirements have typed sidecars; the final
   trace derives separate tool and decision entry variants.
10. Agent and owner evidence cannot be replaced by deterministic or gate
   output, copied from another run, or dated before its dependency receipts.
11. A gate cannot observably alter production truth in monitored roots or
    create its own prerequisite.
12. The closure meta-gate cannot require or consume its own receipt/decision.
13. Missing, stale, copied, skipped, or unplanned evidence blocks closure.
14. Legacy traces and Workbench artifacts remain readable and unchanged.
15. Every touched obsolete/misleading candidate has a retirement-table outcome;
    deleted surfaces have zero active references and no legacy-reader duty,
    while `legacy_read_only` surfaces cannot be dispatched by a strict run.
16. No removed command, Capability ID, entry marker, next action, or Skill
    consumer reference remains discoverable as active.
17. A fresh bounded technical run invokes the two registered fixture
    capabilities and reaches the correct owner gate without requiring a
    creative verdict.
18. The pinned focused, compatibility, real-audit, integrity, and full-suite
    checks pass.

## 20. Explicit Architecture Rejections

Reject any implementation that:

- creates `entry_v2`, `capability_catalog.json`, a second run registry, or a
  second closure decision engine;
- turns the single-step executor into a route selector;
- lets a gate call hidden helpers to repair its own inputs;
- requires editing every tool to emit receipts;
- backfills historical runs;
- deletes an old-looking surface without proving zero live consumers and zero
  required legacy-reader duty;
- keeps a superseded path apparently active through a silent alias, stale
  marker, compatibility shim, or unresolved next action;
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
fabricated. Mechanisms superseded by that path are either removed with
consumer evidence or visibly confined to read-only legacy compatibility, so a
new agent is not routed into a decaying half-active path.

The system still permits failure, uncertainty, owner revision, and creative
disagreement. What it no longer permits is an unsupported completion claim.
