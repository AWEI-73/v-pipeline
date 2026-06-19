# Brownfield Edit Route

Brownfield Edit is the fast local patch route for an existing pipeline result.
Use it after a draft/final candidate, Workbench patch, VERIFY gap, or effect gap
already exists. It is not the canonical story/material pipeline.

## Purpose

Turn a local problem into a reviewed artifact that can be consumed by a second
`contract-run`.

Typical inputs:

- Workbench draft patches (`timeline_patch.json`, `subtitle_patch.json`,
  `audio_cue_patch.json`, `effect_patch.json`)
- `light_effects_baseline_review.json`
- `effect_revision_request.json`
- `effect_recipe_patch.json`
- local effect asset / sfx / overlay additions

Typical outputs:

- non-canonical preview render from a draft
- draft patch artifact
- reviewed artifact
- second `contract-run` handoff
- Remotion prompt pack / worker-output review artifact for prompt-driven effects

## Hard Boundaries

- do not rewrite the blueprint.
- Do not rewrite the story contract wholesale.
- Do not overwrite canonical artifacts directly.
- Do not claim browser preview equals final render.
- Do not use Brownfield as a backdoor to satisfy story evidence material.
- Do not mark a `material_need` covered from a new story asset unless it goes
  through material-map review and receives a reviewed `satisfies` edge.

## Asset Addition Rule

Brownfield may handle incremental assets only when they are local finishing
assets:

- effect asset / sfx / overlay
- transition plate
- title texture
- lower-third plate
- light leak or particle overlay

These assets may be imported as effect assets or referenced by effect patches.
They are not real-event evidence and must not satisfy material-map coverage.

If the added asset is story evidence material, route it through the material-map
lifecycle instead:

```text
new story asset
-> material-map import / review
-> satisfies edge
-> fresh material delta
-> BUILD handoff
```

## Route

```text
VERIFY gap / Workbench patch / effect gap
-> Brownfield request
-> draft patch
-> optional incremental effect-asset import
-> reviewed artifact
-> second contract-run
-> VERIFY again
```

The route is fast because it is local and bounded. It is not fast because it
skips review.

## Current Tool Mapping

- Workbench draft validation: `workbench-handoff-validate`
- Workbench non-canonical preview: `workbench-draft-rerender`
- Effect gap request: `effect-revision-request`
- Effect draft patch: `effect-revision-draft`
- Reviewed apply: `effect-revision-apply`
- Remotion prompt jobs for adapter-route effect gaps: `remotion-prompt-pack`
- Remotion worker-output validation for Workbench review:
  `remotion-worker-outputs`

Node14 remains a legacy implementation node inside Brownfield Edit. Treat
`effect_revision_request.json` and `effect_recipe_patch.json` as compatible
Brownfield artifacts, not as a separate main pipeline.

## Remotion Prompt-Driven Effects

Use Remotion inside Brownfield only after an effect gap exists or a user asks
for a finishing effect that the ffmpeg-safe route cannot express.

```text
effect_revision_request.json
-> remotion_prompt_pack.json
-> Remotion-capable worker writes remotion_worker_outputs.json + media files
-> remotion_effect_review.json
-> Workbench / human review
-> reviewed artifact
-> second contract-run / ffmpeg composite
```

Rules:

- Prompt is payload, not pipeline logic.
- Do not run Remotion during normal BUILD.
- Do not accept Remotion output into canonical delivery without review.
- Do not use Remotion output as story material evidence.
