# Decision: P3 CapCut draft serializer (clone-skeleton)

Date: 2026-06-08
Status: implemented
Scope: Node 13 render backend / video_pipeline_core/capcut_backend.py
Superpowers phase: execute

Extends `2026-06-08-p3-capcut-optional-backend.md` (that one recorded the
version-independent scaffolding while CapCut was not installed; this one records
the real draft serializer now that CapCut v171 is installed).

## SPEC

Requirement:
Optionally produce a CapCut-openable draft from our Node 10 timeline so a human
can finish (rich text/templates) and export in CapCut.

Why:
CapCut gives strong manual finishing, but has no public API and a proprietary,
version-specific draft format (`new_version` 171.0.0, time in microseconds, one
project = a UUID-linked graph across `materials` (54 buckets) + `tracks`).

Direction:
Do NOT write the format from scratch. Clone a real `draft_content.json`
skeleton and inject our clips. ffmpeg stays the canonical unattended backend;
CapCut is opt-in via `build_profile.render_backend = capcut_draft`.

Non-goals:
- From-scratch draft generation.
- Unattended GUI export (that needs Computer Use; it is a human/CU gate).
- CapCut as a core dependency, or CapCut fields in `segment_contract.json`.

## DO

Files / modules:
- `video_pipeline_core/capcut_backend.py`: `build_capcut_draft`,
  `write_capcut_draft` (plus `build_draft_manifest` / `record_export` from the
  scaffolding step).
- `video_pipeline_core/build_profile.py`: `render_backend` (+ allowed set),
  `requires_human_or_computer_use`.
- `video_pipeline_core/node_registry.py`: Node 13 outputs include
  `capcut_draft_manifest.json` / `capcut_export_manifest.json`.
- `video_pipeline_core/contract_adapter.py`: emit a draft manifest only when
  `render_backend == capcut_draft`.
- `video_tools.py`: `capcut-draft` CLI.
- `tests/test_capcut_backend.py`.

Function-level plan:
- `build_capcut_draft(skeleton, timeline)`: per clip, clone the template video
  material + segment + each `extra_material_refs` sibling with fresh UUIDs; set
  `source_timerange`/`target_timerange` in microseconds; lay clips sequentially;
  update top-level `duration`.
- `write_capcut_draft(skeleton_path, timeline, project_dir)`: write
  `draft_content.json` + a byte-identical `draft_info.json` (compact JSON).

Data / interface changes:
- All times in microseconds (×1e6).
- A draft folder under CapCut's `com.lveditor.draft` root + an entry in
  `root_meta_info.json` (`all_draft_store` + `draft_ids`) for the home list.

Migration / compatibility:
- `render_backend` defaults to `ffmpeg` → this path is inert; existing runs and
  artifacts are unchanged.

## VERIFY

Pre-checks:
- CapCut installed (AppData/Local/CapCut); draft root present; a real skeleton
  draft available (user's `0608`).

Tests:
- `python -m unittest tests.test_capcut_backend` → 12 pass.
- Full suite: `python -m unittest discover -s tests` → 342 pass.

Manual checks:
- Generated `hermes_p3_demo` (3 real clips from the coffee run) from the `0608`
  skeleton; registered in `root_meta_info.json` (backup `root_meta_info.json.hermesbak`;
  CapCut fully quit via `Stop-Process` before editing).
- PENDING: user opens CapCut and confirms `hermes_p3_demo` appears and the
  timeline shows 3 clips. (Agent screenshots mask CapCut content, so a human/CU
  must eyeball it.) Set Status → verified once confirmed.

Regression risks:
- CapCut format is undocumented and version-specific; incomplete 7-file sync can
  cause silent rollback to an older draft on open.
- Editing draft JSON / `root_meta_info.json` while CapCut runs (8 processes,
  minimize-to-tray) gets overwritten — must quit first.
- Cloning vs sharing `extra_material_refs` across segments (we clone per segment).

## Decision Notes

Accepted because:
- Clone-skeleton is robust vs reproducing the private format; matches the MIT
  reference kit's load/mutate/sync approach (techniques only, no code copied).

Tradeoffs:
- Needs a skeleton at runtime. Follow-up: commit a sanitized skeleton template
  so other agents/machines do not depend on the user's personal `0608` draft.
- Export remains manual / Computer-Use; exported mp4 must pass Node 12 verify.

Open questions:
- Does the generated draft open cleanly in CapCut v171? (pending visual confirm.)
- Is per-segment cloning of `extra_material_refs` required, or can siblings be
  shared? (chose clone for safety.)

## Git / Retrieval

Related files:
- `video_pipeline_core/capcut_backend.py`, `tests/test_capcut_backend.py`,
  `video_pipeline_core/build_profile.py`, `video_pipeline_core/contract_adapter.py`,
  `video_pipeline_core/node_registry.py`, `video_tools.py`.

Related commits:
- `0cc9199` feat(p3): render_backend policy (default ffmpeg)
- `986dcca` feat(p3): optional capcut_backend (draft + export manifests)
- `65aa953` feat(p3): wire optional CapCut backend into contract-run
- `aca8f90` feat(p3): real CapCut draft serializer (clone-skeleton approach)
- `45550dc` docs(handoff): record in-progress P3 CapCut draft state

Graphify anchors: `capcut_backend`, `build_capcut_draft`, `write_capcut_draft`,
`render_backend`.

Search tags: decision-log, spec-do-verify, p3, capcut, draft-serializer,
render-backend, node-13, video-autopilot.
