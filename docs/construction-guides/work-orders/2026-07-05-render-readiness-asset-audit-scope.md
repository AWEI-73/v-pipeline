# Work Order: Render Readiness Asset Audit Scope

Date: 2026-07-05
Status: ready for construction

## Background

The real-material no-render decision flow accepted the material wall draft
verdict but could not produce `render_handoff.json`:

- Flow run: `.tmp/real_material_no_render_flow_20260705-230801/flow`
- `material_first_review_verdict_acceptance.json`: `ok=true`
- `render_readiness_report.json`: `ok=false`
- Block: `asset_path_audit_failed`
- `strict_finding_count`: `434`

Integrator review found that `timeline_build.json` and `rough_cut_plan.json`
use run-local `assets/materials/...` refs. The strict findings mostly come from
source-candidate, material-understanding, draft verdict, review packet, and
report artifacts that preserve provenance or previous-run evidence paths.

This means render readiness is using an audit scope that is too broad for the
render promotion decision.

## Goal

Change material-first render promotion so it hard-blocks only render-critical
asset refs, while preserving non-critical absolute/provenance/evidence path
findings as warnings in `render_readiness_report.json`.

## Desired State

For the real-material copied flow, `build_material_first_render_promotion()`
should produce:

- `render_readiness_report.json` with `ok=true`;
- `render_handoff.json`;
- warnings that summarize non-render-critical absolute path findings;
- no `final.mp4`.

Render-critical refs must still fail closed when they are external, absolute, or
missing.

## Non-Goals

- Do not render.
- Do not call `render_material_first_handoff`.
- Do not run delivery gate.
- Do not edit or clean existing `.tmp` probe/flow folders as the fix.
- Do not delete provenance paths from source-candidate or review evidence
  artifacts merely to pass the gate.
- Do not weaken hard checks for `timeline_build.json`, `rough_cut_plan.json`,
  `materials_db.files[].asset_store_ref`, or copied asset files.

## Owner Zone

The worker may edit only:

- `video_pipeline_core/asset_paths.py`
- `video_pipeline_core/material_first_review_promotion.py`
- `tests/test_material_first_review_promotion.py`
- `docs/construction-guides/work-orders/2026-07-05-render-readiness-asset-audit-scope-report.md`

The worker may create temporary run folders under `.tmp/render_readiness_asset_audit_scope_*/`.

## Forbidden Zone

These paths are read-only:

- `C:/Users/user/Downloads/`
- `.tmp/real_material_e2e_probe_20260705-220325/`
- `.tmp/real_material_no_render_flow_20260705-230801/`
- `video_pipeline_core/material_first_render.py`
- `tools/`
- `tests/` except `tests/test_material_first_review_promotion.py`
- `skills/`
- `runs/`
- `examples/`

## Required Behavior

Render promotion should distinguish:

- **Hard render inputs:** `timeline_build.json`, `rough_cut_plan.json`,
  `materials_db.json` active files, and copied asset store files. These must use
  run-local refs under `assets/materials/...` and must exist.
- **Audit/provenance evidence:** source candidates, material understanding
  matrix, draft verdict evidence, review packet source metadata, and reports.
  Absolute paths here should be listed as warnings/portability findings, but
  must not block `render_handoff.json`.

The existing `_asset_ref_blocks()` hard checks must remain or become stronger.
Do not rely only on a broad audit warning to prove render safety.

## Required Tests

Add red-first coverage in `tests/test_material_first_review_promotion.py`:

1. A run with accepted review verdict, ready material delta, run-local timeline
   refs, and absolute provenance/evidence paths in non-render-critical material
   artifacts produces `render_readiness_report.ok=true` and writes
   `render_handoff.json`.
2. The same report includes warnings or a summary for the non-critical absolute
   path findings.
3. A timeline clip with an external absolute `source_path` still blocks render
   promotion.
4. A missing copied asset store file still blocks render promotion.

## Acceptance Commands

Run from `C:/Users/user/Desktop/video_pipeline`:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_material_first_review_promotion
```

Expected: exit code 0.

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_material_first_review_promotion tests.test_material_first_golden_path tests.test_material_first_source_intake tests.test_material_first_boundary_acceptance tests.test_material_first_landing_case tests.test_material_first_real_source_probe
```

Expected: exit code 0.

Then rerun the no-render flow on a fresh copy of the real-material probe folder
or a temporary equivalent under `.tmp/render_readiness_asset_audit_scope_*/`.
Expected:

- `material_first_review_verdict_acceptance.json` is `ok=true`;
- `render_readiness_report.json` is `ok=true`;
- `render_handoff.json` exists;
- `final.mp4` does not exist;
- report contains warning/summary count for non-critical absolute path findings.

## Stop-Loss Limits

Stop and report before continuing if:

- Fix requires editing outside owner zone.
- A test requires rendering or ffmpeg.
- The only way to pass is deleting provenance/evidence paths.
- Timeline/material render refs become less strict.
- Real-material no-render rerun creates `final.mp4`.

## Delegated Decisions

The worker may decide:

- Whether to implement the narrowed audit as a new helper in `asset_paths.py` or
  local logic in `material_first_review_promotion.py`.
- Exact field names for warning summaries, as long as they are machine-readable
  and visible in `render_readiness_report.json`.
- Fixture shape for tests.

The worker must not decide:

- To render.
- To hand-edit `.tmp` run artifacts as the fix.
- To downgrade render-critical timeline/material refs from hard block to
  warning.

## Final Report Requirements

The worker's final message must include:

- Files changed.
- Tests run with exit codes.
- Real-material no-render rerun path and result.
- Whether `render_handoff.json` exists.
- Confirmation that `final.mp4` was not created.
- Warning/summary count for non-critical absolute path findings.
- Any deviations from this work order.
