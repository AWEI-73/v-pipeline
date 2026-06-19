# ISF1 Interactive Skill Flow

Date: 2026-06-19

## Decision

Solidify the video pipeline as an interactive skill flow, not as a fixed story
template or CI/CD script.

The entry skill remains `video-pipeline`. It routes vague work to
`video-workflow`, story-thin work to `story-soul-blueprint`, material truth to
`material-map`, missing generated assets to `generated-material-producer`, and
official rendering back to the deterministic backend.

## Why

The backend can now enforce material truth, generated-material review, draft
Workbench patching, and final ffmpeg render. The remaining failure mode is not
usually "the tool cannot build"; it is "the agent did not ask enough upstream
questions and produced a thin or mismatched plan."

The flow must therefore teach agents when to stop and ask, which artifact to
emit, and which owner receives the next step.

## Canonical Flow

```text
0 Intake / ambiguity reduction
  -> project_brief.json
1 Story soul / creative blueprint
  -> story_world.json
  -> creative_concept.json
  -> screenplay_beats.json
  -> director_shot_plan.json
2 Material truth
  -> material_needs.json
  -> project_material_map.json
  -> material_delta.json
3 Generated fallback, only when allowed
  -> material_generation_fallback.json
  -> generated_provider_packet.json
  -> generated_provider_outputs.json
  -> reviewed generated material map
4 Contract / BUILD
  -> segment_contract.json
  -> timeline_build.json
  -> render candidate
5 Human review / Workbench draft
  -> timeline_patch.json
  -> patched_draft_timeline.json
  -> workbench_contract_patch.json
6 Verify / delivery
  -> verify_result.json
  -> artifact_manifest.json
  -> state.json.next_action == null / complete_review_final
```

## Boundaries

- Do not confuse process solidification with template solidification. Story
  templates, story sets, and multi-video libraries come later.
- Do not skip `material-map` because generated assets exist. Generated assets
  enter as candidates and require review.
- Do not let Workbench drafts become canonical artifacts without agent review.
- Do not auto-fill generated comic/photo narration with other panels from the
  same need. Use `storyboard_panel_locked=true`, stretch the panel, generate
  more panels, or shorten the narration.

## Current Skill Contracts

- `skills/video-pipeline.md` owns the top-level phase routing.
- `skills/video-workflow.md` owns the interactive brief contract and stop
  conditions.
- `skills/route.md` owns `state.json.next_action` dispatch vocabulary.

## Verification

Locked by `tests/test_interactive_skill_flow_docs.py`.
