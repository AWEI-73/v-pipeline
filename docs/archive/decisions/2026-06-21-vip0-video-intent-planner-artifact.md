# VIP0 Video Intent Planner Artifact

Date: 2026-06-21
Status: accepted
Scope: Stage 0, interactive skill flow, route decision artifact

## SPEC

Solidify VIP0 / ISF infrastructure only. Stage 0 is **Video Intent Planner** and
must decide the input state and entry path before Story Soul, Material Truth,
generated fallback, or BUILD work begins.

The canonical Stage 0 artifact is `video_intent.json`, written by:

```powershell
python video_tools.py video-intent-plan project_brief.json --out video_intent.json
```

It records:

- `video_type`
- `input_state`
- `entry_path`
- `audience`
- `goal`
- `material_availability`
- `text_availability`
- `route`
- `legacy_route`
- `required_followup_questions`
- `assumptions`
- `handoff_to`
- `handoff_packet`

## DO

Implemented:

- `video_pipeline_core/video_intent_planner.py`
- `video_tools.py video-intent-plan`
- `skills/video-intent-planner.md`
- route task Stage 0 allows `video_intent.json`
- command/workflow manifest entry `video_intent_planner`
- run layout declares `video_intent.json` as an orchestration artifact
- `video-intent-acceptance` verifies the VIP0 route/follow-up cases
- route-task Stage 0 accepts a real `video_intent.json` produced by the planner
- roadmap, Start Here, route skill, operating map, canonical route, and docs
  index links

Route handoff:

- `material-first` -> material map lifecycle first, then use map findings to
  reduce ambiguity and build structure.
- `structure-first` -> upstream structure route; zero-material routes then use
  initial material delta before generated material fallback.
- `needs-context` -> ask follow-up questions before choosing a handoff.

`handoff_packet` records owner, first action, required inputs, expected outputs,
and return point. For `material-first`, the first action is
`material_map_quick_inventory`; expected outputs include
`project_material_map.json` and `material_delta.json`.

Compatibility:

- `existing-material-first` maps to `material-first`.
- `story-first` maps to `structure-first`.
- `hybrid` is not a primary Stage 0 entry path; partial material enters
  `material-first`, then material delta decides generation, reshoot, rewrite,
  drop, or waiver.

## VERIFY

Focused tests:

```powershell
python -m unittest tests.test_video_intent_planner tests.test_video_tools_command_catalog tests.test_route_orchestrator -v
python -m unittest tests.test_video_intent_acceptance tests.test_project_workspace tests.test_canonical_route_acceptance -v
```

Coverage:

- teaching with existing material -> `material-first`
- children story with no material but text/story idea -> `structure-first` + generated fallback
- graduation/event with partial material -> `material-first` with `legacy_route=hybrid`
- missing route-changing inputs -> follow-up questions instead of guessed route
- CLI writes `video_intent.json`
- command catalog and route packet expose the Stage 0 artifact

## Boundaries

This does not implement VIP1 teaching, VIP2 event recap, VIP3 memory, renderer
work, Node14, Remotion, or BUILD ranking changes.
