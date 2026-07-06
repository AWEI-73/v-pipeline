# Work Order: Real-Material Full Production Rehearsal After VoxCPM Retry

Date: 2026-07-06

## Goal

Run a fresh 30-60 second real-material production rehearsal through the complete material-first video pipeline after the VoxCPM CPU retry fix. The run must prove whether the voiceover branch can now continue into real music download/probe, audio mix, final AV assembly, delivery gate, and director-review artifacts.

This is not a code repair round. If the complete route still blocks, preserve the real breakpoint evidence instead of patching the pipeline.

## Context Sources

- Current branch includes commit `8c677803` (`Retry VoxCPM narration on CPU after device failure`).
- Previous blocked run: `.tmp/real_material_production_rehearsal_60s_20260706-115057/run`
  - It selected 8 clips and rendered a 40s silent visual.
  - VoxCPM produced 2/3 files and blocked on `opening_context` with return code `3221225477`.
- Diagnostic evidence after the fix:
  - `.tmp/voxcpm_opening_context_diag_20260706-121351`
  - `.tmp/voxcpm_opening_context_narrow_20260706-122007`
  - `.tmp/voxcpm_opening_context_retry_acceptance_20260706-122631`
  - The original 3-segment script reran successfully in a fresh diagnostic output with `voiceover_ready=true`.

## Owner Zone

- `.tmp/real_material_full_production_rehearsal_after_voxcpm_retry_<timestamp>/`
- `docs/construction-guides/work-orders/2026-07-06-real-material-full-production-rehearsal-after-voxcpm-retry-report.md`

## Forbidden Zone

- `video_pipeline_core/`
- `tools/`
- `tests/`
- `skills/`
- `.env`
- `.venv_voxcpm/`
- `reference repo/`
- `Downloads/`
- Existing `.tmp/` runs other than read-only inspection of the context sources above
- Git commit, branch, push, or PR operations

## Runtime

Use the pinned interpreter for every Python command:

`C:\Users\user\miniconda3\python.exe`

Do not use bare `python`, `pytest`, or a different interpreter. This is pinned because prior rounds confused the environment and changed the test runner.

For the real source path, avoid console mojibake by constructing it with Unicode escapes:

```python
Path("C:/Users/user/Downloads") / "\u5fae\u96fb\u5f71\u7d20\u6750" / "_\u6574\u7406\u5f8c"
```

## Ordered Pieces

1. Create a fresh output root under the owner zone.
2. Preflight the real source folder with the Unicode-escaped path. Record `exists`, `is_dir`, and `file_count`.
3. Start a fresh material-first run from the real source folder. Do not copy or continue the previous blocked run as success evidence.
4. Build or select a 30-60 second visual plan with at least 6 real source clips and run-local assets.
5. Render the silent visual candidate. Record duration, file path, and stream evidence.
6. Generate at least 3 narration segments through VoxCPM.
   - If a segment fails on `auto` and CPU retry occurs, record the retry evidence from `voiceover_provider_plan.json`.
   - If VoxCPM still leaves fewer than 3 usable narration files after retry, stop-loss here and report.
7. Continue to the music branch only after voiceover is ready.
   - Require at least 2 distinct music needs.
   - Actually download or import at least 2 real/sourceable music files.
   - Jamendo/Pixabay/yt-dlp/provider source is acceptable only with recorded source metadata.
   - Synthetic generated beds do not satisfy this round.
8. Probe the music files, including vocal-conflict evidence where available. If music source/probe blocks, stop-loss here and report.
9. Build subtitles/voiceover handoff, audio mix, and final AV assembly.
10. Run `pipeline_home` and `write_delivery_gate_report.py`.
11. Produce review artifacts:
    - final media ffprobe JSON
    - final audio ffprobe JSON
    - 0.5-second frame contact sheet or equivalent sampled-frame manifest
    - audio-track/mix evidence with narration and music track mapping
12. Write the final report to the report path in the owner zone.

## Stop-Loss Rules

- Do not patch code or tests to make this pass.
- Do not substitute synthetic music when real/sourceable music download/import fails.
- Do not claim delivery pass if `final.mp4` is absent.
- Do not run delivery gate as a substitute for final assembly; a dashboard/preview gate is not a final delivery pass.
- If an external service blocks, record the command, exit code, and exact artifact state, then stop or continue only where the remaining evidence is still meaningful.

## Acceptance Commands

Run these from repo root. Record command, exit code, and tail/summary in the report.

1. Source/run/provenance check:

```powershell
@'
from pathlib import Path
import json, sys
run = Path(r"<RUN_DIR>")
required = ["script.json", "render_handoff.json", "final_video_silent.mp4"]
missing = [name for name in required if not (run / name).exists()]
print({"run": str(run), "missing": missing})
sys.exit(0 if not missing else 1)
'@ | C:\Users\user\miniconda3\python.exe -
```

2. Multiplicity and branch evidence check:

```powershell
@'
from pathlib import Path
import json, sys
run = Path(r"<RUN_DIR>")
def load(name):
    return json.loads((run / name).read_text(encoding="utf-8-sig"))
script = load("script.json")
handoff = load("subtitle_voiceover_build_handoff.json")
music = load("music_manifest.json")
voice_count = len(handoff.get("voice_files") or [])
music_items = music.get("items") or music.get("tracks") or music.get("downloads") or []
print({"voice_count": voice_count, "music_count": len(music_items)})
sys.exit(0 if voice_count >= 3 and len(music_items) >= 2 else 1)
'@ | C:\Users\user\miniconda3\python.exe -
```

3. Final media check:

```powershell
@'
from pathlib import Path
import json, subprocess, sys
run = Path(r"<RUN_DIR>")
final = run / "final.mp4"
if not final.exists():
    print({"final_exists": False})
    sys.exit(1)
cmd = ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(final)]
result = subprocess.run(cmd, capture_output=True, text=True)
print(result.stdout[-1200:])
data = json.loads(result.stdout)
kinds = {s.get("codec_type") for s in data.get("streams", [])}
sys.exit(0 if {"video", "audio"} <= kinds else 1)
'@ | C:\Users\user\miniconda3\python.exe -
```

4. Pipeline home:

```powershell
C:\Users\user\miniconda3\python.exe tools\pipeline_home.py --run "<RUN_DIR>" --json
```

5. Delivery gate:

```powershell
C:\Users\user\miniconda3\python.exe tools\write_delivery_gate_report.py --run "<RUN_DIR>" --json
```

6. Report content check:

```powershell
@'
from pathlib import Path
import sys
p = Path("docs/construction-guides/work-orders/2026-07-06-real-material-full-production-rehearsal-after-voxcpm-retry-report.md")
text = p.read_text(encoding="utf-8")
required = ["Output root", "Run path", "VoxCPM", "Music downloads", "Delivery gate", "Review artifacts", "Deviations", "Next recommended work"]
missing = [x for x in required if x not in text]
print({"report_exists": p.exists(), "missing": missing})
sys.exit(0 if p.exists() and not missing else 1)
'@ | C:\Users\user\miniconda3\python.exe -
```

## Delegated Decisions

- Exact timestamp suffix and scratch subfolder layout under the owner zone.
- Exact clip choices, pacing, and visual sequence, provided the run uses real source clips and meets the 30-60s / 6+ clip requirements.
- Exact narration text, provided there are at least 3 segments and the handoff proves usable audio refs.
- Exact music provider priority among configured real/sourceable providers, provided the report records source metadata and no synthetic generated bed is counted as music.
- Exact review artifact implementation, provided it includes 0.5-second frame sampling or an equivalent sampled-frame manifest plus audio/media ffprobe evidence.

## Final Report Requirements

Write the report to:

`docs/construction-guides/work-orders/2026-07-06-real-material-full-production-rehearsal-after-voxcpm-retry-report.md`

Include:

- Output root and run path.
- Commands and exit codes.
- Source preflight facts.
- Clip count, duration, and run-local asset evidence.
- VoxCPM segment count, rendered file count, and any CPU retry evidence.
- Music needs count, real download/import count, source metadata, and probe result.
- Audio mix evidence: narration included, music included, track count.
- Final media path, ffprobe summary, and final file size.
- Pipeline home status and delivery gate pass/blocking rules.
- Review artifact paths.
- Deviations, skipped items, and stop-loss trigger if any.
- Whether real user approval and legal/music-use review are still required.
- Next recommended work grounded only in this fresh run.

## Expected Report Summary

If the full route passes, the report should say this is a technical delivery candidate only, not final user approval. If it blocks, it must name the first true blocker and avoid claiming success for later skipped phases.
