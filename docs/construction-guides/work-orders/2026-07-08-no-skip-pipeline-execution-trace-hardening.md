# 2026-07-08 No-Skip Pipeline Execution Trace Hardening

## Goal

Prevent another "run-local handmade render" from being mistaken for a pipeline-aligned rehearsal.

The worker must trace the existing pipeline nodes that should have produced each artifact in the failed copyedit rehearsal, identify skipped or weak nodes, and harden the minimum route contract so future rehearsal candidates cannot pass on self-authored JSON claims alone.

This is primarily a trace-and-hardening task. Do not render another film and do not promote the failed rehearsal.

## Background Evidence

Failed product-quality rehearsal:

- `.tmp\copyedit_rehearsal_title_overlay_repair_20260708-181934\run\final_copyedit_rehearsal.mp4`
- `docs/construction-guides/work-orders/2026-07-08-copyedit-rehearsal-failure-review-report.md`
- `.tmp\copyedit_rehearsal_failure_review_20260708-183000\contact_sheet_10s.jpg`

The final MP4 is technically playable, but product quality failed because gates checked artifact existence/timing more than rendered output quality or reference alignment.

## Owner Zone

Editable paths:

- `video_pipeline_core/`
- `tools/`
- `tests/`
- `docs/branch-contract-registry.md`
- `docs/branch-contract-registry.json`
- `docs/video-pipeline-operating-map.md`
- `docs/pipeline-decision-tree.md`
- Fresh output root under `.tmp\no_skip_pipeline_execution_trace_*`
- `docs/construction-guides/work-orders/2026-07-08-no-skip-pipeline-execution-trace-hardening-report.md`

## Forbidden Zone

Read-only paths:

- `C:\Users\user\Downloads\微電影素材\_整理後`
- Existing `.tmp\` runs, except read-only inputs named in this work order
- `deliveries\`
- Existing final media artifacts
- `.env`, `.env.*`
- `.venv_voxcpm\`
- `reference repo\`
- VoxCPM reference/source repository
- `story_human_review_decision.json`
- `human_transcript_review_decision.json`
- Git branch/commit/push operations

## Required Pieces

1. Inventory existing pipeline entrypoints.
   - Find the actual tools/modules that own: story/script package, visual selection, effect factory, soundtrack/audio handoff, render/build, rendered product QA, delivery gate.
   - Prefer existing tools. Do not invent replacement flow if an owner already exists.

2. Build an execution trace audit for the failed rehearsal.
   - For each artifact in `.tmp\copyedit_rehearsal_title_overlay_repair_20260708-181934\run`, classify:
     - `pipeline_tool_generated`
     - `run_local_worker_generated`
     - `copied_from_prior`
     - `missing_owner_tool`
     - `unknown`
   - For each gate, state whether it was executable verification or a self-authored claim.

3. Add or harden the minimum no-skip contract.
   - Future rehearsal candidates must record a `pipeline_execution_trace.json`.
   - Canonical gate artifacts must record `generated_by` / `source_tool` / `inputs` / `command`.
   - A rendered rehearsal cannot be marked verified preview candidate when required gates are self-authored or missing owner tools.
   - Rendered product QA must inspect rendered frames/contact sheets, not only metadata timing.

4. Add red-first tests or smoke checks.
   - Use the failed rehearsal as fixture/read-only evidence.
   - Prove that a run-local `visual_selection_gate.json` or timing-only `title_effect_lifecycle_qa.json` cannot clear the no-skip trace.
   - Prove a missing rendered product QA blocks preview verification.

5. Produce a no-skip trace report for the failed rehearsal.
   - Write it under a fresh `.tmp\no_skip_pipeline_execution_trace_*` root.
   - Do not alter the failed run.

## Required Artifacts

In the fresh output root, write:

- `pipeline_tool_inventory.json`
- `failed_rehearsal_execution_trace.json`
- `gate_authenticity_audit.json`
- `rendered_product_quality_gap_report.json`
- `no_skip_contract_decision.json`
- `final_artifact_check.json`

If code/tools/tests are changed, also write/update:

- tests proving run-local self-authored gates fail the no-skip contract
- docs explaining the required execution trace

## Red-First Verification

Before implementation, run a failing test or smoke check showing the current system accepts or fails to detect at least one skipped gate from the failed rehearsal:

- self-authored `visual_selection_gate.json` accepted without a tool trace; or
- timing-only `title_effect_lifecycle_qa.json` accepted without rendered-frame visual QA; or
- `final_copyedit_rehearsal.mp4` can exist without `pipeline_execution_trace.json` and still appear artifact-check OK.

Record command, exit code, and failure in the final report.

## Acceptance Commands

Use the pinned interpreter:

```powershell
C:\Users\user\miniconda3\python.exe
```

Run focused tests for any new/changed no-skip trace or rendered product QA modules.

Run the impacted suite:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_delivery_gate tests.test_pipeline_home
```

If new tests are added, include them in the command.

Validate registry JSON:

```powershell
C:\Users\user\miniconda3\python.exe -c "import json; json.load(open('docs/branch-contract-registry.json', encoding='utf-8')); print('json ok')"
```

Run final artifact check for the fresh trace output root. It must verify required trace artifacts exist, JSON/Markdown UTF-8 is clean, and no render/final/approval artifact was created.

Run:

```powershell
git diff --check
```

Expected exit code: `0`, except existing CRLF warnings may be reported if already present.

## Stop-Loss Limits

Stop and report instead of broadening if:

- the only way to pass is to render another film;
- the trace requires modifying prior `.tmp` runs;
- a required pipeline owner tool does not exist;
- the fix would require rewriting the whole build system;
- the work would need Downloads/env/reference repo edits;
- the work would promote or package the failed render.

Missing owner tool is a valid result: record `missing_pipeline_node`, do not hand-roll a replacement.

## Delegated Decisions

- Exact module/tool names for no-skip trace if new code is required.
- Exact JSON schema for `pipeline_execution_trace.json`, as long as it records source tool, command, inputs, outputs, and trust level.
- Whether to implement hardening in delivery gate, pipeline_home, a new trace verifier, or a combination.
- Exact focused test file names.

## Final Report Requirements

Write:

```text
docs/construction-guides/work-orders/2026-07-08-no-skip-pipeline-execution-trace-hardening-report.md
```

Include:

- Files changed.
- Fresh trace output root.
- Red-first evidence.
- Pipeline tool inventory summary.
- Failed rehearsal gate-by-gate trace table.
- Which gates were self-authored claims vs executable verification.
- Code/test/doc hardening performed, if any.
- Acceptance commands and exit codes.
- Confirmation that no render, promotion, approval artifact, Downloads edit, prior run edit, env edit, or delivery package edit occurred.
- Deviations, blockers, and next recommended work.
