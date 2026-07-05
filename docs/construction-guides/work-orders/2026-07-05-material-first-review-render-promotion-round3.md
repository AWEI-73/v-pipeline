# Material-First Review Render Promotion Round 3

Date: 2026-07-05

## Goal

Extend the material-first golden path from source intake and boundary readiness
into an explicit human/agent review and render promotion gate:

```text
source intake
  -> RUN_DIR/assets/materials/
  -> material_review_packet.json
  -> material_wall_review_verdict.json
  -> material map / delta / rough timeline
  -> render_readiness_report.json
  -> render_handoff.json
  -> ready_for_render or blocked
```

This round does not render `final.mp4` and does not claim final delivery.

## Commits

- `996578b3` Add material-first review packet
- `bacbd4e1` Accept material-first review verdict for promotion
- `2fbc875b` Add material-first render promotion gate
- `01180b87` Extend material-first replay through render promotion

## Official Acceptance Command

```powershell
& "$env:USERPROFILE\miniconda3\python.exe" video_tools.py replay-acceptance --scenario material-first-golden-path --out .tmp\material_first_golden_replay.json
```

Latest replay result:

- `ok=true`
- `blocked=false`
- `next_action=ready_for_render`
- `metrics.review_packet_written=true`
- `metrics.review_verdict_accepted=true`
- `metrics.render_readiness_ok=true`
- `metrics.render_handoff_written=true`
- `metrics.final_mp4_absent=true`

## Produced Artifacts

Golden replay produces these Round 3 artifacts:

- `.tmp/material_first_golden_path/run/material_review_packet.json`
- `.tmp/material_first_golden_path/run/material_first_review_verdict_acceptance.json`
- `.tmp/material_first_golden_path/run/render_readiness_report.json`
- `.tmp/material_first_golden_path/run/render_handoff.json`

Render readiness:

- `ok=true`
- `next_action=ready_for_render`
- `final_delivery_claimed=false`
- strict asset path audit: `ok=true`, strict findings `0`

Render handoff:

- `ok=true`
- `next_action=ready_for_render`
- `final_delivery_claimed=false`
- timeline refs point at `assets/materials/real_0001.jpg` through
  `assets/materials/real_0003.jpg`

## Design Notes

`material_review_packet.json` is the handoff surface for a human or agent. It
lists accepted candidate assets, run-relative asset refs, role hints, visual
evidence, basename/hash source metadata, rejected/skipped material summary, and
instructions for writing `material_wall_review_verdict.json`.

`material_first_review_verdict_acceptance.json` records whether the supplied
verdict covers review packet assets and is acceptable for render promotion. It
fails closed when a required reviewed asset has no decision or when a verdict
references unknown assets.

`render_readiness_report.json` is the promotion gate. It checks material delta,
timeline, review verdict acceptance, strict asset-path audit, and asset-store
file presence. On success it writes `render_handoff.json`; on failure it reports
`next_action=blocked` and does not leave a stale handoff.

## Mini Cold-Run

Round count: 1

Result: pass with weak doc note.

Mini command:

```powershell
& "$env:USERPROFILE\miniconda3\python.exe" video_tools.py replay-acceptance --scenario material-first-golden-path --out .tmp\mini_round3_material_first_golden_replay.json
```

Mini observed:

- `ok=true`
- `blocked=false`
- `next_action=ready_for_render`
- review packet, verdict acceptance, render readiness, and render handoff are present
- `assets/materials/` refs are present
- `.tmp/material_first_golden_path/run/final.mp4` is absent
- `final_delivery_claimed=false` in render readiness and handoff

Weak note: the Round 2 work order still documents the older replay top-level
`next_action=ready_for_render_or_human_review`. The nested boundary acceptance
check still reports that value, but Round 3 promotion intentionally advances the
top-level replay to `ready_for_render`.

## Validation

Focused material-first suite:

```powershell
& "$env:USERPROFILE\miniconda3\python.exe" -m unittest tests.test_material_first_review_promotion tests.test_material_first_golden_path tests.test_material_first_source_intake tests.test_material_first_boundary_acceptance tests.test_material_first_landing_case tests.test_material_first_real_source_probe -v
```

Result: `Ran 27 tests ... OK`

Golden replay:

```powershell
& "$env:USERPROFILE\miniconda3\python.exe" video_tools.py replay-acceptance --scenario material-first-golden-path --out .tmp\material_first_golden_replay.json
```

Result: exit 0, report `ok=true`, `next_action=ready_for_render`

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
& "$env:USERPROFILE\miniconda3\python.exe" video_tools.py acceptance-contract --out .tmp\material_first_round3_acceptance_contract.json
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

Result: `Ran 2415 tests ... OK`

## Blocked / Deferred

No blocker remains for this round's success criteria.

Deferred:

- final render and `final.mp4` delivery acceptance
- complete-video delivery gate promotion
- Dashboard/Workbench UI
- stock semantic-fit implementation
- provider/network behavior
- generated storybook route work
- large historical run migration

## Next Recommended Work Order

Title: Material-First Render Execution And Complete-Video Delivery Gate

Scope:

- consume `render_handoff.json` through the existing render/build route
- produce a render candidate without treating it as delivery
- require complete-video validation before final promotion
- preserve `assets/materials/` refs through render input manifests and reports
