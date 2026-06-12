# Decision: S1b Anti-Presentation Planning

Date: 2026-06-12
Status: accepted
Scope: Sensory Phase S1b

## SPEC

Prevent presentation-like treatments before render without introducing a new
effects system:

- Long still segments must request 2-3 shots and rotate existing P5 motion
  modes.
- Centered narrative cards must become lower-thirds.
- Node 9 decisions must reach the concrete render plan and both existing text
  render paths.
- Preserve content without these conditions.

## DO

- `edit_artifacts` emits a deterministic `anti_presentation_plan` from Node 9.
- `contract_adapter` carries that plan into the runtime payload.
- `mv_cut` honors minimum shot count, still-treatment rotation, and text
  placement.
- `motion_graphics` reads runtime timeline placement so `light_effects` renders
  the same lower-third decision instead of reverting to a centered title.

The implementation reuses the existing P5 still modes and existing
`lower_third_clean` recipe. It does not add a new renderer or backend.

## VERIFY

Deterministic:

- Focused regression: 188 tests, OK.
- Full regression: 611 tests, OK.
- Python compile and `git diff --check`: OK.
- Old presentation-style fixture still triggers at least three S1a detectors.

Real renders:

- `C:\Users\user\Desktop\video_project\skill-smoke\runs\20260612-sensory-s1b-v1`
  - VERIFY 92.5, PASS.
  - Presentation-feel audit: 0 fail.
  - Segments 1 and 4 render with `lower_third_clean`.
- `C:\Users\user\Desktop\video_project\city-lite\runs\20260612-sensory-s1b-v1`
  - VERIFY 91.2, PASS.
  - Presentation-feel audit: 0 fail.
  - No narrative card exists, so the visual baseline remains unchanged.

Agent sensory review:

- Skill-smoke preserves the image subject while moving narrative copy out of
  the center; the opening and closing read less like slides.
- City-lite remains visually equivalent, confirming the rule does not mutate
  unrelated timelines.

## DECISION

Accept S1b. The Node 9 plan now forms a closed loop into render behavior while
remaining deterministic and limited to the roadmap's anti-presentation rules.
Proceed to S2.
