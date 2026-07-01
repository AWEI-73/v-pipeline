# Stage Boundary Matrix

Status: active boundary contract for bounded workers.

This file defines the route boundaries for worker mode. It covers the current
route lines:

- Main Pipeline
- Material Map Branch
- Effect Factory Branch
- Soundtrack / Audio Branch
- Subtitle / Voiceover Branch

## Worker Mode vs Maintainer Mode

**worker mode** means a bounded agent is executing one route task packet, one
stage, or one explicit artifact repair. It may write only run-folder artifacts
listed in `allowed outputs`.

**maintainer mode** means the user explicitly asks to change framework rules,
source code, docs, skills, tests, or tools. Maintainer mode requires its own
task and verification. A worker must not silently switch into maintainer mode.

Global forbidden writes for worker mode:

- `.git/` and commits;
- `skills/`;
- `docs/`, except a path explicitly listed in `allowed outputs`;
- `video_pipeline_core/`;
- `tools/`;
- `tests/`;
- `dashboard/`;
- `RUNBOOK.md`, `roadmap.md`, and repository metadata.

If a worker needs any of those paths changed, it must return `blocked` or
`needs_context` and report the requested maintainer change.

## Main Pipeline

| stage | owner | allowed outputs | forbidden writes | done gate | stop gate | next handoff |
|---|---|---|---|---|---|---|
| Video Intent Planner | `video-intent-planner.md` | `video_intent.json`, `project_brief.json`, `project_brief.md`, `interaction_log.md` | BUILD/render artifacts, repo docs/skills/source/tests | `video_intent.json` is canonical and `required_followup_questions=[]` | missing route-changing facts | Material Map, Structure route, or ask follow-up |
| Story / Structure Planner | `story-soul-blueprint.md`, `writer.md`, `director.md` | `story_soul_blueprint.json`, `screenplay_beats.json`, `director_shot_plan.json` | material truth, timeline, final render | story function and beat purposes are explicit | story lacks narrative device or material needs | Spec / Contract Compile |
| Spec / Contract Compile | `spec-contract.md`, `director.md` | `material_needs.json`, `segment_contract.json`, `effect_intent_plan.json` | material map truth, `final.mp4` | schema-valid contract and needs | must-have needs are vague or untestable | Material Truth / Coverage |
| BUILD Planning | `editor.md`, `audio-director.md`, `subtitle-director.md` | `generated_mv_script.json`, `timeline_build.json`, `sfx_cues.json` | `final.mp4`, material truth, repo source | accepted material windows only | GAP, unrenderable windows, stale contract | Official Render |
| Official Render | `editor.md` / parent runner | `final.mp4`, `subtitles.srt`, `artifact_manifest.json`, `state.json` | route decisions, material truth | render plus manifest exists | renderer fails or gate blocks | Verify |
| Verify / Reviewer Layer | `verify.md` | `verify_result.json`, audit reports, `review_report.md`, `contact_sheet.jpg` | timeline/material truth unless routed back | findings classified and next action clear | factual/material failure or delivery failure | Material Map, Brownfield, or Delivery |
| Workbench Draft Review | `dashboard.md`, `brownfield-edit.md` | `preview_timeline.json`, `workbench_revision_request.json`, `timeline_patch.json`, `patched_draft_timeline.json`, `workbench_contract_patch.json` | canonical timeline, material map, final render | draft patch is validated | patch changes truth or lacks review | Brownfield or main route review |
| Delivery | `route.md`, `verify.md` | `delivery_notes.md`, `run_layout.json` | source code, route rules | complete-video validation passes | any required stream/evidence/reviewer state missing | complete |

## Material Map Branch

| stage | owner | allowed outputs | forbidden writes | done gate | stop gate | next handoff |
|---|---|---|---|---|---|---|
| Material Inventory | `material-map.md`, `curator.md` | per-asset `.map.json`, `materials_db.json`, `material_inventory.md` | story contract rewrite, `final.mp4`, repo source | source files are inventoried with stable ids | source folder missing or unreadable | Map Review |
| Map Review Apply | `material-map.md` | `material_map_review_verdict.json`, reviewed `project_material_map.json` | inventing satisfies edges without review | accepted/rejected scene-to-need decisions are explicit | uncertain content or unsupported reviewer claim | Material Delta |
| Material Delta | `gap-analyzer.md` | `material_delta.json`, `shooting_brief.json` | BUILD/render artifacts | coverage/thin/missing is computed from accepted evidence | must-have gaps without fallback/waiver | Revision, generation, reshoot, or BUILD handoff |
| Generated Candidate Return | `generated-material-producer.md` | generated asset manifests, generated maps, `generated_material_review.json` | treating generated output as real proof | candidates are imported and explicitly reviewed | provider outputs unmapped or quality failed | Fresh Material Delta |
| Material Build Handoff | `material-map-lifecycle` | `material_map_lifecycle.json`, build handoff refs | `segment_contract.json` rewrites not backed by decisions | `can_build=true` and refs exist | stale delta, dangling needs, invalid waivers | Main Pipeline BUILD |

## Effect Factory Branch

| stage | owner | allowed outputs | forbidden writes | done gate | stop gate | next handoff |
|---|---|---|---|---|---|---|
| Effect Intent Clarification | `video-effect-factory.md`, `effects-director.md` | `effect_design_map.json`, `visual_technique_plan.json` | material truth, final render, repo source | story function, role, family, controls are visible | fuzzy effect request with no reviewable controls | Effect Contract |
| Effect Contract | `video-effect-factory.md` | `effect_contract.json`, confirmed technique plan | segment story facts, material map | visual primitives, motion primitives, controls, negative rules, backend policy exist | required effect is unbuildable or unsafe | Worker Handoff |
| Worker Handoff | `remotion-effect-worker.md` or light backend | `remotion_prompt_pack.json`, bounded worker packet | `final.mp4`, `segment_contract.json`, material truth | worker input is bounded and references reviewed material only | unsupported family or missing refs | Worker Outputs |
| Worker Outputs / Review | `remotion-effect-worker.md`, `video-effect-factory.md` | `remotion_worker_outputs.json`, preview/contact sheet, `effect_review.json` | canonical delivery, material coverage | output matches contract with evidence refs | no evidence, unreadable text, generic template collapse | Effect Handoff |
| Effect Handoff | `video-effect-factory.md` | `effect_handoff.json`, `remotion_effect_handoff.json` | final assembly ownership | assets are bounded and non-final | effect changes story/material truth | Workbench/Brownfield or BUILD return |

## Soundtrack / Audio Branch

| stage | owner | allowed outputs | forbidden writes | done gate | stop gate | next handoff |
|---|---|---|---|---|---|---|
| Soundtrack Intent Arrange | `soundtrack-arranger.md` | `soundtrack_plan.json`, `music_source_candidates.json`, `sound_license_manifest.json`, `audio_director_handoff.json` | `final.mp4`, canonical timeline, repo source | song/BGM/mixed role, source policy, fallback policy, and license state are explicit | role fallback changes promise without review, source/license unknown | Audio Handoff Review |
| Audio Handoff Review | `soundtrack-arranger.md`, `audio-director.md` | `audio_handoff_acceptance.json`, `audio_mix_plan.json` | downloading unlicensed audio, final render | selected audio is accepted or blocked with explicit reason | missing license/source, missing speech preservation/ducking decision | Audio Mix or user review |
| Audio Mix / BUILD Handoff | `audio-director.md` | `final_audio.wav`, `audio_mix_report.json`, `audio_build_handoff.json` | replacing video render, rewriting Stage 0 | mix evidence exists and BUILD can consume the handoff | mix failed, voice/original audio not preserved, section placement invalid | Main Pipeline BUILD |

## Subtitle / Voiceover Branch

| stage | owner | allowed outputs | forbidden writes | done gate | stop gate | next handoff |
|---|---|---|---|---|---|---|
| Subtitle / Voiceover Intent | `subtitle-director.md`, `audio-director.md` | `subtitle_voiceover_contract` in `video_intent.json`, subtitle/voiceover plan | material truth, final render | language, subtitle requirement, narration requirement, and fallback policy are explicit | whole-video language or narration requirement is route-changing and unknown | Spec / BUILD Planning |
| Subtitle / Narration Execution | `subtitle-director.md`, `audio-director.md` | `subtitles.srt`, `narration_manifest.json`, `voiceover_provider_plan.json`, `subtitle_voiceover_build_handoff.json`, TTS/voiceover manifests | route decisions, material truth | required text/audio assets exist and are UTF-8/readable; VoxCPM is a thin local provider under Audio Director, run through `voxcpm_runtime_check.py` then `tools/voxcpm_voiceover_provider.py` or generic `voiceover-provider-plan`, and records provider readiness | missing narration audio, unreadable subtitles, language mismatch, provider unavailable without explicit fallback/defer | Verify / Delivery |
| Caption / Voice Review | `verify.md`, `subtitle-director.md`, `audio-director.md` | caption audit, narration/audio review notes | canonical story/material truth | readability and audio evidence are present | clipped subtitles, wrong language, unusable narration | Brownfield or Delivery |
