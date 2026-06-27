# Workbench / Dashboard Integration

This document defines the current frontend/backend boundary for Hermes Video
Pipeline. It is intentionally operational: future agents should use it to decide
where a change belongs before editing code.

## Surfaces

### Dashboard Shell

`tools/dashboard_server.py` now serves the main SPA shell at `/`, `/dashboard`,
`/material-map`, `/timeline`, `/verify`, `/artifacts`, and `/workbench`.

The shell is read/review oriented outside the Workbench iframe. It should show:

- the active artifact root and route status;
- Dashboard views for read-oriented review;
- Material Map and verification evidence;
- Workbench draft readiness, including
  `workbench.draft_summary.agent_ready`.

The Dashboard shell is read-only. It must not duplicate native Workbench editing
behavior or silently mutate canonical artifacts.

The shell reads the compact frontend manifest from:

```text
GET /api/control/status
```

It reads Workbench health from the merged server:

```text
GET /api/workbench/health
```

The selected run folder is shared by all shell views through `?root=...`.
Users can switch by selecting a detected run in `選擇 Run`, or by pasting a
folder path into `打開資料夾`. The Dashboard shell passes the same root to
Dashboard, Material Map, Verify, Artifacts, and the Workbench iframe.

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

Dashboard should present decision-making artifacts in Chinese while preserving
English artifact names and JSON keys as the machine contract. Use the data
dictionary and artifact visibility rules in
`docs/construction-guides/dashboard/dashboard-route-review-ux-spec.md`:

```text
decision artifacts -> visible cards
evidence artifacts -> visual proof / compact links
debug artifacts -> collapsed details
```

Do not list every JSON file by default. Show artifacts that affect route,
review, approval, repair, or render eligibility; keep mechanical handoff files
behind a debug drawer.

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

The current `/workbench` SPA route is a thin host around the native Workbench:

- `WorkbenchView` embeds `/workbench/index.html?root=...`.
- The native runtime lives in `dashboard/workbench_native/`.
- The SPA shell may show run context, health, and draft summaries.
- The SPA shell must not reimplement the native monitor, timeline tracks, clip
  selection, or patch math.

### Native Editor Protected Zone

Treat the native Workbench monitor and four lower tracks as protected during
Dashboard/frontend migration:

- video monitor / playback preview;
- video, subtitle, audio, and effect tracks;
- playhead mapping, source-window trim handles, media proxy playback, material
  replacement, subtitle/audio/effect patch drafting, and save/handoff payloads.

Do not change these regions while migrating Dashboard, Material Map, route
review, or artifact review. Only touch them when a dedicated Workbench migration
task names the layer and carries equivalent smoke coverage, or when backend
contract/API changes require it.

The minimal browser guard for this protected zone is:

```powershell
node tools\workbench_browser_layout_smoke.mjs --artifact-root <run-folder>
```

It starts a temporary Workbench server and checks the native editor directly at
1366x900 and 1920x1080: no horizontal page overflow, the monitor stays 16:9,
the playback controls remain present, and the video/subtitle/audio/effect lanes
remain present. When a merged Dashboard server is already running, use:

```powershell
node tools\workbench_browser_layout_smoke.mjs --url http://localhost:8765/workbench
```

Against the merged Dashboard route, the same guard also verifies the
`/workbench` SPA host still uses `app-workbench`, keeps the native iframe
visible in the first viewport, and points it at `/workbench/index.html` before
entering the iframe for the native editor checks. It also rejects protected
editor selectors in the outer SPA shell (`monitor-box`, `timeline-wrap`,
`clip-video`, `wb-monitor`, `wb-timeline`, `track-lane`, `lane-video`) so the
shell cannot silently grow a duplicate monitor or four-track editor.

The faster `tools/workbench_frontend_smoke.py --artifact-root <run-folder>` is
stricter than the layout smoke. It needs a Workbench-previewable run folder with
`timeline.json`, `draft_timeline.json`, or `timeline.plan`, plus enough material
data for at least one editable clip. Use it for HTML/API/draft-write protection,
not for empty layout-only runs.

For routine frontend migration work, run the Workbench tier first:

```powershell
python tools/test_tiers.py --tier workbench
```

That tier includes the SPA shell render/i18n smoke, the native Workbench
server/frontend smoke, and the Workbench API/core/material helper smokes. It is
the default guard before touching the Dashboard shell around Workbench; use the
browser layout smoke when the change affects viewport sizing or iframe layout.
The tier runner sets child-process `TMP` / `TEMP` to `.tmp/test-temp` so a
corrupted Windows user temp folder does not look like a Workbench regression.

For a self-contained fixture, run:

```powershell
python tools/workbench_frontend_smoke.py --artifact-root .tmp/workbench_frontend_smoke_fixture --init-fixture
python tools/workbench_frontend_smoke.py --artifact-root .tmp/workbench_frontend_smoke_fixture --exercise-replace
```

`--init-fixture` refuses non-empty folders by default. Use it only with
disposable `.tmp` paths, or add `--force-init-fixture` when intentionally
recreating that scratch fixture.

Current Workbench shell rules:

- `/workbench` uses the `app-workbench` dense/wide layout.
- `/workbench` does not render the Dashboard pause banner.
- The iframe remains the compatibility bridge.
- Native Workbench state is not mirrored into duplicate Dashboard controls.

Source-window trims are contract-linked edits. The UI should show and preserve
the chain:

```text
segment_contract.json segment
-> material_fit.need_refs
-> project_material_map.json asset_id + scene_index
-> accepted satisfies edge
-> usable_range {start, end}
-> rough_cut_plan.json start_sec + duration_sec
-> backend ffmpeg / contract-run render
```

If the user drags an in/out handle in Workbench, the saved output should be a
draft patch or material-map review verdict patch that updates `usable_range`.
Workbench may preview the trim, but it must not directly rewrite
`timeline_build.json`, `project_material_map.json`, `segment_contract.json`, or
`final.mp4`. Backend review/apply converts the patch into official artifacts and
drives ffmpeg with the resulting `source_path`, `start_sec`, and `duration_sec`.

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

Start the merged Dashboard/Workbench server:

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

Focused checks:

```powershell
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
