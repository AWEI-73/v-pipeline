# Work Order: Branch Env Bootstrap For VoxCPM And Music Sources

Date: 2026-07-06
Status: ready for execution

## Background

The narration/music contract now correctly blocks complete delivery when
voiceover and real music are missing. The latest environment check found the
previous blockers were partly false environment negatives:

- repo root `.env` exists and is ignored by git;
- `.env` contains `JAMENDO_CLIENT_ID` and `PIXABAY_API_KEY`;
- `yt-dlp.exe` is available at `C:/Users/user/miniconda3/Scripts/yt-dlp.exe`;
- `.venv_voxcpm/Scripts/python.exe` exists;
- VoxCPM runtime check succeeds when `VOXCPM_PYTHON` points to that venv.

The branch workers previously looked only at the current process environment,
so they reported Jamendo/Pixabay/VoxCPM unavailable even though the repo has
the needed local configuration.

## Goal

Add a safe branch environment bootstrap so voiceover and music-source branches
can see repo-local credentials/runtime paths without leaking secret values or
requiring manual shell setup.

## User-Visible Desired State

The next parent/subagent continuation can start from a clean shell and still
detect:

- VoxCPM runtime executable through `.venv_voxcpm/Scripts/python.exe`;
- `JAMENDO_CLIENT_ID` present from repo root `.env`;
- `PIXABAY_API_KEY` present from repo root `.env`;
- `yt-dlp` path/version available;
- no token values written into reports, manifests, prompts, or logs.

## Non-Goals

- Do not download music.
- Do not execute VoxCPM generation.
- Do not edit `.env` or `.env.example` unless a test fixture requires a temp
  copy outside the real file.
- Do not render or re-cut video.
- Do not change delivery requirements.
- Do not relax the narration/music delivery contract.

## Owner Zone

The worker may edit only:

- `video_pipeline_core/branch_env.py` if a new helper is appropriate
- `video_pipeline_core/voiceover_provider.py`
- `video_pipeline_core/soundtrack_arranger.py`
- `video_pipeline_core/audio_handoff_acceptance.py`
- `tools/voxcpm_runtime_check.py`
- `tools/voxcpm_voiceover_provider.py`
- `tools/soundtrack_arranger.py`
- `tools/soundtrack_flow_acceptance.py`
- `tools/soundtrack_probe.py`
- `tests/test_branch_env.py`
- `tests/test_voiceover_provider.py`
- `tests/test_soundtrack_arranger.py`
- `tests/test_soundtrack_flow_acceptance.py`
- `.tmp/branch_env_bootstrap_voxcpm_music_*/`
- `docs/construction-guides/work-orders/2026-07-06-branch-env-bootstrap-voxcpm-music-report.md`

## Forbidden Zone

These paths are read-only:

- `.env`
- `.env.example`
- `C:/Users/user/Downloads/`
- `.venv_voxcpm/`
- `reference repo/VoxCPM-main/`
- `.tmp/parent_agent_delivery_cut_20260706-065345/`
- `.tmp/narration_real_music_branch_contract_20260706-083825/`
- `skills/`
- `runs/`
- `examples/`

## Required Behavior

### Env Loading

Branch tools must load repo root `.env` when needed and only for known keys:

- `JAMENDO_CLIENT_ID`
- `PIXABAY_API_KEY`
- `YTDLP_PATH`
- `HERMES_DEFAULT_MUSIC_PROVIDER`
- `HERMES_DEFAULT_BGM_PROVIDER`
- `VOXCPM_PYTHON`

If `VOXCPM_PYTHON` is missing, default to:

`C:/Users/user/Desktop/video_pipeline/.venv_voxcpm/Scripts/python.exe`

when the file exists.

If `YTDLP_PATH` is missing, discover `yt-dlp` or `yt-dlp.exe` from PATH.

### Secret Hygiene

Reports/artifacts may record only:

- key present true/false;
- token length;
- provider name;
- command/tool path;
- tool version;
- missing key names.

They must not write actual secret/token values.

### Branch Probe Artifact

Create a probe command or helper that writes:

`branch_env_probe.json`

The artifact must include:

- `voxcpm_python`;
- `voxcpm_runtime_ok`;
- `jamendo_client_id_present`;
- `pixabay_api_key_present`;
- `yt_dlp_path`;
- `yt_dlp_version`;
- `secrets_redacted=true`;
- no raw token values.

## Required Pieces

### Piece 1: Red-First Tests

Add tests that fail before the fix:

- with the current process env cleared of music keys, branch env bootstrap still
  finds repo root `.env` keys;
- VoxCPM runtime check uses `.venv_voxcpm/Scripts/python.exe` when
  `VOXCPM_PYTHON` is not set;
- probe/report output redacts secret values;
- yt-dlp is discoverable without `YTDLP_PATH`.

Use temp `.env` fixtures for tests. Do not edit the real `.env`.

### Piece 2: Bootstrap Implementation

Implement the minimal helper/wiring so branch tools can use the bootstrap
without duplicating parsing logic.

Do not overwrite existing environment variables if already set.

### Piece 3: Local Probe

Run a scratch probe from a clean-ish process:

```powershell
$STAMP = Get-Date -Format "yyyyMMdd-HHmmss"
$OUT = ".tmp/branch_env_bootstrap_voxcpm_music_$STAMP"
$env:BRANCH_ENV_OUT = [System.IO.Path]::GetFullPath("$OUT")
New-Item -ItemType Directory -Force $env:BRANCH_ENV_OUT | Out-Null
```

Then run the implemented probe command or a pinned Python snippet using the new
helper. It must write:

`$env:BRANCH_ENV_OUT/branch_env_probe.json`

Expected:

- VoxCPM runtime ok is true;
- Jamendo present is true;
- Pixabay present is true;
- yt-dlp version is present;
- no actual token value appears in the JSON.

### Piece 4: Report

Write:

`docs/construction-guides/work-orders/2026-07-06-branch-env-bootstrap-voxcpm-music-report.md`

Include:

- files changed;
- red-first failures;
- test commands and exit codes;
- probe output root;
- VoxCPM runtime result;
- Jamendo/Pixabay present flags;
- yt-dlp path/version;
- secret redaction evidence;
- deviations/skips/blockers.

## Acceptance Commands

Run:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_branch_env tests.test_voiceover_provider tests.test_soundtrack_arranger tests.test_soundtrack_flow_acceptance
```

Expected: exit code 0.

Run:

```powershell
git diff --check
```

Expected: exit code 0, except unchanged pre-existing CRLF warnings may be
recorded.

Run report/probe check:

```powershell
$env:REPORT_PATH = "docs/construction-guides/work-orders/2026-07-06-branch-env-bootstrap-voxcpm-music-report.md"
@'
import json
import os
from pathlib import Path
report = Path(os.environ["REPORT_PATH"])
text = report.read_text(encoding="utf-8")
required = ["VoxCPM", "JAMENDO_CLIENT_ID", "PIXABAY_API_KEY", "yt-dlp", "secrets_redacted"]
missing = [item for item in required if item not in text]
probes = sorted(Path(".tmp").glob("branch_env_bootstrap_voxcpm_music_*/branch_env_probe.json"))
probe = json.loads(probes[-1].read_text(encoding="utf-8")) if probes else {}
bad_secret_leaks = []
for key in ("JAMENDO_CLIENT_ID", "PIXABAY_API_KEY"):
    value = os.environ.get(key)
    if value and value in json.dumps(probe):
        bad_secret_leaks.append(key)
print("report_exists:", report.exists())
print("missing:", missing)
print("probe_exists:", bool(probes))
print("voxcpm_runtime_ok:", probe.get("voxcpm_runtime_ok"))
print("jamendo_present:", probe.get("jamendo_client_id_present"))
print("pixabay_present:", probe.get("pixabay_api_key_present"))
print("yt_dlp_version:", probe.get("yt_dlp_version"))
print("bad_secret_leaks:", bad_secret_leaks)
raise SystemExit(1 if missing or not probes or not probe.get("voxcpm_runtime_ok") or not probe.get("jamendo_client_id_present") or not probe.get("pixabay_api_key_present") or not probe.get("yt_dlp_version") or bad_secret_leaks else 0)
'@ | C:\Users\user\miniconda3\python.exe -
```

Expected: exit code 0.

## Stop-Loss Limits

Stop and report if:

- the implementation would require editing `.env`;
- the implementation would print or write raw token values;
- VoxCPM runtime fails even after defaulting to `.venv_voxcpm`;
- repo root `.env` cannot be parsed;
- yt-dlp cannot be found from PATH.

## Delegated Decisions

The worker may decide:

- exact helper name and module layout;
- whether the probe is a tool command or a pinned Python snippet;
- exact JSON field names in addition to the required fields;
- whether to wire bootstrap into all soundtrack tools now or through the shared
  helper used by them.

The worker must not decide:

- to edit real `.env`;
- to log token values;
- to download music;
- to execute VoxCPM generation;
- to weaken narration/music contract requirements.

## Final Report Requirements

The worker's final message must include:

- changed files;
- commands with exit codes;
- branch env probe path;
- VoxCPM runtime status;
- Jamendo/Pixabay present flags;
- yt-dlp path/version;
- secret redaction statement;
- deviations/skips/blockers;
- next recommended work grounded only in this run.
