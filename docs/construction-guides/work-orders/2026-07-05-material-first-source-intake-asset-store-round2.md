# Material-First Source Intake Asset Store Round 2

Date: 2026-07-05

## Goal

Stabilize the material-first source-folder intake boundary so a user-provided
folder is treated as an intake source only. Accepted assets are copied into the
run/project asset store and canonical material artifacts use run-relative refs:

`assets/materials/<asset_id>.<ext>`

This round does not claim final delivery. It stops at boundary/build-ready
material-first acceptance and final review readiness.

## Commits

- `34e10904` Import accepted material-first assets into run asset store
- `aa8ff603` Probe real material source intake into asset store
- `9f81898c` Add material-first asset store replay checks
- `9e9ffa90` Register material-first review-ready next action

## Intake Contract

- External source folders are intake inputs, not canonical material truth.
- Accepted material-first assets are copied into `RUN_DIR/assets/materials/`.
- `materials_db.json`, `project_material_map.json`, `rough_cut_plan.json`, and
  `timeline_build.json` carry run-relative material refs after import.
- Original source identity is retained as metadata only: basename, hashed source
  path, content hash, and size where available.
- Rejected, corrupt, unsupported, duplicate, or bounded-out probe assets are not
  copied into the material asset store.
- Rejected/skipped source entries are sanitized to basename plus hash metadata so
  strict material/build asset path audit does not depend on external paths.

## Fixture And Acceptance

Golden fixture:

`tests/fixtures/material_first_golden/`

Official replay command:

```powershell
& "$env:USERPROFILE\miniconda3\python.exe" video_tools.py replay-acceptance --scenario material-first-golden-path --out .tmp\material_first_golden_replay.json
```

Expected replay result:

- `ok=true`
- `blocked=false`
- `next_action=ready_for_render_or_human_review`
- `metrics.asset_store_imported=true`
- `metrics.asset_path_audit_strict_ok=true`
- `metrics.asset_path_audit_strict_finding_count=0`
- artifacts include `.tmp/material_first_golden_path/run/assets/materials/real_0001.jpg`
  through `real_0003.jpg`
- `final.mp4` is absent by design

## Real Source Probe

Source probed:

`C:\Users\user\Downloads\微電影素材`

Probe output:

`.tmp/material_first_real_source_probe/intake_report.json`

Probe summary:

- `ok=true`
- `blocked=false`
- `next_action=ready_for_render_or_human_review`
- scanned files: 614
- supported media files: 604
- selected for bounded probe: 12
- accepted/copied to asset store: 3
- probe-rejected: 9
- corrupt or unreadable: 0
- edited-video-like files detected by name/path heuristic: 88
- strict asset path audit: `ok=true`, strict findings `0`

The probe wall verdict is deterministic and marked probe-only. It validates
source-intake mechanics, asset-store copying, artifact handoff, and path
discipline; it is not a human final material review.

## Mini Cold-Run

Round count: 1

Result: pass.

Mini ran:

```powershell
& "$env:USERPROFILE\miniconda3\python.exe" video_tools.py replay-acceptance --scenario material-first-golden-path --out .tmp\mini_material_first_golden_replay.json
```

Mini observed:

- `ok=true`
- `blocked=false`
- `next_action=ready_for_render_or_human_review`
- `asset_store_imported=true`
- `asset_path_audit_strict_ok=true`
- strict findings: 0
- real source probe report exists and parses with Python UTF-8

Weak note: default PowerShell display may show mojibake for Chinese source
basename in JSON output. Python UTF-8 parsing is correct.

## Validation

Focused material-first suite:

```powershell
& "$env:USERPROFILE\miniconda3\python.exe" -m unittest tests.test_material_first_real_source_probe tests.test_material_first_source_intake tests.test_material_first_landing_case tests.test_material_first_boundary_acceptance tests.test_material_first_golden_path -v
```

Result: `Ran 22 tests ... OK`

Golden replay:

```powershell
& "$env:USERPROFILE\miniconda3\python.exe" video_tools.py replay-acceptance --scenario material-first-golden-path --out .tmp\material_first_golden_replay.json
```

Result: exit 0, report `ok=true`

Strict asset path audit:

```powershell
& "$env:USERPROFILE\miniconda3\python.exe" video_tools.py asset-path-audit .tmp\material_first_golden_path\run --strict --json
```

Result: `ok=true`, strict findings `0`

Interface audit:

```powershell
& "$env:USERPROFILE\miniconda3\python.exe" video_tools.py interface-audit
```

Result: `ok=true`

Acceptance contract:

```powershell
& "$env:USERPROFILE\miniconda3\python.exe" video_tools.py acceptance-contract --out .tmp\material_first_acceptance_contract.json
```

Result: exit 0

Registry audit:

```powershell
& "$env:USERPROFILE\miniconda3\python.exe" video_tools.py registry-audit
```

Result: `Registry Audit: OK (7 branches, 14 stages)`

Work-order tier dry run:

```powershell
& "$env:USERPROFILE\miniconda3\python.exe" video_tools.py test-tiers --tier work-order-acceptance --dry-run
```

Result: `ok=true`, command count 4

Full suite:

```powershell
& "$env:USERPROFILE\miniconda3\python.exe" -m unittest discover -s tests
```

Result: `Ran 2410 tests ... OK`

## Deferred

- Final render and `final.mp4` delivery acceptance.
- Complete-video delivery gate promotion.
- Human material-wall review UX.
- Workbench/Dashboard UI changes.
- Stock semantic-fit implementation.
- Provider/network retrieval behavior.
- Generated storybook route work.
- Large historical run migration.

## Next Recommended Work Order

Title: Material-First Human Review And Render Promotion Gate

Scope:

- Add a human-reviewed material wall verdict path for real source folders.
- Promote build-ready material-first artifacts into an explicit render handoff.
- Keep delivery blocked until complete-video and delivery gate evidence exists.
- Preserve `assets/materials/` refs through render input manifests.
