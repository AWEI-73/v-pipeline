# Decision: Effects Baseline And Recipe Order

Date: 2026-06-11
Status: verified
Scope: Effects Phase E1/E2
Superpowers phase: verify

## SPEC

Requirement:

Measure whether `render_profile=light_effects` produces visible effects before
expanding the recipe library.

Why:

Unit tests proved that plans were written, but did not prove that planned
effects reached the renderer or were visible in a real film.

Direction:

Write `light_effects_baseline_review.json` after render and P1 audits. Measure
planned versus rendered effects and expose gaps under dashboard Node 14.

Non-goals:

Do not claim plan-only effects are rendered. Do not start html_playwright before
the ffmpeg/libass baseline is measurable.

## DO

Files / modules:

- `video_pipeline_core/light_effects.py`: baseline coverage review.
- `video_pipeline_core/contract_adapter.py`: write and index the review.
- `video_pipeline_core/dashboard_state.py`, `node_registry.py`: expose gaps.
- `examples/light_effects_baseline_build_profile.json`: repeatable baseline.

Function-level plan:

After P1 audits, compare `light_effects_plan.items` with manifest
`render_outputs`; record missing renderer outputs and visual-review evidence.

Data / interface changes:

Add `light_effects_baseline_review.json` to `artifact_manifest.json`.

Migration / compatibility:

Only light-effects runs create the new artifact. Existing profiles are inert.

## VERIFY

Pre-checks:

Use the existing `skill-smoke` sources without overwriting its passing run.

Tests:

`python -m unittest tests.test_light_effects tests.test_contract_adapter -k light_effects -v`

Manual checks:

Real run:
`C:\Users\user\Desktop\video_project\skill-smoke\runs\20260611-effects-baseline`

Result: final render and P1 audits passed; baseline measured 7 planned effects,
0 rendered effects, and 0% effect coverage. Keyframe review showed static center
text and no visible recipe-level motion.

E2 text-recipe run:
`C:\Users\user\Desktop\video_project\skill-smoke\runs\20260611-effects-e2-text-recipes-v2`

Result: final render, VERIFY 91.5, and P1 audits passed. Three text recipes were
composited, raising coverage to 3/7 (42.9%). Keyframe review confirmed that
base drawtext no longer duplicates the libass text layer. Remaining gaps are
two xfade and two Ken Burns effects.

E2 contract-semantics run:
`C:\Users\user\Desktop\video_project\skill-smoke\runs\20260611-effects-e2-contract-semantics-v3`

Result: final render, VERIFY 91.5, P1 audits, dashboard generation, and
keyframe review passed. The corrected plan measured 3 planned text effects,
3 composited outputs, 0 gaps, and PASS. Hold video is no longer mislabeled as
Ken Burns; beat/direct cuts are no longer mislabeled as xfade. Photo Ken Burns
now records evidence from the MV renderer when it is actually used.

E2 explicit-xfade run:
`C:\Users\user\Desktop\video_project\skill-smoke\runs\20260611-effects-e2-explicit-xfade-v6`

Result: explicit incoming `transition: xfade` rendered through ffmpeg
`xfade` / `acrossfade`; VERIFY 92.5 passed with duration, subtitle, and
technical-quality dimensions at 100. The light-effects baseline measured
4 planned effects, 4 rendered/composited outputs, 0 gaps, and PASS. Timeline,
caption, broll, and visual audits passed. A boundary contact sheet confirmed
the 0.5-second crossfade is visible.

Caption audit correction:

Timeline labels and name supers are visual decoration, not reading-track
subtitles. Generated SRT now includes only narrative/subtitle fields, so a
label visible during an xfade does not create a false subtitle-overlap failure.
Actual narrative/subtitle overlap remains a blocking caption-audit defect.

Regression risks:

The old artifact manifest contains a corrupted Unicode music path. The baseline
run used the filesystem-resolved MP3 path.

Text renderer ownership must remain singular. Light-effects and motion-graphics
profiles preserve canonical text trace but must not also burn base MV drawtext.

## Decision Notes

Accepted because:

The baseline proves that E2 must wire recipes into rendering rather than add
more plan vocabulary. Effect plans must also describe explicit renderer
behavior rather than infer decorative effects from generic pace/layout fields.

Tradeoffs:

The baseline review is intentionally strict and reports gaps until render
outputs are explicitly traceable.

Open questions:

E2 light-effects baseline is closed. Continue with E3 attention-budget and
pacing enforcement. Photo Ken Burns remains rendered by
`mv_cut.photo_zoompan` with manifest evidence.

## Git / Retrieval

Related files:

`video_pipeline_core/light_effects.py`, `video_pipeline_core/motion_graphics.py`

Related commits:

Pending.

Graphify anchors:

`build_light_effects_baseline_review`, `run_motion_graphics_render_plan`,
`composite_ffmpeg_libass_outputs`, `render_mv_audio`,
`_render_segment_sequence`, `_timeline_caption_entries`

Search tags:

`decision-log`, `effects-phase`, `E1`, `E2`, `light-effects-baseline`,
`explicit-xfade`, `caption-audit`
