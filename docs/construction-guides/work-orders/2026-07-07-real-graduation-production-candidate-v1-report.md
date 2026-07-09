# Real Graduation Production Candidate V1 Report

Date: 2026-07-07

## Output

- Output root: `.tmp\real_graduation_production_candidate_v1_20260707-062900`
- Run path: `.tmp\real_graduation_production_candidate_v1_20260707-062900\run`
- Final candidate exists: `true`
- Final video: `.tmp\real_graduation_production_candidate_v1_20260707-062900\run\final.mp4`
- Candidate status: technical V1 candidate only; delivery gate is blocked.

## Source Preflight

- Source root: `C:\Users\user\Downloads\微電影素材\_整理後`
- `exists=true`
- `is_dir=true`
- `file_count=306`
- `media_count=198`
- Source root was read-only.

## Product Route Handoff

- Handoff: `.tmp\product_route_review_writer_20260707-061959\graduation_approved\production_worker_handoff_prompt.md`
- UTF-8 decode: `ok`
- Replacement-character check: `false`
- Question-run check: `false`
- Selected story shell: A
- Theme: `從新人到現場人員`

## Story Sequence

- Sequence model: `growth_line_challenge_first`
- Module order:
  - `opening_story`
  - `basic_training`
  - `advanced_training`
  - `physical_activity`
  - `supervisor_speech`
  - `teacher_class_intro`
  - `closing_story`
- Optional/absent modules:
  - `certification`: optional absent
  - `encouragement_activity`: optional absent
- Weakened/callback modules:
  - `daily_life_optional`
  - `special_activity`

Artifacts:

- `story_theme_selection.json`
- `module_sequence_plan.json`
- `story_to_material_map.json`
- `selected_visual_clips.json`

## Title Treatment Plan

- Plan artifact: `mv_title_treatment_plan.json`
- Treatment count: `6`
- Implementation status: rendered with ffmpeg title rail treatment.
- Design rule: not plain subtitles; not white cards.
- Style: dark translucent left rail, amber divider, high-contrast CJK display text.
- Opening/closing design artifact: `opener_closer_design_plan.json`

## Music Replacement Evidence

- Old source-folder BGM final use: `false`
- `66期學長音樂檔` was not selected as final BGM.
- Replacement provider: `jamendo`
- Downloaded/imported audio: `.tmp\real_graduation_production_candidate_v1_20260707-062900\run\audio\sources\jamendo_training_mv_main_2252788.mp3`
- Download byte size: `1836269`
- Candidate id: `jamendo_training_mv_main_2252788`
- License URL: `http://creativecommons.org/licenses/by-nc-nd/3.0/`
- Legal/music-use review still required before external publishing.

Music artifacts:

- `music_source_policy.json`
- `soundtrack_plan.json`
- `music_source_candidates.json`
- `music_download_result.json`
- `sound_license_manifest.json`
- `music_manifest.json`
- `music_use_evidence.json`
- `soundtrack_probe_report.json`

Soundtrack probe:

- Command exit code: `0`
- `pass=true`
- Duration: `152.712`
- Codec: `mp3`
- Tempo: `143.555 bpm`

## Source Speech / Subtitle / Audio Mix

- Source speech preserved: `false`
- Rationale: V1 uses supervisor/teacher material visually only; no source speech is preserved because subtitle/alignment evidence was not produced.
- Subtitle/audio alignment required: `false`
- Audio stream in final: `true`
- Audio source: replacement Jamendo track.

Artifacts:

- `source_speech_preservation_report.json`
- `subtitle_audio_alignment_report.json`
- `audio_mix_report.json`
- `final_audio.wav`

## Final Media

`ffprobe` result:

- Video stream: `h264`, duration `42.053646`
- Audio stream: `aac`, duration `42.000000`

Artifacts:

- `final.mp4`
- `final_media_ffprobe.json`
- `render_report.json`
- `visual_candidate.mp4`

## Review Artifacts

- `review_artifacts_manifest.json`
- `frame_evidence.json`
- Contact sheet: `.tmp\real_graduation_production_candidate_v1_20260707-062900\run\review_artifacts\contact_sheet.jpg`
- Frame stills: `.tmp\real_graduation_production_candidate_v1_20260707-062900\run\review_artifacts\frame_*.jpg`

## Delivery / Pipeline Status

Pipeline home:

- Status: `REPAIR`
- Cursor: `stage5_final_review`
- Owner: `verify_delivery`
- Next: `route_voiceover_voxcpm_or_attach_no_narration_approval`

Delivery gate:

- Command exit code: `1`
- `pass=false`
- Blocking rules:
  - `narration_required_for_complete_real_material_delivery`
  - `missing_voxcpm_runtime_check`
  - `missing_voiceover_provider_plan`
  - `missing_narration_manifest`
  - `narration_not_mixed`

No waiver was applied. No `story_human_review_decision.json` was written.

## Commands

- `C:\Users\user\miniconda3\python.exe -c "... branch env probe ..."`
  - Exit code: `0`
  - Result: Jamendo present, Pixabay present, yt-dlp version present, secrets redacted.
- `C:\Users\user\miniconda3\python.exe -c "... write production planning artifacts and download music ..."`
  - Exit code: `0`
  - Result: Jamendo replacement music downloaded.
- `C:\Users\user\miniconda3\python.exe tools\soundtrack_probe.py --audio ".tmp\real_graduation_production_candidate_v1_20260707-062900\run\audio\sources\jamendo_training_mv_main_2252788.mp3" --out ".tmp\real_graduation_production_candidate_v1_20260707-062900\run\soundtrack_probe_report.json" --json`
  - Exit code: `0`
  - Result: `pass=true`.
- `C:\Users\user\miniconda3\python.exe -c "... render final.mp4 from selected clips and replacement music ..."`
  - Exit code: `1`
  - Result: first attempt failed with a local Python concat string syntax error before ffmpeg execution.
- `C:\Users\user\miniconda3\python.exe -c "... render final.mp4 from selected clips and replacement music ..."`
  - Exit code: `0`
  - Result: `final.mp4` created with 7 segments.
- `ffprobe -v error -show_entries stream=codec_type,codec_name,duration -of json ".tmp\real_graduation_production_candidate_v1_20260707-062900\run\final.mp4"`
  - Exit code: `0`
  - Result: h264 video + aac audio.
- `C:\Users\user\miniconda3\python.exe -c "... write final_media_ffprobe/audio_mix/frame evidence/review artifacts ..."`
  - Exit code: `0`
  - Result: review artifacts and final audio evidence written.
- `C:\Users\user\miniconda3\python.exe tools\pipeline_home.py --run ".tmp\real_graduation_production_candidate_v1_20260707-062900\run" --json`
  - Exit code: `0`
  - Final result: `REPAIR`, next `route_voiceover_voxcpm_or_attach_no_narration_approval`.
- `C:\Users\user\miniconda3\python.exe tools\write_delivery_gate_report.py --run ".tmp\real_graduation_production_candidate_v1_20260707-062900\run" --json`
  - Exit code: `1`
  - Final result: delivery gate blocked on narration/VoxCPM requirements.
- Final artifact check command
  - Exit code: `0`
  - Result: UTF-8/no-corruption `true`, old source-folder music final BGM `false`, `story_human_review_decision.json` absent.
- `git status --short --branch --untracked-files=all`
  - Exit code: `0`
  - Result: worktree shows the untracked V1 work order file; no code/tool/test files were edited in this round.
- `git diff --check`
  - Exit code: `0`
  - Result: no whitespace errors.

## Deviations / Blockers

Deviations:

- The first render script attempt failed locally due to a Python string literal syntax error before ffmpeg execution. It did not change repo code or source material; the corrected run succeeded.
- The final render uses a basic ffmpeg title rail treatment rather than a richer Remotion/Effect Factory motion package. It is not a plain subtitle or white-card treatment, but it remains a technical V1 treatment.

Blockers:

- Delivery gate blocks complete delivery because narration/VoxCPM evidence is missing and narration is not mixed.
- This candidate is not delivery-approved and not story-approved.
- Legal/music-use review remains required.

## Stop-Loss Review

- Replacement music was obtained, downloaded, licensed-metadata recorded, and probed.
- Title treatments were honestly represented in the rendered candidate.
- Source speech was not preserved, so subtitle/alignment evidence was not required for speech.
- Final contains video and audio streams.
- Delivery gate blocks candidate; no waiver or fake approval was used.

## Next Recommended Work

Run the narration branch for this exact run: perform VoxCPM runtime check, write `voiceover_provider_plan.json`, create a real `narration_manifest.json`, mix narration into the final audio, then rerun `pipeline_home` and `write_delivery_gate_report.py`. After gate repair, send the candidate and review artifacts to the real user for story/delivery approval and keep legal/music-use review required.
