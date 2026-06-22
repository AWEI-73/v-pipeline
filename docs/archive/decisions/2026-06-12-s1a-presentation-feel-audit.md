# Decision: S1a Presentation-Feel Audit

Date: 2026-06-12
Status: verified
Scope: Sensory Phase S1a
Superpowers phase: verify

## SPEC

Add a deterministic Node 12 audit that detects common presentation-like video
patterns without changing render behavior.

Required checks:

- `static_photo_too_long`
- `no_foreground_motion`
- `centered_caption_card`
- `repeated_push_in`
- `text_blocks_dominate`
- `single_layer_composition`

The audit must be profile-gated, indexed in `artifact_manifest.json`, surfaced
under dashboard Node 12, and inert by default.

## DO

Implemented `video_pipeline_core/presentation_feel_audit.py` and wired it
through build profiles, edit trace, contract-run P1 audits, artifact manifests,
dashboard state, Node 12 registry, and runtime audit routing.

Added deterministic tests for all detector families, stable JSON output,
profile defaults, timeline trace, contract-run wiring, and dashboard routing.

Added `examples/sensory_s1a_build_profile.json` as the repeatable real-render
profile.

## VERIFY

Deterministic verification:

- Focused regression: 92 tests passed.
- Full suite: 605 tests passed.
- Python compile check passed.

Real-render baselines:

- `C:\Users\user\Desktop\video_project\skill-smoke\runs\20260612-sensory-s1a-v1`
  - VERIFY 92.5 PASS.
  - Presentation-feel audit: 0 fail, one `single_layer_composition` warning.
  - Keyframe review: coherent coffee process progression; no presentation-card
    failure.
- `C:\Users\user\Desktop\video_project\city-lite\runs\20260612-sensory-s1a-v2`
  - VERIFY 91.2 PASS.
  - Presentation-feel audit: 0 fail, one `single_layer_composition` warning.
  - Keyframe review: real foreground motion prevented a false static-video
    failure; repeated office imagery remains valid S1b input.

Old-film comparison:

- `C:\Users\user\Desktop\video_project\bakery\runs\smoke_test`
  - Three blocking findings: two `static_photo_too_long` findings and one
    `repeated_push_in` finding.
  - Existing old-run metadata proves three detector hits but only two distinct
    detector types. The deterministic fixture covers four distinct detector
    types; do not claim the old film proves three distinct types.

## Decision Notes

Accepted because S1a now measures presentation feel on real renders while
remaining deterministic and profile-gated.

The real baselines expose the next S1b target: single-layer composition and
repeated source windows are warnings, but S1a should not mutate the timeline.
