# 67th Graduation Film Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce and verify an 11-13 minute story-driven, high-energy graduation film from the organized 67th-class material.

**Architecture:** Create an external VIDEO PIPELINE project and retain the source repository as the engine. Build a canonical brief and segment contract, ingest and map local material, generate narration and subtitles, run the canonical ffmpeg build, then verify and revise from generated audit artifacts.

**Tech Stack:** VIDEO PIPELINE, Python, ffmpeg/ffprobe, edge-tts, Ollama VLM, JSON contracts.

---

## Chunk 1: SPEC And Material Intake

### Task 1: Create the project workspace

**Files:**
- Create: `C:\Users\user\Desktop\video_project\67th-graduation-film\`

- [ ] Run `python video_tools.py project-init "67th Graduation Film"`.
- [ ] Run `python video_tools.py project-new-run --label story-mv`.
- [ ] Confirm the active project and run paths.

### Task 2: Build the material database

**Files:**
- Create: active project `input/materials_db.json`
- Create: active run `material_coverage_map.json`

- [ ] Ingest all supported source media without modifying originals.
- [ ] Generate technical metadata and visual captions.
- [ ] Map materials to the dramatic chapters in the approved design.
- [ ] Record missing-course bridges that must come from the existing 67th film.

### Task 3: Write the canonical SPEC

**Files:**
- Create: active project `input/brief.json`
- Create: active project `input/segment_contract.json`
- Create: active project `input/material_categories.json`

- [ ] Encode target duration, audience, tone, must-include material, and hybrid sourcing.
- [ ] Write story narration for the opening, promise, future-choice, gratitude, and ending chapters.
- [ ] Define MV segments for fundamentals, field practice, and life outside training.
- [ ] Run `python video_tools.py spec-review ...`.
- [ ] Resolve all blocking SPEC findings.

## Chunk 2: BUILD

### Task 4: Prepare narration and music

**Files:**
- Create: active run narration audio and subtitle artifacts.
- Create: active run music structure and audio plan artifacts.

- [ ] Generate Taiwan Mandarin male narration with edge-tts.
- [ ] Generate Traditional Chinese subtitle timing.
- [ ] Select or generate music beds with contrasting chapter energy.
- [ ] Validate narration readability and audio plan.

### Task 5: Build the editorial timeline

**Files:**
- Create: active run `assembly_plan.json`
- Create: active run `timeline_build.json`
- Create: active run `editor_review.json`

- [ ] Run the contract adapter and dry build.
- [ ] Review material assignments and pacing.
- [ ] Ensure course sections use MV pacing and story sections preserve narration space.
- [ ] Resolve timeline and editorial-review blockers.

### Task 6: Render the film

**Files:**
- Create: active run `final.mp4`
- Create: active run `artifact_manifest.json`

- [ ] Run the canonical ffmpeg render with subtitles, narration, music, and location sound.
- [ ] Confirm render completion and artifact manifest entries.
- [ ] Rerender failed or weak segments only when possible.

## Chunk 3: VERIFY And Revision

### Task 7: Run mechanical and editorial verification

**Files:**
- Create: active run `timeline_invariants.json`
- Create: active run `caption_audit.json`
- Create: active run `keyframe_grid.jpg`
- Create: active run `visual_audit.json`
- Create: active run `verify_result.json`

- [ ] Verify duration is at least 600 seconds.
- [ ] Verify video and audio streams are valid.
- [ ] Run timeline, caption, keyframe-grid, and visual audits.
- [ ] Inspect the keyframe grid for pacing, repetition, and black frames.
- [ ] Confirm opening and ending narration and MV-based course chapters.

### Task 8: Revise and deliver

**Files:**
- Modify: active run artifacts as directed by verification.

- [ ] Fix blocking verification findings.
- [ ] Re-render affected segments or the full film.
- [ ] Re-run all acceptance checks.
- [ ] Report the final video path, duration, verification result, and remaining creative caveats.
