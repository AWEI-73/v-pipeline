# V6 Voiceover Regeneration With Lead-In Gate Report

Date: 2026-07-07

## Summary

- Output root: `.tmp\v6_voiceover_regeneration_leadin_gate_20260707-234956`
- Fresh run path: `.tmp\v6_voiceover_regeneration_leadin_gate_20260707-234956\run`
- Source V5 run: `.tmp\graduation_v5_content_verify_effect_montage_20260707-200659\run`
- Source V6 transcript run: `.tmp\graduation_v6_transcript_repair_leadin_qa_20260707-212257\run`
- V5 unchanged: true
- V6 unchanged: true
- Regenerated voiceover: four VoxCPM wav files created in the fresh run
- Final media: not produced
- Stop-loss: `voiceover_leadin_qa.json` still blocks `seg02`, `seg03`, and `seg04` for extra `抗` lead-in.
- `story_human_review_decision.json`: not written

## Preserved Inputs

Copied into the fresh run without modifying V5/V6 source folders:

- V6 `asr_raw_transcript.json`
- V6 `agent_transcript_repair_suggestions.json`
- V6 `subtitles.draft.srt`
- V6 `human_transcript_review_decision.json`
- V5 visual/effect/montage/music/final artifacts needed for continuity

Proof:

- `.tmp\v6_voiceover_regeneration_leadin_gate_20260707-234956\final_artifact_check.json`
- `v5_unchanged=true`
- `v6_unchanged=true`

## Voiceover Regeneration Attempt

Command:

```powershell
C:\Users\user\miniconda3\python.exe tools\voxcpm_voiceover_provider.py ".tmp\v6_voiceover_regeneration_leadin_gate_20260707-234956\run\v5_narration_script.json" --out-dir ".tmp\v6_voiceover_regeneration_leadin_gate_20260707-234956\run" --voice-style "calm" --device auto --execute --timeout-sec 1200
```

Exit code: `0`

Settings/result:

- selected_provider: `voxcpm`
- provider_available: true
- provider_python: `C:\Users\user\Desktop\video_pipeline\.venv_voxcpm\Scripts\python.exe`
- voice_style: `calm`
- avoided known leaking style strings: `clear narration`, `firm documentary delivery`, `warm clear documentary delivery`
- voiceover_ready: true
- generated files:
  - `.tmp\v6_voiceover_regeneration_leadin_gate_20260707-234956\run\voiceover\seg01.wav`
  - `.tmp\v6_voiceover_regeneration_leadin_gate_20260707-234956\run\voiceover\seg02.wav`
  - `.tmp\v6_voiceover_regeneration_leadin_gate_20260707-234956\run\voiceover\seg03.wav`
  - `.tmp\v6_voiceover_regeneration_leadin_gate_20260707-234956\run\voiceover\seg04.wav`

Runtime note:

- The provider plan records CUDA primary return code `3221225477` for `seg01`, followed by CPU retry success.

## Independent ASR Summary

Command:

```powershell
C:\Users\user\miniconda3\python.exe tools\independent_voiceover_asr_qa.py --run ".tmp\v6_voiceover_regeneration_leadin_gate_20260707-234956\run" --model tiny --language zh --json
```

Exit code: `0`

Result:

- `voiceover_output_qa.json` pass: true
- blocking: none
- checked_text_count: 34
- no `ClearNeration` / style-control leakage block

ASR summary for regenerated voiceover:

| Segment | ASR text summary |
| --- | --- |
| `seg01.wav` | `康,这一天,学员从集合开始,把安全放进每一个动作里。` |
| `seg02.wav` | `抗,基本顺利案不是口號,而是一次一次把工具,不走和互相提醒做到確實` |
| `seg03.wav` | `抗 敬開抗戀 把壓力變成節奏 也把團隊墨起拉到現場需要的高度` |
| `seg04.wav` | `抗 完成順利後 大家把今天學到的紀律帶回工作 也把感謝留給一路陪伴的人` |

## Lead-In Gate

Command:

```powershell
C:\Users\user\miniconda3\python.exe tools\voiceover_leadin_qa.py --run ".tmp\v6_voiceover_regeneration_leadin_gate_20260707-234956\run" --json
```

Exit code: `0`

Result:

- pass: false
- checked_segment_count: 4
- next_action: `repair_voiceover_leadin`

Detected blocking mismatches:

| Segment | Detected lead-in | Expected starts with | ASR starts with |
| --- | --- | --- | --- |
| `seg02` | `抗` | `基本訓練...` | `抗,基本顺利案...` |
| `seg03` | `抗` | `進階訓練...` | `抗 敬開抗戀...` |
| `seg04` | `抗` | `完成訓練後...` | `抗 完成順利後...` |

Additional observation:

- `seg01` ASR starts with `康,这一天...`; current `voiceover_leadin_qa.py` did not classify `康` as a blocking token, but this remains visible in the ASR summary for human/tool follow-up. No gate was loosened.

Because the lead-in gate blocks, no final assembly was attempted.

## Final Media

- `final_v6.mp4`: absent
- `final_v7.mp4`: absent
- ffprobe command on `final_v6.mp4`: exit `1`, expected stop-loss evidence
- video stream present: false
- audio stream present: false

The fresh run still contains copied V5 `final.mp4` / `final_v5.mp4`, but no new V6/V7 final was produced or claimed.

## Pipeline Home And Delivery Gate

Initial `pipeline_home` before rewriting gate:

- exit code: `0`
- status: `WAITING`
- cursor: `human_story_review`

Delivery gate command:

```powershell
C:\Users\user\miniconda3\python.exe tools\write_delivery_gate_report.py --run ".tmp\v6_voiceover_regeneration_leadin_gate_20260707-234956\run" --json
```

Exit code: `1`

Current delivery gate result:

- pass: false
- blocking:
  - `missing_voiceover_provider_plan`
  - `artifact_manifest_stale` for `narration_manifest`
  - `artifact_manifest_stale` for `subtitle_voiceover_build_handoff`
  - `missing_narration_manifest`
- warning: `story_human_review_required`

Current `pipeline_home` after delivery gate:

- exit code: `0`
- status: `REPAIR`
- cursor: `stage5_final_review`
- next: `dispatch_voiceover_voxcpm`

Important limitation:

- The provider did write `voiceover_provider_plan.json` and `narration_manifest.json` in the fresh run, but delivery gate reports stale/missing evidence because the copied/generated artifact manifest path resolution points to missing nested paths. This was recorded, not repaired, because the lead-in gate had already triggered stop-loss and the work order forbids code/tool changes.

## Transcript Review Status

- Preserved V6 `human_transcript_review_decision.json`
- decision: `revision_requested`
- clears human transcript review: false
- transcript review still required: true
- no human transcript approval was created
- no `story_human_review_decision.json` was written

## Commands And Exit Codes

| Command | Exit | Result |
| --- | ---: | --- |
| fresh output root/run copy and V6 transcript artifact preservation | 0 | run created |
| `C:\Users\user\miniconda3\python.exe tools\voxcpm_voiceover_provider.py ".tmp\v6_voiceover_regeneration_leadin_gate_20260707-234956\run\v5_narration_script.json" --out-dir ".tmp\v6_voiceover_regeneration_leadin_gate_20260707-234956\run" --voice-style "calm" --device auto --execute --timeout-sec 1200` | 0 | four voiceover wavs generated |
| `C:\Users\user\miniconda3\python.exe tools\independent_voiceover_asr_qa.py --run ".tmp\v6_voiceover_regeneration_leadin_gate_20260707-234956\run" --model tiny --language zh --json` | 0 | voiceover output QA pass |
| `C:\Users\user\miniconda3\python.exe tools\voiceover_leadin_qa.py --run ".tmp\v6_voiceover_regeneration_leadin_gate_20260707-234956\run" --json` | 0 | lead-in QA pass false |
| `C:\Users\user\miniconda3\python.exe tools\pipeline_home.py --run ".tmp\v6_voiceover_regeneration_leadin_gate_20260707-234956\run" --json` | 0 | first run `WAITING / human_story_review`; after gate `REPAIR / stage5_final_review` |
| `C:\Users\user\miniconda3\python.exe tools\write_delivery_gate_report.py --run ".tmp\v6_voiceover_regeneration_leadin_gate_20260707-234956\run" --json` | 1 | gate blocks provider/manifest/narration evidence |
| `ffprobe -v error -show_entries stream=codec_type,codec_name,duration -of json ".tmp\v6_voiceover_regeneration_leadin_gate_20260707-234956\run\final_v6.mp4"` | 1 | expected stop-loss; file absent |
| pinned Python final artifact check | 0 | `.tmp\v6_voiceover_regeneration_leadin_gate_20260707-234956\final_artifact_check.json` |
| `git diff --check` | 0 | whitespace check passed; CRLF warnings only |

## UTF-8 / No Corruption

Final artifact check:

- utf8_no_corruption: true
- utf8_bad_files: []

Checked generated/preserved run-local JSON artifacts with explicit UTF-8 reads.

## Deviations / Blockers

- Blocker: regenerated voiceover still has lead-in mismatches on `seg02`, `seg03`, and `seg04`.
- Blocker: no `final_v6.mp4` or `final_v7.mp4` was assembled because lead-in QA did not pass.
- Blocker: delivery gate also reports provider/manifest/narration evidence blocks after the fresh provider run.
- Deviation: command order ran independent ASR before the first lead-in QA because lead-in QA needs current regenerated ASR evidence; the lead-in command was rerun after ASR and is the recorded gate result.
- Limitation: current lead-in QA did not flag `seg01` starting with `康`, but the ASR evidence is visible and not hidden.

## Next Recommended Work

Run a provider-level VoxCPM lead-in diagnostic for short Chinese segments that start with the exact first content word, comparing multiple safe controls and punctuation/segmentation variants. Do not assemble final media until `tools\voiceover_leadin_qa.py` passes all voiceover segments and delivery gate provider/manifest paths are valid in the fresh run.
