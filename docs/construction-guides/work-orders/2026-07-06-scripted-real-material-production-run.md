# Work Order: Scripted Real-Material Production Run

Date: 2026-07-06

## Goal

Run a fresh real-material video production from a designed story contract, not a generic technical rehearsal. The output should test whether the pipeline can make a coherent short film where the story contract, selected shots, source speech, VoxCPM narration, subtitles, music, final media, and review artifacts can be compared directly.

This round may use a simulated client scenario, but all missing facts must be labeled as agent-filled and lower authority than source material or human-supplied facts.

## Scenario Contract

Create `story_contract.json` in the fresh run with this scenario:

- Working title: `訓練現場：從集合到成果`
- Intended audience: internal review / training recap
- Target duration: 45-75 seconds
- Tone: documentary, clear, grounded; not a hype montage
- Required story beats:
  1. Establish the place and group gathering.
  2. Preserve at least one visible speaker / director / instructor speech moment as source speech if usable source audio exists.
  3. Show training/process detail with matching visuals.
  4. Show group practice or collaboration.
  5. Close with a concrete outcome or review moment.
- Audio intent:
  - Human/source speech is first priority.
  - VoxCPM narration may bridge gaps, introduce context, or summarize, but must not replace visible source speech unless the source audio is unusable and the reason is recorded.
  - Music supports the edit and ducks under speech/narration.
- Subtitle intent:
  - Subtitles must correspond to actual audible speech/narration segments.
  - If subtitle text is editorial rather than transcript, mark it as `editorial_caption`, not transcript.

For every field that is not directly from the user or source artifacts, include:

```json
{"value": "...", "authority": "agent_filled", "needs_human_confirmation": true}
```

For fields that come from this work order, use `authority: "human_directed_work_order"`.

## Owner Zone

- `.tmp/scripted_real_material_production_run_<timestamp>/`
- `docs/construction-guides/work-orders/2026-07-06-scripted-real-material-production-run-report.md`

## Forbidden Zone

- `video_pipeline_core/`
- `tools/`
- `tests/`
- `skills/`
- `.env`
- `.venv_voxcpm/`
- `reference repo/`
- `Downloads/`
- Existing `.tmp/` runs except read-only comparison
- Git commit, branch, push, or PR operations

## Runtime

Use only:

`C:\Users\user\miniconda3\python.exe`

Do not use bare `python`, `pytest`, or another interpreter.

Use the real source folder via Unicode escapes:

```python
Path("C:/Users/user/Downloads") / "\u5fae\u96fb\u5f71\u7d20\u6750" / "_\u6574\u7406\u5f8c"
```

## Ordered Pieces

1. Create a fresh output root and `run/`.
2. Preflight source folder; record `exists`, `is_dir`, and `file_count`.
3. Write `story_contract.json` using the scenario above and authority labels.
4. Probe/select candidate clips for story beats. Produce `story_to_material_map.json` with:
   - beat id
   - selected source file(s)
   - evidence type (`visual_match`, `source_speech`, `agent_inferred`)
   - confidence
   - whether human confirmation is needed
5. Identify visible speaker / director / instructor moments. If source audio is usable, preserve at least one source-speech segment in the audio plan. If not usable, write `source_speech_rejection_report.json` with concrete evidence.
6. Build a 45-75s visual timeline with at least 7 real source clips and run-local assets.
7. Create narration plan:
   - At least 2 VoxCPM segments.
   - Narration must not duplicate or overwrite preserved source speech.
   - Record how each narration segment maps to story beats.
8. Create subtitle/caption plan:
   - Transcript subtitles for source speech / VoxCPM where possible.
   - Editorial captions must be labeled separately.
   - Do not write a generic subtitle file unrelated to audible speech.
9. Select/download/import at least 2 real/sourceable music files and run probe/ASR. Synthetic generated beds do not count.
10. Build audio handoff and mix:
    - Preserve source speech if available.
    - Include VoxCPM narration.
    - Include music ducked under speech/narration.
11. Assemble `final.mp4`.
12. Run pipeline home and delivery gate.
13. Produce verify artifacts:
    - 0.5s frame contact sheet
    - ffprobe JSON for final media and audio
    - story-to-final alignment report
    - source-speech preservation report
    - subtitle-audio alignment report
14. Write final report.

## Stop-Loss Rules

- If no visible speaker / source speech can be found or preserved, do not silently replace it with VoxCPM. Record the reason and continue only as a `no_source_speech_available` technical candidate.
- If subtitles do not correspond to audible speech/narration, delivery may still run, but the report must mark `subtitle_alignment_failed`.
- If music cannot be sourced/probed, stop before final delivery claim.
- If final media is absent, do not run a final-delivery claim.
- Do not patch code/tests/tools to make this pass.

## Acceptance Commands

Replace `<RUN_DIR>` with the fresh run path.

1. Contract and source map check:

```powershell
@'
from pathlib import Path
import json, sys
run = Path(r"<RUN_DIR>")
required = ["story_contract.json", "story_to_material_map.json", "render_handoff.json"]
missing = [x for x in required if not (run / x).exists()]
contract = json.loads((run / "story_contract.json").read_text(encoding="utf-8-sig")) if not missing else {}
beats = contract.get("required_story_beats") or contract.get("beats") or []
print({"missing": missing, "beat_count": len(beats)})
sys.exit(0 if not missing and len(beats) >= 5 else 1)
'@ | C:\Users\user\miniconda3\python.exe -
```

2. Speech/narration/subtitle check:

```powershell
@'
from pathlib import Path
import json, sys
run = Path(r"<RUN_DIR>")
required = ["source_speech_preservation_report.json", "narration_manifest.json", "subtitle_audio_alignment_report.json", "subtitles.srt"]
missing = [x for x in required if not (run / x).exists()]
speech = json.loads((run / "source_speech_preservation_report.json").read_text(encoding="utf-8-sig")) if not missing else {}
align = json.loads((run / "subtitle_audio_alignment_report.json").read_text(encoding="utf-8-sig")) if not missing else {}
print({"missing": missing, "source_speech_status": speech.get("status"), "subtitle_ok": align.get("ok")})
sys.exit(0 if not missing and align.get("ok") is True else 1)
'@ | C:\Users\user\miniconda3\python.exe -
```

3. Music and final media check:

```powershell
@'
from pathlib import Path
import json, subprocess, sys
run = Path(r"<RUN_DIR>")
music = json.loads((run / "music_manifest.json").read_text(encoding="utf-8-sig"))
items = music.get("items") or music.get("tracks") or music.get("downloads") or []
final = run / "final.mp4"
probe = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(final)], capture_output=True, text=True)
data = json.loads(probe.stdout) if probe.returncode == 0 and probe.stdout else {}
kinds = {s.get("codec_type") for s in data.get("streams", [])}
print({"music_count": len(items), "final_exists": final.exists(), "streams": sorted(kinds)})
sys.exit(0 if len(items) >= 2 and {"video", "audio"} <= kinds else 1)
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
p = Path("docs/construction-guides/work-orders/2026-07-06-scripted-real-material-production-run-report.md")
text = p.read_text(encoding="utf-8")
required = ["Story contract", "Source speech", "Subtitle alignment", "Story-to-final alignment", "Delivery gate", "Deviations", "Next recommended work"]
missing = [x for x in required if x not in text]
print({"report_exists": p.exists(), "missing": missing})
sys.exit(0 if p.exists() and not missing else 1)
'@ | C:\Users\user\miniconda3\python.exe -
```

## Delegated Decisions

- Exact clip choices and timing, provided every selected clip maps to a story beat with evidence.
- Exact simulated missing details, provided each is marked `agent_filled` and `needs_human_confirmation`.
- Exact VoxCPM narration wording, provided it does not replace preserved source speech and maps to beats.
- Exact music provider/source choice, provided music is real/sourceable and probed.
- Exact verify artifact layout, provided the required reports exist.

## Final Report Requirements

Write:

`docs/construction-guides/work-orders/2026-07-06-scripted-real-material-production-run-report.md`

Include:

- Output root and run path.
- Source preflight.
- Story contract summary and all agent-filled fields.
- Story-to-material map summary.
- Source speech status: preserved / rejected / unavailable, with evidence.
- Narration count and mapping to beats.
- Subtitle-audio alignment result.
- Music download/probe evidence and license caveat.
- Final media path, ffprobe summary, and delivery gate result.
- Verify artifact paths.
- Deviations/skips/blockers.
- Whether this is a true scripted candidate, a technical candidate with story gaps, or blocked.
- Real user approval and legal/music-use review status.
- Next recommended work grounded only in this run.
