# Work Order: Real Material No-Render Decision Flow

Date: 2026-07-05
Status: ready for execution

## Background

The real-material E2E probe reached the material-first review/render boundary
without code changes:

- Source: `C:/Users/user/Downloads/微電影素材/_整理後`
- Probe output: `.tmp/real_material_e2e_probe_20260705-220325/happy_path`
- Current cursor: `stage5_final_review`
- Current next action: `ready_for_render_or_human_review`
- Delivery gate: not reached

The next useful round is not render. It is a no-render decision flow that
applies the existing draft material wall verdict, checks render readiness, and
writes the render handoff that would be consumed by a later render round.

## Goal

Run the complete no-render material-first decision flow on the real-material
probe output: review packet, explicit probe verdict acceptance, render
readiness gate, and `render_handoff.json`, while preserving the original probe
run as evidence.

## User-Visible Desired State

After this round, the user can inspect a report showing whether the real
material run is ready for a later render without actually rendering: accepted
wall verdict, render readiness, run-local asset refs, timeline refs, and the
next exact render or repair action.

## Non-Goals

- Do not render `final.mp4`.
- Do not call `render_material_first_handoff`.
- Do not run `ffmpeg` intentionally.
- Do not attempt delivery gate.
- Do not edit code, tools, tests, skills, or existing docs other than this
  round's report.
- Do not modify files under `Downloads`.
- Do not claim final human aesthetic approval or final delivery.
- Do not mutate the original probe folder
  `.tmp/real_material_e2e_probe_20260705-220325/happy_path`.

## Owner Zone

The worker may write only:

- `.tmp/real_material_no_render_flow_*/`
- `docs/construction-guides/work-orders/2026-07-05-real-material-no-render-decision-flow-report.md`

The worker may read repo files, the previous `.tmp` probe folder, and the real
source folder.

## Forbidden Zone

These paths are read-only for this work order:

- `C:/Users/user/Downloads/`
- `.tmp/real_material_e2e_probe_20260705-220325/`
- `video_pipeline_core/`
- `tools/`
- `tests/`
- `skills/`
- `runs/`
- `examples/`
- `docs/construction-guides/work-orders/2026-07-05-real-material-e2e-probe-report.md`

## Required Flow

Run from `C:/Users/user/Desktop/video_pipeline`.

### Step 1: Copy The Probe Run

Create a fresh output root and copy the previous happy path run into a new flow
run. Do not work in-place in the previous probe folder.

```powershell
$STAMP = Get-Date -Format "yyyyMMdd-HHmmss"
$OUT = ".tmp/real_material_no_render_flow_$STAMP"
$env:SOURCE_RUN = [System.IO.Path]::GetFullPath(".tmp/real_material_e2e_probe_20260705-220325/happy_path")
$env:FLOW_RUN = [System.IO.Path]::GetFullPath("$OUT/flow")
@'
import os
import shutil
from pathlib import Path
source = Path(os.environ["SOURCE_RUN"])
target = Path(os.environ["FLOW_RUN"])
print("source_exists:", source.is_dir())
print("target:", target)
if not source.is_dir():
    raise SystemExit(2)
if target.exists():
    raise SystemExit(f"target already exists: {target}")
target.parent.mkdir(parents=True, exist_ok=True)
shutil.copytree(source, target)
print("copied:", target.is_dir())
'@ | C:\Users\user\miniconda3\python.exe -
```

Expected: exit code 0.

### Step 2: Build Review Packet

```powershell
@'
import os
import json
from pathlib import Path
from video_pipeline_core.material_first_review_promotion import build_material_first_review_packet
run = Path(os.environ["FLOW_RUN"])
packet = build_material_first_review_packet(run)
print(json.dumps({
    "artifact_role": packet.get("artifact_role"),
    "next_action": packet.get("next_action"),
    "accepted_candidate_assets": len(packet.get("accepted_candidate_assets") or []),
    "write_artifact": (packet.get("verdict_instructions") or {}).get("write_artifact"),
}, ensure_ascii=False, indent=2))
'@ | C:\Users\user\miniconda3\python.exe -
```

Expected: exit code 0 and `accepted_candidate_assets > 0`.

### Step 3: Accept The Draft Verdict As Probe Decision

Use the existing `material_wall_review_verdict.draft.json` from the copied run
as a bounded probe decision. This is not final aesthetic approval.

```powershell
@'
import os
import json
from pathlib import Path
from video_pipeline_core.material_first_review_promotion import accept_material_first_review_verdict
run = Path(os.environ["FLOW_RUN"])
verdict = run / "material_wall_review_verdict.draft.json"
result = accept_material_first_review_verdict(run, verdict)
print(json.dumps(result, ensure_ascii=False, indent=2))
raise SystemExit(0 if result.get("ok") else 1)
'@ | C:\Users\user\miniconda3\python.exe -
```

Expected: exit code 0 and `next_action=ready_for_render_promotion_gate`.

### Step 4: Build Render Readiness / Handoff

```powershell
@'
import os
import json
from pathlib import Path
from video_pipeline_core.material_first_review_promotion import build_material_first_render_promotion
run = Path(os.environ["FLOW_RUN"])
report = build_material_first_render_promotion(run)
print(json.dumps(report, ensure_ascii=False, indent=2))
raise SystemExit(0 if report.get("ok") else 1)
'@ | C:\Users\user\miniconda3\python.exe -
```

Expected: exit code 0, `render_readiness_report.json` exists, and
`render_handoff.json` exists. `final.mp4` must not exist.

### Step 5: Inspect Pipeline Home

```powershell
C:\Users\user\miniconda3\python.exe tools/pipeline_home.py --run "$env:FLOW_RUN" --json
```

Expected: exit code 0. Record the cursor even if it still reports the older
review boundary; this round's primary acceptance is the no-render handoff
artifacts.

## Report Requirements

Create:

`docs/construction-guides/work-orders/2026-07-05-real-material-no-render-decision-flow-report.md`

The report must include:

- Source probe run path and copied flow run path.
- Exact commands, exit codes, and concise stdout/stderr tails.
- Review packet summary.
- Verdict acceptance summary.
- Render readiness summary.
- `render_handoff.json` summary: timeline ref count, render input artifacts,
  and whether all refs are run-local `assets/materials/...`.
- Confirmation that `final.mp4` was not produced.
- `pipeline_home` summary.
- Breakpoint table with columns:
  `order`, `stage`, `artifact`, `rule_or_signal`, `classification`,
  `next_action`, `evidence_path`.
- Final recommendation for the next single round, based only on this no-render
  flow.

## Acceptance Commands

Run after writing the report:

```powershell
@'
import os
import json
from pathlib import Path
run = Path(os.environ["FLOW_RUN"])
required = [
    "material_review_packet.json",
    "material_first_review_verdict_acceptance.json",
    "material_wall_review_verdict.json",
    "render_readiness_report.json",
    "render_handoff.json",
]
missing = [name for name in required if not (run / name).is_file()]
readiness = json.loads((run / "render_readiness_report.json").read_text(encoding="utf-8-sig")) if not missing else {}
handoff = json.loads((run / "render_handoff.json").read_text(encoding="utf-8-sig")) if (run / "render_handoff.json").is_file() else {}
bad_refs = [
    ref for ref in handoff.get("timeline_refs") or []
    if not str(ref.get("source_path") or "").startswith("assets/materials/")
]
print("missing:", missing)
print("readiness_ok:", readiness.get("ok"))
print("handoff_ok:", handoff.get("ok"))
print("bad_refs:", bad_refs)
print("final_mp4_exists:", (run / "final.mp4").exists())
raise SystemExit(1 if missing or readiness.get("ok") is not True or handoff.get("ok") is not True or bad_refs or (run / "final.mp4").exists() else 0)
'@ | C:\Users\user\miniconda3\python.exe -
```

Expected: exit code 0.

```powershell
$env:REPORT_PATH = "docs/construction-guides/work-orders/2026-07-05-real-material-no-render-decision-flow-report.md"
@'
import os
from pathlib import Path
p = Path(os.environ["REPORT_PATH"])
text = p.read_text(encoding="utf-8")
required = ["render_handoff.json", "final.mp4", "pipeline_home", "next_action"]
missing = [item for item in required if item not in text]
print("report_exists:", p.exists())
print("missing:", missing)
raise SystemExit(1 if missing else 0)
'@ | C:\Users\user\miniconda3\python.exe -
```

Expected: exit code 0.

## Stop-Loss Limits

Stop and write the report immediately if:

- The source probe run folder is missing.
- The copied flow run would require editing outside the owner zone.
- Verdict acceptance fails.
- Render readiness fails.
- Any artifact contains external absolute source refs where run-local
  `assets/materials/...` refs are required.
- Any step creates `final.mp4`.

## Delegated Decisions

The worker may decide:

- The exact timestamped `$OUT` folder name.
- How much stdout/stderr to include in the report.
- Whether to include additional artifact summaries if they clarify handoff
  readiness.

The worker must not decide:

- To render, package, or run delivery gate.
- To edit code or tests.
- To modify the previous probe folder in place.
- To relabel this probe acceptance as final human approval.

## Final Report Requirements

The worker's final message must include:

- Output root and flow run path.
- Report path.
- Commands and exit codes.
- Whether verdict acceptance passed.
- Whether render readiness passed.
- Whether `render_handoff.json` exists.
- Confirmation that `final.mp4` was not created.
- The next recommended work, grounded only in this no-render flow.
