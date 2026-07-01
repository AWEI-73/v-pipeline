# Effect Factory Route

Date: 2026-06-25
Status: current side-branch design / integrates with main video route

Effect Factory is the designed-effects side branch for Hermes Video Pipeline.
It is peer-level with Material Map as a branch, but it has a different truth
boundary.

```text
Main Video Pipeline Route
  -> Material Map branch: proves material truth and coverage
  -> Effect Factory branch: designs, builds, reviews, and hands off effect assets
```

The main route remains `skills/video-pipeline-route.md`. It calls Material Map
when material truth is needed, and calls Effect Factory when a video segment,
review gap, or user request needs designed effects.

## What Effect Factory Owns

Effect Factory owns:

- effect intent clarification;
- design language mapping;
- `effect_design_map.json`;
- `effect_contract.json`;
- backend choice;
- worker handoff;
- effect output review;
- `effect_handoff.json` / `remotion_effect_handoff.json`.

It does not own:

- `final.mp4`;
- material truth;
- material coverage;
- story facts;
- official ffmpeg assembly.

## Branch Shape

```text
effect need / segment context
  -> effect intent clarification
  -> effect_design_map.json
  -> effect_contract.json
  -> backend handoff
      -> remotion-effect-worker, ffmpeg/light effect, or bounded probe
  -> effect_review.json
  -> effect_handoff.json
  -> Workbench / BUILD / Verify return point
```

`remotion-effect-worker.md` remains the lower Remotion backend. Effect Factory
does not absorb or replace it.

```text
video-effect-factory decides and contracts
remotion-effect-worker builds and reports
video-effect-factory reviews and hands off
```

## Trigger Points

### Brownfield / Material-First

Use Effect Factory when real material exists and needs designed finishing:

- opening title or hook;
- story-to-MV transition;
- chapter card;
- lower third or speaker label;
- emotional closing;
- photo wall / memory plate;
- highlight overlay;
- visual bridge between material groups.

The branch may use material refs from Material Map or Workbench review, but
those refs are evidence for design placement only. They do not prove material
coverage.

### Greenfield / Structure-First

Use Effect Factory only when the story needs an effect as a story device:

- lightning, impact, magic, sakura, hearts, fire/legacy, dream, map, portal;
- teaching diagram or necessary visual emphasis;
- title/transition that carries meaning rather than decoration.

Greenfield should not over-produce effects before script, timing, and material
needs are stable.

## Parameter Dictionary Boundary

Effect Factory uses style families as a reviewable parameter dictionary, not as
a fixed template library.

```text
fuzzy effect request
  -> semantic_slots: role / story function / tone / pacing / material relation
  -> remotion_capability_plan: layers / timing / transition / particle/text/image capabilities
  -> candidate style family and parameter options
  -> effect_build_spec when a supported worker component exists
  -> user/reviewer confirms or revises
  -> effect contract / prompt parameters
  -> bounded worker preview
```

Templates such as title cards, quote cards, or transition cards are only worker
carriers or reviewed samples. They must not become the creative source of truth.
Before worker handoff, unconfirmed candidate families should expose
`semantic_slots`, `remotion_capability_plan`, `visual_primitives`,
`motion_primitives`, `controls`, `negative_rules`, and `candidate_options` for
review.

`style_family` is a label for communication and reporting. The worker-facing
control surface is `effect_build_spec` inside existing `prompt_parameters` when
a supported component exists, or the visible primitives/capabilities when the
request is still exploratory.

The minimum information density for `remotion_capability_plan` is:

- `capabilities`: concrete backend capability names, not vibes;
- `primitives`: Remotion operating primitives such as `Sequence`,
  `TransitionSeries`, particle/text/image/light/camera layers;
- `remotion_api_refs`: API families the worker should reason with;
- `layers`: ordered visual layers, source ownership, and controlling params;
- `timing_controls`: duration, easing, fps conversion, impact moments, or
  transition overlap controls;
- `parameter_schema`: human-readable controls that can later become Zod props;
- `fallback_policy`: explicit behavior when a component is unsupported.

This mirrors OpenMontage's capability-contract idea while staying inside the
Hermes artifact route. Do not copy OpenMontage code; use it only as a reference
for capability density and tool-boundary clarity.

For non-hardened effects, emit a generic layer graph instead of inventing a new
template:

```json
{
  "component": "GenericRemotionEffect",
  "duration_sec": 5,
  "canvas": {"width": 1920, "height": 1080, "fps": 30},
  "layers": [
    {"id": "data_stream", "type": "glyph_stream", "params": {}},
    {"id": "title", "type": "text", "params": {}}
  ],
  "timing": {},
  "review_required": true
}
```

Only promote a repeated, reviewed `GenericRemotionEffect` graph into a named
template after visual evidence and review prove it is stable.

Use this CLI to create the reviewable parameter surface without worker handoff:

```powershell
python video_tools.py visual-technique-plan `
  --request "electric lightning opening with strong impact" `
  --effect-role opening_title `
  --duration-sec 6 `
  --out RUN_DIR\visual_technique_plan.json `
  --json
```

The same entrypoint also accepts Chinese semantic cues and maps them into the
same reviewable parameter surface. Examples:

- `動感閃電開場` -> `electric_lightning_energy`
- `地震裂動開場` -> `earthquake_crack_impact`
- `母親節愛心布景` -> `mothers_day_heart_stage`
- `日式可愛紙本故事開場` -> `japanese_soft_storybook`
- `回憶照片牆` -> `memory_photo_wall_warm`
- `故事轉到後半段 MV 蒙太奇` -> `story_to_mv_transition`
- `黑客資料流揭示` -> `terminal_data_reveal`
- `復古膠片燒灼轉場` -> `vintage_film_burn_transition`

Additional generic translator families:

- `ink spread / ink bloom / rice paper reveal` -> `ink_spread_reveal`
- `prism glass / glass refraction / crystalline split` -> `prism_glass_refraction`

These are not hardened templates. They should emit
`GenericRemotionEffect` layer graphs:

- ink: `mask_reveal`, `texture_overlay`, optional `light_overlay`, readable
  `text`;
- prism: `refraction`, `chromatic_split`, `mask_wipe`.

By default the result should say `handoff_to=review_candidate_parameters`.
Only pass `--confirmed` after user/reviewer acceptance; then it may become
`handoff_to=remotion_prompt_parameters`.

## Capability Review Gate

Before a confirmed effect is handed to a worker, write an
`effect_capability_review.json`. This is the Effect Factory equivalent of a
tool capability gate: it decides whether the requested effect can be built with
the bounded worker surface, should be previewed first, should be rerouted, or is
unsupported.

```powershell
python video_tools.py effect-capability-review `
  --request "electric lightning opening" `
  --effect-role opening_title `
  --duration-sec 4 `
  --out RUN_DIR\effect_capability_review.json
```

The artifact must be read before worker handoff:

- `decision=supported`: an explicit `effect_build_spec.layers[]` graph is
  supported and may be handed to `remotion-effect-worker`.
- `decision=partial`: semantic cues map to supported layers, but user/reviewer
  confirmation is still required.
- `decision=probe_required`: a bounded preview may be made, but not production
  handoff.
- `decision=reroute_material`: the request is new scene/material generation,
  not an overlay effect.
- `decision=reroute_editing`: the request belongs to Workbench/BUILD/audio or
  subtitle editing.
- `decision=unsupported`: the requested capability is outside the bounded
  Remotion worker surface.

Do not silently fall back from an unsupported required effect to a decorative
template. Either revise the effect request, downgrade it explicitly, or reroute
to material generation / editing.

Current generic worker layer types are:

```text
camera_motion, chromatic_split, crack_lines, electric_arcs, film_grain,
glyph_stream, image_layout, light_overlay, mask_reveal, mask_wipe,
particle_overlay, radial_current, refraction, text, texture_overlay
```

`image_layout` may use reviewed placement modes such as `center_logo`,
`full_bleed_hero`, or `hero_background` when the source refs are already
approved. `radial_current` is a generic outer-ring current / orbit / energy-flow
primitive for a reviewed focal image; it is not a named brand template. Keep the
request as a `GenericRemotionEffect` graph until visual review accepts the
result and the user explicitly asks to promote it.

This vocabulary is maintained in
`video_pipeline_core/effect_layer_manifest.py`; schema validation and worker
renderer-marker tests should use that manifest instead of duplicating lists.

## Dictionary Promotion

Reviewed generic graphs can be promoted into the Effect Factory dictionary, but
only after visual evidence exists. A probe result is not a template by itself.

```powershell
python video_tools.py effect-dictionary-promote `
  --request RUN_DIR\effect_dictionary_promotion_request.json `
  --dictionary RUN_DIR\effect_factory_dictionary.json `
  --out RUN_DIR\effect_factory_dictionary.updated.json
```

Promotion request requirements:

- `entry_id`, `display_name_zh`;
- `intent_tags[]` and `story_functions[]`;
- accepted `review` with non-empty `evidence_refs[]`;
- reviewed `effect_build_spec.component=GenericRemotionEffect`.

This keeps the factory extensible without freezing every successful one-off
probe into a hard-coded template.

For artifact-driven interaction, prefer writing a review artifact and applying
it:

```json
{
  "artifact_role": "visual_technique_review",
  "decision": "accept",
  "reviewer": "user",
  "selected_option": "balanced",
  "reason": "balanced is close enough for a short preview"
}
```

```powershell
python video_tools.py visual-technique-review-apply `
  --plan RUN_DIR\visual_technique_plan.json `
  --review RUN_DIR\visual_technique_review.json `
  --out RUN_DIR\visual_technique_plan.confirmed.json
```

`python tools\pipeline_home.py --run <RUN_DIR> --json` reads
`visual_technique_plan.json`: candidate plans route to
`effect_factory_parameter_review`; confirmed plans route to
`effect_factory_contract`. If `visual_technique_review.json` exists beside an
unconfirmed plan, it routes to `effect_factory_parameter_review_apply`.

## Artifact Contract

Minimum artifacts:

- `effect_design_map.json`
- `effect_contract.json`
- backend output, for example `remotion_worker_outputs.json`
- `effect_review.json`
- `effect_handoff.json` or `remotion_effect_handoff.json`

Boundary acceptance command:

```powershell
python tools\effect_factory_boundary_acceptance.py --out <RUN_DIR> --json
```

This no-render probe writes the contract artifacts plus
`remotion_prompt_pack.json`, `remotion_worker_outputs.json`,
`remotion_effect_review.json`, and
`effect_factory_boundary_acceptance_report.json`. A passing report means
semantic effect families can reach the existing Remotion worker/review handoff
without writing `final.mp4`; it does not prove final visual quality.

Route acceptance command:

```powershell
python tools\effect_factory_route_acceptance.py `
  --out <RUN_DIR> `
  --request "electric lightning opening with readable title" `
  --effect-role opening_title `
  --duration-sec 4 `
  --display-text "Opening" `
  --json
```

Use this when you need to prove the full Effect Factory handoff line:

```text
fuzzy semantic request
  -> visual_technique_plan.json
  -> visual_technique_plan.confirmed.json
  -> effect_capability_review.json
  -> effect_intent_plan.json
  -> effect_revision_request.json
  -> timeline_build.json
  -> remotion_prompt_pack.json
  -> remotion_worker_outputs.json
  -> remotion_effect_review.json
  -> effect_handoff.json
  -> effect_factory_route_acceptance_report.json
```

This is still a no-final-render acceptance. A passing report means the effect
request can be translated into supported worker parameters, dry-run worker
evidence, and a bounded handoff. It does not create `final.mp4`, does not prove
material truth, and still requires human visual review before promotion into a
real timeline.

`effect_contract.json` must include:

- `effect_id`
- `role`
- `effect_role`
- `style_family`
- `story_function`
- `display_text`
- `subtitle_text`
- `duration_sec`
- `visual_primitives`
- `motion_primitives`
- `controls`
- `negative_rules`
- `review_questions`
- `backend_policy`

## Backend Policy

Use Remotion when the effect needs:

- particles;
- typography motion;
- stylized opening plates;
- designed transitions;
- photo walls;
- short motion graphics;
- controlled visual primitives that are hard to express in ffmpeg.

Use ffmpeg/light effects when the effect is:

- simple fade;
- simple subtitle/lower third;
- simple overlay;
- color grade;
- deterministic low-cost finishing.

Use HTML/canvas only for exploration or a bounded probe before mainline
adoption. If it becomes useful, translate it into Effect Factory contract terms
instead of leaving it as a one-off.

## Review Gate

Review the output against the contract:

- intent match;
- family distinction;
- text readability and safe area;
- no mojibake or question marks;
- controls preserved;
- negative rules not violated;
- evidence exists: still, contact sheet, preview, or explicit skip reason.

Do not accept an effect just because a file exists.

## Handoff

The handoff must say:

- effect asset route is bounded;
- final assembly owner remains ffmpeg / `contract-run`;
- material truth owner remains Material Map;
- accepted assets and review evidence are listed;
- next action is human review, revise contract, rerun worker, or promote asset.

## Current Proof

The current alignment probe lives at:

```text
runs/remotion_alignment_opening_fx_20260625/
```

It tested one shared contract with two independent workers across:

- `electric_lightning_energy`
- `earthquake_crack_impact`
- `mothers_day_heart_stage`

The still-level result passed intent alignment. It is not production-motion
integration proof.
