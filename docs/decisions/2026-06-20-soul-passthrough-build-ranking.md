# Soul Passthrough And BUILD Ranking

Date: 2026-06-20

## Decision

Move existing upstream story-soul signals into the BUILD moment instead of
creating another planner or verifier.

Two signals now cross the boundary:

- Film-level `story_soul` from blueprint creative concept:
  `narrative_device`, `core_metaphor`, `emotional_arc`.
- Beat-level soul fields into `segment.core`:
  `emotional_movement`, `conflict_or_turn`,
  `intended_viewer_feeling`, `sensory_anchor`.

Director intent remains optional and passes through as `segment.director_intent`.
When `director_intent.material_prompt_requirements` exists, it is also copied
to `segment.material_fit.material_prompt_requirements` so material retrieval can
use it without parsing prose.

## BUILD Use

`material_retrieval.rank_scenes` now computes `score_breakdown.soul`, but only
after a candidate already has base evidence from need/text/function/pace.

That means soul can change admitted-candidate selection when the base evidence
is close enough for the soft score to matter, but it cannot admit an otherwise
unrelated candidate and it should not override deterministic need evidence.

The companion window-quality hardening keeps `avoid_ranges`/`bad_ranges`
inside BUILD selection:

- prefer clean lower-ranked windows when available;
- if every renderable candidate overlaps a known bad range, emit the least-bad
  slot with `window_quality_fallback=true` rather than silently starving the
  segment.

## Verification

Focused tests:

- `tests.test_blueprint_to_contract`
- `tests.test_material_retrieval`
- `tests.test_map_retrieval_wiring`

Key reverse proofs:

- blueprint story-soul fields round-trip into the contract without becoming
  required;
- `soul_ranking=False` vs `soul_ranking=True` can select different windows, and
  the 67th fuller replay report now records `bsa1_soul_selection.flip_count`
  plus a zero-flip reason when real material-map scene semantics are too thin;
- soul evidence does not admit zero-base scenes;
- bad windows backfill to clean windows, and all-bad material returns a traced
  fallback slot instead of an empty segment;
- Workbench/dashboard review surfaces `window_quality_fallback` counts so
  reviewers can see which slots used a least-bad window.

Real 67th planning-only replay:

- input: `C:\Users\user\Downloads\微電影素材\_整理後`;
- result: 12 comparable segments, `flip_count=0`,
  `positive_soul_segments=0`;
- interpretation: the BUILD path is wired, but this 67th material map still
  has no differentiating soul-readable scene labels (`caption` is effectively
  the folder theme; `visual_family`/`action_family`/`subject` are absent), so
  BSA1 correctly reports a zero-flip reason instead of claiming effectiveness.

## Non-Goals

- No new hard gate.
- No new canonical material schema.
- No prompt-time aesthetic scoring.
- No replacement for `material_delta`, visual diversity, or black-frame audit.
- No claim that story soul alone makes a good film; it is a soft BUILD signal.
