# Dashboard And Workbench

Hermes currently has two frontend surfaces. They are connected, but they do not
have the same responsibility.

## Surfaces

### Workbench Home

The Dashboard server root (`/`) serves the native Workbench as the
single-document app home. It links the live read/review surfaces and the
Workbench editor without merging their responsibilities:

- Dashboard for read-only run/node/status review;
- Material Map / Timeline / Verify / Artifacts for white-box inspection;
- Workbench for interactive draft preview and patch creation.

The shell reads run state from `/api/control/status` and Workbench health from
the same merged server under `/api/workbench/health`.

Run selection lives in the shared shell:

- use `選擇 Run` to switch among detected usable run folders;
- use `打開資料夾` to paste or type a run folder path directly;
- both controls update the current route with `?root=...`, so Dashboard,
  Material Map, Verify, Artifacts, and Workbench read the same artifact root.

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

The `/workbench` route is the same native editor home as `/`, and static native
assets are served under `/workbench/...`. During frontend migration, keep these native
regions protected unless a dedicated Workbench task and equivalent smoke tests
say otherwise:

- video monitor / playback preview;
- video, subtitle, audio, and effect tracks;
- trim handles, playhead mapping, source-window math, material replacement, and
  save/handoff payload generation.

The outer Workbench shell may show run context, health, and draft summaries. It
should not mirror native Workbench state into duplicate Dashboard controls.

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

Start Dashboard and Workbench together:

```powershell
python tools\dashboard_server.py --artifact-root .tmp\srp_real67_fuller_replay --port 8765
```

Open:

```text
http://localhost:8765/
```

Dashboard:

```text
http://localhost:8765/dashboard
```

Workbench:

```text
http://localhost:8765/workbench
```

Legacy prototypes:

```text
http://localhost:8765/archive/dashboard_v1.html
```

Archived prototypes under `dashboard/archive/` are historical references only.
The old root-level compatibility routes such as `/dashboard_v1.html`,
`/dashboard/legacy`, `/3d`, and `/physics` intentionally return 404.

Focused checks:

```powershell
python tools\test_tiers.py --tier workbench
node --check dashboard\src\main.js
node --check dashboard\workbench_native\workbench.js
node --check dashboard\workbench_native\workbench_api.js
node --check dashboard\workbench_native\workbench_materials.js
node --check dashboard\workbench_native\workbench_core.js
node tests\dashboard_spa_render_smoke.mjs
node tests\workbench_api_smoke.js
node tests\workbench_materials_smoke.js
node tests\workbench_core_smoke.js
node tools\workbench_browser_layout_smoke.mjs --artifact-root .tmp\srp_real67_fuller_replay
python tools\workbench_frontend_smoke.py --artifact-root .tmp\srp_real67_fuller_replay
python tools\workbench_frontend_smoke.py --artifact-root .tmp\srp_real67_fuller_replay --exercise-replace
python -m unittest tests.test_preview_timeline tests.test_workbench_server tests.test_timeline_patch -q
python -m unittest tests.test_workbench_frontend_smoke -q
```

The `workbench` tier includes the SPA shell render/i18n smoke plus the native
Workbench API/core/material helper smokes. Use it as the default preflight
before changing Dashboard/Workbench frontend code; use the browser layout guard
below when a real viewport check is needed. The tier runner executes child
processes with `TMP` / `TEMP` pointed at `.tmp/test-temp`, so Windows user-level
temp folder issues do not masquerade as Workbench regressions.

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
- `tools/workbench_browser_layout_smoke.mjs --artifact-root <run>` starts a
  temporary Workbench server and checks real browser layout at 1366x900 and
  1920x1080. In `--artifact-root` mode it checks the native editor directly for
  no horizontal overflow, a 16:9 monitor, playback controls, and four timeline
  lanes. Use `--url http://localhost:8765/workbench` when a merged Dashboard
  server is already running; that route additionally verifies the SPA host keeps
  `app-workbench`, keeps the native iframe visible in the first viewport, and
  points that iframe at `/workbench/index.html`. The same guard fails if the
  outer SPA shell contains protected editor selectors such as `monitor-box`,
  `timeline-wrap`, `clip-video`, `wb-monitor`, `wb-timeline`, `track-lane`, or
  `lane-video`.
- `tools/workbench_frontend_smoke.py --artifact-root <run>` is stricter: it
  needs a Workbench-previewable run folder with a valid timeline input and at
  least one editable clip. Use it for HTML/API/draft-write protection, not for
  empty layout-only runs.
  A self-contained fixture can be created with
  `python tools/workbench_frontend_smoke.py --artifact-root .tmp/workbench_frontend_smoke_fixture --init-fixture`;
  then run the same command with `--exercise-replace` to cover replacement.
  `--init-fixture` refuses non-empty folders by default; use only disposable
  `.tmp` paths, or add `--force-init-fixture` when recreating the scratch
  fixture intentionally.

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
