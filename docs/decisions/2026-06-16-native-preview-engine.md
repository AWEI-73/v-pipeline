# 2026-06-16 — Hermes-native Remotion-like Preview Engine

Type: bounded feature (new interactive preview middle-layer). No renderer change,
no canonical-artifact change, no Remotion runtime.

## What this is — and is NOT

This is **not** a Remotion adapter. We do **not** install Remotion, do **not**
link the Remotion runtime, and do **not** modify the vendored `reference repo/
remotion-main`. We do **not** play `final.mp4` as the primary preview.

This **is** a Hermes-native interactive preview engine that *borrows the
preview model* Remotion popularized — `fps` / `currentTime` (frame) /
`durationInFrames` / composition props / per-clip media timing — and reimplements
the minimal slice we need (timeline state → live material preview → second/window
adjustment → patch) as our own contracts and our own ~300-line vanilla-JS core.

## Minimal Remotion reverse-engineering

Only three packages were read, and only to extract the conceptual model:

- `packages/player/src/use-playback.ts` — the playback loop.
- `packages/player/src/calculate-next-frame.ts` — frame advancement math.
- `packages/timeline-utils/src` + `packages/template-blank/src` — listing only,
  to confirm what a "composition" and a clip/timing look like.

### Concepts borrowed (and their Hermes-native mapping)

| Remotion concept | Where it lives in Remotion | Hermes-native form |
| --- | --- | --- |
| `fps` | composition config | `preview_timeline.fps` (default 30) |
| `currentFrame` / `currentTime` | `useTimelinePosition`, `usePlayback` | `currentTime` seconds (frames derived via `secondsToFrame`) |
| frame advance by wall-clock | `calculateNextFrame` (`floor(time*speed/(1000/fps))`) | `requestAnimationFrame` delta-time accumulation in `workbench.js` |
| `durationInFrames` | composition config | `preview_timeline.duration_sec` / `duration_frames` (deterministic from clip order) |
| composition props | `<Composition>` props | the `preview_timeline.json` document |
| media clip timing (`startFrom`/`endAt`) | `<OffthreadVideo>` etc. | clip `source_start_sec` / `source_duration_sec` |

### What we deliberately did NOT port

- Remotion's React/Studio renderer, `<Composition>`/`<Sequence>` component tree.
- Off-thread video decoding, audio sync anchor, buffering state machine,
  `SharedAudioContext`, media-session, waveform/thumbnail workers.
- License gating, RSC checks, server-side bundling/rendering.

### Why no Remotion dependency this round

1. **Tech fit** — Remotion is a React + Node-bundler render stack; Hermes BUILD
   is Python + ffmpeg. Adopting Remotion's runtime would add a large npm/React
   surface we explicitly forbade, for a preview-only need.
2. **Canonical render stays ffmpeg** — Remotion is a *renderer*; we already have
   one (ffmpeg, canonical). We only needed an *interactive preview*, not a second
   render path.
3. **Determinism & testability** — a tiny pure-JS core (`workbench_core.js`) is
   node-testable with zero toolchain and mirrors our Python contracts 1:1.

## Workbench vs. Review Dashboard

- **Review Dashboard** (`tools/dashboard_server.py`, `dashboard/dashboard_v1.*`)
  is **read-only** — a timeline inspector over canonical artifacts. POST is 405.
- **Workbench** (`tools/workbench_server.py`, `dashboard/workbench_native/`) is
  **write-limited & interactive** — it may write only the three workbench
  artifacts and is hard-blocked from canonical ones. It exists to *propose*
  edits, never to deliver.

They are separate servers, separate frontends, separate ports.

## Contracts

### `preview_timeline.json` (built, never authored)

Single input to the native preview frontend. Produced by
`tools/preview_timeline.py build` from `draft_timeline.json` / `timeline.json` +
`project_material_map.json` + `review_subtitles.srt`. Key invariants:

- `timeline_start_sec` is deterministic from clip order + `duration_sec`.
- video clips carry `source_start_sec` / `source_duration_sec`; image clips pin
  `source_start_sec = 0`.
- all seconds convert to frames (`fps`), but playback is seconds-first.
- `src_url` is a browser-safe `/media?src=<urlencoded>` URL — never a raw
  Windows path. Missing/!exists sources are demoted to `gap` / `render_failed`
  and surfaced in `diagnostics`.

### `timeline_patch.json` (the only write path for edits)

Op-list capturing interactive edits. `tools/timeline_patch.py validate|apply`.
Ops: `set_duration`, `set_source_window`, `move_clip`. Validation: duration > 0,
source_start ≥ 0, `source_start + source_duration` ≤ source asset window,
`slot_index` must exist, `move_clip` index in range. Invalid patches write
nothing. `apply` emits `patched_draft_timeline.json` and **never** touches
`timeline.json`. `slot_index` is a **stable identity** (never renumbered on a
move); ordering is represented purely by array position, so later ops in the
same patch keep targeting a clip by its original `slot_index`.

## Save-time FALLBACK spec alignment

On save, `apply_patch` runs `align_plan_to_contract` over the whole plan to
reconcile the edited values back onto the canonical timeline field spec — a
safety net that *fixes* drift instead of rejecting it:

- `slot_dur` / `extract_dur` forced > 0 (fall back to each other, else a min);
- video `extract_start` clamped ≥ 0 and within the source window;
- `extract_start + extract_dur` clamped to the material's `duration_sec`
  (the FALLBACK alignment to material spec);
- image clips pinned to `extract_start = 0`;
- numeric fields rounded to 3 dp for deterministic artifacts.

Every auto-fix is reported in `patched_draft_timeline._spec_alignment.corrections`
and echoed to the UI ("spec-aligned N field(s)"). This is why the saved artifact
is contract-conformant even when the base timeline carried drift.

## Optional export (`tools/workbench_export.py`)

The workbench is a lightweight editor; export is **opt-in**, not a second
renderer. The patched, spec-aligned `plan` is handed to the **canonical** ffmpeg
renderer (`mv_cut.render_mv`) — the same code path BUILD uses — and lands on
`workbench_export.mp4`. Canonical outputs (`final.mp4`, etc.) are hard-blocked;
attempting to export onto one raises. Exposed as CLI and an opt-in
`POST /api/workbench/export` (blocks until ffmpeg finishes). This gives the user
"a second set they can use to actually output" without introducing a browser
render pipeline.

## Patch → pipeline contract draft sync (NPE3)

`tools/workbench_patch_to_contract.py` translates a `timeline_patch` into a
**draft** `workbench_contract_patch.json` describing what the workbench would
like the pipeline contract to change — it never edits `segment_contract.json`.
`set_duration` → per-segment duration suggestion; `set_source_window` →
material window override validated against `project_material_map` scene bounds;
`move_clip` stays in the timeline draft (intra-segment = info, cross-segment =
`unsupported_for_contract_sync`, segment order never silently rewritten).
Fail-closed on unknown slot / non-finite duration / out-of-scene window. Exposed
as CLI and `POST /api/workbench/sync-contract` (writes only the two draft
artifacts). Official delivery still runs the Agent / ffmpeg pipeline on the
draft/patch, then builds.

## Lightweight editorial runtime tracks (NPE4)

The Workbench is now a **lightweight editorial runtime**, not just single-timeline
tuning. It previews and edits four track layers, each saved as an Agent-readable
draft patch — and it is explicitly **not** a final renderer, **not** Remotion, and
makes **no** pixel-perfect guarantee:

- **Subtitle** (`subtitle_patch.py` → `subtitle_patch.json`): text / start /
  duration; the source SRT is never rewritten; overlap is a warning.
- **Audio cue** (`audio_cue_patch.py` → `audio_cue_patch.json`): add/move/delete
  cue markers (enum cue_type, time ≤ duration+1s, strength 1–5, anchor checked).
  Marker layer, not a mixer.
- **Effect intent** (`effect_patch.py` → `effect_patch.json`): preset markers on a
  clip; window must fit the target clip (**fail-closed**). **Intent only — Node14
  consumption deferred, no effect rendered.**
- **Unified save / handoff** (`workbench_handoff.py` → `workbench_handoff.json`):
  `save-all` writes provided track patches atomically (any invalid → nothing
  written) and emits an index + per-layer edit counts for the Agent.

Server endpoints (`subtitle-patch`, `audio-cue-patch`, `effect-patch`, `save-all`)
are write-limited; `review_subtitles.srt` and all canonical artifacts are
hard-blocked. Official output still runs the Agent / FFmpeg / Node14 pipeline on
the drafts.

## ffmpeg BUILD remains canonical

A patch is an editorial *proposal*. The optional export reuses the canonical
ffmpeg renderer on the patched plan — it does not create a new render path and
never produces a canonical artifact. The full Hermes BUILD on canonical
artifacts remains the source of truth for delivery.

## Preview proxy cache (NPE6)

For `.MOV` / large source playback, the workbench can build derived preview
proxies: `tools/workbench_proxy.py` trims each approved video window into a
browser-friendly MP4 under `<root>/workbench_proxy/`. The frontend loads
`/api/workbench/proxies` asynchronously; when a proxy is ready, the monitor uses
the proxy URL and resets media seek time to zero. The original source path and
source window remain the data of record for patches, contract sync, and ffmpeg
BUILD.

This is still not a second canonical renderer. Proxies are cached previews only,
may fail independently, and fall back to original media. They are allowed through
the workbench `/media` gate only because they are derived files under the
artifact root.

## Deferred (intentional)

- Adopting Remotion `Player` / a full NLE.
- Canvas/WebGL multi-layer compositing, transitions, PiP/multi-video, waveforms,
  and in-browser export (Clipchamp-style). Export here is ffmpeg-backed, not
  browser-composited, by design.
- **Frame-cache / WebCodecs smooth scrubbing (Tier C).** NPE5 added a perf pass
  (cached `/media` allow-list, streamed media, seek-on-clip-change) and ffmpeg
  filmstrip thumbnails (`workbench_thumbs.py`) so the timeline is readable; but a
  real-NLE-smooth main monitor needs a frame cache / GPU decode pipeline
  (Remotion's `timeline-utils` does this via `mediabunny` + WebCodecs). That is a
  different tier, carries a `.MOV`/HEVC decode-support risk, and is deferred.
- Precise audio mixing (export uses `render_mv`'s music-mux only).
- Timeline-level drag-resize handles / split / library-add (Tier-1 interaction;
  the patch model already supports the data side).
- Node-registry "14" motion-graphics effects pathway.
- Promoting `patched_draft_timeline.json` back into the canonical chain (a BUILD
  re-entry gate) — out of scope this round.
