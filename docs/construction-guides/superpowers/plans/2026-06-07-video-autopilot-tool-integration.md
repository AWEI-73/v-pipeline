# Video Autopilot Verification Tool Integration Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the P1 deterministic audit and keyframe-grid tool pack defined in `docs/video-autopilot-tool-integration-spec.md`.

**Architecture:** Implement each audit as a focused `video_pipeline_core` module with stable JSON output. Expose thin CLI commands through `video_tools.py`, index outputs in `artifact_manifest.json`, surface them in Node 11/12, and preserve existing behavior when tools are disabled.

**Tech Stack:** Python 3.10, unittest, pathlib/json, ffmpeg/ffprobe, optional configured VLM route.

---

## Chunk 1: Deterministic Audit Modules

### Task 1: Timeline Invariants

**Files:**
- Create: `video_pipeline_core/timeline_invariants.py`
- Create: `tests/test_timeline_invariants.py`

- [ ] Write failing tests for trace presence, invalid duration, overlap, and must-include coverage.
- [ ] Run `python -m unittest tests.test_timeline_invariants -v` and confirm failure.
- [ ] Implement pure audit functions and stable `timeline_invariants.json` writer.
- [ ] Run focused tests and `git diff --check`.
- [ ] Commit the focused change.

### Task 2: B-roll Audit

**Files:**
- Create: `video_pipeline_core/broll_audit.py`
- Create: `tests/test_broll_audit.py`

- [ ] Write failing tests for ratio, unique-source ratio, repeat ceiling, and parameterized policy.
- [ ] Confirm no author-specific keyword map or fixed creator preference is introduced.
- [ ] Implement pure audit functions and stable `broll_audit.json` writer.
- [ ] Run focused tests and commit.

### Task 3: Caption Audit

**Files:**
- Create: `video_pipeline_core/caption_audit.py`
- Create: `tests/test_caption_audit.py`

- [ ] Write failing tests for gaps, overlaps, excessive reading speed, and intended no-caption intervals.
- [ ] Write a regression test proving labels/name supers are not treated as subtitles.
- [ ] Implement parser/audit and stable `caption_audit.json` writer.
- [ ] Run focused tests and commit.

## Chunk 2: Visual Evidence

### Task 4: Keyframe Grid

**Files:**
- Create: `video_pipeline_core/keyframe_grid.py`
- Create: `tests/test_keyframe_grid.py`
- Modify: `video_pipeline_core/platform_tools.py` only if the existing ffmpeg resolver cannot be reused.

- [ ] Write tests for deterministic timestamp selection and grid metadata.
- [ ] Implement ffmpeg-backed grid generation with mechanical-only operation.
- [ ] Add a real short-video smoke fixture or generate one during the test.
- [ ] Verify the output image exists and is non-empty.
- [ ] Run focused tests and commit.

### Task 5: Visual Audit

**Files:**
- Create: `video_pipeline_core/visual_audit.py`
- Create: `tests/test_visual_audit.py`

- [ ] Write tests for mechanical-only evidence and optional model lineage.
- [ ] Implement `visual_audit.json` writer consuming keyframe-grid metadata.
- [ ] Reuse current model routing; do not hardcode Ollama availability.
- [ ] Run focused tests and commit.

## Chunk 3: CLI, Manifest, Node, and Route Integration

### Task 6: CLI Shims

**Files:**
- Modify: `video_tools.py`
- Modify or create a focused `video_pipeline_core/vt_*.py` facade only if consistent with current CLI patterns.
- Modify: relevant CLI tests.

- [ ] Add failing CLI dispatch tests for all five P1 commands.
- [ ] Add thin CLI handlers that call focused modules.
- [ ] Run CLI-focused tests and commit.

### Task 7: Manifest and Dashboard Integration

**Files:**
- Modify: `video_pipeline_core/contract_adapter.py`
- Modify: `video_pipeline_core/dashboard_state.py`
- Modify: `video_pipeline_core/node_registry.py`
- Modify: `tests/test_contract_adapter.py`
- Modify: `tests/test_dashboard_state.py`

- [ ] Write failing tests proving audit artifacts are indexed and displayed under Node 11/12.
- [ ] Add optional manifest keys without changing existing required-artifact behavior.
- [ ] Surface pass/warn/fail findings and evidence paths.
- [ ] Run focused tests and commit.

### Task 8: Runtime and Route Integration

**Files:**
- Modify: `video_pipeline_core/runtime_orchestrator.py`
- Modify: route/state modules only where current taxonomy requires it.
- Modify: `tests/test_runtime.py`

- [ ] Write failing tests for audit failures routing to the smallest affected node/skill.
- [ ] Ensure disabled audit tools preserve current runtime behavior.
- [ ] Ensure mechanical-only verification works without Ollama.
- [ ] Run focused tests and commit.

## Chunk 4: Verification and Documentation

### Task 9: Full Verification

- [ ] Run all new focused tests.
- [ ] Run `python -m unittest tests.test_dashboard_state tests.test_runtime -v`.
- [ ] Run `python -m unittest discover -s tests -p "test_*.py"`.
- [ ] Run `git diff --check`.
- [ ] Generate a real `keyframe_grid.jpg` from a Render Candidate.
- [ ] Inspect generated audit JSON and Runtime status.

### Task 10: Durable Documentation

**Files:**
- Modify: `docs/build-tool-runner-spec.md`
- Modify: `HANDOFF_CURRENT.md`
- Modify: `ROADMAP.md`
- Create or modify: `THIRD_PARTY_NOTICES.md` only if code was copied or substantially derived.

- [ ] Record implemented runner/artifact status.
- [ ] Record exact test count and real smoke evidence.
- [ ] Refresh Graphify only after implementation boundaries stabilize.
- [ ] Commit documentation and Graphify changes separately from implementation.

