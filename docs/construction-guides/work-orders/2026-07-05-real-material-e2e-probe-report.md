# Real Material Material-First E2E Probe Report

Date: 2026-07-05

## Summary

- Source folder: `C:/Users/user/Downloads/微電影素材/_整理後`
- Source existed: `true`
- Source is directory: `true`
- Output root: `.tmp/real_material_e2e_probe_20260705-220325`
- Delivery gate reached: `false`
- Video-only waiver present: `false`
- Video-only waiver applied: `false`

The rerun used the updated Unicode-escape-safe work-order commands. It reached
the no-render material-first happy path and stopped at the review/render
boundary: `ready_for_render_or_human_review`.

## Commands

### Step 1: source preflight

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

Exit code: `0`

Stdout tail:

```text
source: C:/Users/user/Downloads/微電影素材/_整理後
exists: True
is_dir: True
file_count: 306
first_10: ['67期結訓影片-終.mp4', 'IMG_6039.MOV', '_整理報告.md', '_腳本素材對照表.md', '最終版的最終版.mp4', '進場.MOV', '66期配五班隊呼.mp4', '66期配四班隊呼.mp4', 'MAX_0169.MP4', 'MAX_0171.MP4']
```

Stderr tail: empty.

### Step 2: material_first_real_source_probe

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

Exit code: `0`

Stdout tail:

```text
True ready_for_render_or_human_review
C:\Users\user\Desktop\video_pipeline\.tmp\real_material_e2e_probe_20260705-220325\source_probe
```

Stderr tail: empty.

### Step 3: material_first_happy_path

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

Exit code: `0`

Stdout tail:

```json
{
  "ok": true,
  "run_dir": "C:\\Users\\user\\Desktop\\video_pipeline\\.tmp\\real_material_e2e_probe_20260705-220325\\happy_path",
  "preview_duration_sec": 60.0,
  "preview_clip_count": 10,
  "next_action": "ready_for_render_or_human_review",
  "failed_stage": null,
  "rendered": false,
  "limitations": [
    "This wrapper does not render final.mp4.",
    "The wall verdict is a draft and remains reviewable.",
    "Material truth still belongs to Material Map / review apply / delivery gates."
  ]
}
```

Stderr tail: empty.

### Step 4: pipeline_home

```powershell
C:\Users\user\miniconda3\python.exe tools/pipeline_home.py --run "$OUT/happy_path" --json
```

Exit code: `0`

Stdout tail:

```json
{
  "mode": "run",
  "cursor": "stage5_final_review",
  "next": "ready_for_render_or_human_review",
  "next_action_class": "review_stop",
  "owner": "verify_delivery",
  "reason": "material-first boundary acceptance passed: 3/3 stages passed",
  "source": "material_first_boundary_acceptance_report.json"
}
```

Stderr tail: empty.

### Step 5: write_delivery_gate_report

Not run. The happy-path run did not contain `final.mp4`, a verified preview
candidate, or a `pipeline_home` route to a delivery-gate/write-delivery action.
The only `.mp4/.mov` files under `happy_path` were copied material assets:

- `.tmp/real_material_e2e_probe_20260705-220325/happy_path/assets/materials/real_0002.mov`
- `.tmp/real_material_e2e_probe_20260705-220325/happy_path/assets/materials/real_0003.mp4`
- `.tmp/real_material_e2e_probe_20260705-220325/happy_path/assets/materials/real_0006.mp4`

## Source Metrics

| metric | value |
| --- | ---: |
| total files | 306 |
| supported files | 302 |
| selected assets | 12 |
| accepted assets | 3 |
| rejected/corrupt count | 9 rejected, 0 corrupt/unreadable |
| copied assets | 3 |
| edited-video-like count | 0 |
| asset path audit strict findings | 0 |

Evidence: `.tmp/real_material_e2e_probe_20260705-220325/source_probe/intake_report.json`

## Artifact Inventory

| artifact | path |
| --- | --- |
| source intake report | `.tmp/real_material_e2e_probe_20260705-220325/source_probe/intake_report.json` |
| source scan summary | `.tmp/real_material_e2e_probe_20260705-220325/source_probe/source_scan_summary.json` |
| strict path audit | `.tmp/real_material_e2e_probe_20260705-220325/source_probe/asset_path_audit_strict.json` |
| source probe boundary acceptance | `.tmp/real_material_e2e_probe_20260705-220325/source_probe/run/material_first_boundary_acceptance_report.json` |
| happy path report | `.tmp/real_material_e2e_probe_20260705-220325/happy_path/material_first_happy_path_report.json` |
| happy path boundary acceptance | `.tmp/real_material_e2e_probe_20260705-220325/happy_path/material_first_boundary_acceptance_report.json` |
| material wall draft verdict | `.tmp/real_material_e2e_probe_20260705-220325/happy_path/material_wall_review_verdict.draft.json` |
| preview rough cut plan | `.tmp/real_material_e2e_probe_20260705-220325/happy_path/preview_rough_cut_plan.json` |
| contact sheet | `.tmp/real_material_e2e_probe_20260705-220325/happy_path/material_understanding/material_understanding_contact_sheet.jpg` |
| pipeline cursor source | `.tmp/real_material_e2e_probe_20260705-220325/happy_path/material_first_boundary_acceptance_report.json` |

## Pipeline Cursor Summary

- mode: `run`
- cursor: `stage5_final_review`
- next_action: `ready_for_render_or_human_review`
- next_action_class: `review_stop`
- owner: `verify_delivery`
- source: `material_first_boundary_acceptance_report.json`
- reason: `material-first boundary acceptance passed: 3/3 stages passed`
- read: `material_first_boundary_acceptance_report.json`

## Delivery Gate Summary

- delivery gate reached: `false`
- reason: no final or verified preview candidate, and `pipeline_home` did not
  route to a delivery-gate/write-delivery action
- pass: `not_run`
- blocking: `not_run`
- warnings: `not_run`
- limitations: `not_run`
- waivers_applied: `[]`

## Breakpoints

| order | stage | artifact | rule_or_signal | classification | next_action | evidence_path |
| ---: | --- | --- | --- | --- | --- | --- |
| 1 | pipeline cursor | `material_first_boundary_acceptance_report.json` | `next_action=ready_for_render_or_human_review`; `next_action_class=review_stop` | expected_human_review | ready_for_render_or_human_review | `.tmp/real_material_e2e_probe_20260705-220325/happy_path/material_first_boundary_acceptance_report.json` |
| 2 | material wall review | `material_wall_review_verdict.draft.json` | draft wall verdict remains reviewable | expected_human_review | review_or_apply_primary_wall_verdict | `.tmp/real_material_e2e_probe_20260705-220325/happy_path/material_wall_review_verdict.draft.json` |
| 3 | preview planning | `preview_rough_cut_plan.json` | preview rough cut plan exists but no rendered candidate was produced | expected_human_review | review_preview_rough_cut_before_render | `.tmp/real_material_e2e_probe_20260705-220325/happy_path/preview_rough_cut_plan.json` |
| 4 | delivery gate | `delivery_gate.json` | not reached because there is no `final.mp4` or verified preview candidate | not_reached | render_or_review_candidate_before_delivery_gate | `.tmp/real_material_e2e_probe_20260705-220325/happy_path/` |

## Acceptance Commands

### Acceptance 1: pipeline_home on `$OUT/happy_path`

```powershell
C:\Users\user\miniconda3\python.exe tools/pipeline_home.py --run "$OUT/happy_path" --json
```

Exit code: `0`

Stdout tail:

```json
{
  "mode": "run",
  "cursor": "stage5_final_review",
  "next": "ready_for_render_or_human_review",
  "next_action_class": "review_stop",
  "owner": "verify_delivery",
  "reason": "material-first boundary acceptance passed: 3/3 stages passed",
  "source": "material_first_boundary_acceptance_report.json"
}
```

Stderr tail: empty.

### Acceptance 2: report content check

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

Exit code: `0`

Stdout tail:

```text
report_exists: True
missing: []
```

Stderr tail: empty.

## Final Recommendation

Next single repair/probe round: perform the human/operator review-apply step for
the material wall draft verdict and preview rough cut plan, then render or
package a reviewed preview candidate before attempting the delivery gate. This
recommendation is based on the observed `ready_for_render_or_human_review`,
`review_or_apply_primary_wall_verdict`, and `review_preview_rough_cut_before_render`
signals from this rerun.
