# Upstream Story Route

Date: 2026-06-20
Status: current upstream route / before Material Truth

This document defines the upstream creative line that feeds the canonical
Hermes Video Pipeline. Use it when the project needs story quality, generated
material, children's stories, event films with emotional framing, or any route
where a plain parameter sheet would produce a weak video.

The upstream line is:

```text
Role / Literary Lens
  -> Blueprint Interview
  -> Story Soul Package
  -> Director Shot Plan
  -> Contract Compile
  -> Material-Ready Handoff
```

It ends when the project has a validated `segment_contract.json` and
`material_needs.json` that can enter Material Truth.

## Why This Exists

The pipeline already has strong material gates and BUILD tools. The remaining
quality risk is upstream: the system can faithfully build a thin idea. This
route keeps the "soul" of the video explicit before material-map and BUILD
start.

## Stage 1: Role / Literary Lens

Purpose: decide what kind of mind is writing the piece.

Use when the source is a fairy tale, memoir, event film, speech, essay,
training story, or any piece that needs a voice beyond "list the facts".

Typical inputs:

- audience;
- genre;
- moral or thesis;
- source text or lived experience;
- tone boundaries;
- cultural/safety constraints.

Typical outputs:

- `literary_role_lens.json`;
- optional `longform_source.md`;
- optional `literary_master_review.json`.

Reviewer:

- `literary_editor` when `review_policy.level == deep`.

Stop if the lens is generic enough that any story would fit it.

## Stage 2: Blueprint Interview

Purpose: turn the user's rough intent into prose and ordered beats.

Primary skill:

- `skills/blueprint-interview.md`

Main artifacts:

- `blueprint.md` -- prose: thesis, audience, big story, stakes, anti-goals;
- `blueprint.json` -- thin machine index with stable beat ids.

Relevant tools:

```powershell
python video_tools.py blueprint-compile blueprint.md --out blueprint.json
python video_tools.py blueprint-coverage blueprint.json segment_contract.json --out blueprint_coverage.json
```

Rules:

- `blueprint.md` carries the story soul in human language.
- `blueprint.json` is only an index / handle.
- Do not compress prose into empty parameters.
- Beat ids are stable anchors for downstream `blueprint_ref`.

Stop if a beat lacks turn, stakes, emotional purpose, or a reason to exist.

## Stage 3: Story Soul Package

Purpose: create the executable upstream package that downstream tools can read.

Primary skill:

- `skills/story-soul-blueprint.md`

Main tool:

```powershell
python video_tools.py story-soul-blueprint project_brief.json --out-dir story_blueprint
```

Main artifacts:

- `story_world.json`;
- `creative_concept.json`;
- `screenplay_beats.json`;
- `director_shot_plan.json`;
- `material_needs.json`;
- `generation_manifest.json`;
- `review_checklist.md`;
- aggregate `story_soul_blueprint.json` when present.

Rules:

- Every beat should have `conflict_or_turn`.
- Every beat should have `sensory_anchor`.
- Every beat should declare `intended_viewer_feeling`.
- Every planned shot should include `director_intent`.
- Generated-story routes should declare panel/style consistency needs.

Reviewer:

- `story_director` for `normal` and `deep` policy.

Stop if the output is only categories, courses, or scenes without emotional
turns.

## Stage 4: Director Shot Plan

Purpose: convert story into executable visual/audio/subtitle/effect needs.

Primary skills:

- `skills/director.md`;
- `skills/audio-director.md`;
- `skills/subtitle-director.md`;
- `skills/effects-director.md`.

Main artifacts:

- `director_shot_plan.json`;
- `material_needs.json`;
- `effect_intent_plan.json`;
- voiceover/subtitle intent;
- audio cue intent.

Useful tools:

```powershell
python video_tools.py validate-needs material_needs.json
python video_tools.py effect-intent-plan ...
python video_tools.py spec-review segment_contract.json ...
```

Rules:

- Use `need_id` as the material join key.
- A shot plan should describe what material must prove, not just what it looks
  like.
- Effects remain backend-neutral at this stage.
- If generated material is likely, write prompt-facing requirements now:
  character consistency, style bible, camera language, panel count, and negative
  constraints.

Stop if the material plan cannot tell a curator or image generator what to
collect/create.

## Stage 5: Contract Compile

Purpose: produce the BUILD-facing contract while preserving upstream trace.

Primary tools:

```powershell
python video_tools.py blueprint-to-contract blueprint.json decisions.json --out segment_contract.json
python video_tools.py contract-dry-build segment_contract.json ...
```

Main artifacts:

- `segment_contract.json`;
- `material_needs.json`;
- `blueprint_coverage.json` when blueprint route is used.

Rules:

- Segment `core.blueprint_ref` must point back to real blueprint beats.
- Segment material refs must be expressed through `material_fit.need_refs`.
- Do not compile away manual story requirements or must-have beats.
- Do not satisfy a must-have real-world beat with generated stock unless the
  route explicitly allows it.

Stop if blueprint coverage drops a promised beat.

## Stage 6: Material-Ready Handoff

Purpose: hand the upstream contract to Material Truth without ambiguity.

Required handoff:

- `segment_contract.json`;
- `material_needs.json`;
- optional `effect_intent_plan.json`;
- optional `blueprint_coverage.json`;
- optional `review_policy`.

For generated storybook/comic routes, strongly expected handoff artifacts also
include:

- `generation_manifest.json`;
- character/style consistency requirements;
- generated material review rubric;
- subtitle/audio intent, especially target subtitle language;
- panel or shot count expectations.

The next route is:

```text
Material Truth
  -> Material Delta
  -> Revision / Generated Fallback if needed
  -> BUILD
```

## Route Variants

### Event / graduation film

Use a memory device, report-writing frame, day-to-night arc, or other narrative
device that can organize real footage. Material needs should distinguish
speeches, training action, daily life, transitions, and ending closure.

### Generated storybook / comic

Use Role / Literary Lens and Story Soul before generation. The generated
material plan must include panel count, character/style continuity, camera
language, subtitle/voiceover expectations, and a generated-material review
rubric.

For zero-material projects, do not call generated fallback directly from needs.
First enter Material Truth with `material_needs.json` and an empty/initial
project material map, compute a fresh `material_delta.json`, then let
`material-generation-fallback` consume the missing/thin delta.

Example high-risk route:

```text
3-5 minute children's comic/storybook
  -> review_policy.deep
  -> Role / Literary Lens
  -> Blueprint Interview
  -> Story Soul Package
  -> Director Shot Plan with Chinese subtitles and panel count
  -> Contract Compile
  -> Material-Ready Handoff
  -> initial missing material_delta
  -> material_generation_fallback.json
  -> generated_provider_packet.json
  -> generated image production
  -> generated-material-import
  -> generated-material-review
  -> fresh material_delta
  -> contract-run
```

### Training explainer

Use Director Shot Plan heavily. Material needs should prove steps, safety
details, before/after states, and narrator beats. The story soul can be lighter,
but the proof plan must be strict.

## Reviewer Placement

Use `docs/artifact-reviewer-map.md`.

Recommended defaults:

- `light`: no literary review; run technical/material review only.
- `normal`: run `story_director` before Material Truth.
- `deep`: run `literary_editor` before Story Soul and `story_director` before
  Contract Compile.

Reviews should normally return `pass`, `revise`, or `advisory`. They should not
become delivery hard gates unless the route explicitly says so.

## Minimal Agent Checklist

Before Material Truth, confirm:

- the project has a narrative device or explicit reason not to need one;
- must-have beats are traceable;
- every material need has a purpose, count, and fallback;
- generated routes have style/panel/prompt requirements;
- `review_policy` is chosen or intentionally omitted;
- `segment_contract.json` and `material_needs.json` are ready for fresh
  material delta.
