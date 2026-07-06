# Work Order: Multisegment Voiceover And Music Continuation

Date: 2026-07-06
Status: ready for execution

## Background

The branch environment bootstrap now works:

- VoxCPM runtime check succeeds from direct tool execution.
- Soundtrack branch env probe sees repo root `.env` keys for Jamendo/Pixabay.
- `yt-dlp` is discoverable and reports a version.

The previous delivery candidate is not acceptable as final film because it used
no narration and a local synthetic music bed. The next run must prove the
parent/subagent route can connect multiple narration and music needs, not just
one token artifact.

## Goal

Run a fresh parent/subagent continuation from the existing real-material visual
candidate, using a multi-segment script with at least two voiceover segments and
at least two distinct music needs. Confirm whether VoxCPM generation, music
source download/import, soundtrack probing, audio mixing, and delivery gate can
connect end to end. If any branch cannot connect, block truthfully with precise
evidence.

## User-Visible Desired State

The user can inspect a fresh run containing:

- a multi-segment narration script;
- VoxCPM runtime evidence;
- `voiceover_provider_plan.json`;
- `narration_manifest.json` with at least two usable voiceover audio refs, or a
  precise VoxCPM blocker;
- at least two music sections/needs;
- music source evidence for each need, including whether a file was actually
  downloaded/imported and from which provider;
- `soundtrack_probe_report.json` or per-track probe bundle;
- `audio_mix_report.json` and final media if branches connect;
- delivery gate truth.

## Non-Goals

- Do not edit pipeline code or tests.
- Do not edit `.env`, `.venv_voxcpm`, or `reference repo/VoxCPM-main`.
- Do not edit previous `.tmp` runs in place.
- Do not use local synthetic tone/bed as delivery music.
- Do not use delivery waivers.
- Do not claim real user approval.

## Owner Zone

The worker may write only:

- `.tmp/multisegment_voiceover_music_continuation_*/`
- `docs/construction-guides/work-orders/2026-07-06-multisegment-voiceover-music-continuation-report.md`

The fresh run inside the output root may create/overwrite its own copied
artifacts, including `final.mp4`.

## Forbidden Zone

These paths are read-only:

- `.env`
- `.env.example`
- `.venv_voxcpm/`
- `reference repo/VoxCPM-main/`
- `C:/Users/user/Downloads/`
- `.tmp/parent_agent_delivery_cut_20260706-065345/`
- `.tmp/narration_real_music_branch_contract_20260706-083825/`
- `.tmp/branch_env_bootstrap_followup_20260706-095156/`
- `video_pipeline_core/`
- `tools/`
- `tests/`
- `skills/`
- `runs/`
- `examples/`

## Required Flow

### Step 1: Fresh Copy

Copy the visual candidate run into a fresh output:

```powershell
$STAMP = Get-Date -Format "yyyyMMdd-HHmmss"
$OUT = ".tmp/multisegment_voiceover_music_continuation_$STAMP"
$env:SOURCE_RUN = [System.IO.Path]::GetFullPath(".tmp/parent_agent_delivery_cut_20260706-065345/run")
$env:CONT_RUN = [System.IO.Path]::GetFullPath("$OUT/run")
@'
import os, shutil
from pathlib import Path
source = Path(os.environ["SOURCE_RUN"])
target = Path(os.environ["CONT_RUN"])
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

### Step 2: Parent Plan And Dispatch Records

Create:

- `parent_orchestration_log.md`
- `parent_branch_dispatch_probe.json`
- `subagent_dispatches/`

Record prompts/results for at least:

- `voiceover_voxcpm`;
- `subtitle_voiceover_handoff`;
- `music_source_editor`;
- `soundtrack_probe`;
- `audio_mix`;
- `delivery_integration`.

Use real subagents if available. If unavailable, parent-side execution is
allowed, but each branch must still write prompt/result records with
`execution_mode`.

### Step 3: Multi-Segment Script

Write `script.json` or equivalent voiceover input with at least two narration
segments. Suggested content:

1. Opening: introduce the training field and purpose.
2. Practice: describe the equipment/teamwork segment.
3. Closing: connect the group activity to outcome/energy.

At least two segments must be rendered or attempted by VoxCPM. Do not collapse
the whole script into one line/audio file.

### Step 4: VoxCPM Voiceover Branch

Run:

```powershell
C:\Users\user\miniconda3\python.exe tools\voxcpm_runtime_check.py --out "$env:CONT_RUN/voxcpm_runtime_check.json"
```

Expected: exit code 0, `ok_to_execute=true`.

Then run VoxCPM through the repo wrapper, using the branch bootstrap default
for `.venv_voxcpm/Scripts/python.exe`:

```powershell
C:\Users\user\miniconda3\python.exe tools\voxcpm_voiceover_provider.py "$env:CONT_RUN/script.json" --out-dir "$env:CONT_RUN" --execute
```

If it succeeds, verify `narration_manifest.json` has at least two segments with
existing audio refs. If it fails, stop before mixing and report the exact
runtime/model/download/error.

### Step 5: Multi-Need Music Source Branch

Write a soundtrack plan with at least two distinct music needs, for example:

- `opening_underlay`: calm/steady BGM under narration;
- `training_momentum`: more energetic instrumental bed for practice/action.

Run soundtrack branch tooling so it consumes branch env bootstrap and records
`soundtrack_branch_env_probe.json`.

The music-source branch must attempt a real provider/source path for each need:

- Jamendo where song/source search is appropriate;
- Pixabay for BGM/instrumental source;
- `yt-dlp` fallback only with explicit source URL/license/usage notes.

For every selected or attempted music need, record:

- provider;
- query or URL;
- whether a file was actually downloaded/imported;
- local file path and byte size if downloaded/imported;
- license/status/usage scope;
- blocker if not downloaded/imported.

Do not accept `generated_bgm.wav`, local tone, placeholder, or reference-only
music as delivery music.

### Step 6: Soundtrack Probe

For each downloaded/imported selected music file, run:

```powershell
C:\Users\user\miniconda3\python.exe tools\soundtrack_probe.py --audio PATH_TO_AUDIO --out PATH_TO_PROBE_JSON --json
```

If narration is present and music may have vocals, use ASR/vocal analysis when
available or block with a vocal-clearance reason. A probe bundle is acceptable
for multiple tracks if the delivery gate/audio handoff can read it.

### Step 7: Subtitle/Voiceover Handoff

Create/repair subtitle and caption evidence from the narration timing. Run:

```powershell
C:\Users\user\miniconda3\python.exe tools\subtitle_voiceover_handoff_accept.py --contract "$env:CONT_RUN/subtitle_voiceover_contract.json" --caption-audit "$env:CONT_RUN/caption_audit.json" --subtitles "$env:CONT_RUN/subtitles.srt" --narration-manifest "$env:CONT_RUN/narration_manifest.json" --voiceover-provider-plan "$env:CONT_RUN/voiceover_provider_plan.json" --voxcpm-runtime-check "$env:CONT_RUN/voxcpm_runtime_check.json" --out-dir "$env:CONT_RUN" --json
```

If required contract/caption artifacts are missing, create them in the fresh
run from the script and record their basis.

### Step 8: Audio Mix And Assembly

Only after voiceover and at least two valid music needs connect, mix audio and
assemble with the visual candidate. Use existing repo audio tools where
possible. Preserve the silent visual as `final_video_silent.mp4` before
overwriting `final.mp4`.

Required if mixing succeeds:

- `final_audio.wav`;
- `audio_mix_report.json`;
- `assembly_report.json` if final AV assembly tool is used;
- final `final.mp4` with video + audio streams;
- `audio_mix_report.narration_included=true`;
- `audio_mix_report.music_included=true`.

### Step 9: Delivery Gate And Review Artifacts

Run:

```powershell
C:\Users\user\miniconda3\python.exe tools\pipeline_home.py --run "$env:CONT_RUN" --json
```

Then:

```powershell
C:\Users\user\miniconda3\python.exe tools\write_delivery_gate_report.py --run "$env:CONT_RUN" --json
```

Record truthfully whether delivery passes or blocks.

If final media is produced, also create 0.5-second frame review contact sheet
and audio probe artifacts under the fresh output root. Do not modify code to do
this; use local ffmpeg/Python snippets.

## Acceptance Commands

Check branch records and multiplicity:

```powershell
@'
import json, os
from pathlib import Path
run = Path(os.environ["CONT_RUN"])
required = ["parent_orchestration_log.md", "parent_branch_dispatch_probe.json", "voxcpm_runtime_check.json", "script.json"]
missing = [name for name in required if not (run / name).is_file()]
script = json.loads((run / "script.json").read_text(encoding="utf-8-sig")) if (run / "script.json").is_file() else {}
segments = script.get("segments") or script.get("narration_segments") or []
dispatch_dir = run / "subagent_dispatches"
dispatch_count = len(list(dispatch_dir.glob("*_result.json"))) if dispatch_dir.is_dir() else 0
print("missing:", missing)
print("script_segments:", len(segments))
print("dispatch_results:", dispatch_count)
raise SystemExit(1 if missing or len(segments) < 2 or dispatch_count < 5 else 0)
'@ | C:\Users\user\miniconda3\python.exe -
```

Expected: exit code 0.

Check download/import evidence:

```powershell
@'
import json, os
from pathlib import Path
run = Path(os.environ["CONT_RUN"])
probe = json.loads((run / "parent_branch_dispatch_probe.json").read_text(encoding="utf-8-sig"))
music = probe.get("music_source_branch") or {}
needs = music.get("needs") or []
downloads = [item for item in music.get("attempts") or [] if item.get("downloaded_or_imported") is True]
bad = [item for item in downloads if not item.get("path") or not Path(item["path"]).is_file() or Path(item["path"]).stat().st_size <= 0]
print("music_needs:", len(needs))
print("downloads:", len(downloads))
print("bad_downloads:", bad)
raise SystemExit(1 if len(needs) < 2 or bad else 0)
'@ | C:\Users\user\miniconda3\python.exe -
```

Expected: exit code 0 if music connected; if no valid source could be
downloaded/imported, this may exit 1, but the final report must list the exact
provider/source blockers.

Check final media if delivery claims success:

```powershell
@'
import json, os, subprocess
from pathlib import Path
from video_pipeline_core.platform_tools import resolve_ffprobe
run = Path(os.environ["CONT_RUN"])
gate = json.loads((run / "delivery_gate.json").read_text(encoding="utf-8-sig")) if (run / "delivery_gate.json").is_file() else {"pass": False}
if gate.get("pass") is not True:
    print("delivery_pass:", gate.get("pass"))
    print("blocking:", [b.get("rule") for b in gate.get("blocking", [])])
    raise SystemExit(0)
cmd = [resolve_ffprobe(), "-v", "error", "-show_entries", "stream=codec_type,duration", "-of", "json", str(run / "final.mp4")]
res = subprocess.run(cmd, text=True, capture_output=True)
payload = json.loads(res.stdout or "{}")
types = {s.get("codec_type") for s in payload.get("streams", [])}
mix = json.loads((run / "audio_mix_report.json").read_text(encoding="utf-8-sig"))
print("stream_types:", sorted(types))
print("narration_included:", mix.get("narration_included"))
print("music_included:", mix.get("music_included"))
raise SystemExit(1 if {"video", "audio"} - types or mix.get("narration_included") is not True or mix.get("music_included") is not True else 0)
'@ | C:\Users\user\miniconda3\python.exe -
```

Expected: exit code 0.

## Stop-Loss Limits

Stop and write the report if:

- VoxCPM runtime check fails;
- VoxCPM generation fails;
- no valid music source can be downloaded/imported for any need;
- only one narration segment or one music need can be exercised;
- soundtrack probe fails for selected music;
- audio mix cannot include narration and music together;
- any required step would edit outside owner zone.

Stop-loss is not failure if the blocker is real and specific. Do not patch code
or fake artifacts in this work order.

## Delegated Decisions

The worker may decide:

- exact narration wording;
- exact provider query terms;
- whether to use Jamendo, Pixabay, yt-dlp fallback, or a combination;
- exact scratch folder stamp;
- exact audio mix levels if mixing succeeds;
- whether final delivery gate pass is reachable in this run.

The worker must not decide:

- to use synthetic local music;
- to collapse multiple segments/needs into one;
- to skip download/import evidence;
- to hide failed provider attempts;
- to use waivers;
- to claim real user approval.

## Report Requirements

Create:

`docs/construction-guides/work-orders/2026-07-06-multisegment-voiceover-music-continuation-report.md`

The report must include:

- output root and run path;
- commands and exit codes;
- subagent dispatch records;
- narration segment count and VoxCPM status;
- music need count;
- provider attempts, downloads/imports, file sizes, and license/source status;
- soundtrack probe results;
- audio mix and final media status;
- delivery gate pass/block result;
- review artifacts if final media exists;
- deviations/skips/blockers;
- next recommended work grounded only in this run.
