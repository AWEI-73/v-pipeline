# Real Material No-Render Decision Flow Report

Date: 2026-07-05

## Summary

- Output root: `.tmp/real_material_no_render_flow_20260705-230801`
- Source probe run: `.tmp/real_material_e2e_probe_20260705-220325/happy_path`
- Flow run path: `.tmp/real_material_no_render_flow_20260705-230801/flow`
- Verdict acceptance status: `ok=true`
- Render readiness status: `ok=false`
- `render_handoff.json` exists: `false`
- `final.mp4` created: `false`

The no-render flow copied the prior real-material probe run, built a material
review packet, and accepted the draft wall verdict as a bounded probe decision.
The flow stopped at render readiness because strict asset path audit did not
pass: `asset_path_audit_failed`, `strict_finding_count=434`.

## Commands

### Step 1: Copy Previous Probe Run

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

Exit code: `0`

Stdout tail:

```text
OUT=.tmp/real_material_no_render_flow_20260705-230801
FLOW_RUN=C:\Users\user\Desktop\video_pipeline\.tmp\real_material_no_render_flow_20260705-230801\flow
source_exists: True
target: C:\Users\user\Desktop\video_pipeline\.tmp\real_material_no_render_flow_20260705-230801\flow
copied: True
```

Stderr tail: empty.

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

Exit code: `0`

Stdout tail:

```json
{
  "artifact_role": "material_review_packet",
  "next_action": "await_material_wall_review",
  "accepted_candidate_assets": 3,
  "write_artifact": "material_wall_review_verdict.json"
}
```

Stderr tail: empty.

### Step 3: Accept Draft Verdict As Probe Decision

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

Exit code: `0`

Stdout tail:

```json
{
  "artifact_role": "material_first_review_verdict_acceptance",
  "ok": true,
  "next_action": "ready_for_render_promotion_gate",
  "decision_source": "human_or_agent_review",
  "accepted_verdict": "material_wall_review_verdict.json",
  "accepted_asset_count": 3,
  "rejected_asset_count": 9,
  "blocking": []
}
```

Stderr tail: empty.

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

Exit code: `1`

Stdout tail:

```json
{
  "artifact_role": "render_readiness_report",
  "ok": false,
  "next_action": "blocked",
  "checks": {
    "material_delta_ready": true,
    "timeline_clip_count": 3,
    "review_verdict_accepted": true,
    "asset_path_audit_strict_ok": false,
    "asset_path_audit_strict_finding_count": 434
  },
  "blocking": [
    {
      "rule": "asset_path_audit_failed",
      "message": "strict asset path audit must pass before render promotion",
      "strict_finding_count": 434
    }
  ]
}
```

Stderr tail: empty.

### Step 5: pipeline_home

Not run. Stop-loss triggered by Step 4 render readiness failure.

## Review Packet Summary

- Artifact: `.tmp/real_material_no_render_flow_20260705-230801/flow/material_review_packet.json`
- artifact_role: `material_review_packet`
- next_action: `await_material_wall_review`
- accepted_candidate_assets: `3`
- verdict write artifact: `material_wall_review_verdict.json`

## Verdict Acceptance Summary

- Artifact: `.tmp/real_material_no_render_flow_20260705-230801/flow/material_first_review_verdict_acceptance.json`
- ok: `true`
- next_action: `ready_for_render_promotion_gate`
- accepted verdict: `material_wall_review_verdict.json`
- accepted asset count: `3`
- rejected asset count: `9`
- blocking: `[]`

This acceptance used `material_wall_review_verdict.draft.json` as a bounded
probe decision only. It is not final human aesthetic approval.

## Render Readiness Summary

- Artifact: `.tmp/real_material_no_render_flow_20260705-230801/flow/render_readiness_report.json`
- ok: `false`
- next_action: `blocked`
- material_delta_ready: `true`
- timeline_clip_count: `3`
- review_verdict_accepted: `true`
- asset_path_audit_strict_ok: `false`
- asset_path_audit_strict_finding_count: `434`
- blocking rule: `asset_path_audit_failed`

## render_handoff.json Summary

- `render_handoff.json` exists: `false`
- timeline ref count: `not_available`
- render input artifacts: `not_available`
- all refs run-local `assets/materials/...`: `not_available`

No render handoff was produced because render readiness failed.

## final.mp4 Confirmation

`final.mp4` was not created in `.tmp/real_material_no_render_flow_20260705-230801/flow`.

## pipeline_home Summary

`pipeline_home` was not run because Step 4 triggered the work-order stop-loss.
The primary cursor for this no-render flow is the render readiness block:

- mode: `not_run`
- cursor: `render_readiness`
- next_action: `blocked`
- source: `render_readiness_report.json`
- reason: `asset_path_audit_failed`

## Breakpoints

| order | stage | artifact | rule_or_signal | classification | next_action | evidence_path |
| ---: | --- | --- | --- | --- | --- | --- |
| 1 | render readiness | `render_readiness_report.json` | `asset_path_audit_failed`; `strict_finding_count=434` | pipeline_contract_issue | blocked | `.tmp/real_material_no_render_flow_20260705-230801/flow/render_readiness_report.json` |
| 2 | render handoff | `render_handoff.json` | not created because render readiness failed | not_reached | fix_asset_path_audit_before_handoff | `.tmp/real_material_no_render_flow_20260705-230801/flow/` |
| 3 | pipeline home | `tools/pipeline_home.py` | not run because render readiness stop-loss fired | not_reached | rerun_after_render_readiness_passes | `.tmp/real_material_no_render_flow_20260705-230801/flow/render_readiness_report.json` |

## Acceptance Commands

### Acceptance 1: Required No-Render Artifacts

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

Exit code: `1`

Stdout tail:

```text
missing: ['render_handoff.json']
readiness_ok: None
handoff_ok: None
bad_refs: []
final_mp4_exists: False
```

Stderr tail: empty.

Interpretation: acceptance failed because the real no-render flow stopped at
render readiness and did not produce `render_handoff.json`. The actual
`render_readiness_report.json` exists and records `ok=false`.

### Acceptance 2: Report Content

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

Exit code: `0`

Stdout tail:

```text
report_exists: True
missing: []
```

Stderr tail: empty.

## Final Recommendation

Next single round: inspect the 434 strict asset path audit findings produced
during render readiness and repair the copied flow run's asset refs so required
render inputs resolve to run-local `assets/materials/...` paths before retrying
render readiness. Do not render until `render_readiness_report.ok=true` and
`render_handoff.json` exists.
