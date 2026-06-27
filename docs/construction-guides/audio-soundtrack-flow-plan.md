# Audio / Soundtrack Flow Plan

Status: active construction guide for the bounded Soundtrack Arranger to Audio
Director handoff.

Current progress:

- Section-aware `audio_mix_plan.sections[]` execution is implemented.
- `soundtrack_flow_acceptance.py` now accepts a real reviewed/downloaded audio
  file via `--selected-audio-file`, so bounded runs no longer need the
  test-only fake audio path.
- `audio_handoff_acceptance.py` now carries timed `soundtrack_plan.sections[]`
  into `audio_mix_plan.sections[]`, so Audio Director can produce
  `section_timeline` placements instead of an opaque single-track mix.
- Real Jamendo multi-section demo passed:
  `runs/section_audio_e2e/20260627-real-jamendo-sections`.
- Real selected-file acceptance passed:
  `runs/audio_selected_file_acceptance/20260627-selected-jamendo`.
  It used an existing Jamendo MP3, wrote `audio_handoff_acceptance.json`,
  `audio_mix_plan.json`, `final_audio.wav`, and `audio_mix_report.json`, then
  `pipeline_home.py` returned `cursor=audio_ready` /
  `next=return_to_build_with_final_audio`.
- Real selected-file section-timeline acceptance passed:
  `runs/audio_selected_file_acceptance/20260627-selected-jamendo-sections`.
  `audio_mix_report.json` records `mix_mode=section_timeline`, `placements[]`,
  and `section_verification`, so Workbench can show where the selected music
  lands in the story sections.
- Real speech-ducking audio-only acceptance passed:
  `runs/audio_ducking_acceptance/20260627-speech-ducking`.
  It mixes a music bed with preserved original speech in the same section.
  `audio_mix_report.json` records `ducking_applied=true`, music
  `applied_volume=0.28`, preserved speech `applied_volume=1.0`, and
  `pipeline_home.py` returns `cursor=audio_ready`.
- Audio-to-BUILD dry handoff passed:
  `runs/audio_to_build_handoff/20260627-audio-ready-dry-build`.
  `contract-dry-build` consumes `final_audio.wav` and `audio_mix_report.json`,
  writes `audio_build_handoff.json`, records `final_audio`,
  `audio_mix_report`, and `audio_build_handoff` in `artifact_manifest.json`,
  does not render `final.mp4`, and `pipeline_home.py` returns
  `cursor=audio_build_handoff` / `next=continue_build_or_material_gate`.
- The demo produced `final_audio.wav`, `audio_mix_report.json`,
  `section_verification`, and `placements[]`.
- `pipeline_home.py` returned `cursor=audio_ready` and
  `next=return_to_build_with_final_audio`.
- This proves Soundtrack/Audio can download real provider music, assemble
  section-level music, apply ducking evidence, and keep delivery headroom.
- Still open: replace test-only voice placeholders with real TTS/original
  speech and run a full-video E2E where BUILD consumes `final_audio.wav`.

## Goal

Do not build a separate "music factory" yet. Keep audio as a routed side branch:

```text
Stage 0 / existing run
  -> Soundtrack Arranger
  -> reviewed selected audio + license evidence
  -> Audio handoff acceptance
  -> audio_mix_plan.json
  -> Audio Director mixing later
```

The current goal is no-render correctness: prove the artifacts and gates are
connected before doing real ffmpeg mixing.

## Canonical Artifacts

- `soundtrack_plan.json`: section-level emotional/audio contract.
- `music_source_candidates.json`: provider/manual candidates.
- `sound_license_manifest.json`: source and license evidence.
- `audio_director_handoff.json`: accepted or blocked handoff to Audio Director.
- `audio_handoff_acceptance.json`: no-render gate result.
- `audio_mix_plan.json`: mix instructions for Audio Director.
- `soundtrack_flow_acceptance_report.json`: end-to-end no-render acceptance.

## Boundary Rules

- Soundtrack Arranger plans music/song/BGM/source/license only.
- Audio Director owns TTS, ducking, final audio mix, and `final_audio.wav`.
- Famous songs and unlicensed sources stay `reference_only`.
- Internal-only YouTube or manual library audio requires `license_note` or
  `license_url`.
- Speech-critical sections require ducking or original-audio preservation.
- No Soundtrack tool may render `final.mp4` or mix deliverable audio.

## Stage 0 Communication Policy

Stage 0 should decide whether the video communicates mainly through existing
sound, voiceover, subtitles, music, or visual rhythm before it enters
Soundtrack Arranger, Audio Director, Subtitle Director, Material Map, or BUILD.
This is an intent-routing decision, not an audio implementation step.

Recommended Stage 0 fields:

```json
{
  "communication_intent": {
    "voiceover_policy": "required | optional | none | undecided",
    "subtitle_policy": "required | optional | none | undecided",
    "original_audio_policy": "preserve_speech | mixed | replace_with_music | none | undecided",
    "music_policy": "bgm | song | reference_only | none | undecided",
    "speech_priority": "high | medium | low | unknown",
    "handoff_to": [
      "material_map",
      "soundtrack_arranger",
      "audio_director",
      "subtitle_director"
    ]
  }
}
```

Ownership split:

- Stage 0 owns the decision that audio/text communication is needed.
- Material Map may record material sound facts such as speech, ambience,
  noisy audio, usable original sound, and protected moments. It does not write
  narration, subtitle layout, music choices, or mix policy.
- Segment Contract carries the decision per segment: narration intent,
  subtitle intent, original-audio policy, music intent, and effect intent.
- Soundtrack Arranger owns music/song/BGM sourcing, section mood, license
  status, and `audio_director_handoff.json`.
- Audio Director owns TTS, accepted music/original-audio mixing, ducking,
  `final_audio.wav`, and `audio_mix_report.json`.
- Subtitle Director owns subtitle text, line breaks, screen safety, and
  readability. Subtitle repair is not Soundtrack Arranger work.

Stage 0 should ask only route-changing questions. Good questions:

- Should the video rely on voiceover, existing speech, subtitles, music, or
  mostly visuals?
- If there is speech in the footage, should it be preserved or can music cover
  it?
- Is music only a mood reference, or do we have a usable licensed/user-provided
  track?
- Are subtitles required for accessibility/teaching, or only optional style?

Fail-closed routing:

- If `voiceover_policy=required`, do not enter final BUILD without an Audio
  Director or TTS handoff.
- If `subtitle_policy=required`, do not treat text matching as enough; Subtitle
  Director or verify must prove on-screen readability.
- If `original_audio_policy=preserve_speech`, music placement must use ducking
  or speech-safe sections.
- If `music_policy=song` and no licensed/user-provided source exists, keep the
  source `reference_only` and block deliverable audio until reviewed.

## Acceptance Command

```powershell
python tools\soundtrack_flow_acceptance.py `
  --input RUN_DIR\video_intent.json `
  --out-dir RUN_DIR `
  --selected-section-id mv_climax `
  --source-type youtube_audio_library `
  --license-note "user confirmed internal classroom use" `
  --fake-reviewed-audio `
  --json
```

Use `--fake-reviewed-audio` only for no-render tests. Real runs should first
write or download a reviewed audio file, then pass through the same acceptance
gate without fake media:

```powershell
python tools\soundtrack_flow_acceptance.py `
  --input RUN_DIR\video_intent.json `
  --out-dir RUN_DIR `
  --selected-section-id mv_climax `
  --source-type jamendo_song `
  --license-note "Jamendo metadata reviewed for this run" `
  --selected-audio-file RUN_DIR\audio\sources\jamendo_mv_climax.mp3 `
  --json
```

## Next Construction Steps

1. Add real provider/manual import fixtures for one Jamendo candidate and one
   internal-only URL import.
2. Add VERIFY checks for speech ducking, audible clipping, and missing licensed
   evidence.

## Mix Execution

After `audio_mix_plan.json` is ready, Audio Director may create the audio-only
delivery artifact:

```powershell
python tools\audio_mix_plan_execute.py `
  --plan RUN_DIR\audio_mix_plan.json `
  --acceptance RUN_DIR\audio_handoff_acceptance.json `
  --out-dir RUN_DIR `
  --json
```

This writes `final_audio.wav` and `audio_mix_report.json`. It does not render
video or write `final.mp4`. `pipeline_home.py` should then move from
`audio_mix` to `audio_ready` with `next=return_to_build_with_final_audio`.

When `audio_mix_plan.json` contains `sections[]`, the executor uses section
timing instead of simple concat:

```json
{
  "ready_for_mix": true,
  "sections": [
    {"section_id": "opening", "start_sec": 0.0, "duration_sec": 30.0},
    {"section_id": "mv_climax", "start_sec": 420.0, "duration_sec": 90.0}
  ],
  "tracks": [
    {
      "section_id": "opening",
      "audio_file": "audio/sources/opening.wav",
      "role": "music_bed",
      "fade_in_sec": 1.0,
      "fade_out_sec": 1.5
    }
  ]
}
```

Each track is placed at its section start, trimmed to section duration, and
optionally faded. `audio_mix_report.json` records `mix_mode=section_timeline`
and `placements[]` so Workbench can show where the music actually landed. If
`sections[]` is absent, the tool keeps the older single-track or concat behavior
for simple handoffs.

Set `audio_required:true` on sections that must have music, voice, original
audio, or deliberate sound. Audio Director writes `section_verification` into
`audio_mix_report.json` and blocks with `required_section_has_no_audio` if a
required section has no placement. Sections that should be silent should either
omit `audio_required` or mark the policy explicitly in the upstream contract.

For speech-critical sections, set the music track to
`ducking_policy=duck_under_voice` and include a protected voice/original-audio
track in the same section. The executor lowers that music placement to the
default ducked volume and records `ducking_applied=true` plus `applied_volume`
in `placements[]`. This is the current bounded Audio Director behavior; deeper
sidechain automation can be added later without changing the artifact contract.

The executor also records `mean_dbfs` and `peak_dbfs` from ffmpeg
`volumedetect`. It applies a bounded loudness/headroom pass during audio-only
mixing so accepted output should stay below the delivery peak limit. Delivery
VERIFY treats `peak_dbfs > -0.5` as blocking and also blocks any
`duck_under_voice` placement where `ducking_applied` is not true.

## BUILD Handoff

After `final_audio.wav` and `audio_mix_report.json` exist, BUILD must use the
accepted audio instead of falling back to a legacy `--music` file. The canonical
handoff artifact is:

```json
{
  "artifact_role": "audio_build_handoff",
  "selected_audio": "RUN_DIR/final_audio.wav",
  "selection_reason": "audio_ready_final_audio",
  "audio_ready": true,
  "rendered_video": false
}
```

`contract-dry-build` writes `audio_build_handoff.json` and records it in
`artifact_manifest.json` alongside `final_audio` and `audio_mix_report`. This is
still no-render; it only proves Stage 4 can see the accepted audio before a real
`contract-run`.

Minimal verification:

```powershell
python video_tools.py contract-dry-build RUN_DIR\segment_contract.json `
  --categories examples\material_categories.json `
  --out-dir RUN_DIR

python tools\pipeline_home.py --run RUN_DIR --json
```

Expected:

- `audio_build_handoff.json` exists.
- `artifact_manifest.json` contains `final_audio`, `audio_mix_report`, and
  `audio_build_handoff`.
- `final.mp4` is absent.
- `pipeline_home.py` reports `cursor=audio_build_handoff` and
  `next=continue_build_or_material_gate`.
