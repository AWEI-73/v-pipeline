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
