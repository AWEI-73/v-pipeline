# 2026-07-08 Copyedit Rehearsal Title Overlay Repair Report

## Result

Status: final copyedit rehearsal media produced; delivery route still blocks because this rehearsal does not provide the formal `final.mp4` video candidate.

Fresh continuation output root:

```text
.tmp\copyedit_rehearsal_title_overlay_repair_20260708-181934
```

Run path:

```text
.tmp\copyedit_rehearsal_title_overlay_repair_20260708-181934\run
```

Final media:

```text
.tmp\copyedit_rehearsal_title_overlay_repair_20260708-181934\run\final_copyedit_rehearsal.mp4
```

The final copyedit rehearsal MP4 is usable: ffprobe reports one video stream, one audio stream, and 214.0 seconds duration.

## Cleanup Evidence

Before this resume, disk cleanup removed old generated `runs\` content.

Cleanup manifest:

```text
.tmp\cleanup_runs_20260708-181406\cleanup_manifest.json
```

Cleanup summary:

- target count: 137 old generated run entries
- target total listed: 15846 MB
- free space before this render: 22567346176 bytes, about 21 GB
- free space after this render: 22362468352 bytes, about 20.8 GB

## Red-First Evidence

Read from the original blocked alignment run:

```text
.tmp\copyedit_script_pipeline_alignment_rehearsal_20260708-172339\run\stop_loss_report.json
.tmp\copyedit_script_pipeline_alignment_rehearsal_20260708-172339\run\render_command_log.json
```

Recorded in the fresh run:

```text
.tmp\copyedit_rehearsal_title_overlay_repair_20260708-181934\run\red_first_evidence.json
```

Evidence:

- prior blocker: `segment_render_failed`
- prior stderr contained `Error when evaluating the expression`
- prior final media was absent
- previous repair blocker was `final_media_invalid_after_disk_full`

## Overlay Repair Method

Artifact:

```text
.tmp\copyedit_rehearsal_title_overlay_repair_20260708-181934\run\overlay_repair_plan.json
```

Method: pre-rendered transparent PNG overlays applied with ffmpeg `overlay`.

This avoided the previous ambiguous `drawbox` / `w` expression path. Titles enter, hold briefly, and exit in the first 5 seconds of each section. No persistent side rail was used.

Render evidence:

- 18 segment renders: exit `0`
- visual concat: exit `0`
- music mux: exit `0`
- ffprobe validation: exit `0`

## Preserved Decisions

Preserved from the copyedit alignment basis:

- same story
- same section timing
- same used shot manifest
- same visual-selection decisions
- same music-use basis
- same certification bridge policy
- same `music_subtitle_only` / no-narration policy

No `story_human_review_decision.json` or `human_transcript_review_decision.json` was written.

No VoxCPM, narration, legal approval claim, Downloads edit, prior run edit, repo code/test/tool edit, or delivery package edit occurred.

## Media Evidence

ffprobe artifact:

```text
.tmp\copyedit_rehearsal_title_overlay_repair_20260708-181934\run\ffprobe_final_copyedit_rehearsal.json
```

ffprobe summary:

```text
video: h264, duration 214.000000
audio: aac, duration 213.926009
format duration: 214.000000
```

Final artifact check:

```text
.tmp\copyedit_rehearsal_title_overlay_repair_20260708-181934\run\final_artifact_check.json
```

Status: `ok`

Key checks:

- `final_exists=true`
- `usable_final=true`
- `ffprobe_video_audio_duration_210_230=true`
- `utf8_no_corruption=true`
- no story human review decision
- no human transcript review decision
- no VoxCPM artifacts
- no legal approval claim

## Pipeline Home And Delivery Gate

pipeline_home artifact:

```text
.tmp\copyedit_rehearsal_title_overlay_repair_20260708-181934\run\pipeline_home.json
```

Result:

```text
status=REPAIR
next=create_or_verify_video_candidate
reason=delivery gate cannot pass without final.mp4 or a verified video preview candidate
```

delivery_gate artifact:

```text
.tmp\copyedit_rehearsal_title_overlay_repair_20260708-181934\run\delivery_gate.json
```

Result:

```text
pass=false
blocking rule=missing_video_candidate
artifact=final.mp4
```

This was not waived or bypassed. The rehearsal produced `final_copyedit_rehearsal.mp4`; it did not create or promote a formal `final.mp4` delivery candidate.

## Commands

Disk/free-space check:

```text
Get-PSDrive C
```

Exit code: `0`

Result before render: about 21.31 GB free.

Red-first / cleanup evidence check:

```text
C:\Users\user\miniconda3\python.exe -c "<read prior stop-loss and cleanup manifest>"
```

Exit code: `0`

One earlier quoting attempt exited `1`, and one cleanup-manifest read using plain UTF-8 exited `124` after a BOM decode failure. The successful check used `utf-8-sig` for the cleanup manifest.

Run-local assembly:

```text
C:\Users\user\miniconda3\python.exe -  # fresh run-local PNG overlay assembly
```

Exit code: `0`

Result:

```text
output_root=.tmp\copyedit_rehearsal_title_overlay_repair_20260708-181934
usable_final=true
duration_sec=214.0
streams=[video, audio]
```

Final artifact check:

```text
C:\Users\user\miniconda3\python.exe -c "import json; from pathlib import Path; p=Path('.tmp/copyedit_rehearsal_title_overlay_repair_20260708-181934/run/final_artifact_check.json'); data=json.load(open(p,encoding='utf-8')); print(json.dumps(data,ensure_ascii=False,indent=2)); raise SystemExit(0 if data.get('status')=='ok' else 1)"
```

Exit code: `0`

ffprobe:

```text
ffprobe -v error -show_entries stream=codec_type,codec_name,duration -show_entries format=duration -of json ".tmp\copyedit_rehearsal_title_overlay_repair_20260708-181934\run\final_copyedit_rehearsal.mp4"
```

Exit code: `0`

pipeline_home:

```text
C:\Users\user\miniconda3\python.exe tools\pipeline_home.py --run ".tmp\copyedit_rehearsal_title_overlay_repair_20260708-181934\run" --json
```

Exit code: `0`

Result: `REPAIR`, next `create_or_verify_video_candidate`.

write_delivery_gate_report:

```text
C:\Users\user\miniconda3\python.exe tools\write_delivery_gate_report.py --run ".tmp\copyedit_rehearsal_title_overlay_repair_20260708-181934\run" --json
```

Exit code: `1`

Result: blocked on `missing_video_candidate` / `final.mp4`.

git diff check:

```text
git diff --check
```

Exit code: `0`

Output contained existing CRLF warnings only.

Report UTF-8 check:

```text
C:\Users\user\miniconda3\python.exe -c "<read report as UTF-8 and check no replacement char/question-run>"
```

Exit code: `0`

Result: no replacement character, no suspicious repeated question-mark run, fresh root recorded.

## Artifact Paths

Key artifacts:

```text
.tmp\copyedit_rehearsal_title_overlay_repair_20260708-181934\run\source_run_manifest.json
.tmp\copyedit_rehearsal_title_overlay_repair_20260708-181934\run\overlay_repair_plan.json
.tmp\copyedit_rehearsal_title_overlay_repair_20260708-181934\run\render_command_log.json
.tmp\copyedit_rehearsal_title_overlay_repair_20260708-181934\run\ffprobe_final_copyedit_rehearsal.json
.tmp\copyedit_rehearsal_title_overlay_repair_20260708-181934\run\audio_mix_report.json
.tmp\copyedit_rehearsal_title_overlay_repair_20260708-181934\run\title_effect_lifecycle_qa.json
.tmp\copyedit_rehearsal_title_overlay_repair_20260708-181934\run\final_artifact_check.json
.tmp\copyedit_rehearsal_title_overlay_repair_20260708-181934\run\pipeline_home.json
.tmp\copyedit_rehearsal_title_overlay_repair_20260708-181934\run\delivery_gate.json
.tmp\copyedit_rehearsal_title_overlay_repair_20260708-181934\run\command_results.json
.tmp\copyedit_rehearsal_title_overlay_repair_20260708-181934\run\review_packet.md
.tmp\copyedit_rehearsal_title_overlay_repair_20260708-181934\run\review_packet.json
```

## Deviations

- The report was overwritten with this resume result, as requested.
- The successful rehearsal keeps the output named `final_copyedit_rehearsal.mp4`. It does not create a formal `final.mp4` delivery candidate.
- `pipeline_home` and `delivery_gate` therefore remain repair/block states. These were recorded truthfully rather than bypassed.

## Blockers

- No media-render blocker remains for `final_copyedit_rehearsal.mp4`.
- Delivery routing still blocks because the run does not contain a verified formal `final.mp4` candidate.

## Next Recommended Work

Create the next work order to promote or register `final_copyedit_rehearsal.mp4` as an intentional verified preview/video candidate, or to assemble a formal `final.mp4` from the same preserved story, shots, timing, music-use basis, certification bridge, and visual decisions. That round should not change story or materials; it should only resolve the route contract between rehearsal output and delivery candidate verification.
