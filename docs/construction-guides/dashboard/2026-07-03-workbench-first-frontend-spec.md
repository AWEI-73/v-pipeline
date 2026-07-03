# Workbench-First Frontend Spec (for Gemini implementation)

Date: 2026-07-03
Status: approved design, ready for implementation
Implementer: Gemini (frontend only)
Relationship to existing docs:

- `dashboard/workbench_native/API_CONTRACT.md` is LAW. Nothing in this spec
  overrides it. Read it first.
- `docs/construction-guides/dashboard/dashboard-spa-workbench-migration-spec.md`
  remains valid for server merge policy and migration boundaries; this spec
  supersedes only its SPA home-layout portion.

## Product principles

1. Agent is the primary editor; the human is the adjuster. The UI exists for
   human fine-tuning and review, not for building videos from scratch.
2. Workbench IS the home page. The old dashboard becomes the "white box"
   detail layer behind it.
3. Feature-minimal: browse, drag, trim, save, export-for-review. Nothing else
   in v1.
4. The central editing surface (monitor + four lanes) is never covered by
   overlays and never reimplemented — it is the Native Editor Protected Zone
   defined in API_CONTRACT.md, embedded as-is.
5. Clean white style consistent with the existing SPA (`dashboard/src/styles/`).

## Layout (single screen, no scrolling of the page itself)

```
+------------------------------------------------------------------+
| top bar 48px: run selector | 4 domain icons | 管線現況 | 儲存草稿契約 |
+------------------------------------------------------------------+
| [black-box strip 64px, collapsible, hidden by default]           |
+----------------+---------------------------------+---------------+
| left 240px     | center: flex                    | right 300px   |
| asset drawer   | 16:9 preview monitor            | status /      |
| (scroll)       | + playback controls             | contract panel|
|                | (native, untouched)             | (scroll)      |
+----------------+---------------------------------+---------------+
| timeline, full width, fixed height ~240px                        |
| (ruler 24px + 4 lanes x 44px + margins) (native, untouched)      |
+------------------------------------------------------------------+
```

- Upper-row height is driven by the 16:9 monitor width; left/right panels
  scroll internally. Never let left/right panels extend beside the timeline.
- v2 (do NOT build now): collapsible side panels, draggable
  upper/lower splitter.

## Top bar

1. Run/project selector (existing projectsApi source).
2. Four domain icons with status dots:
   - 素材 (photo icon) — material lane / timeline_patch
   - 音樂 (music icon) — audio lane / audio_cue_patch
   - 字幕口白 (microphone icon) — subtitle lane / subtitle_patch
   - 特效 (sparkles icon) — effect lane / effect_patch
   Dot colors: green = patch saved & synced, amber = unsaved draft edits,
   gray = domain not active in this run.
3. `管線現況` button toggles the global black-box strip.
4. `儲存草稿契約` button → `WorkbenchApi.saveAll(...)`; on success show
   which patch files + `workbench_handoff.json` were written.

## Black box vs white box (two-level contract views)

| Level | Black box (inline, minimal) | White box (full data) |
|---|---|---|
| Global | Top strip: one pill per pipeline stage (意圖/契約/素材/BUILD/VERIFY/交付) sourced from `/api/control/status` + `/api/artifacts` | Existing dashboard views (RouteOverview, Artifacts, Verify, MaterialMap) kept as SPA routes, opened from the strip |
| Per domain | Right panel swap: status pill + at most 6 human-readable rows + target patch filename + collapsible raw JSON | Link "展開完整數據" navigates to the corresponding existing SPA view |

Rules:

- Black-box views are READ-ONLY. Editing happens on the lanes; saving updates
  patches; the black box only reflects state.
- Clicking a domain icon swaps the right panel content; clicking again or the
  X returns to the default clip-status view. No modal popups over the center.
- White-box views are the EXISTING SPA views. Restyle minimally if needed;
  do not rebuild them.

## Left panel: asset drawer

1. Tabs: 全部 / 影像 / 音訊 / 特效.
2. Content source: the preview-timeline projection
   (`WorkbenchApi.fetchPreviewTimeline()` materials/clips/effect assets) plus
   thumbnails (`fetchThumbnails()`) and proxies (`fetchProxies()`).
   Media loads only through the existing `/media?src=` allow-list. Do not
   read arbitrary filesystem paths.
3. Search box filtering by name.
4. Items are draggable onto lanes using the native editor's existing
   drag/replace mechanics. Replacement resolution stays
   `project_material_map.json`-based (server-enforced; do not bypass).
5. No material-map review features here. The material domain's white-box
   link covers that.

## Save semantics (unchanged from API_CONTRACT)

- Human edits accumulate as draft state; `儲存草稿契約` calls `save-all`,
  writing layer patches + `workbench_handoff.json`.
- The agent pipeline executes according to the saved patches — this is the
  "human-adjusted contract wins" behavior. Canonical files
  (`segment_contract.json`, `timeline.json`, `final.mp4`) are never written
  by the browser. Do not add any code path that tries.

## Export for review

1. One button: `輸出審閱 mp4` → `WorkbenchApi.exportFfmpeg(payload)` with the
   payload shape the server already accepts (inspect the server handler for
   accepted keys; use its defaults). Output name `workbench_export.mp4`.
2. Label the result clearly as review-grade: 正式交付仍走 pipeline BUILD 與
   delivery gate.
3. If the existing payload has no quality knob, ship with the server default
   and note it; adding quality presets is a future backend order, not yours.

## Files you may modify

- `dashboard/index.html`, `dashboard/index.css`, `dashboard/index.js`
- `dashboard/src/**` (views, components, styles, router, state, api wrappers)

## Files you must NOT modify

- `dashboard/workbench_native/**` — protected zone. The shell embeds it and
  passes `root`; it is not rebuilt, restyled, or duplicated.
- `tools/**`, `video_pipeline_core/**`, `video_tools.py`, `runtime.py`,
  `tests/**`, `docs/**` other than this spec's checklist notes.
- No new server endpoints. No server file edits. Consume only endpoints
  listed in API_CONTRACT.md.
- Legacy pages (`dashboard_v1.*`, `design_mockup.html`, `style_*.html`,
  `material_map_canvas*.html`, `material_map_review.*`,
  `route_review_mockup.html`): do NOT delete or move — several are served by
  `tools/dashboard_server.py` and asserted by `tests/test_dashboard_server.py`.
  Simply do not link them from the new home navigation. Physical archival is
  a separate later work order.

## Acceptance checklist (all must pass)

1. `node tools\workbench_browser_layout_smoke.mjs --url http://localhost:8765/workbench`
   passes (protected zone intact).
2. `python tools\workbench_frontend_smoke.py --artifact-root .tmp\workbench_frontend_smoke_fixture --init-fixture`
   and `--exercise-replace` pass.
3. Full suite green:
   `"%USERPROFILE%\miniconda3\python.exe" -m unittest discover -s tests`.
4. Manual walkthrough on a real run folder:
   - drag an asset from the drawer onto the video lane → clip replaced/added;
   - trim a clip boundary → right panel reflects the new source window;
   - save → patch files + `workbench_handoff.json` appear on disk, dots turn
     green;
   - each of the 4 domain icons opens its black-box view; white-box links
     land on the existing SPA views;
   - `管線現況` strip reflects `/api/control/status`;
   - export produces `workbench_export.mp4`, and `final.mp4` is untouched.
5. No console errors on load in a Chromium browser.

## Explicitly out of scope (do not attempt)

- Material/asset path stabilization ("asset store") — separate backend order.
- Render quality presets beyond the existing export payload.
- Deleting or archiving legacy dashboard files.
- Editing contract JSON from the UI (black box is read-only in v1).
- Collapsible panels and draggable splitter (v2).
