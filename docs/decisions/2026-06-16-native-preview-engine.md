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
`timeline.json`.

## ffmpeg BUILD remains canonical

A patch is an editorial *proposal*. Official rendering still runs through Hermes /
ffmpeg BUILD on canonical artifacts. The workbench never renders.

## Deferred (intentional)

- Adopting Remotion `Player` / a full NLE.
- Precise audio mixing, multi-video simultaneous playback, transitions, canvas
  compositing, waveforms, drag-resize, real export/final render.
- Node-registry "14" motion-graphics effects pathway.
- Promoting `patched_draft_timeline.json` back into the canonical chain (a BUILD
  re-entry gate) — out of scope this round.
