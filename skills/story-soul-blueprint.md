---
name: story-soul-blueprint
description: Use at the front of the video pipeline to turn a user brief into story_world, creative_concept, screenplay_beats, director_shot_plan, material_needs, generation_manifest, and review_checklist before material-map or BUILD work.
---

# Story Soul Blueprint

This skill creates the upstream creative artifacts that keep a video from
becoming a course list or asset list.

Use it before material-map planning when the project needs a narrative device,
emotional spine, or generated comic/photo story plan.

## Command

```powershell
python video_tools.py story-soul-blueprint project_brief.json `
  --out-dir story_blueprint
```

Outputs:

- `story_world.json`
- `creative_concept.json`
- `screenplay_beats.json`
- `director_shot_plan.json`
- `material_needs.json`
- `generation_manifest.json`
- `review_checklist.md`

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
4. Every beat needs a material count estimate.
5. If material quantity is insufficient, shorten, request material, or generate
   candidates instead of pretending the duration is supported.
6. Compile toward existing canonical artifacts; do not invent a second BUILD
   schema.

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

## Integration

```text
story-soul-blueprint
  -> material_needs / director_shot_plan
  -> material-map lifecycle
  -> material-generation-fallback when missing/thin
  -> generated-material-producer/import/review if generated assets are needed
  -> BUILD
```
