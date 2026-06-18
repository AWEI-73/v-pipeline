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

### SSB1 Story Soul Blueprint Skill

Status: implemented / acceptance review.

Canonical files:

- Skill: `skills/story-soul-blueprint.md`
- Tool: `video_tools.py story-soul-blueprint`
- Module: `video_pipeline_core/story_soul_blueprint.py`
- Tests: `tests/test_story_soul_blueprint.py`

Flow:

```text
project_brief.json
  -> story_world.json
  -> creative_concept.json
  -> screenplay_beats.json
  -> director_shot_plan.json
  -> material_needs.json
  -> generation_manifest.json
  -> review_checklist.md
```

Current acceptance:

- Training/graduation brief produces a report-writing memory frame and `0.66%`
  metaphor instead of a course list.
- Generated comic brief produces enough panel estimates for a one-minute story
  and all shot-plan items prefer generated images.
- Generic brief without a story subject fails closed.

Boundary:

- SSB1 is deterministic baseline scaffolding. It gives agents a stronger
  artifact shape and minimum story logic; it is not a substitute for a human or
  high-end writer model improving the prose.

### SSB1→GMP End-To-End Acceptance

Status: implemented / acceptance review.

Tool:

- `tools/story_to_generated_material_e2e.py`

Flow:

```text
project brief
  -> story-soul-blueprint artifacts
  -> material_delta missing
  -> material_generation_fallback
  -> generated_material_produce
  -> generated_material_review
  -> material_delta covered
```

Current case:

- `postcard_city_sky`
- 5 screenplay beats
- 5 material needs
- 21 generated storyboard panels
- initial delta: `missing=5`
- after generation: `thin=5`, `missing=0`
- after review: `covered=5`, `thin=0`, `missing=0`

Boundary: this proves the contract chain and material counts. The deterministic
storyboard cards are not final art; real GPT image / Gemini outputs must enter
through `generated-material-import` before review.

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

### GMP1 Generated Material Producer Skill

Status: implemented / acceptance review.

Purpose: execute MGF1 jobs into generated files and write the artifacts needed
for the material-map lifecycle to review them.

Canonical files:

- Skill: `skills/generated-material-producer.md`
- Tool: `video_tools.py generated-material-produce`
- Module: `video_pipeline_core/generated_material_producer.py`

Flow:

```text
material_generation_fallback.json + material_needs.json
  -> generated images / provider outputs
  -> generated_asset_manifest.json
  -> generated_material_maps/*.map.json
  -> project_material_map.json
  -> generated_material_quality_review.json
```

Hard boundaries:

- generated assets remain `source=generated`.
- generated assets are `candidate` satisfies edges, never accepted evidence.
- `test_pil` renderer is only an offline flow/proof renderer; final art should
  use Gemini / Antigravity / imagegen or another provider that writes the same
  output shape.
- quality review checks story function, style anchors, camera language, and
  truth boundary, but it is not a human aesthetic sign-off.

### GMP2 Provider Output Intake + Style/Character Lock

Status: implemented / acceptance review.

Purpose: accept real generated files from GPT image / Gemini / Antigravity
without letting arbitrary files bypass material-map truth boundaries.

Canonical files:

- Tool: `video_tools.py generated-material-import`
- Module function:
  `generated_material_producer.produce_generated_materials_from_provider_outputs`
- Tests: `tests/test_generated_material_provider_intake.py`

Input shape:

```json
{
  "items": [
    {
      "job_id": "gen_hero",
      "file": "provider/hero-a.png",
      "provider": "codex_imagegen",
      "style_anchors": ["watercolor", "soft ink line"],
      "character_anchors": ["lead apprentice", "amber lantern"]
    }
  ]
}
```

Rules:

- every `job_id` must match a planned generation job.
- each job must provide at least `panel_count` readable image files.
- relative provider file paths resolve relative to the provider output JSON.
- style/character anchors declared by `style_profile.json` must be present in
  provider output metadata; mismatch fails the quality gate.
- successful imports still produce `candidate` material-map evidence only.

### GMP2.5 Real Image Provider Packet

Status: implemented / acceptance review.

Purpose: force real generated-image work through explicit model/provider
execution instead of relying on the offline `test_pil` renderer.

Canonical files:

- Tool: `video_tools.py generated-image-provider-packet`
- Module: `video_pipeline_core/generated_image_provider_packet.py`
- Tests: `tests/test_generated_image_provider_packet.py`
- Skill: `skills/generated-material-producer.md`

Flow:

```text
material_generation_fallback.json
  -> generated-image-provider-packet
  -> agent calls real image provider and saves target files
  -> generated-material-import
  -> generated-material-review
```

Rules:

- the packet writes `generated_provider_packet.json`,
  `generated_provider_prompts.md`, and
  `generated_provider_outputs.template.json`;
- every panel gets a deterministic `target_file` under `provider_outputs/`;
- provider candidates can include Codex imagegen, Gemini, Antigravity, or other
  configured model tools;
- `test_pil` is rejected as a final-art provider in this path;
- the backend still does not trust model output until import + review pass.

### GMP3 Generated-Material Skill Acceptance Harness

Status: implemented / acceptance review.

Purpose: prove the generated-material skill can be driven from the beginning of
a small project, not just unit-tested in isolation.

Tool:

- `tools/generated_material_flow_acceptance.py`

Flow under test:

```text
material_needs.json with no material
  -> material_delta missing
  -> material_generation_fallback jobs
  -> generated_material_produce images/maps/review
  -> project_material_map with candidate satisfies
  -> material_delta rerun
  -> director-style score/report
```

Acceptance cases:

- `Rain Station Apprentice`: watercolor comic, lead apprentice + amber lantern,
  4 generated panels, score 88/100.
- `Rooftop Postcard`: manga watercolor, red scarf courier + postcard, 4
  generated panels, score 85/100.

Important reading: the expected post-generation state is `thin`, not `covered`,
because generated assets remain candidate until reviewer promotion.

### GMP4 Generated Candidate Review / Promotion

Status: implemented / acceptance review.

Purpose: safely promote generated material-map candidates after explicit review.

Canonical files:

- Tool: `video_tools.py generated-material-review`
- Module: `video_pipeline_core/generated_material_review.py`
- Tests: `tests/test_generated_material_review.py`

Flow:

```text
project_material_map with generated candidate edges
  -> generated_material_review.json verdict
  -> reviewed_project_material_map.json
  -> material_delta fresh rerun
```

Rules:

- only generated `candidate` edges can be reviewed by this tool.
- each decision requires reviewer, reason, asset_id, scene_index, need_id, and
  status `accepted` or `rejected`.
- accepted edges can satisfy material_delta; rejected edges remain visible but
  do not count as coverage.
- unknown asset/scene/need, non-generated targets, bad status, or missing reason
  fails closed.

Acceptance harness update:

- `tools/generated_material_flow_acceptance.py` now applies an explicit review
  verdict in both comic cases.
- Post-generation delta: `thin=2`.
- Post-review delta: `covered=2`, `thin=0`.

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
