# M4 Verify Evidence and Replay Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce four-layer visual VERIFY evidence and a deterministic same-case replay report that exposes whether the material-aware pipeline actually improved the edit.

**Architecture:** Extend the existing keyframe-grid mechanism with explicit timestamp sampling, then add a focused `verify_evidence` module that generates overview, per-chapter, critical-segment, and rhythm-strip artifacts. Add a separate `replay_acceptance` module that aggregates timeline and existing audit evidence without inventing aesthetic verdicts.

**Tech Stack:** Python standard library, ffmpeg/ffprobe, unittest, existing material/timeline/audit JSON contracts.

---

### Task 1: Four-Layer Evidence Bundle

**Files:**
- Modify: `video_pipeline_core/keyframe_grid.py`
- Create: `video_pipeline_core/verify_evidence.py`
- Create: `tests/test_verify_evidence.py`

- [ ] Write failing tests for chapter ranges, critical range selection, explicit timestamp grids, and rhythm-strip SVG metadata.
- [ ] Run tests and confirm failures are caused by missing M4 APIs.
- [ ] Implement minimal evidence planning and artifact generation.
- [ ] Run focused tests.

### Task 2: Replay Acceptance Metrics

**Files:**
- Create: `video_pipeline_core/replay_acceptance.py`
- Create: `tests/test_replay_acceptance.py`
- Modify: `video_pipeline_core/edit_artifacts.py`
- Modify: `tests/test_edit_artifacts.py`

- [ ] Write failing tests for short-shot ratio, action-phase coverage, sound-bite/jump-cut applicability, gate bypass detection, and verdict lineage.
- [ ] Write a failing test proving timeline build preserves M3 evidence fields.
- [ ] Run tests and confirm expected failures.
- [ ] Implement deterministic replay aggregation and timeline evidence passthrough.
- [ ] Run focused tests.

### Task 3: CLI and Artifact Wiring

**Files:**
- Modify: `video_tools.py`
- Modify: `tests/test_video_tools_audits.py`

- [ ] Write failing CLI tests for `verify-evidence` and `replay-acceptance`.
- [ ] Run tests and confirm commands are missing.
- [ ] Add command handlers and parser entries.
- [ ] Run focused CLI tests.

### Task 4: Same-Case Evidence and Documentation

**Files:**
- Modify: `roadmap.md`
- Modify: `skills/spec-contract.md`
- Create: `docs/decisions/2026-06-13-m4-material-aware-replay.md`

- [ ] Generate four-layer evidence from the available 2026-06-13 student edit and available pipeline replay artifacts.
- [ ] Record good and bad results, including any acceptance checks that remain unproven.
- [ ] Run focused and full regression suites, `py_compile`, and `git diff --check`.
- [ ] Update roadmap/spec with verified status only.
