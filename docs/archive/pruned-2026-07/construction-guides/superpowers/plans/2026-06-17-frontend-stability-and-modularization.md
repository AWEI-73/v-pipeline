# Frontend Stability And Modularization Plan

Date: 2026-06-17

## Goal

Stabilize the Hermes Workbench frontend as the draft review and light editing base before doing broader backend cleanup. The Workbench must remain a draft-only tool: it previews material composition, writes patch artifacts, and hands decisions back to the Agent/pipeline without overwriting canonical timeline, material maps, final renders, or contracts.

## Current Boundary

The frontend has two product surfaces:

- Dashboard: project/node status, reports, and future orchestration.
- Workbench: interactive draft preview for timeline/material composition, subtitles, audio cue intent, effect intent, and patch handoff.

The Workbench is not a full NLE and is not the official renderer. Official output remains the ffmpeg BUILD path. Optional Workbench export may produce `workbench_export.mp4`, never `final.mp4`.

## Non-Goals

- No Remotion dependency or Remotion runtime.
- No visual redesign pass.
- No Node 14/effects engine implementation.
- No physical material relocation or folder reorganization.
- No canonical overwrite from browser edits.
- No backend material-map or M6 gate changes.

## Invariants

1. Canonical artifacts are read-only from the Workbench:
   - `timeline.json`
   - `project_material_map.json`
   - `material_needs.json`
   - `final.mp4`
   - canonical contracts
2. Browser edits only write draft artifacts:
   - `timeline_patch.json`
   - `subtitle_patch.json`
   - `audio_cue_patch.json`
   - `effect_intent_patch.json`
   - `patched_draft_timeline.json`
   - `workbench_contract_patch.json`
   - `workbench_handoff.json`
   - `workbench_review_report.json`
3. Contract sync is a draft translation, not an automatic SPEC rewrite.
4. The UI must degrade honestly when preview media is expensive or unavailable.
5. Tests must cover server/API contracts before frontend refactors.

## Implementation Chunks

### Chunk 1: Repository-Visible Plan

Add this plan and a decision log entry documenting the frontend boundary.

Acceptance:

- Plan exists under `docs/construction-guides/superpowers/plans/`.
- Decision log exists under `docs/archive/decisions/`.
- No code behavior changes.

### Chunk 2: Workbench Frontend Smoke Harness

Add a reproducible smoke harness that exercises the Workbench HTTP/frontend contract without manual browser work:

- Load `/workbench`.
- Load `/api/workbench/preview-timeline`.
- Save a duration patch through `/api/workbench/save-all`.
- Generate `/api/workbench/review-report`.
- Verify draft artifacts exist.
- Verify canonical artifacts remain byte-identical.

Acceptance:

- Focused unit tests run without external footage.
- CLI can run against any artifact root.
- Failures report a concrete stage.

### Chunk 3: API Client Module Extraction

Extract browser API calls from `workbench.js` into `workbench_api.js`.

Acceptance:

- `workbench.js` no longer hardcodes every Workbench endpoint fetch.
- `index.html` loads `workbench_api.js` before `workbench.js`.
- JS smoke tests verify endpoint and payload shapes.
- UI behavior and draft schemas do not change.

### Chunk 4: Documentation And Runbook

Update Workbench/Dashboard docs with the module boundary and smoke commands.

Acceptance:

- Docs explain Dashboard vs Workbench responsibility.
- Docs list the smoke command.
- Docs explicitly say material organization remains map-first and non-moving.

### Chunk 5: Verification And Commit

Run focused tests, JS checks, and full regression. Commit bounded changes.

Acceptance:

- `git diff --check` clean.
- Focused tests pass.
- Full regression passes, or any skipped/failed environment dependency is reported with exact reason.
- Commit message describes frontend stability scope.
