# Work Order: Canon 67 global editorial state v0 and two-segment forward test

Date: 2026-07-15  
Status: READY_FOR_WORKER  
Recommended worker: Luna, high/maximum reasoning  
Estimated size: medium-small, bounded foundation work  
Integrator: SOL / Codex  

## 1. Goal

Build the smallest durable editorial-state foundation that lets Hermes carry
story decisions horizontally across Stage 0–10 without turning the editing
loop into another route engine.

This work order must:

1. close the stale machine-readable current-state gap;
2. add an immutable `global_editorial_state` revision chain with hash-bound
   deltas and stale-base rejection;
3. seed the state from real Canon 67 artifacts;
4. forward-test the contract on the first two real 540-second segments only;
5. register the new surface in the existing Video Pipeline Route skill so it
   cannot become an orphan tool.

The result is a state/contract capability, not a new orchestrator, selector,
renderer, story engine, or delivery claim.

## 2. Product decisions already made

These are inputs, not questions for the worker:

- Stage owns lifecycle; editing loops improve work inside the current Stage.
- The orchestrator owns canonical editorial state. Workers receive a pinned
  state and return a delta; workers do not rewrite canonical state directly.
- State revisions are immutable. Applying a delta requires the exact base file
  SHA-256 and creates a new revision plus a transition receipt.
- `HANDOFF_CURRENT.md` points to the canonical state path/hash. It must not
  duplicate the whole editorial state.
- Canon 67 material provenance is `material_origin=curated` and
  `annotation_state=unannotated`.
- Editorial guidance is explicitly non-enforceable. Do not encode vague taste
  words such as `energy_target=rising` as objective gates.
- Teacher/adviser material is intentionally deferred because the accepted
  all-or-none rule requires a complete 13/13 owner-approved roster. This is not
  a retrieval failure.
- Current full-suite trust is `STALE`: the last reported 2,786-test green run
  predates the current CapCut backend patch. Do not turn historical green
  evidence into a current PASS.
- Human creative approval and final delivery remain false.

Authoritative source decisions:

- `docs/decisions/2026-07-14-canon67-teacher-all-or-none-memory-ending.md`
- `docs/decisions/2026-07-15-upstream-editorial-discovery-boundary.md`
- `docs/hermes-v-pipeline-honest-capability-map.md`

## 3. In-scope owner zone

New production surfaces:

- `video_pipeline_core/global_editorial_state.py`
- `tools/global_editorial_state.py`
- `tests/test_global_editorial_state.py`

Bounded existing-file edits:

- `skills/video-pipeline-route.md`
  - add exactly one canonical Tool Contract entry;
  - capability ID:
    `cap.video-pipeline-route.global-editorial-state.v1`;
  - `execution_class=deterministic`;
  - `capability_role=adapter`;
  - `loops=[]`;
  - `maturity=experimental`.
- `HANDOFF_CURRENT.md`
  - edit only the JSON between `HANDOFF_STATE_START/END`;
  - change the following narrative heading to identify the old prose as
    historical/superseded context;
  - do not rewrite the rest of the document.
- `.tmp/canon67_540s_route_acceptance/campaign_status.json`
  - additive/current-pointer changes only after the forward test passes.

Run artifacts:

- `.tmp/canon67_540s_route_acceptance/editorial_state_v0/**`

Work report:

- `.tmp/canon67_540s_route_acceptance/editorial_state_v0/final/worker_report.md`

## 4. Forbidden zone

Do not modify:

- Material Map schemas or implementation, including
  `video_pipeline_core/material_map*.py`,
  `video_pipeline_core/project_material_map.py`, and their tests;
- retrieval/ranking, picture-plan, segment-contract, story blueprint, or v1–v3
  Canon 67 artifacts;
- `video_pipeline_core/capability_execution.py` or the accountability engine;
- `video_tools.py`, branch/route registries, `pipeline_home.py`, or no-skip
  machinery;
- `skills/editing-loop-director.md`;
- CapCut, Remotion, subtitle, audio, render, Verify, or delivery surfaces;
- raw media;
- existing unrelated dirty/untracked files.

Do not create a second route runner, state daemon, database, event bus, A/B
engine, cost telemetry engine, capability-card migration, or mutable `latest`
state file.

## 5. Minimal state contract

The exact Python layout is the worker's bounded decision, but the serialized
JSON must contain these concepts and no broad speculative framework.

### 5.1 State envelope

- `artifact_role=global_editorial_state`
- `schema_version=1`
- `project_id`
- `revision_id`
- `created_at`
- `base_state`: null for revision 0, otherwise path + file SHA-256
- `last_updated_by_receipt`: path + receipt SHA-256
- `source_artifacts`: role + path + SHA-256
- `material_context`
- `operational_state`
- `editorial_intent`
- `open_story_risks`
- `retired_story_intents`
- `verification_state`
- `human_creative_approval=false`
- `final_delivery_claimed=false`
- `integrity.state_payload_sha256`

### 5.2 Material context

Use independent axes, not one combined enum:

- `material_origin`: `raw | curated | generated | reference`
- `annotation_state`:
  `intent_annotated | metadata_only | unannotated`
- `intent_notes_available`
- `known_input_limits`

### 5.3 Operational state

Minimum useful fields:

- `segment_order`
- `segments` keyed by stable segment ID
- `coverage_ledger`
- `visual_family_ledger`
- `people_ledger`
- `motif_ledger`

For each seeded segment record:

- `factual_purpose`
- `story_function`
- `entry_state`
- `exit_state`
- `new_information`
- `source_window_refs`
- `review_caption`
- `selected_visual_families`
- `reuse_justifications`
- `cross_segment_repetition_risks`
- `decision_completeness`: `PASS | UNKNOWN`
- `decision_reason`

A statement without source-window references cannot receive PASS.

### 5.4 Editorial intent

Must include `enforceable=false`. It may carry the accepted thesis, logline,
motif guidance, and entry/exit intent, but must not masquerade as an objective
instrument result.

### 5.5 Deferrals and retired directions

Coverage deferrals support at least:

- `deferred_due_to_material`, with reason:
  `not_found | not_present | present_unusable | excluded_by_policy`;
- `deferred_due_to_incomplete_all_or_none_roster`.

Abandoned story directions belong in `retired_story_intents` with
`reconsider_if`; they are not active risks.

### 5.6 Verification state

At minimum record:

- focused test status and evidence for this change;
- `full_suite.status=STALE`;
- historical last-green count/skips/evidence path if independently readable;
- explicit `stale_because` evidence tied to post-green changed surfaces.

Do not guess token cost or fabricate absent test evidence.

## 6. Integrity model

Avoid a circular hash between state and receipt:

1. Canonicalize and hash the state payload before receipt linkage.
2. Write an immutable transition receipt containing:
   - base state file SHA-256 (null for revision 0),
   - delta SHA-256,
   - new state payload SHA-256,
   - source artifact hashes,
   - operation result.
3. Write the immutable state envelope with the receipt path/hash and payload
   hash.
4. Campaign/Handoff pointers pin the final state file path and file SHA-256.

Validation must check both directions that are non-circular: state -> receipt
hash and receipt -> state payload hash.

All writes are create-exclusive. Existing revision, receipt, or delta files
must never be overwritten.

## 7. Required CLI behavior

`tools/global_editorial_state.py` must expose bounded commands equivalent to:

- `init`: create revision 0 from a seed and source refs;
- `validate`: validate schema, hashes, receipt binding, and referenced sources;
- `apply-delta`: require an exact base file hash and create the next revision;
- `validate-worker-context`: reject a worker context whose pinned state
  path/hash is stale or mismatched.

JSON output and stable machine-readable error codes are required. Required
negative codes include:

- `stale_base_state`
- `immutable_artifact_exists`
- `state_receipt_hash_mismatch`
- `receipt_payload_hash_mismatch`
- `source_artifact_hash_mismatch`
- `invalid_material_origin`
- `invalid_annotation_state`
- `pass_without_source_window_refs`

The CLI is a thin adapter over the core module; business logic does not live in
`tools/`.

## 8. Ordered execution

### Task 0 — Freeze and audit

Record HEAD, branch, full `git status --short`, and SHA-256 for every bounded
existing file before editing. Read the real v3 plan and source decisions using
explicit UTF-8. Stop if their hashes drift during the task.

### Task 1 — RED tests

Add failing tests before implementation for:

- revision-0 initialization and validation;
- immutable create-exclusive writes;
- accepted delta producing revision 1 and a bound receipt;
- wrong base hash rejecting with `stale_base_state`;
- state/receipt and receipt/payload tamper detection;
- invalid provenance axes;
- PASS segment without source windows;
- worker-context freshness;
- registered tool discovery with no orphan.

Preserve the RED command, exit code, and output.

### Task 2 — Implement and register

Implement the core and thin CLI, then add the single Tool Contract entry to
`skills/video-pipeline-route.md`. Do not add a new skill.

### Task 3 — Real Canon 67 seed

Create a seed from the actual artifacts below; do not hand-copy unsupported
claims:

- `.tmp/canon67_540s_route_acceptance/stage1/story_soul_blueprint.json`
- `.tmp/canon67_540s_route_acceptance/stage1/screenplay_beats.json`
- `.tmp/canon67_540s_route_acceptance/stage3/project_material_map_l0_v1.json`
- `.tmp/canon67_540s_route_acceptance/stage5/l1_revision_v3/l1_picture_plan_v3.proposed.json`
- `docs/decisions/2026-07-14-canon67-teacher-all-or-none-memory-ending.md`

Seed all ten stable segment IDs at summary level, but deeply calibrate only:

- `seg01_time_moves_people_begin` (30 seconds);
- `seg02_first_gathering` (45 seconds).

The first two segments must use the real v3 clips, source paths, hashes, and
windows. Record PASS only where the stated purpose is directly supported;
otherwise use UNKNOWN with a reason.

Record the teacher/adviser coverage item as
`deferred_due_to_incomplete_all_or_none_roster`, required count 13, with the
accepted decision file as evidence.

### Task 4 — Delta and freshness forward test

Create a real, non-taste delta using already accepted facts from the first two
segments or the teacher deferral. Apply it once to create revision 1. Then:

- validate revision 1;
- prove a worker context pinned to revision 0 is rejected as stale;
- prove a worker context pinned to revision 1 passes;
- prove revision 0, delta, receipt, and revision 1 remain immutable.

Do not ask for a new creative verdict and do not invent one.

### Task 5 — Current-state closure

Only after Task 4 passes:

- update `campaign_status.json` to the truthful current Stage 5 owner-review
  state and add the canonical editorial-state path/hash plus
  `verification_state.full_suite.status=STALE`;
- update only the machine JSON block in `HANDOFF_CURRENT.md` to point to the
  same campaign and state path/hash;
- relabel the old narrative section as historical/superseded context.

The truthful waiting state is
`WAITING_OWNER_CANON67_EDITORIAL_STATE_V0_REVIEW`. It must not imply picture
lock, render permission, human creative approval, or delivery.

### Task 6 — Evidence and report

Write a worker report with:

- pre/post hashes and dirty tree;
- RED/GREEN commands and exit codes;
- exact revision/delta/receipt paths and SHA-256 values;
- first-two-segment completeness results;
- state freshness negative/positive evidence;
- registration/audit results;
- deviations, blind spots, skipped checks, and stop state.

## 9. Acceptance commands

Use the repository Python interpreter. If no interpreter is explicitly pinned,
use `C:\Users\user\miniconda3\python.exe`.

Required focused tests:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_global_editorial_state tests.test_skill_tool_contracts tests.test_dispatch_capabilities tests.test_pipeline_skill_boundaries -v
```

Required registry audit:

```powershell
C:\Users\user\miniconda3\python.exe tools/skill_tool_contract_audit.py --skills-dir skills --tools-dir tools --json
```

Required real CLI evidence:

- `init` exit 0;
- revision-0 `validate` exit 0;
- one `apply-delta` exit 0;
- stale revision-0 worker context exit 1 with `stale_base_state`;
- revision-1 worker context exit 0;
- revision-1 `validate` exit 0.

Also require:

- explicit UTF-8/JSON read-back and no U+FFFD or suspicious repeated
  question-mark sequences in Chinese fields;
- all referenced artifact hashes match;
- new tool is owned and discoverable by exact capability ID;
- `git diff --check` exit 0;
- post-task unrelated dirty paths/hashes preserved.

Full suite is deliberately NOT RUN in this bounded work order. Keep its current
machine state `STALE`; a later integration closure owns the one full-suite run.

## 10. Stop-loss

Stop at the last green state and report `STRUCTURAL` if any of these occur:

- implementation requires a forbidden-zone edit;
- the same failure class recurs after one LOCAL correction;
- existing v3/source/decision hashes drift;
- current artifacts cannot support truthful first-two-segment records;
- the only way forward is manual run-local JSON that bypasses the public CLI;
- tool registration requires a second skill/route/registry owner;
- mutable overwrite is required;
- state freshness cannot be proven without weakening hash checks.

Do not convert a stop into a waiver or optimistic PASS.

## 11. Delegated decisions

The worker may decide:

- internal Python types/functions;
- canonical JSON serialization details;
- revision filename convention, provided it is immutable and deterministic;
- exact split between unit and CLI tests;
- which already accepted operational fact becomes the one forward-test delta.

The worker may not decide:

- new story content or owner taste;
- teacher roster inclusion;
- render/build permission;
- Material Map migration;
- A/B policy implementation;
- CapCut/backend policy;
- maturity beyond `experimental`;
- creative approval or delivery.

## 12. Legal completion state

Success stops at:

`WAITING_INTEGRATOR_CANON67_EDITORIAL_STATE_V0_REVIEW`

with:

- focused tests PASS;
- tool audit PASS;
- real revision 0 -> delta -> revision 1 forward test PASS;
- stale worker context correctly rejected;
- current machine pointers aligned;
- `human_creative_approval=false`;
- `final_delivery_claimed=false`.

This completion does not certify long-film story quality. It only proves that
accepted story/coverage decisions can travel forward without becoming stale,
detached, or silently overwritten.

## 13. Explicit follow-on queue — not part of this work order

After integrator acceptance, open separate bounded work for:

1. Material Map provenance/intent-note schema migration and improved-provenance
   transfer test;
2. Stage 2/5 A/B decision policy and retired-story-intent workflow;
3. capability proposal build/buy fields
   (`capability_nature`, `sourcing_strategy`);
4. cost metrics in a separate `run_metrics.json`;
5. CapCut candidate backend provenance;
6. expansion from two segments to all ten segments.
