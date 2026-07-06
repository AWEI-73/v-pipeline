# Work Order: Branch Env Bootstrap Follow-Up

Date: 2026-07-06
Status: ready for execution

## Background

The previous branch-env bootstrap work added:

- `video_pipeline_core/branch_env.py`
- `tests/test_branch_env.py`
- wiring for VoxCPM provider/runtime code
- report: `docs/construction-guides/work-orders/2026-07-06-branch-env-bootstrap-voxcpm-music-report.md`

Review found two remaining issues:

1. Directly running `tools/voxcpm_runtime_check.py` from the repo root fails:

   ```text
   ModuleNotFoundError: No module named 'video_pipeline_core'
   ```

   The import of `video_pipeline_core.branch_env` happens before the tool adds
   repo root to `sys.path`.

2. The shared bootstrap exists, but soundtrack/music-source entrypoints do not
   appear to consume it. The helper can see `JAMENDO_CLIENT_ID`,
   `PIXABAY_API_KEY`, and `yt-dlp`, but music branch tools may still run from a
   clean shell without loading repo root `.env`.

## Goal

Finish the bootstrap wiring so direct VoxCPM runtime checks and soundtrack
branch entrypoints both use the shared branch environment bootstrap.

## User-Visible Desired State

From a clean shell in `C:/Users/user/Desktop/video_pipeline`:

- `C:\Users\user\miniconda3\python.exe tools\voxcpm_runtime_check.py --out ...`
  succeeds and uses `.venv_voxcpm/Scripts/python.exe`;
- soundtrack/music-source branch commands can detect Jamendo/Pixabay key
  presence and `yt-dlp` path/version through the shared bootstrap;
- no token values are printed or written.

## Non-Goals

- Do not download music.
- Do not run VoxCPM generation.
- Do not edit `.env`, `.env.example`, `.venv_voxcpm`, or
  `reference repo/VoxCPM-main`.
- Do not render or cut video.
- Do not change narration/music delivery contract rules.

## Owner Zone

The worker may edit only:

- `video_pipeline_core/branch_env.py`
- `video_pipeline_core/voiceover_provider.py`
- `video_pipeline_core/soundtrack_arranger.py`
- `tools/voxcpm_runtime_check.py`
- `tools/voxcpm_voiceover_provider.py`
- `tools/soundtrack_arranger.py`
- `tools/soundtrack_flow_acceptance.py`
- `tools/soundtrack_probe.py`
- `tests/test_branch_env.py`
- `tests/test_voiceover_provider.py`
- `tests/test_soundtrack_arranger.py`
- `tests/test_soundtrack_flow_acceptance.py`
- `.tmp/branch_env_bootstrap_followup_*/`
- `docs/construction-guides/work-orders/2026-07-06-branch-env-bootstrap-followup-report.md`

## Forbidden Zone

These paths are read-only:

- `.env`
- `.env.example`
- `.venv_voxcpm/`
- `reference repo/VoxCPM-main/`
- `C:/Users/user/Downloads/`
- existing `.tmp` runs
- `video_pipeline_core/delivery_gate.py`
- tests unrelated to branch env / voiceover / soundtrack

## Required Pieces

### Piece 1: Red-First Smokes

Record the current failures before fixing:

```powershell
C:\Users\user\miniconda3\python.exe tools\voxcpm_runtime_check.py --out .tmp\branch_env_bootstrap_followup_red_voxcpm.json
```

Expected before fix: exit code nonzero with `ModuleNotFoundError` or equivalent.

Add or extend tests so they fail before fix for:

- direct tool import/path behavior;
- soundtrack branch environment availability from a clean env;
- no secret values in soundtrack/branch env metadata.

### Piece 2: Fix Direct Tool Import

Ensure all tools importing `video_pipeline_core.branch_env` add repo root to
`sys.path` before the import, following existing tool style.

At minimum fix `tools/voxcpm_runtime_check.py`.

### Piece 3: Wire Soundtrack Branch

Wire `bootstrap_branch_env()` into soundtrack/music-source entrypoints or the
shared soundtrack arranger core so they can use repo root `.env` and discovered
`yt-dlp`.

Required artifact or command output must expose redacted branch env metadata:

- Jamendo present true/false and length;
- Pixabay present true/false and length;
- `yt-dlp` path and version;
- `secrets_redacted=true`;
- no raw token values.

Do not perform provider download/search in this work order.

### Piece 4: Scratch Probe

Create a fresh scratch output:

```powershell
$STAMP = Get-Date -Format "yyyyMMdd-HHmmss"
$OUT = ".tmp/branch_env_bootstrap_followup_$STAMP"
$env:FOLLOWUP_OUT = [System.IO.Path]::GetFullPath($OUT)
New-Item -ItemType Directory -Force $env:FOLLOWUP_OUT | Out-Null
```

Run direct VoxCPM runtime check:

```powershell
C:\Users\user\miniconda3\python.exe tools\voxcpm_runtime_check.py --out "$env:FOLLOWUP_OUT/voxcpm_runtime_check.json"
```

Expected: exit code 0, `ok_to_execute=true`.

Run the soundtrack/music-source branch env smoke implemented in this work
order. It must write:

`$env:FOLLOWUP_OUT/soundtrack_branch_env_probe.json`

Expected:

- Jamendo present true;
- Pixabay present true;
- yt-dlp version present;
- secrets redacted true.

### Piece 5: Report

Write:

`docs/construction-guides/work-orders/2026-07-06-branch-env-bootstrap-followup-report.md`

Include:

- changed files;
- red-first failure;
- direct VoxCPM smoke result;
- soundtrack branch env smoke result;
- Jamendo/Pixabay present flags;
- yt-dlp path/version;
- secret redaction evidence;
- test commands and exit codes;
- deviations/skips/blockers.

## Acceptance Commands

Run:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_branch_env tests.test_voiceover_provider tests.test_soundtrack_arranger tests.test_soundtrack_flow_acceptance
```

Expected: exit code 0.

Run:

```powershell
C:\Users\user\miniconda3\python.exe tools\voxcpm_runtime_check.py --out .tmp\branch_env_bootstrap_followup_voxcpm_acceptance.json
```

Expected: exit code 0 and JSON `ok_to_execute=true`.

Run the implemented soundtrack branch env smoke. Expected: exit code 0 and
JSON reports Jamendo/Pixabay/yt-dlp present with no token leakage.

Run:

```powershell
git diff --check
```

Expected: exit code 0, except unchanged pre-existing CRLF warnings may be
recorded.

Run report check:

```powershell
$env:REPORT_PATH = "docs/construction-guides/work-orders/2026-07-06-branch-env-bootstrap-followup-report.md"
@'
from pathlib import Path
import os
text = Path(os.environ["REPORT_PATH"]).read_text(encoding="utf-8")
required = ["ModuleNotFoundError", "voxcpm_runtime_check.py", "JAMENDO_CLIENT_ID", "PIXABAY_API_KEY", "yt-dlp", "secrets_redacted"]
missing = [item for item in required if item not in text]
print("missing:", missing)
raise SystemExit(1 if missing else 0)
'@ | C:\Users\user\miniconda3\python.exe -
```

Expected: exit code 0.

## Stop-Loss Limits

Stop and report if:

- fixing direct imports requires broad tool restructuring;
- soundtrack branch env visibility would require downloading or contacting
  providers;
- any probe/report would print raw token values;
- `.env` or `.venv_voxcpm` would need edits.

## Delegated Decisions

The worker may decide:

- whether the soundtrack branch env smoke is a new tool flag, helper function,
  or test-only command;
- exact JSON field names in addition to required fields;
- whether wiring lives in tools or the shared soundtrack arranger core.

The worker must not decide:

- to skip direct tool smoke;
- to download/search music;
- to run VoxCPM generation;
- to log token values;
- to edit forbidden files.

## Final Report Requirements

The worker's final message must include:

- changed files;
- commands and exit codes;
- red-first direct-tool failure;
- direct VoxCPM runtime result;
- soundtrack branch env smoke path/result;
- secret redaction statement;
- deviations/skips/blockers;
- next recommended work grounded only in this run.
