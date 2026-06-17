# Decision: Dashboard and Workbench Integration Cleanup

Date: 2026-06-17
Status: accepted
Scope: dashboard/workbench/frontend-backend handoff
Superpowers phase: plan

## SPEC

Requirement:

The frontend must be consolidated around two clear surfaces: Dashboard for project/node/status review, and Workbench for interactive preview plus draft patching.

Why:

The backend pipeline now has material-map gates, BUILD planners, timeline preview, patch artifacts, subtitles, audio cues, and effect cues. Without a fixed frontend/backend contract, new UI work can accidentally blur review, editing, and canonical render responsibilities.

Direction:

Keep Dashboard and Workbench separate but connected. Dashboard remains read-oriented and shows run/node/handoff state. Workbench remains write-limited and produces draft artifacts only. Backend/agent workflows consume those artifacts and decide whether to revise contracts, rerender, reject a patch, or route to a future Node 14/effects workflow.

Non-goals:

- No Remotion dependency.
- No full browser NLE.
- No canonical output overwrite from Workbench.
- No new material-map gate.
- No new delivery gate.
- No heavy effects runtime.

## DO

Files / modules:

- `dashboard/dashboard_v1.*`: Dashboard review surface and Workbench entry/status link.
- `dashboard/workbench_native/*`: interactive preview and patch drafting surface.
- `tools/workbench_server.py`: write-limited Workbench API.
- `tools/preview_timeline.py`: preview timeline builder.
- `tools/timeline_patch.py`: timeline patch validation/application.
- `tools/workbench_patch_to_contract.py`: draft contract interpretation.
- `tools/workbench_handoff.py`: agent/backend handoff package.
- `docs/workbench-dashboard-integration.md`: integration contract.
- `dashboard/README.md`: local operator documentation.

Function-level plan:

- Stabilize Workbench layout and preserve existing editing behavior.
- Harden draft artifact ownership and canonical write blocking.
- Add Dashboard-to-Workbench handoff visibility without making Dashboard editable.
- Add a review report so an agent can inspect human edits without replaying the browser.
- Document startup, save, sync, and verification commands.

Data / interface changes:

- Preserve existing `preview_timeline.json`, `timeline_patch.json`, `patched_draft_timeline.json`, `workbench_contract_patch.json`, and `workbench_handoff.json` contracts.
- If a review report is added, it must be a new draft artifact and must not become canonical truth.

Migration / compatibility:

- Existing backend render remains ffmpeg/pipeline-owned.
- Existing Workbench URLs and patch files should remain backward compatible.
- No new frontend build system or npm dependency.

## VERIFY

Pre-checks:

- `git status --short`
- `node --check dashboard\workbench_native\workbench.js`
- `node --check dashboard\workbench_native\workbench_core.js`

Tests:

- `node tests\workbench_core_smoke.js`
- `python -m unittest tests.test_preview_timeline tests.test_workbench_server tests.test_timeline_patch -q`
- `python -m unittest discover -s tests -q`

Manual checks:

- Start `tools/workbench_server.py` against `.tmp\srp_real67_fuller_replay`.
- Open `http://localhost:8770/workbench`.
- Verify preview playback, material replacement, trim clamp, timeline scrolling, subtitles/audio/effect draft markers, save/sync.
- Verify canonical `timeline.json` and `final.mp4` hashes do not change after Workbench draft edits.

Regression risks:

- Workbench accidentally overwrites canonical artifacts.
- Dashboard becomes an editor and duplicates Workbench behavior.
- UI layout changes break timeline scrolling or preview centering.
- Patch/handoff reports drift from actual patch semantics.

## Decision Notes

Accepted because:

The backend is stable enough that uncontrolled frontend growth is now the bigger risk than missing features. A bounded integration cleanup creates a safer base for later material browser, effects, and Node 14 work.

Tradeoffs:

This delays new visual features, but it reduces future ambiguity. The user can still review and lightly edit, while the backend remains responsible for official output.

Open questions:

- Whether the existing untracked demo files should be ignored, moved to `scratch/`, or committed as references.
- Whether Dashboard and Workbench eventually share a visual shell or remain separate pages with links.
- Whether review reports should be required before backend rerender or remain optional.

## Git / Retrieval

Related files:

- `docs/superpowers/plans/2026-06-17-dashboard-workbench-integration-cleanup.md`
- `docs/workbench-dashboard-integration.md`
- `dashboard/README.md`
- `dashboard/dashboard_v1.html`
- `dashboard/dashboard_v1.css`
- `dashboard/dashboard_v1.js`
- `dashboard/workbench_native/index.html`
- `dashboard/workbench_native/workbench.css`
- `dashboard/workbench_native/workbench.js`
- `dashboard/workbench_native/workbench_core.js`
- `tools/workbench_server.py`
- `tools/preview_timeline.py`
- `tools/timeline_patch.py`
- `tools/workbench_patch_to_contract.py`
- `tools/workbench_handoff.py`

Related commits:

- `f4cb3a5` docs(workbench): plan dashboard integration cleanup
- `43ab9f3` docs(workbench): define dashboard integration contract
- `bcce523` fix(workbench): stabilize preview and timeline layout
- `b543a01` fix(workbench): harden draft artifact handoff
- `e330de1` feat(dashboard): surface workbench draft status

Graphify anchors:

- Dashboard
- Workbench
- preview_timeline
- timeline_patch
- workbench_handoff
- frontend-backend handoff

Search tags:

- decision-log
- spec-do-verify
- dashboard-workbench-integration
- native-preview-engine
- video-pipeline

## Implementation Closure

Date: 2026-06-17
Status: implemented

Completed chunks:

- Chunk 0: focused preflight for Workbench JS core and Python preview/server/patch tests.
- Chunk 1: integration contract documentation in `docs/workbench-dashboard-integration.md` and `dashboard/README.md`.
- Chunk 2: Workbench layout stabilization so the preview and timeline stay within the viewport and the timeline scrolls internally.
- Chunk 3: Workbench handoff hardening with `artifact_details` (`path`, `size_bytes`, `sha256`) and malformed patch JSON structured errors.
- Chunk 4: Dashboard read-only Workbench status integration. `/api/artifacts` now reports draft artifact presence, counts, sizes, and hashes under `workbench.draft_artifacts` / `workbench.draft_summary`; Dashboard displays that state without adding write endpoints.

Verification run:

- `node --check dashboard\dashboard_v1.js`
- `node --check dashboard\workbench_native\workbench.js`
- `node --check dashboard\workbench_native\workbench_core.js`
- `node tests\workbench_core_smoke.js`
- `python -m unittest tests.test_dashboard_server tests.test_workbench_server tests.test_workbench_handoff tests.test_preview_timeline tests.test_timeline_patch -q`
- `python -m unittest discover -s tests -q` -> 1441 tests OK
- `git diff --check`

Review result:

- Dashboard is still read-only.
- Workbench remains write-limited and draft-only.
- Canonical timeline/final render are not consumed or overwritten by Dashboard.
- Agent/backend handoff is discoverable from one API payload and one handoff artifact.

Still deferred:

- Full Dashboard visual redesign.
- Material library organization or physical asset relocation.
- Deep browser-side NLE rendering parity with ffmpeg.
- Node 14/effects authoring beyond draft intent markers.
- Automated consumption of Workbench drafts by official pipeline rerender.

## Continuation Closure

Date: 2026-06-17
Status: implemented

Added after the initial cleanup:

- `workbench_review_report.json` / `.md` draft artifacts summarize timeline,
  subtitle, audio cue, and effect intent edits for Agent review.
- `POST /api/workbench/review-report` writes only draft report artifacts.
- `workbench_handoff.json` and Dashboard draft status now include review report
  artifacts when present.
- `docs/material-organization-policy.md` fixes the material-map-first rule:
  folders are projections; source-file moves are not part of normal Workbench or
  Dashboard operation.

Verification run:

- `python -m unittest tests.test_workbench_review_report tests.test_workbench_server tests.test_workbench_handoff tests.test_dashboard_server -q`
- `node --check dashboard\dashboard_v1.js`
- `node --check dashboard\workbench_native\workbench.js`
- `node --check dashboard\workbench_native\workbench_core.js`
- `node tests\workbench_core_smoke.js`
- `python -m unittest discover -s tests -q` -> 1448 tests OK
- HTTP E2E against `.tmp\srp_real67_fuller_replay`: `POST /api/workbench/review-report` returned `ok=true`, `canonical_changed=false`, and Dashboard draft summary reported the review report artifacts as present.

Related commits:

- `ef5f626` feat(workbench): add draft review report
- `00bdf87` docs(materials): define map-first organization policy
- `0e2c041` fix(workbench): include review report in handoff status

## Control Index Closure

Date: 2026-06-17
Status: implemented

Added a top-level Control Index for the dashboard server:

- `/` and `/index.html` now serve `dashboard/index.html`.
- `/dashboard` keeps the existing read-only Dashboard surface.
- the Control Index displays artifact-root facts, final-video presence,
  Workbench start command, and Workbench draft readiness.
- the page is read-only and does not duplicate Workbench editing behavior or
  Dashboard review panels.

Verification run:

- `python -m unittest tests.test_dashboard_server -q`
- `node --check dashboard\index.js`
- `node --check dashboard\dashboard_v1.js`
- `git diff --check`

Boundary:

- Dashboard remains read-only.
- Workbench remains write-limited and draft-only.
- The Control Index is only a shell for routing and status visibility.
