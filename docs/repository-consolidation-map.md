# Repository Consolidation Map

Date: 2026-06-17
Status: current orientation map

This document is the high-level map for agents working in this repository. It
does not replace detailed contracts. It points to the right owner before a
change is made.

Inputs used for this map:

- current code scan at commit `ec05a1b`;
- historical Graphify output built from commit `ce2add48` (local analysis
  artifact, not tracked in the public MVP tree);
- current frontend boundary docs:
  `docs/workbench-dashboard-integration.md`,
  `dashboard/workbench_native/API_CONTRACT.md`, and
  `docs/material-organization-policy.md`.

The Graphify snapshot is useful for finding high-connectivity areas, but it is
stale after the recent frontend and Workbench integration commits. Re-run
Graphify before using it for precise refactor impact analysis.

## Product Surfaces

### Control Index

Owner: `dashboard/index.html`, `dashboard/index.css`, `dashboard/index.js`,
served by `tools/dashboard_server.py`.

Purpose:

- top-level project cockpit;
- shows artifact root, final-video presence, Dashboard entry, Workbench entry,
  and Workbench health;
- read-only.

Do not add timeline editing here. Route editing to Workbench.

### Dashboard

Owner: `dashboard/dashboard_v1.*`, `video_pipeline_core/dashboard_state.py`,
`tools/dashboard_server.py`.

Purpose:

- read-oriented run review;
- shows run state, node/gate findings, material-map status, final video, reports,
  and Workbench draft readiness.

Dashboard may link to draft artifacts, but it must not author edits.

### Workbench

Owner: `dashboard/workbench_native/*`, `tools/workbench_server.py`, and the
Workbench draft tools in `tools/`.

Purpose:

- interactive material-composition preview;
- human draft edits for clip duration, source windows, order, replacement,
  subtitles, audio cues, and effect intents;
- optional non-canonical ffmpeg preview export.

Workbench writes draft artifacts only. Official delivery still goes through the
backend BUILD pipeline.

## Runtime Entry Points

### Primary CLI

`video_tools.py` is the large multi-command tool surface. It includes contract
adapt/run, material-map lifecycle, material delta/revision, audits, acceptance
replay, project workspace helpers, CapCut draft helpers, and legacy media tools.

Use it when the operation is a canonical pipeline command.

`video_tools.py commands-manifest [--out FILE]` emits the machine-readable
command catalog. The implementation uses `VIDEO_TOOLS_DISPATCH` plus
`video_pipeline_core/tool_command_catalog.py`; agents should inspect that
manifest before guessing which command group owns a feature.

`video_tools.py workflow-manifest [--out FILE]` emits the machine-readable
workflow catalog for bounded Agent operations: run setup, material-map
lifecycle, canonical build, and Workbench draft rerender. It is an execution
guide, not a new orchestrator.

`video_tools.py test-tiers [--tier NAME] [--dry-run]` emits or runs the standard
verification tiers. Use it to choose focused checks before the full regression;
it is a thin command runner over existing Python/Node tests. The emitted
manifest also carries non-blocking `optional_checks` for environment-dependent
guards, such as the Workbench browser layout smoke that protects the native
monitor and four timeline lanes.

### Runtime Resume

`runtime.py` is the route/resume/status surface. It reads `state.json` and
dispatches the next action.

Use it when continuing a project run.

### Project Workspace

`video_pipeline_core/project_workspace.py` creates external project/run folders
and writes the repo-local `.project/active.json` pointer.

New runs also include `run_layout.json`, a machine-readable map of folder roles,
canonical artifact names, Workbench draft artifact names, and derived cache
directories. It is navigation metadata for agents and frontend shells; it does
not replace `segment_contract.json`, material maps, `state.json`, or gate
artifacts.

Use `video_tools.py run-layout-validate <run-dir>` before handing a run to
another agent or shell. The validator owns folder/artifact ownership checks; UI
surfaces only display its read-only status.

Use `video_tools.py workbench-handoff-validate <run-dir>` before consuming
Workbench human edits. It validates the draft handoff index, referenced draft
artifact presence, and size/hash integrity; canonical artifacts remain outside
the handoff surface.

### Contract Run

`video_pipeline_core/contract_adapter.py` adapts canonical contracts and runs
the canonical BUILD path. It owns M6 material gates, revision runtime plumbing,
and stale-final safety behavior.

Use it when changing how a contract becomes a renderable build.

### Workbench Server

`tools/workbench_server.py` serves `/workbench`, `/media`, and
`/api/workbench/*`. It is write-limited and should keep canonical artifact
protection server-side.

Use it when adding or changing interactive draft-edit behavior.

### Dashboard Server

`tools/dashboard_server.py` serves `/`, `/dashboard`, `/api/control/*`,
`/api/projects`, `/api/artifacts`, and material listing endpoints.

Use it when changing read/status surfaces or Control Index integration.
It reads `run_layout.json` as read-only navigation metadata through
`/api/control/status` and `/api/artifacts`; it must not write or repair layout
artifacts.

## Backend Domain Ownership

### SPEC And Contract

Primary files:

- `video_pipeline_core/spec_contract.py`
- `video_pipeline_core/spec_review.py`
- `video_pipeline_core/blueprint.py`
- `video_pipeline_core/blueprint_compile.py`
- `video_pipeline_core/blueprint_to_contract.py`
- `video_pipeline_core/contract_adapter.py`

Responsibility:

- validate and adapt what should be made;
- fail closed before BUILD if the contract is invalid;
- avoid hidden coercion.

### Material Map Lifecycle

Primary files:

- `video_pipeline_core/material_needs.py`
- `video_pipeline_core/material_lineage.py`
- `video_pipeline_core/material_delta.py`
- `video_pipeline_core/material_revision.py`
- `video_pipeline_core/material_map_lifecycle.py`
- `video_pipeline_core/material_map.py`
- `video_pipeline_core/project_material_map.py`
- `video_pipeline_core/material_retrieval.py`

Responsibility:

- express material needs;
- connect needs to scenes through satisfies edges;
- compute covered/thin/missing/excess;
- block BUILD when required material is not ready;
- retrieve renderable windows for BUILD.

Do not move source files to "organize" material. The material map is the truth;
folders are projections. See `docs/material-organization-policy.md`.

### BUILD Planning

Primary files:

- `video_pipeline_core/mv_cut.py`
- `video_pipeline_core/opening_sequence.py`
- `video_pipeline_core/opening_recipe_planner.py`
- `video_pipeline_core/beat_sequence.py`
- `video_pipeline_core/sequence_recipe_planner.py`
- `video_pipeline_core/story_arc_planner.py`
- `video_pipeline_core/ending_sequence.py`
- `video_pipeline_core/edit_point_planner.py`
- `video_pipeline_core/punctuation.py`
- `video_pipeline_core/music_structure.py`
- `video_pipeline_core/sfx.py`
- `video_pipeline_core/light_effects.py`
- `video_pipeline_core/motion_graphics.py`

Responsibility:

- turn approved material windows into a timeline;
- apply opening, beat sequence, story arc, ending, punctuation, and light effect
  intent;
- keep correctness and material evidence ahead of aesthetic preference.

Graphify identified `run_mv()`, `plan_opening_recipe()`,
`plan_story_arc()`, and `plan_ranked_windows()` as high-connectivity nodes.
Treat these as refactor-sensitive. Add characterization tests before moving
behavior.

### VERIFY And Delivery

Primary files:

- `video_pipeline_core/delivery_gate.py`
- `video_pipeline_core/black_frame_audit.py`
- `video_pipeline_core/broll_audit.py`
- `video_pipeline_core/new_visual_information_audit.py`
- `video_pipeline_core/presentation_feel_audit.py`
- `video_pipeline_core/visual_fatigue.py`
- `video_pipeline_core/semantic_novelty_audit.py`
- `video_pipeline_core/action_progression.py`
- `video_pipeline_core/timeline_invariants.py`
- `video_pipeline_core/verify_evidence.py`
- `video_pipeline_core/visual_audit.py`
- `video_pipeline_core/caption_audit.py`
- `video_pipeline_core/treatment_audit.py`

Responsibility:

- prove technical and evidence conditions after BUILD;
- separate hard delivery failures from quality warnings;
- avoid treating weak aesthetic proxies as proof of quality.

### Optional / Provider-Specific Backends

Primary files:

- `video_pipeline_core/capcut_backend.py`
- `video_pipeline_core/motion_graphics.py`

Responsibility:

- optional finishing or motion-graphics paths;
- never replace ffmpeg as the unattended canonical backend without an explicit
  roadmap decision.

## Workbench Draft Ownership

Canonical backend-owned artifacts:

- `final.mp4`
- canonical `timeline.json`
- source contracts
- material-map source files
- delivery and verification gate artifacts

Workbench-owned draft artifacts:

- `preview_timeline.json`
- `timeline_patch.json`
- `patched_draft_timeline.json`
- `workbench_contract_patch.json`
- `subtitle_patch.json`
- `audio_cue_patch.json`
- `effect_patch.json`
- `workbench_handoff.json`
- `workbench_review_report.json`
- `workbench_review_report.md`
- optional `workbench_export.mp4`

Rules:

- Workbench may preview and draft.
- Backend/Agent decides whether a draft becomes an official rerender or contract
  revision.
- Browser code must not contain canonical gate logic.

## Acceptance And Harness Scripts

These scripts are evidence tools, not product entry points:

- `tools/m6e_acceptance.py`
- `tools/srp_acceptance_replay.py`
- `tools/srp_real67_sanity.py`
- `tools/srp_real67_review_demo.py`
- `tools/srp_real67_fuller_replay.py`
- `tools/gemini_demo_film.py`

Use them to prove behavior on controlled or real footage. Do not make production
logic depend on their fixture shortcuts.

## Test Families

Frontend and Workbench:

- `tests/test_dashboard_server.py`
- `tests/test_workbench_server.py`
- `tests/test_workbench_frontend_smoke.py`
- `tests/test_workbench_tracks.py`
- `tests/test_workbench_proxy.py`
- `tests/workbench_*_smoke.js`
- `tools/workbench_frontend_smoke.py` (fast HTML/API guard for native monitor,
  playback controls, and the four tracks)
- `tools/workbench_browser_layout_smoke.mjs` (optional browser guard; also
  listed under `video_tools.py test-tiers` -> `workbench.optional_checks`)

Material lifecycle:

- `tests/test_material_needs.py`
- `tests/test_material_lineage.py`
- `tests/test_material_delta.py`
- `tests/test_material_delta_gate.py`
- `tests/test_material_revision.py`
- `tests/test_material_revision_runtime.py`
- `tests/test_material_map_lifecycle.py`
- `tests/test_project_material_map.py`
- `tests/test_material_map_loader.py`

BUILD planning:

- `tests/test_map_retrieval_wiring.py`
- `tests/test_material_retrieval.py`
- `tests/test_sequence_recipe_planner.py`
- `tests/test_opening_recipe_planner.py`
- `tests/test_story_arc_planner.py`
- `tests/test_story_arc_runtime.py`
- `tests/test_ar1_run_mv_characterization.py`

Acceptance:

- `tests/test_srp_acceptance_replay.py`
- `tests/test_srp_real67_*`

When moving shared behavior, run the focused family first, then full regression.

## Consolidation Backlog

### Low Risk

Do these first:

- keep this map and `docs/INDEX.md` current;
- keep `dashboard/README.md`,
  `docs/workbench-dashboard-integration.md`, and
  `dashboard/workbench_native/API_CONTRACT.md` aligned;
- add focused tests before any endpoint or draft artifact change;
- keep local demo files out of commits unless explicitly promoted.

### Medium Risk

Do only with characterization tests:

- split more of `dashboard/workbench_native/workbench.js` into pure helpers;
- extract shared dashboard/workbench status builders from `tools/dashboard_server.py`;
- add a material-library projection panel using material-map metadata;
- add richer effect-intent presets that remain draft-only until backend review.

### High Risk / Defer

Do not do as cleanup:

- moving core modules into new directories;
- merging Dashboard and Workbench into one server process;
- changing canonical artifact names;
- making Workbench the official renderer;
- auto-applying `workbench_contract_patch.json` to source contracts;
- reorganizing physical source media files.

## Recommended Next Increment

The next safe consolidation increment is not a code move. It is a bounded
frontend/backend API stabilization pass:

1. freeze `/api/control/status` and `/api/workbench/health` response shapes with
   tests;
2. add an operator-facing "which artifact owns this state?" panel or doc link in
   the Control Index;
3. keep all writes in Workbench server whitelist;
4. verify with JS smoke, Workbench frontend smoke, Dashboard server tests, and
   full regression.

Only after that should module moves or backend package reshaping be considered.
