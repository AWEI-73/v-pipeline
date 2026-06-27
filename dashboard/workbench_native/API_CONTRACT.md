# Workbench API Contract

This contract documents the browser-facing API used by the Hermes native
Workbench. It lives beside the frontend modules because it is the contract
Workbench contributors should check before adding UI features.

The Workbench is a draft review/editing surface. It previews material
composition and writes draft artifacts. It is not the canonical renderer and it
must not overwrite pipeline truth.

## Ownership

### Canonical Files: Read-Only

Workbench routes must not write or replace these files:

- `timeline.json`
- `project_material_map.json`
- `material_needs.json`
- `segment_contract.json`
- `final.mp4`
- source media files

### Draft Files: Writable By Workbench

The server may write only fixed basenames from its whitelist:

- `preview_timeline.json`
- `timeline_patch.json`
- `patched_draft_timeline.json`
- `workbench_contract_patch.json`
- `subtitle_patch.json`
- `audio_cue_patch.json`
- `effect_patch.json`
- `workbench_handoff.json`
- `workbench_review_report.json`
- `workbench_review_report.md`

Anything else belongs in the backend or Agent pipeline, not the browser.

## Frontend Modules

- `workbench_core.js`: pure deterministic timeline/editing logic.
- `workbench_api.js`: HTTP endpoint wrapper. Add endpoint names here only after
  the Python server route exists and has tests.
- `workbench_materials.js`: pure material-browser helpers.
- `workbench.js`: DOM controller, browser preview, and user interaction.

## Native Editor Protected Zone

The native Workbench owns the editing-critical surface:

- video monitor / playback preview;
- four lower timeline lanes: video, subtitle, audio, and effect;
- clip selection, drag/replace, trim/source-window interaction, playback
  controls, and patch/handoff actions tied to those lanes.

Dashboard/SPA migration may wrap this surface in a shell, show health and draft
summaries around it, and pass a `root` parameter into it. It must not duplicate,
mirror, or reimplement the native monitor or four-lane editor unless a dedicated
Workbench migration task proves parity for playback, lane interaction, source
window mapping, and draft artifact writes.

The browser guard for this boundary is:

```powershell
node tools\workbench_browser_layout_smoke.mjs --url http://localhost:8765/workbench
```

The guard verifies the SPA host still embeds `/workbench/index.html`, then
enters the native iframe and checks the 16:9 monitor, playback controls, and
four timeline lanes. On the SPA host side, it also fails if the outer shell
duplicates protected editor selectors such as `monitor-box`, `timeline-wrap`,
`clip-video`, `wb-monitor`, `wb-timeline`, `track-lane`, or `lane-video`. Run it
before and after any change touching the iframe shell, native monitor, playback
controls, timeline lanes, or their responsive layout.

The fast HTML/API guard is:

```powershell
python tools\workbench_frontend_smoke.py --artifact-root .tmp\workbench_frontend_smoke_fixture --init-fixture
python tools\workbench_frontend_smoke.py --artifact-root .tmp\workbench_frontend_smoke_fixture --exercise-replace
```

This guard checks protected HTML markers, draft writes, canonical write
protection, and `replace_clip`. `--init-fixture` refuses non-empty folders by
default; use it only with disposable `.tmp` paths, or add
`--force-init-fixture` when intentionally recreating that scratch fixture.

## Endpoints

### `GET /workbench`

Serves the Workbench HTML shell.

### `GET /workbench/<file>`

Serves fixed frontend assets from `dashboard/workbench_native`. Traversal and
nested paths are denied.

### `GET /media?src=<absolute path>`

Serves allow-listed source media, thumbnail cache files, and proxy cache files.

Rules:

- source must be present in `preview_timeline` material/clip/effect projection,
  or under the Workbench derived thumbnail/proxy directories;
- supports HTTP byte ranges for browser video seeking;
- must not become a generic filesystem server.

### `GET /api/workbench/preview-timeline`

Builds the browser preview projection from existing artifacts.

Consumer:

- `WorkbenchApi.fetchPreviewTimeline()`

Expected use:

- initial UI load;
- reading clips, subtitles, audio/effect intent markers, material assets, and
  effect assets.

Non-goal:

- this is not a canonical timeline writer.

### `GET /api/workbench/thumbnails`

Builds/reads derived filmstrip thumbnails under `workbench_thumbs/`.

Consumer:

- `WorkbenchApi.fetchThumbnails()`

Rules:

- derived cache only;
- may be slow on first run;
- failure should degrade preview only.

### `GET /api/workbench/proxies`

Builds/reads derived preview proxies under `workbench_proxy/`.

Consumer:

- `WorkbenchApi.fetchProxies()`

Rules:

- derived cache only;
- used to reduce browser `.MOV` seek stalls;
- official rendering still uses canonical source media.

### `POST /api/workbench/patch`

Validates and writes one `timeline_patch.json`, applies it to a draft timeline,
and refreshes `preview_timeline.json`.

Consumer:

- `WorkbenchApi.savePatch(patch)`

Writes:

- `timeline_patch.json`
- `patched_draft_timeline.json`
- `preview_timeline.json`

Common operations:

- `set_duration`
- `set_source_window`
- `replace_clip`
- `move_clip`

Rules:

- validation is fail-closed;
- canonical `timeline.json` is never overwritten;
- replacement must resolve through `project_material_map.json`.

### `POST /api/workbench/save-all`

Atomic save for all draft layers.

Consumer:

- `WorkbenchApi.saveAll(payload)`

Payload keys may include:

- `timeline_patch`
- `subtitle_patch`
- `audio_cue_patch`
- `effect_patch`

Writes:

- any valid supplied layer patch;
- `patched_draft_timeline.json` when `timeline_patch` is supplied;
- `workbench_handoff.json`.

Rules:

- validates all supplied layers before writing anything;
- if any layer is invalid, writes nothing;
- intended as the normal save path for human fine-tuning.

### `POST /api/workbench/review-report`

Builds an Agent-readable report from current draft artifacts.

Consumer:

- `WorkbenchApi.writeReviewReport()`

Writes:

- `workbench_review_report.json`
- `workbench_review_report.md`

Rules:

- report is draft evidence;
- `canonical_changed` must remain false unless a future explicit canonical
  writer exists.

### `POST /api/workbench/sync-contract`

Translates a timeline patch into a draft pipeline-contract patch.

Consumer:

- `WorkbenchApi.syncContract(patch)`

Writes:

- `workbench_contract_patch.json`
- `patched_draft_timeline.json`

Rules:

- draft-only;
- fail-closed on source-window bounds and malformed inputs;
- never rewrites `segment_contract.json`.

### `POST /api/workbench/export`

Optional review export through the ffmpeg path.

Consumer:

- `WorkbenchApi.exportFfmpeg(payload)`

Writes:

- `workbench_export.mp4` or another non-protected output name.

Rules:

- must refuse protected output basenames such as `final.mp4`;
- does not replace official BUILD output;
- useful for review, not delivery truth.

### Single-Layer Patch Endpoints

These exist for focused layer saves:

- `POST /api/workbench/subtitle-patch`
- `POST /api/workbench/audio-cue-patch`
- `POST /api/workbench/effect-patch`

Current UI primarily uses `save-all`; new frontend features should prefer
`save-all` unless there is a concrete UX reason for single-layer writes.

## Dashboard Read API

Dashboard reads Workbench draft status through its own `/api/artifacts` response:

- `workbench.draft_artifacts`
- `workbench.draft_summary`
- `workbench.draft_summary.agent_ready`

`agent_ready` is true only when both `workbench_handoff.json` and
`workbench_review_report.json` exist. It means "ready for Agent review", not
"safe to accept".

Control Index reads the compact frontend manifest from
`/api/control/status`. It uses `/api/control/workbench-health` as a same-origin
proxy for Workbench server liveness.

## Workbench Health

### `GET /api/workbench/health`

Returns a small diagnostic payload for tooling and the Dashboard server proxy.
It must not build thumbnails, proxies, or preview timelines.

Example:

```json
{
  "artifact_role": "workbench_health",
  "version": 1,
  "status": "ok",
  "artifact_root": "C:/path/to/run",
  "can_preview": true,
  "write_limited": true,
  "writable_artifacts": ["timeline_patch.json"]
}
```

`can_preview` is true when the artifact root contains one of the timeline inputs
the preview builder can consume: `draft_timeline.json`, `timeline.json`, or the
legacy `timeline.plan`.

Browsers should normally use the Dashboard same-origin proxy
`/api/control/workbench-health` instead of calling this cross-origin endpoint
directly.

## Extension Rules

When adding a new Workbench feature:

1. Prefer extending an existing draft patch payload before adding an endpoint.
2. Keep deterministic edit math in `workbench_core.js` or another pure helper.
3. Keep endpoint wrappers in `workbench_api.js`.
4. Keep canonical validation and artifact write rules in Python.
5. Add focused JS smoke tests for any new frontend helper.
6. Add Python endpoint tests for every new server write path.
7. Update this file and `docs/workbench-dashboard-integration.md`.

Do not add placeholder endpoints "for later". Add an endpoint only when there is
a tested consumer and a specific draft artifact contract.
