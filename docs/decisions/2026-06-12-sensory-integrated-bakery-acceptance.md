# Decision: Sensory Integrated Bakery Acceptance

Date: 2026-06-12
Status: verified
Scope: fresh MV/local-material/light-effects end-to-end acceptance

## SPEC

Run a fresh film from contract through true render and require technical VERIFY,
deterministic editorial audits, and agent sensory review to agree. Do not count
a technically valid render as accepted while editorial failures remain.

## DO

- Used the bakery contract and local material library as a fresh Sensory
  integration baseline.
- Synthesized stereo silence when a `keep_audio` source has no audio stream.
- Raised fast-tempo photo-stack shots to the 0.8s reviewable floor.
- Prevented motion-peak snaps from overlapping other planned source windows.
- Preserved explicit `group_photo` hold reasons into `timeline_build`.
- Scoped assembly beat grids to the actual rendered timeline.

## VERIFY

- Accepted run:
  `C:\Users\user\Desktop\video_project\bakery\runs\20260612-integrated-sensory-v5`
- Technical VERIFY: 100 PASS.
- Editor review: PASS, all nine clips clean.
- Treatment audit: PASS, zero findings.
- Editorial QA: 85 PASS; the long group-photo close remains a visible
  acknowledged warning.
- Light effects: 5/5 rendered, zero gaps.
- Agent keyframe review confirmed a coherent bakery-to-process-to-close flow.
- Full regression: 663 tests PASS.

## Boundary

This is the integrated acceptance for the MV/local-material/light-effects
branch. Narrative-only S2b/S2c/S3a/S3b mechanisms cannot execute in the same MV
render branch; their existing narrative true-render evidence remains their
acceptance record.

Search tags: `sensory`, `integrated-acceptance`, `bakery`, `mv`, `pacing`
