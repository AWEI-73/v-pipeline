# Decision: Effects / Node14 Roadmap Alignment

Date: 2026-06-19
Status: accepted
Scope: roadmap / effects-director / Workbench / Node14 planning

## Context

The backend material-map lifecycle, generated-material fallback, story-soul
scaffolding, and Workbench draft layer are now stable enough to resume effects
work. Effects should be the next visible quality layer, but the boundary must
stay clear:

- ffmpeg / `contract-run` remains the canonical final renderer.
- Workbench is a draft preview and intent-editing surface.
- Remotion may help preview or author effects, but it is not a required normal
  BUILD dependency.
- Node14 is the local revision/effects orchestration node, not a mandatory
  stage for every no-effects render.

## Decision

Treat the next effects work as four bounded tracks:

1. **FX0 Effects status cleanup**: align docs, dashboard wording, build-profile
   boundaries, and tests.
2. **FX1 Effect asset spec**: define overlays, transition plates, lower thirds,
   particles, title textures, and generated motion backgrounds as effect assets
   with `asset_role=effect`.
3. **FX2 Effect build wiring**: prove `light_effects` / `motion_graphics`
   produce visible ffmpeg-rendered outputs with traceable manifests and gap
   reporting.
4. **FX3 Node14 revision orchestration**: consume effect gaps or Workbench draft
   effect intents and write bounded revision artifacts without restarting the
   whole pipeline.

Remotion is evaluated under **FX4 Remotion/Preview Boundary** only as optional
preview/authoring support. A Remotion component must export intent/spec back to
pipeline artifacts before it can affect canonical delivery.

## Boundaries

- Effect assets are not real-event evidence and must not satisfy material-map
  coverage.
- Generated effect assets keep `source_type=generated`.
- Missing optional effects warn; missing `required_for_story` effects can block
  or route to Node14.
- Text ownership must remain singular. Do not burn the same text layer in both
  base MV and motion graphics.
- Workbench patches remain draft artifacts until backend contracts consume and
  revalidate them.

## Acceptance Signals

- Roadmap no longer lists Node14 effects as generically deferred.
- The active roadmap names effect asset spec, effect build, Node14 orchestration,
  and Remotion boundary separately.
- `docs/INDEX.md` points agents to this decision.
- Tests assert the roadmap status so later agents do not regress the boundary.

## FX1 Implementation Note

Implemented as a neutral contract layer:

- Module: `video_pipeline_core/effect_contract.py`
- CLI: `python video_tools.py effect-intent-plan director_shot_plan.json --out-plan effect_intent_plan.json --out-spec effect_asset_spec.json`
- Command catalog workflow: `effects_contract`
- Upstream skill hook: `skills/story-soul-blueprint.md` writes
  `effect_intent` at beat level; `skills/video-workflow.md` can collect
  `effect_direction` during the interactive brief.

The generated `effect_intent_plan.json` is backend-neutral and forbids
Remotion-specific fields such as component names, props, fps, springs, and
`durationFrames`. The generated `effect_asset_spec.json` marks all effect
assets with `asset_role=effect` and `must_not_satisfy_material_need=true`.

This lets FX2/FX3 map an effect intent to ffmpeg, motion graphics, or optional
Remotion adapters without contaminating upstream SPEC with a single renderer's
API.
