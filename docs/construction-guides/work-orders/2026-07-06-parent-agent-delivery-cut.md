# Work Order: Parent Agent Delivery Cut

Date: 2026-07-06
Status: ready for execution

## Background

The renderer now produces a real-material visual candidate:

- Source run: `.tmp/material_first_render_video_input_support_20260706-063649/run`
- Rendered video: `final.mp4`
- `material_first_final_artifact_acceptance.json`: `ok=true`
- ffprobe: one h264 video stream, 320x180, duration 12 seconds

The delivery gate then blocked because the parent flow did not dispatch the
remaining delivery branches:

- `missing_delivery_requirements`
- `missing_audio_stream`
- `missing_narration_manifest`
- `missing_music_manifest`
- `missing_audio_mix_report`
- `missing_subtitles`
- `missing_frame_evidence`

## Goal

Act as the parent production agent for the already rendered real-material cut:
copy the source run, dispatch or execute the missing delivery branches, produce
a playable candidate with audio/subtitles/frame evidence, and rerun the delivery
gate truthfully.

## User-Visible Desired State

The user can inspect a fresh run containing:

- a playable `final.mp4` with video and audio streams;
- `delivery_requirements.json`;
- `music_manifest.json`;
- `audio_mix_report.json`;
- `subtitles.srt`;
- `frame_evidence.json`;
- parent/subagent orchestration logs;
- delivery gate result showing either a true pass or the exact remaining block.

## Delivery Target For This Round

Target a no-narration technical delivery candidate:

- `requires_audio`: true
- `requires_music`: true
- `requires_subtitles`: true
- `requires_narration`: false
- `requires_frame_evidence`: true
- `requires_soundtrack_probe`: false
- `requires_vocal_conflict_check`: false

Do not create fake narration. If the worker chooses to add real narration
anyway, it must provide real usable narration audio refs and explain why.

## Non-Goals

- Do not modify pipeline code or tests.
- Do not modify `C:/Users/user/Downloads/`.
- Do not edit previous `.tmp` runs in place.
- Do not claim real user approval.
- Do not use delivery waivers to hide missing required artifacts.
- Do not bypass delivery gate.

## Owner Zone

The worker may write only:

- `.tmp/parent_agent_delivery_cut_*/`
- `docs/construction-guides/work-orders/2026-07-06-parent-agent-delivery-cut-report.md`

The fresh run inside `.tmp/parent_agent_delivery_cut_*/run` may contain new or
overwritten delivery artifacts, including `final.mp4`.

## Forbidden Zone

These paths are read-only:

- `C:/Users/user/Downloads/`
- `.tmp/material_first_render_video_input_support_20260706-063649/`
- `.tmp/simulated_client_production_drill_20260706-062052/`
- `.tmp/render_readiness_asset_audit_scope_20260705-235822/`
- `video_pipeline_core/`
- `tools/`
- `tests/`
- `skills/`
- `runs/`
- `examples/`

## Required Pieces

### Piece 1: Fresh Parent Run

Copy the source run into a fresh parent-run folder:

```powershell
$STAMP = Get-Date -Format "yyyyMMdd-HHmmss"
$OUT = ".tmp/parent_agent_delivery_cut_$STAMP"
$env:SOURCE_RUN = [System.IO.Path]::GetFullPath(".tmp/material_first_render_video_input_support_20260706-063649/run")
$env:CUT_RUN = [System.IO.Path]::GetFullPath("$OUT/run")
@'
import os
import shutil
from pathlib import Path
source = Path(os.environ["SOURCE_RUN"])
target = Path(os.environ["CUT_RUN"])
print("source_exists:", source.is_dir())
print("target:", target)
if not source.is_dir():
    raise SystemExit(2)
target.parent.mkdir(parents=True, exist_ok=True)
shutil.copytree(source, target)
print("copied:", target.is_dir())
'@ | C:\Users\user\miniconda3\python.exe -
```

Expected: exit code 0.

### Piece 2: Parent Orchestration Record

Create:

- `parent_orchestration_log.md`
- `subagent_dispatches/`

If subagent tools are available in the worker session, use them for at least
these streams and save each prompt/result under `subagent_dispatches/`:

- delivery requirements;
- music/audio mix;
- subtitles;
- frame evidence.

If subagent tools are unavailable, execute the streams parent-side and still
write the dispatch records with `execution_mode: parent_fallback`.

### Piece 3: Delivery Requirements

Write `delivery_requirements.json` for the no-narration target above. Include a
short rationale tied to `simulated_client_brief.json` or `interaction_log.md`.

### Piece 4: Audio And Music Branch

Create a run-local music/audio bed and mux it into `final.mp4`.

Minimum required artifacts:

- preserve the silent candidate as `final_video_silent.mp4` before overwrite;
- `generated_bgm.wav` or equivalent run-local audio source;
- `music_manifest.json`;
- `audio_mix_report.json`;
- final `final.mp4` with both video and audio streams.

The audio must be generated or sourced locally and reported honestly. Do not
claim licensed music unless a licensed source exists.

### Piece 5: Subtitle Branch

Write `subtitles.srt` for the 12-second cut. It must contain valid timing cues
and human-readable Traditional Chinese text grounded in the simulated brief,
timeline, or material review artifacts.

### Piece 6: Frame Evidence Branch

Extract or sample frames from the selected timeline/video assets into a
run-local evidence folder. Write `frame_evidence.json` with:

- `artifact_role`: `frame_evidence`;
- `pass`: true only if inspected evidence supports it;
- one inspected entry per selected timeline asset where possible;
- each inspected asset has non-empty `frames`, `observations`, and
  `semantic_match: true`.

Do not invent visual observations unsupported by exported frames or existing
material understanding artifacts. If frame inspection cannot be performed, set
`pass=false` and stop before claiming delivery.

### Piece 7: Parent Integration

Run:

```powershell
C:\Users\user\miniconda3\python.exe tools/pipeline_home.py --run "$env:CUT_RUN" --json
```

Then run:

```powershell
C:\Users\user\miniconda3\python.exe tools/write_delivery_gate_report.py --run "$env:CUT_RUN" --json
```

Record the exact pass/block result. Do not patch code if delivery still blocks.

## Acceptance Commands

Check media streams:

```powershell
@'
import json
import os
import subprocess
from pathlib import Path
from video_pipeline_core.platform_tools import resolve_ffprobe
run = Path(os.environ["CUT_RUN"])
final = run / "final.mp4"
cmd = [resolve_ffprobe(), "-v", "error", "-show_entries", "stream=codec_type,codec_name,duration", "-of", "json", str(final)]
result = subprocess.run(cmd, text=True, capture_output=True)
print("ffprobe_rc:", result.returncode)
print(result.stdout)
payload = json.loads(result.stdout or "{}") if result.returncode == 0 else {}
types = {s.get("codec_type") for s in payload.get("streams", [])}
print("stream_types:", sorted(types))
raise SystemExit(0 if {"video", "audio"} <= types else 1)
'@ | C:\Users\user\miniconda3\python.exe -
```

Expected: exit code 0.

Check required artifacts:

```powershell
@'
import os
from pathlib import Path
run = Path(os.environ["CUT_RUN"])
required = [
    "parent_orchestration_log.md",
    "delivery_requirements.json",
    "music_manifest.json",
    "audio_mix_report.json",
    "subtitles.srt",
    "frame_evidence.json",
    "final.mp4",
    "final_video_silent.mp4",
]
missing = [name for name in required if not (run / name).is_file()]
print("missing:", missing)
raise SystemExit(1 if missing else 0)
'@ | C:\Users\user\miniconda3\python.exe -
```

Expected: exit code 0.

Run the delivery gate:

```powershell
C:\Users\user\miniconda3\python.exe tools/write_delivery_gate_report.py --run "$env:CUT_RUN" --json
```

Expected: exit code 0 if the technical delivery candidate passes. If it exits
1, stop and report the exact remaining blocks without code changes.

Run report check:

```powershell
$env:REPORT_PATH = "docs/construction-guides/work-orders/2026-07-06-parent-agent-delivery-cut-report.md"
@'
import os
from pathlib import Path
p = Path(os.environ["REPORT_PATH"])
text = p.read_text(encoding="utf-8")
required = ["parent_orchestration_log.md", "subagent_dispatches", "final.mp4", "audio", "subtitles.srt", "frame_evidence.json", "delivery gate", "real user approval"]
missing = [item for item in required if item not in text]
print("report_exists:", p.exists())
print("missing:", missing)
raise SystemExit(1 if missing else 0)
'@ | C:\Users\user\miniconda3\python.exe -
```

Expected: exit code 0.

## Stop-Loss Limits

Stop and write the report if:

- the source run is missing;
- any needed edit would leave the owner zone;
- subagent tools are unavailable and parent-side execution cannot produce the
  required artifact truthfully;
- audio muxing fails;
- frame evidence cannot be supported by inspected frames or existing material
  understanding;
- delivery gate still blocks after the branches complete.

## Delegated Decisions

The worker may decide:

- whether to use actual subagent tools or parent-side fallback if unavailable;
- the exact subagent prompts and number of subagents;
- the exact generated instrumental bed, volume, and ffmpeg command;
- the exact subtitle wording, as long as it is grounded in existing artifacts;
- the frame sample times and evidence folder layout;
- the report layout.

The worker must not decide:

- to edit code/tests/tools;
- to edit previous runs in place;
- to treat simulated approval as real user approval;
- to use a waiver instead of completing required artifacts;
- to mark `frame_evidence.pass=true` without support.

## Final Report Requirements

Create:

`docs/construction-guides/work-orders/2026-07-06-parent-agent-delivery-cut-report.md`

The worker's final message must include:

- output root and run path;
- final video path;
- parent orchestration log path;
- subagent dispatch record paths and whether real subagents or fallback ran;
- audio/music/subtitle/frame-evidence artifacts created;
- `pipeline_home` status;
- delivery gate pass/block status and remaining blocks if any;
- commands with exit codes;
- explicit statement that real user approval is still required;
- next recommended work grounded only in this run.
