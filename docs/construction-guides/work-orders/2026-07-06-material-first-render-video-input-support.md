# Work Order: Material-First Render Video Input Support

Date: 2026-07-06
Status: ready for execution

## Background

The real-material simulated-client production drill reached actual render and
then stopped correctly:

- Drill report: `docs/construction-guides/work-orders/2026-07-06-real-material-simulated-client-production-drill-report.md`
- Drill run: `.tmp/simulated_client_production_drill_20260706-062052/run`
- Render result: `ffmpeg_render_failed`
- Error: `Option loop not found.`

The drill run's `render_handoff.json` contains video inputs:

- `assets/materials/real_0006.mp4`
- `assets/materials/real_0002.mov`
- `assets/materials/real_0003.mp4`

Current renderer behavior in `video_pipeline_core/material_first_render.py`
adds `-loop 1` for every input. That works for still images but fails for the
real video inputs above.

## Goal

Teach the material-first handoff renderer to render run-local video inputs
without breaking the existing still-image render path.

## User-Visible Desired State

A real-material run whose `render_handoff.json` points at run-local `.mp4` or
`.mov` assets can produce a probed `final.mp4`, so the simulated-client drill
can continue past render instead of stopping at `Option loop not found`.

## Non-Goals

- Do not change delivery-gate waiver behavior.
- Do not fabricate `final.mp4`.
- Do not modify source material in `C:/Users/user/Downloads/`.
- Do not edit previous `.tmp` probe/drill folders in place.
- Do not claim delivery success if delivery gate later blocks.
- Do not switch to bare `python` or `pytest`.

## Owner Zone

The worker may edit only:

- `video_pipeline_core/material_first_render.py`
- `tests/test_material_first_review_promotion.py`
- `tests/test_material_first_render.py` if a new focused test file is cleaner
- `.tmp/material_first_render_video_input_support_*/`
- `docs/construction-guides/work-orders/2026-07-06-material-first-render-video-input-support-report.md`

## Forbidden Zone

These paths are read-only:

- `C:/Users/user/Downloads/`
- `.tmp/render_readiness_asset_audit_scope_20260705-235822/`
- `.tmp/simulated_client_production_drill_20260706-062052/`
- `.tmp/real_material_e2e_probe_20260705-220325/`
- `video_pipeline_core/delivery_gate.py`
- `video_pipeline_core/material_first_review_promotion.py`
- `tools/pipeline_home.py`
- `tools/write_delivery_gate_report.py`
- `docs/branch-contract-registry.json`
- `docs/branch-contract-registry.md`
- `docs/pipeline-decision-tree.md`
- `docs/video-pipeline-operating-map.md`

## Required Pieces

### Piece 1: Red-First Coverage

Add a failing test proving that `render_material_first_handoff()` can render a
handoff whose `timeline_refs` point at run-local video files.

The red test must fail before the implementation fix with the current
`Option loop not found` behavior or equivalent render failure.

Use the pinned interpreter:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_material_first_review_promotion
```

If a new test file is used, include it in every command below.

### Piece 2: Renderer Fix

Update `video_pipeline_core/material_first_render.py` so render inputs are
handled by media type:

- still-image inputs keep the existing looped-image behavior;
- video inputs do not use `-loop 1`;
- video inputs respect `start_sec` and `duration_sec` from `render_handoff.json`;
- output remains canonical run-local `final.mp4`;
- `material_first_final_artifact_acceptance.json` still records
  `final_delivery_claimed=false`;
- missing, absolute, or non-`assets/materials/` refs still block before render.

Do not loosen run-local asset validation.

### Piece 3: Targeted Verification

Run:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_material_first_review_promotion
```

Expected: exit code 0.

Then run the focused real-material render smoke from a fresh copy:

```powershell
$STAMP = Get-Date -Format "yyyyMMdd-HHmmss"
$OUT = ".tmp/material_first_render_video_input_support_$STAMP"
$env:SOURCE_RUN = [System.IO.Path]::GetFullPath(".tmp/render_readiness_asset_audit_scope_20260705-235822/flow")
$env:RENDER_RUN = [System.IO.Path]::GetFullPath("$OUT/run")
@'
import os
import shutil
from pathlib import Path
source = Path(os.environ["SOURCE_RUN"])
target = Path(os.environ["RENDER_RUN"])
print("source_exists:", source.is_dir())
if not source.is_dir():
    raise SystemExit(2)
target.parent.mkdir(parents=True, exist_ok=True)
shutil.copytree(source, target)
print("target:", target)
print("copied:", target.is_dir())
'@ | C:\Users\user\miniconda3\python.exe -
```

Expected: exit code 0.

```powershell
@'
import os
import json
from pathlib import Path
from video_pipeline_core.material_first_render import render_material_first_handoff
run = Path(os.environ["RENDER_RUN"])
result = render_material_first_handoff(run)
print(json.dumps(result, ensure_ascii=False, indent=2))
raise SystemExit(0 if result.get("ok") else 1)
'@ | C:\Users\user\miniconda3\python.exe -
```

Expected: exit code 0, `final.mp4` exists, and ffprobe evidence reports at
least one video stream.

### Piece 4: Bounded Simulated Drill Rerun

After Piece 3 is green, rerun the previous simulated-client production drill
from a fresh copy or equivalent fresh drill folder. It must preserve the
simulation boundary and must not edit the previous drill run in place.

Run at least:

```powershell
C:\Users\user\miniconda3\python.exe tools/pipeline_home.py --run "$env:RENDER_RUN" --json
```

```powershell
C:\Users\user\miniconda3\python.exe tools/write_delivery_gate_report.py --run "$env:RENDER_RUN" --json
```

Record truthfully whether delivery gate passes or blocks. A delivery block is
not a renderer failure.

### Piece 5: Report

Write:

`docs/construction-guides/work-orders/2026-07-06-material-first-render-video-input-support-report.md`

The report must include:

- files changed;
- red-first command and failure;
- green test commands and exit codes;
- real-material render smoke output root;
- rendered `final.mp4` path and ffprobe summary;
- `pipeline_home` result;
- delivery gate pass/block result if reached;
- whether any simulated drill artifacts were rerun or reused;
- deviations, skipped items, and blockers.

## Acceptance Commands

Run:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_material_first_review_promotion tests.test_material_first_golden_path tests.test_material_first_source_intake tests.test_material_first_boundary_acceptance tests.test_material_first_landing_case tests.test_material_first_real_source_probe
```

Expected: exit code 0.

Run:

```powershell
git diff --check
```

Expected: exit code 0, except pre-existing CRLF warnings may be recorded if
they remain unchanged.

Run this report/content check:

```powershell
$env:REPORT_PATH = "docs/construction-guides/work-orders/2026-07-06-material-first-render-video-input-support-report.md"
@'
import os
from pathlib import Path
p = Path(os.environ["REPORT_PATH"])
text = p.read_text(encoding="utf-8")
required = ["Option loop not found", "final.mp4", "ffprobe", "pipeline_home", "delivery gate"]
missing = [item for item in required if item not in text]
print("report_exists:", p.exists())
print("missing:", missing)
raise SystemExit(1 if missing else 0)
'@ | C:\Users\user\miniconda3\python.exe -
```

Expected: exit code 0.

## Stop-Loss Limits

Stop and write the report if:

- the red test cannot reproduce the render failure;
- the fix would require changing delivery gate, review promotion, or pipeline
  routing behavior;
- the fresh real-material render smoke cannot copy from the ready flow;
- render still fails after the focused renderer change;
- delivery gate blocks after render succeeds.

For a delivery-gate block after successful render, do not patch around it in
this work order. Record the block as the next recommended work.

## Delegated Decisions

The worker may decide:

- whether to place the new regression in the existing promotion test file or a
  focused material render test file;
- how to classify image vs video input, as long as acceptance covers both the
  existing still-image path and the new video path;
- the exact ffmpeg filter graph, as long as output is playable and probed;
- the exact timestamped scratch folder name;
- the report layout.

The worker must not decide:

- to use bare `python` or `pytest`;
- to skip the red-first test;
- to edit forbidden zones;
- to treat simulated approval as real user approval;
- to claim delivery pass if the delivery gate blocks.

## Final Report Requirements

The worker's final message must include:

- changed files;
- command lines and exit codes;
- red-first failure summary;
- rendered video path;
- ffprobe video-stream evidence;
- `pipeline_home` and delivery gate status;
- deviations/skips/blockers;
- next recommended work grounded only in this run.
