# Single Entry And Forward Accountability Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give Hermes one unmistakable operational entry and a forward-only,
fail-closed execution contract that keeps capabilities discoverable, proves
registered tool execution, binds agent/owner decisions to the current run, and
retires only evidence-proven obsolete or misleading mechanisms.

**Architecture:** Extend the existing Skill-derived Capability Catalog,
`video_tools.py` dispatch, document hygiene, and no-skip closure. Add one thin
`capability_execution.py` core for committed contracts, initialization,
reservations, immutable receipts, manifest continuity, and decision-sidecar
validation. Do not add a route selector, second registry, database, journal,
Workbench redesign, or historical migration.

**Tech Stack:** Python 3.11, `unittest`, Git, existing JSON artifacts,
`video_tools.py`, Codebase Memory MCP for discovery, ffmpeg-backed existing
audio tools, Markdown/HTML markers.

**Source design:**
`docs/superpowers/specs/2026-07-13-single-entry-forward-accountability-design.md`

**Formal work order:**
`docs/construction-guides/work-orders/2026-07-13-single-entry-forward-accountability-long-task.md`

**Execution location:** Use the current workspace
`C:/Users/user/Desktop/video_pipeline`, not a new worktree. This is a deliberate
exception because `AGENTS.md`, `RUNBOOK.md`, `HANDOFF_CURRENT.md`, and
`docs/INDEX.md` already contain user-owned uncommitted authority changes that
Phase A must preserve and reconcile. Never stage those pre-existing dirty
files; leave their combined authority patch for integrator review.

---

## File Structure And Ownership Map

### Existing files modified

- `AGENTS.md` — always-loaded pointer marker only; pre-existing dirty, never
  stage in worker commits.
- `RUNBOOK.md` — sole operational-entry marker and stable routing doctrine;
  pre-existing dirty, never stage in worker commits.
- `HANDOFF_CURRENT.md` — one current-state block and pointer to authoritative
  state JSON; pre-existing dirty, never stage in worker commits.
- `docs/INDEX.md` — document-map marker only; pre-existing dirty, never stage
  in worker commits.
- `docs/START_HERE_VIDEO_PIPELINE.md` — orientation marker only, if it exists
  and is clean.
- `video_pipeline_core/doc_reference_hygiene.py` — exact entry-marker and
  HANDOFF state validation.
- `video_pipeline_core/skill_tool_contract.py` — canonical capability schema,
  command normalization, and retirement-delta validation.
- `video_pipeline_core/capability_catalog.py` — live Card projection and query
  fields; remains derived from Skills.
- `tools/skill_tool_contract_audit.py` — real repo orphan/schema/retirement
  audit.
- `video_pipeline_core/tool_command_catalog.py` — classify the new
  `capability-run` command.
- `video_tools.py` — add only `capability-run` handler, parser, and dispatch
  registration.
- `video_pipeline_core/no_skip_execution_trace.py` — strict contract discovery,
  decision binding, derived trace v2, gate purity, and legal closure state.
- `tools/no_skip_execution_trace.py` — add strict `--contract` CLI input while
  preserving legacy invocation.
- `video_pipeline_core/route_closure_integrity.py` — only bounded integration
  required to recognize strict closure artifacts; do not redesign route stages.
- Eleven Domain Skills with `TOOL_CONTRACT` blocks:
  `audio-director.md`, `brownfield-edit.md`, `dashboard.md`,
  `generated-material-producer.md`, `material-map.md`,
  `soundtrack-arranger.md`, `spec-contract.md`, `subtitle-director.md`,
  `verify.md`, `video-effect-factory.md`, and `video-pipeline-route.md`.

### New production/test files

- `video_pipeline_core/capability_execution.py` — the only new shared runtime
  core; committed-contract/path/hash/reference/reservation/receipt/manifest
  responsibilities only.
- `tests/test_accountability_retirement.py` — retirement table and catalog
  delta rules.
- `tests/test_capability_execution_contract.py` — activation, schema,
  decision-sidecar, and strict negative fixtures.
- `tests/test_capability_execution_receipts.py` — initialization,
  reservation, attempts, retries, execution, and manifest chain.
- `tests/test_accountability_path_rules.py` — Windows/portable path and JSON
  hashing rules.
- `tests/fixtures/accountability_forward_v1/**` — small committed JSON/audio
  fixtures and four negative fixture shapes.
- `docs/construction-guides/work-orders/2026-07-13-single-entry-forward-accountability-acceptance.execution.json`
  — committed strict forward-test companion, created only after runtime code is
  green.
- `docs/construction-guides/work-orders/2026-07-13-single-entry-forward-accountability-long-task.md`
  — read-only construction authority and the execution companion's exact
  `work_order_path`/hash source.

### Read-only protected files

- `skills/editing-loop-director.md`
- `docs/construction-guides/2026-07-10-editing-loop-product-spec.md`
- `skills/INDEX.md`
- `docs/branch-contract-registry.json`
- `dashboard/**`
- `reference repo/**`
- `tools/workbench_handoff.py`, `tools/preview_timeline.py`,
  `tools/timeline_patch.py`, `tools/subtitle_patch.py`,
  `tools/audio_cue_patch.py`, `tools/effect_patch.py`
- Existing candidates, media, raw sources, and historical work-order evidence.

---

## Chunk 1: Baseline And Single Entry

### Task 1: Freeze the dirty workspace and current factory baseline

**Files:**
- Create runtime evidence only:
  `.tmp/single_entry_forward_accountability_acceptance/baseline/**`
- Do not modify production files in this task.

- [ ] **Step 1: Read authority and source design completely**

Read `AGENTS.md`, the source design, this plan,
`docs/construction-guides/work-orders/2026-07-13-single-entry-forward-accountability-long-task.md`,
and the current `RUNBOOK.md` / `HANDOFF_CURRENT.md`. Use explicit UTF-8 for
Markdown.

Before proceeding, prove all three planning authorities are tracked:

```powershell
git ls-files --error-unmatch docs/superpowers/specs/2026-07-13-single-entry-forward-accountability-design.md
git ls-files --error-unmatch docs/superpowers/plans/2026-07-13-single-entry-forward-accountability-implementation-plan.md
git ls-files --error-unmatch docs/construction-guides/work-orders/2026-07-13-single-entry-forward-accountability-long-task.md
```

Expected: each exits `0`. Any miss stops before execution.

- [ ] **Step 2: Record HEAD, branch, dirty paths, and authority hashes**

Create evidence directories, then record full output without cleaning,
resetting, staging, or moving anything:

```powershell
New-Item -ItemType Directory -Force .tmp/single_entry_forward_accountability_acceptance/baseline,.tmp/single_entry_forward_accountability_acceptance/phase_a/red,.tmp/single_entry_forward_accountability_acceptance/phase_a/before,.tmp/single_entry_forward_accountability_acceptance/phase_b,.tmp/single_entry_forward_accountability_acceptance/phase_c,.tmp/single_entry_forward_accountability_acceptance/final | Out-Null
git status --short --branch 2>&1 | Tee-Object .tmp/single_entry_forward_accountability_acceptance/baseline/git_status.txt
git rev-parse HEAD 2>&1 | Tee-Object .tmp/single_entry_forward_accountability_acceptance/baseline/head.txt
Get-FileHash -Algorithm SHA256 AGENTS.md,RUNBOOK.md,HANDOFF_CURRENT.md,docs/INDEX.md,docs/construction-guides/2026-07-10-editing-loop-product-spec.md,skills/editing-loop-director.md | Format-List Path,Hash | Out-File -Encoding utf8 .tmp/single_entry_forward_accountability_acceptance/baseline/authority_hashes.txt
```

Expected: commands exit `0`; the known dirty files remain dirty.

- [ ] **Step 3: Freeze live capability and command sets**

```powershell
C:/Users/user/miniconda3/python.exe tools/skill_tool_contract_audit.py --skills-dir skills --tools-dir tools --out .tmp/single_entry_forward_accountability_acceptance/baseline/skill_tool_contract.json
C:/Users/user/miniconda3/python.exe video_tools.py commands-manifest --out .tmp/single_entry_forward_accountability_acceptance/baseline/commands_manifest.json
```

Expected: both exit `0`; record the exact pre-change Capability ID set, Python
tool ownership counts, command set/count, duplicate IDs, orphan tools, and
unclassified commands. Do not hard-code `51` as the post-change count.

- [ ] **Step 4: Verify protected Workbench hashes against the source design**

Run the exact six-file `Get-FileHash` command in design section 16.4. Expected:
all six values equal the frozen table. A mismatch is STRUCTURAL and stops the
campaign before edits.

- [ ] **Step 5: Run the pre-change focused baseline**

```powershell
C:/Users/user/miniconda3/python.exe -m unittest tests.test_pipeline_skill_boundaries tests.test_doc_reference_hygiene tests.test_interactive_skill_flow_docs tests.test_skill_index tests.test_skill_tool_contract_parser tests.test_skill_tool_contracts tests.test_dispatch_capabilities tests.test_video_tools_command_catalog tests.test_no_skip_execution_trace tests.test_route_closure_integrity -v
```

Expected: exit `0`. If existing failures occur, report them as baseline FAIL
and stop; do not repair unrelated tests.

### Task 2: Add red-first exact entry-marker and HANDOFF tests

**Files:**
- Modify: `tests/test_pipeline_skill_boundaries.py`
- Modify: `tests/test_doc_reference_hygiene.py`
- Modify: `tests/test_interactive_skill_flow_docs.py`

- [ ] **Step 1: Write marker placement tests**

Add assertions for the exact six markers from design section 5.1. Tests must
fail for missing, duplicated, wrong-surface, or wrong-value markers and must
not infer authority from prose.

Use exact codes and at least these concrete cases:

```python
def test_entry_contract_rejects_missing_runbook_marker(self):
    root = self._entry_fixture(runbook="# Runbook\n")
    report = evaluate_entry_contract(root)
    self.assertIn("entry_marker_missing:RUNBOOK.md:OPERATIONAL_ENTRY", report["errors"])

def test_entry_contract_rejects_marker_on_wrong_surface(self):
    root = self._entry_fixture(index="<!-- OPERATIONAL_ENTRY: RUNBOOK -->\n")
    report = evaluate_entry_contract(root)
    self.assertIn("entry_marker_wrong_surface:docs/INDEX.md:OPERATIONAL_ENTRY", report["errors"])
```

- [ ] **Step 2: Write HANDOFF schema/state tests**

Create temporary fixtures covering: one valid block, duplicate block, malformed
JSON, unknown key, missing path, `IDLE` with active fields, active state without
an authoritative JSON artifact/field, and an exact state mismatch.

The valid block fixture is exactly:

```json
{
  "artifact_role": "current_handoff_state",
  "version": 1,
  "updated_at": "2026-07-13T00:00:00+08:00",
  "state": "ACTIVE",
  "active_work_order": "docs/construction-guides/work-orders/fixture.md",
  "active_spec": null,
  "active_skill": null,
  "active_run_root": ".tmp/fixture",
  "authoritative_state_artifact": ".tmp/fixture/state.json",
  "authoritative_state_field": "state",
  "next_actions": ["continue_fixture"],
  "do_not_do": ["claim_delivery"],
  "human_creative_approval": false,
  "final_delivery_claimed": false
}
```

Required error codes are `handoff_block_missing`, `handoff_block_duplicate`,
`handoff_json_invalid`, `handoff_unknown_key:<key>`,
`handoff_path_missing:<field>`, `handoff_idle_has_active_fields`,
`handoff_state_authority_missing`, and `handoff_state_mismatch`.

- [ ] **Step 3: Write stable RUNBOOK tests**

Assert RUNBOOK contains no `active_work_order`,
`authoritative_state_artifact`, `ACTIVE_WORK_ORDER` marker, or state token
matching the design regex. Historical links in START_HERE/docs INDEX remain
allowed and non-authoritative.

- [ ] **Step 4: Run RED**

```powershell
$log='.tmp/single_entry_forward_accountability_acceptance/phase_a/red/entry_tests.log'; C:/Users/user/miniconda3/python.exe -m unittest tests.test_pipeline_skill_boundaries tests.test_doc_reference_hygiene tests.test_interactive_skill_flow_docs -v 2>&1 | Tee-Object $log; $code=$LASTEXITCODE; [IO.File]::WriteAllText('.tmp/single_entry_forward_accountability_acceptance/phase_a/red/exit_code.txt',"$code`n",[Text.UTF8Encoding]::new($false)); if($code -eq 0){throw 'expected RED entry tests'}
```

Expected: exit `1` only for the newly required entry/HANDOFF behaviors. Save
stdout/stderr/exit code under `phase_a/red/`.

### Task 3: Implement and apply the single-entry contract

**Files:**
- Modify: `video_pipeline_core/doc_reference_hygiene.py`
- Modify, do not stage: `AGENTS.md`
- Modify, do not stage: `RUNBOOK.md`
- Modify, do not stage: `HANDOFF_CURRENT.md`
- Modify, do not stage: `docs/INDEX.md`
- Modify if clean: `docs/START_HERE_VIDEO_PIPELINE.md`
- Create runtime state:
  `.tmp/single_entry_forward_accountability_acceptance/campaign_status.json`

- [ ] **Step 1: Add pure entry-contract parsing**

Implement a focused entry evaluator alongside existing doc classification:

```python
def evaluate_entry_contract(repo_root: str | Path) -> dict[str, object]:
    """Validate exact markers and the one HANDOFF JSON block."""
```

Implement these deterministic helpers in the same module:

```python
ENTRY_SURFACES = {
    "AGENTS.md": {"OPERATIONAL_ENTRY_POINTER": "RUNBOOK.md"},
    "RUNBOOK.md": {"OPERATIONAL_ENTRY": "RUNBOOK", "CURRENT_HANDOFF_POINTER": "HANDOFF_CURRENT.md"},
    "HANDOFF_CURRENT.md": {"DOCUMENT_ROLE": "CURRENT_HANDOFF"},
    "docs/START_HERE_VIDEO_PIPELINE.md": {"DOCUMENT_ROLE": "ORIENTATION"},
    "docs/INDEX.md": {"DOCUMENT_ROLE": "MAP"},
}

def parse_handoff_state(text: str) -> tuple[dict[str, object] | None, list[str]]: ...
```

Return exactly `artifact_role`, `version`, `ok`, sorted `errors`, parsed
`handoff`, and `scanned_surfaces`. Use the error codes from Task 2 and explicit
UTF-8 reads; do not create an entry registry.

Implementation algorithm is fixed: parse HTML comments with
`re.finditer(r"<!--\s*([A-Z_]+):\s*([^>]+?)\s*-->")`; compare the resulting
`(surface,key,value)` tuples to `ENTRY_SURFACES`; extract exactly one substring
between `HANDOFF_STATE_START/END`; `json.loads` it; compare keys to the exact
valid-block key set; resolve each non-null path under repo root; for active
state load the named JSON and walk the single top-level field named by
`authoritative_state_field`; compare its exact string to HANDOFF `state`.
`IDLE` requires every active/state-authority field null. Sort/de-duplicate
errors before returning.

- [ ] **Step 2: Make current doc hygiene include entry results**

Keep existing orphan-document semantics. Add `entry_contract` and make top-level
`ok` false when either orphan classification or entry validation fails.

- [ ] **Step 3: Apply the exact markers and current state**

Use `RUNBOOK.md` as sole entry. HANDOFF must name this formal work order and
`.tmp/.../campaign_status.json`, whose `state` is `ACTIVE`. Preserve all
pre-existing user text that does not conflict with the new fixed role.

The only pre-approved retirement edits in this unattended worker run are:

1. remove RUNBOOK section `## Current Editing Loop Continuation` and replace it
   with the stable HANDOFF pointer doctrine;
2. remove docs/INDEX's `Current Editing Loop continuation` current-authority
   row while preserving any historical link elsewhere as map content;
3. replace HANDOFF's old 2026-07-11/2026-07-03 current-campaign payload with
   the one machine block and a short human summary of this work order.

No code, command, Capability ID, Skill, test, or whole document is approved for
deletion in this long task.

- [ ] **Step 4: Capture the campaign-only authority delta**

Copy pre-edit authority files to `.tmp/.../phase_a/before/` before editing,
then use `git diff --no-index` after editing to create bounded evidence. Do not
stage or commit the four pre-existing dirty authority files.

Before Step 3 edits:

```powershell
Copy-Item AGENTS.md,RUNBOOK.md,HANDOFF_CURRENT.md,docs/INDEX.md -Destination .tmp/single_entry_forward_accountability_acceptance/phase_a/before
```

After edits:

```powershell
$pairs=@(@('AGENTS.md','AGENTS.md'),@('RUNBOOK.md','RUNBOOK.md'),@('HANDOFF_CURRENT.md','HANDOFF_CURRENT.md'),@('INDEX.md','docs/INDEX.md')); foreach($pair in $pairs){$before=".tmp/single_entry_forward_accountability_acceptance/phase_a/before/$($pair[0])";$text=(& git diff --no-index -- $before $pair[1] 2>&1 | Out-String);$code=$LASTEXITCODE;$out=".tmp/single_entry_forward_accountability_acceptance/phase_a/$($pair[0]).campaign.diff";[IO.File]::WriteAllText($out,$text,[Text.UTF8Encoding]::new($false));if($code -gt 1){throw "git diff failed: $($pair[1])"}}
```

Exit `1` means a diff was found and is expected; greater than `1` fails.

- [ ] **Step 5: Run GREEN and real audit**

```powershell
C:/Users/user/miniconda3/python.exe -m unittest tests.test_pipeline_skill_boundaries tests.test_doc_reference_hygiene tests.test_interactive_skill_flow_docs tests.test_skill_index -v
C:/Users/user/miniconda3/python.exe tools/doc_reference_hygiene.py --repo-root . --out .tmp/single_entry_forward_accountability_acceptance/phase_a/doc_reference_hygiene.json
```

Expected: both exit `0`; report `ok=true`.

- [ ] **Step 6: Leave Phase A as one integrator-owned unstaged unit**

Do not commit the entry evaluator/tests separately from the authority markers:
that commit would fail when checked out without the dirty docs. Leave
`video_pipeline_core/doc_reference_hygiene.py`, the three focused tests,
START_HERE (if changed), and the four authority docs unstaged. Record their
exact paths and post-hashes. The manager/integrator will review and commit this
whole Phase A unit after the Luna run; later Phase B/C/D commits must exclude
every Phase A path.

---

## Chunk 2: Capability Schema, Catalog, And Retirement Safety

### Task 4: Add red-first Capability Card schema tests

**Files:**
- Modify: `tests/test_skill_tool_contract_parser.py`
- Modify: `tests/test_skill_tool_contracts.py`
- Modify: `tests/test_dispatch_capabilities.py`
- Create: `tests/test_accountability_retirement.py`

- [ ] **Step 1: Test the two new fields and allowed matrix**

Assert every canonical entry requires `execution_class` in
`deterministic|hybrid` and `capability_role` in
`operation|review|gate|adapter`. Reject `hybrid+adapter` and unknown values.

Add exact assertions against `validate_contract_schema`:

```python
def test_canonical_card_requires_execution_class_and_role(self):
    errors = validate_contract_schema([self._contract_without_accountability_fields()])
    self.assertEqual(
        {e["code"] for e in errors},
        {"missing_execution_class", "missing_capability_role"},
    )

def test_hybrid_adapter_is_rejected(self):
    errors = validate_contract_schema([self._contract(execution_class="hybrid", capability_role="adapter")])
    self.assertIn("invalid_execution_class_role", {e["code"] for e in errors})
```

- [ ] **Step 2: Test live command projection**

Assert live Cards expose normalized `command`, `execution_class`, and
`capability_role`. For `video_tools.py`, command identity includes the exact
subcommand. Domain Skills must not store a duplicate `command` field.

Concrete projection assertion:

```python
self.assertEqual(card["command"], "video_tools.py voiceover-provider-plan")
self.assertEqual(card["execution_class"], "deterministic")
self.assertEqual(card["capability_role"], "operation")
self.assertNotIn("command", source_entry)
```

- [ ] **Step 3: Test retirement delta rules**

Define fixtures for `delete`, `legacy_read_only`, `keep`, and UNKNOWN. Assert:
post IDs equal pre IDs minus only approved `delete` IDs; `keep` and
`legacy_read_only` cannot disappear; a delete with live consumer/legacy-reader
evidence or UNKNOWN is rejected.

Use this exact row schema:

```json
{
  "candidate_id": "entry.runbook.current-editing-loop-continuation",
  "surface_type": "doc_section | command | capability | skill | code | test | alias",
  "paths": ["RUNBOOK.md"],
  "outcome": "delete | legacy_read_only | keep",
  "replacement": "HANDOFF_CURRENT.md or null",
  "live_consumer": {"status": "PASS | FAIL | UNKNOWN", "refs": ["path:locator"]},
  "legacy_reader": {"status": "PASS | FAIL | UNKNOWN", "refs": ["path:locator"]},
  "approved_by": "design:2026-07-13 or null"
}
```

For a delete row, `live_consumer.status=PASS` means the search proved zero live
consumers and `legacy_reader.status=PASS` means zero required readers. Required
errors are `retirement_row_missing:<candidate>:<field>`,
`retirement_outcome_invalid:<candidate>`,
`retirement_delete_not_approved:<candidate>`,
`retirement_delete_live_consumer:<candidate>`,
`retirement_delete_legacy_reader:<candidate>`,
`retirement_delete_unknown:<candidate>`,
`retirement_unapproved_catalog_removal:<capability_id>`, and
`retirement_preserved_id_missing:<capability_id>`.

Concrete negative test:

```python
def test_delete_with_unknown_consumer_is_rejected(self):
    rows = [{
        "candidate_id": "cap.x.y.v1", "surface_type": "capability",
        "paths": ["skills/x.md"], "outcome": "delete", "replacement": None,
        "live_consumer": {"status": "UNKNOWN", "refs": []},
        "legacy_reader": {"status": "PASS", "refs": ["rg:no references"]},
        "approved_by": "design:2026-07-13",
    }]
    errors = validate_retirement_delta({"cap.x.y.v1"}, set(), rows)
    self.assertIn("retirement_delete_unknown:cap.x.y.v1", [e["code"] for e in errors])
```

- [ ] **Step 4: Run RED**

```powershell
C:/Users/user/miniconda3/python.exe -m unittest tests.test_skill_tool_contract_parser tests.test_skill_tool_contracts tests.test_dispatch_capabilities tests.test_accountability_retirement -v
```

Expected: exit `1` for missing schema/projection/retirement behavior only.

At this stage, all new tests use synthetic contract/catalog/retirement fixtures
only. Do not add a real-repo assertion that all eleven Skills are migrated yet;
that RED belongs to Task 6.

### Task 5: Implement the shared schema/catalog rules

**Files:**
- Modify: `video_pipeline_core/skill_tool_contract.py`
- Modify: `video_pipeline_core/capability_catalog.py`
- Modify: `tools/skill_tool_contract_audit.py`

- [ ] **Step 1: Add constants and validation**

Add `EXECUTION_CLASSES`, `CAPABILITY_ROLES`, and the allowed class/role matrix.
Keep existing schema compatibility only for explicitly legacy reads; canonical
active Cards fail missing fields.

Use these exact constants:

```python
EXECUTION_CLASSES = {"deterministic", "hybrid"}
CAPABILITY_ROLES = {"operation", "review", "gate", "adapter"}
ALLOWED_CLASS_ROLE = {
    "operation": EXECUTION_CLASSES,
    "review": EXECUTION_CLASSES,
    "gate": EXECUTION_CLASSES,
    "adapter": {"deterministic"},
}
```

Emit `missing_execution_class`, `invalid_execution_class`,
`missing_capability_role`, `invalid_capability_role`, and
`invalid_execution_class_role` through the existing `_error()` shape.

- [ ] **Step 2: Derive command without duplicate storage**

Normalize the existing `tool` value into live Card `command`. Preserve the
exact `video_tools.py <subcommand>` pair. Keep `tool` for backward-compatible
query output if current consumers need it.

- [ ] **Step 3: Add pure retirement validation**

Implement:

```python
def validate_retirement_delta(
    pre_ids: set[str], post_ids: set[str], rows: list[dict[str, object]]
) -> list[dict[str, str]]:
    """Return deterministic retirement errors; never discover/delete files."""
```

This is validation, not a registry or deletion engine.

Return sorted dictionaries with exactly `code`, `candidate_id`, and `message`.
Validate the row schema/error codes from Task 4 before comparing ID sets.

- [ ] **Step 4: Extend real audit output**

Expose class/role/command errors and optional retirement-delta results. Keep
existing orphan/duplicate/tool ownership checks intact.

- [ ] **Step 5: Run fixture-scoped GREEN**

Create the exact test classes
`CapabilityAccountabilitySchemaUnitTest`,
`CapabilityCatalogAccountabilityUnitTest`, and
`AccountabilityRetirementUnitTest` for the synthetic cases from Task 4, then:

```powershell
C:/Users/user/miniconda3/python.exe -m unittest tests.test_skill_tool_contract_parser.CapabilityAccountabilitySchemaUnitTest tests.test_dispatch_capabilities.CapabilityCatalogAccountabilityUnitTest tests.test_accountability_retirement.AccountabilityRetirementUnitTest -v
```

Expected: exit `0`. The real-repo audit is intentionally not run before Task 6.

- [ ] **Step 6: Preserve the synthetic-GREEN schema as an unstaged migration unit**

Do not commit yet: the real audit correctly fails until all eleven live Skills
carry the now-required fields. Record the synthetic GREEN command/exit, leave
the shared schema/catalog/audit and synthetic tests unstaged, and continue
directly to Task 6. Task 6 commits this whole migration atomically.

### Task 6: Migrate the 11 Domain Skills without overclaiming

**Files:**
- Modify the eleven Skill files listed in the ownership map.
- Create evidence only:
  `.tmp/.../phase_b/capability_classification.json`
  and `.tmp/.../phase_b/retirement_table.json`

- [ ] **Step 1: Classify all pre-change Capability IDs with one rule set**

Use these frozen rules:

- `operation`: changes a production artifact, media asset, plan, or accepted
  pipeline truth.
- `review`: produces evidence/draft/report for later judgment without applying
  production truth.
- `gate`: primarily returns PASS/FAIL/UNKNOWN/readiness and findings.
- `adapter`: deterministic format conversion/bridge/export only.
- default `execution_class=deterministic`.
- use `hybrid` only when the current Capability's own documented contract
  inherently requires agent judgment after its tool output; record the exact
  existing sentence as `hybrid_reason` in evidence, not in the Skill Card.
- `material-rough-cut` is `hybrid+operation` for the forward fixture.
- never mark `adapter` hybrid.

- [ ] **Step 2: Add only the two fields to every canonical entry**

Do not rewrite prose, move ownership, add a second command field, alter
maturity/certified scope, or edit `skills/editing-loop-director.md`.

Before editing the Skills, add real-repo assertions in
`tests/test_skill_tool_contracts.py` that every canonical Card has both fields
and the allowed pair. Run that module; expected exit `1` with
`missing_execution_class`/`missing_capability_role`. Save this Task-6 RED, then
apply the 11-Skill migration.

- [ ] **Step 3: Build the retirement table before deleting anything**

Audit only surfaces made redundant/touched by this project. Use Codebase Memory
callers plus `rg` for strings/config/docs. Outcome is `delete`,
`legacy_read_only`, or `keep`; UNKNOWN must be `keep`. Do not delete a
Capability or command unless the integrator-approved design rules and all
evidence are green. In this long task, default to `keep` if any doubt remains.

Freeze exactly the three pre-approved document rows from Task 3 as `delete`.
Every discovered code/command/Capability/Skill/test/alias candidate must be
`keep` or `legacy_read_only`; it is a recommendation for a later integrator
decision and must not change Phase B file/commit scope.

- [ ] **Step 4: Run GREEN and real catalog queries**

```powershell
C:/Users/user/miniconda3/python.exe -m unittest tests.test_skill_tool_contract_parser tests.test_skill_tool_contracts tests.test_dispatch_capabilities tests.test_accountability_retirement -v
C:/Users/user/miniconda3/python.exe tools/skill_tool_contract_audit.py --skills-dir skills --tools-dir tools --out .tmp/single_entry_forward_accountability_acceptance/phase_b/skill_tool_contract.json
C:/Users/user/miniconda3/python.exe video_tools.py dispatch-capabilities --id cap.material-map.material-rough-cut.v1 --json
C:/Users/user/miniconda3/python.exe video_tools.py dispatch-capabilities --loop L3 --json
```

Expected: all exit `0`; no orphan/duplicate/broken consumer; query results show
the new fields and exact command.

- [ ] **Step 5: Verify catalog delta**

Compare post IDs to Task 1 pre IDs through `validate_retirement_delta`.
Expected: only approved `delete` rows disappear. If no deletion is proven, ID
sets must be identical.

- [ ] **Step 6: Commit Phase B clean scope**

Stage only the 11 Skills, shared schema/catalog/audit files, and four focused
tests. There are no approved Capability/command deletions in this commit, so
the post ID set must equal the pre ID set.

```powershell
git add video_pipeline_core/skill_tool_contract.py video_pipeline_core/capability_catalog.py tools/skill_tool_contract_audit.py skills/audio-director.md skills/brownfield-edit.md skills/dashboard.md skills/generated-material-producer.md skills/material-map.md skills/soundtrack-arranger.md skills/spec-contract.md skills/subtitle-director.md skills/verify.md skills/video-effect-factory.md skills/video-pipeline-route.md tests/test_skill_tool_contracts.py tests/test_skill_tool_contract_parser.py tests/test_dispatch_capabilities.py tests/test_accountability_retirement.py
git commit -m "feat: classify registered capabilities"
```

---

## Chunk 3: Forward-Only Contract And Trusted Step Execution

### Task 7: Implement red-first contract, path, and activation rules

**Files:**
- Create: `tests/test_capability_execution_contract.py`
- Create: `tests/test_accountability_path_rules.py`
- Create: `video_pipeline_core/capability_execution.py`

- [ ] **Step 1: Write contract activation tests**

Cover: tracked unique companion, no companion legacy, malformed/unsupported
invoked companion, dirty/untracked companion, duplicate `work_order_id`,
duplicate normalized `work_order_path`, conflicting versions, run-root match
with omitted CLI contract, and strict-control artifacts without reference.

The public activation result is fixed:

```json
{
  "ok": true,
  "strict": true,
  "contract_path": "docs/construction-guides/work-orders/example.execution.json",
  "contract_sha256": "64 hex chars",
  "contract_source_commit": "40 hex chars",
  "run_root": ".tmp/example",
  "accountability_root": ".tmp/example/accountability",
  "contract": {},
  "errors": []
}
```

Errors are sorted objects with `code`, `path`, `message`. Activation codes are
`contract_not_tracked`, `contract_worktree_drift`, `contract_json_invalid`,
`contract_version_unsupported`, `contract_duplicate_work_order_id`,
`contract_duplicate_work_order_path`, `contract_run_root_conflict`,
`strict_contract_argument_missing`, and `strict_contract_reference_missing`.

- [ ] **Step 2: Write Windows/portable path tests**

Reject absolute, drive, UNC, backslash, empty component, `..`, case collision,
and symlink/junction escape. Test exact and directory-prefix owner zones,
deleted tombstones, repository containment, and POSIX stored spelling.

- [ ] **Step 3: Write canonical JSON/hash tests**

Assert sorted keys, `ensure_ascii=False`, compact separators, LF, explicit
self-hash exclusion, and stable SHA-256.

- [ ] **Step 4: Run RED**

```powershell
C:/Users/user/miniconda3/python.exe -m unittest tests.test_capability_execution_contract tests.test_accountability_path_rules -v
```

Expected: exit `1` because the module/API does not exist.

- [ ] **Step 5: Implement and green canonical JSON/path rules only**

Implement:

```python
def canonical_json_bytes(payload: dict, *, self_hash_field: str | None = None) -> bytes: ...
def normalize_repo_path(repo_root: Path, raw: str) -> str: ...
def hash_file(path: Path) -> str: ...
```

Run `tests.test_accountability_path_rules`; expected exit `0`. Activation
tests remain RED.

- [ ] **Step 6: Implement committed companion discovery only**

Implement:

```python
def discover_execution_companions(repo_root: Path) -> list[dict]: ...
def load_execution_contract(repo_root: Path, contract_path: str | Path) -> dict: ...
```

Use `git ls-files docs/construction-guides/work-orders/*.execution.json`,
`git rev-list -1 HEAD -- <path>`, and `git show <commit>:<path>`. Require
working tree and index bytes to match the committed blob. Run the activation
tests scoped to malformed/untracked/dirty/duplicate cases; expected exit `0`.

- [ ] **Step 7: Implement strict resolution and schema validation**

```python
def resolve_strict_contract(repo_root: Path, run_root: Path, contract_path: str | Path | None) -> dict: ...
def validate_execution_contract(repo_root: Path, contract: dict, catalog: dict) -> list[dict]: ...
```

Use argv lists, replace only `{python}` with `sys.executable`, and expose no
route choice.

- [ ] **Step 8: Run Task 7 GREEN**

Run the Task 7 command. Expected: exit `0`.

- [ ] **Step 9: Commit Task 7**

```powershell
git add video_pipeline_core/capability_execution.py tests/test_capability_execution_contract.py tests/test_accountability_path_rules.py
git commit -m "feat: validate accountable execution contracts"
```

### Task 8: Implement initialization, reservation, receipts, and continuity

**Files:**
- Create: `tests/test_capability_execution_receipts.py`
- Modify: `video_pipeline_core/capability_execution.py`

- [ ] **Step 1: Write contract-reference RED tests**

Assert exclusive initialization, UUIDv4, committed path/hash/source commit,
initial/protected hashes, empty control root, and refusal to reinitialize. The
reference is exactly:

```json
{
  "artifact_role": "accountability_contract_reference",
  "version": 1,
  "run_instance_id": "UUIDv4",
  "run_root": ".tmp/example",
  "contract_path": "docs/construction-guides/work-orders/example.execution.json",
  "contract_sha256": "SHA-256",
  "contract_source_commit": "git SHA",
  "initialized_at": "RFC3339"
}
```

Run the initialization test class; expected exit `1`.

- [ ] **Step 2: Implement and green initialization only**

```python
def initialize_accountable_run(repo_root: Path, contract_path: Path) -> dict: ...
```

Publish with exclusive create; no overwrite or route choice. Re-run the
initialization class; expected exit `0`.

- [ ] **Step 3: Write reservation/concurrency RED tests**

Assert reservation exists before child launch; second invocation never starts
the child; stale reservation is non-retryable UNKNOWN; attempts are
consecutive/bounded; PASS is terminal. Reservation schema:

```json
{
  "artifact_role": "accountability_attempt_reservation",
  "version": 1,
  "run_instance_id": "UUID",
  "contract_path": "repo-relative path",
  "contract_sha256": "SHA-256",
  "step_id": "stable step ID",
  "capability_id": "registered Capability ID",
  "attempt": 1,
  "argv_sha256": "SHA-256 of canonical argv JSON",
  "process_id": 1234,
  "started_at": "RFC3339"
}
```

Run reservation tests; expected exit `1`.

- [ ] **Step 4: Implement and green exclusive reservation only**

```python
def reserve_attempt(repo_root: Path, contract: dict, step_id: str) -> dict: ...
```

Use `O_CREAT|O_EXCL`; return a structured error before any child process on
collision. Re-run reservation tests; expected exit `0`.

- [ ] **Step 5: Write manifest continuity RED tests**

Cover baseline -> pre -> post -> next-pre -> final, tombstones, undeclared
output, protected drift, and child writes into the control subtree. Manifest:

```json
{
  "artifact_role": "accountability_state_manifest",
  "version": 1,
  "run_instance_id": "UUID",
  "scope": "production | child_control",
  "captured_at": "RFC3339",
  "files": [{"path": "repo-relative POSIX", "state": "present | deleted", "sha256": "SHA-256 or null"}]
}
```

Run manifest tests; expected exit `1`.

- [ ] **Step 6: Implement and green manifest snapshots only**

```python
def snapshot_monitored_state(repo_root: Path, contract: dict, *, scope: str) -> dict: ...
def compare_manifest_chain(expected: dict, actual: dict) -> list[dict]: ...
```

Exclude the reserved control subtree from production state but audit it
separately. Re-run manifest tests; expected exit `0`.

- [ ] **Step 7: Write execution/receipt/retry RED tests**

Require `shell=False`, repo cwd, frozen argv/timeout/input hashes, output hashes,
child-control equality, failure class, and contract-derived retryability.
Receipt schema:

```json
{
  "artifact_role": "accountability_step_receipt",
  "version": 1,
  "run_instance_id": "UUID",
  "contract_path": "repo-relative path",
  "contract_sha256": "SHA-256",
  "step_id": "stable step ID",
  "capability_id": "registered Capability ID",
  "attempt": 1,
  "reservation_path": "repo-relative path",
  "reservation_sha256": "SHA-256",
  "command_argv": ["resolved argv"],
  "started_at": "RFC3339",
  "completed_at": "RFC3339",
  "duration_sec": 0.0,
  "exit_code": 0,
  "status": "pass | fail | unknown | stopped",
  "failure_class": null,
  "retryable": false,
  "input_hashes": {},
  "output_hashes": {},
  "changed_paths": [],
  "pre_manifest_path": "repo-relative path",
  "pre_manifest_sha256": "SHA-256",
  "post_manifest_path": "repo-relative path",
  "post_manifest_sha256": "SHA-256",
  "source_tool": "video_tools.py capability-run"
}
```

Allow only listed `LOCAL_*` FAIL/UNKNOWN retries; reject all structural/STOPPED
and unlisted classes. Run execution/retry tests; expected exit `1`.

- [ ] **Step 8: Implement and green one-step execution**

```python
def run_capability_step(repo_root: Path, contract_path: Path, step_id: str) -> dict: ...
```

Use `subprocess.run(..., shell=False, cwd=repo_root, timeout=...)`; do not retry
or select next steps. Re-run execution/retry tests; expected exit `0`.

- [ ] **Step 9: Write RED closure-facing validator tests**

Add class `AccountableRunEvidenceValidatorTest` asserting the exact six-key
shape below, deterministic ordering, and no filesystem writes when validating
a complete in-memory/temp-run evidence set. Run that class; expected exit `1`
because the function is absent.

- [ ] **Step 10: Add the closure-facing pure evidence validator**

```python
def validate_accountable_run_evidence(
    repo_root: Path, contract: dict, catalog: dict
) -> dict:
    """Return ok, tool_entries, decision_entries, final_state, errors, warnings."""
```

Return exactly those six keys. This function reads evidence and never writes
trace/decision artifacts; Chunk 4 consumes it.

- [ ] **Step 11: Run GREEN and adjacent contract tests**

```powershell
C:/Users/user/miniconda3/python.exe -m unittest tests.test_capability_execution_contract tests.test_capability_execution_receipts tests.test_accountability_path_rules -v
```

Expected: exit `0`.

- [ ] **Step 12: Commit Task 8**

```powershell
git add video_pipeline_core/capability_execution.py tests/test_capability_execution_receipts.py
git commit -m "feat: record accountable capability receipts"
```

### Task 9: Register the one thin CLI surface

**Files:**
- Modify: `video_tools.py`
- Modify: `video_pipeline_core/tool_command_catalog.py`
- Modify: `tests/test_video_tools_command_catalog.py`
- Modify: `tests/test_dispatch_capabilities.py` only if CLI catalog integration
  requires it.

- [ ] **Step 1: Write RED CLI tests**

Test dispatch/parser/manifest classification for:

```text
capability-run --initialize --contract <path> --json
capability-run --contract <path> --step-id <id> --json
```

Require exactly one of initialize/step ID, structured JSON, nonzero on invalid
contract, and no route-selection argument.

- [ ] **Step 2: Run RED**

```powershell
C:/Users/user/miniconda3/python.exe -m unittest tests.test_video_tools_command_catalog tests.test_dispatch_capabilities -v
```

Expected: exit `1` for missing command only.

- [ ] **Step 3: Add handler/parser/dispatch/catalog group**

The handler delegates to `capability_execution.py`; it contains no duplicate
validation or orchestration. Add `capability-run` to `COMMAND_GROUPS` and the
runtime dispatch manifest.

- [ ] **Step 4: Run GREEN and combined Phase C tests**

```powershell
C:/Users/user/miniconda3/python.exe -m unittest tests.test_capability_execution_contract tests.test_capability_execution_receipts tests.test_accountability_path_rules tests.test_video_tools_command_catalog tests.test_dispatch_capabilities -v
```

Expected: exit `0`.

- [ ] **Step 5: Commit Task 9 clean scope**

```powershell
git add video_pipeline_core/tool_command_catalog.py video_tools.py tests/test_video_tools_command_catalog.py tests/test_dispatch_capabilities.py
git commit -m "feat: add accountable capability execution"
```

---

## Chunk 4: Strict Closure, Forward Fixture, And Final Acceptance

### Task 10: Extend no-skip closure without breaking legacy runs

**Files:**
- Modify: `video_pipeline_core/no_skip_execution_trace.py`
- Modify: `tools/no_skip_execution_trace.py`
- Modify: `video_pipeline_core/route_closure_integrity.py` only as bounded by
  failing tests.
- Modify: `tests/test_no_skip_execution_trace.py`
- Modify: `tests/test_route_closure_integrity.py`
- Extend: `tests/test_capability_execution_contract.py`

- [ ] **Step 1: Write strict/legacy RED tests**

Cover strict `--contract`, run-root companion discovery, no strict-to-legacy
fallback, immutable reference, reservations/receipts, dependency ordering,
catalog-derived class/role, input/output hashes, verifier step IDs,
baseline/pre/post/final continuity, approval flags, and legacy v1 readability.

- [ ] **Step 2: Write decision-sidecar RED tests**

Cover exact contract/run-instance/dependency receipt set/hash, post-dependency
timestamp, missing agent UNKNOWN, missing owner WAITING, copied/stale sidecars,
agent substitution for owner, deterministic/gate substitution for agent, and
no production writes by decision actors.

Agent sidecar required keys are `artifact_role=agent_attestation`, `version`,
`run_instance_id`, `execution_contract_path`,
`execution_contract_sha256`, `requirement_id`, `step_id`, `capability_id`,
`actor_type=agent`, `agent_run_id`, optional proven `model`,
`reviewed_evidence[]`, `dependency_receipts[]`, `judgment`, non-empty
`blind_spots[]`, `proposed_findings[]`, and `attested_at`. Owner sidecar keys
are `artifact_role=owner_decision`, `version`, the same run/contract/requirement
and dependency bindings, `scope`, `decision` in
`approve|revise|reject|delegate`, non-empty `evidence_refs[]`,
`verbatim_owner_text`, and `decided_at`. Each dependency item has exact
`step_id`, receipt `path`, `sha256`, and `completed_at`.

- [ ] **Step 3: Write derived trace tests**

Assert v2 has `tool_entries` and `decision_entries`, no receipt fields on
decision entries, execution class/role from live Catalog, and the closure
meta-gate outside the step list.

The closure-facing validator from Task 8 returns:

```json
{
  "ok": true,
  "tool_entries": [{"step_id": "fixture.material", "receipt_path": "...", "receipt_sha256": "..."}],
  "decision_entries": [{"requirement_id": "fixture.review", "actor_class": "agent", "status": "present"}],
  "final_state": "WAITING_OWNER_ACCOUNTABILITY_FIXTURE",
  "errors": [],
  "warnings": []
}
```

Add an exact assertion that `set(result) == {"ok", "tool_entries",
"decision_entries", "final_state", "errors", "warnings"}`. The derived
`pipeline_execution_trace.json` adds artifact/version/run/contract metadata but
copies those two entry arrays without inventing receipt fields for decisions.

- [ ] **Step 4: Run RED**

```powershell
C:/Users/user/miniconda3/python.exe -m unittest tests.test_capability_execution_contract tests.test_no_skip_execution_trace tests.test_route_closure_integrity -v
```

Expected: exit `1` only for strict closure additions.

- [ ] **Step 5: Implement two-phase sealing**

Keep existing legacy evaluation. For strict runs, resolve the committed
contract/reference, validate via `capability_execution`, capture final state,
derive trace v2, and write only trace/decision/audit under the accountability
root. Extend CLI with optional `--contract`; a matching run-root companion or
control artifact makes strict validation mandatory even when omitted.

- [ ] **Step 6: Preserve and extend gate authenticity**

Keep `pipeline_tool_generated` acceptance and block
`run_local_worker_generated`, `copied_from_prior`, and unknown. Add observable
gate final-state purity without claiming OS sandbox protection.

- [ ] **Step 7: Run GREEN**

Run the Task 10 command. Expected: exit `0` and existing legacy tests unchanged.

- [ ] **Step 8: Commit strict closure clean scope**

```powershell
git add video_pipeline_core/no_skip_execution_trace.py tools/no_skip_execution_trace.py tests/test_no_skip_execution_trace.py tests/test_capability_execution_contract.py
```

Add `video_pipeline_core/route_closure_integrity.py` and
`tests/test_route_closure_integrity.py` only if their bounded diff is required
and green. Exclude every Phase A dirty path.

```powershell
git commit -m "feat: enforce accountable no-skip closure"
```

### Task 11: Build committed positive and negative fixtures

**Files:**
- Create: `tests/fixtures/accountability_forward_v1/**`
- Create:
  `docs/construction-guides/work-orders/2026-07-13-single-entry-forward-accountability-acceptance.execution.json`

- [ ] **Step 1: Create minimal material JSON fixtures with `apply_patch`**

Create `material/segment_contract.json` exactly as:

```json
{"artifact_role":"segment_contract","version":1,"segments":[{"segment":1,"requested_duration_sec":4,"material_fit":{"need_refs":["nd_opening"]}},{"segment":2,"requested_duration_sec":6,"material_fit":{"need_refs":["nd_closing"]}}]}
```

Create `material/project_material_map.json` with two assets:

```json
{"artifact_role":"project_material_map","version":1,"assets":[{"asset_id":"clip-a","asset_type":"video","source":"materials/a.mp4","scenes":[{"scene_index":0,"start":2.0,"end":8.0,"caption":"opening cohort","satisfies":[{"need_id":"nd_opening","status":"accepted"}]}]},{"asset_id":"clip-b","asset_type":"video","source":"materials/b.mp4","scenes":[{"scene_index":0,"start":10.0,"end":20.0,"caption":"closing group","satisfies":[{"need_id":"nd_closing","status":"accepted"}]}]}]}
```

Expected tool output is an `ok=true`, two-clip, 10.0-second rough-cut plan; no
raw media is read or rendered.

- [ ] **Step 2: Create minimal audio fixtures**

Copy `assets/sfx/riser_1.wav` to both fixture WAV paths using `Copy-Item` in one
PowerShell operation:

```powershell
New-Item -ItemType Directory -Force tests/fixtures/accountability_forward_v1/audio | Out-Null
Copy-Item -LiteralPath assets/sfx/riser_1.wav -Destination tests/fixtures/accountability_forward_v1/audio/source_speech.wav
Copy-Item -LiteralPath assets/sfx/riser_1.wav -Destination tests/fixtures/accountability_forward_v1/audio/background_music.wav
```

Create `audio/audio_handoff_acceptance.json`:

```json
{"artifact_role":"audio_handoff_acceptance","version":1,"ok":true,"accepted_track_count":1}
```

Create `audio/audio_mix_plan.json`:

```json
{"artifact_role":"audio_mix_plan","version":1,"ready_for_mix":true,"rendered":false,"tracks":[{"section_id":"technical_fixture","candidate_id":"fixture_music","audio_file":"background_music.wav","role":"music_main","ducking_policy":"none","source_type":"repository_test_asset","license_status":"repository_fixture"}]}
```

Expected output is a playable 1.2-second `final_audio.wav` plus
`audio_mix_report.json`. `source_speech.wav` is protected fixture evidence but
is intentionally not mixed; this test makes no speech/ducking or rights claim.

- [ ] **Step 3: Write fixture manifest and four negative shapes**

Use canonical SHA-256 for every committed fixture. Negative fixtures cover
missing step, self-authored gate, stale agent sidecar, and copied owner sidecar.

Each negative directory contains `mutation.json` with one exact payload:

```json
{"mutation":"remove_required_receipt","expected_code":"missing_required_step"}
{"mutation":"inject_run_local_gate","expected_code":"self_authored_gate_artifact","classification":"run_local_worker_generated"}
{"mutation":"replace_agent_run_instance","expected_code":"stale_agent_decision_sidecar"}
{"mutation":"copy_owner_sidecar_from_other_run","expected_code":"copied_owner_decision_sidecar"}
```

`fixture_manifest.json` lists path/SHA-256 for every file except itself; the
committed execution companion protects the manifest's own SHA-256.

- [ ] **Step 4: Write the committed execution companion**

Use the exact run/accountability roots, Workbench protected hashes, material
and audio commands, decision requirements, attempts, dependencies, owner
zones, forbidden paths, and flags from design section 16.3. It must be valid
before commit and must not contain its own commit SHA.

The companion fields are fixed:

- `artifact_role=work_order_execution_contract`, `version=1`,
  `accountability_contract_version=1`;
- `work_order_id=single-entry-forward-accountability-long-task`;
- `work_order_path` is this plan's exact formal work-order path and
  `work_order_sha256` is computed with `Get-FileHash`;
- `run_root=.tmp/single_entry_forward_accountability_acceptance/forward` and
  `accountability_root=<run_root>/accountability`;
- initial run/owner manifests are empty;
- material step: capability
  `cap.material-map.material-rough-cut.v1`, exact command
  `{python} tools/material_rough_cut.py --contract <fixture contract>
  --project-map <fixture map> --out <run material/rough_cut_plan.json>`, inputs
  hashed, required output exact, no verifier IDs, one attempt, no retries;
- audio step: capability
  `cap.audio-director.audio-mix-plan-execute.v1`, depends on material, exact
  command `{python} tools/audio_mix_plan_execute.py --plan <fixture plan>
  --acceptance <fixture acceptance> --out-dir <run audio> --json`, hashed
  inputs, two exact outputs, one attempt, no retries;
- one agent requirement `fixture.technical-review` depends on both steps and
  writes the exact attestation path; one owner requirement `owner.final`
  depends on both and maps absence to
  `WAITING_OWNER_ACCOUNTABILITY_FIXTURE`;
- allowed owner zone is exact directory-prefix run root; forbidden exact paths
  are the six Workbench files; protected paths contain their frozen hashes,
  the formal work order, fixture manifest, and all positive fixture files;
- both approval flags are false.

Populate every hash with actual 64-hex output; no placeholder string may remain.

- [ ] **Step 5: Validate fixture shapes before commit**

Add
`AccountabilityForwardFixtureTest.test_fixture_and_companion_schema` to
`tests/test_capability_execution_contract.py`; it parses every JSON, verifies
fixture-manifest hashes, required paths/commands/IDs, work-order hash, protected
hashes, and absence of placeholder tokens.

```powershell
C:/Users/user/miniconda3/python.exe -m unittest tests.test_capability_execution_contract.AccountabilityForwardFixtureTest.test_fixture_and_companion_schema -v
```

Expected: exit `0`.

- [ ] **Step 6: Commit fixture/companion only**

```powershell
git add tests/fixtures/accountability_forward_v1 docs/construction-guides/work-orders/2026-07-13-single-entry-forward-accountability-acceptance.execution.json tests/test_capability_execution_contract.py
git commit -m "test: add accountable forward fixtures"
```

### Task 12: Run the real strict forward test

**Files:**
- Create runtime evidence only:
  `.tmp/single_entry_forward_accountability_acceptance/forward/**`
- Create command logs:
  `.tmp/single_entry_forward_accountability_acceptance/final/logs/**`

Before Step 1:

```powershell
New-Item -ItemType Directory -Force .tmp/single_entry_forward_accountability_acceptance/final/logs | Out-Null
```

For every native command in Tasks 12-13, capture evidence with this exact
suffix, substituting the table's name:

```powershell
2>&1 | Tee-Object ".tmp/single_entry_forward_accountability_acceptance/final/logs/<name>.log"; $code=$LASTEXITCODE; [IO.File]::WriteAllText(".tmp/single_entry_forward_accountability_acceptance/final/logs/<name>.exit.txt","$code`n",[Text.UTF8Encoding]::new($false)); if($code -ne 0){throw "<name> failed: $code"}
```

Use names `initialize`, `material_step`, `audio_step`, `attestation_json`,
`strict_no_skip`, `negative_fixtures`, `focused`, `workbench`, `skill_audit`,
`doc_audit`, `route_audit`, `commands_manifest`, `diff_check`, and
`full_suite`. The final worker report hashes these logs and exit files.

- [ ] **Step 1: Initialize and execute the two exact steps**

```powershell
C:/Users/user/miniconda3/python.exe video_tools.py capability-run --initialize --contract docs/construction-guides/work-orders/2026-07-13-single-entry-forward-accountability-acceptance.execution.json --json
C:/Users/user/miniconda3/python.exe video_tools.py capability-run --contract docs/construction-guides/work-orders/2026-07-13-single-entry-forward-accountability-acceptance.execution.json --step-id fixture.material-rough-cut --json
C:/Users/user/miniconda3/python.exe video_tools.py capability-run --contract docs/construction-guides/work-orders/2026-07-13-single-entry-forward-accountability-acceptance.execution.json --step-id fixture.audio-mix-plan-execute --json
```

Expected: all exit `0`; one reference and two PASS receipts.

- [ ] **Step 2: Perform the actual technical agent review**

Read both outputs and receipts. Write only the declared attestation with current
run-instance/contract/dependency hashes, bounded judgment, and non-empty blind
spots. Parse it with the pinned `json.tool` command; expected exit `0`.

```powershell
C:/Users/user/miniconda3/python.exe -m json.tool .tmp/single_entry_forward_accountability_acceptance/forward/accountability/attestations/fixture.technical-review.json
```

- [ ] **Step 3: Seal and verify legal WAITING owner state**

```powershell
C:/Users/user/miniconda3/python.exe tools/no_skip_execution_trace.py --contract docs/construction-guides/work-orders/2026-07-13-single-entry-forward-accountability-acceptance.execution.json --run .tmp/single_entry_forward_accountability_acceptance/forward --out-dir .tmp/single_entry_forward_accountability_acceptance/forward/accountability --json
```

Expected exit `0`,
`ok=true`, `WAITING_OWNER_ACCOUNTABILITY_FIXTURE`, and both approval flags
false.

- [ ] **Step 4: Run the four pinned negative tests**

```powershell
C:/Users/user/miniconda3/python.exe -m unittest tests.test_capability_execution_contract.AccountabilityNegativeFixtureTests.test_missing_required_step tests.test_capability_execution_contract.AccountabilityNegativeFixtureTests.test_self_authored_gate tests.test_capability_execution_contract.AccountabilityNegativeFixtureTests.test_stale_agent_sidecar tests.test_capability_execution_contract.AccountabilityNegativeFixtureTests.test_copied_owner_sidecar -v
```

Expected: exit `0`, four passing tests, and their asserted blocking codes.

### Task 13: Run compatibility, real audits, and one full suite

**Files:**
- Create runtime evidence only under `.tmp/.../final/**`
- Do not modify Workbench production files.

- [ ] **Step 1: Run combined focused/adjacent tests**

```powershell
C:/Users/user/miniconda3/python.exe -m unittest tests.test_pipeline_skill_boundaries tests.test_doc_reference_hygiene tests.test_interactive_skill_flow_docs tests.test_skill_index tests.test_accountability_retirement tests.test_skill_tool_contract_parser tests.test_skill_tool_contracts tests.test_dispatch_capabilities tests.test_video_tools_command_catalog tests.test_capability_execution_contract tests.test_capability_execution_receipts tests.test_accountability_path_rules tests.test_no_skip_execution_trace tests.test_route_closure_integrity -v
```

Expected: exit `0`.

- [ ] **Step 2: Run Workbench compatibility**

```powershell
C:/Users/user/miniconda3/python.exe -m unittest tests.test_workbench_handoff tests.test_preview_timeline tests.test_workbench_contract_sync tests.test_workbench_draft_rerender -v
```

Expected: exit `0`. Re-read all six protected hashes; exact match required.

- [ ] **Step 3: Run the three real audits**

```powershell
C:/Users/user/miniconda3/python.exe tools/skill_tool_contract_audit.py --skills-dir skills --tools-dir tools --out .tmp/single_entry_forward_accountability_acceptance/final/skill_tool_contract.json
C:/Users/user/miniconda3/python.exe tools/doc_reference_hygiene.py --repo-root . --out .tmp/single_entry_forward_accountability_acceptance/final/doc_reference_hygiene.json
C:/Users/user/miniconda3/python.exe tools/route_closure_integrity.py --repo-root . --out .tmp/single_entry_forward_accountability_acceptance/final/route_closure_integrity.json
C:/Users/user/miniconda3/python.exe video_tools.py commands-manifest --out .tmp/single_entry_forward_accountability_acceptance/final/commands_manifest.json
```

Expected: each exits `0`; the three audit reports have `ok=true`; command
manifest has no unclassified command. Compare post Capability/command sets to
baseline through the retirement table; no Capability ID may disappear in this
work order.

- [ ] **Step 4: Run `git diff --check`**

```powershell
git diff --check
```

Expected exit `0`; CRLF informational warnings are allowed, whitespace errors
are not.

- [ ] **Step 5: Run the full suite exactly once**

```powershell
C:/Users/user/miniconda3/python.exe -m unittest discover -s tests
```

Use timeout `1,200,000 ms`. Expected exit `0`. If it fails or times out, stop
at the last green commit and do not patch or rerun the full suite in this work
order.

### Task 14: Close at integrator review, not delivery

**Files:**
- Update runtime only:
  `.tmp/single_entry_forward_accountability_acceptance/campaign_status.json`
- Create runtime only:
  `.tmp/single_entry_forward_accountability_acceptance/final/worker_report.md`
- Modify, keep in Phase A unstaged unit: `HANDOFF_CURRENT.md`

- [ ] **Step 1: Re-read all frozen evidence**

Verify fixture, contract, Workbench, receipt, attestation, trace, decision,
audit, and test-log hashes. Verify existing dirty/untracked user files remain
present and were not staged or reset.

- [ ] **Step 2: Finalize the retirement table**

For each touched obsolete/misleading candidate, record `delete`,
`legacy_read_only`, or `keep`, with live-consumer and legacy-reader evidence.
Assert catalog delta matches approved delete rows exactly.

- [ ] **Step 3: Update current state**

Set runtime campaign state and HANDOFF authoritative state to
`WAITING_INTEGRATOR_FINAL_REVIEW`. Keep
`human_creative_approval=false` and `final_delivery_claimed=false`.

- [ ] **Step 4: Write the bounded worker report**

Include commits, exact command/exit summaries, RED/GREEN evidence, artifacts
and hashes, retirement table, deviations, skipped items, blind spots, full
suite result, pre/post dirty tree, and uncommitted authority-file paths. Do not
claim final delivery or independently commit pre-existing dirty authority
files.

- [ ] **Step 5: Integrator-only reconciliation and Codebase Memory refresh**

The Luna worker stops after Step 4. The manager/integrator independently
reviews and commits the complete Phase A authority/evaluator/test unit, reruns
its focused tests, then refreshes Codebase Memory exactly once using
`index_repository` with repo path `C:/Users/user/Desktop/video_pipeline`, mode
`fast`, and persistence enabled. Verify `index_status=ready`; if MCP is
unavailable, record UNKNOWN and do not treat it as code failure.

---

## Stop-Loss Summary

Stop at the last green commit and report when any of these occurs:

- a required change falls outside the listed owner zones;
- a pre-existing dirty authority file changes before its assigned Phase A edit;
- protected Workbench/fixture hash drifts;
- the same failure class recurs after one LOCAL correction;
- a structural path, contract, concurrency, gate-purity, strict-fallback, or
  actor-binding failure appears;
- deletion evidence has a live consumer, required legacy reader, or UNKNOWN;
- a focused/adjacent acceptance command remains nonzero;
- the single final full-suite run fails or times out.

No stop-loss may be bypassed by a run-local helper, copied gate, relaxed test,
private renderer, compatibility shim, or manual artifact that impersonates a
registered capability.
