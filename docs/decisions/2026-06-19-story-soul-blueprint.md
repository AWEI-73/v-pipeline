# SSB1 Story Soul Blueprint

Date: 2026-06-19

## Decision

Add a deterministic baseline skill and CLI that compiles a high-level video
brief into upstream creative artifacts before material-map or BUILD work starts.

## Why

The backend can now enforce material truth and generated-material boundaries.
The remaining repeated failure is upstream: thin briefs produce technically valid
but emotionally flat videos.

SSB1 creates the minimum artifact shape needed for agents to reason about:

- story world
- core metaphor / narrative device
- screenplay beats
- director shot plan
- material needs
- generated material plan
- review checklist

## Command

```powershell
python video_tools.py story-soul-blueprint project_brief.json --out-dir story_blueprint
```

## Outputs

- `story_world.json`
- `creative_concept.json`
- `screenplay_beats.json`
- `director_shot_plan.json`
- `material_needs.json`
- `generation_manifest.json`
- `review_checklist.md`

## Acceptance

Focused tests cover:

- a graduation/training brief that must produce a `0.66%` metaphor and
  report-writing memory frame, not a course list;
- a generated comic story that must estimate enough panels for one minute and
  prefer generated images;
- a generic brief with no story subject that must fail closed;
- CLI artifact writing.

## Boundary

SSB1 is a baseline scaffold, not a final writer model. It provides deterministic
structure and minimum story logic. A human or high-end model can improve prose
inside the same artifacts without changing downstream contracts.

## End-To-End Acceptance

Add:

```powershell
python tools/story_to_generated_material_e2e.py .tmp/story_to_generated_material_e2e
```

The harness runs:

```text
project brief
  -> story-soul-blueprint
  -> material_delta missing
  -> material_generation_fallback
  -> generated_material_produce
  -> generated_material_review
  -> material_delta covered
```

Current evidence:

- case: `postcard_city_sky`
- beats: `5`
- needs: `5`
- generated panels: `21`
- initial delta: `missing=5`
- after generation: `thin=5`, `missing=0`
- after review: `covered=5`, `thin=0`, `missing=0`

This proves the current upstream story artifacts can drive the generated
material lifecycle end to end. It does not prove final art quality because the
test renderer intentionally emits deterministic storyboard cards.
