# Story Soul Blueprint Skills — Design

Status: planned
Last updated: 2026-06-18

This document defines the upstream creative skill layer that should be added
above the existing material-map and BUILD lifecycle.

The goal is not to add more runtime knobs. The goal is to give the existing
writer/director/material-map pipeline enough story intelligence before it starts
promising shots.

## Problem

The backend can now enforce material truth:

```text
material_needs -> material_map -> delta -> revision -> BUILD -> verify
```

But a technically valid video can still lack narrative soul. The current weak
failure mode is:

```text
opening -> course A -> course B -> course C -> life footage -> ending
```

That is a list, not a film.

A stronger graduation/training film uses a narrative device and emotional spine,
for example:

```text
"0.66% of life"
  -> writing the internship report triggers memory
  -> morning-to-night training center recollection
  -> course montage as lived struggle, not curriculum list
  -> director encouragement as spiritual anchor
  -> daily life and activities as human warmth
  -> memory closes; training is complete; students leave the center
```

This kind of story logic must be extracted before material planning.

## Existing Nodes To Keep

Do not replace the current writer/director/material-map nodes.

Instead, feed them richer upstream artifacts:

- `skills/writer.md` remains responsible for turning story intent into
  screenplay/voiceover/bridge prose.
- `skills/director.md` remains responsible for translating script beats into
  shot language, treatment, and edit intent.
- `skills/material-map.md` remains responsible for supply/demand truth,
  satisfies edges, delta, revision, and build handoff.

The missing layer sits before them.

## Proposed Skill Chain

```text
SSB1 Story World Intake
  -> SSB2 Narrative Device And Concept
  -> SSB3 Screenplay Beat Architect
  -> SSB4 Director Shot And Material Prompt Compiler
  -> existing writer/director/material-map/BUILD
```

These can be implemented as separate skills or one composite skill with four
sections. The preferred implementation is one composite skill first, split only
when usage proves the sections need independent invocation.

## SSB1 — Story World Intake

Purpose: collect the world, people, time, place, and social meaning before any
script is written.

Inputs:

- user brief
- event type
- audience
- known footage/material categories
- organization/context facts
- constraints such as duration, tone, and required inclusions

Outputs: `story_world.json`

Required fields:

- `project_type`
- `audience`
- `people`
- `place`
- `time_span`
- `institutional_context`
- `key_events`
- `required_inclusions`
- `available_material_summary`
- `emotional_truths`
- `known_symbols`

Hard rule:

- If the agent cannot state who the story is about and why the period matters,
  it must stop instead of writing a generic script.

## SSB2 — Narrative Device And Concept

Purpose: find the film's soul: metaphor, memory frame, narrative device, and
emotional promise.

Outputs: `creative_concept.json`

Required fields:

- `core_metaphor`
- `logline`
- `narrative_device`
- `memory_frame`
- `emotional_arc`
- `visual_motifs`
- `human_anchors`
- `opening_question`
- `closing_answer`
- `why_this_is_not_a_course_list`

Examples of valid narrative devices:

- report-writing memory frame
- final day before leaving
- packing a bag
- a letter to future trainees
- a safety helmet / notebook / uniform as object spine
- one day from morning to night

Invalid outputs:

- "show the training process"
- "introduce every course"
- "make it touching"

Those are not concepts.

## SSB3 — Screenplay Beat Architect

Purpose: convert the concept into story beats with function, emotion, and
material implications.

Outputs: `screenplay_beats.json`

Each beat must include:

- `beat_id`
- `title`
- `story_function`
- `emotional_movement`
- `narrative_mode`: `voiceover | mv | interview | title_card | mixed`
- `voiceover_intent`
- `visual_intent`
- `required_actions`
- `human_anchor`
- `transition_in`
- `transition_out`
- `existence_test`
- `minimum_material_count`
- `ideal_material_count`
- `fallback_if_missing`

Existence test:

Every beat must answer: "If this beat is removed, what story meaning is lost?"
If the answer is empty, the beat should be removed or merged.

## SSB4 — Director Shot And Material Prompt Compiler

Purpose: compile screenplay beats into concrete material needs, generation
prompts, and review criteria.

Outputs:

- `director_shot_plan.json`
- `material_needs.json`
- `generation_manifest.json`
- `review_checklist.md`

Each shot/material unit should include:

- `need_id`
- `beat_id`
- `story_function`
- `emotion`
- `visual_family`
- `angle_scale`
- `action_family`
- `subject`
- `media_preference`: `video | photo | generated_image | generated_video`
- `panel_count_min`
- `panel_count_ideal`
- `prompt`
- `negative_prompt`
- `motion_treatment`
- `subtitle_or_title_card_intent`
- `fallback_route`

Material-count rule:

- 1 minute comic/photo story: normally 18-30 useful panels.
- 5 minute comic/photo story: minimum 80-100 panels; better 110-140 for cinematic
  pacing.
- If the plan has fewer panels than the target duration needs, it must shorten,
  request/generate more assets, or declare low visual variety.

## Integration With Existing Pipeline

The target flow after implementation:

```text
Node 0 user brief
  -> SSB1 story_world.json
  -> SSB2 creative_concept.json
  -> SSB3 screenplay_beats.json
  -> SSB4 director_shot_plan + material_needs + generation_manifest
  -> existing material-map lifecycle
  -> existing writer/director contract generation
  -> BUILD
  -> Workbench / dashboard / verify
```

Existing `segment_contract.json` should not become the creative bible. It remains
the executable BUILD contract.

## MGF1 — Material Generation Fallback

Purpose: when the canonical material-map lifecycle proves that planned material
is `missing` or `thin`, convert the affected needs into provider-neutral
generation jobs.

This is a downstream rescue skill, not a replacement for SSB4.

```text
SSB4 director_shot_plan + material_needs
  -> material-map lifecycle / material_delta
  -> MGF1 material_generation_fallback.json
  -> provider generates assets
  -> generated assets re-enter material-map as candidate evidence
```

MGF1 should reuse:

- `material_delta.json` for outcome and count
- `material_needs.json` for required purpose and fallback options
- `creative_concept.json` for metaphor / narrative device
- `director_shot_plan.json` for visual family, angle, action, subject, prompt,
  and negative prompt

MGF1 must never:

- generate jobs from a broken delta
- claim generated work is real footage
- mark generated assets as accepted
- satisfy proof-critical / identity-sensitive needs without explicit human
  decision

Good MGF1 targets:

- comic/photo story panels
- memory-frame inserts
- symbolic object bridges
- chapter-card backgrounds
- non-identifying reenactment details

Bad MGF1 targets:

- real director speech
- real trainee reaction proof
- official certificate / logo / name badge evidence
- actual event timeline evidence

## Skill Files To Add Later

Preferred first implementation:

- `skills/story-soul-blueprint.md`
- `skills/material-generation-fallback.md`

Optional split after proving use:

- `skills/story-world-intake.md`
- `skills/narrative-device.md`
- `skills/screenplay-beat-architect.md`
- `skills/material-prompt-compiler.md`

Do not split early unless the composite skill becomes too hard for agents to use.

## Reference Repos

Use these as inspiration, not dependencies:

- `reference repo/video-autopilot-kit-main`
  - useful for content-type templates, checklist thinking, asset scanning,
    frame grids, and audit helpers.
- `reference repo/ai-media-generator-main`
  - useful for concept-first prompting, storyboard structure, character/style/
    scene cards, model-aware prompt construction, and quality-control playbooks.

## First Acceptance Case

Use a graduation/training video case inspired by the 66th/67th training-center
discussion.

Input should include:

- rough project brief
- course/activity categories
- available material categories
- desired duration
- audience

Expected output must include:

- a non-generic core metaphor or narrative device
- 8-12 story beats
- each beat mapped to material count and required visual actions
- generated material prompts where existing footage is insufficient
- a review checklist that can judge whether the final video preserved the soul

Failure conditions:

- output only lists course items
- no narrative device
- no material quantity estimate
- no per-beat existence test
- no fallback when material is insufficient

## Boundary

This layer is upstream of material truth. It may request or generate material,
but it must not bypass:

- material-map satisfies edges
- M6 delta
- M6 revision decisions
- pre-BUILD gate
- Workbench draft/canonical separation
