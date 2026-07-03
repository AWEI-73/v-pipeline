# Dashboard SPA and Workbench Server Merge Spec

Status: archived migration contract, superseded by native single-document Workbench / 2026-07-03

## Goal

Record the completed migration from the old SPA-hosted Workbench iframe to the
native single-document Workbench. The old Control Index is removed from the
formal route. Workbench is served by the same Dashboard server under a bounded
`/api/workbench/*` namespace. Dashboard SPA views remain as white-box modules
and compatibility routes, but they are no longer the Workbench host.

## Formal Routes

| Route | Behavior |
| --- | --- |
| `/` | Native Workbench single-document app |
| `/dashboard` | SPA Dashboard white-box compatibility route |
| `/material-map` | SPA Dashboard shell with Material Map active |
| `/workbench` | Native Workbench single-document app |
| `/dashboard/legacy` | Legacy `dashboard_v1` fallback |

The formal routes must not serve `material_map_canvas.html` directly and must
not contain `MODE_MOCKS`. `/` and `/workbench` must expose native Workbench
markers such as `wb-monitor`, `wb-timeline`, and the four `track-lane` lanes.

## SPA Layout

The Dashboard shell follows the new Antigravity direction:

- Clean white operational surface.
- Top header with run status and run root.
- Top nav: `Route`, `Material Map`, `Timeline`, `Verify`, `Workbench`,
  `Artifacts`.
- Greenfield / brownfield mode signal near the header.
- Vertical route timeline in the left rail.
- Important artifact cards in the main surface.
- Material Map view visualizes needs, assets, satisfaction edges, and
  material delta.
- Workbench view is a first-class tab in the same shell, not a separate card
  launcher.

## Frontend Structure

Use plain JavaScript modules first. Do not introduce React, Vite, Next.js, or a
build step in this migration.

```text
dashboard/
  index.html
  src/
    main.js
    router.js
    state.js
    api/
      controlApi.js
      artifactsApi.js
      materialMapApi.js
      workbenchApi.js
    components/
      AppHeader.js
      TopNav.js
      StatusPill.js
      VerticalRouteTimeline.js
      ArtifactCard.js
    views/
      RouteOverviewView.js
      MaterialMapView.js
      WorkbenchView.js
      VerifyView.js
      ArtifactsView.js
    styles/
      base.css
      layout.css
      components.css
      views.css
  legacy/
    dashboard_v1.html
    dashboard_v1.css
    dashboard_v1.js
  prototypes/
    material_map_canvas.html
    route_review_mockup.html
```

During migration, existing files may remain in place for compatibility.
White-box routes load from `dashboard/index.html` and `dashboard/src/*`; the
formal Workbench app loads from `dashboard/workbench_native/index.html` and
imports `dashboard/src` views into its slide-over panel.

## Data Sources

Formal SPA views consume real APIs:

- `/api/control/status`
- `/api/material-map-view`
- `/api/artifacts`
- `/api/projects`
- `/api/control/workbench-health`
- `/api/workbench/health`
- `/api/workbench/preview-timeline`
- `/api/workbench/thumbnails`
- `/api/workbench/proxies`

Workbench write APIs are allowed only under `/api/workbench/*` and only for
draft artifacts already whitelisted by the Workbench runtime.

## Server Merge Policy

The final runtime is one Dashboard server process. It serves:

- SPA routes.
- Dashboard read/review APIs.
- Material-map view API.
- Workbench static runtime assets.
- Workbench read/write APIs under `/api/workbench/*`.
- Workbench media preview under `/media` with the existing allow-list behavior.

The merge must preserve safety:

- Dashboard review APIs do not mutate canonical artifacts.
- Workbench write APIs write only whitelisted draft artifacts.
- `project_material_map.json`, `reviewed_project_material_map.json`,
  `timeline.json`, `timeline_build.json`, and `final.mp4` are never overwritten
  by Workbench patch/save endpoints.

## Workbench Migration Boundaries

The Workbench migration is a staged replacement of the editing surface, not a
rewrite of pipeline ownership. The Dashboard shell may visualize status,
handoff readiness, and draft artifacts, but canonical video artifacts remain
owned by the backend BUILD/render route.

Current state:

- `/workbench` is the native Workbench route.
- The active editor is no longer loaded through an iframe.
- Dashboard white-box views are imported into the native Workbench slide-over
  panel. They may show run context, health status, draft summaries, route,
  material-map, artifacts, and verify views, but they must not re-layout or
  reimplement the native editor's monitor/timeline interaction.
- `/workbench/index.html` and related files are served from
  `dashboard/workbench_native/`.
- `/api/workbench/*` is already hosted by the merged Dashboard server.
- `/media` is shared with the Workbench preview runtime and keeps the existing
  allow-list behavior.

Do not migrate by copying mock behavior from material_map_canvas.html. That file
is a visual reference only; it contains prototype routing, mock state, and
iframe control code that must not become the formal runtime contract.
Prototype selectors such as `monitor-box` and `lane-video` are references for
guarding against accidental mock imports; native truth remains the Workbench
`wb-monitor`, `wb-timeline`, and `track-lane` markers.

### Native Editor Protected Zone

Until the Workbench editor is deliberately migrated layer-by-layer with
equivalent smoke coverage, treat these native regions as protected:

- The video monitor / playback preview area.
- The four lower timeline tracks: video, subtitle, audio, and effect.
- Clip selection, playhead mapping, trim handles, source-window math, media
  proxy playback, material replacement, subtitle patching, audio cue patching,
  effect marker preview, and save/handoff payload generation.

Do not change these regions as part of Dashboard shell, Material Map, route
review, artifact review, or general UX cleanup. Only touch them when the
contract or API shape for ffmpeg/backend editing changes, or when a dedicated
Workbench migration step names the affected layer and carries equivalent tests.

The baseline browser guard for this protected zone is:

```powershell
node tools\workbench_browser_layout_smoke.mjs --artifact-root <run-folder>
```

It starts a temporary Workbench server and checks the native editor directly at
1366x900 and 1920x1080: no horizontal page overflow, a 16:9 monitor, and the
playback controls plus four video/subtitle/audio/effect lanes still present.
Use `--url http://localhost:8765/workbench` when the merged Dashboard server is
already running; that route now verifies the same native document directly.

The current `/workbench` route must therefore optimize the native document
instead of an outside shell:

- Keep the native monitor, transport, material drawer, inspector, and four-lane
  timeline mounted.
- Mount Dashboard white-box views only in the slide-over module host.
- Do not mirror native Workbench state into duplicate Dashboard controls.

### Draft Artifact Contract

Workbench is write-limited. It can propose edits by writing draft artifacts
only. It must not overwrite canonical artifacts or delivery artifacts.

Allowed draft outputs:

- `timeline_patch.json`
- `patched_draft_timeline.json`
- `workbench_contract_patch.json`
- `subtitle_patch.json`
- `audio_cue_patch.json`
- `effect_patch.json`
- `workbench_handoff.json`
- `workbench_review_report.json`
- `workbench_review_report.md`

Source-window edits:

- Workbench source-window trimming is represented as an artifact patch, not as
  direct media mutation. The preferred material-first shape is a draft
  material-map review decision that carries
  `usable_range: {"start": number, "end": number}` for an accepted
  `asset_id` + `scene_index` + `need_id` edge.
- The SPA should display the full chain behind each editable clip:
  `segment_contract.json` segment -> `material_fit.need_refs` ->
  `project_material_map.json` accepted scene -> `usable_range` ->
  `rough_cut_plan.json` clip -> `timeline_build.json` render slot.
- The browser may preview `ffmpeg`-equivalent trims, but official cutting is
  backend-owned. Backend BUILD consumes artifact values such as `source_path`,
  `start_sec`, and `duration_sec` and then renders through ffmpeg /
  `contract-run`.
- If a Workbench edit changes which need a clip satisfies, route it through a
  material-map review/apply packet. If it only changes timing inside an already
  accepted scene, route it through a source-window patch that still preserves
  the same `asset_id`, `scene_index`, and `need_id`.

Protected canonical/delivery outputs:

- `timeline.json`
- `timeline_build.json`
- `segment_contract.json`
- `project_material_map.json`
- `reviewed_project_material_map.json`
- `final.mp4`

### Completed Migration Shape

Phase V2-1: slide-over module host

- Keep `dashboard/workbench_native/*` as the editor runtime.
- Import reusable Dashboard white-box views from `dashboard/src/*` into the
  native Workbench slide-over.
- Route pipeline step buttons and full-data actions into the slide-over instead
  of navigating away from the editor.
- Keep playback position, selected clip, and drawer state mounted while the
  slide-over opens, switches modules, or closes.

Phase V2-2: native Workbench as home route

- Serve `dashboard/workbench_native/index.html` directly for `/` and
  `/workbench`.
- Keep `/dashboard`, `/material-map`, `/verify`, and `/artifacts` as SPA
  white-box compatibility routes.
- Keep all Workbench writes under `/api/workbench/*`.
- Keep draft-only writes and canonical artifact protection unchanged.

Phase V2-3: retired SPA host cleanup

- Remove the old SPA iframe host. `WorkbenchView` is now a light handoff view
  that links to the native Workbench route and shows draft summary context.
- Do not duplicate native Workbench state in the Dashboard compatibility shell.
- Do not reimplement the native monitor, transport, material drawer, or
  four-lane timeline in `dashboard/src`.

### Acceptance Checklist

- `/workbench` remains reachable from the Dashboard top navigation.
- The selected run root is preserved across Dashboard, Material Map, and
  Workbench routes.
- The Workbench editor can load preview data for a real run folder.
- Saving from Workbench writes only whitelisted draft artifacts.
- Handoff readiness is visible before an agent consumes Workbench drafts.
- Tests prove that Workbench APIs are still served by the merged Dashboard
  server and that canonical artifacts are not mutated.
- `node tools\workbench_browser_layout_smoke.mjs --artifact-root <run-folder>`
  passes before and after any change touching the native monitor, timeline
  lanes, or slide-over host.

## Prototype Policy

Antigravity prototype files may remain as design references only:

- `dashboard/prototypes/material_map_canvas.html`
- `dashboard/prototypes/route_review_mockup.html`

They cannot be formal route targets until mock data and fake write behavior are
removed.

## Test and Browser Gates

Focused tests must prove:

- `/` and `/workbench` serve the native Workbench single-document app.
- `/dashboard`, `/material-map`, `/verify`, and `/artifacts` serve SPA
  white-box compatibility views.
- `/dashboard/legacy` serves legacy dashboard.
- Formal route HTML does not contain `MODE_MOCKS`.
- SPA assets are served from `dashboard/src/*`.
- `/api/material-map-view` reads real material-map and delta artifacts.
- `/api/workbench/health` is served by the merged Dashboard server.
- `/api/workbench/patch` writes only Workbench draft artifacts.
- Dashboard read APIs do not mutate canonical artifacts.

Browser verification must include:

- Open `/` or `/workbench` and wait for the native monitor, transport, and four
  lanes.
- Open `/material-map` and wait for a real asset id from the run folder.
- Open the native Workbench slide-over and switch route/material/artifacts/verify
  modules without losing playback position or clip selection.
- Save screenshots for all three.
