# Decision: S2c Speech Tail Breathing

Date: 2026-06-12
Status: verified
Scope: Sensory Phase S2c / narrative TTS timing
Superpowers phase: execute

## SPEC

Requirement:

Leave a 0.3-0.5 second breathing pause after each non-final narrative segment
before the next transition.

Why:

The current TTS concat and segment timing end exactly on the last spoken sample,
so even J/L visual seams cannot create an audible sentence-ending breath.

Direction:

Insert a deterministic requested 0.4 second silent MP3 after each non-final
spoken segment. Probe its encoded duration and extend segment timing by that
actual amount while keeping phrase subtitle end times on the spoken audio.

Non-goals:

- Do not add silence after the final segment.
- Do not stretch spoken phrases or subtitles.
- Do not change J/L cut direction or material selection.

## DO

Files / modules:

- `video_pipeline_core/vt_audio.py`
- `tests/test_vt_audio_timing.py`

Function-level plan:

- Finalize segment timing with explicit speech-end and tail-padding fields.
- Render one Edge-TTS-compatible silent MP3 and reuse it between segments.
- Include silent tails in `voice.mp3` and `tts_timing.json`.

Data / interface changes:

- Timing segments gain `speech_end_sec` and `tail_padding_sec`.

Migration / compatibility:

Existing phrase timing remains unchanged. The final segment has zero padding.

## VERIFY

Pre-checks:

- Confirmed Edge TTS output is MP3, mono, 24kHz, 48kbps.

Tests:

- Timing padding and final-segment exemption.
- Real ffmpeg silence render duration: PASS.
- Focused regression: 28 tests, PASS.
- Fresh full regression: 627 tests, PASS.

Manual checks:

- City-lite narrative rerender:
  `C:\Users\user\Desktop\video_project\city-lite\runs\20260612-sensory-s2c-v1`.
- VERIFY 97.0 PASS, 0 issues; final 37.20s versus timing/voice 37.176s.
- Three non-final segments each carry an audio-probed 0.456s tail.
- Three sentence-tail waveform/frame checks confirmed silence, continuing
  visuals, cleared subtitles, and intact S2b J/L behavior.

Regression risks:

- Silent MP3 encoding delay can drift from requested padding.
- Narrative duration grows by the probed 0.3-0.5 second tail per non-final
  segment.

## Decision Notes

Accepted because:

Real silence in the voice track makes the breathing pause audible and keeps all
downstream duration owners aligned.

The first true render exposed MP3 encoder padding: a requested 0.4s file probes
as 0.456s. Timing now records the probed duration, keeping segment sum and
`voice.mp3` exactly aligned while remaining inside the 0.3-0.5s requirement.

Tradeoffs:

A fixed deterministic pause is less expressive than semantic pause selection,
but remains inside the roadmap range and is reproducible.

Open questions:

Future audio direction may vary padding based on punctuation or delivery style.

## Git / Retrieval

Related files:

- `roadmap.md`
- `video_pipeline_core/vt_audio.py`

Related commits:

- `feat(sensory): add speech-tail breathing`

Graphify anchors:

- Sensory Phase
- S2 micro-rhythm
- TTS timing

Search tags:

- `decision-log`
- `spec-do-verify`
- `s2c`
- `speech-tail`
- `breathing-pause`
