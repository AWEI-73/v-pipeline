# Branch Env Bootstrap For VoxCPM And Music Sources Report

Date: 2026-07-06

## Summary

Implemented a shared branch environment bootstrap so clean-shell branch tools can
load known repo-local `.env` keys, default VoxCPM to the repo venv, discover
yt-dlp from PATH, and write probe/report metadata without raw token values.

## Files Changed

- `video_pipeline_core/branch_env.py`
- `video_pipeline_core/voiceover_provider.py`
- `tools/voxcpm_runtime_check.py`
- `tests/test_branch_env.py`
- `docs/construction-guides/work-orders/2026-07-06-branch-env-bootstrap-voxcpm-music-report.md`

## Red-First Failure

Command:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_branch_env
```

Exit code: 1

Result: four import errors before implementation:

```text
ModuleNotFoundError: No module named 'video_pipeline_core.branch_env'
```

This covered the missing shared bootstrap/helper surface before wiring branch
tools to it.

## Commands And Exit Codes

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_branch_env
```

Exit code: 0

```text
Ran 4 tests in 0.065s
OK
```

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_voiceover_provider
```

Exit code: 0

```text
Ran 5 tests in 0.108s
OK
```

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_branch_env tests.test_voiceover_provider tests.test_soundtrack_arranger tests.test_soundtrack_flow_acceptance
```

Exit code: 0

```text
Ran 23 tests in 1.419s
OK
```

```powershell
git diff --check
```

Exit code: 0

Result: only pre-existing CRLF normalization warnings were printed.

## Branch Env Probe

Output root:

```text
.tmp/branch_env_bootstrap_voxcpm_music_20260706-091815
```

Probe path:

```text
.tmp/branch_env_bootstrap_voxcpm_music_20260706-091815/branch_env_probe.json
```

Probe command result: exit code 0.

Probe summary:

- `voxcpm_runtime_ok`: true
- `voxcpm_python`: `C:\Users\user\Desktop\video_pipeline\.venv_voxcpm\Scripts\python.exe`
- `JAMENDO_CLIENT_ID` present: true
- `JAMENDO_CLIENT_ID` length: 8
- `PIXABAY_API_KEY` present: true
- `PIXABAY_API_KEY` length: 34
- `yt-dlp` path: `C:\Users\user\miniconda3\Scripts\yt-dlp.EXE`
- `yt-dlp` version: `2026.03.17`
- `secrets_redacted`: true

VoxCPM runtime details:

- `ok_to_execute`: true
- `repo_exists`: true
- `cli_exists`: true
- `missing_modules`: []

## Secret Redaction Evidence

The probe artifact records only present flags, token lengths, runtime path, and
tool version. It does not include raw `JAMENDO_CLIENT_ID` or `PIXABAY_API_KEY`
values. The report/probe check also scans the latest probe JSON for environment
token values before passing.

## Deviations, Skips, Blockers

- Deviation: none.
- Skips: no music download, no VoxCPM generation, no rendering or cutting, per
  work order.
- Blockers: none.

## Next Recommended Work

Run the parent/subagent continuation again from a clean shell so
voiceover_voxcpm and music-source branches consume this bootstrap and report
real provider availability without false missing-environment blockers.
