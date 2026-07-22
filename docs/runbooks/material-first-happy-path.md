# Material-First Happy Path Runbook

Date: 2026-07-05
Status: validation fixture verified through actual render; not a user-job route

This is a validation-only golden fixture, not a user-job entry. Use it to test
the deterministic material-first machinery with tracked fixture inputs. For a
real user material folder, start from `RUNBOOK.md` and
`skills/video-pipeline-route.md`; do not substitute this replay command for the
operator route.

## Current Verified Path

The replay acceptance currently verifies this path:

```text
source intake
  -> asset store import
  -> project_material_map.json
  -> material_delta.json
  -> review packet
  -> verdict acceptance
  -> render_handoff.json
  -> actual render
  -> run-local final.mp4
  -> ffprobe-backed final artifact acceptance
  -> ready_for_delivery_gate
```

The `actual render` and `final.mp4` below belong only to the generated fixture
run. They prove render mechanics; they do not authorize a real user job to skip
Stage 0, material review, `render_handoff.json`, Verify, or owner delivery gates.

This means the route has accepted source material into the run-local asset
store, produced a material map and delta, created a review packet, accepted the
review verdict, written `render_handoff.json`, rendered a run-local
`final.mp4`, and captured ffprobe-backed video-stream evidence.

It does not mean complete-video delivery has passed. The current expected replay
state is:

```text
ok=true
blocked=false
next_action=ready_for_delivery_gate
final_mp4_absent=false
final_mp4_ref=final.mp4
```

## Validation Replay Command

Run from `C:\Users\user\Desktop\video_pipeline`:

```powershell
& "$env:USERPROFILE\miniconda3\python.exe" video_tools.py replay-acceptance --scenario material-first-golden-path --out .tmp\material_first_golden_replay.json
```

The replay uses the tracked fixture recipe at
`tests/fixtures/material_first_golden/fixture_manifest.json` and generates tiny
runtime media under `.tmp\material_first_golden_path\`. It does not depend on a
user's old run folder or external providers.

Expected key artifacts are written under the generated run directory, including:

- `project_material_map.json`
- `material_delta.json`
- `material_review_packet.json`
- `material_first_review_verdict_acceptance.json`
- `render_readiness_report.json`
- `render_handoff.json`
- `final.mp4`
- `material_first_final_artifact_acceptance.json`

## Next Construction Path

The next construction topic is:

```text
Material-First Delivery Gate Completion Round 1
```

That round should start from the current final artifact acceptance and build
this path:

```text
ready_for_delivery_gate
  -> complete-video delivery gate inputs
  -> audio / narration / music / subtitle requirements verified
  -> delivery accepted or blocked
```

The delivery round must provide the complete-video requirements that this actual
render round intentionally did not claim.

## Later Delivery Gate Path

Complete-video delivery remains a later path:

```text
ready_for_delivery_gate
  -> complete-video delivery gate
  -> audio / narration / music / subtitle requirements verified
  -> delivery accepted or blocked
```

Do not treat `ready_for_render`, `render_handoff.json`, a draft render, or a
plain `final.mp4` file as complete delivery. Complete-video acceptance still
requires the delivery gate to verify the required audio, narration, music,
subtitles, and media-stream evidence.

## Operator Boundaries

- Use the exact source directory supplied by the operator or the tracked golden
  replay fixture. Do not substitute a neighboring folder.
- If source material is missing, stop with `blocked` or `needs-context` instead
  of selecting replacement media.
- If the replay reports `next_action=ready_for_delivery_gate`, hand off to the
  complete-video delivery gate path. Do not claim final delivery.
- If `final_mp4_absent=true`, the actual render path regressed; inspect
  `render_handoff.json` and `material_first_final_artifact_acceptance.json`.
