# Hermes Video Pipeline v2 — RUNBOOK

## 2026-06-11 Windows Quick Start

```powershell
cd C:\Users\user\Desktop\video_pipeline

python video_tools.py project-init "My Video"
python video_tools.py project-new-run --label baseline
python runtime.py status
python runtime.py resume

python video_tools.py dashboard <run-directory> --out <run-directory>\dashboard_view.html

$env:PYTHONUTF8=1
python -m unittest discover -s tests
```

Current verified baseline: **541 tests OK**.

Supported build profiles include canonical ffmpeg, Node 14
`motion_graphics` with `ffmpeg_libass`, and optional `capcut_draft`.
Motion graphics writes timed ASS overlay assets. CapCut drafts contain editable
text and explicit BGM/audio tracks; GUI export remains a human/Computer-Use gate.

How to trigger every external API / model and run the pipeline reproducibly.
All commands are designed to run **directly on Windows native** (using PowerShell or CMD), with WSL (Ubuntu-24.04) supported as a secondary option.

## 0. One-time setup

```bash
cd ~/video_pipeline
cp .env.example .env          # then fill in keys (see §2)
```

| Dependency | Where | Check |
|---|---|---|
| ffmpeg / ffprobe | `~/.local/bin/ffmpeg` | `~/.local/bin/ffmpeg -version` |
| edge-tts (TTS) | python pkg + `~/.local/bin/edge-tts` | `python3 -c "import edge_tts"` |
| Ollama | `~/.local/ollama/bin/ollama` (+ lib in `~/.local/ollama/lib/ollama`) | see §3 |
| VLM models | `qwen3-vl:4b-instruct` (gate, QA, retry) | `~/.local/ollama/bin/ollama list` |

## 1. Run the full pipeline (E2E)

### Canonical contract run

Use this when the input is `segment_contract.json`:

```bash
cd ~/video_pipeline
python3 video_tools.py contract-adapt examples/segment_contract_graduation_mv.json \
  --categories examples/material_categories.json \
  --out /tmp/video_route_story_mv/generated_mv_script.json

python3 video_tools.py contract-run examples/segment_contract_graduation_mv.json \
  --categories examples/material_categories.json \
  --material-db /path/to/materials_db.json \
  --music /path/to/music.mp3 \
  --out /tmp/video_route_story_mv/final.mp4
```

`contract-run` writes `generated_mv_script.json`, `build_profile.json`,
`model_routes.json`, `generated_asset_requests.json`, edit artifacts,
`artifact_manifest.json`, and `state.json` beside the output.

### Project workspace

Keep this repository as engine/source. Create real project folders outside the
repo, then pass the active run directory to build commands:

```bash
cd ~/video_pipeline
python3 video_tools.py project-init "ETF Demo"
python3 video_tools.py project-new-run --label baseline
```

Default layout:

```text
<project-root>/<project>/
  input/materials/
  runs/<timestamp>-<label>/
    spec/
    build/
    verify/
    materials/
      raw/
      selected/
      generated/
      stock/
    nodes/
    thumbs/
    logs/
    brownfield/
```

The repo-local `.project/active.json` only records the active project/run
pointer as a repo-relative reference and is gitignored. Existing legacy outputs
in the repo are not moved by these commands.

Treat the run directory as the only output truth source. Put candidate material
in `materials/raw/`, copied/approved edit material in `materials/selected/`, and
generated fallback outputs in `materials/generated/`. Keep formal SPEC-layer
artifacts under `spec/`, BUILD-layer artifacts under `build/`, VERIFY artifacts
under `verify/`, and node-specific details under `nodes/` only after the node
contract is confirmed. Root-level files such as
`state.json`, `artifact_manifest.json`, `final.mp4`, `assembly_plan.json`, and
`timeline_build.json` remain at the run root for dashboard/route compatibility.
New runs include `run_layout.json`, which is the machine-readable guide for
folder roles, canonical artifacts, Workbench draft artifacts, and derived cache
directories. Treat it as navigation metadata only; it does not override
`segment_contract.json`, material maps, or gate artifacts.

Validate a run's layout before handing it to another agent or frontend shell:

```powershell
python video_tools.py run-layout-validate C:\path\to\project\runs\20260618-demo --out C:\path\to\project\runs\20260618-demo\run_layout_validation.json
```

The validator fails closed on missing/malformed `run_layout.json`, unsafe
relative paths, duplicate artifact ownership, missing declared folders, and
cache paths that are files instead of directories.

Inspect the canonical command and workflow surfaces:

```powershell
python video_tools.py commands-manifest --out C:\path\to\run\video_tools_commands.json
python video_tools.py workflow-manifest --out C:\path\to\run\video_tools_workflows.json
```

`commands-manifest` classifies every `video_tools.py` command. `workflow-manifest`
lists the bounded Agent workflows for run setup, material-map lifecycle,
canonical build, and Workbench draft rerender.

Use bounded test tiers before full regression:

```powershell
python video_tools.py test-tiers --out C:\path\to\run\test_tiers.json
python video_tools.py test-tiers --tier backend-smoke --dry-run
python video_tools.py test-tiers --tier workbench
python video_tools.py test-tiers --tier full
```

`test-tiers` defines the standard focused sets (`backend-smoke`, `workbench`,
`material-map`, `render-e2e`, `full`). Use the smallest relevant tier first,
then run `full` before claiming cross-cutting backend changes complete.

Validate Workbench draft handoff before an Agent consumes human edits:

```powershell
python video_tools.py workbench-handoff-validate C:\path\to\run --out C:\path\to\run\workbench_handoff_validation.json
```

This checks that `workbench_handoff.json` references only Workbench draft
artifacts, that referenced files exist, and that their recorded size/hash still
match the files on disk.

Render a non-canonical preview candidate from a validated Workbench handoff:

```powershell
python video_tools.py workbench-draft-rerender C:\path\to\run --out workbench_rerender.mp4
```

This writes `workbench_rerender.mp4` and `workbench_rerender_report.json` only.
It refuses invalid handoffs and still refuses protected canonical outputs such
as `final.mp4`.

**Always use the wrapper** — it boots Ollama, warms the model, runs the pipeline,
and kills Ollama in the same shell session (so WSL idle won't orphan it):

```bash
cd ~/video_pipeline
bash run_with_ollama.sh nightmarket/script.json --out nightmarket_e2e --verbose
```

Exit 0 = `qa_pass:true`. Outputs land in `--out` dir: `final.mp4`, `qa_report.json`,
`decision_log.json`, `content_qa.json`, `picks.json`, `precompose_gate.json`.

Useful flags (passed straight to `video_pipeline.py`):
`--no-retry` · `--max-retries N` · `--no-strict` (disable D1 gate) ·
`--no-vlm-gate` · `--vlm-model` · `--vlm-model-retry` · `--content-qa-weight` · `--bgm <mp3>`.

> Running long jobs from a one-shot `wsl …` call will be killed when the call
> returns. Launch via a persistent shell / background runner instead.

## 2. APIs — Pexels & Pixabay

- Keys are read from the environment; `video_pipeline.py` auto-loads `~/video_pipeline/.env`
  (then the `video_director` profile `.env`) via a tiny loader. **No keys are hardcoded.**
- `video_tools.py pexels-search` **requires** `PEXELS_API_KEY` in its env (dies otherwise);
  the pipeline exports it to subprocesses automatically.
- Standalone search test:
  ```bash
  set -a; . .env; set +a
  python3 video_tools.py pexels-search "night market neon" --type video --limit 3
  ```

## 3. Model — Ollama / qwen3-vl

- `run_with_ollama.sh` does: `ollama serve` → wait for `/api/tags` → warm up
  `qwen3-vl:4b-instruct` → run pipeline → kill server.
- Endpoint: `http://localhost:11434` (override with `OLLAMA_URL`). Called via
  `POST {OLLAMA_URL}/api/generate` with base64 images.
- Model used: **qwen3-vl:4b-instruct** for prepick gate, content_qa, and retry re-pick.
- Manual start (debug):
  ```bash
  export LD_LIBRARY_PATH=$HOME/.local/ollama/lib/ollama:$LD_LIBRARY_PATH
  $HOME/.local/ollama/bin/ollama serve &
  curl -s http://localhost:11434/api/tags
  ```

## 4. Script validation (before a run)

```bash
python3 video_tools.py validate nightmarket/script.json
```
Warns on Chinese `search_query` (D2 — use English visual concept, put intent in
`query_zh`), short/duplicate queries, subtitle reading speed, etc.

## 5. Regression tests

```powershell
cd C:\Users\user\Desktop\video_pipeline
$env:PYTHONUTF8=1; python -m unittest discover -s tests -v   # 541 expected
```

## 6. Known issues / troubleshooting

- **Retry attempts log `error:HTTPError` on the VLM gate.** Current policy is
  4b-only (`qwen3-vl:4b-instruct`) for gate, QA, and retry. `_ollama_vlm_yn`
  retries with backoff; persistent failures usually mean Ollama/model startup,
  endpoint, or memory pressure rather than a missing 8b model.
- **Per-run artifacts under `nightmarket/` are gitignored** (audio/materials/
  thumbs/final.mp4/qa_report…); only `script.json` + `decision_log.example.json`
  are tracked. Use a separate `--out` dir for experiments.
- **Secrets in git history:** keys were previously hardcoded in `video_pipeline.py`
  and remain in past commits. Rotating the Pexels/Pixabay keys (or rewriting
  history) is required before any public push.

## 7. Native Preview Workbench (human fine-tuning line)

The workbench is a **human fine-tuning surface** — review material, watch how the
cut plays, and make small adjustments (clip duration / source window / order).
It is *not* an editor, not Remotion, not a renderer, and it never writes canonical
artifacts.

```powershell
# open the workbench against a built run
python tools\workbench_server.py --artifact-root <run-dir> --port 8770
#   -> http://localhost:8770/workbench
```

The Review Dashboard links to this same surface. Start it when you want a
read-only project overview first, then open the Workbench for review edits:

```powershell
python tools\dashboard_server.py --root <run-dir> --port 8765
#   -> dashboard exposes the Workbench URL/command in its artifact metadata
```

Buttons: **Save patch → server** (writes the draft artifacts), **Sync → contract**
(draft contract patch; fail-closed on out-of-scene windows), **Export (ffmpeg)**
(optional `workbench_export.mp4` via canonical render; never `final.mp4`).

Timeline interactions currently supported:

- drag the left / right edge handles on a clip to trim duration;
- edit duration / source window in the Inspector;
- move clips left / right;
- select or drag a material asset onto a timeline clip to replace that clip
  (`replace_clip` draft op; Python re-resolves the asset from
  `project_material_map.json`);
- add subtitle, audio-cue, and effect-intent markers as draft patch layers;
- scrub and preview material composition with proxy video, subtitles, BGM, and
  intent markers.

### What an Agent reads to grasp the current state

After a human fine-tunes, the Agent's entry points to understand "what the film
looks like now" are the draft artifacts below. Read these instead of guessing
from screenshots, and never treat them as canonical delivery artifacts:

- **`patched_draft_timeline.json`** — the current human-adjusted timeline draft.
- **`workbench_review_report.json` / `workbench_review_report.md`** — the concise
  summary of what changed, generated from draft patch layers for Agent review.
- **`workbench_contract_patch.json`** — the human edits expressed as a draft of
  intent/diagnostics against the pipeline contract (which clips changed duration
  / source window / order, mapped to segments; cross-segment moves flagged
  `unsupported_for_contract_sync`).
- **`workbench_handoff.json`** — the layer index and edit counts written by
  unified save; use it as the first file to inspect when multiple patch layers
  exist.
- **`subtitle_patch.json` / `audio_cue_patch.json` / `effect_patch.json`** —
  optional layer patches. They are intent data for the Agent/BUILD path, not
  canonical subtitles, audio, or rendered effects.

Generate the review report from an artifact root:

```powershell
python tools\workbench_review_report.py --artifact-root <run-dir>
```

Workbench server endpoint:

```text
POST /api/workbench/review-report
```

Material organization policy:

- `project_material_map.json` and per-asset maps are the source of truth.
- Physical folders are convenience projections only.
- Do not move/delete original source files during normal Workbench or Dashboard
  operation.
- See `docs/material-organization-policy.md`.

### Boundaries (do not cross from the workbench)

- **Official delivery still runs the Agent / FFmpeg build.** The drafts feed the
  build; the workbench never produces the canonical film.
- **No auto write-back to canonical.** `timeline.json`, `segment_contract.json`,
  `project_material_map.json`, `material_needs.json`, `final.mp4` are write-blocked.
  Folding a draft back into the SPEC is a deliberate human/Agent decision.
- **Intent-level re-cut, effects, and material replacement are out of scope here**
  — they belong to the later **Node 14** path / a future **`replace_clip`**
  increment, not the fine-tuning workbench.

With this documented, the Workbench fine-tuning line (NPE1–NPE3) is converged.
Next functional increment, when opened, is `replace_clip` / material swap
("drag material from the review panel onto the timeline").
