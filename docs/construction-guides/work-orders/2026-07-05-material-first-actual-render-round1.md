# Material-First Actual Render Execution Round 1

Date: 2026-07-05
Status: ready for implementation worker

## Goal

Move the deterministic material-first golden path from:

```text
render_handoff.json -> ready_for_render -> final_mp4_absent=true
```

to:

```text
render_handoff.json
  -> actual render
  -> run-local final.mp4
  -> ffprobe-backed final artifact acceptance
  -> ready_for_delivery_gate
```

This round is not complete-video delivery. Do not claim complete-video delivery
unless the existing complete-video gate actually passes with its required
artifacts.

## Current Baseline

Repo baseline before this round:

- `HEAD`: `88a69af2 Add material-first happy path runbook`
- `docs/runbooks/material-first-happy-path.md` records the route state.
- Official replay currently exits 0 with:
  - `ok=true`
  - `blocked=false`
  - `next_action=ready_for_render`
  - `metrics.final_mp4_absent=true`
  - `render_handoff.json` present
  - `final.mp4` absent

Official baseline command:

```powershell
& "$env:USERPROFILE\miniconda3\python.exe" video_tools.py replay-acceptance --scenario material-first-golden-path --out .tmp\material_first_golden_replay.json
```

## Owner Zone

The worker may edit only:

- `video_pipeline_core/material_first_golden_path.py`
- `video_pipeline_core/material_first_review_promotion.py`
- a new focused material-first render helper under `video_pipeline_core/` or
  `tools/`
- `video_tools.py` only if a command entry is required
- `tests/test_material_first_golden_path.py`
- `tests/test_material_first_review_promotion.py`
- a new focused material-first render test if needed
- `docs/runbooks/material-first-happy-path.md` only if verified state text must
  be updated after implementation
- this work-order file only for appending the worker report

## Forbidden Zone

Do not edit:

- Dashboard/Workbench UI
- provider/network code
- stock semantic-fit
- generated storybook route
- historical run migration
- broad route/runtime refactors
- complete-video delivery requirements
- unrelated failing tests or gates

Do not weaken existing gates/tests to pass this round.

## Ordered Outcomes

1. Red-first coverage exists for the current gap:
   `render_handoff.json` is present and valid, but `final.mp4` is absent. The
   coverage defines the desired final evidence: `final_mp4_absent=false`,
   `final_mp4_ref`, and ffprobe stream evidence.

2. Render execution reads render input from `render_handoff.json`; it does not
   reselect material and does not use original external source paths.

3. The render writes run-local `final.mp4` and a small run-local JSON report for
   final artifact acceptance. ffprobe evidence must prove at least one video
   stream.

4. `material-first-golden-path` replay reports:
   - `ok=true`
   - `blocked=false`
   - `final_mp4_absent=false`
   - `final_mp4_ref` points to run-local `final.mp4`
   - ffprobe stream evidence is present
   - `next_action=ready_for_delivery_gate` or the existing repo-equivalent
     delivery-gate-ready state

5. `final_delivery_claimed` remains `false` unless the existing complete-video
   validation actually passes. This round is expected to keep it `false`.

## Bounded Internal Repair Loop

The worker may run up to 3 total implementation/fix iterations.

Each iteration is:

```text
implement/fix
-> focused tests
-> material-first replay
-> ffprobe final.mp4
-> asset-path-audit strict
-> inspect replay/report metrics
-> decide next fix or stop
```

Stop and report if:

- the loop reaches 3 iterations and acceptance still fails
- the same failure class appears twice after attempted fixes
- more than 8 core files would need edits
- more than 4 commits would be needed
- actual render requires architecture rewrite beyond deterministic fixture render
- a fix would cross forbidden zones
- a broad/full-suite failure appears unrelated to this round
- complete-video delivery artifacts become required beyond this round's scope

## Acceptance Commands

Run from `C:\Users\user\Desktop\video_pipeline`.

```powershell
& "$env:USERPROFILE\miniconda3\python.exe" -m unittest tests.test_material_first_golden_path tests.test_material_first_review_promotion -v
```

```powershell
& "$env:USERPROFILE\miniconda3\python.exe" video_tools.py replay-acceptance --scenario material-first-golden-path --out .tmp\material_first_golden_replay.json
```

```powershell
& "$env:USERPROFILE\miniconda3\python.exe" video_tools.py interface-audit --out .tmp\material_first_interface_audit.json
```

```powershell
& "$env:USERPROFILE\miniconda3\python.exe" video_tools.py acceptance-contract --out .tmp\material_first_acceptance_contract.json
```

```powershell
& "$env:USERPROFILE\miniconda3\python.exe" video_tools.py registry-audit --json
```

```powershell
& "$env:USERPROFILE\miniconda3\python.exe" video_tools.py asset-path-audit .tmp\material_first_golden_path\run --strict --json
```

```powershell
& "$env:USERPROFILE\miniconda3\Library\bin\ffprobe.exe" -v error -show_entries stream=codec_type,codec_name,width,height,duration -of json .tmp\material_first_golden_path\run\final.mp4
```

## Commit Guidance

Use at most 4 commits. Suggested sequence:

1. `Add red coverage for material-first final render gap`
2. `Render material-first handoff to final mp4`
3. `Extend material-first replay final artifact acceptance`
4. `Record material-first actual render state`

## Delegated Decisions

- Whether the focused helper lives under `video_pipeline_core/` or `tools/`.
- Exact artifact/report name for the final artifact acceptance JSON.
- Whether the deterministic fixture render is video-only or includes audio,
  provided existing touched gates are not weakened and complete-video scope is
  not opened.

## Worker Report

Append a report here with:

- commits
- files changed
- loop count
- each loop failure summary and fix summary
- final acceptance command exit codes
- final replay metrics: `ok`, `blocked`, `next_action`,
  `final_mp4_absent`, `final_mp4_ref`
- ffprobe stream evidence
- asset-path-audit strict result
- whether `final_delivery_claimed` remains `false`
- deviations, skips, blockers
- `git status --short`

### 2026-07-05 Worker Report

Commits:

- `a7861f9e` Render material-first handoff to final mp4
- report commit: `Record material-first actual render state`

Files changed:

- `video_pipeline_core/material_first_render.py` - new deterministic
  material-first render helper. It reads `render_handoff.json`, requires
  run-local `assets/materials/...` refs, renders `final.mp4`, probes it with
  ffprobe, and writes `material_first_final_artifact_acceptance.json`.
- `video_pipeline_core/material_first_golden_path.py` - replay now executes the
  render handoff and reports final artifact acceptance metrics.
- `tests/test_material_first_golden_path.py` - red-first replay coverage for
  `ready_for_delivery_gate`, `final_mp4_absent=false`, `final_mp4_ref`, and
  ffprobe stream evidence.
- `tests/test_material_first_review_promotion.py` - focused helper coverage
  proving render execution uses run-local handoff refs and does not leak the
  external source directory.
- `docs/runbooks/material-first-happy-path.md` - updated verified route state:
  actual render is now covered, complete-video delivery is still deferred.
- `docs/construction-guides/work-orders/2026-07-05-material-first-actual-render-round1.md`
  - this worker report.

Loop count:

- 1 implementation loop.

Loop failure and fix summary:

- Red run failed as expected:
  - `ModuleNotFoundError: No module named 'video_pipeline_core.material_first_render'`
  - replay still reported `final_mp4_absent=true`
  - replay still ended at `ready_for_render`
- Fix:
  - added `render_material_first_handoff`
  - wired the golden replay through actual render
  - updated replay metrics and route runbook state
- Focused rerun initially found one stale test expectation
  (`ready_for_render` vs `ready_for_delivery_gate`); corrected the test to the
  work-order outcome and reran green.

Final acceptance command exit codes and tails:

- `& "$env:USERPROFILE\miniconda3\python.exe" -m unittest tests.test_material_first_golden_path tests.test_material_first_review_promotion -v`
  - exit code 0
  - tail: `Ran 8 tests in 5.265s` / `OK`
- `& "$env:USERPROFILE\miniconda3\python.exe" video_tools.py replay-acceptance --scenario material-first-golden-path --out .tmp\material_first_golden_replay.json`
  - exit code 0
  - tail metrics: `ok=true`, `blocked=false`,
    `next_action=ready_for_delivery_gate`
- `& "$env:USERPROFILE\miniconda3\python.exe" video_tools.py interface-audit --out .tmp\material_first_interface_audit.json`
  - exit code 0
  - output file: `.tmp\material_first_interface_audit.json`
  - parsed result: `ok=true`
- `& "$env:USERPROFILE\miniconda3\python.exe" video_tools.py acceptance-contract --out .tmp\material_first_acceptance_contract.json`
  - exit code 0
  - output file: `.tmp\material_first_acceptance_contract.json`
  - parsed result: `ok=true`
- `& "$env:USERPROFILE\miniconda3\python.exe" video_tools.py registry-audit --json`
  - exit code 0
  - tail: `ok=true`, `finding_count=0`
- `& "$env:USERPROFILE\miniconda3\python.exe" video_tools.py asset-path-audit .tmp\material_first_golden_path\run --strict --json`
  - exit code 0
  - tail: `ok=true`, `strict_finding_count=0`
- `& "$env:USERPROFILE\miniconda3\Library\bin\ffprobe.exe" -v error -show_entries stream=codec_type,codec_name,width,height,duration -of json .tmp\material_first_golden_path\run\final.mp4`
  - exit code 0
  - stream evidence: `codec_type=video`, `codec_name=h264`, `width=320`,
    `height=180`, `duration=12.000000`

Final replay metrics:

- `ok=true`
- `blocked=false`
- `next_action=ready_for_delivery_gate`
- `final_mp4_absent=false`
- `final_mp4_ref=final.mp4`
- `final_artifact_acceptance_ok=true`
- `ffprobe_video_stream_count=1`
- `asset_path_audit_strict_ok=true`
- `asset_path_audit_strict_finding_count=0`
- `final_delivery_claimed=false`

Final artifact acceptance:

- report: `.tmp\material_first_golden_path\run\material_first_final_artifact_acceptance.json`
- `ok=true`
- `next_action=ready_for_delivery_gate`
- `final_mp4_ref=final.mp4`
- input refs:
  - `assets/materials/real_0001.jpg`
  - `assets/materials/real_0002.jpg`
  - `assets/materials/real_0003.jpg`

Asset-path-audit strict result:

- `ok=true`
- `strict_finding_count=0`
- non-strict findings remain in `other` family from existing boundary reports;
  they did not block strict material/build/effect/audio acceptance.

Delivery claim:

- `final_delivery_claimed=false`
- Complete-video delivery was not claimed. The render is video-only and stops
  at `ready_for_delivery_gate`.

Deviations, skips, blockers:

- No stop-loss condition triggered.
- The deterministic actual render is video-only, as allowed by the delegated
  decision in this work order.
- Complete-video audio, narration, music, and subtitle gate inputs remain
  deferred.
- The work-order file was untracked in the starting workspace; this report
  commit adds it as the requested report target.

`git status --short`:

- Before this report commit: `?? docs/construction-guides/work-orders/2026-07-05-material-first-actual-render-round1.md`
- Expected after report commit: clean.
