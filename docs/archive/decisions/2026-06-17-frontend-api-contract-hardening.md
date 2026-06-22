# Frontend API Contract Hardening

Date: 2026-06-17
Status: accepted

## Decision

Freeze the response shape for the two frontend coordination APIs currently used
by the Control Index, Dashboard, and Workbench:

- `GET /api/control/status`
- `GET /api/workbench/health`

This is a small consolidation increment. It does not merge frontend surfaces,
move backend modules, or change canonical rendering.

## Why

The project now has three frontend-facing surfaces:

- Control Index: top-level read-only cockpit;
- Dashboard: read-oriented review;
- Workbench: write-limited draft editor.

These surfaces are intentionally separate, but they need stable coordination
payloads. If the health/status payloads drift, future Dashboard integration work
will become guesswork.

## Contract Locked

`/api/control/status` must return:

- `artifact_role`
- `version`
- `artifact_root`
- `dashboard`
- `workbench`
- `final_video`
- `timeline`
- `recommended_next_action`

`/api/workbench/health` must return:

- `artifact_role`
- `version`
- `status`
- `artifact_root`
- `can_preview`
- `write_limited`
- `writable_artifacts`

`writable_artifacts` is tied to the server whitelist, not duplicated in the
test. `can_preview` must match the preview builder's accepted timeline inputs:
`draft_timeline.json`, `timeline.json`, or legacy `timeline.plan`.

## Boundaries

- No browser path becomes canonical truth.
- Workbench remains write-limited.
- Dashboard remains review/read-oriented.
- Official render remains backend/ffmpeg.
- This change does not alter material-map, M6, Node 14, effects, or delivery
  gate behavior.

## Verification

- Focused server tests:
  `python -m unittest tests.test_dashboard_server tests.test_workbench_server -q`
- JS smoke:
  `node tests/workbench_api_smoke.js`
  `node tests/workbench_core_smoke.js`
- Frontend smoke:
  `python tools/workbench_frontend_smoke.py --artifact-root .tmp/srp_real67_fuller_replay`
- Full regression:
  `python -m unittest discover -s tests -q`
