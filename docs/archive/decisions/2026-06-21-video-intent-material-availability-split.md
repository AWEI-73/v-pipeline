# Video Intent / Material Availability Split

Date: 2026-06-21
Status: accepted
Scope: upstream intake, material-map routing, generated-material boundary

## SPEC

The pipeline needs one durable upstream mechanism before Story Soul or BUILD:
the agent must determine the user's video intent and material availability.

Without this split, the same request can be misrouted:

- a teaching video with real screen recordings or footage can be pushed into a
  generated story route;
- a personal video can be treated like a fictional storyboard;
- a zero-material storybook can skip the initial material delta and pretend
  generation is already accepted material;
- existing-material cases can lose the chance to let the material map shape the
  story.

The required split is:

```text
video intent
  -> material availability
  -> existing-material-first | story-first | hybrid
  -> route-specific story/design/material work
```

## DO

Update the canonical route documents and operator skills so Stage 0 explicitly
asks about material availability before deeper story work.

Defined routes:

- `existing-material-first`: real footage/photos/materials exist. Run
  material-map early; the material map is the story source and constraint.
  Generation is fallback only for non-proof support such as diagrams, chapter
  cards, symbolic inserts, or bridge visuals.
- `story-first`: no usable material exists, or the user explicitly wants a
  generated/storybook/comic route. Story/design/teaching intent leads, then
  material needs drive generated or captured candidates.
- `hybrid`: some real material exists, but missing beats may require reshoot,
  generation, rewrite, shortening, drop, or waiver after material-delta.

The first upstream role is a video intent planner, not always a fiction writer.
It can become a teacher, personal video editor, event director, brand editor, or
storybook writer depending on the route.

## VERIFY

Focused tests lock the mechanism:

```powershell
python -m unittest tests.test_upstream_route_alignment_docs -q
python -m unittest tests.test_canonical_route_acceptance -q
```

The canonical route acceptance harness also checks the Stage 0 terms:

- `material availability`
- `existing-material-first`
- `story-first`
- `hybrid`
- `generation is fallback`
- `teaching`
- `personal video`

This is process solidification, not template solidification. It does not freeze
story templates, reviewer personas, or video genres.

## Boundaries

- Do not create a new runtime schema for this split yet; keep it as route/skill
  operating discipline unless a real run proves a machine-readable field is
  needed beyond existing brief fields.
- Do not make generated material default for existing-material-first teaching or
  personal video routes.
- Do not let material-map write story soul; it informs and constrains the story,
  then validates coverage.
- Do not bypass `material_delta`, generated-material review, or `contract-run`
  gates.

