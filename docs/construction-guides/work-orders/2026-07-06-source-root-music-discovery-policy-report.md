# Source-Root Music Discovery Policy Report

Date: 2026-07-06

## Files Changed

- `video_pipeline_core/soundtrack_arranger.py`
- `tests/test_soundtrack_arranger.py`
- `docs/soundtrack-arranger-route.md`
- `docs/branch-contract-registry.md`
- `docs/branch-contract-registry.json`
- `docs/video-pipeline-operating-map.md`
- `docs/construction-guides/work-orders/2026-07-06-source-root-music-discovery-policy-report.md`

## Red-First Evidence

- Command: `C:\Users\user\miniconda3\python.exe -m unittest tests.test_soundtrack_arranger`
- Exit code: `1`
- Result: failed before implementation with `ImportError: cannot import name 'discover_source_root_music' from 'video_pipeline_core.soundtrack_arranger'`.

## Implemented Behavior

- Added `discover_source_root_music(source_root)` in `video_pipeline_core.soundtrack_arranger`.
- Discovery searches only inside the active `source_root`; no Downloads path or approved-run filename is hard-coded.
- Audio files are source-root candidates only when their source-relative path
  carries music/audio intent signals; plain speech/interview audio is not
  promoted as music.
- Video containers are considered only when path/name signals indicate likely music/audio use.
- Signals include general tokens such as `music`, `bgm`, `sound`, `audio`, `theme`, plus Chinese music/audio terms.
- `arrange_soundtrack` now reads `source_root`, `material_source_root`, `source_folder`, `source_dir`, or equivalent nested `source` fields from the payload.
- When source-root music exists, `source_folder_audio` is inserted before external provider candidates and section `source_type_priority` starts with `source_folder_audio`.
- When source-root music is absent, `fallback_intent.status=external_fallback_available` and providers include `jamendo` and `yt-dlp`.

Integrator follow-up before commit:

- Tightened source-root discovery so generic `.wav/.mp3` files without music or
  audio naming signals are not selected as BGM candidates.
- Added a regression test proving plain source speech audio remains unselected
  and external fallback remains available.
- Added `deliveries/` to `.gitignore` so local approved delivery packages do
  not get accidentally staged with source changes.

## Source-Relative Evidence

Selected source-root candidates record:

- `path`: absolute local evidence path.
- `source_relative_path`: stable path relative to active `source_root`.
- `provider`: `source_root`.
- `source_type`: `source_folder_audio`.

The same relative path is preserved in `music_source_candidates.json` and in `sound_license_manifest.sources[]` when a source-root candidate is present.

## Legal / Music-Use Caveat

Source-folder audio is not treated as legal approval.

- `legal_review_required=true`
- `license_status=source_folder_audio_requires_review`
- `delivery_allowed=false`
- `legal_caveat=Source-folder audio is source evidence, not a legal/music-use approval.`

No artifact writes `license_approved` for source-folder discovery.

## Fresh Smoke

- Output root: `.tmp\source_root_music_discovery_policy_20260706-204946`
- Smoke result: `.tmp\source_root_music_discovery_policy_20260706-204946\smoke_result.json`

Case A: nested source-root music exists.

- Selected source type: `source_folder_audio`
- Provider: `source_root`
- `source_relative_path`: `nested/music/opening_theme.mp3`
- Fallback status: `not_selected_source_root_available`
- Legal caveat: source-folder audio remains source evidence only, not legal/music-use approval.

Case B: no source-root music exists.

- `source_root_music_available=false`
- Selected candidate: `null`
- Fallback status: `external_fallback_available`
- Fallback providers: `jamendo`, `yt-dlp`
- Legal caveat remains visible.

## Commands

- `C:\Users\user\miniconda3\python.exe -m unittest tests.test_soundtrack_arranger`
  - Exit code: `1`
  - Purpose: red-first evidence before implementation.
- `C:\Users\user\miniconda3\python.exe -m unittest tests.test_soundtrack_arranger`
  - Exit code: `0`
  - Worker result: `Ran 14 tests ... OK`
  - Integrator re-run after generic-audio hardening: `Ran 15 tests ... OK`
- `C:\Users\user\miniconda3\python.exe -m unittest tests.test_soundtrack_arranger tests.test_soundtrack_flow_acceptance`
  - Exit code: `0`
  - Result: `Ran 18 tests ... OK`
- `C:\Users\user\miniconda3\python.exe -m unittest tests.test_soundtrack_arranger tests.test_soundtrack_flow_acceptance tests.test_delivery_gate tests.test_pipeline_home`
  - Exit code: `0`
  - Worker result: `Ran 163 tests ... OK`
  - Integrator re-run after generic-audio hardening: `Ran 164 tests ... OK`
- `C:\Users\user\miniconda3\python.exe -c "import json; json.load(open('docs/branch-contract-registry.json', encoding='utf-8')); print('json ok')"`
  - Exit code: `0`
  - Result: `json ok`
- `git diff --check`
  - Exit code: `0`
  - Result: no whitespace errors; Git printed line-ending warnings for modified tracked text files.
- Fresh smoke command using `C:\Users\user\miniconda3\python.exe -`
  - Exit code: `0`
  - Result: wrote `smoke_result.json` and printed Case A / Case B summary.

## Deviations

- None.

## Stop-Loss

- Not stopped.
- No render, delivery gate semantic, VoxCPM, provider runtime, Downloads, deliveries, or existing `.tmp` run changes were required.

## Next Recommended Work

Run the next real-material soundtrack branch with an explicit active `source_root` in `video_intent.json`, then verify the selected `source_folder_audio` candidate with soundtrack probe and human music-use/legal review before delivery packaging.
