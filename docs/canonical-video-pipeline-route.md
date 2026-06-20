# Canonical Video Pipeline Route

Date: 2026-06-20
Status: v1 accepted / keep as route map before broad node renaming
Scope: full Hermes Video Pipeline flow, skill routing, tools, artifacts, gates

This document is the stable route map for agents. It does not replace older
M/SRP/FX/Node names immediately. It gives one canonical workflow that maps
skills to tools and artifacts so future templates can extend the same route
without changing the pipeline each time.

## Operating Principle

Hermes is a contract-first video pipeline, not a one-off slideshow script.

The stable unit of work is:

```text
intent -> story/design contract -> material truth -> BUILD -> verify -> draft edit -> delivery
```

Generated material, real footage, human-picked footage, and Workbench edits all
must return to the same artifact route. No surface may silently become the new
truth.

## Canonical Route

| # | Canonical stage | Purpose | Primary skill | Main tools | Main artifacts | Gate / stop condition |
|---|---|---|---|---|---|---|
| 0 | Intake | Capture user goal, audience, length, style, constraints, available material, and expected output. | `video-workflow.md`, `video-pipeline.md` | none, or project/run tools if needed | project brief, run folder | Stop if goal is ambiguous enough to change route. |
| 1 | Story Soul | Create story world, narrative device, emotional spine, and core idea before technical shot planning. | `story-soul-blueprint.md`, `blueprint-interview.md`, `writer.md` | `story-soul-blueprint`, `blueprint-to-contract` when compiling from blueprint | `story_soul_blueprint.json`, screenplay beats, director shot plan | Stop if story lacks a narrative device or character/emotional spine. |
| 2 | Director Shot Plan | Convert story into concrete beats, shot purposes, visual families, audio/subtitle intent, and material needs. | `director.md`, `audio-director.md`, `subtitle-director.md`, `effects-director.md` | `effect-intent-plan`, `validate-needs` | `material_needs.json`, `effect_intent_plan.json`, subtitle plan | Stop if must-have needs are vague or untestable. |
| 3 | Material Truth | Inventory real material, generate missing material if needed, and attach evidence to needs. | `material-map.md`, `curator.md`, `material-generation-fallback.md`, `generated-material-producer.md` | `project-material-map`, `material-map-lifecycle`, `material-generation-fallback`, `generated-image-provider-packet`, `generated-material-import`, `generated-material-review` | per-asset `.map.json`, `project_material_map.json`, `material_generation_fallback.json`, `generated_provider_packet.json`, reviewed material map | Stop if material is missing, unreviewed, dangling, or insufficient for must-have needs. |
| 4 | Coverage / Decision Gate | Compare needs to accepted material evidence; decide build, wait, generate, reshoot, rewrite, drop, or waive. | `gap-analyzer.md`, `shooting-brief.md`, `route.md` | `material-delta`, `lineage-link`, `material-revision`, `contract-run` pre-BUILD gate | `material_delta.json`, `shooting_brief.json`, `revision_decisions.json`, `revised_segment_contract.json` | BUILD is blocked if delta is broken or must-have gaps lack valid fallback/waiver. |
| 5 | BUILD Planning | Select windows, order material, create sequence/opening/story arc plans, subtitles, audio cues, and effect intents. | `editor.md`, `audio-director.md`, `subtitle-director.md`, `effects-director.md` | `contract-adapt`, `contract-dry-build`, `rank-local`, `match-mv`, internal SRP/VD planning in `contract-run` | `generated_mv_script.json`, `timeline_build.json`, `sfx_cues`, story arc/opening/sequence traces | Stop if planning produces GAP, unrenderable windows, or contract/runtime mismatch. |
| 6 | Official Render | Produce canonical video through backend renderer. | `editor.md` | `contract-run`, `script-run`, `assemble`, `merge-final`, `burnsub`, `mix-audio`, `sfx-mix` | `final.mp4`, `subtitles.srt`, `artifact_manifest.json`, `state.json` | Official output only exists after render + verify path succeeds. |
| 7 | Verify | Check technical quality, content alignment, subtitles, black frames, visual fatigue, and delivery readiness. | `verify.md` | `verify`, `black-frame-audit`, `caption-audit`, `new-visual-audit`, `visual-audit`, `timeline-audit`, `verify-evidence` | `verify_result.json`, audit reports, contact sheet, review report | If failure is factual/material, return to Material Truth or Coverage Gate. If failure is finishing/editing, route to Brownfield Edit. |
| 8 | Workbench Draft Review | Let humans/agents inspect composition, adjust draft timing/subtitles/audio/effect markers, and export preview/draft patches. | `dashboard.md`, `brownfield-edit.md` | `workbench_server.py`, `preview_timeline.py`, `timeline_patch.py`, `workbench-handoff-validate`, `workbench-draft-rerender` | `preview_timeline.json`, `timeline_patch.json`, `patched_draft_timeline.json`, `workbench_contract_patch.json`, draft preview/export | Workbench must not overwrite canonical timeline, material map, or final. |
| 9 | Brownfield Edit / Finishing | Apply bounded fixes after review: subtitle/audio/effect patch, generated effect assets, Remotion adapter route, or small material replacement. | `brownfield-edit.md`, `effects-director.md`, `subtitle-director.md`, `audio-director.md` | `effect-revision-request`, `effect-revision-draft`, `effect-revision-apply`, `remotion-prompt-pack`, `remotion-worker-outputs`, `remotion-worker-smoke`, `remotion-composite-draft`, `light-effects-plan` | `effect_revision_request.json`, `effect_recipe_patch.json`, `remotion_prompt_pack.json`, `remotion_effect_review.json`, non-canonical draft composite | If edit changes material truth, return to Material Truth / Delta. If it only changes finishing, rerender/draft then verify. |
| 10 | Delivery | Produce final report, artifacts, and handoff. | `route.md`, `verify.md`, `dashboard.md` | `dashboard`, `state`, run layout tools | `final.mp4`, `review_report.md`, `contact_sheet.jpg`, `run_layout.json`, delivery notes | Do not mark delivery complete without final path, verify status, and known limitations. |

## Skill Design Rules

### 1. Skills ask for missing decisions, tools enforce facts

Skills are interactive operators. They should ask or infer missing creative and
workflow decisions. Tools should validate deterministic facts.

Examples:

- `story-soul-blueprint.md` may ask for audience, lesson, narrative device, and
  emotional arc.
- `material-map.md` may ask whether the route is existing-material-first,
  script-first, or generated-material fallback.
- `material-delta` decides coverage from artifacts, not from agent confidence.
- `contract-run` reruns gates before BUILD, even if a prior report said ready.

### 2. Generated assets are material candidates, not truth

Generated image/video/audio should flow through:

```text
generation job -> provider output -> generated-material-import
  -> generated-material-review -> material_delta -> BUILD
```

Do not let generated files satisfy needs until review accepts them. Do not infer
provider output order from "latest files"; use explicit job-to-file mapping.

### 3. Workbench is draft authority only

Workbench may create:

- draft timeline patches;
- draft subtitles/audio/effect markers;
- draft export previews;
- contract patch suggestions.

Workbench may not overwrite:

- canonical `timeline_build.json`;
- canonical material maps;
- canonical `final.mp4`;
- accepted material evidence.

### 4. Effects are neutral until backend route is chosen

`effect_intent_plan.json` stays backend-neutral. Ffmpeg, motion graphics,
Remotion, or future providers are adapters.

Current policy:

- lightweight Workbench preview is approximate-by-design;
- official output remains ffmpeg / contract-run unless Brownfield route creates
  an explicitly reviewed non-canonical composite;
- Remotion is allowed as an effect asset/adapter worker, not as a replacement
  for the core pipeline yet.

### 5. Templates extend the route, not the route itself

Templates should define:

- story structure;
- default audience/style;
- default material need patterns;
- default pacing profile;
- default effect/audio/subtitle style;
- review checklist.

Templates should not bypass material maps, delta, BUILD, or verify.

## Tool Surface By Stage

### Intake / Project

- `project-init`
- `project-new-run`
- `workflow-manifest`
- `commands-manifest`
- `run-layout-validate`

### Story / Blueprint

- `story-soul-blueprint`
- `blueprint-coverage`
- `blueprint-compile`
- `blueprint-to-contract`
- `spec-review`
- `capability-manifest`

### Material

- `validate-needs`
- `project-material-map`
- `material-map-lifecycle`
- `material-generation-fallback`
- `generated-image-provider-packet`
- `codex-imagegen-provider-fill`
- `generated-material-import`
- `generated-material-review`
- `visual-diversity-review`
- `visual-family-normalize`

### Coverage / Revision

- `lineage-link`
- `material-delta`
- `material-revision`
- `supply-review`
- `contract-dry-build`

### BUILD

- `contract-adapt`
- `contract-run`
- `script-run`
- `rank-local`
- `match-mv`
- `kenburns`
- `collage`
- `montage`
- `gen-bgm`
- `music-fetch`
- `srt`
- `mksrt`
- `subtitle`
- `burnsub`
- `mix-audio`
- `sfx-mix`
- `assemble`
- `merge-final`

### Effects / Brownfield

- `effect-intent-plan`
- `light-effects-plan`
- `effect-revision-request`
- `effect-revision-draft`
- `effect-revision-apply`
- `remotion-prompt-pack`
- `remotion-worker-outputs`
- `remotion-worker-smoke`
- `remotion-composite-draft`
- `workbench-handoff-validate`
- `workbench-draft-rerender`

### Verify

- `verify`
- `verify-evidence`
- `timeline-audit`
- `broll-audit`
- `new-visual-audit`
- `black-frame-audit`
- `caption-audit`
- `keyframe-grid`
- `visual-audit`
- `semantic-novelty-audit`
- `action-progression-audit`
- `replay-acceptance`

### Optional External / Legacy

- `capcut-draft`
- `capcut-finalize`
- `pexels-search`
- `pexels-download`
- `search`
- `download`
- `probe`
- `cut`
- `concat`
- `grade`
- `title-card`
- `title-sequence`

## Artifact Ownership

| Artifact | Owner stage | Canonical? | Notes |
|---|---|---|---|
| `project_brief.json` | Intake | yes per run | User/project intent. |
| `story_soul_blueprint.json` | Story Soul | yes per route | Creative source before screenplay/materials. |
| `segment_contract.json` | Story / Director | yes | Main BUILD contract. |
| `material_needs.json` | Director Shot Plan | yes | Stable `need_id` source. |
| per-asset `.map.json` | Material Truth | yes | Source-level evidence. |
| `project_material_map.json` | Material Truth | projection | Aggregates per-asset maps; not a second truth. |
| `material_generation_fallback.json` | Material Truth | yes per run | Missing/thin material generation plan. |
| `generated_provider_packet.json` | Material Truth | handoff | Provider jobs and target files. |
| `generated_material_review.json` | Material Truth | yes | Promotion from candidate to accepted/rejected. |
| `material_delta.json` | Coverage Gate | yes per current inputs | Fresh calculation; stale artifact is never trusted by BUILD. |
| `revision_decisions.json` | Coverage Gate | yes if used | Human/agent accepted decisions. |
| `revised_segment_contract.json` | Coverage Gate | yes if produced | Must be re-gated before BUILD. |
| `generated_mv_script.json` | BUILD Planning | derived | Runtime script from contract. |
| `timeline_build.json` | Official Render | canonical for rendered output | Timeline actually rendered. |
| `final.mp4` | Official Render | yes | Canonical delivery candidate. |
| `subtitles.srt` | Official Render | yes | Delivery subtitle artifact. |
| `verify_result.json` | Verify | yes | Delivery quality evidence. |
| `preview_timeline.json` | Workbench | projection | Draft preview source. |
| `timeline_patch.json` | Workbench | draft | Human/agent draft edits. |
| `patched_draft_timeline.json` | Workbench | draft | Not official unless routed back. |
| `workbench_contract_patch.json` | Workbench | suggestion | Must be reviewed/applied via backend route. |
| `effect_intent_plan.json` | Effects | yes | Backend-neutral effect intent. |
| `remotion_prompt_pack.json` | Effects | handoff | Optional adapter jobs. |
| `remotion_effect_review.json` | Effects | review | Accepted/rejected adapter outputs. |
| `remotion_composite_draft_report.json` | Effects | draft report | Non-canonical unless promoted by route. |

## Legacy Name Mapping

| Legacy name | Canonical route name | Keep / migrate policy |
|---|---|---|
| M6 | Material Truth + Coverage Gate | Keep as historical implementation phase; document as material-map lifecycle. |
| VD1 / VD2 | Material/BUILD visual diversity | Keep as internal capability names. |
| SRP1 | Segment Sequence Planner | Keep as BUILD planning internals. |
| SRP2 | Opening / Hook Planner | Keep as BUILD planning internals. |
| SRP3 | Story Arc Planner | Keep as BUILD planning internals. |
| FX1-FX4 | Effects Route increments | Keep until effects route stabilizes. |
| Node14 | Brownfield Edit / Finishing Route | Use Brownfield Edit as canonical label; Node14 remains compatibility alias. |
| Dashboard | Review surface | Keep. |
| Workbench | Draft edit surface | Keep. |

Do not mass-rename code yet. Use this mapping in docs and UI labels first.

## Stable Routes Already Proven

### Existing material route

Evidence:

- M6e real 67th acceptance.
- 67th fuller replay: real footage, 12 needs/segments, 65s output, contact sheet
  and drift reporting.

Known gaps:

- shot-aware window selection / black-transition avoidance remains a quality
  improvement for raw event footage.
- visual family labels are not always available for older real footage, so VD2
  may degrade to deterministic ordering.

### Generated storybook route

Evidence:

- `docs/decisions/2026-06-20-snow-white-generated-storybook-e2e.md`
- Cinderella and Snow White `.tmp` validation runs.

Known gaps:

- camera language in generated panels is still weak unless prompts are more
  director-specific;
- character/style consistency should be strengthened in provider packets;
- pacing should be template-controlled, not one duration everywhere by default.

### Workbench draft route

Evidence:

- Native preview engine and frontend API hardening decisions.
- Workbench can preview composition, edit timing/subtitles/audio/effect markers,
  save draft patches, and export non-canonical previews.

Known gaps:

- Workbench visual preview is not final parity;
- effect preview is approximate by design unless a deterministic effect renderer
  is adopted;
- source replacement and material organization should remain material-map aware.

## Template Route Plan

Templates should be layered on top of the canonical route.

Priority template families:

1. `storybook-generated-panels`
   - For children's stories, moral lessons, fairy tales.
   - Uses generated material fallback heavily.
   - Requires character/style bible and panel-locked pacing.
2. `event-graduation-documentary`
   - For training/course/graduation films.
   - Uses real material map, voiceover, MV sections, speeches, and life moments.
   - Requires material richness and visual family tagging.
3. `training-explainer`
   - For procedure/course explanation.
   - Uses narration, diagrams, highlight effects, subtitles.
   - Requires proof-preserving material and clear segment function.
4. `comic-recap`
   - For generated or illustrated recap videos.
   - Uses panels, subtitles, light motion, optional TTS.
   - Needs stronger shot/panel grammar than generic storybook.
5. `effects-finishing`
   - For post-review polish.
   - Uses Brownfield Edit and effect adapters.
   - Must not change material truth unless routed back through material map.

## Review Checklist For New Routes

Before adding a new route or template, answer:

1. What is the narrative device?
2. Who is the audience?
3. What are the must-have beats?
4. What material evidence is required?
5. What can be generated, and what must be real?
6. Which artifacts prove coverage?
7. Which tool performs official BUILD?
8. Which verify/audit decides pass/fail?
9. What can Workbench edit without changing truth?
10. What sends the route back to material map or Brownfield Edit?

## Current Recommendation

Use this canonical route as the stable planning surface now.

Do not perform broad node/file renaming yet. Instead:

1. Update user-facing docs and dashboard labels to show canonical route names.
2. Keep legacy labels as aliases where tests/code still use them.
3. Build new templates against this route.
4. Only rename internals after the frontend and backend both consume this route
   consistently.

