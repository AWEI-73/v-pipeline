# Stage 0-10 Route Alignment Construction Plan

Date: 2026-06-27
Status: active construction guide

This guide keeps Hermes from growing into many competing routes. The target is
one main Stage 0-10 spine, with side branches expressed as child contracts and
bounded handoffs.

## Alignment Rule

Do not merge every branch into one giant contract. Do not create independent
routes for every feature. Use this structure:

```text
Stage 0 Video Intent Planner
  -> main route decision: material-first | structure-first | needs-context
  -> child contracts:
     material_contract
     soundtrack_contract
     effect_policy
     subtitle_voiceover_contract
  -> Stage 1-10 main spine
```

Child contracts are requests and constraints, not permission to skip the main
route. A child branch may produce its own artifacts, but BUILD and Delivery must
consume only accepted handoffs.

## Canonical Stage 0-10 Spine

| stage | purpose | branch hooks |
|---|---|---|
| 0 Video Intent Planner | Decide goal, audience, target length, input state, entry path, follow-up gaps, and child intents. | Writes `material_contract`, `soundtrack_contract`, `effect_policy`, and reserved `subtitle_voiceover_contract`. |
| 1 Story / Structure Planner | Turn the brief into story structure, teaching structure, recap arc, or other video skeleton. | Uses Stage 0 intent; does not inspect material as truth unless Material Map returned evidence. |
| 2 Director Shot Plan / Spec Compile | Convert structure into segment-level needs, subtitles/audio/effect intents, and `segment_contract.json`. | Expands child contracts into segment-level material, soundtrack, effect, subtitle, and voiceover needs. |
| 3 Material Truth | Inventory, review, generate/import candidates, and attach evidence to needs. | Material Map owns accepted scene-to-need evidence. Generated material returns here as candidate material. |
| 4 Coverage / Decision Gate | Decide build, revise, generate, reshoot, rewrite, drop, or waive. | Material delta and lifecycle own readiness; no branch may bypass this gate. |
| 5 BUILD Planning | Convert accepted material and accepted branch handoffs into timeline, audio cues, subtitle plan, and effect markers. | Consumes `audio_build_handoff`, `effect_handoff`, subtitle/voiceover handoff, and accepted material windows. |
| 6 Official Render | Produce canonical render through backend renderer. | Renderer may mix audio, burn subtitles, and include accepted effect assets only. |
| 7 Verify / Reviewer Layer | Check technical quality, content alignment, readability, audio, and delivery readiness. | Delivery gate must surface material, subtitle, audio, and effect semantic failures, not only `verify_result.pass`. |
| 8 Workbench Draft Review | Let human/agent inspect and draft patches for clips, timing, subtitles, audio, and effect markers. | Workbench is draft authority only; patches return to owning branch or BUILD. |
| 9 Brownfield Edit / Finishing | Apply bounded reviewed fixes after verify/review. | Small material replacement returns to Material Map; audio/subtitle/effect fixes return to their branch or BUILD handoff. |
| 10 Delivery | Ship final artifacts only with complete evidence and no unresolved blocks. | Requires accepted media manifests, readable reports, and branch evidence when branch work was planned. |

## Branch Contract Boundaries

### Material Map Branch

Stage 0 writes `material_contract`; Stage 3 owns the evidence. This branch
answers what material exists, what it can prove, what is missing, and what can
be built. It may create generated/reshoot/rewrite/waiver tasks, but BUILD must
wait for a fresh material delta or accepted handoff.

Primary artifacts:

- `materials_db.json`
- per-asset `.map.json`
- `project_material_map.json`
- `material_map_review_verdict.json`
- `material_delta.json`
- `material_map_lifecycle.json`

### Soundtrack / Audio Branch

Stage 0 writes `soundtrack_contract`. Soundtrack Arranger owns semantic music,
song, BGM, source, license, fallback, and Audio Director handoff. Audio Director
owns actual mixing, ducking, voice preservation, and `final_audio.wav`.

Primary artifacts:

- `soundtrack_plan.json`
- `music_source_candidates.json`
- `sound_license_manifest.json`
- `audio_director_handoff.json`
- `audio_handoff_acceptance.json`
- `audio_mix_plan.json`
- `final_audio.wav`
- `audio_mix_report.json`
- `audio_build_handoff.json`

### Effect Factory Branch

Stage 0 writes `effect_policy`; Stage 2/9 may expand it into concrete effect
contracts. Effect Factory owns effect design language and worker handoff.
Remotion worker is a backend worker, not the route owner.

Primary artifacts:

- `effect_intent_plan.json`
- `effect_design_map.json`
- `effect_contract.json`
- `remotion_prompt_pack.json`
- `remotion_worker_outputs.json`
- `effect_review.json`
- `effect_handoff.json`
- `effect_render_verification.json`

### Subtitle / Voiceover Branch

This branch is reserved as a child contract surface until the dedicated route is
hardened. Today, subtitle and voiceover intent mostly lives in Stage 2/5 BUILD
contracts and in Subtitle Director / Audio Director execution. Stage 0 should
record whole-video language and voiceover intent so later tools do not guess.

Primary artifacts:

- `subtitle_voiceover_contract` in `video_intent.json`
- subtitle plan or `subtitles.srt`
- `narration_manifest.json`
- voiceover or TTS manifests when required
- `subtitle_voiceover_handoff_acceptance.json`
- `subtitle_voiceover_build_handoff.json`
- caption/readability audit outputs

## Construction Sequence

1. **Spec alignment.** Update canonical route docs, boundary matrix, RUNBOOK,
   and skill docs so they all describe the same spine and child contract model.
2. **Stage 0 contract threading.** Keep `material_contract`,
   `soundtrack_contract`, `effect_policy`, and reserved
   `subtitle_voiceover_contract` visible in dashboard state, material-first
   acceptance, and `pipeline_home.py`.
3. **Stage 1/2 expansion.** Convert Stage 0 child intents into segment-level
   needs without letting them bypass material truth or branch review. Current
   minimum implementation preserves `stage0_child_contracts` through
   `story_soul_blueprint`, `director_shot_plan`, `material_needs`, and
   `blueprint_to_contract` / `segment_contract`. Story Soul output now has a
   direct bridge:
   `video_tools.py story-soul-to-contract --story-dir RUN_DIR\story_blueprint --out RUN_DIR\segment_contract.json`,
   so agents do not need to hand-author a parallel decisions file just to reach
   Node 3.
4. **Stage 3/4 material gate.** Treat material evidence and coverage as the
   authority for real/generative material readiness. Accepted scene-to-need
   edges and reviewed usable ranges must survive into `rough_cut_plan.json` and
   `timeline_build.json`; timeline clips should carry `scene_id`, `asset_id` or
   `material_map_id`, and `need_id` so BUILD, Workbench, and delivery gates can
   verify what material truth each clip claims. If the reviewed usable range is
   shorter than the segment request, `rough_cut_plan` must emit a gap with the
   requested, selected, and missing seconds; do not silently shrink the film and
   report `ok=true`. Still images/photos can hold for the requested duration,
   but must keep trace fields so Workbench and review can judge fatigue/reuse.
5. **Stage 5 build handoff.** Let BUILD consume accepted material windows,
   accepted audio handoff, accepted effect handoff, and subtitle/voiceover
   plans as separate lanes. Current minimum implementation preserves
   `stage0_child_contracts` from `segment_contract.json` into
   `generated_mv_script.json` / runtime payload so BUILD planning and Workbench
   can see the upstream intent before accepted branch handoffs exist. Required
   subtitles/voiceover can now be accepted through
   `subtitle_voiceover_handoff_acceptance.json` and promoted to
   `subtitle_voiceover_build_handoff.json` without rendering video. Dry and
   official BUILD manifests must keep accepted branch handoffs visible through
   `artifact_manifest.json`, including `rough_cut_plan.json`,
   `audio_build_handoff.json`, `subtitle_voiceover_build_handoff.json`, and
   `effect_handoff.json` when they exist. `rough_cut_plan.json` remains owned by
   Material Map / Coverage; BUILD lists it as input evidence and must not
   silently replace it.
6. **Stage 7/10 gate evidence.** Delivery must report branch-specific blocking
   reasons even when `verify_result.json` is technically true. Current minimum
   implementation makes `evaluate_delivery_gate()` read
   `stage0_child_contracts` from `segment_contract.json` / runtime payload and
   block missing soundtrack, subtitle, voiceover, or required-effect evidence.
   Required-effect evidence may come from `effect_render_verification.json`,
   accepted `effect_handoff.json`, or accepted `remotion_effect_handoff.json`.
   Material timeline validation must compare each timeline clip against
   `segment_contract.material_map_ids` and `material_fit.need_refs`, using direct
   timeline fields first and falling back to `project_material_map.json` by
   `scene_id`. `tools/write_delivery_gate_report.py` should persist the current
   gate as `delivery_gate.json`; dashboard state should surface that persisted
   report separately from the in-memory `delivery_gate` evaluation so reviewers
   can inspect the exact report handed to the next agent.
7. **Workbench route-back.** `workbench_handoff.json` is draft-only evidence.
   It must carry `route_back` so the dashboard and agent know which owner
   reviews the patch before promotion:
   `material-map` for clip replacement/insertion, `build-planning` for timing
   and source-window changes, `subtitle-director` for subtitle patch,
   `audio-director` for cue/mix patch, and `effect-factory` for effect patch.
8. **Workbench visibility.** UI should display Chinese labels and human-readable
   contract cards from the same artifacts, not separate front-end truth.

## Tests To Keep Green

- Stage 0: `tests.test_video_intent_planner`
- Stage 1/2 expansion: `tests.test_story_soul_blueprint`,
  `tests.test_blueprint_to_contract`
- Stage 5 BUILD handoff: `tests.test_contract_adapter`
- Stage 7/10 delivery evidence: `tests.test_delivery_gate`,
  `tests.test_delivery_gate_report`
- Material acceptance: `tests.test_material_first_boundary_acceptance`
- Soundtrack/audio: `tests.test_soundtrack_arranger`,
  `tests.test_soundtrack_flow_acceptance`, `tests.test_audio_handoff_acceptance`
- Subtitle/voiceover: `tests.test_subtitle_voiceover_handoff`
- Route/home/dashboard: `tests.test_pipeline_home`,
  `tests.test_dashboard_state`
- Docs alignment: `tests.test_stage_boundary_matrix`,
  `tests.test_canonical_route_acceptance`

## Stop Conditions

Stop and route back instead of continuing when:

- Stage 0 has route-changing unknowns.
- Material exists but has no accepted material map evidence.
- Generated material has no import/review result.
- Song/BGM fallback changes the user-facing promise without review.
- Required effects have no reviewable effect contract or rendered evidence.
- Subtitle/voiceover intent is required but no readable artifact or manifest
  exists.
- Workbench patch changes material truth without returning to the owning branch.
- Workbench has `route_back` entries but dashboard/agent tries to continue
  BUILD or final review without owner acceptance.
