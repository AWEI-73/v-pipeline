---
title: Hermes Video Pipeline — Canonical Roadmap
type: project
status: active
updated: 2026-06-18
tags: [project, video, pipeline, roadmap, agent-workflow]
---

# Hermes Video Pipeline — Canonical Roadmap

This file is now the **current-state roadmap and navigation index**. Long-form
implementation history was moved out to `docs/roadmap-history/` so agents do not
confuse historical plans with active direction.

Read order for agents:

1. `README.md`
2. `roadmap.md` (this file)
3. `RUNBOOK.md`
4. `docs/INDEX.md`
5. Topic-specific docs linked below

## Current Canonical State

### Backend

The backend is stable through the material-map lifecycle and BUILD handoff:

- Material supply/demand lifecycle M6a-M6e is complete as backend
  infrastructure.
- `contract-run` revalidates material needs, maps, delta, revisions, and gate
  status before BUILD.
- Map-ranked retrieval, visual diversity soft selection, photo map-ranked
  renderability, SRP1/SRP2/SRP3, opening/ending bookends, and Workbench draft
  handoff are implemented.
- Existing known quality gaps are now creative/input issues more than core
  contract issues: weak upstream story concept, thin material plans, black/cut
  windows in raw footage, and human sign-off.

Canonical material-map summary:

- `docs/material-map-lifecycle.md`

### Frontend

Dashboard and Workbench are separate surfaces:

- Dashboard = read/review/node-status surface.
- Workbench = interactive preview, draft timeline patching, limited export, and
  contract patch handoff.
- Workbench writes draft artifacts only; official final render remains backend
  ffmpeg / `contract-run`.

Frontend references:

- `docs/workbench-dashboard-integration.md`
- `docs/decisions/2026-06-16-native-preview-engine.md`
- `dashboard/README.md`

## Active Direction

### Next Strategic Work: Creative Blueprint / Story Soul Layer

Current problem: the pipeline can enforce material truth, but the upstream story
blueprint is too thin. It can produce a technically valid video that still lacks
narrative soul.

Next work should build a reusable upstream creative layer, not add more BUILD
parameters:

```text
Story World / Information Intake
  -> Creative Concept / Narrative Device
  -> Screenplay Beats
  -> Director Shot Plan
  -> material_needs + generation_manifest
  -> Material Map Lifecycle
  -> BUILD
```

Target first increment:

- `SSB1 Story Soul Blueprint Skill`
- Design reference: `docs/story-soul-blueprint-skills.md`

Expected outputs:

- `story_world.json`
- `creative_concept.json`
- `screenplay_beats.json`
- `director_shot_plan.json`
- `material_needs.json`
- `generation_manifest.json` / `material_generation_fallback.json`
- `review_checklist.md`

Acceptance intent:

- A graduation/training film should not be reduced to "course A, course B,
  course C".
- The skill must extract a core metaphor/narrative device, such as the 66th
  graduation film example: "0.66% of life spent in training center" and a
  report-writing memory frame.
- Every beat must declare its story function, emotional movement, required
  visual actions, material count, and fallback.
- Material quantity must be estimated honestly before BUILD. If available or
  generated material cannot support the promised duration, the plan must shorten
  or request material instead of pretending success.

Implementation direction:

- Start with one composite skill: `skills/story-soul-blueprint.md`.
- Keep existing `writer`, `director`, and `material-map` skills. The new skill
  feeds them richer upstream artifacts; it does not replace them.
- Do not split into multiple skills until the composite skill has passed at
  least one real graduation/training acceptance case and one generated
  comic/photo story acceptance case.
- Once proven, the composite sections may be split into:
  `story-world-intake`, `narrative-device`, `screenplay-beat-architect`, and
  `material-prompt-compiler`.
- The layer must compile toward existing canonical artifacts rather than create
  a second BUILD schema.

### MGF1 Material Generation Fallback Skill

Status: in implementation / review.

Purpose: when M6 delta proves some needs are `missing` or `thin`, produce a
provider-neutral generated-material job list without pretending generated
assets are real footage.

Canonical files:

- Skill: `skills/material-generation-fallback.md`
- Tool: `video_tools.py material-generation-fallback`
- Module: `video_pipeline_core/material_generation_fallback.py`

Flow:

```text
material_delta.json
  + optional story_world / creative_concept / screenplay_beats / director_shot_plan
  -> material_generation_fallback.json
  -> external provider / imagegen / Gemini / Antigravity
  -> generated files re-ingested into material-map
  -> satisfies(candidate)
  -> material_delta fresh rerun
  -> reviewer accept / revision
  -> BUILD
```

Hard boundaries:

- `material_delta.ok=false` produces no jobs.
- Only `missing` / `thin` needs produce jobs.
- Generated assets enter as `candidate`, never `accepted`.
- Generated assets must carry `source_type=generated` and
  `must_not_claim_real_event=true`.
- This skill does not bypass M6 gate, material-map review, or Workbench
  canonical separation.

Practical use:

- Good for comic/photo stories, symbolic memory frames, chapter bridges,
  abstract transitions, and non-identifying reenactment inserts.
- Not valid for real-person proof, official speeches, identity-sensitive
  scenes, or event evidence.

## Stable Foundations — Do Not Reopen Without Evidence

These areas are considered settled unless a fresh run proves a contract bug:

- M6 material-map lifecycle and gate: `docs/material-map-lifecycle.md`
- Native preview / Workbench draft layer:
  `docs/decisions/2026-06-16-native-preview-engine.md`
- Dashboard/Workbench integration:
  `docs/workbench-dashboard-integration.md`
- Tool/run layout consolidation:
  `docs/repository-consolidation-map.md`,
  `docs/decisions/2026-06-17-tool-surface-and-run-layout-consolidation.md`
- Working loop and TDD evidence rules:
  `docs/decisions/2026-06-14-working-loop-and-tdd-evidence.md`

## Deferred / Later

These remain intentionally deferred until the creative blueprint layer is useful:

- Deep semantic function vocabulary F2.
- VD3 or advanced visual understanding.
- Node 14 advanced effects / Remotion-like final renderer.
- Full Audio Graph V2.
- Dashboard OAuth / hosted runtime control.
- Large repo/module refactors that do not directly unblock a user-visible flow.

## Historical Archive

The previous long-form roadmap was archived losslessly here:

- `docs/roadmap-history/2026-06-18-roadmap-pre-split.md`

Use it for evidence only. It contains historical sections for:

- Material phase M0-M6 and MM/BR/VD/MR/SRP work.
- Sensory phase S1-S4.
- Effects phase E1-E7.
- Convergence work C0-C6.
- Windows migration and early VERIFY tool packs.
- Native preview / Workbench / effect / operator-flow acceptance notes.

The archive is not current instruction unless this roadmap or a current decision
document links to a specific section.

## Current Engineering Rule

When adding new work:

1. Put creative intent above the material-map lifecycle.
2. Keep runtime contracts deterministic and testable.
3. Do not mix historical roadmap text into active instructions.
4. Add a short decision doc for significant architecture changes.
5. Run focused tests and relevant full regression before claiming completion.
