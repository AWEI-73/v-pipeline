# Material Map Lifecycle ??Canonical Summary

Status: complete as a backend lifecycle, with real-case automated acceptance.
Last consolidated: 2026-06-18

This document is the short, current reference for the material-map work that used
to be spread through the long roadmap. The full historical evidence remains in
`docs/archive/roadmap-history/2026-06-18-roadmap-pre-split.md`.

## Purpose

The material map is the pipeline's supply/demand contract layer. It prevents the
system from silently using wrong material, faking missing footage, or treating a
thin material pool as a complete film.

It supports three entry modes:

1. Existing material first (`existing-material-first`): scan/curate actual
   material, then discuss story. The material map becomes the story source and
   constraint, especially for teaching, personal video, event recap, and brand
   footage routes.
2. Story first (`story-first` / script-first): declare `material_needs`, then
   prove coverage or request more material. The material map becomes the
   validation and handoff layer after story/design intent has produced needs.
3. Partial material (`hybrid`): combine covered needs, missing needs, accepted
   waivers, generated/reshoot candidates, and revised contracts without
   bypassing the BUILD gate.

In existing-material-first routes, generation is fallback: diagrams, chapter
cards, symbolic inserts, or missing non-proof bridge visuals. In story-first
generated routes, generated assets may be primary visual candidates, but they
still return through material-map review before satisfying coverage.

## Canonical Artifacts

- `material_needs.json` ??required material demand, stable `need_id`, fallback
  options, and validation.
- Per-asset `*.map.json` ??actual scenes, sources, captions, labels, and
  `satisfies[]` edges.
- `project_material_map.json` ??deterministic project-level aggregation of
  per-asset maps. It is a projection, not a second canonical truth source.
- `visual_diversity_review.json` -- curator/human review of scene-level
  `visual_family`, `angle_scale`, `action_family`, subject, duplicate/reject,
  and visual-diversity evidence.
- `material_delta.json` ??coverage outcomes: `covered`, `thin`, `missing`,
  `excess`, plus tier/route/evidence.
- `material_gap_brief.json` -- machine-readable follow-up task packet for
  missing/thin needs: collect existing material, reshoot, generated material,
  stock retrieval, text bridge, script rewrite, or waiver.
- `shooting_brief.md` -- human-readable reshoot / collection brief derived from
  `material_gap_brief.json` when real capture is the right follow-up route.
- `revision_decisions.json` ??accepted/rejected/pending human decisions for
  missing material.
- `revised_segment_contract.json` ??revised executable contract when decisions
  change the script.
- `material_map_lifecycle.json` ??stage report and handoff status.

## Implemented Lifecycle

### M6a ??Contract And Lineage

Completed:

- `material_needs` validator.
- Stable project-local `need_id`.
- Scene-level `satisfies[]` edges with `accepted | candidate | rejected`.
- End-to-end reference chain:
  `need_id -> shooting brief -> scene satisfies edge -> segment_contract need_refs`.

Boundary:

- M6a validates joins and reference integrity. It does not decide covered/thin/
  missing.

### M6b ??Material Delta And Pre-BUILD Gate

Completed:

- Coverage outcomes based on validated needs and satisfies edges.
- Renderable-evidence filtering.
- Asset identity validation.
- Fail-closed pre-BUILD gate in `contract_adapter`.
- Stale final quarantine when a blocked run would otherwise leave an old
  `final.mp4` at the canonical path.

Gate rule:

- BUILD may proceed only when `delta.ok is True` and
  `delta.ready_for_build is True`.

### M6c ??Delta-Driven Script Revision

Completed:

- Revision decisions: collect/reshoot/review/shorten/rewrite/drop/waive.
- Canonical waiver contract.
- Atomic revised-contract + material-revision artifact writes.
- Runtime plumbing: declared decisions trigger fresh delta, revision application,
  and gate re-check before BUILD.

Boundary:

- M6c does not invent story content. It applies accepted decisions only.

### M6d ??Independent Material Map Skill

Completed:

- `skills/material-map.md` and `material-map-lifecycle` orchestration.
- Stage machine:
  `await_requirements_discussion`, `await_material`, `await_map_review`,
  `await_revision_decision`, `revision_blocked`, `build_ready`, `invalid`.
- Build handoff only when runtime gate can re-validate the contract.

Boundary:

- M6d orchestrates canonical tools. It does not create a second material-map
  schema and does not render.

### M6e ??Real-Case Automated Acceptance

Completed:

- Four entry replay on real 67th footage:
  only-material, script-first insufficient material, covered material, and
  revision/waiver.
- Unified relative-path material map loader across lifecycle, gate, and BUILD.
- Acceptance harness can be rerun from repo.

Open but non-blocking:

- Human sign-off on final film quality.
- Full-scale ingest of all raw footage and HEIC coverage in production-like runs.

## Current Boundary

The material-map backend is stable enough to treat as infrastructure. Future work
should not reopen M6 unless a real run proves a contract bug.

Upcoming creative work should happen above it:

```text
Story World / Creative Blueprint
  -> Screenplay Beats / Director Shot Plan
  -> material_needs + generation_manifest
  -> Material Map Lifecycle
  -> BUILD
```

## ISF1 Relationship

In the interactive skill flow, material-map is the material truth layer. It is
not the story writer, not the image generator, and not the Workbench editor.

```text
story-soul-blueprint
  -> material_needs.json
  -> material-map lifecycle
  -> material_delta.json
  -> shooting-brief / material gap brief when needs are missing or thin
  -> generated-material-producer when generation is allowed
  -> generated assets return as candidate satisfies edges
  -> material_delta fresh rerun
  -> rough_cut_plan.json / timeline_build.json with scene_id, material_map_id,
     need_id, usable range, and duration shortfall evidence
  -> official BUILD handoff only after gate/revision passes
```

Relationship boundaries:

- `story-soul-blueprint` owns story world, narrative device, beats, and shot
  intent. Material-map consumes that intent as `material_needs.json`; it does
  not invent a better story.
- `curator` reviews scene-level material labels and duplicate/reject evidence.
  These labels help rough cut and visual fatigue checks, but they do not satisfy
  `material_needs` until material-map coverage is recalculated.
- `generated-material-producer` can fill missing/thin needs, but generated
  assets return to material-map as `candidate` evidence and require review
  before they can satisfy delta.
- `shooting-brief` converts missing/thin needs into executable gap tasks. It
  does not satisfy coverage; it creates the handoff for collect/reshoot,
  generation, retrieval, rewrite, or waiver. Resulting files must return through
  material-map review and fresh delta.
- `storyboard_panel_locked=true` is interpreted before BUILD for comic/photo/
  storybook narration. It means one generated panel owns one story beat; extend
  duration or generate more panels instead of auto-filling unrelated panels.
- Workbench can preview and write draft patches. Workbench drafts are not
  material truth and must not overwrite canonical needs, maps, delta, or the
  official BUILD handoff.
- Rough cut may trim a long accepted scene to the segment's requested duration,
  but it must not hide a shortfall. If a reviewed `usable_range` is shorter
  than the requested segment duration, keep the selected clip and emit a
  `rough_cut_plan.gaps[]` item with the missing seconds so delivery and
  Workbench can route the issue back to material collection, shorten/merge,
  generation, or waiver. Still images/photos may hold for the requested
  duration; they are not duration-shortfall failures, but they must keep
  `asset_id`/`need_id` trace for Workbench and visual-fatigue review.
- The official BUILD handoff remains backend-owned and must be revalidated by
  `contract-run` / M6 gates.

## Useful Links

- Full pre-split evidence: `docs/archive/roadmap-history/2026-06-18-roadmap-pre-split.md`
- Real-case M6e decision: `docs/archive/decisions/2026-06-15-m6e-real-case-acceptance.md`
- Material-map blackbox observation: `docs/archive/decisions/2026-06-18-node13-material-map-blackbox-observation.md`
- Skill: `skills/material-map.md`
- Curator skill: `skills/curator.md`
- Gap brief skill: `skills/shooting-brief.md`
- Gap brief tool: `tools/material_gap_brief.py`
- Core modules: `video_pipeline_core/material_needs.py`,
  `video_pipeline_core/project_material_map.py`,
  `video_pipeline_core/material_delta.py`,
  `video_pipeline_core/material_gap_brief.py`,
  `video_pipeline_core/material_revision.py`,
  `video_pipeline_core/material_map_lifecycle.py`
