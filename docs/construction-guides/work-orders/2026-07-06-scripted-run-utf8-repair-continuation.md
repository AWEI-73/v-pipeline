# Work Order: Scripted Run UTF-8 Repair Continuation

Date: 2026-07-06

## Goal

Repair the existing scripted real-material run after delivery gate correctly blocked corrupted Chinese script/subtitle artifacts. Preserve the existing story contract, source-speech preservation, selected material map, music downloads/probes, and visual timeline. Rebuild the corrupted Chinese narration/subtitle branch, rerender voiceover, remix, reassemble final media, and rerun delivery gate.

This is a run-local continuation, not a code repair round.

## Source Run

`C:\Users\user\Desktop\video_pipeline\.tmp\scripted_real_material_production_run_20260706-131200\run`

Current blocker:

- `delivery_gate.json` has `pass=false`.
- Blocking rules:
  - `corrupt_narration_manifest`
  - `corrupt_subtitles`
- `script.json`, `narration_manifest.json`, and `subtitles.srt` contain repeated literal `?` placeholders.
- Source speech is preserved as `source_speech_director.wav` and must remain preserved.

## Owner Zone

- `C:\Users\user\Desktop\video_pipeline\.tmp\scripted_real_material_production_run_20260706-131200\run`
- `docs/construction-guides/work-orders/2026-07-06-scripted-run-utf8-repair-continuation-report.md`

## Forbidden Zone

- `video_pipeline_core/`
- `tools/`
- `tests/`
- `skills/`
- `.env`
- `.venv_voxcpm/`
- `reference repo/`
- `Downloads/`
- Other `.tmp/` runs except read-only comparison
- Git commit, branch, push, or PR operations

## Runtime And Encoding

Use only:

`C:\Users\user\miniconda3\python.exe`

Do not use bare `python`, `pytest`, or another interpreter.

Do not pass raw Chinese text through PowerShell here-strings, stdin, `>`, `Out-File`, or `Set-Content`.

Use one of these safe paths:

- Write Chinese literals inside Python using Unicode escapes.
- Read Chinese text from an existing UTF-8 file, then write using `Path.write_text(..., encoding="utf-8")`.

After every Chinese JSON/SRT/Markdown artifact write, explicitly check:

- `"\ufffd" not in text`
- no suspicious repeated literal question marks such as `"????"`
- expected Chinese fields contain at least one CJK character

## Required Replacement Text

Use these narration/subtitle texts. Encode them using Unicode escapes or a verified UTF-8 source, not raw PowerShell stdin.

1. `opening_bridge`, 1.0-7.0s, beat `establish_gathering`:
   `畫面從集合與場地展開，這是一段訓練現場從準備走向成果的紀錄。`
2. `process_bridge`, 28.0-38.0s, beats `training_process_detail`, `group_practice_collaboration`:
   `主任的提醒之後，畫面回到訓練過程，動作、口令與團隊節奏逐漸被整理起來。`
3. `outcome_bridge`, 51.0-60.0s, beat `concrete_outcome_review`:
   `最後留下的不只是活動片段，而是這群人完成訓練、互相支撐的證明。`

The source-speech subtitle may continue to use the existing ASR preview, but it must remain marked as requiring human transcript confirmation.

## Ordered Pieces

1. Snapshot current blocker state in a repair note under the run, including current delivery gate blocking rules and question-mark counts.
2. Rewrite `script.json` with the required replacement text and existing timing/story beat mapping.
3. Remove or archive the old corrupted VoxCPM outputs so they cannot be mistaken for regenerated narration.
4. Rerun VoxCPM for the three narration segments using the pinned interpreter and the repaired `script.json`.
5. Rebuild `narration_manifest.json` so its text and commands contain the repaired Chinese strings, not question marks.
6. Rebuild `subtitles.srt` from:
   - the three repaired VoxCPM narration texts and timings
   - the preserved source-speech ASR subtitle at 14.0-24.8s
7. Rebuild `subtitle_audio_alignment_report.json` and make it fail if any aligned text contains repeated `?` or lacks expected CJK.
8. Rebuild/refresh subtitle voiceover handoff if needed.
9. Rerun audio mix so final audio uses regenerated VoxCPM files plus preserved source speech and existing music.
10. Reassemble `final.mp4`.
11. Refresh verify artifacts: ffprobe JSON, contact sheet/frame evidence if final media changed, audio mix evidence, story-to-final alignment if subtitle/narration paths changed.
12. Rerun `pipeline_home` and `write_delivery_gate_report.py`.
13. Write the final repair report.

## Stop-Loss Rules

- If regenerated VoxCPM still contains question marks in text artifacts or audio is not regenerated, stop before final assembly.
- If source speech is dropped or replaced by VoxCPM, stop and report.
- If subtitles still contain `????`, stop before delivery claim.
- Do not edit code/tests/tools to make gate pass.

## Acceptance Commands

Replace `<RUN_DIR>` with the source run path.

1. UTF-8 and CJK artifact check:

```powershell
@'
from pathlib import Path
import json, re, sys
run = Path(r"<RUN_DIR>")
paths = ["script.json", "narration_manifest.json", "subtitles.srt", "subtitle_audio_alignment_report.json"]
bad = []
cjk = re.compile(r"[\u4e00-\u9fff]")
for name in paths:
    text = (run / name).read_text(encoding="utf-8-sig")
    if "\ufffd" in text or "????" in text:
        bad.append(name)
    if name in {"script.json", "narration_manifest.json", "subtitles.srt"} and not cjk.search(text):
        bad.append(name + ":no_cjk")
print({"bad": bad})
sys.exit(0 if not bad else 1)
'@ | C:\Users\user\miniconda3\python.exe -
```

2. Speech preservation and regenerated narration check:

```powershell
@'
from pathlib import Path
import json, sys
run = Path(r"<RUN_DIR>")
speech = json.loads((run / "source_speech_preservation_report.json").read_text(encoding="utf-8-sig"))
manifest = json.loads((run / "narration_manifest.json").read_text(encoding="utf-8-sig"))
files = [Path(seg.get("audio_file") or seg.get("target_file", "")) for seg in manifest.get("segments", [])]
ok_files = [p for p in files if p.exists() and p.stat().st_size > 0]
print({"speech_status": speech.get("status"), "voice_files": len(ok_files)})
sys.exit(0 if speech.get("status") == "preserved" and len(ok_files) >= 3 else 1)
'@ | C:\Users\user\miniconda3\python.exe -
```

3. Final media check:

```powershell
@'
from pathlib import Path
import json, subprocess, sys
run = Path(r"<RUN_DIR>")
final = run / "final.mp4"
probe = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(final)], capture_output=True, text=True)
data = json.loads(probe.stdout) if probe.returncode == 0 and probe.stdout else {}
kinds = {s.get("codec_type") for s in data.get("streams", [])}
print({"final_exists": final.exists(), "streams": sorted(kinds), "duration": data.get("format", {}).get("duration")})
sys.exit(0 if final.exists() and {"video", "audio"} <= kinds else 1)
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

6. Report check:

```powershell
@'
from pathlib import Path
import sys
p = Path("docs/construction-guides/work-orders/2026-07-06-scripted-run-utf8-repair-continuation-report.md")
text = p.read_text(encoding="utf-8")
required = ["UTF-8 repair", "VoxCPM", "Source speech", "Subtitle alignment", "Delivery gate", "Deviations", "Next recommended work"]
missing = [x for x in required if x not in text]
print({"report_exists": p.exists(), "missing": missing})
sys.exit(0 if p.exists() and not missing else 1)
'@ | C:\Users\user\miniconda3\python.exe -
```

## Delegated Decisions

- Exact archive location/name for corrupted pre-repair artifacts inside the run.
- Whether to regenerate only VoxCPM files or any dependent handoff artifacts, provided no corrupted artifact remains canonical.
- Exact review artifact refresh method, provided final media and audio evidence are current.

## Final Report Requirements

Write:

`docs/construction-guides/work-orders/2026-07-06-scripted-run-utf8-repair-continuation-report.md`

Include:

- Run path.
- Pre-repair blocker snapshot.
- UTF-8/CJK checks before and after repair.
- VoxCPM command/exit codes and regenerated voice file paths.
- Source speech preservation status.
- Subtitle alignment result.
- Audio mix and final media result.
- Pipeline home and delivery gate result.
- Verify artifact paths.
- Deviations/skips/blockers.
- Whether the result is now a scripted technical candidate or still blocked.
- Real user approval and legal/music-use review status.
- Next recommended work grounded in this repair run.
