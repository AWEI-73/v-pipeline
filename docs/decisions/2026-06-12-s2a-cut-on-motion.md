# Decision: S2a Cut On Motion

Date: 2026-06-12
Status: verified
Scope: Sensory Phase S2a / Node 10 timeline build
Superpowers phase: verify

## SPEC

Requirement:

Snap real edit windows to local frame-difference motion peaks. Scene boundaries
must keep priority over motion peaks.

Why:

The existing scene-cut snap only changed `timeline_build` after rendering.
S2a must change the concrete render plan so the final video and timeline trace
cannot disagree.

Direction:

Use deterministic grayscale frame-difference energy, select spaced local
maxima, apply the snap before render, then preserve the original and adjusted
source times in Node 10.

Non-goals:

- Do not implement J/L cuts or speech-tail padding.
- Do not move the opening frame.
- Do not change clip duration, timeline duration, material selection, or audio.

## DO

Files / modules:

- `video_pipeline_core/edit_artifacts.py`
- `video_pipeline_core/mv_cut.py`
- `tests/test_edit_artifacts.py`
- `tests/test_mv_cut.py`

Function-level plan:

- Detect local frame-difference energy peaks with lazy OpenCV decoding.
- Use scene-first, motion-second snap precedence.
- Reject snaps that would exceed source duration.
- Snap the concrete MV render plan before `render_mv_audio`.
- Preserve `original_start_sec`, adjusted `start_sec`, and
  `snapped_to_motion_peak` in `timeline_build`.

Data / interface changes:

- Concrete render-plan items may carry `original_extract_start` and
  `adjustment_reason`.
- Node 10 clips expose the same adjustment trace.

Migration / compatibility:

Decode failures or missing peaks leave windows unchanged. Existing scene-cut
behavior remains compatible.

## VERIFY

Pre-checks:

- Existing S1b real-render plans were probed before rendering.
- First-shot movement and source-tail overflow were found and prevented by
  regression tests.

Tests:

- Focused regression: 191 tests, OK.
- Full regression: 617 tests, OK.
- Python compile and `git diff --check`: OK.

Manual checks:

- Skill-smoke S2a: VERIFY 92.5 PASS, one rendered motion snap, 0
  presentation-feel failures.
- City-lite S2a: VERIFY 91.2 PASS, 15 rendered motion snaps, 0
  presentation-feel failures.
- Three city-lite transition samples were compared against S1b. The S2a cuts
  enter on visibly active crowd and keyboard-hand motion without black frames,
  source overflow, or content loss.

Regression risks:

- High-motion sources can produce many valid peaks; spacing and source-duration
  checks bound the behavior.
- Scene-cut evidence is still optional, but when supplied it wins over motion.

## Decision Notes

Accepted because:

The final video now consumes the same adjusted source windows recorded by Node
10, and real renders show visible cut-on-motion behavior without technical
regression.

Tradeoffs:

OpenCV decoding adds a small pre-render analysis cost per unique source.

Open questions:

S2b must decide the narrative-chain ownership boundary for audio overlap without
mixing it into this visual-window decision.

## Git / Retrieval

Related files:

- `roadmap.md`
- `video_pipeline_core/edit_artifacts.py`
- `video_pipeline_core/mv_cut.py`

Related commits:

- `feat(sensory): snap cuts to motion peaks`

Graphify anchors:

- Sensory Phase
- S2 micro-rhythm
- Node 10 timeline build

Search tags:

- `decision-log`
- `spec-do-verify`
- `s2a`
- `cut-on-motion`
- `motion-peak`
