# Editorial Soul Layer + Material Treatment Grammar (2026-06-08)

## Context

The converged pipeline (SPEC → render → verify) produced correct-but-lifeless
videos: material selection was coarse and uncoupled from content. The engine knew a
segment "used a photo" but not why or how — it fell back to one rule (`1 photo = 1
still`), so photos either held too long or "just kept jumping" with no motivation.
Clip selection was bolted only to subtitles. A soulful film needs (a) a single
narrative center every shot serves, and (b) material treatment driven by what each
segment is actually about.

This session also hardened the convergence baseline: a stock-first generic E2E
fixture (`stock_story_e2e`) was driven to a green 92.5 PASS, surfacing several real
bugs along the way (logged in Verification below).

## Decision

Add a three-tier front-of-pipeline stack, each layer compiling the one above into
something executable. Each respects the roadmap non-goals (no new render backend, no
forced cuts, honesty guard intact, no provider choices in SPEC).

```text
WHY        docs/narrative-blueprint-spec.md            prose thesis + ordered beats
HOW-struct docs/editing-intent-sequence-grammar-spec.md (Codex) cut/hold reasons
HOW-matl   docs/material-treatment-grammar-spec.md      content -> treatment -> count -> lanes
```

### 1. Narrative blueprint gate (WHY) — wired live

`blueprint.json` carries a `thesis` + ordered `beats[]` (stable ids). Each
`segment.core.blueprint_ref` names the beat(s) it serves. A **two-way trace gate**
(`blueprint.beat_coverage`): every ref must resolve to a real beat (else
`invalid_ref`), and every beat must be realized by ≥1 segment (else `dropped_beat`,
BLOCKING). `runtime_orchestrator` runs the gate before render (inert when no
`blueprint.json`), so a run that lost a promised story beat cannot complete. CLI:
`video_tools.py blueprint-coverage` (exit 1 on dropped/invalid). This is the
roadmap's long-named-but-unbuilt narrative spine.

### 2. Material treatment grammar (HOW-material) — wired Node 9 + Node 11

A segment's `editing_intent.content_pattern` (emotional / establishing /
enumeration / process / bridge / action / testimony) resolves a `treatment`
(single_hold / photo_stack_beat / quick_cut_bridge / stepped_sequence /
video_primary / collage / real_material_only), which derives `n_required` and
co-varies the four lanes (photo/video, subtitle, music). Wiring is **opt-in**: only
segments that declare a content_pattern/treatment are affected, so existing runs are
untouched.

- `material_treatment.resolve_treatment` (resolver) + `treatment_audit.audit_treatment`
  (Node 11 fit/label/beat checks) authored as pure modules.
- Adapter passes `editing_intent`/`material_treatment`/`section_role` to BUILD.
- `edit_artifacts.build_assembly_plan` resolves a treatment per opted-in segment;
  `write_edit_artifacts` emits `treatment_audit.json`.
- `dashboard_state` + runtime `_AUDIT_NODE` surface/route treatment_audit (node 11),
  reusing the P1 inert-when-absent pattern.
- Honesty guard preserved: testimony/proof/identity → `real_material_only`
  (never stock/generated).

### 3. Photo-stack renderer — implemented + proven end-to-end

An enumeration segment now actually renders as N labeled stills on the beat, not one
long clip:

- `vt_stock.fetch_stock_photo` (Pexels photo).
- `mv_cut`: `_stack_items` (opt-in detector), `allocate_segments` override
  (n_clips = #items; each still ≈ one beat via `stack_shot_sec` derived from tempo —
  beat-fast, not the full segment budget), `_plan_stock_stack_segment` (per-item
  Pexels photo → labeled still slots), `run_mv` dispatch.

## Verification

```text
Full suite: 420 tests OK (255 baseline + new: blueprint, material_treatment,
  treatment_audit, treatment_integration, stack_renderer).

stock_story_e2e (ffmpeg canonical): verify 92.5 PASS; 5/5 P1 audits pass;
  blueprint gate live-proven (good blueprint completes; an unrealized beat blocks
  before render).

treatment_demo (enumeration): "three coffee-bean origins" renders as 3 Pexels
  stills (Ethiopia/Colombia/Guatemala), each beat-fast (~one beat, tempo-derived),
  each carrying its per-item label; treatment_audit PASS (count==n_required,
  labels present); E2E verify 92.5 PASS.
```

Bugs fixed this session (surfaced by driving the real chain):

```text
- video_tools.py validate: NameError GRADE_PRESETS/BGM_MOODS (missing imports).
- video_tools.py: Windows cp950 UnicodeEncodeError (no UTF-8 stdout reconfigure).
- runtime category resolution: always used the global examples map and ignored a
  project's own categories_ref vocabulary -> failed validate_contract. Now prefers
  categories_ref -> run dir -> project input -> global.
- runtime: a contract with no brief.json looped forever on missing_artifact:brief.json.
  Now stops with a clear "provide a brief" message.
```

## Status

Three-tier editorial layer landed: blueprint gate live in runtime; material treatment
wired Node 9/11 with a working photo-stack renderer (beat-fast). Codex's
editing-intent structural layer (editorial_design / shot_slots expansion) and a Node 2
`n_required` coverage producer remain unwired (the Node 11 treatment audit already
does the count check). ffmpeg stays canonical; all additions are opt-in and inert for
existing runs.
