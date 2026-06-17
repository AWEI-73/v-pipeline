# Workbench / Dashboard Integration

This document defines the current frontend/backend boundary for Hermes Video
Pipeline. It is intentionally operational: future agents should use it to decide
where a change belongs before editing code.

## Surfaces

### Control Index

The Control Index is the top-level entry page served by `tools/dashboard_server.py`
at `/`.

It should show:

- the active artifact root and final-video presence;
- the Dashboard entrypoint for read-oriented review;
- the Workbench entrypoint and start command;
- Workbench draft artifact readiness, including
  `workbench.draft_summary.agent_ready`.

The Control Index is read-only. It must not duplicate Dashboard review panels or
Workbench editing behavior.

Control Index reads the compact frontend manifest from:

```text
GET /api/control/status
```

It checks whether the external Workbench server is reachable through the
same-origin proxy:

```text
GET /api/control/workbench-health
```

The browser should not call `localhost:8770` directly for health checks because
that creates avoidable cross-origin behavior. The direct Workbench health
endpoint is still available for tools and diagnostics:

```text
GET http://localhost:8770/api/workbench/health
```

### Dashboard

Dashboard is the read-oriented review surface.

It should show:

- project/run status;
- node and gate status;
- material-map and verification findings;
- whether Workbench draft artifacts exist;
- links or commands that open Workbench.

Dashboard should not author timeline edits. If a user wants to change timing,
source windows, subtitles, audio cues, or effect cues, route them to Workbench.

### Workbench

Workbench is the interactive preview and draft-patch surface.

It can:

- preview the current material composition, not only the final rendered MP4;
- trim approved source windows within safe limits;
- replace a selected clip with a material-map scene;
- edit subtitle draft timing/text;
- add audio cue draft markers;
- add effect intent draft markers;
- save draft patch artifacts;
- create an agent/backend handoff package.

Workbench must not overwrite canonical artifacts.

## Integration Flow

```text
SPEC / contract
-> material map / needs / delta gates
-> BUILD timeline / final render
-> Dashboard review
-> Workbench draft edits
-> timeline_patch.json
   + patched_draft_timeline.json
   + workbench_contract_patch.json
   + workbench_handoff.json
   + workbench_review_report.json / .md
-> Agent review
-> backend rerender / contract revision / reject patch
```

Hard rule:

```text
Workbench can preview and draft. Backend remains responsible for official render.
```

## Artifact Ownership

### Canonical Artifacts

These are backend-owned and must not be overwritten by Workbench:

- `final.mp4`
- canonical `timeline.json`
- canonical contract files
- material-map source files
- delivery/verification gate artifacts

### Workbench Draft Artifacts

Workbench may write these files under the active artifact root:

- `preview_timeline.json`
- `timeline_patch.json`
- `patched_draft_timeline.json`
- `workbench_contract_patch.json`
- `workbench_handoff.json`
- subtitle/audio/effect draft patch files
- `workbench_review_report.json`
- `workbench_review_report.md`
- optional workbench export files that are explicitly non-canonical

Draft artifacts are evidence for a later agent/backend decision. They are not
automatic truth.

## Material Organization

Material-map references are the canonical way to identify usable media.
Workbench material browsing and replacement should use `asset_id` +
`scene_index` from the project material map. Do not require physical source
files to be moved into UI-specific folders.

For the folder policy, see `docs/material-organization-policy.md`.

## Backend Consumption

The backend or agent should inspect draft artifacts before official rerender.

Primary Agent entrypoints:

1. `workbench_handoff.json` tells the Agent which draft artifacts exist and
   includes per-artifact hashes.
2. `workbench_review_report.json` summarizes what changed across timeline,
   subtitles, audio cues, and effect intents.
3. `workbench_contract_patch.json` is a draft interpretation of timeline edits
   at the pipeline-contract layer.

The Agent should not infer that `final.mp4` or canonical `timeline.json` changed
just because these draft files exist. The report must keep
`canonical_changed=false` unless a future explicit canonical writer exists.

The bounded backend preview path is:

```powershell
python video_tools.py workbench-handoff-validate <run-dir>
python video_tools.py workbench-draft-rerender <run-dir> --out workbench_rerender.mp4
```

`workbench-draft-rerender` produces a non-canonical candidate render from the
validated Workbench draft. It must not write `final.mp4`; official delivery
still remains owned by the normal backend pipeline.

Expected decision routes:

- accept patch and rerender from backend;
- convert patch into a contract revision;
- ask for more material;
- reject patch because it violates source windows, material-map identity, or
  current contract constraints;
- route future effect-heavy work to Node 14 / effects workflow.

## Workbench Module Boundary

The native Workbench frontend is intentionally small and dependency-light:

- `dashboard/workbench_native/workbench_core.js`: pure timeline/editing data
  functions. This is the safest place for deterministic clip math, patch
  construction, local trimming, replacement, and track-marker projection.
- `dashboard/workbench_native/workbench_api.js`: HTTP client for Workbench API
  endpoints. This centralizes endpoint names and response wrapping.
- `dashboard/workbench_native/workbench_materials.js`: pure material-browser
  helpers for family extraction and search/filter behavior.
- `dashboard/workbench_native/workbench.js`: DOM controller and browser media
  preview. Keep it thin where possible; do not put new canonical artifact rules
  here.
- `tools/workbench_server.py`: write-limited server enforcing artifact
  ownership.

The browser/server API is documented in
`dashboard/workbench_native/API_CONTRACT.md`.

Do not add backend gate logic to the browser. Browser edits should become draft
patches; backend/Agent review decides whether they become official pipeline
changes.

## Local Commands

Start Workbench against the current real 67th fuller replay artifact:

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
python -m unittest tests.test_workbench_review_report -q
```

Dashboard `/api/artifacts` exposes Workbench handoff readiness through
`workbench.draft_summary.agent_ready`. It becomes true only when
`workbench_handoff.json` exists, `workbench_review_report.json` exists, and the
same handoff passes `video_tools.py workbench-handoff-validate`. This is a
review routing flag for Agent handoff, not proof that edits should be accepted
or rendered without further backend checks.

Control Index should prefer `/api/control/status` over `/api/artifacts`.
Dashboard keeps `/api/artifacts` because it needs the full review payload.

Full regression:

```powershell
python -m unittest discover -s tests -q
```

## Workbench Layout Acceptance

- Left material panel scrolls independently.
- Center preview remains centered for portrait and landscape media.
- Inspector stays usable.
- Timeline area has horizontal access when clips exceed the viewport.
- Track stack remains reachable when lanes overflow vertically.
- No default browser selection border appears around preview media.
- Play controls remain visible.
- Text, audio, and effect lanes are visible as lanes even when empty.

## Safety Rules

- Keep `/` as a read-only Control Index.
- Do not add Dashboard editing behavior.
- Do not let Workbench write canonical artifacts.
- Do not add a new frontend framework for this cleanup.
- Do not make Workbench the official renderer.
- Do not silently translate draft patches into source contract changes.
- Do not bypass M6 material gates or delivery gates.

## Deferred Work

- Full browser NLE behavior.
- Remotion-like final renderer.
- Complex multi-track audio graph.
- Heavy motion graphics / Node 14 effects authoring.
- Material library folder-management workflow.
- Dashboard visual redesign beyond integration clarity.
