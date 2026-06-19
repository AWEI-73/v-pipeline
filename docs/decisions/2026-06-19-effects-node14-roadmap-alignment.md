# Decision: Effects / Node14 Roadmap Alignment

Date: 2026-06-19
Status: accepted
Scope: roadmap / effects-director / Workbench / Brownfield Edit / Node14 planning

## Context

The backend material-map lifecycle, generated-material fallback, story-soul
scaffolding, and Workbench draft layer are now stable enough to resume effects
work. Effects should be the next visible quality layer, but the boundary must
stay clear:

- ffmpeg / `contract-run` remains the canonical final renderer.
- Workbench is a draft preview and intent-editing surface.
- Remotion may author prompt-driven effects inside Brownfield Edit / Node14, but
  it is not a required normal BUILD dependency.
- Brownfield Edit is the local revision/effects orchestration route, not a
  mandatory stage for every no-effects render.
- Node14 remains a legacy implementation node inside Brownfield Edit.

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
4. **FX3 Brownfield Edit revision orchestration**: consume effect gaps or
   Workbench draft effect intents and write bounded revision artifacts without
   restarting the whole pipeline.

Remotion is evaluated under **FX4 Remotion/Preview Boundary** only as optional
preview/authoring support. A Remotion component must export intent/spec back to
pipeline artifacts before it can affect canonical delivery.

## Boundaries

- Effect assets are not real-event evidence and must not satisfy material-map
  coverage.
- Generated effect assets keep `source_type=generated`.
- Missing optional effects warn; missing `required_for_story` effects can block
  or route to Brownfield Edit.
- Brownfield may import incremental effect asset / sfx / overlay files, but
  story evidence material must return through material-map review before it can
  affect coverage.
- Text ownership must remain singular. Do not burn the same text layer in both
  base MV and motion graphics.
- Workbench patches remain draft artifacts until backend contracts consume and
  revalidate them.

## Acceptance Signals

- Roadmap no longer lists Node14 effects as generically deferred.
- The active roadmap names effect asset spec, effect build, Brownfield Edit /
  Node14 orchestration, and Remotion boundary separately.
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

## FX2 Implementation Note

FX2 now has a bounded neutral-intent handoff into the existing light-effects
BUILD lane:

- `light_effects.build_light_effects_plan(..., effect_intent_plan=...)` maps
  validated FX1 effects to safe operations where possible.
- `video_tools.py light-effects-plan --effect-intent-plan ...` exposes the
  offline planning path.
- `contract-run` accepts a top-level `effect_intent_plan_ref` only for
  effects-enabled builds. The ref resolves strictly next to the contract file
  for relative paths, validates through `validate_effect_intent_plan`, and
  fails closed before render when broken.
- Non-ffmpeg effects are represented as `external_effect` with
  `status=pending_backend`, which is the intended bridge to Brownfield Edit or an
  optional Remotion adapter.
- `motion_graphics.contract_from_effect_intent_plan` projects ffmpeg-safe
  `title_card` / `lower_third` intents into timed ASS overlays after the BUILD
  timeline exists.
- `tests/test_effects_e2e.py` proves a real `contract-run` can render a
  lower-third from `effect_intent_plan_ref` into `final.mp4`, while a
  Remotion-only transition remains a visible baseline gap.

This is not a Remotion runtime and does not make browser preview equal final
ffmpeg output. The remaining effects work is broader recipe coverage and FX3
Brownfield routing for unresolved gaps.

## FX3a Node14 Gap Routing

Current naming: this is a Brownfield Edit route step. The Node14 name is kept
for backward-compatible artifacts and dashboards.

Implemented as a bounded artifact conversion, not an effect renderer.

- New CLI: `python video_tools.py effect-revision-request --baseline-review light_effects_baseline_review.json --light-effects-plan light_effects_plan.json --out effect_revision_request.json`
- New artifact: `effect_revision_request.json`.
- Source of truth remains `light_effects_baseline_review.json` plus optional
  `light_effects_plan.json` evidence.
- Route mapping:
  - regular missing ffmpeg-safe effects -> `implement_or_wire_effect_recipe`;
  - `external_effect` or pending backend items -> `route_to_node14_or_remotion_adapter`.
- Dashboard/Node14 surfaces pending effect revision requests before raw gap
  warnings.

Boundary: FX3a does not call Remotion, does not render, does not mutate
`final.mp4`, and does not rewrite canonical `effect_intent_plan.json`. The
actual adapter implementation and automatic revised effect-intent authoring
remain separate increments.

## FX3b Request To Draft Patch

Implemented as a second bounded Brownfield/Node14 step.

- New CLI: `python video_tools.py effect-revision-draft --request effect_revision_request.json --out-patch effect_recipe_patch.json --effect-intent-plan effect_intent_plan.json --out-intent-draft revised_effect_intent_plan.draft.json`
- New primary artifact: `effect_recipe_patch.json`.
- Optional draft wrapper: `revised_effect_intent_plan.draft.json`.
- Patch mapping:
  - `implement_or_wire_effect_recipe` -> `wire_effect_recipe`;
  - `route_to_node14_or_remotion_adapter` -> `build_node14_adapter`.
- The optional draft intent plan only adds proposed backend availability and
  lineage inside a `draft_only` wrapper. The inner plan remains validator-clean.
- Dashboard/Node14 surfaces pending `effect_recipe_patch.json` before raw
  revision requests.

Boundary: FX3b does not apply the draft to canonical input, does not call an
adapter, and does not render. A later increment must explicitly review/apply
the draft before any second BUILD.

## FX3c Reviewed Draft Apply + Second Render

Implemented as an explicit review gate after FX3b.

- New CLI: `python video_tools.py effect-revision-apply --draft revised_effect_intent_plan.draft.json --out effect_intent_plan.reviewed.json --reviewer REVIEWER --reason "accepted Node14 effect draft" --accept`
- New output shape: a validator-clean `effect_intent_plan` written to a separate
  reviewed path. It is no longer wrapped in `draft_only`.
- Required review fields: `--accept`, non-empty reviewer, and non-empty reason.
  Missing any of these fails closed.
- The original `effect_intent_plan.json` is never overwritten.
- E2E evidence extends the real ffmpeg effect test through:
  `effect_intent_plan_ref -> contract-run -> light_effects_baseline_review ->
  effect_revision_request -> revised_effect_intent_plan.draft -> reviewed plan
  -> second contract-run`.

Boundary: FX3c proves a reviewed plan can be consumed by canonical BUILD. It
does not implement the Remotion/Node14 adapter itself, and it does not silently
close adapter gaps. Any remaining external-effect gap stays visible until a
renderer/adapter increment handles it.

## FX4a/FX4b Remotion Prompt Adapter Foundation

Implemented as a bounded Brownfield/Node14 adapter contract, not a main BUILD
renderer.

- New CLI: `python video_tools.py remotion-prompt-pack --request effect_revision_request.json --effect-intent-plan effect_intent_plan.json --timeline timeline_build.json --out remotion_prompt_pack.json`
- New CLI: `python video_tools.py remotion-worker-outputs --prompt-pack remotion_prompt_pack.json --worker-outputs remotion_worker_outputs.json --out-review remotion_effect_review.json`
- New module: `video_pipeline_core/remotion_effects.py`.
- `remotion_prompt_pack.json` only converts
  `route_to_node14_or_remotion_adapter` requests into worker jobs. Ordinary
  ffmpeg recipe gaps remain FX3 recipe work.
- Each job carries prompt payload, source effect id, target timing, component
  family, output target hints, and acceptance criteria. Prompt is payload, not
  pipeline logic.
- `remotion_worker_outputs.json` is validated fail-closed: unknown job ids,
  missing preview/rendered files, duplicate jobs, malformed statuses, and bad
  durations are rejected.
- Valid outputs produce `remotion_effect_review.json` for Workbench/Brownfield
  review. They are not accepted into canonical delivery by validation alone.

Boundary: FX4a/FX4b does not run Remotion, does not install npm packages, does
not composite Remotion output into `final.mp4`, and does not make Remotion a
normal BUILD dependency. A later reviewed-asset/apply step must explicitly
promote accepted Remotion output before a second `contract-run` can consume it.

## Brownfield Edit Route Naming

Brownfield Edit is now the preferred route name for local patch work after a
candidate build exists. Node14 remains a legacy implementation node inside that
route.

The route accepts review gaps, Workbench patches, effect gaps, and incremental
effect asset / sfx / overlay additions. It returns draft or reviewed artifacts
for a second `contract-run`.

It must not rewrite the blueprint, silently overwrite canonical artifacts, or
use new story evidence material to satisfy coverage without material-map review.
