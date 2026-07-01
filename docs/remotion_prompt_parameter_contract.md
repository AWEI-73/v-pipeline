# Remotion Prompt Parameter Contract

This document defines the first stable prompt-parameter contract for Remotion
effect workers in Hermes Video Pipeline. The goal is not to hand-code one final
effect. The goal is to make prompt intent structured enough that another worker
can produce consistent, reviewable Remotion assets.

Remotion remains a bounded effect asset producer. Final assembly still belongs to
ffmpeg / contract-run.

## Artifact Surface

`effect_intent_plan.effects[]` may include:

```json
{
  "prompt_parameters": {}
}
```

`remotion-prompt-pack` must preserve that object into:

```json
{
  "jobs": [
    {
      "props": {
        "prompt_parameters": {}
      }
    }
  ]
}
```

`tools/remotion_worker_bridge.mjs` must expose it as:

```js
JOB.promptParameters
```

The worker may read these fields to choose motion grammar, timing emphasis, and
material treatment. The worker must not treat them as material truth.

## Worker-Consumed Fields

The current Remotion worker bridge consumes these fields directly:

| Template | Field | Current behavior |
| --- | --- | --- |
| `memory_photo_wall` / `MemoryPhotoWall` | `effect_build_spec.material_refs[]` | Uses reviewed material-first stills or material-wall keyframes as the photo wall inputs when `collage_media_refs` is empty. |
| `memory_photo_wall` / `MemoryPhotoWall` | `effect_build_spec.story_function` | Carries the story purpose, such as material-first recap openings or emotional setup, into worker review. |
| `memory_photo_wall` / `MemoryPhotoWall` | `effect_build_spec.pacing`, `density`, `reveal_mode`, `camera_motion`, `accent_light` | Controls reveal timing, visual density, one-by-one/cascade/full-plate progression, gentle camera movement, and restrained accent light. |
| `training_opening_title` | `material_strategy.hero_source = reviewed_people_group` | Prefers `collage_media_refs` with `visual_role = people_group` as early hero/collage candidates. |
| `training_opening_title` | `material_strategy.avoid_hero_roles[]` | Demotes refs whose `visual_role` is listed, especially `title_card`, when choosing early hero/collage candidates. |
| `film_strip_transition_card` | `transition_strength = soft / medium / impact` | Scales thumbnail acceleration, midpoint flash, and hard-cut impact bars. |
| `training_opening_title` | `motion_grammar[]` | Controls opening layer flags listed in the controlled enum below. |
| `film_strip_transition_card` | `motion_grammar[]` | Controls transition layer flags listed in the controlled enum below. |

Fields not listed here are still preserved for review and future worker routing,
but should not be claimed as rendered behavior yet.

## Shared Fields

Use these fields across Remotion effect templates:

| Field | Type | Purpose |
| --- | --- | --- |
| `effect_goal` | string | What this effect must communicate. |
| `tone` | string[] | Emotional and editorial tone. |
| `motion_grammar` | string[] | Concrete motion verbs the worker can implement. |
| `material_strategy` | object | Which reviewed material may be used and how. |
| `text_hierarchy` | object | Which text is primary or secondary. |
| `negative_rules` | string[] | Things the worker must avoid. |

Prefer controlled terms over prose. Free-form prose may still appear in
`intent`, `prompt`, or `visual_language`, but it should not be the only source of
truth.

## Effect Build Spec

`effect_build_spec` is the preferred v1 control surface for component-level
Remotion behavior. It lives inside `prompt_parameters` so the current route
stays intact:

```json
{
  "prompt_parameters": {
    "effect_build_spec": {
      "component": "MemoryPhotoWall",
      "duration_sec": 10,
      "story_function": "emotional_setup",
      "pacing": "slow",
      "density": "low",
      "reveal_mode": "one_by_one",
      "camera_motion": "slow_push_in",
      "caption_mode": "minimal",
      "accent_light": "soft_warm",
      "material_refs": []
    }
  }
}
```

The current supported build-spec components are:

- `MemoryPhotoWall` for slow reviewed-material photo walls and material-first recap openings.
- `StoryToMVTransition` for a story-to-MV / montage section shift.
- `GenericRemotionEffect` for reviewed generic layer graphs when the request
  does not deserve a named template yet.

Reusable neutral fields are `story_function`, `pacing`, `density`,
`reveal_mode`, `camera_motion`, and `accent_light`. Component-specific fields
may extend these only after the neutral story purpose is clear.

Unsupported component names must fail closed instead of becoming generic motion
templates.

### GenericRemotionEffect Layer API

`GenericRemotionEffect` is a layer graph, not a template name. It is for
bounded probes and reviewed reusable effects. The worker bridge currently
understands these layer types:

| Layer type | Purpose |
| --- | --- |
| `text` | Main title/subtitle typography. |
| `image_layout` | Reviewed image/photo placement. |
| `particle_overlay` | Sparks, dust, petals, embers, or other simple particles. |
| `light_overlay` | Glow, wash, flare, or accent light plates. |
| `camera_motion` | Bounded scale/shake/drift applied to the effect layer group. |
| `mask_reveal` | Ink/organic/simple reveal mask. |
| `mask_wipe` | Plane wipe, burn edge, or transition mask. |
| `texture_overlay` | Paper, grain, scanline, or simple material texture. |
| `refraction` | Prism/glass plane treatment. |
| `chromatic_split` | RGB/spectral split treatment. |
| `glyph_stream` | Terminal/data-stream rows. |
| `film_grain` | Film grain / gate texture. |
| `electric_arcs` | Stylized lightning/electric arc paths. |
| `crack_lines` | Stylized impact/crack line paths. |
| `radial_current` | Outer-ring current, orbit, or energy-flow accents around a reviewed focal image. |

The single source of truth for this vocabulary is
`video_pipeline_core/effect_layer_manifest.py`. The validator and worker
alignment tests must stay in sync with that manifest.

For reviewed image refs, `image_layout` can use placement modes such as
`center_logo`, `full_bleed_hero`, and `hero_background`. These layout modes and
`radial_current` are generic worker primitives. Do not treat them as fixed
templates or brand-specific shortcuts.

Any unknown layer type must fail closed in `validate_effect_build_spec()`.
Before production handoff, run:

```powershell
python video_tools.py effect-capability-review --input effect_request.json --out effect_capability_review.json
```

Only `decision=supported` should enter the Remotion worker without an extra
human/probe review step.

## Controlled Motion Grammar

These `motion_grammar[]` tokens are currently implemented by
`tools/remotion_worker_bridge.mjs`. Empty `motion_grammar` means legacy default:
all template layers remain enabled. A non-empty list enables only the listed
controllable layers while preserving core layout and labels.

Opening tokens for `training_opening_title`:

| Token | Rendered behavior |
| --- | --- |
| `collage_depth_reveal` | Enables cinematic opening plate, depth vignette, scanline texture, and collage depth shadow. |
| `gold_title_sweep` | Enables the gold title sweep overlay. |
| `title_punch` | Enables title impact pulse scaling. |

Transition tokens for `film_strip_transition_card`:

| Token | Rendered behavior |
| --- | --- |
| `film_rail` | Enables the film thumbnail rail. |
| `thumbnail_acceleration` | Enables thumbnail blur trail and acceleration streak. |
| `flash_wipe` | Enables film flash wipe and midpoint impact flash. |
| `hard_cut_bars` | Enables midpoint hard-cut impact bars, impact flash plate, and commercial shutter bands for short high-impact transitions. |
| `midpoint_impact` | Enables midpoint impact flash without requiring the flash-wipe layer. |

## Opening Title Contract

Template: `training_opening_title`

Required intent:

- Communicate the training / graduation recap identity.
- Establish a credible, formal first impression.
- Use reviewed material, preferably people/group/training context.
- Avoid using title-card screenshots as the main hero image when better human
  material exists.

Useful prompt parameters:

```json
{
  "effect_goal": "formal_training_opening",
  "tone": ["formal", "warm", "memory_recap"],
  "material_strategy": {
    "hero_source": "reviewed_people_group",
    "avoid_hero_roles": ["title_card"],
    "collage_count": 5
  },
  "motion_grammar": [
    "collage_depth_reveal",
    "gold_title_sweep",
    "title_punch"
  ],
  "text_hierarchy": {
    "primary": "program_title",
    "secondary": "subtitle"
  },
  "negative_rules": [
    "do_not_cover_faces",
    "avoid_party_style_flash",
    "avoid_random_stock_look"
  ]
}
```

Review focus:

- Does the opening look intentional before the title is read?
- Are human faces or group context preserved?
- Does it feel like training recap, not a generic slideshow intro?
- Is the title hierarchy readable in one glance?

## Story To MV Transition Contract

Template: `film_strip_transition_card`

Required intent:

- Make the viewer understand that the edit moves from story / setup into a more
  rhythmic MV or montage section.
- The transition should carry motion energy, not just show a static chapter card.
- Use reviewed stills or thumbnails as visual memory anchors.

Useful prompt parameters:

```json
{
  "effect_goal": "story_half_to_mv_half_transition",
  "transition_strength": "impact",
  "phase_labels": ["STORY", "MONTAGE"],
  "cut_point": "midpoint_impact",
  "material_strategy": {
    "thumbnail_source": "reviewed_stills",
    "thumbnail_density": "balanced",
    "reject_low_information_refs": true
  },
  "motion_grammar": [
    "film_rail",
    "thumbnail_acceleration",
    "flash_wipe",
    "hard_cut_bars"
  ],
  "negative_rules": [
    "do_not_read_as_static_chapter_card",
    "do_not_obscure_proof_footage",
    "avoid_random_party_flash"
  ]
}
```

Review focus:

- Can a viewer infer the section change without reading a long explanation?
- Is the motion grammar visible in contact-sheet review?
- Does the midpoint cut feel deliberate?
- Are thumbnails meaningful, or are they low-information filler?

## Current Scope

This contract currently hardens three high-value effect classes:

- `MemoryPhotoWall` through `effect_build_spec`
- `training_opening_title`
- `film_strip_transition_card` with `story_to_mv_film_transition`

Lower thirds, highlight overlays, profile cards, and quote cards should be added
only after these contracts are stable in actual runs.
