---
name: remotion-effect-worker
description: Bounded Remotion effect worker for Hermes Video Pipeline. Use for Brownfield/finishing title intros, chapter transitions, lower thirds, and highlight overlays when ffmpeg/light effects are insufficient. The worker consumes existing Hermes effect route artifacts, writes Remotion worker outputs and review evidence, and never owns final.mp4, material-map decisions, rough-cut selection, or segment_contract rewriting.
---

# Remotion Effect Worker

This skill defines how a Remotion-capable worker plugs into the existing Hermes effect route. Remotion is an effect asset producer, not the main renderer. Final assembly remains owned by ffmpeg / `contract-run`.

## Mainline Contract

Use the existing route whenever possible:

```text
effect_intent_plan.json
-> light_effects_plan.json
-> light_effects_baseline_review.json
-> effect_revision_request.json
-> remotion_prompt_pack.json
-> remotion_worker_outputs.json
-> remotion_effect_review.json
-> optional remotion_composite_draft.mp4
-> reviewed artifact
-> ffmpeg / contract-run final assembly
```

Existing commands:

```powershell
python video_tools.py remotion-prompt-pack ...
python video_tools.py remotion-worker-smoke --dry-run ...
python video_tools.py remotion-worker-outputs ...
python video_tools.py remotion-composite-draft ...
```

The worker should normally start from `remotion_prompt_pack.json`. It should not invent a parallel route unless explicitly asked to run a standalone probe.

## Worker Role

The worker may:

- render short Remotion clips or overlays;
- write `remotion_worker_outputs.json`;
- produce preview files, rendered effect assets, and contact sheets;
- support Workbench/material-map review by providing evidence;
- help produce `effect_render_verification.json` when the route promotes Remotion output into required effect evidence.

The worker must not:

- modify `segment_contract.json`;
- modify material-map artifacts;
- select source footage;
- rewrite rough-cut or timeline ownership;
- write or overwrite `final.mp4`;
- treat effect assets as factual material evidence.

## Supported Effect Families

Initial supported effect families:

- `title_intro`
- `chapter_transition`
- `lower_third`
- `highlight_overlay`

Map these from existing Remotion prompt-pack component families when possible:

| Prompt-pack family | Worker family |
| --- | --- |
| `title_reveal` | `title_intro` |
| `page_turn_transition` | `chapter_transition` |
| `lower_third_motion` | `lower_third` |
| `overlay_motion` | `highlight_overlay` |
| `light_leak_overlay` | `highlight_overlay` |
| `speed_line_overlay` | `highlight_overlay` |

Unsupported component families should return a failed worker output with a clear reason instead of creating arbitrary full-scene logic.

## Template Dictionary

Before inventing effect wording, check the reusable template dictionary:

```text
examples/training_recap_effect_dictionary.json
```

This dictionary records reviewed training-recap treatments as stable `template_id` values. Upstream stages should prefer a template when the requested look matches an existing treatment. The prompt-pack builder merges template defaults into `props.presentation`, while explicit effect-level `presentation` values still override the template.

Also check the capability manifest before claiming a template is supported:

```text
examples/remotion_effect_capability_manifest.json
```

The manifest records concrete worker support, reference-review evidence, and
known verify caveats. For the current 67th training recap reference, the visual
audit evidence passes, but the black-frame audit flags three short black
intervals. Treat those as transition plates that must be formalized or fixed in
delivery, not as silent pass evidence.

Currently useful training-recap template ids:

| template_id | Use |
| --- | --- |
| `training_opening_title` | Black collage opening plate, large yellow title, optional subtitle. |
| `module_label_white_blue` | Clean white/blue course or chapter label. |
| `speaker_subtitle_yellow_bar` | Readable speaker subtitle bar. |
| `soft_light_transition` | Short warm chapter transition. |
| `highlight_warm_glow` | Warm highlight overlay for memory moments. |
| `blurred_side_fill` | Vertical/low-resolution footage side fill. |
| `profile_memory_card` | Individual/team memory card. |
| `memory_photo_wall` | Slow reviewed-material wall for material-first recap openings. |
| `film_strip_transition_card` | Story-to-MV or montage transition card. |
| `clean_white_quote_card` | Simple reflection or closing quote card. |

The current worker bridge has concrete renderer support for
`training_opening_title`, `module_label_white_blue`,
`speaker_subtitle_yellow_bar`, `soft_light_transition`,
`highlight_warm_glow`, `blurred_side_fill`, `profile_memory_card`,
`film_strip_transition_card`, `clean_white_quote_card`, and `memory_photo_wall`.

## Prompt Parameter Contract

For high-value Remotion effects, do not rely only on free-form wording such as
"commercial", "MV", or "make it stronger". Prefer structured
`prompt_parameters` in `effect_intent_plan.effects[]`. The prompt-pack builder
preserves this object into `remotion_prompt_pack.jobs[].props.prompt_parameters`,
and the worker bridge exposes it as `JOB.promptParameters`.

Canonical contract and examples:

```text
docs/remotion_prompt_parameter_contract.md
examples/remotion_prompt_params_training_opening_title.json
examples/remotion_prompt_params_story_to_mv_transition.json
```

Currently hardened parameter contracts:

- `training_opening_title`: formal training opening, reviewed people/group hero
  strategy, collage reveal, title sweep, face-preservation rules.
- `film_strip_transition_card` with `story_to_mv_film_transition`: story-to-MV
  section change, impact strength, film rail, thumbnail acceleration, midpoint
  impact, and static-card avoidance rules.
- `MemoryPhotoWall` via `effect_build_spec`: slow material-first memory wall
  driven by reviewed refs, pacing, density, reveal mode, camera motion, and
  accent light.

For v1, keep `effect_build_spec` inside existing `prompt_parameters`. Do not add `effect_story_planner.json` or a parallel Remotion planning chain unless the mainline contract has already proven too cramped. The worker role is to consume the current prompt-pack control surface, not to introduce a new upstream route.

If `prompt_parameters` conflict with material-map or Workbench review, material
review wins. These parameters shape effect presentation; they do not approve
material content.

When upstream effects omit `template_id`, `remotion-prompt-pack` applies a
conservative template policy for common training-recap cases:

- speaker lower thirds -> `speaker_subtitle_yellow_bar`
- non-speaker lower thirds -> `module_label_white_blue`
- story/MV/montage transitions -> `film_strip_transition_card`
- explicit soft/warm light transitions -> `soft_light_transition`
- vertical/side-fill panel frames -> `blurred_side_fill`
- warm/key-moment overlays -> `highlight_warm_glow`
- opening/collage title cards -> `training_opening_title`
- profile/team/memory cards -> `profile_memory_card`
- quote/closing/reflection cards -> `clean_white_quote_card`

Explicit `template_id` always wins. Inferred templates are recorded in job
`diagnostics` as `template_inferred:<template_id>` so Workbench review can tell
whether a choice was specified or policy-derived.

Example effect intent:

```json
{
  "effect_id": "fx_intro_01",
  "role": "title_card",
  "template_id": "training_opening_title",
  "display_text": "67TH TRAINING",
  "subtitle_text": "ON THE LAST PAGE",
  "collage_media_refs": [
    {"ref_id": "opening_01", "path": "file:///C:/path/opening_01.jpg", "label": "集合"},
    {"ref_id": "training_01", "path": "file:///C:/path/training_01.jpg", "label": "訓練"}
  ],
  "intensity": "high",
  "visual_language": ["black collage", "yellow title", "memory recap"]
}
```

For `speaker_subtitle_yellow_bar`, use `display_text` for the spoken line and
`speaker_name` for the optional speaker tag:

```json
{
  "effect_id": "fx_speaker_01",
  "role": "lower_third",
  "template_id": "speaker_subtitle_yellow_bar",
  "display_text": "保持初心，繼續前進。",
  "speaker_name": "主任",
  "intensity": "low",
  "visual_language": ["yellow subtitle bar", "speaker remarks", "readable"]
}
```

`collage_media_refs` should come from material-map or Workbench-reviewed stills,
not from arbitrary unreviewed media. If no refs are available, the worker may use
placeholder collage frames, but the review note must say so.

For material-first projects with mostly video, prefer reviewed keyframes from
`material_wall_request.json`. `MemoryPhotoWall` may receive refs through
`effect_build_spec.material_refs`; the worker bridge uses those refs when
`collage_media_refs` is empty. These refs are review evidence, not proof that
the full source clip is selected for final assembly.

To build refs from reviewed material artifacts, use:

```powershell
python video_tools.py effect-collage-refs `
  --project-map project_material_map.json `
  --wall-verdict material_wall_review_verdict.json `
  --wall-request verify/material_wall/material_wall_request.json `
  --workbench-thumbnails workbench_thumbnails.json `
  --out effect_collage_media_refs.json
```

Refs sourced from material-wall video keyframes should carry
`evidence_kind=material_wall_keyframe`.

Then pass it into prompt-pack:

```powershell
python video_tools.py remotion-prompt-pack `
  --request effect_revision_request.json `
  --effect-intent-plan effect_intent_plan.json `
  --collage-refs effect_collage_media_refs.json `
  --out remotion_prompt_pack.json
```

The prompt-pack builder injects refs into `training_opening_title` only when the
effect does not already carry explicit `collage_media_refs`. The command only
converts reviewed still/thumbnail evidence; it does not extract frames, approve
material truth, or modify the material map.

For a repeatable material-first MemoryPhotoWall boundary check, use:

```powershell
python tools/remotion_material_first_memory_acceptance.py `
  --run-dir runs/remotion_material_first_memory_acceptance/<timestamp> `
  --project-map project_material_map.json `
  --wall-verdict material_wall_review_verdict.json `
  --wall-request verify/material_wall/material_wall_request.json `
  --json
```

This writes `remotion_material_first_memory_acceptance_report.json` plus the
prompt-pack, worker-output, review, `remotion_visual_probe.html`,
`remotion_contact_sheet.svg`, and `effect_render_verification.json` artifacts.
A passed report means the material-first Remotion effect boundary is ready for
human effect review or pipeline promotion; it is **not final delivery** and must
not be treated as `final.mp4` verification.

## Input Priority

Prefer inputs in this order:

1. `remotion_prompt_pack.json`
2. `effect_revision_request.json` + `effect_intent_plan.json`
3. `effect_intent_plan.json` for standalone probes only
4. `segment_contract.json` / `timeline_build.json` as read-only timing context only

## Output Contract

For each prompt-pack job, write a matching worker output:

```json
{
  "job_id": "rm_fx_intro_01",
  "source_effect_id": "fx_intro_01",
  "status": "rendered",
  "preview_file": "remotion_effects/rm_fx_intro_01.preview.mp4",
  "rendered_asset": "remotion_effects/rm_fx_intro_01.mov",
  "duration_sec": 4.0,
  "backend": "remotion",
  "evidence_refs": ["remotion_effects/rm_fx_intro_01_contact_sheet.jpg"]
}
```

The full artifact:

```json
{
  "artifact_role": "remotion_worker_outputs",
  "version": 1,
  "status": "rendered",
  "summary": {
    "job_count": 1,
    "rendered_count": 1,
    "failed_count": 0
  },
  "jobs": []
}
```

Then run or hand off to `remotion-worker-outputs` validation so Hermes can produce `remotion_effect_review.json`.

## Optional Probe Packet

`remotion_effect_packet.json` is allowed only for isolated proof-of-concept runs or future light wrappers. It is not currently the mainline Hermes schema. If a packet is used, also create a compatible `remotion_worker_outputs.json` or clearly state that the result is a standalone probe.

## Rendering Rules

- Render only short effect assets.
- Default to 1920x1080, 30 fps.
- Title intros: 3-6 seconds.
- Chapter transitions: 1-2 seconds.
- Lower thirds: 3-6 seconds.
- Highlight overlays: 1-5 seconds.
- Use frame-driven Remotion animation with `useCurrentFrame()` and `interpolate()`.
- Do not use CSS transitions or CSS animations.
- Keep text inside safe areas.
- Do not obscure proof footage when `must_preserve_proof=true`.

## Review And Gate Rules

Every rendered effect needs evidence:

- preview clip;
- rendered asset;
- contact sheet or keyframe image;
- duration;
- matching `job_id`.

Required story effects must not silently disappear. If a required effect fails, report a failed job and a clear `next_action`. Decorative effects may fall back, but the fallback must be explicit.

The worker does not decide delivery pass/fail. It produces reviewable artifacts so Workbench, material-map review, and delivery gates can decide.

## Minimal Acceptance

A successful bounded worker run has:

- `remotion_prompt_pack.json` or a clearly marked standalone packet;
- rendered short effect files;
- contact-sheet evidence;
- `remotion_worker_outputs.json`;
- `remotion_effect_review.json` after validation, or a clear instruction to run validation;
- no changes to `final.mp4`.
