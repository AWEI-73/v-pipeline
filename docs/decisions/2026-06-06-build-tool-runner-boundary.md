# Decision: BUILD Tool Runner Boundary

Date: 2026-06-06
Status: accepted
Scope: BUILD layer / runner tooling
Superpowers phase: brainstorm

## SPEC

Requirement:
Make the BUILD flow executable by agents without forcing them to infer tool
choices from prompts or legacy runtime details.

Why:
The project now has a strong canonical SPEC surface, but BUILD still mixes three
different concepts: provider policy, work requests, and actual runners. Without
an explicit boundary, future agents may treat `generated_mv_script.json` as SPEC,
call the wrong provider, or add tool behavior directly into prompts.

Direction:
Split BUILD into policy artifacts, request artifacts, and runners. Keep
`roadmap.md` as the strategic source and use `docs/build-tool-runner-spec.md` as
the concrete runner handoff.

Non-goals:
Do not implement provider clients in this decision. Do not make
`segment_contract.json` provider-specific. Do not re-enable ComfyUI as an active
default provider.

## DO

Files / modules:

- `roadmap.md`: record BUILD runner strengthening and priority order.
- `docs/build-tool-runner-spec.md`: define runner contracts, artifacts, and
  verification.
- `HANDOFF_CURRENT.md`: add the new spec to the resume path.

Function-level plan:

- No runtime function changes in this decision.
- Future implementation should focus on `contract_adapter.run_contract`,
  `generated_assets.py`, `motion_graphics.py`, `dashboard_state.py`, and
  `video_tools.py`.

Data / interface changes:

- Policy artifacts: `build_profile.json`, `model_routes.json`.
- Request artifacts: `generated_asset_requests.json`,
  `motion_graphics_render_plan.json`, `assembly_plan.json`,
  `timeline_build.json`.
- Runner outputs must appear in `artifact_manifest.json`.

Migration / compatibility:

Legacy `generated_mv_script.json` remains runtime payload only. Existing
`mv_cut` behavior stays compatible while canonical runners mature.

## VERIFY

Pre-checks:

- Confirm current canonical CLI exists: `video_tools.py contract-adapt` and
  `video_tools.py contract-run`.
- Confirm BUILD modules exist under `video_pipeline_core/`.

Tests:

- Documentation-only decision; no new code tests required.
- Existing baseline should remain:
  `python3 -m unittest discover -s tests -v`.

Manual checks:

- Read `roadmap.md` and confirm the next priority is runner execution, not SPEC
  expansion.
- Read `docs/build-tool-runner-spec.md` and confirm an agent can identify
  input/output artifacts for each runner.

Regression risks:

- Agents may still over-index on old `script.json` docs.
- Motion graphics may be overbuilt before light effects and generated manifest
  plumbing are stable.

## Decision Notes

Accepted because:
This keeps the current MVP runnable while making future BUILD work concrete,
testable, and agent-friendly.

Tradeoffs:
Adds one more doc, but prevents `roadmap.md` from becoming a施工手冊 and gives
Graphify a precise retrieval anchor.

Open questions:

- Whether generated provider runners should be fully automatic or manual-provider
  adapters first.
- Whether dashboard should remain read-only until all runner manifests stabilize.

## Git / Retrieval

Related files:

- `roadmap.md`
- `docs/build-tool-runner-spec.md`
- `HANDOFF_CURRENT.md`
- `video_pipeline_core/contract_adapter.py`
- `video_pipeline_core/build_profile.py`
- `video_pipeline_core/generated_assets.py`
- `video_pipeline_core/motion_graphics.py`

Related commits:

- Pending.

Graphify anchors:

- BUILD runner strengthening
- Policy artifacts
- Request artifacts
- Runner manifest

Search tags:

- decision-log
- spec-do-verify
- build-runner
- video-pipeline
- agent-workflow
