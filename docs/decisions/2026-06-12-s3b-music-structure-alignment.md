# Decision: S3b Music Structure Alignment

Date: 2026-06-12
Status: verified
Scope: Sensory Phase S3b / narrative single-track BGM
Superpowers phase: execute

## SPEC

Use the existing `music_structure.sections` artifact to start one BGM track
from a structural point that aligns the narrative `climax` with the track's
highest-energy section.

Non-goals:

- No multi-track song switching.
- No cloud audio analysis.
- No dynamic volume automation beyond the existing ducking path.

## DO

- Populate section `energy_score` deterministically with local ffmpeg
  `volumedetect` mean volume.
- Find the narrative climax from `section_role`, editing intent, or title.
- Select the highest-energy music section.
- Snap the required source offset to the nearest music section start.
- Persist `music_alignment_plan.json`.
- Pass the offset into the existing single-track `mix-audio` loop/crossfade
  graph.

Fallback:

Missing BGM, climax, timing, structure, or energy keeps offset `0.0` and records
the reason. Existing no-offset behavior remains unchanged.

## VERIFY

Tests:

- Planner climax/high-energy alignment and zero-offset fallback.
- Section energy annotation with an injected detector.
- Offset loop graph and real ffmpeg offset mix.
- Focused regression: 13 tests PASS.
- Full regression: 637 tests PASS.

True render:

- Run:
  `C:\Users\user\Desktop\video_project\city-lite\runs\20260612-sensory-s3b-v1`
- Same city-lite content and BGM; segment 3 marked `climax`.
- Climax starts at `19.080s`.
- Highest-energy section starts at `130.194s`.
- Selected structural offset: `110.991s`.
- Alignment error: `0.123s`.
- Final duration: `37.20s`.
- B technical dimensions: all 100; complete QA 92.5 PASS, with the sole issue
  being unrelated seg3 content alignment.
- Offset-0 A technical VERIFY: 100 PASS, 0 issues.

Sensory A/B:

- Offset-0 source window at climax: mean `-15.6dB`.
- Aligned source window at climax: mean `-9.8dB`.
- Final mixed climax window moves only from mean `-26.5dB` to `-26.1dB`;
  narration peaks remain unchanged at `-13.1dB`.
- Waveform review shows a more continuous music bed under the climax without
  masking narration or creating unsafe peaks.

## Decision Notes

Accepted because the result makes a single BGM track follow narrative shape
without introducing song switching or opaque agent timing.

The planner intentionally snaps to section starts instead of arbitrary sample
offsets. This keeps the decision deterministic and auditable, at the cost of a
small alignment error.

## Git / Retrieval

Related files:

- `video_pipeline_core/music_structure.py`
- `video_pipeline_core/vt_audio.py`
- `video_pipeline.py`
- `tests/test_music_alignment.py`

Search tags:

- `sensory-phase`
- `s3b`
- `music-structure`
- `climax`
- `bgm-offset`
