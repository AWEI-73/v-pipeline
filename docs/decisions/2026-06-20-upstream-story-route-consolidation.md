# Upstream Story Route Consolidation

Date: 2026-06-20
Status: accepted

## Decision

Add `docs/upstream-story-route.md` as the stable upstream line before Material
Truth:

```text
Role / Literary Lens
  -> Blueprint Interview
  -> Story Soul Package
  -> Director Shot Plan
  -> Contract Compile
  -> Material-Ready Handoff
```

This keeps creative story development separate from material truth and BUILD.
It also reconciles the older prose `blueprint.md` / `blueprint.json` path with
the newer executable `story-soul-blueprint` package.

## Why

Recent generated storybook and event-film tests showed that backend gates are
mostly stable, but weak upstream story/design inputs still produce weak videos.
The pipeline needs a clear operator route for story-heavy projects before
material-map and BUILD begin.

## Boundaries

- This is not a new BUILD system.
- This does not bypass material map, delta, generated-material review, or
  `contract-run`.
- `Material-Ready Handoff` means the project is ready to enter Material Truth,
  not ready to render.
- Generated assets remain candidates until reviewed and accepted.

## Subagent Cold-Start Review

A read-only cold-start subagent validated a 3-5 minute children's comic/storybook
case with no existing material and Chinese subtitles.

Findings:

- The upstream line is clear enough to reach Material-Ready Handoff.
- The route naturally connects to Material Truth, generated fallback, fresh
  delta, and BUILD.
- `review_policy.level=deep` is appropriate for children story + generated
  material + subtitles.
- Two doc gaps were fixed:
  - zero-material generated routes must first compute an initial missing/thin
    `material_delta.json`;
  - generated storybook/comic handoff should explicitly include
    `generation_manifest.json`, style/character consistency requirements,
    generated material review rubric, and subtitle/audio intent.

## Verification

Focused tests:

```powershell
python -m unittest tests.test_upstream_route_alignment_docs tests.test_canonical_route_acceptance -v
python -m unittest tests.test_upstream_route_alignment_docs tests.test_canonical_route_acceptance tests.test_story_soul_blueprint tests.test_story_to_generated_material_e2e -q
python tools\canonical_route_acceptance.py --out .tmp\canonical_route_acceptance.json
```

Result: all green, `canonical_route_acceptance.ok == true`.

