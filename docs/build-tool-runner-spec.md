# BUILD Tool Runner Spec

Updated: 2026-06-06

This document is the BUILD-layer handoff for agents. `roadmap.md` records the
strategic direction; this file records the concrete runner contracts that turn
`segment_contract.json` into executable work.

## Current Position

The project already has a canonical SPEC surface and a working MVP runtime:

```text
segment_contract.json
-> contract_adapter.py
-> generated_mv_script.json
-> mv_cut.mv_chain()
-> final.mp4 + artifact_manifest.json + state.json
```

The next BUILD step is not to expand SPEC again. The next step is to make tool
selection and runner execution explicit enough that agents can perform the run
without guessing which tool owns each artifact.

## Runner Layer Model

Keep BUILD split into three layers:

```text
Policy artifacts
  build_profile.json
  model_routes.json

Request artifacts
  generated_asset_requests.json
  motion_graphics_render_plan.json
  assembly_plan.json
  timeline_build.json

Runners
  stock runner
  generated asset runner
  motion graphics runner
  mv_chain render runner
  verify/editor-review runner
```

Policy artifacts decide what is allowed. Request artifacts describe work to do.
Runners perform the work and write manifests.

## Runner Contracts

| Runner | Status | Input | Output | Notes |
|---|---|---|---|---|
| `contract_adapter.run_contract` | wired | `segment_contract.json`, `materials_db.json`, music file, optional build/model profiles | `generated_mv_script.json`, `build_profile.json`, `model_routes.json`, `generated_asset_requests.json`, `music_structure.json`, `assembly_plan.json`, `timeline_build.json`, `editor_review.json`, `artifact_manifest.json`, `state.json`, `final.mp4` | Current canonical MVP entrypoint. |
| Stock runner | wired through runtime | `source=stock` segments, `search_query`, Pexels/Pixabay keys | downloaded stock material, selected clip paths | Pexels first, Pixabay fallback. Good enough for conceptual MVP. |
| Local material runner | wired through `ingest-meta` / `caption-meta` / `match-mv` | local folders | `materials_db.json`, captions, match output | Useful when students/users provide assets. Needs dashboard ergonomics later. |
| Generated asset runner | manual/provider adapter wired | `generated_asset_requests.json`, provider/manual outputs JSON | `generated_asset_manifest.json` | Stays provider-neutral. Antigravity / assistant_imagegen / codex_imagegen can satisfy the request externally, then `video_tools.py generated-manifest` validates and records the result. |
| Light effects runner | ffmpeg-safe plan wired | `segment_contract.json`, `build_profile.json` | `light_effects_plan.json`, `light_effects_manifest.json` | Maps contract facets to safe operations: grade, Ken Burns, title card, lower third, xfade. |
| Motion graphics runner | plan-only | `motion_graphics_contract.json` or generated render plan | `motion_graphics_manifest.json`, rendered overlays/assets | Current module validates and plans. Real heavy runner is not wired yet. |
| MV render runner | wired | generated runtime payload + selected material/music | `final.mp4`, render plan, state | Implemented by `video_pipeline_core.mv_cut`. |
| Editor review runner | wired | `timeline_build.json` | `editor_review.json` | Deterministic checks before expensive iteration. |
| Dashboard/story-map runner | wired | `artifact_manifest.json`, `state.json`, related artifacts | self-contained HTML | Read-only surface for node/skill/output status. |

## Required BUILD Artifacts

Every canonical BUILD run should write or explicitly mark these artifacts:

```text
generated_mv_script.json
build_profile.json
model_routes.json
generated_asset_requests.json
music_structure.json
assembly_plan.json
timeline_build.json
editor_review.json
artifact_manifest.json
state.json
final.mp4
```

Optional artifacts:

```text
stock_first_route.json
generated_asset_manifest.json
motion_graphics_contract.json
motion_graphics_render_plan.json
motion_graphics_manifest.json
light_effects_plan.json
light_effects_manifest.json
revision_plan.json
```

If an optional artifact is not produced, dashboard should show it as optional,
warn, or blocked according to `build_profile.json` and `state.json.next_action`.

## Tool Selection Rules

`build_profile.json` owns tool choices:

```json
{
  "render_profile": "no_effects | light_effects | motion_graphics | debug",
  "fallback_visual_provider": "antigravity | assistant_imagegen | codex_imagegen | gemini_veo | pexels | pixabay",
  "fallback_visual_mode": "stock_video | generated_image | generated_video | text_bridge",
  "effects_enabled": false,
  "motion_graphics_backend": "ffmpeg_libass | html_playwright | remotion | mlt | blender",
  "model_routes": "model_routes.json"
}
```

Rules:

- `no_effects` is the MVP quality baseline.
- `light_effects` may use ffmpeg-native grade, xfade, Ken Burns, lower-third,
  title-card, subtitle styling.
- `motion_graphics` requires explicit `motion_graphics_render_plan.json`.
- Generated providers must be external to the core runner unless a dedicated
  provider runner is added.
- ComfyUI remains deprecated/disabled unless explicitly requested as an isolated
  experiment.
- `model_routes.json` keeps visual judgment roles (`video_understanding`,
  `verify_vlm`, `content_qa`) on the agent/cloud route by default. Local
  Ollama/qwen is legacy opt-in only and must not be the default gate.

## Implementation Priorities

### P1: Build Runner Manifest Completeness

Status: implemented.

Review:
`contract_adapter.run_contract` already writes most artifacts, but the manifest
should be the single index for dashboard and route.

Build:
Ensure `artifact_manifest.json` records every required and optional artifact
with stable relative or absolute paths. Add explicit nulls for optional artifacts
that were intentionally skipped.

Verify:
Unit test that a canonical run manifest contains all required keys and that
dashboard reads generated manifest paths from the manifest.

### P2: Generated Asset Runner Boundary

Status: implemented for manual/provider adapter; direct provider calls remain out
of scope.

Review:
Generated fallback is currently request-only. This is correct for MVP, but route
must know whether it is waiting for a provider or can continue with stock/text.

Build:
Add a small runner interface that can consume `generated_asset_requests.json`
and write `generated_asset_manifest.json`. The first implementation validates
externally created files and can attach the generated manifest path back to
`artifact_manifest.json`.

Runtime:

```bash
python3 video_tools.py generated-manifest generated_asset_requests.json \
  --outputs generated_asset_outputs.json \
  --out generated_asset_manifest.json \
  --artifact-manifest artifact_manifest.json
```

Verify:
Test that a request with generated-capable segments blocks or warns until a
matching generated manifest appears, then dashboard Node 8 becomes satisfied.

### P3: Light Effects Runner

Status: implemented as ffmpeg-safe operation planner; per-operation rendering
can be added after dashboard/route consumes the plan.

Review:
Motion graphics is too heavy for MVP, but light effects are useful and already
close to existing ffmpeg tools.

Build:
Create a light effects plan that maps contract visual/text facets to existing
ffmpeg-safe tools: grade, xfade, Ken Burns, title-card, lower-third/name-super,
subtitle style.

Runtime:

```bash
python3 video_tools.py light-effects-plan segment_contract.json \
  --build-profile build_profile.json \
  --out-dir build
```

Verify:
Smoke test a no-effects run and a light-effects run from the same contract. The
light-effects run must not change SPEC artifacts.

### P4: Motion Graphics Runner

Review:
`motion_graphics.py` currently validates and writes plans. That is enough for
spec clarity but not enough for actual title/list/card animation.

Build:
Add a backend runner in this order:

```text
1. ffmpeg_libass
2. html_playwright
3. remotion
4. blender / external_ae only as explicit heavy backend
```

Verify:
Test that heavy backends are rejected unless policy allows them. For
`ffmpeg_libass`, verify rendered overlay files exist and are listed in
`motion_graphics_manifest.json`.

### P5: Dashboard Build Control Surface

Review:
Dashboard is currently read-only. That is fine for review, but BUILD work needs
a clear visual surface for node -> skill -> output.

Build:
Keep dashboard read-first. Add controls only after artifact contracts are stable:
profile selection, generated request status, material selected/generated
preview, route next_action, and per-node artifact open links.

Verify:
Render dashboard/story-map from a canonical run and confirm Node 8-14 reflect
manifest artifacts rather than inferred file guesses.

## P1 Verification Tool Pack (implemented 2026-06-07)

Deterministic editing-quality evidence at Node 11/12. See
`docs/video-autopilot-tool-integration-spec.md`. All artifacts are optional
VERIFY evidence, never SPEC truth, and are inert when not produced.

| Runner | Module | CLI | Artifact | Owner Node | Status |
|---|---|---|---|---|---|
| Timeline invariants | `timeline_invariants.py` | `timeline-audit` | `timeline_invariants.json` | 11 | implemented |
| B-roll/repetition audit | `broll_audit.py` | `broll-audit` | `broll_audit.json` | 11 | implemented |
| Caption timing audit | `caption_audit.py` | `caption-audit` | `caption_audit.json` | 11/12 | implemented |
| Keyframe grid | `keyframe_grid.py` | `keyframe-grid` | `keyframe_grid.jpg` | 12 | implemented (ffmpeg) |
| Visual audit | `visual_audit.py` | `visual-audit` | `visual_audit.json` | 12 | implemented (mechanical; optional VLM) |

Integration:

- Manifest: optional keys added to `artifact_manifest.json` (null by default).
- Dashboard: audits attached as evidence on Node 11/12 with pass/warn/fail
  findings (`dashboard_state.load_dashboard_state`).
- Node registry: audit artifacts listed in Node 11/12 `outputs` for lifecycle
  cleanup; `outputs[0]` unchanged.
- Runtime: `runtime_orchestrator.resolve_audit_route` consumes audit findings
  and routes the smallest affected node/skill; it runs no audit algorithm and is
  inert when no audit findings exist.
- Auto-generation (P1.5): `contract_adapter.run_contract` calls `_write_p1_audits`
  after build/render. It produces the deterministic audits from `timeline_build`
  + `subtitles.srt`, and `keyframe_grid` + mechanical `visual_audit` from
  `final.mp4`. Gated by `build_profile.verification_tools` (all OFF by default).

Enable per project in `build_profile.json`:

```json
{
  "verification_tools": {"timeline_invariants": true, "broll_audit": true,
    "caption_audit": true, "keyframe_grid": true, "visual_audit": true},
  "broll_policy": {"target_ratio": null, "max_source_repeats": null},
  "keyframe_grid": {"sample_count": 12, "columns": 4}
}
```

Policy is parameterized (build_profile / creator profile / brief). No creator
keyword map or preferred ratio is baked in. Mechanical-only verify works without
Ollama; the optional VLM reviewer takes provider/model lineage from model routes.
`caption-audit` reads a real `subtitles.srt` (`--srt`) or a caption-events JSON.
`keyframe-grid` fails loudly when no frames can be extracted.

Acceptance evidence (2026-06-07):

- Full Windows suite: `320 tests OK`.
- Disabled by default: a standard run produces no audit artifacts (manifest keys
  null); existing behavior unchanged.
- One-click smoke with all tools enabled (real 5s video): all five artifacts
  written from a single build pass; `broll_audit` correctly fails to `curator`
  on a reused source; `keyframe_grid.jpg` is a real ~80 KB image;
  `visual_audit` mechanical `pass` with `model_review: null`.
- Deterministic bundle smoke: timeline-audit must-include failure routes to
  `fix_timeline_or_assembly`; caption-audit excludes name supers from subtitle
  overlap and parses SRT cues.

## Agent Work Rules

- Do not make `segment_contract.json` provider-specific.
- Do not let generated providers write truth-critical evidence.
- Do not bury tool choices in prompts; write them to `build_profile.json`.
- Do not call motion graphics heavy backends unless the build profile allows it.
- Do not treat `generated_mv_script.json` as public SPEC.
- Do not add new root-level god modules; put implementation in
  `video_pipeline_core/` and expose through `video_tools.py` only when needed.

## Verification Commands

Use these before claiming BUILD flow changes are complete:

```bash
cd ~/video_pipeline
python3 -m unittest tests.test_contract_adapter tests.test_build_profile tests.test_generated_assets tests.test_motion_graphics tests.test_dashboard_state -v
python3 -m unittest discover -s tests -v
```

For a manual MVP run:

```bash
python3 video_tools.py contract-run examples/segment_contract_graduation_mv.json \
  --categories examples/material_categories.json \
  --material-db /path/to/materials_db.json \
  --music /path/to/music.mp3 \
  --out /tmp/video_route_story_mv/final.mp4
```
