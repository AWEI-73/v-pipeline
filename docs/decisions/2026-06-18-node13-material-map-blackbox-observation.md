# Node 1-13 Backend Flow + Material Map Skill Blackbox Observation

Date: 2026-06-18

## Scope

This was an observation-only run. Two subagents acted as black-box operators and
were not allowed to edit tracked repository code or commit changes.

- Backend Node 1-13 replay worker output:
  `.tmp/node13_backend_flow_worker/node13_flow_report.json`
- Material-map genericity worker output:
  `.tmp/material_map_skill_generic_worker/material_map_skill_report.json`

The goal was to test whether the current backend flow and material-map skill can
be driven by contracts/artifacts rather than session memory.

## Executive Result

The material-map lifecycle skill passed the genericity test.

The full Node 1-13 replay did not converge when using
`.tmp/srp_real67_fuller_replay` as the source artifact root. This is not evidence
that the render engine is broken. The failure is that the source root is a review
artifact bundle, not a complete lifecycle run package: it has a
`project_material_map.json` containing `satisfies` edges, but it does not include
the matching `material_needs.json`.

That makes `material-map-lifecycle` correctly fail closed at Node 2.

## Backend Flow Findings

### B1. Workflow command catalog is coherent

`python video_tools.py workflow-manifest` returned `missing_commands=[]`.

The exposed workflow groups are:

- `run_setup`
- `material_map_lifecycle`
- `canonical_build`
- `workbench_review_rerender`

### B2. Node 2 failed closed on incomplete artifacts

Command:

```powershell
python video_tools.py material-map-lifecycle --out-dir .tmp/node13_backend_flow_worker/material_lifecycle --project-map .tmp/node13_backend_flow_worker/project_material_map.json
```

Observed result:

- exit code: `1`
- stage: `invalid`
- reason: the project map contains `satisfies` edges but no declared
  `material_needs.json`

Interpretation:

This is the correct safety behavior. A satisfaction edge cannot be trusted
without the canonical needs it references.

### B3. Existing Workbench handoff was stale

The copied `workbench_handoff.json` failed validation because report artifact
size/hash values no longer matched current files.

After deterministic regeneration inside the worker root, validation passed:

```powershell
python video_tools.py workbench-handoff-validate .tmp/node13_backend_flow_worker --out .tmp/node13_backend_flow_worker/workbench_handoff_validation.json
```

This means handoff is intentionally content-addressed. If a draft report changes,
handoff must be regenerated rather than reused.

### B4. Node 11-13 Workbench rerender path passed

After regenerating handoff, the worker ran:

```powershell
python video_tools.py workbench-draft-rerender .tmp/node13_backend_flow_worker --out node13_workbench_rerender.mp4 --report-out .tmp/node13_backend_flow_worker/node13_workbench_rerender_report.json --effects
```

Observed:

- exit code: `0`
- rendered clips: `43`
- output: `.tmp/node13_backend_flow_worker/node13_workbench_rerender.mp4`
- canonical `timeline.json`, `project_material_map.json`, and `final.mp4` stayed
  unchanged

### B5. Current gap for full Node 1-13 replay

The current repo has tools for the pieces, but `.tmp/srp_real67_fuller_replay`
is not a complete replay package for Node 1-13.

To make this test repeatable as one command, the acceptance fixture/tool needs to
package or generate:

- `material_needs.json`
- `project_material_map.json` or `materials_db.json`
- `segment_contract.json` when testing canonical build
- workbench draft artifacts when testing human-edit handoff

Without this, a post-render review folder can validate Workbench rerender but
cannot validate the full material-map lifecycle from Node 1.

## Material Map Skill Genericity Findings

The material-map worker created generic fixtures that did not use 67th footage or
Gemini-specific vocabulary. Results:

### M1. Existing-material-first

Input: maps only, no needs.

Observed:

- stage: `await_requirements_discussion`
- `can_build=false`
- no invented needs
- no material delta

This matches the intended "inventory first, discuss requirements later" mode.

### M2. Script-first

Input: needs only, no maps.

Observed:

- stage: `await_material`
- `shooting_brief.json` produced
- `material_delta.json` produced
- missing must-have blocks build readiness

This matches the intended "script first, ask for material" mode.

### M3. Partial / hybrid

Input: needs plus one satisfying scene.

Observed:

- stage: `await_material`
- delta summary: one covered, one missing
- missing must-have blocks build readiness

This matches the intended partial lifecycle.

### M4. Invalid references fail closed

Two adversarial cases passed:

- dangling `satisfies.need_id` -> `invalid`, not `missing`
- blank `asset_id` -> `invalid`, no delta produced

This confirms the lifecycle distinguishes "not enough material" from "broken
reference graph."

## Reported Technical Debt

### T1. Console encoding can mislead skill-file review

During the first review pass, `skills/material-map.md` appeared corrupted when
read through the PowerShell console. Re-reading the file as explicit UTF-8 shows
the file content is valid and readable.

This is not a material-map skill defect. Future reviewers should read UTF-8
Markdown files with an explicit encoding before reporting text corruption.

### T2. Replay roots need declared artifact completeness

The pipeline is strict about canonical references. That is good, but it means
operator replay roots must be explicit about which lifecycle stage they represent:

- inventory-only root
- full material lifecycle root
- canonical build root
- workbench review/rerender root

Mixing these produces correct fail-closed behavior but poor operator experience.

## Recommended Next Step

Do not change core pipeline behavior yet.

Create a bounded `operator_flow_acceptance` fixture/tool that constructs a
complete run package before replaying it. It should make the stage explicit:

1. material-map generic lifecycle
2. canonical build when complete contract/needs/maps exist
3. workbench patch/handoff/rerender

The tool should fail with a clear "incomplete replay package" error when required
artifacts are absent, instead of making operators infer that from a Node 2
`invalid` result.
