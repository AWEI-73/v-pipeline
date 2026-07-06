# Work Order: Real Material Simulated Client Production Drill

Date: 2026-07-06
Status: ready for execution

## Background

The real-material pipeline has reached render readiness:

- Real material source: `C:/Users/user/Downloads/微電影素材/_整理後`
- Ready flow run: `.tmp/render_readiness_asset_audit_scope_20260705-235822/flow`
- `render_readiness_report.json`: `ok=true`
- `render_handoff.json`: exists and `ok=true`
- `final.mp4`: not yet created in that flow

The user now wants to simulate a realistic ambiguous client production process:
the operator starts from vague human intent, talks with a simulated client
subagent, records the conversation, and slowly produces a video candidate.

## Goal

Run a simulated-client production drill on the real material flow, preserving
the full conversation and producing a rendered candidate video plus explicit
simulation-labeled review/delivery artifacts.

## User-Visible Desired State

The user can inspect:

- the full simulated client conversation;
- how vague requests became brief/intent/review decisions;
- the rendered candidate video path;
- whether the pipeline technically rendered and what remains simulated;
- which decisions still require the real user's approval before formal delivery.

## Non-Goals

- Do not claim this is the user's final approval.
- Do not mutate `C:/Users/user/Downloads/`.
- Do not modify pipeline code, tests, skills, or existing runbooks.
- Do not hide or summarize away the simulated conversation.
- Do not edit the ready flow run in place.
- Do not fabricate delivery-gate success if the gate blocks.

## Owner Zone

The worker may write only:

- `.tmp/simulated_client_production_drill_*/`
- `docs/construction-guides/work-orders/2026-07-06-real-material-simulated-client-production-drill-report.md`

The worker may read repo files, previous `.tmp` runs, and the real source
folder.

## Forbidden Zone

These paths are read-only:

- `C:/Users/user/Downloads/`
- `.tmp/render_readiness_asset_audit_scope_20260705-235822/`
- `.tmp/real_material_e2e_probe_20260705-220325/`
- `video_pipeline_core/`
- `tools/`
- `tests/`
- `skills/`
- `runs/`
- `examples/`

## Simulation Contract

The worker must create and preserve:

- `interaction_log.md`: complete worker ↔ simulated client conversation.
- `decision_trace.json`: each human-like statement mapped to interpretation,
  artifact, and whether it is simulated or pipeline-derived.
- `simulated_client_brief.json`: the final brief from the conversation.
- `simulation_notice.json`: states this is a production drill, not real user
  approval.

The simulated client must begin vague, for example:

```text
幫我用這批微電影素材做一支能看的片，感覺要像成果回顧，但我還沒想好細節。
```

The worker must ask at least three useful follow-up questions over the
conversation before locking a brief. The simulated client may answer in
imperfect, human-like language, but must not authorize code changes or claim to
be the real user.

## Required Flow

Run from `C:/Users/user/Desktop/video_pipeline`.

### Step 1: Create Drill Run

Copy the ready flow into a fresh drill run. Do not edit the source flow in
place.

```powershell
$STAMP = Get-Date -Format "yyyyMMdd-HHmmss"
$OUT = ".tmp/simulated_client_production_drill_$STAMP"
$env:SOURCE_RUN = [System.IO.Path]::GetFullPath(".tmp/render_readiness_asset_audit_scope_20260705-235822/flow")
$env:DRILL_RUN = [System.IO.Path]::GetFullPath("$OUT/run")
@'
import os
import shutil
from pathlib import Path
source = Path(os.environ["SOURCE_RUN"])
target = Path(os.environ["DRILL_RUN"])
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

### Step 2: Simulate Conversation

Write `interaction_log.md`, `decision_trace.json`,
`simulated_client_brief.json`, and `simulation_notice.json` inside `$DRILL_RUN`.

Rules:

- Include the opening vague request.
- Include at least three worker questions and simulated client answers.
- The simulated client answers should progressively clarify audience, length,
  tone, must-include preference, and acceptance level.
- Every final brief field must cite the interaction log turn that supports it.
- If using the existing 3-clip/12-second render handoff, disclose that it is a
  technical candidate, not a full creative microfilm.

### Step 3: Render Candidate

Render using the existing `render_handoff.json`.

```powershell
@'
import os
import json
from pathlib import Path
from video_pipeline_core.material_first_render import render_material_first_handoff
run = Path(os.environ["DRILL_RUN"])
result = render_material_first_handoff(run)
print(json.dumps(result, ensure_ascii=False, indent=2))
raise SystemExit(0 if result.get("ok") else 1)
'@ | C:\Users\user\miniconda3\python.exe -
```

Expected: exit code 0, `final.mp4` exists, and
`material_first_final_artifact_acceptance.json` is `ok=true`.

### Step 4: Package As Simulated Candidate

Run `pipeline_home` and delivery gate report. Delivery gate may pass or block;
record the truth.

```powershell
C:\Users\user\miniconda3\python.exe tools/pipeline_home.py --run "$env:DRILL_RUN" --json
```

```powershell
C:\Users\user\miniconda3\python.exe tools/write_delivery_gate_report.py --run "$env:DRILL_RUN" --json
```

Expected: record exit codes and outputs. Do not force pass.

### Step 5: Optional Preview Package

If delivery gate or `pipeline_home` routes to preview packaging and the required
inputs exist, package a verified preview candidate. Do not promote to final
delivery without a simulated review decision artifact that clearly says it is
simulation-only.

## Report Requirements

Create:

`docs/construction-guides/work-orders/2026-07-06-real-material-simulated-client-production-drill-report.md`

The report must include:

- Output root and drill run path.
- Conversation artifact paths.
- Render result and candidate video path.
- `pipeline_home` result.
- Delivery gate result, including blocks/limitations if any.
- Whether a verified preview package was created.
- Clear distinction between technical render success, simulated client
  acceptance, and real user approval still required.
- Top five decisions from `decision_trace.json`.
- Final next recommended work grounded in the drill.

## Acceptance Commands

Run after writing the report:

```powershell
@'
import os
import json
from pathlib import Path
run = Path(os.environ["DRILL_RUN"])
required = [
    "interaction_log.md",
    "decision_trace.json",
    "simulated_client_brief.json",
    "simulation_notice.json",
    "render_handoff.json",
    "final.mp4",
    "material_first_final_artifact_acceptance.json",
]
missing = [name for name in required if not (run / name).is_file()]
acceptance = json.loads((run / "material_first_final_artifact_acceptance.json").read_text(encoding="utf-8-sig")) if not missing else {}
trace = json.loads((run / "decision_trace.json").read_text(encoding="utf-8-sig")) if (run / "decision_trace.json").is_file() else {}
turn_count = len(trace.get("decisions") or [])
print("missing:", missing)
print("render_ok:", acceptance.get("ok"))
print("turn_decisions:", turn_count)
raise SystemExit(1 if missing or acceptance.get("ok") is not True or turn_count < 5 else 0)
'@ | C:\Users\user\miniconda3\python.exe -
```

Expected: exit code 0.

```powershell
$env:REPORT_PATH = "docs/construction-guides/work-orders/2026-07-06-real-material-simulated-client-production-drill-report.md"
@'
import os
from pathlib import Path
p = Path(os.environ["REPORT_PATH"])
text = p.read_text(encoding="utf-8")
required = ["interaction_log.md", "final.mp4", "delivery_gate", "real user approval"]
missing = [item for item in required if item not in text]
print("report_exists:", p.exists())
print("missing:", missing)
raise SystemExit(1 if missing else 0)
'@ | C:\Users\user\miniconda3\python.exe -
```

Expected: exit code 0.

## Stop-Loss Limits

Stop and write the report if:

- The ready source run is missing.
- Rendering fails.
- Any command would require editing outside owner zone.
- The simulated conversation cannot be preserved fully.
- Delivery gate blocks; record it instead of bypassing it.

## Delegated Decisions

The worker may decide:

- The exact simulated client wording.
- The exact timestamped output folder.
- Whether to package a preview candidate after delivery reporting.
- The report layout.

The worker must not decide:

- To treat simulated approval as real user approval.
- To modify source material or pipeline code.
- To hide delivery gate blocks.
- To promote a preview/final as formally delivered.

## Final Report Requirements

The worker's final message must include:

- Output root and drill run path.
- Rendered video path.
- Conversation log path.
- Delivery gate pass/block status.
- Whether preview package was created.
- Explicit statement that real user approval is still required.
- Commands run with exit codes.
