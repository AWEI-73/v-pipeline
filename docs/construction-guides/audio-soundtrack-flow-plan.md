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
- Soundtrack Probe now has an optional ASR layer:
  `tools/soundtrack_probe.py --enable-asr --asr-model small --language zh`.
  It writes `features.vocal_analysis` and `section_fit[]`. Soundtrack
  Arranger owns producing this probe; Verify / Delivery Gate owns blocking
  required music-understanding delivery when the probe or `section_fit` is
  missing.
- Soundtrack Probe is sealed as MVP for now. Do not expand into deep genre
  classification before the route is wired into Stage 0 / Audio Director /
  Verify.
- Audio handoff now requires a probe for selected deliverable music. A BGM/song
  track can remain a candidate without a probe, but it cannot become an
  `audio_mix_plan.tracks[]` item until `soundtrack_probe_report.json` passes
  and includes `section_fit[]`.

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
- `soundtrack_probe_report.json`: agent-readable audio material map containing
  tempo, beat/energy sections, loudness/silence, optional vocal/transcript
  analysis, and section fit suggestions.
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
- Selected deliverable BGM/song requires `soundtrack_probe_report.json` before
  Audio Director handoff. Original speech preservation is governed by source
  audio policy and ducking, not by the music probe.
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
    "original_audio_policy": "preserve_speech | mixed | replace_with_music | preserve_if_detected | none | undecided",
    "music_policy": "bgm | song | mixed | reference_only | none | undecided",
    "speech_priority": "high | medium | low | unknown",
    "ducking_policy": "duck_under_voice | none",
    "time_authority": "video_sections | music_sections",
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
- `communication_intent` is the whole-video/default policy. `segment_contract`
  may override it per section, but missing per-segment policy should inherit
  this Stage 0 surface instead of guessing at BUILD time.
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
- If `original_audio_policy=replace_with_music`, BUILD should not map source
  video audio into the final deliverable unless Workbench or a later reviewed
  patch changes the policy.
- If `original_audio_policy=mixed`, each audio section must declare whether it
  preserves original speech, ducks music under speech, or replaces source audio.
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
write or download a reviewed audio file, run Soundtrack Probe, then pass through
the same acceptance gate without fake media:

```powershell
python tools\soundtrack_probe.py `
  --audio RUN_DIR\audio\sources\jamendo_mv_climax.mp3 `
  --out RUN_DIR\soundtrack_probe_report.json `
  --json

python tools\soundtrack_flow_acceptance.py `
  --input RUN_DIR\video_intent.json `
  --out-dir RUN_DIR `
  --selected-section-id mv_climax `
  --source-type jamendo_song `
  --license-note "Jamendo metadata reviewed for this run" `
  --selected-audio-file RUN_DIR\audio\sources\jamendo_mv_climax.mp3 `
  --soundtrack-probe-report RUN_DIR\soundtrack_probe_report.json `
  --json
```

## Next Construction Steps

1. Add real provider/manual import fixtures for one Jamendo candidate and one
   internal-only URL import.
2. Add VERIFY checks for speech ducking, audible clipping, and missing licensed
   evidence.

## Soundtrack Probe / Verify Split

Soundtrack Arranger should run the probe after a candidate audio file is
accepted and before Audio Director places it:

```powershell
python tools\soundtrack_probe.py `
  --audio RUN_DIR\audio\sources\selected.mp3 `
  --out RUN_DIR\soundtrack_probe_report.json `
  --enable-asr `
  --asr-model small `
  --language zh `
  --json
```

Use `--enable-asr` only when vocals, lyrics, singing, or speech conflict matter.
Without ASR, the probe still provides duration, loudness, silence, tempo, beat
times, energy sections, `editing_fit`, and `section_fit`.

When a deliverable depends on this music understanding, write:

```json
{
  "requires_soundtrack_probe": true
}
```

into `delivery_requirements.json`. Delivery Gate then blocks if
`soundtrack_probe_report.json` is missing, `pass` is false, `features` /
`sections` / `editing_fit` are empty, or required `section_fit[]` is missing.

## Validated Probe Example

Run folder:

```text
runs/ytdlp_music_probe_20260628_good_pace
```

Source:

```text
Good Pace - Thomas Gresen | Background Music For Videos No Copyright Trap Music Instrumental Free
https://www.youtube.com/watch?v=CNA1ZZ8ioq8
```

Observed probe result:

- `analysis_depth=basic_ffmpeg+music_features+vocal_asr`
- `duration_sec=161.808`
- `tempo_bpm=99.384`
- `features.vocal_analysis.has_vocals=false`
- `transcript_preview=""`
- `section_fit.hotblooded_montage.fit=medium`
- `section_fit.speech_underlay.fit=high`
- `peak_dbfs=0.0`, so Audio Director should reduce/limit before final mix

External listening review agreed with the probe: the track is instrumental,
mid-tempo Chill Trap / Lo-Fi Trap / Future Bass style, suitable for steady
movement or neutral modern background, not a hard explosive climax. Treat this
as the acceptance example for how agents should interpret
`soundtrack_probe_report.json`.

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
`audio_mix_plan.json` also carries `source_audio_policy` so BUILD and Workbench
can see whether source footage audio should be preserved, ducked, replaced, or
handled section-by-section.

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

## Final AV Assembly Smoke

When visual BUILD has already produced a bounded visual draft such as
`video_cut.mp4`, and Audio Director has produced `final_audio.wav`, use the
small final assembly tool instead of hand-writing an ffmpeg command:

```powershell
python tools\final_av_assemble.py `
  --video RUN_DIR\video_cut.mp4 `
  --audio RUN_DIR\final_audio.wav `
  --out RUN_DIR\final.mp4 `
  --report RUN_DIR\assembly_report.json `
  --title "HERMES E2E HIGHLIGHT" `
  --label "0:15:OPENING" `
  --label "15:30:ACTION" `
  --source-audio-policy replace_with_music `
  --json
```

This tool only assembles already-approved streams. It does not choose clips,
music, voiceover, or effects. It always maps the selected audio as `1:a:0` and
does not map source-video audio, so `assembly_report.json` must record
`source_audio_mapped:false`. If Stage 0 declares `preserve_speech` or `mixed`,
the upstream audio plan must first produce a mixed `final_audio.wav`; final
assembly still maps only that accepted output.

After final assembly, regenerate delivery evidence:

```powershell
python video_tools.py keyframe-grid RUN_DIR\final.mp4 --out RUN_DIR\keyframe_grid.jpg
python video_tools.py visual-audit RUN_DIR\final.mp4 --out RUN_DIR\visual_audit.json --grid RUN_DIR\keyframe_grid.jpg
python video_tools.py verify-evidence RUN_DIR\final.mp4 --timeline RUN_DIR\timeline_build.json --out-dir RUN_DIR
python video_tools.py effect-render-verification `
  --effect-intent-plan RUN_DIR\effect_intent_plan.json `
  --remotion-review RUN_DIR\remotion_effect_review.json `
  --out RUN_DIR\effect_render_verification.json `
  --root RUN_DIR
python tools\write_delivery_gate_report.py --run RUN_DIR --out-name delivery_gate.json --json
python tools\pipeline_home.py --run RUN_DIR --json
python tools\preview_timeline.py build --artifact-root RUN_DIR --out RUN_DIR\preview_timeline.json
```

Expected final state:

- `delivery_gate.json` has `pass:true`.
- `pipeline_home.py` returns `mode=done`, `cursor=complete`, and
  `source=delivery_gate.json`.
- `preview_timeline.json` exposes video clips, audio placements, and effect
  markers for Workbench review.

## Soundtrack Probe / Music Material Map

Music should not be placed only by duration or waveform existence. Before a
selected track becomes part of the final mix, build a lightweight music material
map:

```powershell
python tools\soundtrack_probe.py `
  --audio RUN_DIR\audio\sources\selected_music.mp3 `
  --out RUN_DIR\soundtrack_probe_report.json `
  --json
```

The current probe is deliberately local and bounded. It records:

- audio duration and codec from ffprobe;
- mean/peak dBFS from ffmpeg `volumedetect`;
- silence count/ratio from ffmpeg `silencedetect`;
- optional librosa tempo, beat timestamps, and RMS energy curve;
- coarse sections such as `intro`, `build`, `candidate_climax`, and
  `outro_or_resolve`;
- `editing_fit` hints for montage, speech underlay, and ending reflection.

This is not a final music taste judge. It is a decision artifact for Stage 0.5,
Soundtrack Arranger, Workbench, and Delivery Gate. To require it at final
delivery, set:

```json
{
  "requires_soundtrack_probe": true
}
```

Delivery Gate then blocks if `soundtrack_probe_report.json` is missing, did not
pass, has no sections, or has no `editing_fit`.
