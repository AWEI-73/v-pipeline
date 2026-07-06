# Real-Material Scripted Production With Preproduction Brief Report

Date: 2026-07-06

## Output

- Output root: `C:\Users\user\Desktop\video_pipeline\.tmp\real_material_scripted_preproduction_20260706-185346`
- Run path: `C:\Users\user\Desktop\video_pipeline\.tmp\real_material_scripted_preproduction_20260706-185346\run`
- Source: `C:\Users\user\Downloads\微電影素材\_整理後`

## Source Preflight

- exists: true
- is_dir: true
- file_count: 306
- media_count: 88
- representative folders: `66期學長音樂檔`, `主任勉勵`, `工安體感`, `拖拉電纜`, `換桿`, `活線作業`, `感謝導師`

Preflight artifact:

`C:\Users\user\Desktop\video_pipeline\.tmp\real_material_scripted_preproduction_20260706-185346\run\source_preflight.json`

## Preproduction Brief

Brief path:

`C:\Users\user\Desktop\video_pipeline\.tmp\real_material_scripted_preproduction_20260706-185346\run\human_preproduction_brief.json`

Brief summary:

- 全片中文為主，不做中英混雜旁白。
- 不替現場真人憑空生成講話。
- 來源聲音可用時優先保留。
- 旁白只補敘事空白或轉場脈絡。
- 音樂使用可追溯來源，不使用 synthetic bed。
- agent 初選故事與素材時標 `agent_filled=true` / `needs_human_confirmation=true`。
- 未寫入 `story_human_review_decision.json`，真人 approval 保留給使用者。

## Story / Script Summary

Story contract:

`story_contract.json`

Required beats:

- `establish_gathering`
- `safety_context`
- `training_process_detail`
- `field_operation_practice`
- `live_line_awareness`
- `source_speech_instruction`
- `closing_gratitude`

Selected source segments: 7.

All story/material choices in `story_to_material_map.json` are marked as agent-filled and `needs_human_confirmation=true`.

Narration segments: 3.

Narration role: bridge context only. It does not fabricate speech for on-camera people.

## Final Media

Final video:

`C:\Users\user\Desktop\video_pipeline\.tmp\real_material_scripted_preproduction_20260706-185346\run\final.mp4`

ffprobe:

- ffprobe exit: 0
- duration: 48.156 seconds
- streams: video + audio
- stored evidence: `final_ffprobe.json`

Review visual evidence:

- `review_contact_sheet.jpg`
- frame evidence: `frame_evidence.json`

## Source Speech

Source speech status: preserved.

Evidence:

`source_speech_preservation_report.json`

Summary:

- 主任勉勵片段使用來源音訊保留在 final mix。
- 旁白 placement 避開主要原聲段落。
- `audio_mix_report.json` includes a `source_speech` placement and preserved source audio track evidence.

## Narration

VoxCPM runtime:

- `voxcpm_runtime_check.py` exit 0.
- `ok_to_execute=true`.

VoxCPM execution:

- `voxcpm_voiceover_provider.py --execute` exit 0 after UTF-8 repair.
- Artifacts: `voiceover_provider_plan.json`, `subtitle_voiceover_build_handoff.json`, `narration_manifest.json`, `voiceover/seg01.wav`, `voiceover/seg02.wav`, `voiceover/seg03.wav`.

UTF-8 note:

An initial run-local script was corrupted because raw Chinese text was passed through a PowerShell here-string. This was repaired inside the run using Python Unicode escapes, archived under `corrupt_script_archive_before_unicode_repair` and `corrupt_text_artifact_archive_before_unicode_repair`, then VoxCPM was rerun. Final checked artifacts have no `\ufffd` and no `????`.

## Music

Music source:

`C:\Users\user\Downloads\微電影素材\_整理後\66期學長音樂檔\1片頭.mp4`

Local extracted audio:

`sourceable_music_from_provided_material.wav`

Evidence:

- `music_manifest.json`
- `sound_license_manifest.json`
- `soundtrack_probe_report.json`

Summary:

- source_type: `source_folder_audio`
- synthetic_generated_audio_bed: not used
- legal/music-use review: still required
- probe result: pass=true, low-underlay placement

## Review Packet

Review packet:

`C:\Users\user\Desktop\video_pipeline\.tmp\real_material_scripted_preproduction_20260706-185346\run\operator_review_packet.json`

Markdown companion:

`operator_review_packet.md`

Packet includes:

- story beats
- selected source material per beat
- agent-filled choices
- source speech usage
- narration lines
- music source/license summary
- known review risks

## Pipeline Home

Command:

`C:\Users\user\miniconda3\python.exe tools\pipeline_home.py --run "C:\Users\user\Desktop\video_pipeline\.tmp\real_material_scripted_preproduction_20260706-185346\run" --json`

Exit code: 0.

Result:

- mode: `waiting`
- cursor: `human_story_review`
- status: `WAITING`
- next: `human_review_story_to_material_map`

## Delivery Gate

Command:

`C:\Users\user\miniconda3\python.exe tools\write_delivery_gate_report.py --run "C:\Users\user\Desktop\video_pipeline\.tmp\real_material_scripted_preproduction_20260706-185346\run" --json`

Exit code: 0.

Result:

- pass: true
- blocking: none
- warning: `story_human_review_required`
- waivers: none
- video stream present: true
- audio stream present: true

## Story Review Decision

Confirmed:

- `story_human_review_decision.json` does not exist.
- No fake human approval was written.
- The run intentionally stops at `WAITING / human_story_review`.

## Commands And Exit Codes

- source preflight / brief creation: exit 0
- candidate media probe: exit 0
- `C:\Users\user\miniconda3\python.exe tools\voxcpm_runtime_check.py --out "...run\voxcpm_runtime_check.json"`: exit 0
- initial `voxcpm_voiceover_provider.py --execute`: exit 0, but produced corrupted `????` text due run-local script encoding issue
- Unicode repair of run-local script/metadata: exit 0
- rerun `voxcpm_voiceover_provider.py --execute`: exit 0
- clip render / concat / audio mix / mux: exit 0
- contact sheet generation: exit 0
- artifact writing and UTF-8 checks: exit 0
- `write_delivery_gate_report.py --json`: exit 0
- `pipeline_home.py --json`: exit 0
- final acceptance check: exit 0

## Deviations

- The source path in the work order body is mojibake, so the actual source path from the user request was used: `C:\Users\user\Downloads\微電影素材\_整理後`.
- A first run-local script/brief artifact attempt was corrupted by PowerShell here-string handling of Chinese. The corrupted run-local artifacts were archived, then rewritten using Unicode escapes. No repo code/tools/tests were changed.
- `narration_manifest.json` produced by the voiceover tool used `target_file`; delivery gate required `audio_ref`. I added relative `audio_ref` fields inside the run-local manifest only.
- The music is source-folder audio from user-provided material. It is sourceable but still requires real legal/music-use review.

## Stop-Loss

No remaining blocker. Final candidate was produced and the expected human review stop was reached.

## Next Recommended Work

Have the user watch `final.mp4` with `operator_review_packet.json` and `review_contact_sheet.jpg`, then record a real `story_human_review_decision.json` using the approved writer command only after human story/material review. Legal/music-use review should also be completed before any external delivery.
