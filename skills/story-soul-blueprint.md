---
name: story-soul-blueprint
description: Use at the front of the video pipeline to turn a user brief into story_world, creative_concept, screenplay_beats, director_shot_plan, material_needs, generation_manifest, and review_checklist before material-map or BUILD work.
---

# Story Soul Blueprint

This skill creates the upstream creative artifacts that keep a video from
becoming a course list or asset list.

Use it before material-map planning when the project needs a narrative device,
emotional spine, or generated comic/photo story plan.

When a whole-video request begins fuzzy or has more than one credible story
shape, use `skills/editorial-ambiguity-loop.md` as the Stage 0–2 method overlay.
This Skill still owns Story Soul content; the overlay owns only progressive
clarification, decision evidence, and the Stage 2 handoff shape.

## Command

```powershell
python video_tools.py story-soul-blueprint project_brief.json `
  --out-dir story_blueprint
python video_tools.py story-soul-to-contract `
  --story-dir story_blueprint `
  --out segment_contract.json
```

Outputs:

- `story_world.json`
- `creative_concept.json`
- `screenplay_beats.json`
- `director_shot_plan.json`
- `material_needs.json`
- `generation_manifest.json`
- `review_checklist.md`
- optional bridge output: `segment_contract.json` via `story-soul-to-contract`

## Required Input Ideas

The brief should include:

- `project_type`
- `audience`
- `duration_sec`
- `facts`
- known material categories, if any
- required inclusions, if any
- `seed_device` when the user already has a metaphor or narrative device

If the agent cannot state who the story is about and why the period matters, it
must stop instead of writing generic content.

## Design Rules

1. Find a narrative device before writing beats.
2. Every beat needs a story function and emotional movement.
3. Every beat needs an existence test: what is lost if this beat is removed?
4. Every beat needs a conflict/turn, sensory anchor, and intended viewer
   feeling. These are not decoration; they tell the director what the shot must
   make the viewer experience.
5. Every shot in `director_shot_plan.json` needs `director_intent` with
   composition, camera motion, edit role, audio/subtitle intent, and prompt
   requirements. This is the bridge from story soul to material-map/generation.
6. Every beat needs a material count estimate.
7. If material quantity is insufficient, shorten, request material, or generate
   candidates instead of pretending the duration is supported.
8. Compile toward existing canonical artifacts; do not invent a second BUILD
   schema.
9. If the input brief carries Stage 0 child contracts, preserve them instead of
   re-deciding them. `stage0_child_contracts.material` informs material needs,
   `stage0_child_contracts.soundtrack` becomes director audio intent,
   `stage0_child_contracts.effect` becomes effect policy, and
   `stage0_child_contracts.subtitle_voiceover` becomes subtitle/voiceover
   intent. These are constraints and handoffs, not permission to skip material
   truth or BUILD gates.
10. Do not stop at beat names. Before Stage 3, expand the accepted causal arc
    into `segment_story_contract.json` and `evidence_need_map.json` through
    `editorial-ambiguity-loop`; every segment must declare its state change and
    the picture roles needed to prove it.

## Good Output

For a graduation/training film, a good blueprint might use:

- core metaphor: `0.66% of life`
- narrative device: report-writing memory frame
- emotional spine: pressure -> struggle -> companionship -> gratitude -> leaving
- material needs: report insert, morning assembly, hard training, teamwork,
  director encouragement, daily life, activities, completion

For a generated comic story, a good blueprint should declare:

- consistent protagonist / object spine
- visual motifs
- 18-30 panels per minute
- prompt and fallback for every beat

## Bad Output

Reject:

- "introduce courses"
- "show the training process"
- "make it touching"
- beats with no existence test
- material needs with no count estimate
- promised duration unsupported by material quantity

## Effect Intent Hook

When the project asks for strong style, opening hook, chapter transition,
comic/storybook language, memory frame, or motion-graphic emphasis, capture the
effect as story intent rather than renderer API.

Ask only enough to decide the story function:

- What should the effect communicate: hook, chapter boundary, emotional
  emphasis, information label, memory frame, or visual rhythm?
- How strong should it be: low / medium / high?
- Does the effect protect or risk proof footage readability?
- Can it be generated as a separate effect asset, or should it stay a simple
  ffmpeg-safe treatment?

Write the decision into `director_shot_plan.json` beat items:

```json
{
  "beat_id": "b02",
  "story_function": "report_memory_transition",
  "effect_intent": {
    "role": "chapter_transition",
    "intent": "report page turns into training memory",
    "intensity": "medium",
    "visual_language": ["paper_texture", "timestamp_overlay"],
    "required_for_story": true,
    "must_preserve_proof": true,
    "fallback": "simple_title_card_fade"
  }
}
```

Do not write Remotion component names, props, fps, or `durationFrames` here.
Those belong to a later backend adapter after `effect-intent-plan` compiles
neutral `effect_intent_plan.json` and `effect_asset_spec.json`.

## Integration

```text
story-soul-blueprint
  -> editorial-ambiguity-loop hypothesis / verdict / causal expansion
  -> material_needs / director_shot_plan
  -> stage0_child_contracts preserved into Director Shot Plan when present
  -> segment_story_contract + evidence_need_map + Stage 2 ambiguity gate
  -> story-soul-to-contract when the next owner is Segment Contract / Node 3
  -> effect-intent-plan when effect_intent exists
  -> material-map lifecycle
  -> material-generation-fallback when missing/thin
  -> generated-material-producer/import/review if generated assets are needed
  -> BUILD
```
