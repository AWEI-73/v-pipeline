# Render Readiness Asset Audit Scope Report

Date: 2026-07-05

## Summary

- Real-material rerun root: `.tmp/render_readiness_asset_audit_scope_20260705-235822`
- Real-material flow run: `.tmp/render_readiness_asset_audit_scope_20260705-235822/flow`
- Render readiness: `ok=true`
- `render_handoff.json` exists: `true`
- `final.mp4` created: `false`
- Non-render-critical absolute path warning count: `440`

The fix narrows render promotion blocking to render-critical refs while keeping
absolute provenance/evidence path findings visible in
`render_readiness_report.json`. A review fix added `rough_cut_plan.json` clips
to the same hard render-critical ref validation as `timeline_build.json`.

## Files Changed

- `video_pipeline_core/material_first_review_promotion.py`
- `tests/test_material_first_review_promotion.py`
- `docs/construction-guides/work-orders/2026-07-05-render-readiness-asset-audit-scope-report.md`

`video_pipeline_core/asset_paths.py` did not require changes.

## Behavior

- Render-critical refs are still checked by `_asset_ref_blocks()`:
  `materials_db.files[].asset_store_ref`, `timeline_build.clips[].source_path`,
  `rough_cut_plan.clips[].source_path`, and copied asset files must be
  run-local under `assets/materials/...` and exist.
- Broad asset path audit findings are preserved as warnings:
  `asset_path_warning_summary.finding_count` and `warnings[]`.
- `render_handoff.json` is written only when render-critical checks pass.

## Commands

### Target Unit Test

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_material_first_review_promotion
```

Red-first result for the review-fix rough cut regression: exit code `1`.

Command:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_material_first_review_promotion.MaterialFirstReviewPromotionTest.test_render_promotion_blocks_external_absolute_rough_cut_source_path
```

Failure tail:

```text
FAIL: test_render_promotion_blocks_external_absolute_rough_cut_source_path
AssertionError: True is not false
report ok=true; next_action=ready_for_render
```

Single regression test after fix exit code: `0`.

Full target test after fix exit code: `0`.

Stdout tail:

```text
Ran 9 tests in 2.736s

OK
```

### Pinned Material-First Acceptance

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_material_first_review_promotion tests.test_material_first_golden_path tests.test_material_first_source_intake tests.test_material_first_boundary_acceptance tests.test_material_first_landing_case tests.test_material_first_real_source_probe
```

Exit code: `0`.

Stdout tail:

```text
Ran 31 tests in 8.520s

OK
```

### Real-Material No-Render Rerun

The latest rerun copied `.tmp/real_material_e2e_probe_20260705-220325/happy_path` into
`.tmp/render_readiness_asset_audit_scope_20260705-235822/flow`, then built the
review packet, accepted the draft verdict as a probe decision, and ran render
readiness. It did not render.

Exit code: `0`.

Stdout tail:

```json
{
  "accepted_candidate_assets": 3,
  "acceptance_ok": true,
  "readiness_ok": true,
  "readiness_next_action": "ready_for_render",
  "blocking": [],
  "warning_count": 440,
  "render_handoff_exists": true,
  "handoff_ok": true,
  "timeline_ref_count": 3,
  "bad_refs": [],
  "final_mp4_exists": false
}
```

Stderr tail: empty.

## Real-Material Result

- `material_first_review_verdict_acceptance.json`: `ok=true`
- `render_readiness_report.json`: `ok=true`
- `render_handoff.json`: exists and `ok=true`
- timeline ref count: `3`
- bad timeline refs: `[]`
- `final.mp4`: absent
- warning/summary count: `440`

## Review Fix Coverage

- Red-first rough cut regression:
  `test_render_promotion_blocks_external_absolute_rough_cut_source_path`
  initially failed because an external absolute
  `rough_cut_plan.clips[0].source_path` still produced `ok=true` and wrote a
  handoff.
- The fix extends render-critical validation to include rough cut clip refs.
- Existing guarantees remained covered:
  non-render-critical provenance/evidence absolute paths stay warnings,
  external timeline refs still block, and missing copied asset files still
  block.

## Deviations

None. No render was run, `render_material_first_handoff` was not called, the
delivery gate was not run, and previous real-material `.tmp` folders were not
mutated in place.
