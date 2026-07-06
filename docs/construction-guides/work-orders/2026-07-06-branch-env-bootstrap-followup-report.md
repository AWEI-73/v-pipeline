# Branch Env Bootstrap Follow-Up Report

Date: 2026-07-06

## Summary

Fixed the follow-up gaps from branch env bootstrap:

- `tools/voxcpm_runtime_check.py` now adds repo root to `sys.path` before
  importing `video_pipeline_core.branch_env`.
- Soundtrack branch artifact writing now consumes shared branch env bootstrap
  and writes redacted `soundtrack_branch_env_probe.json`.

No `.env`, `.env.example`, `.venv_voxcpm`, VoxCPM reference repo, Downloads,
existing `.tmp` runs, music download/search, VoxCPM generation, render, or cut
was performed.

## Changed Files

- `tools/voxcpm_runtime_check.py`
- `video_pipeline_core/soundtrack_arranger.py`
- `tests/test_branch_env.py`
- `tests/test_soundtrack_arranger.py`
- `docs/construction-guides/work-orders/2026-07-06-branch-env-bootstrap-followup-report.md`

## Red-First Failures

Direct tool smoke:

```powershell
C:\Users\user\miniconda3\python.exe tools\voxcpm_runtime_check.py --out .tmp\branch_env_bootstrap_followup_red_voxcpm.json
```

Exit code: 1

Failure:

```text
ModuleNotFoundError: No module named 'video_pipeline_core'
```

Red tests after adding coverage:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_branch_env tests.test_soundtrack_arranger
```

Exit code: 1

Failures:

- direct `voxcpm_runtime_check.py` subprocess returned exit code 1 with
  `ModuleNotFoundError`;
- soundtrack writer raised `TypeError: write_soundtrack_artifacts() got an unexpected keyword argument 'repo_root'`.

## Commands And Exit Codes

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_branch_env tests.test_soundtrack_arranger
```

Exit code: 0

```text
Ran 16 tests in 7.780s
OK
```

```powershell
C:\Users\user\miniconda3\python.exe tools\voxcpm_runtime_check.py --out .tmp\branch_env_bootstrap_followup_voxcpm_devcheck.json
```

Exit code: 0

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_branch_env tests.test_voiceover_provider tests.test_soundtrack_arranger tests.test_soundtrack_flow_acceptance
```

Exit code: 0

```text
Ran 25 tests in 10.642s
OK
```

```powershell
C:\Users\user\miniconda3\python.exe tools\voxcpm_runtime_check.py --out .tmp\branch_env_bootstrap_followup_voxcpm_acceptance.json
```

Exit code: 0

## Direct VoxCPM Runtime Result

Acceptance artifact:

```text
.tmp/branch_env_bootstrap_followup_voxcpm_acceptance.json
```

Result:

- `ok_to_execute`: true
- `python`: `C:\Users\user\Desktop\video_pipeline\.venv_voxcpm\Scripts\python.exe`
- `repo_exists`: true
- `cli_exists`: true
- `missing_modules`: []

## Scratch Follow-Up Smoke

Output root:

```text
C:\Users\user\Desktop\video_pipeline\.tmp\branch_env_bootstrap_followup_20260706-095156
```

Direct runtime artifact:

```text
C:\Users\user\Desktop\video_pipeline\.tmp\branch_env_bootstrap_followup_20260706-095156\voxcpm_runtime_check.json
```

Result:

- command exit code: 0
- `ok_to_execute`: true
- `python`: `C:\Users\user\Desktop\video_pipeline\.venv_voxcpm\Scripts\python.exe`

Soundtrack branch env smoke command:

```powershell
C:\Users\user\miniconda3\python.exe tools\soundtrack_arranger.py --input $env:FOLLOWUP_OUT\video_intent.json --out-dir $env:FOLLOWUP_OUT --json
```

Exit code: 0

Soundtrack env smoke artifact:

```text
C:\Users\user\Desktop\video_pipeline\.tmp\branch_env_bootstrap_followup_20260706-095156\soundtrack_branch_env_probe.json
```

Result:

- `JAMENDO_CLIENT_ID` present: true
- `JAMENDO_CLIENT_ID` length: 8
- `PIXABAY_API_KEY` present: true
- `PIXABAY_API_KEY` length: 34
- `yt-dlp` path: `C:\Users\user\miniconda3\Scripts\yt-dlp.EXE`
- `yt-dlp` version: `2026.03.17`
- `secrets_redacted`: true

## Secret Redaction

The soundtrack branch env metadata records only present flags, token lengths,
tool path, and tool version. It does not write raw `JAMENDO_CLIENT_ID` or
`PIXABAY_API_KEY` values. The smoke check scanned the probe JSON for current
environment token values and passed with no leaks.

## Deviations, Skips, Blockers

- Deviations: none.
- Skips: no music download/search, no VoxCPM generation, no render/cut.
- Blockers: none.

## Next Recommended Work

Rerun the parent/subagent continuation for VoxCPM voiceover and real music
source branches from a clean shell, using these direct tool and soundtrack
branch env probes as the baseline evidence.
