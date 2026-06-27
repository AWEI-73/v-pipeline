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
  -> candidate style family and parameter options
  -> user/reviewer confirms or revises
  -> effect contract / prompt parameters
  -> bounded worker preview
```

Templates such as title cards, quote cards, or transition cards are only worker
carriers or reviewed samples. They must not become the creative source of truth.
Before worker handoff, unconfirmed candidate families should expose
`visual_primitives`, `motion_primitives`, `controls`, `negative_rules`, and
`candidate_options` for review.

Use this CLI to create the reviewable parameter surface without worker handoff:

```powershell
python video_tools.py visual-technique-plan `
  --request "electric lightning opening with strong impact" `
  --effect-role opening_title `
  --duration-sec 6 `
  --out RUN_DIR\visual_technique_plan.json `
  --json
```

By default the result should say `handoff_to=review_candidate_parameters`.
Only pass `--confirmed` after user/reviewer acceptance; then it may become
`handoff_to=remotion_prompt_parameters`.

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
