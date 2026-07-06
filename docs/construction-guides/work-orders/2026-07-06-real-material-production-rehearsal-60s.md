# Work Order: Real Material Production Rehearsal 60s

Date: 2026-07-06
Status: ready for execution

## Background

The pipeline has already proven the technical chain on a 12-second candidate:

- real-material visual render;
- VoxCPM voiceover;
- Jamendo music source download;
- soundtrack probe with vocal analysis;
- subtitle/voiceover handoff;
- audio mix and final AV assembly;
- delivery gate pass.

That was a connectivity demo, not a real production rehearsal. The next round
must use the actual real-material source folder and produce a longer candidate
that can be reviewed as a microfilm-style result.

Important source path note: direct Chinese path literals have produced false
negative preflights before. Build the source path using Unicode escapes or
another explicit UTF-8-safe method.

## Goal

Run a real-material production rehearsal from the actual source folder and
produce a 30-60 second technical candidate with multiple clips, multiple
voiceover segments, multiple music needs, downloaded/probed music, subtitles,
frame evidence, audio mix, delivery gate result, and director-review artifacts.

## User-Visible Desired State

The user can inspect:

- a 30-60 second `final.mp4` candidate if all branches connect;
- the selected visual timeline and why the clips were chosen;
- VoxCPM narration with at least three segments;
- at least two downloaded/imported music sources or precise provider blockers;
- soundtrack probe evidence per selected music source;
- subtitles aligned with narration;
- 0.5-second frame contact sheet and audio review artifacts;
- delivery gate pass/block truth;
- clear statement that real user approval is still required.

## Non-Goals

- Do not edit pipeline code, tools, tests, skills, `.env`, `.venv_voxcpm`, or
  `reference repo/VoxCPM-main`.
- Do not edit `C:/Users/user/Downloads/`.
- Do not edit prior `.tmp` runs in place.
- Do not use local synthetic tone/bed as delivery music.
- Do not use waivers to force delivery pass.
- Do not claim final user approval.

## Owner Zone

The worker may write only:

- `.tmp/real_material_production_rehearsal_60s_*/`
- `docs/construction-guides/work-orders/2026-07-06-real-material-production-rehearsal-60s-report.md`

## Forbidden Zone

These paths are read-only:

- `C:/Users/user/Downloads/`
- `.env`
- `.env.example`
- `.venv_voxcpm/`
- `reference repo/VoxCPM-main/`
- existing `.tmp` runs
- `video_pipeline_core/`
- `tools/`
- `tests/`
- `skills/`
- `runs/`
- `examples/`

## Required Flow

### Step 1: Real Source Preflight

Run from repo root:

```powershell
@'
from pathlib import Path
source = Path("C:/Users/user/Downloads") / "\u5fae\u96fb\u5f71\u7d20\u6750" / "_\u6574\u7406\u5f8c"
print("source:", source)
print("exists:", source.exists())
print("is_dir:", source.is_dir())
print("file_count:", sum(1 for p in source.rglob("*") if p.is_file()) if source.is_dir() else 0)
raise SystemExit(0 if source.is_dir() else 2)
'@ | C:\Users\user\miniconda3\python.exe -
```

Expected: exit code 0 and file count greater than 0.

Stop if this fails. Do not substitute fixtures.

### Step 2: Fresh Production Rehearsal Run

Create:

- `.tmp/real_material_production_rehearsal_60s_<timestamp>/run`
- `parent_orchestration_log.md`
- `parent_branch_dispatch_probe.json`
- `subagent_dispatches/`

Use the actual source folder from Step 1. Do not start by copying the
12-second demo run unless you explicitly record it as reference-only context.

### Step 3: Material Intake And Timeline

Run the material-first source/intake path on the source folder, then create a
30-60 second candidate timeline.

Requirements:

- at least six visual clips or a documented reason why fewer clips are better;
- at least three story beats: opening context, training/action/process, group
  closing/outcome;
- selected assets must be copied run-locally under `assets/materials/`;
- no external absolute media refs in render-critical artifacts.

If the existing material-first tools can only create a shorter rough cut, the
parent must extend/repair the fresh run using existing artifacts and record the
limitation. Do not edit code.

### Step 4: Render Visual Candidate

Build render readiness and render the visual candidate to a silent or source-
audio candidate. Preserve it as `final_video_silent.mp4` before final audio
assembly.

Expected duration target: 30-60 seconds.

Stop if rendering fails.

### Step 5: Multi-Segment Script And VoxCPM

Write `script.json` with at least three narration segments grounded in the
selected timeline:

- opening field/context;
- training/process;
- group/outcome/closing.

Run:

```powershell
C:\Users\user\miniconda3\python.exe tools\voxcpm_runtime_check.py --out "$env:RUN_DIR/voxcpm_runtime_check.json"
```

Expected: exit code 0 and `ok_to_execute=true`.

Run:

```powershell
C:\Users\user\miniconda3\python.exe tools\voxcpm_voiceover_provider.py "$env:RUN_DIR/script.json" --out-dir "$env:RUN_DIR" --execute
```

Expected: at least three voiceover audio files and
`narration_manifest.json` with usable audio refs.

### Step 6: Multi-Need Music Source

Create at least two music needs, for example:

- `opening_underlay`: steady documentary bed under narration;
- `training_momentum`: more energetic bed for action/process;
- optional `closing_resolve`: warmer ending cue.

Use branch env bootstrap through the soundtrack branch. Attempt real providers:

- Jamendo;
- Pixabay where applicable;
- yt-dlp fallback only with explicit URL/source/license notes.

For every need, record provider attempts, query/URL, whether a file was
downloaded/imported, file path, byte size, license/source metadata, and blockers.

Do not accept local synthetic music, placeholder, or reference-only music.

### Step 7: Probe, Handoff, Mix, Assemble

For each selected music file:

- run `tools/soundtrack_probe.py`;
- use ASR/vocal analysis when needed for voiceover conflict;
- write or bundle probe reports so audio handoff and delivery gate can read
  the evidence.

Then run subtitle/voiceover handoff, audio handoff, audio mix, and final AV
assembly using existing repo tools. The final `audio_mix_report.json` must
declare:

- `narration_included=true`;
- `music_included=true`;
- duration aligned with final video.

### Step 8: Delivery Gate And Review

Run:

```powershell
C:\Users\user\miniconda3\python.exe tools\pipeline_home.py --run "$env:RUN_DIR" --json
```

Run:

```powershell
C:\Users\user\miniconda3\python.exe tools\write_delivery_gate_report.py --run "$env:RUN_DIR" --json
```

If final media exists, create review artifacts:

- 0.5-second frame contact sheet;
- `final_media_ffprobe.json`;
- `final_audio_ffprobe.json`;
- audio waveform/spectrum if practical;
- review artifact manifest.

## Acceptance Commands

Check source/provenance and multiplicity:

```powershell
@'
import json, os
from pathlib import Path
run = Path(os.environ["RUN_DIR"])
required = ["parent_orchestration_log.md", "parent_branch_dispatch_probe.json", "script.json", "render_handoff.json"]
missing = [name for name in required if not (run / name).is_file()]
script = json.loads((run / "script.json").read_text(encoding="utf-8-sig")) if (run / "script.json").is_file() else {}
segments = script.get("segments") or script.get("narration_segments") or []
handoff = json.loads((run / "render_handoff.json").read_text(encoding="utf-8-sig")) if (run / "render_handoff.json").is_file() else {}
timeline_refs = handoff.get("timeline_refs") or []
print("missing:", missing)
print("script_segments:", len(segments))
print("timeline_refs:", len(timeline_refs))
raise SystemExit(1 if missing or len(segments) < 3 or len(timeline_refs) < 6 else 0)
'@ | C:\Users\user\miniconda3\python.exe -
```

Expected: exit code 0 if a full 30-60 second candidate was built. If it exits
1, report the exact reason and do not hide it.

Check media duration and streams when final exists:

```powershell
@'
import json, os, subprocess
from pathlib import Path
from video_pipeline_core.platform_tools import resolve_ffprobe
run = Path(os.environ["RUN_DIR"])
final = run / "final.mp4"
if not final.is_file():
    print("final_exists: false")
    raise SystemExit(0)
cmd = [resolve_ffprobe(), "-v", "error", "-show_entries", "stream=codec_type,duration:format=duration", "-of", "json", str(final)]
res = subprocess.run(cmd, text=True, capture_output=True)
payload = json.loads(res.stdout or "{}")
types = {s.get("codec_type") for s in payload.get("streams", [])}
duration = float((payload.get("format") or {}).get("duration") or 0)
print("stream_types:", sorted(types))
print("duration:", duration)
raise SystemExit(1 if {"video", "audio"} - types or duration < 30 or duration > 65 else 0)
'@ | C:\Users\user\miniconda3\python.exe -
```

Expected: exit code 0 for completed final media.

Check music downloads:

```powershell
@'
import json, os
from pathlib import Path
run = Path(os.environ["RUN_DIR"])
probe = json.loads((run / "parent_branch_dispatch_probe.json").read_text(encoding="utf-8-sig"))
music = probe.get("music_source_branch") or {}
needs = music.get("needs") or []
downloads = [x for x in music.get("attempts") or [] if x.get("downloaded_or_imported") is True]
bad = [x for x in downloads if not x.get("path") or not Path(x["path"]).is_file() or Path(x["path"]).stat().st_size <= 0]
print("needs:", len(needs))
print("downloads:", len(downloads))
print("bad:", bad)
raise SystemExit(1 if len(needs) < 2 or len(downloads) < 2 or bad else 0)
'@ | C:\Users\user\miniconda3\python.exe -
```

Expected: exit code 0 if music connected. If provider blocks, report blockers.

## Stop-Loss Limits

Stop and write the report if:

- source preflight fails;
- material intake cannot produce enough run-local material;
- render fails;
- VoxCPM runtime or generation fails;
- fewer than three narration segments can be produced;
- fewer than two music needs can be attempted;
- fewer than two music files can be downloaded/imported and probed;
- final media cannot reach 30 seconds;
- delivery gate blocks.

Do not patch code or fake artifacts in this work order.

## Delegated Decisions

The worker may decide:

- exact creative brief and wording;
- exact target duration within 30-60 seconds;
- exact clip choices;
- provider query terms;
- final mix levels;
- whether delivery pass is reachable.

The worker must not decide:

- to use synthetic local music;
- to collapse the test to one narration or one music need;
- to edit forbidden zones;
- to skip download/probe evidence;
- to use waivers;
- to claim real user approval.

## Report Requirements

Create:

`docs/construction-guides/work-orders/2026-07-06-real-material-production-rehearsal-60s-report.md`

The report must include:

- output root and run path;
- source preflight result;
- commands and exit codes;
- subagent dispatch records;
- selected timeline duration and clip count;
- narration segment count and VoxCPM status;
- music needs, provider attempts, downloads/imports, file sizes, license/source
  status;
- probe results;
- final media path/duration/streams if produced;
- delivery gate pass/block result;
- review artifact paths;
- deviations/skips/blockers;
- clear statement that real user approval and legal/music-use review remain
  required.
