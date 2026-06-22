# Dashboard SPA and Workbench Server Merge Spec

Status: implementation contract / 2026-06-21

## Goal

Replace the legacy Dashboard entry with a single Hermes SPA Dashboard. The SPA
is the main product surface for route review, material-map review, artifacts,
verification, and Workbench editing. The old Control Index is removed from the
formal route. Workbench is moved into the same dashboard project and served by
the same Dashboard server under a bounded `/api/workbench/*` namespace.

## Formal Routes

| Route | Behavior |
| --- | --- |
| `/` | SPA Dashboard shell, default Route view |
| `/dashboard` | SPA Dashboard shell, default Route view |
| `/material-map` | SPA Dashboard shell with Material Map active |
| `/workbench` | SPA Dashboard shell with Workbench active |
| `/dashboard/legacy` | Legacy `dashboard_v1` fallback |

The formal routes must not serve `material_map_canvas.html` directly and must
not contain `MODE_MOCKS`.

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

During migration, existing files may remain in place for compatibility, but the
formal routes must load from `dashboard/index.html` and `dashboard/src/*`.

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

- `/workbench` is a SPA Dashboard route.
- The active editor is still loaded inside `WorkbenchView` through an iframe to
  `/workbench/index.html`.
- `/workbench/index.html` and related files are served from
  `dashboard/workbench_native/`.
- `/api/workbench/*` is already hosted by the merged Dashboard server.
- `/media` is shared with the Workbench preview runtime and keeps the existing
  allow-list behavior.

Do not migrate by copying mock behavior from material_map_canvas.html. That file
is a visual reference only; it contains prototype routing, mock state, and
iframe control code that must not become the formal runtime contract.

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

Protected canonical/delivery outputs:

- `timeline.json`
- `timeline_build.json`
- `segment_contract.json`
- `project_material_map.json`
- `reviewed_project_material_map.json`
- `final.mp4`

### Migration Phases

Phase 0: iframe containment

- Keep `dashboard/workbench_native/*` as the editor runtime.
- Keep the iframe in `WorkbenchView` as the compatibility bridge.
- Strengthen the SPA shell around it with status panels, draft artifact
  summaries, and handoff readiness.
- Do not duplicate native Workbench state in the Dashboard shell.

Phase 1: shell-native status panels

- Render Workbench draft artifact status directly in the SPA shell from
  `/api/artifacts` and `/api/control/status`.
- Show `agent_ready`, handoff validation errors, draft counts, and changed layer
  counts before the iframe.
- Add direct links from Dashboard Material Map evidence to the Workbench route
  while preserving `?root=...`.

Phase 2: extract Workbench modules

- Move reusable native Workbench logic into importable modules under
  `dashboard/src/workbench/` only after tests cover the original behavior.
- Keep `workbench_native/workbench_core.js`, `workbench_api.js`, and
  `workbench_materials.js` as the source contracts until the extracted modules
  pass equivalent smoke tests.
- Migrate one layer at a time: preview loading, material browser, timeline
  editing, subtitle/cue/effect patches, save-all/handoff.

Phase 3: replace iframe with SPA-native composition

- Replace the iframe only after the SPA-native editor can load
  `/api/workbench/preview-timeline`, render material preview, produce the same
  patch payloads, and pass the Workbench smoke tests.
- Keep all writes under `/api/workbench/*`.
- Keep draft-only writes and canonical artifact protection unchanged.

### Acceptance Checklist

- `/workbench` remains reachable from the Dashboard top navigation.
- The selected run root is preserved across Dashboard, Material Map, and
  Workbench routes.
- The Workbench editor can load preview data for a real run folder.
- Saving from Workbench writes only whitelisted draft artifacts.
- Handoff readiness is visible before an agent consumes Workbench drafts.
- Tests prove that Workbench APIs are still served by the merged Dashboard
  server and that canonical artifacts are not mutated.

## Prototype Policy

Antigravity prototype files may remain as design references only:

- `dashboard/prototypes/material_map_canvas.html`
- `dashboard/prototypes/route_review_mockup.html`

They cannot be formal route targets until mock data and fake write behavior are
removed.

## Test and Browser Gates

Focused tests must prove:

- `/`, `/dashboard`, `/material-map`, and `/workbench` serve the SPA shell.
- `/dashboard/legacy` serves legacy dashboard.
- Formal route HTML does not contain `MODE_MOCKS`.
- SPA assets are served from `dashboard/src/*`.
- `/api/material-map-view` reads real material-map and delta artifacts.
- `/api/workbench/health` is served by the merged Dashboard server.
- `/api/workbench/patch` writes only Workbench draft artifacts.
- Dashboard read APIs do not mutate canonical artifacts.

Browser verification must include:

- Open `/` and wait for SPA header/nav.
- Open `/material-map` and wait for a real asset id from the run folder.
- Open `/workbench` and wait for Workbench view/health.
- Save screenshots for all three.
