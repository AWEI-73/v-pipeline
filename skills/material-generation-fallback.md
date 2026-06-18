---
name: material-generation-fallback
description: Use when fresh material_delta.json has missing/thin needs and the project should plan generated image/video fallback jobs without bypassing material-map review or M6 gates.
---

# Material Generation Fallback

This skill plans generated-material jobs from real material gaps.

It does not generate files. It produces `material_generation_fallback.json`,
which is then executed by `skills/generated-material-producer.md`.

## When To Use

Use this when:

- `material_delta.json` is fresh and `ok=true`
- one or more needs are `missing` or `thin`
- the need can safely be represented by generated material:
  - comic/photo story panel
  - symbolic insert
  - generic chapter bridge
  - title/background/card
  - non-identifying reenactment detail

Do not use this when:

- `material_delta.ok=false`
- the material map has dangling references or invalid asset identity
- the need is proof-critical, identity-sensitive, official speech, certificate,
  logo, name badge, real-event evidence, or anything the audience must trust as
  actual footage

## Command

```powershell
python video_tools.py material-generation-fallback material_delta.json `
  --needs material_needs.json `
  --creative-concept creative_concept.json `
  --director-shot-plan director_shot_plan.json `
  --out material_generation_fallback.json
```

Optional context:

- `story_world.json`
- `screenplay_beats.json`

## Output Contract

Each `generation_jobs[]` item must carry:

- `need_id`
- `source_type: generated`
- `status: planned`
- `media_type`
- `panel_count`
- `story_function`
- `visual_family`
- `angle_scale`
- `action_family`
- `subject`
- `prompt`
- `negative_prompt`
- `review_criteria`
- `material_map_return.initial_satisfies_status: candidate`
- `honesty.must_not_claim_real_event: true`

Generated material must re-enter the material-map lifecycle as candidate
evidence. It must never bypass review or become accepted automatically.

## Standard Flow

```text
material_delta missing/thin
  -> material-generation-fallback plans jobs
  -> generated-material-producer creates/imports files
  -> project_material_map with candidate satisfies edges
  -> material_delta fresh rerun
  -> reviewer accepts/rejects candidates
  -> BUILD only after accepted evidence or explicit revision/waiver
```

## Prompt Planning Rules

For each generated job:

1. State the story function first.
2. Preserve the project style and character anchors.
3. Include camera language: angle, scale, lens, composition, or motion intent.
4. Include negative prompts for text, watermark, logo, distorted hands/faces,
   fake official signs, and unrelated subjects.
5. Split long needs into `panel_count` panels instead of asking one image to
   do too much.

## Review Checklist

Before sending jobs to a provider, confirm:

- every job maps to a real `need_id`
- the prompt supports the need purpose, not decorative filler
- generated output cannot be mistaken for documentary proof
- `visual_family`, `angle_scale`, and `action_family` are filled
- the fallback if generation fails is explicit

After provider output returns, use `generated-material-producer` to validate and
write candidate material-map evidence.
