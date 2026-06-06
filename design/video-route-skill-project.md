---
title: Video Route Skill Project
type: design
status: active
updated: 2026-06-01
tags: [video, route-skill, portable-agent-flow, dashboard, material-sources]
---

# Video Route Skill Project

## Purpose

This project is the portable agent workflow for video editing.

It should work for Hermes and for other agent platforms that can read skill
instructions, run shell commands, and inspect JSON artifacts. The project is not
an image-generation provider project and not a one-off WSL demo. It is the
reusable route skill kit that coordinates video production through explicit
contracts.

## Product Boundary

The core product is:

```text
brief / interactive spec
-> segment_contract.json
-> deterministic build profile + runtime payload
-> final.mp4 + artifact_manifest.json + state.json
-> route skill -> dashboard/review
```

The core product is not:

- a full high-end motion graphics studio;
- a ComfyUI/Antigravity/imagegen workflow repository;
- a platform-specific Hermes-only extension;
- a pile of unrelated scripts copied between folders.

The first milestone is a complete, portable route skill project that can make
solid narrative/MV videos, expose honest failure states, and accept better
material sources later.

## Layer Model

### 1. Tools

`video_tools.py` contains deterministic operations:

- TTS and SRT generation;
- audio mix;
- stock search/download;
- local media analysis;
- montage/collage/Ken Burns/title sequence rendering;
- ffmpeg composition;
- technical verify.

Tools should be callable from any agent platform. They should not make routing
decisions.

### 2. Skills

`skills/*.md` contains role contracts:

- `writer`: produce text/narrative facets inside `segment_contract.json`;
- `audio-director`: produce voice/BGM artifacts;
- `subtitle-director`: produce subtitles;
- `curator`: select material candidates;
- `editor`: assemble deterministic video;
- `effects-director`: apply style, grade, titles, transitions;
- `verify`: judge output quality;
- `route`: decide the next action from `state.json`;
- `dashboard`: show progress and review state.

Skills describe taste and I/O. They should avoid platform-specific assumptions
except in a small setup/run section.

### 3. Route

`route.py` is the orchestration layer. It reads `state.json.next_action` and
decides what to do next:

| State | Route behavior |
|---|---|
| no `state.json` | run a full build |
| `next_action == null` | stop: final video is ready |
| `await_material` | check `--material-dir` for `seg{n}_user.*`, switch that segment to `source=local`, then run `--only-seg n` |
| `retry:curator(seg=[...])` | stop for human/source intervention; pipeline already exhausted automatic retry |
| `needs_generated(seg=[...])` | future: request generated material provider output |
| `review` | stop for human review |

Route does not pick clips, write prompts, edit videos, or judge aesthetics. It
only dispatches.

### 4. Dashboard

Dashboard is the human review surface over `state.json` and artifacts. It should
show:

- stage status;
- final video link;
- QA score and dimensions;
- low/unfixable segments;
- `next_action`;
- required user material;
- source type per segment;
- selected candidate thumbnails;
- route command suggestions.

The dashboard should not become the source of truth. It reads project artifacts.

## Canonical Flow

```text
1. interactive brief/director/writer/spec-contract produce `segment_contract.json`
2. contract adapter validates canonical SPEC and emits runtime payload/artifact manifest
3. build profile selects provider/model/effects/tool policy
4. runtime creates audio/subtitles/material picks/renders/final/QA artifacts
5. `state.json` records route truth and verification status
6. `route.py` reads `state.json.next_action`
7. route either stops, asks for material/generated output/review, or reruns targeted segments
8. dashboard visualizes node -> skill -> output -> status -> next action
```

## Material Source Contract

The pipeline should converge on one material-source model:

```json
{
  "segment": 6,
  "source": "stock | local | generated",
  "file": "/absolute/path/to/material",
  "provider": "pexels | pixabay | user_upload | antigravity | assistant_imagegen | codex_imagegen | gemini_veo | manual",
  "status": "candidate | selected | rejected | needs_review",
  "score": 0.0,
  "visual_desc": "Chinese visual description used for QA",
  "metadata": {}
}
```

### Stock

Current default. Good for generic scenes and filler B-roll. Weak for specific
people, local food, school/class scenes, and exact story beats.

```json
{
  "segment": 2,
  "source": "stock",
  "provider": "pexels",
  "file": "/tmp/run/materials/seg2_raw.mp4",
  "status": "selected",
  "score": 100.0,
  "visual_desc": "夜晚下雨的城市街道，路面反光，車燈與霓虹在雨水中閃爍",
  "metadata": {
    "query": "雨夜 街道",
    "asset_id": "pexels:12345"
  }
}
```

### Local

Primary path for real project footage. Route already supports
`seg{n}_user.jpg|mp4` handoff through `--material-dir`.

```json
{
  "segment": 6,
  "source": "local",
  "provider": "user_upload",
  "file": "/home/user/student_uploads/seg6_user.mp4",
  "status": "selected",
  "score": null,
  "visual_desc": "雨後清晨的城市街道，天空微亮，地面仍有積水反光",
  "metadata": {
    "route": "await_material",
    "original_name": "seg6_user.mp4"
  }
}
```

### Generated

Reserved provider slot for Antigravity, assistant/Codex image generation, Gemini
Veo, or another generator. Generated material must enter the pipeline as normal
files plus metadata. The route skill project should not own provider
installation, workflow JSON, model downloads, or local GPU setup.

```json
{
  "segment": 6,
  "source": "generated",
  "provider": "assistant_imagegen",
  "file": "/tmp/run/materials/generated/seg6.jpg",
  "status": "selected",
  "score": null,
  "visual_desc": "雨後清晨的城市街道，天空微亮，地面仍有積水反光",
  "metadata": {
    "prompt_file": "/tmp/run/materials/generated/seg6.json",
    "external_provider": true
  }
}
```

## Generated Provider Boundary

Generated material providers are developed in separate projects/agents.
Antigravity and assistant/Codex image generation are the preferred image sources
for the current BUILD layer. ComfyUI is deprecated/disabled by default because
current output quality is below those sources.

This project accepts generated output only through the material source contract:

```text
materials/generated/seg6.jpg
materials/generated/seg6.json
```

The metadata file should include prompt, negative prompt, seed, workflow name,
model, generation time, provider, and any safety/quality notes. Once present,
route can treat the segment as `source=generated` and rerun `--only-seg 6`.

Do not commit provider client code, installers, model files, or workflow
experiments into the route skill core. ComfyUI artifacts should remain historical
WIP unless the user explicitly asks for an isolated experiment.

## Quality Gate Policy

The system should be strict about content quality:

- technical QA failures route to the responsible deterministic stage;
- content QA failures route to curator/source intervention;
- if VLM rejects all candidates, do not silently trust top text score;
- montage/collage must not be skipped by content QA forever;
- low confidence should become `review`, `await_material`, or
  `needs_generated`, not a hidden pass.

This is the difference between a demo generator and a reusable editing workflow.

### All-Candidate Rejection Policy

When VLM pre-pick rejects every stock candidate for a segment, the long-term
route policy should be:

| Segment/source condition | Route result |
|---|---|
| user/local material is expected or available | `await_material` |
| segment is local-specific, culturally specific, or stock ceiling is likely | `await_material` first; future `needs_generated(seg=[...])` if generated provider is configured |
| generated provider output already exists | switch to `source=generated` and rerun `--only-seg` |
| no better source is configured | `review` |

The current runtime may still fall back to top text-score stock candidates. That
is tolerated only as legacy behavior until QA-hardening tests are written. New
route skill work should not treat silent fallback as a desired contract.

## Portable Project Kit

The project should eventually be copyable as one folder containing:

```text
video-route-skill/
  README.md
  RUNBOOK.md
  route.py
  run_with_ollama.sh
  video_pipeline.py
  video_tools.py
  content_qa.py
  skills/
  design/
  docs/decisions/
  examples/
  tests/
```

Environment-specific code belongs in setup shims, not in skill contracts:

- WSL/Linux shell runner;
- Windows runner if needed;
- model runner abstraction;
- path/encoding checks;
- API key/env loading.

## Readiness Levels

### Current

- Full build works.
- `state.json` exists.
- `--only-seg` works.
- route can resume local material.
- QA catches at least obvious content failures.

### Route Skill Project Ready

- New agent can read one design + roadmap and run the smoke test.
- Material source contract is documented and used.
- Dashboard shows `next_action` and low segments.
- Failure states are explicit.
- Generated providers remain external but pluggable; ComfyUI is external and deprecated by default.

### High-Effect Video Ready

- montage/collage are QA-covered;
- effect layer has explicit contracts;
- beat/transition/style policy is separate from content sourcing;
- local/generated sources can fill stock gaps;
- dashboard supports human review and targeted replacement.
