# Subtitle Polish Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:test-driven-development to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Chinese subtitles consistently readable through deterministic text cleanup, line wrapping, and resolution-aware bottom-center ASS styling.

**Architecture:** Add a focused pure-Python subtitle presentation module. Both ffmpeg subtitle-burning entrypoints consume its polished SRT output and shared ASS style, while `editorial_design.subtitle_strategy` records the provider-neutral defaults.

**Tech Stack:** Python standard library, unittest, ffmpeg ASS `force_style`

---

## Chunk 1: Pure Subtitle Presentation Policy

### Task 1: Text Cleanup And Wrapping

**Files:**
- Create: `video_pipeline_core/subtitle_presentation.py`
- Create: `tests/test_subtitle_presentation.py`

- [ ] Write failing tests for punctuation-to-fullwidth-space cleanup, 16-character wrapping, and the two-line ceiling.
- [ ] Run `python -m unittest tests.test_subtitle_presentation -v` and confirm failure because the module does not exist.
- [ ] Implement minimal pure functions.
- [ ] Re-run focused tests.

### Task 2: Responsive ASS Style

**Files:**
- Modify: `video_pipeline_core/subtitle_presentation.py`
- Modify: `tests/test_subtitle_presentation.py`

- [ ] Write failing tests for bottom-center alignment and resolution-scaled font/margin.
- [ ] Implement minimal ASS style generation.
- [ ] Re-run focused tests.

## Chunk 2: Pipeline Integration

### Task 3: Record Provider-Neutral Defaults

**Files:**
- Modify: `video_pipeline_core/editorial_design.py`
- Modify: `tests/test_editorial_design.py`

- [ ] Write failing assertions for subtitle presentation defaults.
- [ ] Add defaults to `subtitle_strategy`.
- [ ] Re-run editorial design tests.

### Task 4: Share Policy Across Burn Entrypoints

**Files:**
- Modify: `video_tools.py`
- Modify: `video_pipeline_core/vt_editor.py`
- Test: `tests/test_subtitle_presentation.py`

- [ ] Write failing integration-level tests for polished SRT preparation and shared style.
- [ ] Replace duplicated hard-coded ASS style strings with the shared module.
- [ ] Run focused tests.
- [ ] Run `python -m unittest discover -s tests`.

