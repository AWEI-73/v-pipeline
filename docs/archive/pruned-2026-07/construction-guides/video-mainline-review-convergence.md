# Video Mainline Review Convergence Construction Guide

Status: active construction guide
Created: 2026-06-27

This guide freezes the next construction direction for the main Video Pipeline
route before changing runtime nodes. The goal is to keep the mainline stable
while review, audio, effects, material map, and Workbench branches are folded
back into one route.

## Goal

Make the video mainline reviewable and mechanically bounded before adding more
render behavior.

Do not start by changing render, Remotion, or Audio mixing. First make the route
surface answer these questions consistently:

- Which stage owns the current decision?
- Which artifact is the source of truth?
- Which reviewer or deterministic gate may pass, warn, revise, or block?
- Which branch may be called next: Material Map, Effect Factory, Soundtrack
  Arranger, Workbench, Brownfield, or Delivery?

## Current Route Shape

The practical route is documented in:

- `RUNBOOK.md`
- `docs/video-pipeline-operating-map.md`
- `docs/artifact-reviewer-map.md`
- `docs/material-map-lifecycle.md`
- `docs/effect-factory-route.md`
- `docs/soundtrack-arranger-route.md`

The runtime node surface is currently in:

- `video_pipeline_core/node_registry.py`

The runtime node order is:

```text
0 -> 3 -> 2 -> 4-7 -> 5 -> 8 -> 9 -> 10 -> 10.5 -> 11 -> 13 -> 12 -> 14
```

The product route map is:

```text
Stage 0  Video Intent Planner
Stage 1  Story Soul
Stage 2  Director Shot Plan
Stage 3  Material Truth
Stage 4  Coverage Gate
Stage 5  BUILD Planning
Stage 6  Official Render
Stage 7  Verify
Stage 8  Workbench Draft Review
Stage 9  Brownfield Edit / Finishing
Stage 10 Delivery
```

These two maps are related but not yet perfectly aligned. Do not assume the
runtime node number and product stage number mean the same thing.

## Branch Ownership

### Mainline

Owns:

- `video_intent.json`
- `project_brief.json`
- `story_soul_blueprint.json`
- `segment_contract.json`
- `timeline_build.json`
- `final.mp4`
- `verify_result.json`
- delivery notes and review reports

Mainline decides when a branch may be called and when its result may be accepted
back.

### Material Map

Owns material truth:

- per-asset `.map.json`
- `project_material_map.json`
- `material_wall_review_verdict.json`
- `material_delta.json`
- `material_first_boundary_acceptance_report.json`
- generated candidate review artifacts

Rule: no material, generated asset, or reshoot candidate satisfies a need until
it returns through Material Map review and a fresh delta/lifecycle decision.

### Effect Factory

Owns designed effects:

- `visual_technique_plan.json`
- `visual_technique_review.json`
- `visual_technique_plan.confirmed.json`
- `effect_design_map.json`
- `effect_contract.json`
- `remotion_prompt_pack.json`
- `remotion_worker_outputs.json`
- `effect_review.json`
- `effect_handoff.json`

Rule: Effect Factory is a design and bounded build branch. Remotion output is a
reviewed candidate or finishing asset, not the canonical renderer.

### Soundtrack Arranger

Owns music/song/source/license planning:

- `soundtrack_plan.json`
- `music_source_candidates.json`
- `sound_license_manifest.json`
- `audio_director_handoff.json`
- `audio_handoff_acceptance.json`
- `audio_mix_plan.json`

Rule: Soundtrack Arranger does not mix final audio. It prepares a license-safe
handoff to Audio Director.

### Workbench

Owns draft inspection and patching:

- `preview_timeline.json`
- `timeline_patch.json`
- `patched_draft_timeline.json`
- `workbench_contract_patch.json`
- subtitle/audio/effect/material patch drafts

Rule: Workbench never overwrites canonical `timeline_build.json`,
`project_material_map.json`, or `final.mp4`.

## Review Layer First

Before changing the runtime path, make review decisions consistent.

Reviewer policy lives in:

- `docs/artifact-reviewer-map.md`
- `video_pipeline_core/reviewer_registry.py`
- `video_pipeline_core/reviewer_role_runner.py`
- `video_pipeline_core/reviewer_aggregation.py`
- `tools/reviewer_flow_acceptance.py`

Policy levels:

```text
light  -> material_producer, technical_verify
normal -> story_director, material_producer, editorial_timeline, technical_verify
deep   -> literary_editor, story_director, material_producer,
          generated_material_art_director, editorial_timeline,
          audio_subtitle_reviewer, effect_reviewer, technical_verify
```

Required discipline:

- `VERIFY` remains deterministic technical/delivery checking.
- Creative review should happen before expensive BUILD/render.
- Material review is hard when coverage is broken.
- Effect review is advisory or revise unless an effect is marked required.
- Audio/subtitle review becomes important when speech, songs, or subtitles are
  central to the video.
- Delivery review must not pass from `final.mp4` alone.

## Construction Order

### Step 1: Review route alignment

Goal: ensure the mainline can say which reviewer applies at each product stage.

Touch only review docs/tests unless a small registry bug is found.

Check:

- Stage 0/1: intent and story review route to `story_director` or
  `literary_editor` only when needed.
- Stage 2: contract review can flag vague material/audio/subtitle/effect needs.
- Stage 3/4: material producer has hard authority on missing/weak material.
- Stage 5: editorial timeline can revise `timeline_build.json`.
- Stage 6/7/10: technical verify and delivery review are distinct.
- Stage 9: effect/audio/subtitle reviewers can advise Brownfield fixes without
  rewriting material truth.

Validation:

```powershell
python video_tools.py reviewer-policy --registry --out .tmp\reviewer_registry.json
python video_tools.py reviewer-flow-acceptance --level normal --scenario all --out .tmp\reviewer_flow_normal.json
python video_tools.py reviewer-flow-acceptance --level deep --scenario all --out .tmp\reviewer_flow_deep.json
python -m unittest tests.test_reviewer_registry tests.test_reviewer_flow_acceptance -q
```

Expected result: review policy is route-driven and does not require every
artifact to be reviewed every time.

### Step 2: Product stage to runtime node bridge

Goal: document and test the bridge between the 0-10 product stages and runtime
nodes.

Likely files:

- `docs/video-pipeline-operating-map.md`
- `tools/pipeline_map.py`
- `docs/generated/pipeline_map.md`
- `docs/generated/pipeline_map.json`
- tests around pipeline map or route entry if present

Required mapping:

| Product stage | Runtime node / branch |
|---|---|
| Stage 0 Video Intent Planner | Node 0 plus `video_intent.json` |
| Stage 1 Story Soul | upstream story route before Node 3 |
| Stage 2 Director Shot Plan | Node 3 and 4-7 facets |
| Stage 3 Material Truth | Material Map lifecycle plus Node 2 coverage |
| Stage 4 Coverage Gate | material delta / dry build / supply review |
| Stage 5 BUILD Planning | Nodes 8, 9, 10, 10.5, 11 |
| Stage 6 Official Render | Node 13 |
| Stage 7 Verify | Node 12 plus audit reports |
| Stage 8 Workbench Draft Review | Workbench branch, draft-only |
| Stage 9 Brownfield Edit / Finishing | Node 14 plus effect/audio/subtitle patch branches |
| Stage 10 Delivery | delivery gate, dashboard state, run layout |

Validation:

```powershell
python tools\pipeline_map.py --out docs\generated\pipeline_map.md --json-out docs\generated\pipeline_map.json
python tools\orphan_audit.py --json
```

Expected result: agents can find the route from RUNBOOK without random doc
searching.

### Step 3: Audio/Soundtrack return seam

Goal: define where Soundtrack Arranger returns into mainline before implementing
final mixing.

Current completed branch artifacts:

- `soundtrack_plan.json`
- `music_source_candidates.json`
- `sound_license_manifest.json`
- `audio_director_handoff.json`
- `audio_handoff_acceptance.json`
- `audio_mix_plan.json`

Current gap:

```text
audio_mix_plan.json + timeline_build.json
  -> audio_fit_plan.json
  -> final_audio.wav / audio_mix_report.json
  -> Node 13 render consumes final_audio.wav
  -> Node 12 verify checks audio levels, license, speech preservation, and fit
```

Do not implement this before Step 1 review alignment is green.

Acceptance target for the later implementation:

- `audio_handoff_acceptance.ok == true`
- `audio_mix_plan.ready_for_mix == true`
- no `reference_only` source enters deliverable audio
- speech sections use ducking or preserve original audio
- final audio duration matches timeline within tolerance

### Step 4: Effect Factory return seam

Goal: keep Effect Factory powerful but bounded.

Do not turn effect examples into fixed templates. The dictionary/parameter
surface should let an agent translate semantic style into reviewable controls,
then pass only confirmed parameters to the worker.

Return artifacts:

- `effect_contract.json`
- `effect_review.json`
- `effect_handoff.json`
- optional `remotion_worker_outputs.json`

Mainline acceptance:

- required effects must have render evidence or explicit waiver;
- decorative effects may warn and continue;
- effect previews do not become final delivery;
- if an effect changes material truth, return to Material Map or Director Shot
  Plan.

### Step 5: Workbench review seam

Goal: keep Workbench useful without making it the pipeline.

Workbench can show:

- story/contract sheet;
- material map by scene/need;
- video, subtitle, audio, and effect lanes;
- draft patches;
- human/agent review state.

Workbench cannot:

- overwrite canonical map/timeline/final;
- silently pass delivery;
- become a second source of truth.

### Step 6: Mainline render hardening

Only after review and branch return seams are clear, update runtime behavior.

Likely later changes:

- Node 5 Audio should stop being only `music_structure.json` and understand the
  new Soundtrack/Audio artifacts.
- Node 9/10 BUILD should expose enough timeline data for audio fitting.
- Node 13 should consume `final_audio.wav` or a verified audio mix artifact, not
  only a single `--music bgm.mp3` path.
- Node 12 should verify audio intent, levels, speech preservation, subtitles,
  and license status.

## Stop Conditions

Stop and revise the construction plan if any of these happen:

- An implementation makes `final.mp4` the only proof of success.
- A branch artifact bypasses its owner gate.
- Workbench writes canonical outputs directly.
- Effect or audio branch outputs are accepted without review evidence.
- `pipeline_home.py` cannot explain the next action.
- A route task packet says complete but canonical artifacts are missing.
- Review policy requires every reviewer for every route by default.

## Minimum Useful Tests Before Mainline Runtime Changes

Before editing Node 5, Node 13, or Node 12 behavior, run:

```powershell
python video_tools.py reviewer-flow-acceptance --level normal --scenario all --out .tmp\reviewer_flow_normal.json
python video_tools.py reviewer-flow-acceptance --level deep --scenario all --out .tmp\reviewer_flow_deep.json
python video_tools.py workflow-manifest --out .tmp\video_tools_workflows.json
python tools\pipeline_home.py --run .tmp\soundtrack_import_url_real_youtube2 --json
python -m unittest tests.test_pipeline_home tests.test_dashboard_state tests.test_audio_handoff_acceptance tests.test_soundtrack_arranger tests.test_soundtrack_providers -q
```

Full regression:

```powershell
python -m unittest discover -s tests -q
```

Run full regression only after the focused route and review tests are green.

## Next Recommended Work

Do this first:

1. Tighten reviewer route acceptance and artifact reviewer map tests.
2. Regenerate pipeline map and verify no important branch is orphaned.
3. Only then implement the Audio return seam:
   `audio_mix_plan + timeline_build -> audio_fit_plan`.

This keeps the main route stable while making Soundtrack, Effect Factory,
Material Map, and Workbench visible as bounded side branches instead of
uncontrolled feature additions.
