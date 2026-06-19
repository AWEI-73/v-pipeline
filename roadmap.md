---
title: Hermes Video Pipeline — Canonical Roadmap
type: project
status: active
updated: 2026-06-19
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

### ISF1 Interactive Skill Flow

Status: implemented / accepted as current process contract.

Purpose: solidify the interactive operating flow without freezing story
templates. Agents should acquire missing parameters through skills, emit
canonical artifacts, and stop at explicit gates instead of guessing.

Decision:

- `docs/decisions/2026-06-19-interactive-skill-flow.md`

Canonical entry:

```text
video-pipeline
  -> video-workflow when the request is vague
  -> story-soul-blueprint when story soul / narrative device is thin
  -> material-map when material truth, coverage, delta, or handoff is needed
  -> generated-material-producer when missing material may be generated
  -> runtime / Workbench / verify for BUILD, draft review, and delivery
```

Rules:

- This is process solidification, not template solidification.
- `storyboard_panel_locked=true` applies to comic/photo/storybook/panel
  narration; stretch the panel or generate more panels instead of auto-filling
  unrelated panels.
- Workbench remains a draft patch surface; official render remains backend
  ffmpeg / `contract-run`.
- Historical roadmap sections are evidence only, not active flow instruction.

### Next Strategic Work: Creative Blueprint / Story Soul Layer

Status: implemented as SSB1 baseline; continue with real creative acceptance.

Current problem: the pipeline can enforce material truth, but the upstream story
blueprint can still be too thin if the agent treats it as a parameter sheet. It
can produce a technically valid video that still lacks narrative soul.

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

Status: implemented / accepted as baseline scaffolding.

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

Status: implemented / accepted for contract-chain proof.

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

Status: implemented / accepted for provider-neutral generated-material fallback.

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

Status: implemented / accepted for offline and provider-output material flow.

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

Status: implemented / accepted for provider-output import.

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

Status: implemented / accepted for real image-provider handoff.

Purpose: force real generated-image work through explicit model/provider
execution instead of relying on the offline `test_pil` renderer.

Canonical files:

- Tool: `video_tools.py generated-image-provider-packet`
- Tool: `video_tools.py codex-imagegen-provider-fill`
- Module: `video_pipeline_core/generated_image_provider_packet.py`
- Tests: `tests/test_generated_image_provider_packet.py`
- Skill: `skills/generated-material-producer.md`

Flow:

```text
material_generation_fallback.json
  -> generated-image-provider-packet
  -> agent calls real image provider
  -> codex-imagegen-provider-fill OR manual generated_provider_outputs.json
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
- Codex imagegen outputs can be copied from explicit image files or from the
  newest `~/.codex/generated_images` session into `generated_provider_outputs.json`;
- `test_pil` is rejected as a final-art provider in this path;
- the backend still does not trust model output until import + review pass.

### GMP2.6 Storyboard Panel-Locked Rendering Boundary

Status: documented / acceptance-proven.

Purpose: preserve story semantics for generated comic/photo narratives.

Evidence:

- Real Codex imagegen E2E produced 21 manga-style panels for
  `Rooftop Postcard`.
- Normal BUILD auto-fill made a technically valid story MV, but reused panels
  to fill long TTS narration.
- A panel-locked render stretched each image to its TTS segment duration,
  yielding a better comic/storybook video: one panel per narration beat,
  21/21 panels used exactly once.

Rule:

```text
storyboard_panel_locked=true
  -> one generated panel owns one narration/story beat
  -> stretch panel duration / Ken Burns for long voiceover
  -> generate more panels or shorten narration if visual support is too thin
  -> do not auto-fill with other accepted panels from the same need
```

Normal auto-fill remains correct for event MV / recap / course montage cases
where accepted shots under the same need are interchangeable enough to cover
duration.

### GMP3 Generated-Material Skill Acceptance Harness

Status: implemented / accepted for small generated-material flow replay.

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

Status: implemented / accepted for generated candidate promotion.

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

## Next Phase — Effects / Node14

Status: active next development direction.

Purpose: add tasteful, bounded visual effects now that material truth, generated
material fallback, Workbench draft review, and story-soul scaffolding are
stable enough. This is not a switch to a Remotion final renderer.

Canonical decision:

- `docs/decisions/2026-06-19-effects-node14-roadmap-alignment.md`

Current proven foundation:

- `effects-director` owns visual-style intent: color grade, title card,
  transition, and motion-graphic intent.
- `build_profile.render_profile` already supports `no_effects`,
  `light_effects`, and `motion_graphics`.
- `contract-run` can write `light_effects_plan.json`,
  `light_effects_manifest.json`, `light_effects_baseline_review.json`,
  `motion_graphics_contract.json`, `motion_graphics_render_plan.json`, and
  `motion_graphics_manifest.json` when enabled.
- Dashboard Node14 can surface effects artifacts and gaps.
- Workbench can show draft effect intent markers, but it is not the official
  final renderer.
- Remotion is installed and may be used as a reference or optional preview
  runtime, but canonical delivery remains ffmpeg / `contract-run`.

Planned increments:

### FX0 Effects Status Cleanup

Goal: normalize docs and tests around current effect ownership before adding
new capabilities.

Acceptance:

- roadmap, effects-director, dashboard docs, and build-profile boundaries agree.
- Node14 is described as revision/effects orchestration, not a mandatory render
  stage for every film.
- Remotion is explicitly optional / preview / reference only.

### FX1 Effect Asset Spec

Status: implemented / accepted for neutral effect contract.

Goal: define effect assets as first-class, reviewable material-like inputs
without mixing them with event evidence.

Expected artifacts:

- `effect_asset_spec.json`
- `effect_asset_manifest.json`
- `effect_intent_plan.json`

Canonical files:

- Tool: `video_tools.py effect-intent-plan`
- Module: `video_pipeline_core/effect_contract.py`
- Tests: `tests/test_effect_contract.py`

Rules:

- effect assets may be overlays, particles, light leaks, lower thirds,
  transition plates, title textures, or generated motion backgrounds.
- effect assets carry `asset_role=effect`, not event material coverage.
- generated effect assets must keep `source_type=generated` and must not satisfy
  real-event material needs.
- missing optional effects should warn, not block, unless the contract marks
  the effect as `required_for_story`.
- neutral SPEC forbids backend-specific fields such as Remotion component names,
  props, fps, or `durationFrames`; those belong to FX2/FX3 adapters.

### FX2 Effect Build Wiring

Goal: make `light_effects` / `motion_graphics` build outputs visible and
measurable in real renders.

Acceptance:

- an enabled `light_effects` build writes plan, manifest, baseline review, and
  at least one visible rendered effect in a real ffmpeg output.
- effect outputs are traced back to segment/clip/effect id.
- no duplicate text burn: canonical text ownership remains singular.
- failed effect render produces a Node14-visible gap instead of pretending
  success.

### FX3 Node14 Revision Orchestration

Goal: use Node14 for local effect fixes and optional finishing adjustments
without restarting the whole pipeline.

Acceptance:

- Node14 consumes effect gaps, Workbench draft effect intents, or user revision
  requests.
- Node14 writes bounded revision artifacts such as `effect_patch.json` or
  revised `effect_intent_plan.json`.
- canonical final render still goes through backend ffmpeg / `contract-run`.
- Dashboard shows Node14 status and links to effect artifacts.

### FX4 Remotion/Preview Boundary

Goal: evaluate Remotion only where it helps preview or effect authoring.

Rules:

- Do not make Remotion a required dependency for normal BUILD.
- Do not claim browser preview equals final ffmpeg output unless a specific
  effect has a parity test.
- If a Remotion component is useful, export its intent/spec back to pipeline
  artifacts before final render.

Deferred inside effects:

- full Remotion-like final renderer;
- arbitrary free-form VFX;
- paid/closed CapCut effect packs as required dependencies;
- full Audio Graph V2.

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
- Effects baseline and current gap reporting:
  `docs/decisions/2026-06-11-effects-baseline-and-recipe-order.md`
- Working loop and TDD evidence rules:
  `docs/decisions/2026-06-14-working-loop-and-tdd-evidence.md`

## Deferred / Later

These remain intentionally deferred until a concrete run proves they are needed:

- Deep semantic function vocabulary F2.
- VD3 or advanced visual understanding.
- Remotion-like final renderer.
- Arbitrary free-form advanced VFX.
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
