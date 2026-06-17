# Dashboard And Workbench

Hermes currently has two frontend surfaces. They are connected, but they do not
have the same responsibility.

## Surfaces

### Control Index

The Dashboard server root (`/`) serves a small Control Index. It links the two
frontend surfaces together without merging their responsibilities:

- Dashboard for read-only run/node/status review;
- Workbench for interactive draft preview and patch creation.

The index also exposes the Workbench start command and draft readiness from
`/api/control/status`. It checks the external Workbench server through
`/api/control/workbench-health`, which proxies
`http://localhost:8770/api/workbench/health` without making the browser perform
cross-origin health checks.

### Dashboard

Dashboard is for review and status:

- pipeline run state;
- node/gate status;
- material-map and verification findings;
- backend artifacts;
- Workbench handoff visibility.

Dashboard should stay read-oriented. It should not become a timeline editor.

### Workbench

Workbench is for interactive draft edits:

- preview the current material composition;
- inspect and trim clips;
- replace clips from the material map;
- edit subtitle drafts;
- add audio cue drafts;
- add effect intent drafts;
- save draft patch/handoff artifacts.

Official rendering still belongs to the backend ffmpeg pipeline.

## Artifact Ownership

Workbench may write draft artifacts such as:

- `preview_timeline.json`
- `timeline_patch.json`
- `patched_draft_timeline.json`
- `workbench_contract_patch.json`
- `workbench_handoff.json`

Workbench must not overwrite canonical artifacts such as:

- `final.mp4`
- canonical `timeline.json`
- material-map source files
- source contracts

## Local Run Commands

Start Workbench:

```powershell
python tools\workbench_server.py --artifact-root .tmp\srp_real67_fuller_replay --port 8770
```

Open:

```text
http://localhost:8000/
```

Dashboard:

```text
http://localhost:8000/dashboard
```

Workbench:

```text
http://localhost:8770/workbench
```

Focused checks:

```powershell
node --check dashboard\index.js
node --check dashboard\workbench_native\workbench.js
node --check dashboard\workbench_native\workbench_api.js
node --check dashboard\workbench_native\workbench_materials.js
node --check dashboard\workbench_native\workbench_core.js
node tests\workbench_api_smoke.js
node tests\workbench_materials_smoke.js
node tests\workbench_core_smoke.js
python tools\workbench_frontend_smoke.py --artifact-root .tmp\srp_real67_fuller_replay
python tools\workbench_frontend_smoke.py --artifact-root .tmp\srp_real67_fuller_replay --exercise-replace
python -m unittest tests.test_preview_timeline tests.test_workbench_server tests.test_timeline_patch -q
python -m unittest tests.test_workbench_frontend_smoke -q
```

## Frontend Module Boundary

- `workbench_core.js`: pure deterministic timeline/editing logic.
- `workbench_api.js`: Workbench HTTP API client.
- `workbench_materials.js`: pure material-browser search/filter helpers.
- `workbench.js`: DOM controller, browser preview, and user interaction.

The browser/server API is documented in
`dashboard/workbench_native/API_CONTRACT.md`.

Keep canonical artifact rules in the Python server/backend. Browser modules
should produce draft patches and handoff artifacts, not official pipeline truth.

## Workbench Layout Acceptance

- Left material panel scrolls independently.
- Center preview remains centered for portrait and landscape media.
- Inspector stays usable.
- Timeline area has horizontal access when clips exceed the viewport.
- Track stack remains reachable when lanes overflow vertically.
- Play controls remain visible.
- Text, audio, and effect lanes are visible as lanes even when empty.

## Safety Rules

- Dashboard reads; Workbench drafts.
- Workbench draft artifacts require agent/backend review before official rerender.
- No frontend path should silently rewrite canonical pipeline truth.
- No browser export should be treated as the official final video.

## Known Deferred Work

- Material-library folder organization.
- Richer visual design polish.
- Heavy effects authoring.
- Full multi-track NLE behavior.
- Full preview/output visual parity.
