# Video Route Skill Project

Portable agent workflow for producing narrated videos through explicit skill
contracts, deterministic tools, `state.json`, and a route dispatcher.

This repository is designed to be usable by Hermes and by other agent platforms
that can read Markdown instructions, run shell commands, and inspect JSON
artifacts. The core flow is platform-neutral; local runners and setup details
belong in the runbook.

## What This Is

```text
brief / interactive spec
-> segment_contract.json
-> build_profile.json + model_routes.json
-> generated_mv_script.json / assembly_plan.json / timeline_build.json
-> final.mp4
-> artifact_manifest.json + state.json + verify artifacts
-> route.py + dashboard/review
```

The project coordinates video creation through three aligned surfaces:

- **Tools:** root CLI entrypoints plus `video_pipeline_core/*` implementation modules
- **Skills:** `skills/*.md` role contracts for writer, director, curator, editor,
  effects, audio, subtitle, verify, route, dashboard, and related roles
- **Route:** `route.py` reads `state.json.next_action` and decides the next step

Core library modules live in `video_pipeline_core/`; root-level Python files are
kept for CLI/runtime entrypoints and small debug helpers.

The current system can produce narrative/MV-style videos, verify technical and
content quality, rerender only selected segments, and resume after user-provided
material arrives.

## Skills by Layer (SPEC / BUILD / VERIFY)

The layers above describe the *implementation stack* (Tools / Skills / Route).
Orthogonally, every skill plays a *functional* role in one of three layers, with
`state.json` + `decision_log.json` as the audit spine threading through all three.
Route is **not** a member of any functional layer — it is the control loop sitting
on top, reading the VERIFY verdict (via `state.json`) to decide which layer to
re-enter and on which segments.

| Layer | Does | Skills | Output |
|---|---|---|---|
| **SPEC** | define what to make | `video-workflow`, `director`, `writer`, `spec-contract`, `gap-analyzer`, `shooting-brief` | `brief.json`, `segment_contract.json`, `fallback_route.json` |
| **BUILD** | make it | `curator`, `editor`, `effects-director`, `audio-director`, `subtitle-director`, `generative-director` + runtime tools | `build_profile.json`, `generated_mv_script.json`, `assembly_plan.json`, `timeline_build.json`, `final.mp4` |
| **VERIFY** | check it | `verify`, `editor_review`, package-internal `video_pipeline_core.content_qa`, `precompose_gate` | `editor_review.json`, `qa_report.json`, `content_qa.json`, `verify_result.json`, `state.json` |
| **Control / view plane** | move & inspect work across layers | `route` (machine reader: dispatch on `next_action`), `dashboard` (human reader: visualize the same state) | — |

```text
SPEC ──► BUILD ──► VERIFY ──► (state.json / decision_log.json)
 ▲          ▲                          │
 └──────────┴── route reads next_action, decides which layer to re-run ◄┘
```

See `skills/route.md` for the full boundary write-up (including the known gap:
route currently re-enters only BUILD or escalates to human — it does not yet
auto-route back to SPEC for writer/director rewrites).

## What This Is Not

- Not a ComfyUI repository.
- Not a high-end motion graphics studio yet.
- Not tied to one agent platform.
- Not a collection of unrelated helper scripts.

ComfyUI or other generators should live in a separate project and enter this
pipeline only as `source=generated` material files plus metadata.

## Start Here

Read these files in order:

1. `HANDOFF_CURRENT.md` - clean current alignment snapshot and resume anchor
2. `roadmap.md` - current state and next project phases
3. `design/video-route-skill-project.md` - architecture, boundaries, material source contract
4. `docs/dashboard-node-skill-output-spec.md` - dashboard/node/skill/output contract
5. `skills/route.md` - route dispatcher contract
6. `RUNBOOK.md` - local execution details

## Requirements

Runtime dependencies used by the current WSL setup:

- Python 3
- ffmpeg / ffprobe
- edge-tts
- Ollama
- `qwen3-vl:4b-instruct`
- Pexels/Pixabay API keys for stock sourcing

Environment variables are loaded from `.env` and, in the current local setup,
from the `video_director` Hermes profile `.env`. Do not commit secrets.

## Canonical Entrypoints

Create an external project workspace:

```bash
python3 video_tools.py project-init "ETF Demo"
python3 video_tools.py project-new-run --label baseline
```

By default, project inputs and run outputs live outside this repository under
`<project-root>/<project>/` (`VIDEO_PIPELINE_PROJECT_ROOT` can override the
default). The repo only keeps `.project/active.json` as a local relative pointer
to the active project/run. This keeps the source tree and Graphify corpus focused
on engine, skills, contracts, and review documents.

Within a run, keep outputs detectable: candidate material goes to
`materials/raw/`, approved edit material to `materials/selected/`, generated
fallback material to `materials/generated/`. SPEC/BUILD/VERIFY placement uses
`spec/`, `build/`, and `verify/`; node-specific subfolders under `nodes/` should
be added only after the node contract is confirmed. Root-level run artifacts
remain the route/dashboard surface (`state.json`, `artifact_manifest.json`,
`final.mp4`, etc.).

Validate a script:

```bash
python3 video_tools.py validate examples/story_mv_smoke_script.json
```

Adapt a canonical segment contract into the legacy runtime payload:

```bash
python3 video_tools.py contract-adapt examples/segment_contract_graduation_mv.json \
  --categories examples/material_categories.json \
  --out /tmp/video_route_story_mv/generated_mv_script.json
```

Run the canonical MV chain through the adapter:

```bash
python3 video_tools.py contract-run examples/segment_contract_graduation_mv.json \
  --categories examples/material_categories.json \
  --material-db /path/to/materials_db.json \
  --music /path/to/music.mp3 \
  --out /tmp/video_route_story_mv/final.mp4
```

Run a full build:

```bash
bash run_with_ollama.sh examples/story_mv_smoke_script.json \
  --out /tmp/video_route_story_mv --verbose
```

Run the route dispatcher:

```bash
python3 route.py examples/story_mv_smoke_script.json \
  --out /tmp/video_route_story_mv \
  --material-dir student_uploads \
  --verbose
```

Rerender selected segments:

```bash
bash run_with_ollama.sh examples/story_mv_smoke_script.json \
  --out /tmp/video_route_story_mv \
  --only-seg 6 \
  --verbose
```

## Route States

`state.json` is the execution truth source. `route.py` reads `next_action`:

| `next_action` | Meaning |
|---|---|
| `null` | final video is ready |
| `await_material` | wait for `seg{n}_user.*` in `--material-dir`, then rerender that segment as local material |
| `retry:curator(seg=[...])` | automatic retry is exhausted; human/source intervention required |
| `needs_generated(seg=[...])` | future generated provider hook |
| `review` | human review required |

## Material Sources

All material providers should converge on this model:

```json
{
  "segment": 6,
  "source": "stock | local | generated",
  "provider": "pexels | pixabay | user_upload | antigravity | assistant_imagegen | codex_imagegen | gemini_veo | manual",
  "file": "/absolute/path/to/material",
  "status": "candidate | selected | rejected | needs_review",
  "score": 0.0,
  "visual_desc": "Chinese visual description used for QA",
  "metadata": {}
}
```

Current source roles:

- `stock`: Pexels/Pixabay generic B-roll
- `local`: user/student uploaded real material
- `generated`: external/generated provider output, preferably Antigravity or assistant/Codex image generation

## Generated Provider Boundary

Generated providers are intentionally outside this core project. Another
agent/project may produce generated material, but this route skill project only
accepts its output:

```text
materials/generated/seg6.jpg
materials/generated/seg6.json
```

ComfyUI is deprecated/disabled by default because current output quality is below
Antigravity and assistant/Codex image generation. Do not mix ComfyUI installers,
clients, workflow JSON, or model files into the route skill core unless the user
explicitly asks for an isolated experiment.

## Smoke Test

The portable story/MV smoke script is:

```text
examples/story_mv_smoke_script.json
```

Minimum verification:

```bash
python3 video_tools.py validate examples/story_mv_smoke_script.json
python3 -m unittest tests.test_content_qa tests.test_video_pipeline_state tests.test_video_tools_state -v
```

Full verification on a configured machine:

```bash
bash run_with_ollama.sh examples/story_mv_smoke_script.json \
  --out /tmp/video_route_story_mv --verbose
```

The run may fail content QA if stock material is poor. That is useful signal:
inspect `/tmp/video_route_story_mv/state.json` and route from there.

## Current Known Gaps

- montage/collage content QA needs representative-frame coverage;
- all-candidate VLM rejection should route explicitly instead of trusting top
  text-score fallback;
- dashboard should read route state directly and surface `next_action`;
- high-end motion graphics require a later effect layer contract.
