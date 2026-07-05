# Material-First Happy Path Runbook

Date: 2026-07-05
Status: verified through render handoff; not final delivery

Use this runbook when a user provides a material folder and the route should
stabilize material truth before any render work. This is the current
operator-level happy path for the deterministic material-first golden fixture.

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
  -> ready_for_render
```

This means the route has accepted source material into the run-local asset
store, produced a material map and delta, created a review packet, accepted the
review verdict, and written `render_handoff.json` for the next owner.

It does not mean a final video exists. The current expected replay state is:

```text
ok=true
blocked=false
next_action=ready_for_render
final_mp4_absent=true
```

## Official Replay Command

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

## Next Construction Path

The next construction topic is:

```text
Material-First Actual Render Execution Round 1
```

That round should start from the current handoff and build this path:

```text
render_handoff.json
  -> actual render
  -> run-local final.mp4
  -> ffprobe-backed final artifact acceptance
  -> ready_for_delivery_gate
```

The render round must prove `final.mp4` exists in the run folder and is a
playable media artifact with the expected streams before it can move to
`ready_for_delivery_gate`.

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
- If the replay reports `next_action=ready_for_render`, hand off to the actual
  render construction path. Do not claim final delivery.
- If `final_mp4_absent=false` appears before the actual render round owns it,
  inspect why a render artifact exists and verify it before promotion.
