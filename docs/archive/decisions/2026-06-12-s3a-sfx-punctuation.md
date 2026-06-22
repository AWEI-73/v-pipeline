# Decision: S3a SFX Punctuation

Date: 2026-06-12
Status: verified
Scope: Sensory Phase S3a / narrative final audio
Superpowers phase: execute

## SPEC

Requirement:

Add restrained deterministic SFX punctuation: whoosh at chapter transitions
and hit at explicit title-card entrances.

Why:

The current final audio has voice and BGM only, so structural visual events lack
audible punctuation.

Direction:

Generate an auditable `sfx_plan.json` from narrative script roles, timing, and
explicit text effects. Rotate through a small local CC0 library and mix cues at
volume 0.15 into `final_audio.wav`.

Non-goals:

- Do not add SFX to every cut.
- Do not implement music-structure alignment or multi-track song switching.
- Do not use cloud audio generation.

## DO

Files / modules:

- `video_pipeline_core/sfx.py`
- `video_pipeline_core/vt_audio.py`
- `video_tools.py`
- `video_pipeline.py`
- `assets/sfx/`

Function-level plan:

- Plan whoosh/hit cues deterministically.
- Build delayed SFX inputs and explicit stereo channel summing.
- Add a `sfx-mix` tool and invoke it after the stable voice/BGM mix.
- Persist plan and local asset provenance.

Data / interface changes:

- Narrative runs gain `sfx_plan.json`.

Migration / compatibility:

Runs with no cues retain the existing final audio unchanged.

## VERIFY

Pre-checks:

- Confirmed no existing SFX library or narrative SFX wiring.

Tests:

- Cue rules, deterministic asset rotation, filter delay/mix graph.
- Real SFX mix render: PASS.
- Focused regression: 27 tests, PASS.
- Fresh full regression: 631 tests, PASS.

Manual checks:

- City-lite S3a render:
  `C:\Users\user\Desktop\video_project\city-lite\runs\20260612-sensory-s3a-v1`.
- Two sparse whoosh cues landed at 9.912s and 28.512s.
- A/B audio probes confirmed the no-cue base RMS is preserved within 0.04 dB
  and cue regions do not create unsafe peaks.
- Final technical VERIFY 98.5 PASS, 0 issues; audio levels remain passing at
  90 (`max -3.8dB`).

Regression risks:

- Overuse can make narrative audio feel templated.
- SFX peaks can harm audio-level verification.

## Decision Notes

Accepted because:

Explicit structural cues add audible punctuation while keeping the plan sparse,
deterministic, and reviewable.

True-render A/B exposed two bundled-ffmpeg constraints: `amix` lacks
`normalize=0`, and mono-to-stereo `aformat` lowers the base by 3 dB. The final
graph uses `amerge + pan` and explicit mono channel duplication, preserving the
base track while adding cues.

Tradeoffs:

The first version uses mechanical role changes rather than semantic agent
selection.

Open questions:

S3b may adjust cue timing against music sections.

## Git / Retrieval

Related files:

- `roadmap.md`
- `video_pipeline_core/sfx.py`
- `video_pipeline_core/vt_audio.py`

Related commits:

- `feat(sensory): add SFX punctuation`

Graphify anchors:

- Sensory Phase
- S3 audio layer
- final audio

Search tags:

- `decision-log`
- `spec-do-verify`
- `s3a`
- `sfx`
- `whoosh`
- `hit`
