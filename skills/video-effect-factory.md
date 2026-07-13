---
name: video-effect-factory
description: Use when the Hermes Video Pipeline needs designed video effects as a routed capability, including openings, transitions, title cards, lower thirds, emotional overlays, photo-wall treatments, lightning/crack/heart/sakura/fire visuals, or material-first finishing assets. It plans the effect design, writes contracts, calls remotion-effect-worker or lighter backends, reviews outputs, and hands off bounded effect assets without owning final.mp4.
---

# Video Effect Factory Skill

This is the upper route for designed effects in Hermes.

## Tool Contract

<!-- TOOL_CONTRACT_START -->
{
  "version": 1,
  "skill": "video-effect-factory",
  "stage_owner": "effect_factory_side_branch",
  "triggers": [
    "使用者要求開場、轉場、標題、字幕樣式、櫻花、火焰、閃電、愛心、照片牆等設計特效",
    "pipeline review 發現需要 bounded effect asset 或 Remotion worker handoff"
  ],
  "canonical_tools": [
    {
      "tool": "tools/visual_technique_plan.py",
      "when": "把模糊特效語意轉成可審查參數、primitives、controls 和候選選項",
      "inputs": [
        "effect phrase",
        "segment context",
        "optional review"
      ],
      "outputs": [
        "visual_technique_plan.json or confirmed plan"
      ],
      "stop_if": [
        "parameter_status=candidate_parameters and no review is supplied"
      ],
      "capability_id": "cap.video-effect-factory.visual-technique-plan.v1",
      "execution_class": "deterministic",
      "capability_role": "operation",
      "loops": [
        "L4"
      ],
      "maturity": "experimental"
    },
    {
      "tool": "python video_tools.py effect-design-concept",
      "when": "after fuzzy user-facing effect intent and before locking worker params; creates a design brief, multiple concepts, and a selected concept",
      "inputs": [
        "request",
        "effect_role",
        "duration_sec",
        "material_context"
      ],
      "outputs": [
        "effect_design_brief.json",
        "effect_concept_options.json",
        "effect_concept_selection.json"
      ],
      "stop_if": [
        "selected concept conflicts with material truth or requires unsupported renderer controls"
      ],
      "capability_id": "cap.video-effect-factory.effect-design-concept.v1",
      "execution_class": "deterministic",
      "capability_role": "operation",
      "loops": [
        "L4"
      ],
      "maturity": "experimental"
    },
    {
      "tool": "python video_tools.py effect-capability-review",
      "when": "before Remotion worker handoff, or when deciding whether an effect request is supported, partial, unsupported, or should be rerouted",
      "inputs": [
        "request/effect_role/duration/effect_build_spec"
      ],
      "outputs": [
        "effect_capability_review.json"
      ],
      "stop_if": [
        "decision is partial/probe_required/reroute_material/reroute_editing/unsupported"
      ],
      "capability_id": "cap.video-effect-factory.effect-capability-review.v1",
      "execution_class": "deterministic",
      "capability_role": "gate",
      "loops": [
        "L4"
      ],
      "maturity": "experimental"
    },
    {
      "tool": "python video_tools.py effect-design-review",
      "when": "after a playable preview/contact sheet exists; checks the rendered result against the selected concept",
      "inputs": [
        "effect_concept_selection.json",
        "render probe report"
      ],
      "outputs": [
        "effect_design_review.json"
      ],
      "stop_if": [
        "default/internal copy remains",
        "duration padding/drift",
        "missing playable preview",
        "presentation feel"
      ],
      "capability_id": "cap.video-effect-factory.effect-design-review.v1",
      "execution_class": "deterministic",
      "capability_role": "gate",
      "loops": [
        "L4"
      ],
      "maturity": "experimental"
    },
    {
      "tool": "python video_tools.py effect-dictionary-promote",
      "when": "after a GenericRemotionEffect preview has accepted review evidence and should become reusable",
      "inputs": [
        "promotion request with accepted review evidence",
        "effect_factory_dictionary.json"
      ],
      "outputs": [
        "updated effect_factory_dictionary.json"
      ],
      "stop_if": [
        "review evidence is missing or not accepted"
      ],
      "capability_id": "cap.video-effect-factory.effect-dictionary-promote.v1",
      "execution_class": "deterministic",
      "capability_role": "operation",
      "loops": [
        "L4"
      ],
      "maturity": "experimental"
    },
    {
      "tool": "tools/effect_factory_boundary_acceptance.py",
      "when": "驗證 Effect Factory 邊界與 handoff，不接管 final.mp4",
      "inputs": [
        "effect intent fixture or run folder"
      ],
      "outputs": [
        "effect_factory_boundary_acceptance_report.json"
      ],
      "stop_if": [
        "candidate parameters unconfirmed",
        "required effect lacks review evidence"
      ],
      "capability_id": "cap.video-effect-factory.effect-factory-boundary-acceptance.v1",
      "execution_class": "deterministic",
      "capability_role": "gate",
      "loops": [
        "L4"
      ],
      "maturity": "experimental"
    },
    {
      "tool": "tools/effect_factory_route_acceptance.py",
      "when": "prove the full semantic request -> visual technique -> capability review -> Remotion prompt pack -> worker review -> bounded handoff line without final render",
      "inputs": [
        "effect request",
        "effect_role",
        "duration_sec",
        "display_text"
      ],
      "outputs": [
        "effect_factory_route_acceptance_report.json"
      ],
      "stop_if": [
        "visual_technique_plan needs follow-up",
        "effect_capability_review is not supported",
        "remotion_effect_review evidence is missing"
      ],
      "capability_id": "cap.video-effect-factory.effect-factory-route-acceptance.v1",
      "execution_class": "deterministic",
      "capability_role": "gate",
      "loops": [
        "L4"
      ],
      "maturity": "experimental"
    }
  ],
  "supporting_tools": [
    {
      "tool": "tools/remotion_material_first_memory_acceptance.py",
      "when": "用 material-first refs 驗證 Remotion effect probe 或照片牆類素材輸入",
      "inputs": [
        "material refs",
        "effect build spec"
      ],
      "outputs": [
        "remotion material-first acceptance report"
      ],
      "stop_if": [
        "material refs are missing or unreviewed"
      ]
    },
    {
      "tool": "tools/remotion_transition_acceptance.py",
      "when": "驗證 bounded Remotion transition probe 是否符合 contract",
      "inputs": [
        "transition effect contract"
      ],
      "outputs": [
        "transition acceptance report"
      ],
      "stop_if": [
        "preview/contact sheet/evidence missing"
      ]
    },
    {
      "tool": "tools/gemini_demo_film.py",
      "when": "將外部 HTML/canvas demo 當 bounded reference probe，不作 canonical render",
      "inputs": [
        "demo spec or local html"
      ],
      "outputs": [
        "demo film/probe evidence"
      ],
      "stop_if": [
        "probe is mistaken for pipeline output"
      ]
    }
  ],
  "forbidden_tools": [
    "Do not replace remotion-effect-worker",
    "Do not silently collapse fuzzy effect intent into a fixed template",
    "Do not write final.mp4 from Effect Factory"
  ],
  "capability_namespace": "cap.video-effect-factory.*",
  "capability_lookup_owner": "video-effect-factory"
}
<!-- TOOL_CONTRACT_END -->

Shared hard boundary: read `skills/pipeline-boundary.md`. Stage 0 entry lock
must be resolved for whole-video requests. Do not direct-cut from a fuzzy
request; Effect Factory only handles a bounded effect need or reviewed route
handoff.

It does **not** replace `remotion-effect-worker.md`. The worker remains the
backend builder. Effect Factory owns design collection, contract shape, backend
choice, review, and handoff.

```text
effect need / segment context
  -> effect intent clarification
  -> effect_design_brief.json
  -> effect_concept_options.json
  -> effect_concept_selection.json
  -> effect_design_map.json
  -> effect_contract.json
  -> backend handoff, often remotion-effect-worker
  -> worker outputs / stills / contact sheets / preview assets
  -> effect_design_review.json
  -> effect_review.json
  -> effect_handoff.json
```

## Pipeline Position

The main route is still `skills/video-pipeline-route.md`.

Effect Factory is a side branch called by the main route when a segment or
review requires designed effects:

```text
Video Pipeline main route
  -> Material Map branch, when material truth is needed
  -> Effect Factory branch, when designed effect assets are needed
```

Use it in **brownfield/material-first** work when reviewed material needs
finishing:

- opening title or hook;
- story-to-MV transition;
- chapter card;
- lower third or speaker label;
- highlight overlay;
- emotional closing;
- photo wall, memory plate, or reviewed-material treatment.

Use it in **greenfield/structure-first** work only when the story needs an
effect as a story device:

- magic, lightning, sakura, fire/legacy, hearts, impact, dream, map, portal;
- teaching diagram or important visual emphasis;
- required transition from one narrative state to another.

If the effect is decorative and low value, prefer a light ffmpeg effect or skip
it.

## Boundaries

Effect Factory may:

- ask short clarification questions for fuzzy effect intent;
- create `effect_design_map.json` and `effect_contract.json`;
- choose backend: `remotion-effect-worker`, ffmpeg/light effects, or standalone
  HTML/canvas probe;
- request bounded worker previews, stills, contact sheets, or short effect
  assets;
- review worker outputs against the contract;
- write handoff artifacts for Workbench, dashboard, or final ffmpeg assembly.

Effect Factory must not:

- replace `remotion-effect-worker.md`;
- write or overwrite `final.mp4`;
- treat effect assets as material truth;
- approve material-map coverage;
- rewrite segment story facts;
- silently fall back to a generic template when a required effect cannot be
  built.

## Workflow

1. Clarify only route-changing effect intent:
   effect role, story function, tone, material context, intensity, duration.
2. Write `effect_design_map.json`.
3. Write `effect_contract.json` with:
   `effect_id`, `style_family`, `story_function`, `visual_primitives`,
   `motion_primitives`, `controls`, `negative_rules`, and `review_questions`.
4. Choose backend:
   - Remotion for particles, typography motion, stylized openings, transitions,
     photo walls, and short motion graphics.
   - ffmpeg/light effects for simple fades, subtitles, overlays, color grade, or
     deterministic low-cost finishing.
   - HTML/canvas only for bounded exploration before mainline adoption.
5. If Remotion is chosen, read `skills/remotion-effect-worker.md` and hand off
   to the worker route.
6. Review outputs against the contract, not vague taste.
7. Write `effect_handoff.json` or `remotion_effect_handoff.json`.
8. Register the handoff and review evidence in `artifact_manifest.json` using
   flat keys plus nested `artifacts.<key>.path` metadata. Unsupported required
   effects must leave a blocked route acceptance report, not a generic template
   handoff.

## Parameter Dictionary, Not Template Lock-In

Effect Factory may use style-family seeds as a dictionary for interaction, but
it must not silently turn a fuzzy request into a fixed template. The intended
flow is:

```text
fuzzy style request
  -> semantic_slots
  -> remotion_capability_plan
  -> candidate style family / parameter options
  -> visual_technique_plan.json
  -> visual_technique_review.json
  -> visual_technique_plan.confirmed.json
  -> user or reviewer confirms direction
  -> effect_build_spec when a supported worker component exists
  -> visible controls enter effect_contract / prompt_parameters
  -> worker preview
  -> review / revise
```

Templates are worker carriers or reviewed samples. They are not the creative
source of truth. If the user says "lightning", "heart", "Japanese", "legacy
fire", or another style, expose the proposed primitives and controls first:
`semantic_slots`, `remotion_capability_plan`, `visual_primitives`,
`motion_primitives`, `controls`, `negative_rules`, and `candidate_options`.
Do not send candidate parameters to a worker until the route has a confirmation,
a task packet explicitly authorizes a probe, or the effect is already hardened
by prior review evidence.

Treat `style_family` as a communication label, not the creative source of
truth. The practical translation target is Remotion capability language:
`Sequence`, `TransitionSeries`, particle/text/image/light layers,
`useCurrentFrame` timing, and worker-supported `effect_build_spec`.

The information density should be close to a capability contract, not a style
tag. A valid `remotion_capability_plan` should expose:

- backend `capabilities`;
- Remotion `primitives`;
- `remotion_api_refs`;
- ordered `layers` with source ownership and controlling params;
- `timing_controls`;
- `parameter_schema`;
- `fallback_policy`;
- `review_evidence_required`.

Use OpenMontage only as an architectural reference for capability menus,
registry-like clarity, and stage/tool boundaries. Do not copy code from it.

For effects that are not hardened components, translate into
`effect_build_spec.component=GenericRemotionEffect` with a layer graph. This is
the current generic translator path. Do not create a new named template just
because a probe looks good. Templates are promoted later from reviewed,
repeatable layer graphs.

Before handing a confirmed generic graph to `remotion-effect-worker`, write an
`effect_capability_review.json`:

```powershell
python video_tools.py effect-capability-review `
  --input RUN_DIR\effect_request.json `
  --out RUN_DIR\effect_capability_review.json
```

Only `decision=supported` may enter worker handoff without another review step.
`partial` and `probe_required` stop for confirmation/probe evidence.
`reroute_material` belongs to material generation or story route.
`reroute_editing` belongs to Workbench/BUILD/audio/subtitle routes.
`unsupported` must be revised instead of silently mapped to a decorative
template.

Current generic layer vocabulary:

```text
camera_motion, chromatic_split, crack_lines, electric_arcs, film_grain,
glyph_stream, image_layout, light_overlay, mask_reveal, mask_wipe,
particle_overlay, radial_current, refraction, text, texture_overlay
```

Common parameterized, non-template uses:

- `image_layout.layout=center_logo` for a reviewed logo or mark.
- `image_layout.layout=full_bleed_hero` / `hero_background` for a reviewed
  generated or source hero plate with explicit fade timing.
- `radial_current` for outer-ring current, orbit, or energy-flow accents around
  a reviewed focal image.

Do not promote these into a fixed template unless the user explicitly asks to
solidify a reviewed result into the dictionary.

If a preview is accepted and should become reusable, promote it through:

```powershell
python video_tools.py effect-dictionary-promote `
  --request RUN_DIR\effect_dictionary_promotion_request.json `
  --dictionary RUN_DIR\effect_factory_dictionary.json `
  --out RUN_DIR\effect_factory_dictionary.updated.json
```

Promotion requires accepted review evidence and a reviewed
`GenericRemotionEffect` layer graph.

Use `visual-technique-review-apply` to turn reviewed candidate parameters into
a confirmed plan. The presence of `visual_technique_review.json` means "apply
the review", not "send to worker directly". The worker only receives
`visual_technique_plan.confirmed.json` or an explicitly probe-authorized packet.

For a repeatable no-render route check from natural-language effect intent to
worker handoff, use:

```powershell
python tools/effect_factory_route_acceptance.py `
  --out RUN_DIR `
  --request "electric lightning opening with readable title" `
  --effect-role opening_title `
  --duration-sec 4 `
  --json
```

This writes `effect_factory_route_acceptance_report.json` and the intermediate
artifacts from `visual_technique_plan.json` through `effect_handoff.json`. It is
the preferred smoke test when verifying that Effect Factory can translate a
semantic request into supported Remotion worker parameters without producing
`final.mp4`.

The route proof must also update `artifact_manifest.json`. A supported route
records `effect_handoff` with `owner=effect_factory` and accepted status. An
unsupported route records a blocked `effect_factory_route_acceptance_report`
and must not create `effect_handoff.json`.

## Canonical Artifacts

### `visual_technique_plan.json`

```json
{
  "artifact_role": "visual_technique_plan",
  "version": 1,
  "style_family": "electric_lightning_energy",
  "effect_role": "opening_title",
  "handoff_to": "review_candidate_parameters",
  "parameter_status": "candidate_parameters",
  "visual_primitives": ["branching_lightning_arcs"],
  "motion_primitives": ["arc_strike"],
  "controls": {"strike_count": 4},
  "candidate_options": [
    {"option_id": "restrained"},
    {"option_id": "balanced"},
    {"option_id": "expressive"}
  ]
}
```

### `visual_technique_review.json`

```json
{
  "artifact_role": "visual_technique_review",
  "decision": "accept",
  "reviewer": "user",
  "selected_option": "balanced",
  "reason": "balanced for preview",
  "control_overrides": {}
}
```

Apply it:

```powershell
python video_tools.py visual-technique-review-apply `
  --plan RUN_DIR\visual_technique_plan.json `
  --review RUN_DIR\visual_technique_review.json `
  --out RUN_DIR\visual_technique_plan.confirmed.json
```

### `effect_design_map.json`

```json
{
  "artifact_role": "effect_design_map",
  "version": 1,
  "route": "effect-factory",
  "source_context": {
    "video_route": "material-first | structure-first | hybrid | standalone_probe",
    "segment_ids": [],
    "material_refs": [],
    "user_intent": ""
  },
  "design_families": [
    {
      "style_family": "electric_lightning_energy",
      "status": "candidate | reviewed | hardened",
      "communicates": "momentum / sharp start / urgency",
      "best_roles": ["opening_title", "transition", "montage_hit"],
      "avoid_when": ["soft memorial", "formal documentary"]
    }
  ],
  "followup_questions": [],
  "assumptions": []
}
```

### `effect_contract.json`

```json
{
  "artifact_role": "effect_contract",
  "version": 1,
  "effects": [
    {
      "effect_id": "fx_opening_lightning_01",
      "role": "title_card",
      "effect_role": "opening_title",
      "style_family": "electric_lightning_energy",
      "story_function": "high-impact opening that signals momentum",
      "display_text": "開場啟動",
      "subtitle_text": "把能量集中到第一秒",
      "tone": "powerful, sharp, energetic, controlled",
      "duration_sec": 6,
      "visual_primitives": ["branching_lightning_arcs", "electric_blue_glow"],
      "motion_primitives": ["arc_strike", "micro_jitter", "flash_reveal"],
      "controls": {
        "strike_count": 4,
        "flash_intensity": "high",
        "title_reveal_frame": 54
      },
      "negative_rules": ["no horror tone", "no unreadable strobe"],
      "review_questions": ["Are lightning arcs visible?", "Is text readable?"],
      "backend_policy": {
        "preferred": "remotion-effect-worker",
        "fallback": "explicit_degraded_or_ask_followup"
      }
    }
  ]
}
```

### `effect_review.json`

```json
{
  "artifact_role": "effect_review",
  "version": 1,
  "status": "pass | revise | fail",
  "reviewed_effects": [
    {
      "effect_id": "fx_opening_lightning_01",
      "intent_match": "pass | revise | fail",
      "visual_distinction": "pass | revise | fail",
      "text_readability": "pass | revise | fail",
      "controls_preserved": "pass | revise | fail",
      "negative_rules": "pass | revise | fail",
      "evidence_refs": []
    }
  ],
  "blocking_issues": [],
  "next_action": "handoff | revise_contract | rerun_worker | ask_user"
}
```

### `effect_handoff.json`

```json
{
  "artifact_role": "effect_handoff",
  "version": 1,
  "status": "ready_for_human_review | ready_for_pipeline_promotion | blocked",
  "boundary": {
    "role": "bounded_effect_asset_route",
    "owns_final_delivery": false,
    "owns_material_truth": false,
    "final_assembly_owner": "ffmpeg_contract_run"
  },
  "accepted_assets": [],
  "review_evidence": [],
  "next_action": "human_review_or_promote_effect_assets_to_timeline"
}
```

## Style Family Seeds

These are starting points. Mark new families as `candidate` until reviewed.

- `electric_lightning_energy`: branching lightning, electric glow, flash reveal,
  snap scale, micro jitter.
- `earthquake_crack_impact`: surface cracks, dust burst, impact shadow,
  title settle, low-frequency pulse.
- `mothers_day_heart_stage`: heart bokeh, pink/gold gradient, ribbon sweep,
  petal drift, gentle glow.
- `japanese_soft_storybook`: paper texture, rounded ink lines, pastel wash,
  gentle parallax, soft character/title plate.
- `japanese_sakura`: sakura petals, soft bloom, parallax drift, slow reveal.
- `warm_legacy_fire`: soft embers, afterglow, dimmed group photo, long fade,
  restrained emotional closure.
- `terminal_data_reveal`: generated terminal glyph stream, scanlines, cursor
  blink, title assembly, readability guard.
- `vintage_film_burn_transition`: burn mask wipe, light leak edge, film grain,
  gate weave, memory-to-truth reveal.
- `ink_spread_reveal`: ink bloom mask, paper fiber texture, feathered organic
  reveal, readable title after ink settles.
- `prism_glass_refraction`: prism planes, spectral split, refraction sweep,
  chromatic settle, clip-path transition wipe.

Readable Chinese semantic cues should route through the same dictionary before
worker handoff:

- `動感閃電` -> `electric_lightning_energy`
- `地震裂動` -> `earthquake_crack_impact`
- `母親節愛心` -> `mothers_day_heart_stage`
- `日式可愛紙本` -> `japanese_soft_storybook`
- `回憶照片牆` -> `memory_photo_wall_warm`
- `故事轉 MV / 故事轉蒙太奇` -> `story_to_mv_transition`
- `黑客資料流 / 終端機資料揭示` -> `terminal_data_reveal`
- `復古膠片燒灼 / film burn` -> `vintage_film_burn_transition`

Additional readable English cues:

- `ink spread / ink bloom / rice paper reveal` -> `ink_spread_reveal`
- `prism glass / glass refraction / crystalline split` -> `prism_glass_refraction`

For `ink_spread_reveal` and `prism_glass_refraction`, do not invent a named
template. Keep them as `GenericRemotionEffect` layer graphs until visual review
proves a repeated graph should be promoted:

- ink graph: `mask_reveal`, `texture_overlay`, optional `light_overlay`,
  readable `text`;
- prism graph: `refraction`, `chromatic_split`, `mask_wipe`.

These cues only select candidate parameters. They do not authorize a worker run
until `visual_technique_review.json`, `--confirmed`, or an explicit bounded
probe packet confirms the direction.

## Review Checklist

Before claiming the branch is ready:

- effect has a clear `story_function`;
- `style_family` is explicit;
- visual and motion primitives are concrete;
- controls include duration and important strength/count/timing parameters;
- negative rules prevent the obvious wrong direction;
- worker output preserves IDs and text;
- Chinese text is not mojibake and not replaced with question marks;
- evidence exists: still, contact sheet, preview, or explicit skip reason;
- different families do not collapse into one generic template;
- handoff says bounded/non-final and names the final assembly owner.
