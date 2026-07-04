# Work Order: Storybook Run - stock-story

Date: 2026-07-04
Case name: stock-story

## Filled Dispatch

- Brief: `幫我做一支 60 秒的短片,主題是『城市裡的獨處時刻』,用 stock 素材,沉靜的氛圍配樂,結尾留一句字卡。`
- Materials: none - stock (Pexels)
- Expected entry path: structure-first
- Target: 60s, 16:9, subtitles optional

## Rules

1. Enter through the front door: `docs/START_HERE_VIDEO_PIPELINE.md`
   Rule Zero -> `skills/video-pipeline.md` -> `runtime.py` /
   `state.json.next_action`. Never hand-run ffmpeg or stitch materials outside
   the pipeline.
2. Probe, do not repair. When the route stalls, dead-ends, or does something
   surprising, capture state and artifacts, write a probe finding, then try to
   continue through legitimate pipeline means.
3. Record prompts, interactive answers, every `next_action` transition, gates,
   costs, interventions, and final artifacts.

## Result

### Result: stalled

- Run:
  `runs/storybook-stock-story/runs/20260704-storybook-stock-story-probe`
- Video: no `final.mp4`; the last successful render artifact was an audio-only
  intermediate, not a delivery-ready video.
- Cost: `$0` visible in this session. Mini-B reported no successful live
  stock-provider calls; the run used cached local stock clips. Although the
  supervisor confirmed a real-looking `PEXELS_API_KEY` in the root `.env`, this
  probe's own runtime reported missing provider keys, so this result must not be
  mixed with true-provider data.

### Route Trace

- `.rerun_guard.json`: `await_material` at node 2.
- Orchestrator advance: `missing_artifact:material_coverage_map.json`.
- After material coverage, spec review, assembly, and editor review:
  `await_visual_review`.
- After manual visual review verdict: `missing_artifact:final.mp4`.
- Final render failed at mux stage: `Stream map '0:v:0' matches no streams`.

### Gates And Evidence

- `.rerun_guard.json`: initial `await_material` block.
- `spec_review.json`: `ready_for_build=true`, with target-length mismatch and
  weak stock-query warnings.
- `material_coverage_map.json`: all 6 segments covered from local stock clips.
- `visual_review_request.json` / `visual_review_verdict.json`: 6 clips reviewed
  and accepted.
- `music_structure.json`: `sections=[]`.
- `timeline_build.json`: `clips=[]`.
- `mv_audio_wgm0gltx/mvseg_001.mp4` and later segments contain video streams.
- `mv_audio_wgm0gltx/mvseg_000.mp4` is audio-only.
- `mv_audio_wgm0gltx/mv_av.mp4` is audio-only per `ffprobe`.

### Interventions

- Mini-B manually wrote a visual review verdict to keep the state machine
  moving.
- No pipeline Q&A prompts appeared in the session.
- Mini-B did not modify repo files and did not commit.

### Probe Findings

- [High] Final concat path starts from an audio-only first segment, so assembled
  `mv_av.mp4` loses video stream structure before final mux. Suggested owner:
  audio/timeline assembly.
- [High] `timeline_build.json` has no clips, so downstream render has no actual
  video schedule to mux. Suggested owner: timeline builder / contract-run
  orchestration.
- [Medium] `music_structure.json` has no sections, so the timing scaffold for a
  60s piece is absent. Suggested owner: music analysis / assembly planner.
- [Medium] Run initially hit `await_material` because live stock route was
  unavailable and had to be backfilled with cached local clips. Suggested owner:
  stock intake / supply routing.
- [Low] `spec_review.json` still flags target-length mismatch and repeated
  search-query / weak-description issues. Suggested owner: contract authoring.

### Smoke Candidate

No. The route is useful product data, but it is not a passing happy path and
should not be pinned as an e2e smoke until live stock intake, timeline schedule,
music sections, and final muxing are fixed.
