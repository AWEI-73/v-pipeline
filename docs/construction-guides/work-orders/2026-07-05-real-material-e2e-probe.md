# Work Order: Real Material Material-First E2E Probe

Date: 2026-07-05
Status: ready for probe execution

## Background

The material-first delivery gate now has an explicit video-only waiver path.
Previous rounds exercised many bounded gates and fixtures, but the project still
does not have a current, artifact-backed run of today's material-first path on
the user's real material folder.

This round must make contact with real inputs:

`C:/Users/user/Downloads/微電影素材/_整理後`

This is a probe round. The goal is a truthful breakpoint list, not a perfect
final film.

## Goal

Run the current material-first path against the real material folder, capture
the run artifacts, and write a breakpoint report that names exactly where the
route stops, which artifacts/rules caused the stop, and which next actions are
real repair work versus expected human review.

## User-Visible Desired State

After this round, the user can open one report and see what actually happened
when today's pipeline touched the real material folder: source intake metrics,
generated artifacts, current cursor, delivery gate status if reached, and a
prioritized list of breakpoints.

## Non-Goals

- Do not fix pipeline code in this round.
- Do not add a new tool, schema, dashboard state, waiver type, or test suite.
- Do not require perfect `final.mp4` output.
- Do not delete, move, rename, transcode, or modify files under Downloads.
- Do not fabricate human review acceptance.
- Do not bypass review gates to claim E2E success.
- Do not replace real breakpoints with internal cleanup recommendations.

## Owner Zone

The worker may write only these locations:

- `.tmp/real_material_e2e_probe_*/`
- `docs/construction-guides/work-orders/2026-07-05-real-material-e2e-probe-report.md`

The worker may read repo files and the real source folder.

## Forbidden Zone

These paths are read-only for this work order:

- `C:/Users/user/Downloads/微電影素材/_整理後`
- `C:/Users/user/Downloads/`
- `video_pipeline_core/`
- `tools/`
- `tests/`
- `skills/`
- `docs/branch-contract-registry.json`
- `docs/branch-contract-registry.md`
- `docs/pipeline-decision-tree.md`
- `docs/video-pipeline-operating-map.md`
- `runs/`
- `examples/`

## Required Probe Path

Run from `C:/Users/user/Desktop/video_pipeline`.

Use a fresh output root:

```powershell
$STAMP = Get-Date -Format "yyyyMMdd-HHmmss"
$OUT = ".tmp/real_material_e2e_probe_$STAMP"
```

### Step 1: Source Existence / UTF-8 Safe Preflight

```powershell
@'
from pathlib import Path
source = Path("C:/Users/user/Downloads") / "\u5fae\u96fb\u5f71\u7d20\u6750" / "_\u6574\u7406\u5f8c"
print("source:", source.as_posix())
print("exists:", source.exists())
print("is_dir:", source.is_dir())
files = [p for p in source.rglob("*") if p.is_file()] if source.is_dir() else []
print("file_count:", len(files))
print("first_10:", [p.name for p in files[:10]])
'@ | C:\Users\user\miniconda3\python.exe -
```

Expected: exit code 0 and `exists: True`, `is_dir: True`. If not, stop and
write the report.

### Step 2: Real Source Intake Probe

```powershell
$env:PROBE_OUT = [System.IO.Path]::GetFullPath($OUT)
@'
import os
from pathlib import Path
from video_pipeline_core.material_first_real_source_probe import build_material_first_real_source_probe
source = Path("C:/Users/user/Downloads") / "\u5fae\u96fb\u5f71\u7d20\u6750" / "_\u6574\u7406\u5f8c"
out = Path(os.environ["PROBE_OUT"]) / "source_probe"
report = build_material_first_real_source_probe(
    source,
    out,
    max_assets=12,
)
print(report.get("ok"), report.get("next_action"))
print(out)
'@ | C:\Users\user\miniconda3\python.exe -
```

Record `source_probe/intake_report.json`,
`source_probe/source_scan_summary.json`, `source_probe/asset_path_audit_strict.json`,
and `source_probe/run/material_first_boundary_acceptance_report.json` if present.

### Step 3: No-Render Material-First Happy Path

```powershell
$env:PROBE_OUT = [System.IO.Path]::GetFullPath($OUT)
@'
import json
import os
from pathlib import Path
from tools.material_first_happy_path import run_material_first_happy_path
source = Path("C:/Users/user/Downloads") / "\u5fae\u96fb\u5f71\u7d20\u6750" / "_\u6574\u7406\u5f8c"
out = Path(os.environ["PROBE_OUT"]) / "happy_path"
result = run_material_first_happy_path(
    out,
    source_dir=source,
    max_assets=12,
)
print(json.dumps(result, ensure_ascii=False, indent=2))
raise SystemExit(0 if result.get("ok") else 1)
'@ | C:\Users\user\miniconda3\python.exe -
```

Expected: exit code 0 or non-zero. Do not repair on non-zero; record stdout,
stderr, and artifacts.

### Step 4: Pipeline Cursor

```powershell
C:\Users\user\miniconda3\python.exe tools/pipeline_home.py --run "$OUT/happy_path" --json
```

Expected: exit code 0. Record `mode`, `cursor`, `next`, `source`, `reason`, and
`read`.

### Step 5: Delivery Gate If Reached

Run this only if the happy-path run contains a video candidate or
`pipeline_home.py` routes to a delivery-gate/write-delivery action:

```powershell
C:\Users\user\miniconda3\python.exe tools/write_delivery_gate_report.py --run "$OUT/happy_path" --json
```

Record exit code, `pass`, `blocking`, `warnings`, `limitations`, and
`waivers_applied`. Do not create a waiver unless the run already contains one.

## Breakpoint Report Requirements

Create:

`docs/construction-guides/work-orders/2026-07-05-real-material-e2e-probe-report.md`

The report must include:

- Source folder path and whether it existed.
- Output root path.
- Exact commands run, exit codes, and concise stdout/stderr tails.
- Source metrics: total files, supported files, selected assets, rejected/corrupt
  count, copied assets, edited-video-like count.
- Artifact inventory with paths relative to the repo.
- Pipeline cursor summary from `pipeline_home.py`.
- Delivery gate summary if run.
- Breakpoint table with columns:
  `order`, `stage`, `artifact`, `rule_or_signal`, `classification`,
  `next_action`, `evidence_path`.
- Classify each breakpoint as one of:
  `expected_human_review`, `data_issue`, `pipeline_contract_issue`,
  `tool_error`, `environment_issue`, `not_reached`.
- Final recommendation: the next single repair/probe round. It must be based on
  observed breakpoints from this real run.

## Acceptance Commands

Run these after writing the report:

```powershell
C:\Users\user\miniconda3\python.exe tools/pipeline_home.py --run "$OUT/happy_path" --json
```

Expected: exit code 0.

```powershell
$env:REPORT_PATH = "docs/construction-guides/work-orders/2026-07-05-real-material-e2e-probe-report.md"
@'
import os
from pathlib import Path
p = Path(os.environ["REPORT_PATH"])
text = p.read_text(encoding="utf-8")
source = (Path("C:/Users/user/Downloads") / "\u5fae\u96fb\u5f71\u7d20\u6750" / "_\u6574\u7406\u5f8c").as_posix()
required = ["Breakpoint", "pipeline_home", source, "next_action"]
missing = [item for item in required if item not in text]
print("report_exists:", p.exists())
print("missing:", missing)
raise SystemExit(1 if missing else 0)
'@ | C:\Users\user\miniconda3\python.exe -
```

Expected: exit code 0.

## Stop-Loss Limits

Stop and write the report immediately if:

- The source folder does not exist.
- A command would require editing outside the owner zone.
- A command tries to modify or delete the Downloads source folder.
- A tool asks for human creative review or material review; record it instead
  of fabricating approval.
- A run exceeds 30 minutes without producing a new artifact or stdout progress.

## Delegated Decisions

The worker may decide:

- The exact timestamped `$OUT` folder name under `.tmp/`.
- Whether to include more artifact paths than the minimum if they clarify the
  breakpoint.
- Whether to run `tools/material_first_landing_case.py` as an additional
  read-only comparison after the required path, if time permits and it writes
  only inside `$OUT`.

The worker must not decide:

- To edit code or docs other than the required report.
- To skip the real source folder and use fixtures instead.
- To turn this probe into a production render/fix round.
- To replace observed breakpoints with internal cleanup topics.

## Final Report Requirements

The worker's final message must include:

- Output root path.
- Report path.
- Commands run with exit codes.
- Top three breakpoints.
- Whether delivery gate was reached.
- Whether any video-only waiver was present or applied.
- The next recommended work, grounded only in this real-material probe.
