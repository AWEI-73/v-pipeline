# Video Route Skill Project Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Consolidate the current video pipeline into a portable route skill project usable by Hermes and other shell-capable agent platforms.

**Architecture:** Keep deterministic video production in `video_pipeline.py`/`video_tools.py`, keep orchestration in `route.py`, keep cross-agent contracts in `skills/*.md` and `design/video-route-skill-project.md`, and use `state.json` as the dashboard/review truth source.

**Tech Stack:** Python 3, ffmpeg/ffprobe, Ollama qwen3-vl, edge-tts, JSON artifacts, Markdown skill contracts.

---

## Chunk 1: Project Kit Boundaries

### Task 1: Add a Portable Project README

**Files:**
- Create: `README.md` or `docs/video-route-skill-kit.md`
- Reference: `design/video-route-skill-project.md`
- Reference: `RUNBOOK.md`

- [x] Write the project purpose: portable video route skill flow for agent platforms.
- [x] List required runtime commands and environment variables.
- [x] List canonical entrypoints: `run_with_ollama.sh`, `route.py`, `video_pipeline.py`, dashboard.
- [x] Verify a new agent can find the smoke-test command from the README.

### Task 2: Freeze the Copyable Folder Contract

**Files:**
- Modify: `design/video-route-skill-project.md`
- Modify: `roadmap.md`

- [x] Define the final copyable folder tree.
- [x] Mark ComfyUI client/workflow/model files as external provider artifacts.
- [x] Add `.gitignore` coverage for provider-side WIP that should not enter core.
- [x] Verify `git status --ignored` shows ComfyUI WIP as ignored.

## Chunk 2: Material Source Contract

### Task 3: Document `stock | local | generated`

**Files:**
- Modify: `design/video-route-skill-project.md`
- Modify: `skills/curator.md`
- Modify: `skills/route.md`

- [x] Define source fields: `source`, `provider`, `file`, `status`, `score`, `metadata`.
- [x] Define generated provider output as files plus metadata only.
- [x] State that route never owns ComfyUI installation or workflow execution.
- [x] Add examples for stock, local upload, and generated material.

### Task 4: Add State Next-Action Semantics

**Files:**
- Modify: `skills/route.md`
- Modify: `docs/decisions/2026-05-31-orchestration-state-json.md`
- Later code task: `video_pipeline.py`, `route.py`

- [x] Document `needs_generated(seg=[...])` as a future route state.
- [x] Define when all-candidate rejection becomes `review`, `await_material`, or `needs_generated`.
- [x] Keep current runtime behavior unchanged until tests are written.

## Chunk 3: QA Hardening

### Task 5: Cover Montage/Collage in Content QA

**Files:**
- Modify later: `content_qa.py`
- Modify later: `video_pipeline.py`
- Add tests later under project test suite.

- [x] Write a failing test showing montage/collage segments are included or sampled.
- [x] Implement representative-frame sampling for montage/collage.
- [x] Verify a story-MV run reports QA for those segments instead of `reason: montage`.

### Task 6: Stop Silent Top-Text Fallback Passing

**Files:**
- Modify later: `video_pipeline.py`
- Modify later: `route.py`

- [x] Write a failing test for all VLM candidates rejected.
- [x] Change state building so all-rejected material does not silently pass as normal stock.
- [x] Route to `review`, `await_material`, or future `needs_generated`.

## Chunk 4: Dashboard Integration

### Task 7: Make Dashboard Read Route State

**Files:**
- Modify later: dashboard HTML/state command location in `video_tools.py`
- Modify: `skills/dashboard.md`

- [x] Display `next_action`. (route banner, color-coded + copy-paste command)
- [x] Display low/unfixable segments. (segments table: status/score/fix_class→fix_target/block_reason)
- [x] Display source type per segment. (segments table `source` column)
- [~] Display candidate thumbnails and route command suggestions. (route commands done; candidate thumbnails deferred — state.json doesn't carry thumb paths yet)

## Verification Matrix

Run these before claiming the project kit is ready:

- [ ] `python3 video_tools.py validate <example-script>`
- [ ] 3-segment smoke full build
- [ ] 6-segment story MV full build
- [ ] local material replacement through `route.py --material-dir`
- [ ] stock failure produces explicit `state.next_action`
- [ ] `--only-seg` reuses unchanged segment renders
