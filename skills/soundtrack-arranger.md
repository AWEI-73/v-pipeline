---
name: soundtrack-arranger
description: Use for bounded music, song, BGM, soundtrack mood, section audio sourcing, license/source decisions, reference tracks, and Audio Director handoff. Do not use for existing-video volume repair or subtitle repair.
---

# Soundtrack Arranger Skill

## Tool Contract

<!-- TOOL_CONTRACT_START -->
{
  "version": 1,
  "skill": "soundtrack-arranger",
  "stage_owner": "soundtrack_branch",
  "triggers": [
    "bounded music/song/BGM request needs section soundtrack planning",
    "pipeline needs soundtrack_plan, license manifest, or Audio Director handoff"
  ],
  "canonical_tools": [
    {
      "tool": "tools/soundtrack_arranger.py",
      "when": "write deterministic soundtrack plan, source candidates, license manifest, and Audio Director handoff from a brief or video_intent",
      "inputs": ["brief or section plan", "optional provider credentials", "optional license notes"],
      "outputs": ["soundtrack_plan.json", "music_source_candidates.json", "sound_license_manifest.json", "audio_director_handoff.json"],
      "stop_if": ["license_status is missing", "candidate is reference_only for delivery"]
    },
    {
      "tool": "tools/soundtrack_flow_acceptance.py",
      "when": "run a no-render acceptance from soundtrack plan through reviewed selected audio, handoff acceptance, audio_mix_plan, and pipeline_home",
      "inputs": ["video_intent or brief JSON", "optional reviewed selected audio decision", "soundtrack_probe_report.json for selected music"],
      "outputs": ["soundtrack_flow_acceptance_report.json", "audio_handoff_acceptance.json", "audio_mix_plan.json"],
      "stop_if": ["audio_handoff_acceptance ok=false", "selected audio is missing or unlicensed", "selected music has no soundtrack_probe_report or section_fit"]
    },
    {
      "tool": "tools/soundtrack_probe.py",
      "when": "inspect an accepted music/audio file before placement so agents can see tempo, beats, energy sections, silence, loudness, optional vocals/transcript, and section fit",
      "inputs": ["audio file"],
      "outputs": ["soundtrack_probe_report.json"],
      "stop_if": ["probe pass=false", "sections, editing_fit, or required section_fit are missing"]
    }
  ],
  "supporting_tools": [
    {
      "tool": "tools/audio_cue_patch.py",
      "when": "convert approved section audio cue decisions into a Workbench/Brownfield draft patch",
      "inputs": ["audio cue decisions", "timeline context"],
      "outputs": ["audio_cue_patch.json"],
      "stop_if": ["cue would cover protected speech without ducking policy"]
    }
  ],
  "forbidden_tools": [
    "Do not download or use unlicensed music for delivery",
    "Do not mix final audio from fuzzy soundtrack intent",
    "Do not treat reference-only songs as delivery-allowed"
  ]
}
<!-- TOOL_CONTRACT_END -->

Shared boundary: obey `skills/pipeline-boundary.md`. The `Stage 0 entry lock`
still applies. Do not direct-cut, download music, mix audio, run `contract-run`,
or render from a fuzzy request.

Use this skill when the user asks for music, songs, BGM, voiceover mood,
section-based soundtrack, or references such as "hot-blooded MV music",
"emotional ending", "use a pop song feel", or "do not cover the speech".

## Responsibility

Soundtrack Arranger is the semantic and licensing layer for audio. It decides
what the video should sound like and what source class is allowed. It does not
execute TTS, mixing, ducking, or final assembly. Those belong to
`skills/audio-director.md`.

Canonical artifacts:

- `soundtrack_plan.json`
- `music_source_candidates.json`
- `sound_license_manifest.json`
- `soundtrack_probe_report.json`
- `audio_director_handoff.json`

## Required Contract

Each section should record:

- `section_id`
- `story_function`: intro, warm_story, training_drive, mv_climax, ending_reflection
- `duration_sec`
- `music_role`: bgm, song, diegetic, silence, reference_only
- `vocal_policy`: no_vocal, vocal_ok, instrumental_required, preserve_speech
- `energy_curve`: low, medium, high, build, resolve
- `ducking_policy`: none, duck_under_voice, preserve_original_audio
- `source_type`
- `license_status`
- `handoff_to`: audio-director

When the input is `video_intent.json`, preserve
`soundtrack_contract` as `stage0_soundtrack_contract` in
`soundtrack_plan.json`. Also preserve `communication_intent` as
`source_audio_policy` when present, so later Audio Director / BUILD steps know
whether source footage audio is preserved, replaced by music, or mixed by
section. Carry its `fallback_policy` into `sound_license_manifest.json` and
`audio_director_handoff.json`.

Fallback policy:

- Provider fallback is allowed: try the configured song/BGM provider, then
  manual import, then `reference_only`.
- Role fallback is review-gated. If a requested song cannot be delivered and
  the route proposes BGM/instrumental instead, write
  `role_fallback_requires_review` and stop before Audio Director.
- Brownfield fallback is allowed after review: Workbench may replace or retime
  music without rewriting Stage 0 truth.
- If `speech_preservation=required`, all BGM under speech-critical sections
  must use `duck_under_voice` or `preserve_original_audio`.

Allowed `source_type` values:

- `user_provided`
- `licensed_library`
- `youtube_audio_library`
- `pixabay_music`
- `jamendo_song`
- `suno_udio_external`
- `reference_only`
- `placeholder`

## API And Token Boundary

API keys are an optional API layer, not a prerequisite for route planning.

- Jamendo: use `JAMENDO_CLIENT_ID` only when later API search is enabled.
- Pixabay: use `PIXABAY_API_KEY` only when later provider search is enabled.
- YouTube references: no API key, but keep them `reference_only` unless license
  and use rights are explicit.
- Suno/Udio: external/manual generation source for now; record the account and
  license status, but do not assume an official local API.

Recommended `.env` names:

```env
JAMENDO_CLIENT_ID=
PIXABAY_API_KEY=
YTDLP_PATH=
FFMPEG_PATH=
FFPROBE_PATH=
HERMES_ALLOW_REFERENCE_MUSIC=false
HERMES_ALLOW_UNLICENSED_MUSIC=false
HERMES_DEFAULT_MUSIC_PROVIDER=jamendo
HERMES_DEFAULT_BGM_PROVIDER=pixabay
```

Never commit `.env` values.

## Fail-Closed Rules

- If the user asks for a famous song without a usable file/license, write
  `reference_only` and `delivery_allowed:false`.
- If speech, ceremony audio, applause, vows, chants, or interviews matter,
  set `preserve_speech` or `preserve_original_audio`.
- If license metadata is missing, write the candidate but block delivery.
- If the user only says "make it more powerful", ask for the section role:
  opening, story, training, MV climax, ending, or full-film reference.

## Handoff

`audio_director_handoff.json` must include only accepted or placeholder audio
decisions. Audio Director may then fetch approved files, run TTS, apply ducking,
and output `final_audio.wav` / `audio_mix_report.json`.

Selected deliverable music must be probed before Audio Director handoff.
`audio_handoff_acceptance.json` now fails closed when a selected BGM/song track
does not have `soundtrack_probe_report.json` with `pass=true`, non-empty
`features`, and non-empty `section_fit[]`. Original source speech tracks are
not blocked by the music probe rule; they are governed by
`preserve_original_audio` / ducking policy instead.

## Soundtrack Probe

Before placing a selected song or BGM into `audio_mix_plan.json`, run:

```powershell
python tools\soundtrack_probe.py --audio PATH\song.mp3 --out RUN_DIR\soundtrack_probe_report.json --json
```

The first implementation is intentionally bounded:

- ffprobe duration/codec
- ffmpeg `volumedetect`
- ffmpeg `silencedetect`
- optional librosa tempo, beat times, and RMS energy curve when available
- optional faster-whisper ASR vocal/transcript pass when requested:

```powershell
python tools\soundtrack_probe.py `
  --audio PATH\song.mp3 `
  --out RUN_DIR\soundtrack_probe_report.json `
  --enable-asr `
  --asr-model small `
  --language zh `
  --json
```

It does not yet run source separation, CLAP, or a music-language model. ASR is a
bounded optional layer: it can identify likely vocals, transcript preview,
vocal density, and instrumental windows, but it is not a final lyric or singing
quality judge.

The output is an agent-readable music material map: use it to decide where a
track fits, whether it is too dense under speech, and which window can support
montage/climax/ending. `section_fit[]` translates the probe into video-section
choices such as `opening_intro`, `hotblooded_montage`, `warm_story`,
`speech_underlay`, and `ending_reflection`.

If delivery requires music understanding, set
`delivery_requirements.requires_soundtrack_probe=true`; Delivery Gate will then
block if `soundtrack_probe_report.json` is missing, empty, or lacks
`section_fit`.
