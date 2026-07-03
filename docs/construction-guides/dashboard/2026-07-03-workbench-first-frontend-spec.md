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
- Panel roles (design rationale — do not merge them into tabs):
  - RIGHT panel is the always-on surface: clip inspector + domain contract
    black-box. It is never collapsed or covered.
  - LEFT drawer is the occasional surface (replace/add material only).
    v1 REQUIREMENT: collapsible to a ~44px icon rail with one toggle
    (see template `#btn-drawer`). Default expanded on first load; remember
    state in localStorage. The replace flow needs materials and the selected
    clip visible AT THE SAME TIME — that is why left and right are separate
    panels and must not become tabs of one panel.
- v2 (do NOT build now): draggable upper/lower splitter.

## Top bar

1. Run/project selector:
   - list runs from the existing `/api/projects` (see
     `dashboard/src/api/projectsApi.js`);
   - pass the selected root as the `?root=` query param on every subsequent
     API call — the server validates it via `get_validated_root()`
     (tools/dashboard_server.py). Do NOT add a free-form "add path" input and
     do NOT try to bypass root validation; scanning additional folders is a
     server startup concern, out of scope.
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
5. Fit-first ordering (make the EXISTING behavior visible):
   `workbench_materials.js` already sorts assets by match against the
   selected clip's `need_id` (`matchStatusForNeed` / `sort_score`). Surface
   it in the UI:
   - when a clip is selected, the drawer header shows 「適合這段的素材」 and
     each asset gets a fit badge — 符合需求 (green) / 候選 (amber) /
     其他 (gray) — mapped from the existing match status;
   - when nothing is selected, plain browse order with search + family
     filter (this is the flexibility mode; keep it).
   Do not modify the sorting logic itself (workbench_core /
   workbench_materials are read-only).
6. Material gap request (v1, frontend-only): a button at the drawer bottom
   「素材不夠?請 agent 補」 opens a small inline form (這段需要什麼畫面,
   free text + the selected clip/segment id) and produces a structured
   request text the user copies to the agent. Do NOT implement file upload
   and do NOT write new artifact types — `project_material_map.json` and
   source media are canonical read-only per API_CONTRACT, and material
   sourcing belongs to the agent's material-map branch (gap → reshoot /
   generate / stock). A `material_request` field in `workbench_handoff.json`
   is a future small backend order, not yours.
7. No material-map review features here. The material domain's white-box
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

## Implementation route (revised 2026-07-03)

Survey result: `dashboard/workbench_native/index.html` ALREADY implements most
of the target — left material drawer with search/filter, center monitor +
transport, right clip inspector, full-width four-lane timeline, and footer
save/handoff/export actions. Therefore the implementation is an EVOLUTION of
the native page, not a new shell page.

Visual reference template (static, self-contained, demo data only):
`dashboard/workbench_first_template.html`. It shows the target layout, the
four domain-contract black-box views, the pipeline strip, and the friendly
copy tone. Each action button carries a `data-api` attribute naming its real
endpoint. Copy the intent, not the file — real work happens in
workbench_native.

What to ADD to the native page:

1. Top-bar domain icons (素材/音樂/字幕口白/特效) with status dots.
2. Right inspector second mode: read-only domain contract black-box (swap on
   icon click, X to return). Default mode stays the clip inspector.
3. Collapsible pipeline-status strip (global black box) fed by
   `/api/control/status` + `/api/artifacts`.
4. Friendlier copy for non-professional users (see template): plain-language
   field labels (從素材的哪裡開始/用多長), and save feedback that says the
   agent will execute the adjusted contract.

## Files you may modify

- `dashboard/workbench_native/index.html`, `workbench.css`, `workbench.js`
  under these hard rules:
  - protected ids/classes stay present and functional (`monitor`,
    `wb-monitor`, `wb-timeline`, `track-lane`, `lane-video`, `lane-subtitle`,
    `lane-audio`, `lane-effect`, `timeline-ruler`, `playhead`, transport
    controls, `.wb-materials`) — both smoke guards enforce this;
  - deterministic edit math stays in `workbench_core.js` (read-only for you);
  - `workbench_api.js` may gain wrappers ONLY for endpoints already listed in
    API_CONTRACT.md.
- `dashboard/index.html`, `dashboard/index.css`, `dashboard/index.js`
- `dashboard/src/**` (make /workbench the home route; keep white-box views)

## Files you must NOT modify

- `dashboard/workbench_native/workbench_core.js` and
  `workbench_materials.js` — pure logic modules, read-only.
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
