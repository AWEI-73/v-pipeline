# Canon 67 150-Second Picture-First L0 Execution Plan

> **For agentic workers:** REQUIRED: Use `superpowers:executing-plans` to
> execute this plan sequentially. Do not spawn subagents or add a second writer.

**Goal:** Inspect the complete Canon 67 real-material pool, build a stratified
evidence-backed candidate pool, and propose a coherent 150-second picture-only
sequence without rendering it.

**Architecture:** The committed accountability companion runs the deterministic
complete-pool inventory through `capability-run`. Registered Material Map and
perception Capabilities then generate bounded observation evidence. The worker
personally reviews that evidence and binds its L0 judgment to the current run in
an `agent_attestation`. Machine outputs remain observations; the proposal is an
agent decision awaiting integrator review.

**Source design:**
`docs/superpowers/specs/2026-07-13-canon67-150s-picture-first-longform-design.md`

**Formal work order:**
`docs/construction-guides/work-orders/2026-07-13-canon67-150s-picture-first-l0-selects.md`

**Execution companion:**
`docs/construction-guides/work-orders/2026-07-13-canon67-150s-picture-first-l0-selects.execution.json`

**Run root:** `.tmp/canon67_150s_picture_first_longform/l0`

---

## Task 1: Freeze authority, workspace, and source boundaries

- [ ] Read `AGENTS.md`, `RUNBOOK.md`, `HANDOFF_CURRENT.md`, the approved
  design, this plan, the work order, `skills/editing-loop-director.md` L0/L1
  sections, and `skills/material-map.md` completely where relevant.
- [ ] Record `git status --short --branch`, HEAD, source-root existence, source
  top-level folders, and hashes of all protected authorities under
  `l0/baseline/`.
- [ ] Confirm the canonical source root is
  `C:/Users/user/Downloads/微電影素材/_整理後` and remains read-only.
- [ ] Confirm the pre-created `campaign_status.json` and
  `control/stage0_material_scan_decision.json` hashes match the committed
  companion before initializing it.
- [ ] Stop if the work order, plan, spec, companion, or source root is missing;
  do not substitute a remembered path.

## Task 2: Run the accountable complete-pool inventory

- [ ] Initialize exactly once:

```powershell
C:/Users/user/miniconda3/python.exe video_tools.py capability-run --initialize --contract docs/construction-guides/work-orders/2026-07-13-canon67-150s-picture-first-l0-selects.execution.json --json
```

- [ ] Execute exactly once:

```powershell
C:/Users/user/miniconda3/python.exe video_tools.py capability-run --contract docs/construction-guides/work-orders/2026-07-13-canon67-150s-picture-first-l0-selects.execution.json --step-id L0.complete-pool-inventory --json
```

- [ ] Require a PASS receipt and a non-empty
  `accountable/material_inventory_summary.json`. Record actual counts; the
  design-time count of 198 is context, not a hard-coded result.
- [ ] Produce `inventory/exclusion_report.json` covering every approved
  exclusion family. Do not infer visual meaning from folder names.

## Task 3: Freeze the source ledger and stratified deep-review pool

- [ ] Build `inventory/source_ledger.json` for every discovered media item with
  relative path, absolute source path, media type, byte size, SHA-256, source
  category, and exclusion status. A short run-local evidence generator is
  allowed only under `l0/evidence_helpers/`, must be preserved, and must declare
  `artifact_role=evidence_only_pilot_helper`; it is not a production tool or a
  render bypass.
- [ ] Use deterministic metadata only to form a review pool of 72-96 assets.
  Stratify across all three target sections, at least twelve source categories,
  and both videos and stills where usable.
- [ ] Do not use catalog order, filename order, or `first N` as the final
  admission rule. Record the admission reason for every candidate and the
  reason every excluded/rejected item was not deeply reviewed.
- [ ] Stable asset IDs derive from source content SHA-256, never list position.
  Write `inventory/candidate_pool.materials_db.json` and
  `inventory/candidate_pool_selection_ledger.json`.

## Task 4: Generate and personally review real perception evidence

- [ ] Split the candidate DB into three section-shaped batches without
  duplicating assets. Run the registered
  `cap.material-map.material-understanding-matrix.v1` command for each batch,
  using actual media duration and a frame budget of at least 5 for videos.
- [ ] For every proposed video window, create temporal evidence that shows more
  than one timepoint; for every proposed still, inspect its real pixels. Reuse
  prior evidence only after exact source SHA-256 match and record the reuse.
- [ ] Open and review the resulting contact sheets and temporal strips. Record
  each viewed artifact path/hash and what was actually observed in
  `perception/review_access_ledger.json`.
- [ ] Write `perception/observations.json` with `observed_content`, shot scale
  when observable, motion/action, source window, section fit, evidence refs,
  exact/near-duplicate links, uncertainty, and whether the statement is
  objective evidence or agent judgment.
- [ ] Treat filename/folder `role_hints` as hints only. A proposal based only on
  them is a FAIL.

## Task 5: Compose the L0 150-second selects proposal

- [ ] Propose 40-60 distinct stable clip IDs across exactly these sections:
  `discipline_and_arrival`, `technical_craft`, and `life_and_bonds`.
- [ ] Make each section 45-55 seconds and the plan total 150.0 seconds within
  0.5 seconds. Video clip IDs bind source hash plus in/out window; still IDs
  bind source hash plus planned duration.
- [ ] Use at least six source categories. No raw asset repeats unless marked as
  an intentional motif; do not admit known duplicate, rejected, reference,
  dialogue-led, generated, prior-render, or excluded 66th-class material.
- [ ] For each selection record: stable ID, section, order, duration, source
  window, source hash/category/type, observed content, story function, evidence
  refs, duplicate status, and selection rationale.
- [ ] Write:
  `proposal/l0_selects_proposal.json`,
  `proposal/sequence_summary.md`,
  `proposal/rejected_and_duplicates.json`,
  `proposal/coverage_summary.json`, and
  `proposal/six_field_decision_record.json`.

## Task 6: Build the integrator review packet

- [ ] Generate section contact sheets and dense strips for any uncertain video
  windows. Do not render a 150-second candidate or storyboard MP4.
- [ ] Write `review/owner_review_index.md` with links grouped by section and a
  compact table of sequence position, stable ID, duration, category, and reason.
- [ ] Write `review/integrator_verdict_template.json` with `approve`, `revise`,
  and `reject` choices but leave the decision unset.
- [ ] Separate objective findings from taste findings and state all blind spots.

## Task 7: Bind the agent judgment and close accountability evidence

- [ ] After the inventory receipt exists, write the run-bound sidecar at
  `accountability/attestations/L0.selection-review.json`. It must use the exact
  current `run_instance_id`, contract path/hash, dependency receipt path/hash/
  completion time, actor type `agent`, reviewed evidence paths/hashes/locators,
  judgment, blind spots, proposed findings, and a valid post-receipt RFC3339
  timestamp.
- [ ] The attestation `step_id` is `L0.complete-pool-inventory` and its
  `capability_id` is `cap.material-map.material-quick-inventory.v1`.
- [ ] Run strict closure:

```powershell
C:/Users/user/miniconda3/python.exe tools/no_skip_execution_trace.py --run .tmp/canon67_150s_picture_first_longform/l0 --contract docs/construction-guides/work-orders/2026-07-13-canon67-150s-picture-first-l0-selects.execution.json --out-dir .tmp/canon67_150s_picture_first_longform/l0/final/strict_closure --json
```

- [ ] Require exit `0`, `ok=true`, the inventory receipt PASS, and the agent
  decision sidecar present. This certifies evidence continuity, not creative
  quality.

## Task 8: Validate and stop for integrator review

- [ ] Run focused tests only:

```powershell
C:/Users/user/miniconda3/python.exe -m unittest tests.test_capability_execution_contract tests.test_capability_execution_receipts tests.test_accountability_path_rules tests.test_skill_tool_contracts tests.test_material_understanding_matrix tests.test_material_wall_verdict_draft -v
```

- [ ] Run `video_tools.py registry-audit --json` and `git diff --check`.
- [ ] Verify source hashes still match; no `final.mp4`, timeline, subtitle,
  effect, audio mix, delivery artifact, or production-code change exists.
- [ ] Update runtime `campaign_status.json` and only the machine-state block plus
  current-work summary in `HANDOFF_CURRENT.md` to
  `WAITING_INTEGRATOR_150S_L0_SELECTS_REVIEW`.
- [ ] Write `final/worker_report.md` with commands/exits, receipts/hashes,
  evidence counts, exact dirty-tree preservation, corrections, deviations,
  blind spots, and both approval flags false.
- [ ] Do not run the full suite. Stop. The integrator, not the worker, decides
  whether L1 composition may begin.

