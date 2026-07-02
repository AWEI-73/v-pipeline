# Soundtrack Arranger Route

Status: side branch for music, songs, BGM, voiceover intent, and source/license
decisions.

This route exists because video music is not only a file. It is a section-level
contract: what emotion the section needs, whether speech must survive, which
source is legal, and what Audio Director may actually mix.

## Place In The Pipeline

```text
Stage 0 Video Intent Planner
  -> story / material / effect planning
  -> Soundtrack Arranger when audio intent or music source matters
  -> Audio Director for TTS, mixing, ducking, and final_audio.wav
  -> BUILD / Verify
```

Soundtrack Arranger does not replace `skills/audio-director.md`. It prepares
the audio plan and license evidence. Audio Director executes.

Canonical artifacts:

- `soundtrack_plan.json`
- `music_source_candidates.json`
- `sound_license_manifest.json`
- `audio_director_handoff.json`

`soundtrack_plan.json` is the section requirement contract. It must expose:

- `required_track_count`: minimum number of distinct deliverable music tracks
  needed by the current section plan.
- `section_music_requirements[]`: compact requirements for each section.
- `sections[].required_audio`: role, duration, vocal policy, energy curve,
  ducking policy, and speech-preservation requirement.
- `sections[].source_type_priority`: ordered provider/source fallback list.
- `sections[].probe_required`: whether a selected deliverable audio file must
  pass `soundtrack_probe_report.json` before Audio Director handoff.
- `sections[].delivery_allowed_requires_license`: whether the section needs
  explicit source/license evidence before delivery.

## Source Types

| source_type | Use for | Delivery rule |
|---|---|---|
| `user_provided` | User-owned file | Allowed only with user assertion or metadata |
| `licensed_library` | Internal/paid/free library | Requires license metadata |
| `youtube_audio_library` | YouTube Audio Library tracks | Requires track/license record |
| `pixabay_music` | Pixabay Music/BGM | Requires track URL and license snapshot |
| `jamendo_song` | Songs/vocals via Jamendo | Requires Jamendo metadata |
| `suno_udio_external` | User-created external AI music | Requires account/source/license note |
| `reference_only` | Famous song or mood reference | Not deliverable as final soundtrack |
| `placeholder` | Temporary planning audio | Not deliverable |

## API And Token Boundary

Provider credentials are an optional API layer. They are not required to plan a
soundtrack or write canonical artifacts.

Recommended environment names:

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

- Jamendo: get a developer `JAMENDO_CLIENT_ID` before automated search.
- Pixabay: keep the existing `PIXABAY_API_KEY`; use it only after provider
  wiring exists.
- YouTube: no token needed for references, but license must be explicit before
  delivery.
- Suno/Udio: treat as external/manual until a supported integration exists.

## Minimal Section Plan

For a 10 minute graduation/training recap, a good first split is:

```json
{
  "required_track_count": 2,
  "sections": [
    {
      "section_id": "intro",
      "duration_sec": 30,
      "music_role": "bgm",
      "energy_curve": "build",
      "required_audio": {"role": "bgm", "vocal_policy": "no_vocal"},
      "source_type_priority": ["pixabay_music", "licensed_library", "manual_import"],
      "probe_required": true,
      "delivery_allowed_requires_license": true
    },
    {
      "section_id": "mv_climax",
      "duration_sec": 150,
      "music_role": "song",
      "energy_curve": "high",
      "required_audio": {"role": "song", "vocal_policy": "vocal_ok"},
      "source_type_priority": ["jamendo_song", "manual_import", "reference_only"],
      "probe_required": true,
      "delivery_allowed_requires_license": true
    }
  ]
}
```

## CLI

Planning does not require provider tokens:

```powershell
python video_tools.py soundtrack-arrange RUN_DIR\video_intent.json --out-dir RUN_DIR
```

This writes:

```text
RUN_DIR\soundtrack_plan.json
RUN_DIR\music_source_candidates.json
RUN_DIR\sound_license_manifest.json
RUN_DIR\audio_director_handoff.json
```

Provider search and download are optional:

```powershell
python video_tools.py soundtrack-provider-search `
  --plan RUN_DIR\soundtrack_plan.json `
  --out RUN_DIR\music_source_candidates.json `
  --providers jamendo,pixabay `
  --limit 3

python video_tools.py soundtrack-provider-download `
  --candidates RUN_DIR\music_source_candidates.json `
  --candidate-id CANDIDATE_ID `
  --out-dir RUN_DIR

python video_tools.py soundtrack-import-url `
  --url "https://www.youtube.com/watch?v=..." `
  --section-id mv_climax `
  --source-type youtube_audio_library `
  --usage-scope internal_only `
  --license-note "user confirmed internal classroom use" `
  --out-dir RUN_DIR

python video_tools.py soundtrack-audio-handoff-accept `
  --handoff RUN_DIR\audio_director_handoff.json `
  --soundtrack-plan RUN_DIR\soundtrack_plan.json `
  --license-manifest RUN_DIR\sound_license_manifest.json `
  --out-dir RUN_DIR
```

Jamendo search uses `JAMENDO_CLIENT_ID` and official `tracks` API metadata.
Pixabay audio search is intentionally fail-closed because the documented
official API surface does not expose music search/download. Manually reviewed
Pixabay audio can still be represented as a candidate with `direct_download_url`
and downloaded by `soundtrack-provider-download`.

Provider priority:

- Songs/vocals: Jamendo first.
- BGM/manual licensed/internal-only fallback: `soundtrack-import-url` through
  yt-dlp.
- `soundtrack-import-url` requires `license_note` or `license_url`.
- `reference_only` is never imported into deliverable audio.

`soundtrack-audio-handoff-accept` writes `audio_handoff_acceptance.json` and
`audio_mix_plan.json`. This is still no-render; it only proves the selected
audio is ready for Audio Director mixing.

End-to-end no-render boundary acceptance:

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

This writes the Soundtrack Arranger artifacts, a reviewed selected-audio
handoff, `audio_handoff_acceptance.json`, `audio_mix_plan.json`, and
`soundtrack_flow_acceptance_report.json`, then verifies the run surface through
`pipeline_home.py`. It does not download real music, mix audio, run ffmpeg, or
render `final.mp4`. Omit `--fake-reviewed-audio` in real runs and point the
handoff at an actual reviewed/downloaded audio file.

## Gates

Block handoff to Audio Director when:

- `sound_license_manifest.json` lacks license/source evidence for deliverable
  music.
- A famous/commercial song is marked as final instead of `reference_only`.
- A speech-critical segment lacks `ducking_policy` or `preserve_original_audio`.
- Section durations do not add up to the target audio structure.

Pass handoff when `audio_director_handoff.json` contains accepted section
decisions and every deliverable candidate has license metadata.
