# Graduation Recap Run Setup Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Set up a new Hermes run folder for a graduation/training recap video, then complete Stage 0 artifacts and a source-material inventory without touching pipeline source code or starting any render/build work.

**Architecture:** Treat the run folder as the unit of work and keep the repo source tree unchanged. First establish the project/run location, then inspect the source material folder and record what is available, and finally write the Stage 0 decision artifacts that capture the approved material-first, story-led route. The output should be a clean handoff point for later material-map and BUILD work.

**Tech Stack:** PowerShell, `video_tools.py`, Hermes run-folder layout, Markdown artifact docs, JSON artifacts

---

## Chunk 1: Run Folder and Stage 0 Skeleton

**Files:**
- Create: `docs/superpowers/plans/2026-06-27-graduation-recap-run.md`
- Create: external run folder under the project workspace root
- Create: `project_brief.json`
- Create: `video_intent.json`

- [ ] **Step 1: Confirm the active project/run naming**

```text
Pick a project/run name that matches the graduation recap scope and can be reused for later material-map and build artifacts.
```

- [ ] **Step 2: Create the external project and run folder**

Run: `python video_tools.py project-init "<project-name>"` then `python video_tools.py project-new-run --label "<run-label>"`

Expected: a new run folder exists outside the repo tree, with a readable run manifest and no source-code changes in the pipeline repo.

- [ ] **Step 3: Write the initial project brief**

```json
{
  "video_type": "graduation_event",
  "style": "story-led recap with a music-driven finish",
  "target_length": "3-5 minutes",
  "audience": ["students", "instructors", "family", "coworkers"],
  "must_include": ["training and interaction", "closing group photo"],
  "voiceover": "short opening-middle narration only",
  "text_layer": "light chapter cards and key labels"
}
```

- [ ] **Step 4: Derive the Stage 0 intent artifact**

Run: `python video_tools.py video-intent-plan project_brief.json --out video_intent.json`

Expected: `video_intent.json` records `input_state=material_available`, `entry_path=material-first`, `handoff_to=material_map_lifecycle`, and no blocking follow-up questions.

## Chunk 2: Material Inventory and Handoff Notes

**Files:**
- Read: source material folder under `C:\Users\user\Downloads\微電影素材\_整理後`
- Read: `_整理報告.md`
- Read: `_腳本素材對照表.md`
- Create: `material_inventory.md`
- Create: `interaction_log.md`

- [ ] **Step 1: Inventory the source folder**

Run: `Get-ChildItem -LiteralPath "<source-folder>" -Recurse | ...`

Expected: a concise inventory that groups folders and notable media, with special attention to training, interaction, group photo, and any speaker/commencement footage.

- [ ] **Step 2: Read the companion notes**

Expected: the inventory reflects the existing organizer notes instead of guessing from file names alone.

- [ ] **Step 3: Write the human-readable inventory summary**

Expected: `material_inventory.md` lists likely story beats, obvious gaps, and any items that need confirmation.

- [ ] **Step 4: Record the interaction log**

Expected: `interaction_log.md` captures the approved direction, must-have beats, and unresolved questions so the next stage can continue without re-asking.

## Chunk 3: Validation and Stop Point

**Files:**
- Create: `run_layout_validation.json` if needed
- Create: `pipeline_home.json` or equivalent readout if needed

- [ ] **Step 1: Verify the run is readable**

Run: `python tools/pipeline_home.py --run <run-dir> --json`

Expected: the run surfaces as a material-first setup with no render/build work started.

- [ ] **Step 2: Confirm no render artifacts were produced**

Expected: no `final.mp4`, no timeline build, and no build/verify artifacts created at this stage.

- [ ] **Step 3: Stop at the handoff boundary**

Expected: the run is ready for material-map work, not BUILD or render.

