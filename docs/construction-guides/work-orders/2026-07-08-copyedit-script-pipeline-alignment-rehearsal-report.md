# 2026-07-08 Copyedit Script Pipeline Alignment Rehearsal Report

## Result

Status: blocked before final media.

Output root:

```text
.tmp\copyedit_script_pipeline_alignment_rehearsal_20260708-172339
```

Run path:

```text
.tmp\copyedit_script_pipeline_alignment_rehearsal_20260708-172339\run
```

Final media was not produced.

Expected final path if render had succeeded:

```text
.tmp\copyedit_script_pipeline_alignment_rehearsal_20260708-172339\run\final_copyedit_rehearsal.mp4
```

## Red-First / Precondition Evidence

`red_first_precondition.json` records:

- copyedit package `ready_for_render`: false
- copyedit package `no_final_media`: true
- fresh final existed before planning: false

This confirms the copyedit package was a story basis only and was not already render-ready.

## Alignment Plan

Profile:

```text
music_subtitle_only
```

Planned current-capacity duration:

```text
214 seconds
```

No VoxCPM or narration was used.

Sections:

- `s01_opening_departure`: 0-18s
- `s02_safety_boundary`: 18-52s
- `s03_team_force`: 52-96s
- `s04_pressure_decision`: 96-136s
- `s05_standards_bridge`: 136-148s
- `s06_people_context`: 148-182s
- `s07_closing_handoff`: 182-214s

## Visual Decisions

`visual_selection_gate.json`:

```text
ok=true
```

Suspicious refs were not silently used:

- `工安早會/IMG_2120.JPG`: replaced, not used
- `工安早會/IMG_2124.JPG`: replaced, not used

Replacement refs:

- `工安早會/IMG_8515.MOV`
- `工安早會/IMG_8516.MOV`

Used-shot summary:

- total used shot chunks: 18
- raw_usable chunks: 18
- compiled/reference chunks used as primary: 0
- needs-human-review chunks used as primary: 0

Certification/check:

```text
bridge_only_not_primary_proof
```

Compiled certification footage was not used.

## Effect / Title Lifecycle

`title_effect_lifecycle_plan.json` records enter/hold/exit timing for every beat.

Policy:

```text
enter_hold_exit_no_persistent_side_rail
```

Every beat has:

- title start at section start
- readable hold for about 4 seconds
- title exit by about 5 seconds
- clears before next section

This was planned, but not verified in final media because render stopped before final output.

## Music Use Basis

Selected music:

```text
C:\Users\user\Downloads\微電影素材\_整理後\66期學長音樂檔\1片頭.mp4
```

Source-relative path:

```text
66期學長音樂檔/1片頭.mp4
```

ffprobe for the selected music source:

- exit code: 0
- video stream: hevc
- audio stream: aac
- duration: 72.679 seconds

Music basis:

```text
status=human_declared_allowed
usage_scope=internal_rehearsal
legal_approval_claimed=false
external_publication_requires_rights_review=true
```

No legal/music approval was claimed.

## Stop-Loss Blocker

`stop_loss_report.json`:

```text
blocker=segment_render_failed
```

Failed command:

```text
kind=segment_render
clip=segments\clip_001.mp4
source_relative_path=進場.MOV
duration_sec=9
exit_code=1
```

stderr tail:

```text
[Parsed_drawbox_3 @ ...] Error when evaluating the expression 'w'.
[Parsed_drawbox_3 @ ...] Failed to configure input pad on Parsed_drawbox_3
Error reinitializing filters!
Failed to inject frame into filter network: Invalid argument
Error while processing the decoded data for stream #0:0
```

Classification:

```text
run-local ffmpeg filter expression failure
```

The material/evidence gates passed before render, but final media was not produced because the ffmpeg title-overlay filter failed on the first segment.

## Commands

Initial generator attempt:

```powershell
C:\Users\user\miniconda3\python.exe -
```

Exit code: 1.

Result: local Python syntax error in the generator command. No output root was created.

Second generator attempt:

```powershell
C:\Users\user\miniconda3\python.exe -
```

Exit code: 1.

Result: fresh output root created; stopped with `segment_render_failed`.

Final artifact check preparation:

```powershell
C:\Users\user\miniconda3\python.exe -
```

Exit code: 0.

Final artifact check:

```powershell
C:\Users\user\miniconda3\python.exe -c "import json; from pathlib import Path; root=Path('.tmp/copyedit_script_pipeline_alignment_rehearsal_20260708-172339/run'); check=json.load(open(root/'final_artifact_check.json',encoding='utf-8')); print(json.dumps(check,ensure_ascii=False,indent=2)); raise SystemExit(0 if check.get('status')=='ok' else 1)"
```

Exit code: 0.

UTF-8/no-corruption check:

```powershell
C:\Users\user\miniconda3\python.exe -c "from pathlib import Path; root=Path('.tmp/copyedit_script_pipeline_alignment_rehearsal_20260708-172339/run'); bad=[]; count=0; ..."
```

Exit code: 0.

Output:

```text
checked 18
bad []
```

Git diff check:

```powershell
git diff --check
```

Exit code: 0.

Output contained CRLF warnings only.

## Final Artifact Check

`final_artifact_check.json` status:

```text
ok
```

Verified:

- required run-local planning artifacts exist
- `final_copyedit_rehearsal.mp4` does not exist
- `stop_loss_report.json` exists
- `final_absence_evidence.json` exists
- no `story_human_review_decision.json`
- no `human_transcript_review_decision.json`
- no VoxCPM artifacts
- no legal approval claim
- prior inputs were not mutated by rehearsal artifacts
- generated JSON/Markdown decodes as UTF-8 with no replacement characters or suspicious repeated question marks

Because final media does not exist, ffprobe, `pipeline_home.py`, and `write_delivery_gate_report.py` were not run.

## Confirmed Non-Actions

- No VoxCPM.
- No narration.
- No story approval artifact.
- No transcript approval artifact.
- No legal/music approval claim.
- No Downloads edit.
- No prior run edit.
- No repo code/test/tool/skill edit.
- No delivery package edit.

## Deviations

- Final media was not produced because the run hit the work-order render stop-loss.
- The generated effect/title lifecycle plan was not media-verified because render stopped on the first segment.
- The failure is in the run-local ffmpeg drawbox/title overlay command, not in material availability.

## Next Recommended Work

Run a narrow copyedit rehearsal repair that keeps the same story, shots, music basis, and visual decisions, but changes only the run-local title overlay assembly:

- replace the failing `drawbox=w=w` style expression with a valid ffmpeg expression such as `w=iw:h=130`, or
- pre-render title/caption overlays as PNG frames and overlay them with ffmpeg, avoiding drawtext/drawbox expression ambiguity.

Then rerun the same `music_subtitle_only` 214-second rehearsal from the existing copyedit script basis and re-run ffprobe, pipeline_home, and delivery gate only if final media is produced.
