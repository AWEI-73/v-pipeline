# Material Understanding Matrix MVP Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a bounded multi-material "eyes and ears" artifact that summarizes real visual/audio evidence before rough cut selection.

**Architecture:** Add a focused `material_understanding_matrix` core module and CLI. It consumes an existing `materials_db.json` or source folder, emits per-asset visual evidence refs, rough audio evidence, duplicate/final-master flags, and role hints without claiming semantic truth. Existing Material Wall and Material Map remain the owning gates; this matrix is a decision aid and handoff artifact.

**Tech Stack:** Python stdlib, existing ffmpeg/ffprobe resolver, existing `material_wall`, `soundtrack_probe`, and unittest.

---

## Chunk 1: Matrix Core And CLI

### Task 1: Add Matrix Builder Contract

**Files:**
- Create: `video_pipeline_core/material_understanding_matrix.py`
- Create: `tools/material_understanding_matrix.py`
- Test: `tests/test_material_understanding_matrix.py`

- [ ] **Step 1: Write failing tests**

Create tests that build a small materials DB with:
- one video with fake frame extraction;
- one photo;
- one final/export-like video;
- one duplicate path/name hint.

Assert the output has:
- `artifact_role = "material_understanding_matrix"`;
- `assets[]` entries with `asset_id`, `source_path`, `media_type`, `visual_evidence`, `audio_evidence`, `risk_flags`, `role_hints`, and `next_review_action`;
- final/export-like asset gets `risk_flags` containing `looks_like_finished_export`;
- no asset is marked as accepted or need-covered.

- [ ] **Step 2: Run failing test**

Run:

```powershell
python -m unittest tests.test_material_understanding_matrix -v
```

Expected: fail because module/CLI does not exist.

- [ ] **Step 3: Implement minimal core**

Implement `build_material_understanding_matrix(materials_db, out_dir, max_assets=24, frame_budget=3, ...)`.

Rules:
- Use existing DB shape: `files[]` with `id`, `path`, `type`, `metadata.duration_sec`, `tags_from_path`, `vlm_caption`.
- For videos, extract up to `frame_budget` frames through injectable `frame_extractor`.
- For photos, use source path as visual evidence.
- Add rough role hints from folder/caption keywords only as hints, never truth.
- Add `risk_flags` for likely finished exports, duplicate-ish names, unsupported/missing paths.
- Write `material_understanding_matrix.json` and `material_understanding_contact_sheet.jpg` when possible.

- [ ] **Step 4: Add CLI**

CLI:

```powershell
python tools\material_understanding_matrix.py `
  --materials-db RUN_DIR\materials_db.json `
  --out-dir RUN_DIR `
  --max-assets 24 `
  --json
```

Output JSON should include `ok`, `matrix`, `asset_count`, and `next_action`.

- [ ] **Step 5: Verify tests pass**

Run:

```powershell
python -m unittest tests.test_material_understanding_matrix -v
python -m py_compile tools\material_understanding_matrix.py video_pipeline_core\material_understanding_matrix.py
```

## Chunk 2: Route Surface And Real Probe

### Task 2: Connect To Material Map Skill And Runbook

**Files:**
- Modify: `skills/material-map.md`
- Modify: `RUNBOOK.md`
- Modify: `docs/pipeline-decision-tree.md`

- [ ] **Step 1: Document when to use it**

Add `tools/material_understanding_matrix.py` after quick inventory and before wall verdict for multi-material runs.

Boundary language:
- It is observation, not final truth.
- It helps reviewer write `material_wall_review_verdict.json`.
- BUILD must still wait for wall/map review and rough cut gates.

- [ ] **Step 2: Run a bounded real-material probe**

Use:

```powershell
python tools\material_understanding_matrix.py `
  --materials-db RUN_DIR\materials_db.json `
  --out-dir RUN_DIR\material_understanding `
  --max-assets 24 `
  --json
```

Expected:
- matrix exists;
- contact sheet exists;
- at least video/photo/final-export flags appear if present.

- [ ] **Step 3: Review output**

Write a short `material_understanding_review.md` beside the run output:
- what it can infer;
- what still requires VLM/human review;
- whether it improves material-wall verdict writing.

- [ ] **Step 4: Run focused regression**

Run:

```powershell
python -m unittest tests.test_material_understanding_matrix tests.test_material_first_landing_case tests.test_pipeline_home -v
```

- [ ] **Step 5: Commit**

Commit only implementation/docs/tests, not run outputs.
