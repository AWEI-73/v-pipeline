# Windows Native Migration Spec

Updated: 2026-06-06
Status: accepted
Primary target: Windows native

This document is the implementation contract for migrating the video pipeline
from WSL to Windows without breaking the canonical workflow.

## Paths And Ownership

```text
Primary Windows source:
  C:\Users\user\Desktop\video_pipeline

Primary Windows project/output root:
  C:\Users\user\Desktop\video_project

Example project/output:
  C:\Users\user\Desktop\video_project\coffee

WSL reference source:
  \\wsl$\Ubuntu-24.04\home\lio730309\video_pipeline
```

Ownership rules:

- All new migration development happens in the Windows source.
- WSL remains read-only unless a comparison or emergency reference fix is
  explicitly requested.
- Do not maintain two independent feature branches by manually copying changes
  in both directions.
- Project media and outputs must live under
  `C:\Users\user\Desktop\video_project\<project-name>`.
- Source code must not contain project output, generated media, secrets, or
  active `.env` files.

## Migration Goal

The Windows version must preserve the existing canonical workflow:

```text
brief / interactive spec
-> segment_contract.json
-> build_profile.json + model_routes.json
-> runtime runners
-> final.mp4
-> artifact_manifest.json + state.json + verify artifacts
-> route/dashboard/revision
```

The migration is complete when a Windows agent can create a named project,
execute a canonical no-effects build, inspect artifacts in dashboard/route, and
perform targeted iteration without calling WSL.

## Non-Goals

- Do not rewrite the pipeline from scratch.
- Do not change canonical SPEC contracts merely to fit Windows.
- Do not add heavy motion graphics during portability work.
- Do not rebuild Graphify after every migration step.
- Do not copy old WSL media/output folders into the Windows source tree.
- Do not remove the WSL reference until Windows E2E is verified.

## Small-Step Migration Protocol

Every migration step must follow:

```text
SPEC
  identify one Linux/WSL assumption and expected Windows behavior

BUILD
  make the smallest compatible change in the Windows source

VERIFY
  run focused Windows tests
  run a Windows smoke command
  compare with WSL behavior when the change affects runtime semantics
  run broader Windows tests before marking the step complete
```

Rules:

- One portability boundary per change.
- Add or update a test before changing runtime behavior.
- Preserve artifact names and JSON shapes.
- Prefer Python and `pathlib` over shell-specific scripts.
- Prefer executable discovery/configuration over hardcoded absolute paths.
- A failed verification stops the migration step. Fix or revert before moving
  to the next step.

## Baseline

Current Windows baseline:

```text
Source:
  C:\Users\user\Desktop\video_pipeline

Python:
  3.10.16

Verified:
  python video_tools.py --help
  52 artifact/spec/build-policy smoke tests

Known first Windows migration failure:
  tests.test_project_workspace has 2 failures because active project pointers
  use Windows backslashes instead of portable forward slashes.

Not yet verified:
  ffmpeg / ffprobe runtime
  yt-dlp runtime
  Ollama / qwen3-vl runtime
  edge-tts / ASR runtime
  canonical contract-run true render
  full Windows test suite
  Windows Graphify
```

The WSL baseline remains:

```text
Reference source:
  \\wsl$\Ubuntu-24.04\home\lio730309\video_pipeline

Latest known full test baseline:
  236 tests pass
```

## Migration Phases

### W0: Establish Windows Source And Project Boundaries

SPEC:

- Windows source is `C:\Users\user\Desktop\video_pipeline`.
- Windows project root is `C:\Users\user\Desktop\video_project`.
- Named project layout is:

```text
C:\Users\user\Desktop\video_project\coffee\
  input\
  runs\<timestamp>-<label>\
    spec\
    build\
    verify\
    materials\
    nodes\
    logs\
    thumbs\
    brownfield\
```

BUILD:

- Update `project_workspace.default_project_root()` to use
  `VIDEO_PIPELINE_PROJECT_ROOT` when set.
- On Windows, default to `Desktop\video_project`.
- Keep repo-local `.project\active.json` as the active project/run pointer.

VERIFY:

```powershell
python video_tools.py project-init coffee
python video_tools.py project-new-run --label baseline
```

Confirm:

- Project exists under `C:\Users\user\Desktop\video_project\coffee`.
- Source tree remains free of run outputs.
- `.project\active.json` resolves correctly.
- `.project\active.json` stores portable `/` separators even when written on
  Windows.

Current W0 evidence:

```text
tests.test_project_workspace:
  test_init_project_creates_external_layout_and_active_pointer: fail
  expected ../projects, received ..\projects

  test_create_run_dir_updates_active_pointer: fail
  expected runs/..., received runs\...
```

First implementation task:

```text
Normalize serialized active-pointer paths to POSIX-style `/`.
Keep path resolution platform-native when reading the pointer.
Run tests.test_project_workspace on Windows before continuing to W1.
```

### W1: Add Cross-Platform Tool And Path Resolver

SPEC:

Centralize platform-dependent executable and path discovery.

BUILD:

Add:

```text
video_pipeline_core/platform_tools.py
```

Required interfaces:

```python
resolve_python()
resolve_ffmpeg()
resolve_ffprobe()
resolve_ytdlp()
resolve_ollama_url()
resolve_temp_dir()
resolve_font()
```

Resolution order:

```text
explicit environment variable
-> executable on PATH
-> platform-specific known location
-> clear ToolError with setup guidance
```

Expected environment variables:

```text
VIDEO_PIPELINE_PYTHON
FFMPEG_PATH
FFPROBE_PATH
YTDLP_PATH
OLLAMA_URL
VIDEO_PIPELINE_TEMP
VIDEO_PIPELINE_FONT
VIDEO_PIPELINE_PROJECT_ROOT
```

VERIFY:

- Unit tests mock Windows/Linux resolution.
- `python video_tools.py --help` still works without requiring every optional
  executable.
- Missing tools produce a clear error only when the related runner is invoked.

### W2: Remove Hardcoded WSL/Linux Paths

SPEC:

Runtime modules must consume `platform_tools.py`, not hardcoded `/home`,
`~/.local/bin`, `/tmp`, `python3`, or Linux font paths.

BUILD:

Prioritize:

```text
video_pipeline_core/vt_core.py
video_pipeline_core/mv_cut.py
video_pipeline.py
route.py
video_tools.py
video_pipeline_core/vt_effects.py
video_pipeline_core/vt_audio.py
video_pipeline_core/curator.py
```

Replace:

```text
"/home/lio730309/..."
"~/.local/bin/ffmpeg"
"~/.local/bin/ffprobe"
"~/.local/bin/yt-dlp"
"/tmp"
"python3"
Linux-only font lookup
```

with resolver calls or caller-provided paths.

VERIFY:

- Search Windows source for remaining active hardcoded Linux paths.
- Run focused module tests after each file migration.
- Compare JSON artifacts with the WSL reference for the same pure-input tests.

### W3: Replace Bash-Only Orchestration

SPEC:

Windows runtime must not require Bash for normal operation.

BUILD:

Add:

```text
run_with_ollama.py
```

It must:

```text
check OLLAMA_URL
-> start Ollama only when configured/needed
-> wait for /api/tags
-> optionally warm qwen3-vl:4b-instruct
-> execute the requested Python runner
-> preserve exit code and logs
-> stop only the process it started
```

Migrate Bash-generated temporary ffmpeg scripts in `video_tools.py` to direct
`subprocess.run([...])` argument lists.

Compatibility:

- Keep `run_with_ollama.sh` as WSL reference until Windows E2E passes.
- Windows route must prefer Python orchestration.

VERIFY:

- Unit tests for process-started vs existing-server behavior.
- Windows smoke against an already-running Ollama server.
- No normal Windows command invokes `bash`.

### W4: Verify Native External Tools

SPEC:

Confirm external tools independently before full E2E.

VERIFY:

```powershell
python --version
ffmpeg -version
ffprobe -version
yt-dlp --version
ollama list
```

Then run focused runtime smoke:

```powershell
python video_tools.py probe <sample-video>
python video_tools.py grade <sample-video> --preset neutral --out <output>
python video_tools.py pexels-search "coffee shop" --type video --limit 1
```

Each external tool must have:

- detected path;
- clear missing-tool message;
- focused test or reproducible smoke command.

### W5: Canonical Windows No-Effects E2E

SPEC:

The first true Windows E2E uses `no_effects`. Do not add motion graphics to this
milestone.

BUILD:

Create or reuse a small named project:

```text
C:\Users\user\Desktop\video_project\coffee
```

Run:

```powershell
python video_tools.py contract-run <segment_contract.json> `
  --categories <material_categories.json> `
  --material-db <materials_db.json> `
  --music <music.mp3> `
  --out C:\Users\user\Desktop\video_project\coffee\runs\<run>\final.mp4
```

VERIFY:

- `final.mp4` exists and is playable.
- `artifact_manifest.json` contains required keys.
- `state.json` has a valid next action.
- `assembly_plan.json`, `timeline_build.json`, and `editor_review.json` exist.
- Duration, resolution, and audio are mechanically verified.
- Compare artifact structure and route behavior with WSL reference.

### W6: Route, Dashboard, And Monitoring

SPEC:

Progress monitoring must operate against a named project/run under
`Desktop\video_project`.

BUILD:

- Ensure route/dashboard read active project/run pointers on Windows.
- Display node -> skill -> artifact -> status -> next_action.
- Keep dashboard read-first during migration.

VERIFY:

```powershell
python video_tools.py state <run-dir>
python video_tools.py dashboard <run-dir>
python video_tools.py story-map <run-dir>
```

Confirm the dashboard reflects manifest artifacts rather than inferred WSL
paths.

### W7: Rebuild Graphify On Windows

SPEC:

Graphify is rebuilt only after Windows source/runtime boundaries stabilize.

BUILD:

- Run Graphify against:

```text
C:\Users\user\Desktop\video_pipeline
```

- Exclude:

```text
.git
graphify-out
.project
__pycache__
media/output/project folders
```

VERIFY:

- Graphify root points to the Windows source.
- Report reflects `platform_tools.py`, Windows orchestration, and migration
  decisions.
- No Windows project media or outputs are indexed.
- No stale WSL-only path is presented as the current runtime architecture.

## Verification Ladder

Every agent must use the smallest relevant verification first:

```text
1. focused unit test for the changed boundary
2. related test module group
3. Windows CLI smoke
4. Windows full test suite
5. WSL comparison only when runtime semantics changed
6. true Windows E2E only at defined milestones
```

Recommended commands:

```powershell
python -m unittest tests.test_project_workspace -v
python -m unittest tests.test_contract_adapter tests.test_generated_assets tests.test_light_effects -v
python -m unittest discover -s tests -v
```

Do not claim a migration phase complete without fresh Windows verification
output.

## Compatibility And Rollback

- WSL is the behavioral reference during migration, not the active development
  target.
- Keep artifact schemas compatible so a Windows-produced artifact can still be
  inspected by existing route/dashboard logic.
- If a Windows portability change breaks runtime behavior, revert only that
  migration step; do not copy the entire WSL tree back over Windows.
- Record intentional Windows/WSL behavior differences in a decision log.

## Agent Handoff Checklist

Before an agent starts:

```text
1. Work only in C:\Users\user\Desktop\video_pipeline.
2. Read roadmap.md and this migration spec.
3. Identify the current W-phase.
4. Inspect the WSL reference only when needed.
5. Write a focused failing test before runtime changes.
6. Make one portability change.
7. Run focused Windows verification.
8. Update roadmap/spec status only after verification.
9. Do not rebuild Graphify until W7.
```

## Completion Criteria

Windows becomes the confirmed primary runtime when:

```text
project-init/new-run use Desktop\video_project
all active tool paths use platform resolver
normal runtime uses no Bash
external tools pass native smoke
canonical no-effects E2E passes
route/dashboard monitoring passes
full Windows test suite passes
Windows Graphify is rebuilt
```
