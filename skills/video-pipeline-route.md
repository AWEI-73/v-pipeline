---
name: video-pipeline-route
description: Use when an agent must run or plan the full Hermes Video Pipeline route across story, material map, generated fallback, BUILD, verify, Workbench, Brownfield edit, and delivery
---

# Video Pipeline Route Skill

This is the operator entry skill for the full Hermes Video Pipeline.

Read `docs/START_HERE_VIDEO_PIPELINE.md` first. Then use
`docs/video-pipeline-operating-map.md` as the stage/tool/artifact checklist and
`docs/canonical-video-pipeline-route.md` as the route definition. When the
project needs story quality before material work, read
`docs/upstream-story-route.md`.

## Core Rule

Do not jump straight to render.

Stage 0 is **Video Intent Planner**. Always decide **input state** first, then
the entry path:

```text
Video Intent Planner
-> input_state: material_available | text_available | idea_only | unknown
-> entry_path: material-first | structure-first | needs-context
draft review / brownfield edit
```

Then produce or verify the artifacts for the current stage.

Stage 0 owns the canonical `video_intent.json` artifact. Produce it with:

```powershell
python video_tools.py video-intent-plan project_brief.json --out video_intent.json
```

It must include `input_state`, `entry_path`, `video_type`, `audience`, `goal`,
`material_availability`, `text_availability`, `route`,
`required_followup_questions`, `assumptions`, and `handoff_to`.
If route-changing information is missing, ask the follow-up questions instead
of guessing or entering Story Soul/BUILD.

Stage 0 artifact ownership:

- `project_brief.json` / `brief.json` is raw input.
- `video_intent.json` is the canonical Stage 0 route decision.
- `route_decision.json` is legacy/compat unless a current harness explicitly
  requires it.
- `input_state` records `material_available`, `text_available`, `idea_only`, or
  `unknown`.
- `entry_path` records `material-first`, `structure-first`, or `needs-context`;
  hybrid is not a primary Stage 0 entry path.

The first upstream role is a Video Intent Planner. It may behave like a
teacher, personal video editor, event director, brand editor, or storybook
writer depending on the user's goal and material availability. Do not force a
teaching or personal video into a generated story route.

## Route Boundary

The route owns orchestration, handoff, and stop/go decisions. It does not own
every implementation detail.

Route owns:

- Stage 0 input-state and entry-path decision.
- Greenfield / brownfield / hybrid badge selection.
- `next_action`, `handoff_to`, and bounded task packet shape.
- Review stop points and whether a stage may continue.
- Expected artifacts for each stage and freshness checks.
- Return routes when material, generated outputs, Workbench drafts, or reviews
  change the truth.

Route does not own:

- Renderer internals, ffmpeg implementation details, Remotion implementation
  details, or provider account/auth.
- Treating generated files as accepted material without explicit review.
- Turning Workbench draft patches into canonical truth.
- Manual timeline editing inside Dashboard or Material Map.
- Final visual/story quality judgment by artifact existence alone.

Route must stop instead of continuing when:

- Stage 0 lacks route-changing intent or material information.
- Material Map has candidate/thin/missing must-have needs.
- Generated provider outputs exist but have not re-entered import + explicit
  generated-material review.
- `material_delta.json` blocks ready-for-build.
- reviewer aggregation or a hard-gate reviewer blocks.
- Workbench draft artifacts exist and need agent/backend review.

Dashboard and Material Map are review surfaces. They may save review decisions
or draft artifacts, but must not silently rewrite canonical pipeline truth.
Workbench may draft timeline/material edits, but backend/agent review decides
whether they become official.

Compatibility keyword: generation is fallback for material-first teaching and
personal video routes with real material.

- **material-first**: real or partial media exists. Run material-map early.
  Existing media and existing material reveal people, scenes, actions, emotions, timeline, and gaps;
  then interaction reduces ambiguity and builds the structure. generation is
  fallback only for missing/non-proof support.
- **structure-first**: no usable media exists, but an article, outline, script,
  story, or developed idea exists. Clarify the structure first, then create
  material needs and route missing visuals through generated material fallback.
- **needs-context**: the request is too vague to choose a handoff. Ask focused
  questions first.

Legacy wording remains accepted as compatibility language:
`existing-material-first` maps to `material-first`; `story-first` maps to
`structure-first`; `hybrid` is not a primary Stage 0 entry path. Partial
material enters `material-first`, then material-delta decides generation,
reshoot, rewrite, drop, or waiver.

Review policy is route-driven, not universal. Use
`docs/artifact-reviewer-map.md` to decide whether the route needs `light`,
`normal`, or `deep` review. Materialize the policy when needed:

```powershell
python video_tools.py reviewer-policy --level normal --out reviewer_policy_packet.json
python video_tools.py reviewer-flow-acceptance --level deep --scenario all --out reviewer_flow_acceptance.json
```

For multi-agent execution, do not let subagents decide the whole route ad hoc.
Issue bounded task packets and accept them with the route orchestrator harness:

```powershell
python video_tools.py route-task-next RUN_DIR --out route_subagent_task.json
# external agent writes allowed outputs and route_subagent_result.json
python video_tools.py route-task-accept --task route_subagent_task.json --result route_subagent_result.json --state-out route_orchestrator_state.json
python video_tools.py route-orchestrator-acceptance RUN_DIR --route existing-material-first --stage-count 4 --out route_orchestrator_acceptance.json
```

The harness enforces `must_not_touch`, output freshness, allowed output
whitelists, and explicit `blocked / needs_context / failed` transitions. It
trusts artifacts, not agent claims.

Worker-facing packet rules and a copyable prompt template live in
`docs/route-agent-runner-protocol.md`.

## Stage Order

Use this order unless the user explicitly asks for a bounded review/edit task:

1. Intake
2. Story Soul
3. Director Shot Plan
4. Material Truth
5. Coverage / Decision Gate
6. BUILD Planning
7. Official Render
8. Verify
9. Workbench Draft Review
10. Brownfield Edit / Finishing
11. Delivery

Legacy names are aliases, not the public route:

- `M6` = Material Truth + Coverage / Decision Gate
- `SRP` = BUILD planning internals
- `FX` = Effects route internals
- `Node14` = Brownfield Edit / Finishing route

## Upstream Story Line

Use this before Material Truth when the brief is story-heavy, generated,
children-oriented, essay-like, or emotionally framed:

```text
Role / Literary Lens
-> Blueprint Interview
-> Story Soul Package
-> Director Shot Plan
-> Contract Compile
-> Material-Ready Handoff
```

This route is documented in `docs/upstream-story-route.md`.

Do not collapse these into one prompt if quality matters. The important split:

- `Role / Literary Lens`: what kind of mind is writing the piece;
- `Blueprint Interview`: prose soul in `blueprint.md` plus beat index in
  `blueprint.json`;
- `Story Soul Package`: executable story-world, concept, beats, shot plan,
  material needs, and generation manifest;
- `Director Shot Plan`: concrete visual/audio/subtitle/effect needs;
- `Contract Compile`: validated `segment_contract.json` and traceable
  `material_needs.json`;
- `Material-Ready Handoff`: enter material map / delta, not BUILD directly.

## Intake Questions

Ask only what materially changes the route:

- audience and purpose;
- target length;
- output type: story / event / training / explainer / recap;
- material availability and material mode:
  existing-material-first / story-first / hybrid;
- can reshoot or generate missing material;
- must-have beats or people;
- subtitle / voiceover / music expectations;
- review level: quick smoke, normal, high.

If enough information already exists in artifacts, do not re-ask. Read the
artifacts and continue.

## Route Selection

### Existing-material route

Use when the user already has footage or images.

Expected path:

```text
material-map -> material_delta -> contract-run -> verify -> Workbench/Brownfield if needed
```

### Generated-material route

Use when material is missing or the requested style is synthetic/comic/storybook.

Expected path:

```text
story-soul-blueprint
-> material_needs
-> initial project_material_map.json (empty or initial material truth)
-> initial material_delta.json with ready_for_build=false
-> material-generation-fallback
-> generated-image-provider-packet
-> provider output mapping is required
-> generated-material-import
-> generated-material-review
-> material_delta
-> contract-run
```

Generated files must be reviewed before they satisfy material needs.
For zero-material projects, do not skip the initial delta: fallback should be
driven by missing/thin evidence, not by agent confidence alone.

### Hybrid route

Use when some real material exists and some needs must be generated or reshot.

Expected path:

```text
project_material_map + generated candidates
-> explicit review
-> fresh material_delta
-> revision or BUILD
```

### Draft / Brownfield route

Use after a render or review when the user wants local changes.

Expected path:

```text
Workbench draft patch
-> workbench handoff
-> Brownfield edit if needed
-> rerender / verify
```

If the edit changes material truth, return to Material Truth and rerun delta.

## Resume Existing Run

When the user points to an existing run folder, recover state before planning
new work:

1. Locate the newest or user-specified run directory.
2. Read available artifacts in this order:
   `video_intent.json`, `state.json`, `segment_contract.json`, `material_needs.json`,
   `project_material_map.json`, `material_delta.json`, `timeline_build.json`,
   `verify_result.json`, `preview_timeline.json`, `timeline_patch.json`,
   `workbench_contract_patch.json`.
3. If `final.mp4` exists, treat it as a delivery candidate only after checking
   `verify_result.json` or rerunning `verify`.
4. If draft artifacts exist, do not assume they are canonical. Route them
   through `workbench-handoff-validate` or Brownfield Edit.
5. If material or needs changed, rerun `material-delta` fresh before BUILD.

## Tool Checklist

Use deterministic tools for facts:

- `reviewer-policy`: reviewer role expansion and eval principle packet.
- `video-intent-plan`: Stage 0 `video_intent.json` route decision artifact.
- `video-intent-acceptance`: deterministic VIP0 route/follow-up acceptance.
- `reviewer-flow-acceptance`: reviewer policy smoke/e2e harness for route,
  upstream, and effects/brownfield reviewer sets.
- `validate-needs`: material need schema.
- `project-material-map`: aggregate material maps.
- `material-map-lifecycle`: route material stage.
- `material-delta`: coverage decision.
- `material-revision`: accepted revision decisions.
- `contract-run`: official BUILD and pre-BUILD gate.
- `verify`: delivery quality.
- `workbench-handoff-validate`: draft handoff safety.
- `effect-revision-*` / `remotion-*`: Brownfield effect route.
- `route-task-next` / `route-task-accept` / `route-orchestrator-acceptance`:
  runner-neutral multi-agent packet issuance and fail-closed acceptance.
- `tools/material_first_boundary_acceptance.py`: local material-first boundary
  acceptance from Stage 2/3 through Stage 5. It writes
  `material_first_boundary_acceptance_report.json`, which `pipeline_home.py`
  and Dashboard state use as the compact handoff result.

## Minimal CLI Skeletons

Existing material:

```powershell
python video_tools.py project-material-map --maps-dir MATERIAL_MAPS --needs material_needs.json --out project_material_map.json
python video_tools.py material-map-lifecycle --out-dir RUN --needs material_needs.json --project-map project_material_map.json --contract segment_contract.json
python tools/material_first_boundary_acceptance.py --out RUN --source-dir MATERIAL_SOURCE_DIR --wall-verdict material_wall_review_verdict.json --max-assets 12 --json
python video_tools.py contract-run segment_contract.json --material-db materials_db.json --music bgm.mp3 --out final.mp4 --mat-dir RUN
python video_tools.py verify --script segment_contract.json --timing audio/tts_timing.json --edit-log edit_log.json --srt subtitles.srt --video final.mp4 --out verify_result.json
```

For material-first route testing, prefer
`tools/material_first_boundary_acceptance.py` before render. If
`material_first_boundary_acceptance_report.json` returns `ok=false`, stop and
repair the reported `failed_stage`; do not continue to `contract-run`. Workers
must use the operator-provided material folder exactly: do not substitute `--source-dir`; if the specified folder is missing, stop and report blocked
instead of selecting a neighboring folder.

Generated material:

```powershell
python video_tools.py material-generation-fallback material_delta.json --needs material_needs.json --out material_generation_fallback.json
python video_tools.py generated-image-provider-packet material_generation_fallback.json --out-dir provider_packet
# image-capable agent writes each target_file from generated_provider_packet.json
python video_tools.py generated-material-import material_generation_fallback.json --needs material_needs.json --provider-outputs provider_outputs.json --out-dir generated_material
python video_tools.py generated-material-review generated_material/project_material_map.json --needs material_needs.json --verdict generated_material_review.json --out reviewed_project_material_map.json
```

Workbench / Brownfield:

```powershell
python tools/preview_timeline.py build --artifact-root RUN --out preview_timeline.json
python tools/timeline_patch.py apply --artifact-root RUN --patch timeline_patch.json --out patched_draft_timeline.json
python video_tools.py workbench-handoff-validate RUN --out workbench_handoff_report.json
python video_tools.py effect-revision-request --baseline-review light_effects_baseline_review.json --light-effects-plan light_effects_plan.json --out effect_revision_request.json
```

## Stop Conditions

Stop and report instead of guessing when:

- must-have material is missing and no fallback/waiver exists;
- generated provider outputs are missing or cannot be mapped to jobs;
- generated material has not been explicitly reviewed;
- material delta is broken or stale;
- Workbench patch would overwrite canonical truth;
- effect output changes story evidence instead of finishing;
- verify fails on black frames, subtitle corruption, or content mismatch.

## Storybook / Comic Route

For picture-book, comic, fairy-tale, or children story cases:

- set `storyboard_panel_locked=true`;
- usually use `review_policy.level=deep`;
- use generated material fallback if no source art exists;
- include `generation_manifest.json`, style/character consistency rules, panel
  count, and generated material review rubric before provider handoff;
- state Chinese subtitle requirements if the output is for Chinese-speaking
  children;
- prefer more panels over unrelated filler;
- if holding one panel for a long time, make that intentional in pacing;
- verify Chinese subtitles are real UTF-8 text, not `????`;
- never map generated images by "latest N files"; use provider output mapping.

## Delivery Summary

A completed route report must state:

- final video path;
- duration;
- material coverage summary;
- generated or real material source count;
- verify result;
- known limitations;
- next action, if any.
