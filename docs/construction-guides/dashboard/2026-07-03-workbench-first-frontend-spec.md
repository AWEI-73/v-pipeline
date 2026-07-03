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

### Swap safety: three defense layers (v1 scope marked per item)

Replacing a clip's material is the riskiest human action. The design relies
on three layers; the frontend implements the first two and VISUALIZES the
third — it never re-implements gate logic in the browser.

1. Pre-constraint (v1, frontend): when a clip is selected, the drawer
   defaults to 「只看符合契約」ON — only 符合需求 + 候選 assets are shown
   (scoped by the segment's need via the existing match status); a toggle
   reveals the full library. This is how "materials don't all need to be
   displayed" works: the segment contract scopes the choices.
2. Drop-time checks (v1, frontend): before writing a replace patch,
   check locally and warn inline:
   - duration: replacement source shorter than the slot's duration →
     block with 「素材長度不足(還差 X 秒)」;
   - fit: dropping an 其他-badged asset → allow but require one extra
     confirm (「這個素材不符合這段的契約需求,仍要替換?」).
   Server-side validation stays authoritative: the patch endpoint is
   fail-closed and resolves replacement through `project_material_map.json`;
   never bypass or duplicate it, the frontend checks exist only to fail
   earlier with friendlier messages.
3. Post-swap evaluation (existing pipeline, frontend only shows state):
   a swap is a DRAFT until gates accept it. After a replace, the clip gets a
   「已替換・草稿」 marker and the 素材 domain dot turns amber; the save
   feedback says the agent will re-verify the affected segment (review
   report → route re-entry → BUILD → verify gate). The frontend must never
   present a swapped draft as final.
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

## Fix Round + Declutter Pass (v1.1, added 2026-07-03 after review)

Review verdict: structure and mechanics landed, but the page keeps too much
legacy chrome for a non-professional user, plus one bug and two placement
gaps. This section is the complete v1.1 work list. Guard safety: the
frontend smoke asserts only these markers — page title, `wb-monitor`/
`monitor`, `wb-transport`, `btn-play`, `btn-rewind`, `scrubber`,
`time-label`, `btn-save-all`, the four `lane-*` ids and four
`track-label` spans. Everything listed for removal below is OUTSIDE that
set. All four `Fix` items from the review and every Declutter item must
keep both smoke guards green.

### Bug fix

1. `#pipestrip` in index.html carries inline `style="display: none;"`,
   which beats the `.show` class toggle. Remove the inline style (the CSS
   already defaults `.pipestrip` to `display:none`). Verify visually that
   the strip opens and closes.

### Placement fixes

2. Top bar gains the primary save button 「儲存並交給 agent」 (blue,
   right of 管線現況), wired to the SAME save-all handler as the footer
   button — do not duplicate logic. The `btn-save-all` id must remain in
   the page (guard marker); keep it on the footer button or move the id
   with the primary button, either way exactly one element keeps it.
3. Rename 「輸出 ffmpeg 草稿」 to 「輸出審閱影片」.

### Declutter: REMOVE (pure noise for the target user)

4. Header subtitle 「素材替換 / 段落微調 / ffmpeg 草稿輸出」.
5. Header badges 「草稿編輯」「正式輸出 = ffmpeg BUILD」 — their message
   already lives in the save feedback line.
6. The left vertical tab rail (素材/字幕/音訊 tab-bar) — 字幕/音訊 are
   disabled placeholders; the drawer has its own header and collapse
   toggle. Update any JS references so nothing errors.
7. Transport frame label 「f0」 and the 「音訊：關閉/未載入」 status text.
8. The monitor overlay meta 「VID #0 · src 0.00s ...」 (`stage-meta`) —
   that information belongs to the inspector.
9. Asset card meta line 「video · 未分類 · 未標角度 · scene 0 · 瀏覽素材」
   — a card shows name + duration + fit badge only.
10. The hint line 「BGM、字幕、音效與特效會寫成草稿 patch...」.

### Declutter: DEMOTE into one collapsible 「進階」 area (keep function)

11. The track-tools row (+ 音效提示 @ 播放點 / 特效素材選擇 /
    + 特效意圖到片段) collapses into a single 「進階工具」 toggle,
    closed by default.
12. Footer buttons 「下載 patch」「儲存 patch 到資料夾」「同步草稿合約」
    move into the same 進階 area. Footer keeps only: save feedback text,
    「輸出審閱影片」, and the save-all button (if it stays in the footer).

### Declutter: KEEP as-is

Undo/redo, aspect-ratio select, scrubber + time label, drawer header
with count/search/type filter, domain icons + strip, inspector.

### Global styling

13. Align workbench.css global tokens (background, panel, border, radius,
    button styling) with `workbench_first_template.html`'s clean white
    look. No layout-structure changes, no protected-element size behavior
    changes.

### Acceptance for v1.1

- Both smoke guards green; miniconda full suite green.
- Browser console shows no errors after the tab-rail removal.
- Visual check: strip opens/closes; top-bar save works; 進階 area opens
  and every demoted control still functions.
- Append a `### Fix Round Report` under the Implementation Report with
  commits and guard tails.

## V2: Single-Document Architecture (approved direction 2026-07-03)

Decision: the native workbench page becomes THE app; the dashboard's
white-box views become modules mounted into it. The SPA shell and its
iframe boundary are retired. Root cause being solved: every SPA route
switch destroys and recreates the workbench iframe (full editor reload,
lost playback/selection state) — removing the iframe removes the jank
class entirely.

Sequencing is add-first, remove-later, because `tests/test_dashboard_server.py`
asserts the SPA shell today. Three pieces, single implementer (Codex,
reassigned 2026-07-03 — one owner through the switchover beats a mid-change
handoff). Pieces stay in this order; each piece fully green before the next.

### Piece V2-1 (additive only — SPA untouched, guards must stay green)

1. Add a slide-over panel host to the native page: a right-side full-height
   panel (~640px, above the page with a scrim on the remaining area is NOT
   allowed over the monitor/lanes — instead the panel pushes content or
   overlays ONLY when opened from strip/white-box links, and closes with X
   or ESC, returning exactly to prior editor state; the editor is never
   unmounted).
2. Port the four SPA views (RouteOverview, Artifacts, Verify, MaterialMap)
   into native-page modules rendered inside the slide-over. Reuse the
   existing view code and api wrappers from `dashboard/src/` — import them,
   do not rewrite logic. Views receive the current `?root=` context.
3. Wire entries: pipeline-strip stage pills and every black-box
   「展開完整數據」 link open the slide-over to the matching module
   (no more navigation to SPA routes from within the workbench).
4. Drawer one-row compaction: search box (flex) + type select + collapse
   toggle merge into a single row; asset count folds into the header; the
   fit-only checkbox becomes a compact chip; asset cards become a two-column
   thumbnail grid (name overlaid, badge and duration in corners).
5. Run selector in the native top bar: list from `/api/projects`, selected
   root drives `?root=` on subsequent API calls (same validation rules as
   before).
6. Acceptance: both smoke guards green; full suite green; opening/closing
   every slide-over module three times leaves playback position, clip
   selection, and drawer state intact (verify in a real browser).

### Piece V2-2 (the switchover — server + tests + docs)

1. `tools/dashboard_server.py`: serve the native workbench page as the home
   route; keep legacy SPA shell reachable at an explicit legacy path or
   remove per test updates.
2. Update `tests/test_dashboard_server.py` and, if needed, the SPA-host
   branch of `tools/workbench_browser_layout_smoke.mjs` to assert the new
   single-document home (native markers remain the source of truth).
3. Update `dashboard/workbench_native/API_CONTRACT.md` (Protected Zone
   wording about the SPA shell) and
   `docs/construction-guides/dashboard/dashboard-spa-workbench-migration-spec.md`
   (mark the shell retired).
4. Acceptance: full suite green; both guards green against the new home.

### Piece V2-3 (cleanup after V2-2)

1. Remove SPA-shell-only wiring that piece V2-1 kept alive (router shell,
   shell header), keeping the `dashboard/src` modules that the native page
   now imports.
2. Acceptance: guards + full suite green; no dead nav entries.

Out of scope for V2: rewriting editor interactions, new endpoints, physical
archival of legacy pages (own order, can ride with V2-2).

## Implementation Report

### Git Commits
- **Step 2 (Collapsible material drawer)**: `d39f3c33`
- **Step 3 (Fit badges & contract filter)**: `ba1d517b`
- **Step 4 (Swap safety & draft markers)**: `9514acca`
- **Step 5 (Domain contract inspector views)**: `e4abb0d0`
- **Step 6 (Collapsible pipeline status strip)**: `0badccca`
- **Step 7 (Humanize inspector labels & save feedback)**: `81554ef8`
- **Step 8 (Material gap request helper)**: `852dfa87`
- **Step 9 (Make workbench default home route)**: `2509a3df`

### Mismatches & Contradictions (Rule G)
1. **Material Drawer Replacement Candidates**: In `workbench_materials.js`, `replacementCandidates()` automatically filtered out the currently selected scene/clip, causing search logic to fail if we wanted to match status on it. We solved this by falling back to `Materials.matchStatusForNeed` for the selected clip.
2. **Template CSS vs. HTML Class Names**: `workbench_first_template.html` used status styles like `.st-done`, `.st-now`, and `.st-todo` but its HTML elements used classes like `pstep ok`. We aligned this by using the CSS-defined classes `.st-done`, `.st-now`, `.st-todo` on the status elements.
3. **Friendly Labels Scope**: The specification only asked to humanize labels for `duration_sec` and `source_start_sec`. To prevent unintended side effects, we only modified these two and kept `source_duration_sec` aligned.
4. **Header Layout and Icons Placement**: The top bar of the SPA and native index.html have separate structures. To satisfy the layout smoke ratio test (which checks viewport ratios inside the native iframe), we placed the domain icons inside the native header's `.wb-badges` flex container and fixed the header height to exactly `48px`.
5. **SPA Home Route configuration**: Making `/workbench` the home route was done by mapping `routes["/"] = "workbench"` and `pathForView("workbench") = "/"` to maintain clean navigation and allow fallback routes.

### Test Verification
- **Layout Smoke Test**: Passed with `"ok": true`.
- **Frontend Smoke Test**: Passed with `"ok": true`.
- **Unit Test Suite**: Ran successfully and matches baseline.

### Fix Round Report (v1.1)

- **Bug fix (Item 1)**: Removed inline style from `#pipestrip` (`display: none;`) to allow `.show` toggle class to control visibility.
- **Placement & Text fixes (Items 2, 3)**:
  - Added primary blue save button 「儲存並交給 agent」 to the top bar (`id="btn-save-all"`) and renamed footer button ID to `btn-save-all-footer`.
  - Renamed 「輸出 ffmpeg 草稿」 to 「輸出審閱影片」.
- **Declutter: REMOVE (Items 4-10)**:
  - Removed header subtitle and badges 「草稿編輯」「正式輸出 = ffmpeg BUILD」.
  - Removed left vertical tab rail.
  - Removed transport frame label 「f0」, audio status text, monitor overlay meta (`#stage-meta`), and asset card metadata (leaving only duration).
  - Removed track hint text.
  - Optimized project scanning in `dashboard/src/main.js` to lazy-load on select box focus, eliminating browser test timeouts.
- **Declutter: DEMOTE (Items 11-12)**:
  - Collapsed track tools and secondary footer buttons into a single collapsible `<details class="adv-tools">` area.
- **Global Styling (Item 13)**:
  - Updated root custom properties in `workbench.css` to match clean white look.

#### Git Commits:
- **Commit 1 (Items 1-3)**: `9ce0845d` —— `Fix pipestrip toggle and move save button`
- **Commit 2 (Items 4-6)**: `da837aa3` —— `Remove legacy subtitle, badges, and tab rail`
- **Commit 3 (Items 7-10)**: `2786cb58` —— `Remove legacy frame-label, audio status, stage meta, and card metadata`
- **Commit 4 (Items 11-12)**: `a1ec2645` —— `Demote advanced tools and secondary buttons into details container`
- **Commit 5 (Item 13)**: `bf4ff9d6` —— `Align workbench.css with template clean white tokens`

#### Test Verification:
- **Layout Smoke Test**: Passed with `"ok": true`.
- **Frontend Smoke Test**: Passed with `"ok": true`.
- **Unit Test Suite**: Passed successfully.

## V2 Report

### Commits

- **Support fix**: `75ea975a` — `Isolate MV render temp segments on Windows`
- **V2-1**: `d84940a3` — `Add slide-over module host and port dashboard views`
- **V2-2**: `196a8e14` — `Serve native workbench as home and retire SPA shell routing`
- **V2-3**: `a8dcc046` — `Remove retired SPA shell wiring`

### Piece Results

#### V2-1 Additive Module Host

- Added the native Workbench slide-over host.
- Imported existing Dashboard white-box views from `dashboard/src` into the native page:
  Route, Material Map, Artifacts, and Verify.
- Wired pipeline strip steps and "expand full data" actions to the slide-over.
- Added the run selector to the native top bar.
- Compact material drawer now uses a tighter one-row / two-column grid shape.

Verification:

- `node tools\workbench_browser_layout_smoke.mjs --artifact-root .tmp\wb_accept_fixture`
  passed with `"ok": true`.
- `python tools\workbench_frontend_smoke.py --artifact-root .tmp\wb_accept_fixture --exercise-replace`
  passed with `"ok": true`.
- Full suite after the Windows temp-file support fix:
  `Ran 2354 tests in 744.763s` / `OK`.
- Browser operation verified on `/workbench/index.html?root=...`:
  selected a video clip, scrubbed to `1.00 / 2.00s`, opened Material Map
  white-box, switched to Verify, closed the panel.
- State preservation verified:
  playback time remained `1.00 / 2.00s`; selected clip remained selected;
  material drawer state was unchanged; inspector state was unchanged; four lanes
  remained mounted.

#### V2-2 Native Workbench Home Route

- `/` and `/workbench` now serve the native Workbench document directly.
- `/dashboard`, `/material-map`, `/verify`, and `/artifacts` remain SPA
  white-box compatibility routes.
- Browser layout guard now treats native direct mode as the source of truth.
- API contract and migration spec now describe the native single-document route
  instead of the old SPA-hosted Workbench iframe.

Verification:

- Focused dashboard server tests:
  `Ran 30 tests in 125.485s` / `OK`.
- `node tools\workbench_browser_layout_smoke.mjs --artifact-root .tmp\wb_accept_fixture`
  passed with `"ok": true`.
- `python tools\workbench_frontend_smoke.py --artifact-root .tmp\wb_accept_fixture --exercise-replace`
  passed with `"ok": true`.
- Full suite:
  `Ran 2355 tests in 747.564s` / `OK`.
- Browser operation verified on `/workbench?root=...`:
  selected a clip, scrubbed to `1.00 / 2.00s`, opened Material Map white-box,
  switched to Artifacts, closed the panel.
- State preservation verified:
  playback time remained `1.00 / 2.00s`; selected clip remained selected;
  drawer/inspector state was unchanged; four lanes remained mounted.

#### V2-3 Retired SPA Shell Cleanup

- Removed the SPA Workbench iframe host from `WorkbenchView`.
- Replaced it with a lightweight handoff view linking to the native Workbench
  route and showing draft context.
- Removed iframe-specific CSS and layout smoke assumptions.
- Sanitized the SPA render smoke test so it validates structure and contract
  instead of mojibake text fixtures.
- Updated the migration and frontend implementation docs to make the native
  single-document route the current contract.

Verification:

- `node tests/dashboard_spa_render_smoke.mjs` passed.
- Focused dashboard server tests:
  `Ran 30 tests in 119.681s` / `OK`.
- `node tools\workbench_browser_layout_smoke.mjs --artifact-root .tmp\wb_accept_fixture`
  passed with `"ok": true`.
- `python tools\workbench_frontend_smoke.py --artifact-root .tmp\wb_accept_fixture --exercise-replace`
  passed with `"ok": true`.
- Full suite:
  `Ran 2355 tests in 675.680s` / `OK`.
- Browser operation verified on `/workbench?root=...`:
  selected `.clip-block`, scrubbed to `1.00 / 2.00s`, opened the Material Map
  white-box through `#pstep-material`, switched to Artifacts, closed via
  `#btn-whitebox-close`.
- State preservation verified:
  before and after both reported `time: "1.00 / 2.00s"`, selected clip count
  `1`, `laneCount: 4`, and panel hidden after close.

### Recorded Mismatches

1. Full unittest exposed an unrelated Windows temp MP4 lock in `mv_cut.py`.
   The support commit isolates MV render temp segments into per-run temp folders.
2. Browser `networkidle` is not a reliable wait condition for the native
   Workbench because media/proxy requests can keep the page active. Browser
   verification uses `domcontentloaded` plus `.wb-monitor`.
3. Existing route/archive cleanup changes were present in the working tree while
   this V2 task ran. They were not included in the V2 commits.
4. Running the full suite can regenerate root-level `supply_review.json`; it was
   removed after verification so the repo root is not polluted by test residue.
