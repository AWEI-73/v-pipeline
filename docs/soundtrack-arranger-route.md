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

If Stage 0 sets `soundtrack_contract.contract_status=not_applicable` or
`music_role=none`, Soundtrack Arranger must produce a no-audio/silence plan with
`required_track_count=0`. Do not create provider/license/probe requirements for
music the route explicitly does not need.

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
| `source_folder_audio` | Music/audio discovered under the active source root | Internal/rehearsal use may proceed with `music_use_basis.status=human_declared_allowed`; still requires source-relative evidence and probe before mix |
| `suno_udio_external` | User-created external AI music | Requires account/source/license note |
| `reference_only` | Famous song or mood reference | Not deliverable as final soundtrack |
| `placeholder` | Temporary planning audio | Not deliverable |

## Source-Root Music Discovery

When the current brief or `video_intent.json` provides an active `source_root`,
Soundtrack Arranger first scans inside that folder for likely source-folder
music/audio before external provider fallback. The scan is source-root scoped:
it does not hard-code a user Downloads path and does not inspect outside the
provided root.

Selected source-root candidates are written as `source_type=source_folder_audio`
and preserve both:

- `path`: absolute evidence path for the local run.
- `source_relative_path`: stable evidence relative to the active source root.

The source-root route recognizes audio files and likely music/video containers
from general folder or file-name signals such as `music`, `bgm`, `sound`,
`audio`, `theme`, and Chinese music/audio terms. If no source-root music is
found, `source_root_music_discovery.fallback_intent` keeps external fallback
available through sourceable providers such as Jamendo or yt-dlp.

Source-folder presence is not legal approval. For internal rehearsal/review,
`source_folder_audio`, `user_provided`, `manual_import`, or `reviewed_manual`
may become mixable when a human declaration is recorded:

```json
{
  "music_use_basis": {
    "status": "human_declared_allowed",
    "usage_scope": "internal_rehearsal",
    "declared_by": "human",
    "basis_note": "User allowed this music for internal review.",
    "pipeline_legal_search_performed": false,
    "legal_approval_claimed": false,
    "external_publication_requires_rights_review": true
  }
}
```

This clears only the internal/rehearsal music-use policy. It does not set
`license_approved=true`, does not approve external publication/upload, and does
not bypass missing-file, probe, vocal-conflict, section-mismatch, or
`reference_only` blockers.

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

- Source-root-scoped music/audio first when `source_root` is present and a
  candidate is found.
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
  --source-type source_folder_audio `
  --license-note "user confirmed internal classroom use" `
  --music-use-basis human_declared_internal_use `
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
