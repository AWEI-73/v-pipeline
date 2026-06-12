# Decision: S2b Narrative J/L Cuts

Date: 2026-06-12
Status: verified
Scope: Sensory Phase S2b / narrative xfade timeline
Superpowers phase: execute

## SPEC

Requirement:

Move narrative visual cuts 0.3-0.7 seconds before or after the corresponding
audio seam.

Why:

The narrative renderer currently aligns every visual transition exactly to the
TTS segment boundary, which makes edits feel mechanically assembled.

Direction:

Keep TTS, subtitles, and source selection unchanged. Build a deterministic
alternating J/L cut plan from `tts_timing.json`, then pass its visual boundary
times into the existing narrative xfade graph.

Non-goals:

- Do not overlap spoken phrases.
- Do not change material selection or source start windows.
- Do not implement S2c speech-tail padding.
- Do not enable J/L cuts for MV or promo renders.

## DO

Files / modules:

- `video_pipeline.py`
- `tests/test_narrative_jl_cut.py`

Function-level plan:

- Derive bounded J/L cut shifts from narrative TTS segment seams.
- Let `build_filter_chain` consume explicit visual boundary offsets.
- Persist the cut plan in narrative timing/edit artifacts.
- Budget render tail across consecutive shifted xfade boundaries without moving
  source starts.

Data / interface changes:

- Narrative `tts_timing.json` gains `jl_cuts`.
- Narrative `edit_log.json` gains `jl_cuts`.

Migration / compatibility:

Non-narrative styles and callers without boundary offsets retain the existing
aligned-cut behavior.

## VERIFY

Pre-checks:

- Confirmed narrative voice is one continuous concatenated TTS track.
- Confirmed visual boundaries are owned by `video_pipeline.build_filter_chain`.

Tests:

- Deterministic plan, bounds, style gating, chained-xfade tail, and xfade wiring:
  PASS.
- Focused regression: 28 tests, PASS.
- Fresh full regression after true-render verification: 624 tests, PASS.
- Real ffmpeg filter smoke held the requested output duration exactly.

Manual checks:

- City-lite narrative rerender:
  `C:\Users\user\Desktop\video_project\city-lite\runs\20260612-sensory-s2b-v1`.
- VERIFY 97.0 PASS, 0 issues; final 35.83s versus TTS 35.81s.
- Three seam waveform/frame A/B checks confirmed two J-cuts and one L-cut:
  next narration leads retained visuals at seams 1 and 3; the office visual
  leads the retained commute narration at seam 2.
- No overlapping speech, black frames, subtitle drift, or content loss.

Regression risks:

- Delayed visual cuts need tail based on the difference between consecutive
  shifts, not only the current positive shift.
- Final output duration must continue matching the voice track.

## Decision Notes

Accepted because:

Moving visual seams against unchanged audio produces actual J/L timing without
creating overlapping narration or changing material selection.

The first true render exposed a chained-xfade tail bug: an L-to-J transition
needs `next_shift - previous_shift + transition` tail. The deterministic tail
test now locks this formula; the corrected rerender restored full duration.

Tradeoffs:

Alternating deterministic shifts are less editorially semantic than a future
agent-selected cut type, but are reproducible and auditable.

Open questions:

S2c will separately add sentence-tail breathing and may refine seam placement.

## Git / Retrieval

Related files:

- `roadmap.md`
- `video_pipeline.py`

Related commits:

- `feat(sensory): add narrative J/L cuts`

Graphify anchors:

- Sensory Phase
- S2 micro-rhythm
- narrative xfade timeline

Search tags:

- `decision-log`
- `spec-do-verify`
- `s2b`
- `j-cut`
- `l-cut`
