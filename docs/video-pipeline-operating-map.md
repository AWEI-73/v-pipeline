# Video Pipeline Operating Map

Date: 2026-06-25
Status: current operator manual / route-to-tool map

This is the practical operating manual for agents. It maps every stable pipeline
stage to the skill to read, Python/JS tools to call, expected artifacts, gates,
and return routes.

Use this with:

- `docs/canonical-video-pipeline-route.md` for canonical stage names.
- `docs/upstream-story-route.md` for the complete upstream line before Material
  Truth.
- `docs/artifact-reviewer-map.md` for lightweight route-driven review policy.
- `docs/material-map-lifecycle.md` for material truth details.
- `docs/effect-factory-route.md` for the designed-effects side branch.
- `docs/build-capability-alignment.md` for which declared capabilities actually
  change BUILD output.
- `docs/route-orchestrator-harness.md` when multiple agents execute the route
  through bounded task packets.

## Operating Rules

1. **Contract first.** Do not let UI drafts, generated files, or stale reports
   become truth.
2. **Fresh gates.** BUILD must recompute material delta / revision gates from
   current inputs.
3. **Generated assets are candidates.** They must return through material-map
   review before satisfying needs.
4. **Workbench is draft-only.** It may write patches and draft exports, never
   canonical `timeline_build.json`, `project_material_map.json`, or `final.mp4`.
5. **Effects are adapters.** `effect_intent_plan.json` is backend-neutral;
   ffmpeg, Remotion, and future engines are adapter routes.
   Use `video-effect-factory.md` when effects need design collection,
   contracts, worker handoff, review, and bounded asset promotion. Use
   `remotion-effect-worker.md` only as the lower Remotion backend.
6. **Reviewer policy is route-driven.** Do not review every artifact by default;
   use `light`, `normal`, or `deep` from `docs/artifact-reviewer-map.md`.
   Use `python video_tools.py reviewer-policy --level LEVEL` to materialize the
   reviewer/eval packet for a route.
   Use `python video_tools.py reviewer-flow-acceptance --level LEVEL` after
   changing reviewer policy or role wiring.
7. **Verify before delivery.** A video path alone is not delivery.
8. **Agent packets are bounded.** For multi-agent runs, use
   `route-task-next` / `route-task-accept`; the harness validates artifacts,
   freshness, and `must_not_touch` hashes instead of trusting status prose.

## Full Route Map

| Stage | Stable name | Main decision | Skill(s) | Tool entrypoints | Main artifacts | Pass / stop rule | Return route |
|---|---|---|---|---|---|---|---|
| 0 | Video Intent Planner | What are we making, for whom, with what inputs? Decide `input_state` and choose `entry_path`: material-first, structure-first, or needs-context before deeper story/build work. `Intake` is the legacy label. | `video-intent-planner.md`, `video-workflow.md`, `video-pipeline.md`, `route.md` | `video-intent-plan`, `project-init`, `project-new-run`, `commands-manifest`, `workflow-manifest` | `video_intent.json`, project brief, run folder | Stop if audience, goal, input state, material/text availability, generation permission, or handoff changes the plan. | Back to user / brief refinement |
| 1 | Story Soul | What is the narrative device and emotional spine? | `story-soul-blueprint.md`, `blueprint-interview.md`, `writer.md` | `story-soul-blueprint`, `story-soul-to-contract`, `blueprint-coverage`, `blueprint-compile`, `blueprint-to-contract` | `story_soul_blueprint.json`, screenplay beats, director shot plan, `segment_contract.json` bridge | Stop if the output is just a parameter sheet with no conflict/turn/feeling. | Intake / writer refinement |
| 2 | Director Shot Plan | What exact shots, audio, subtitles, effects, and material needs prove the story? | `director.md`, `audio-director.md`, `subtitle-director.md`, `effects-director.md`, `video-effect-factory.md`, `spec-contract.md` | `validate-needs`, `effect-intent-plan`, `spec-review`, `capability-manifest`, `supply-review` | `material_needs.json`, `effect_intent_plan.json`, `effect_design_map.json`, `effect_contract.json`, subtitle/audio intent, `segment_contract.json` | Stop if must-have needs are vague, untestable, unsupported, or if required effects lack a reviewable contract. | Story Soul / Director refinement |
| 3 | Material Truth | What real or generated assets can satisfy each need? | `material-map.md`, `curator.md`, `material-generation-fallback.md`, `generated-material-producer.md` | `project-material-map`, `material-map-lifecycle`, `source-section-map`, `source-motion-profile`, `source-material-matrix`, `material-generation-fallback`, `generated-image-provider-packet`, `codex-imagegen-provider-fill`, `generated-material-import`, `generated-material-review`, `visual-diversity-review`, `visual-family-normalize` | per-asset `.map.json`, `project_material_map.json`, `source_section_map.json`, `source_motion_profile.json`, `source_motion_points.jpg`, `source_material_matrix.json`, `source_material_matrix_contact_sheet.jpg`, `material_generation_fallback.json`, `generated_provider_packet.json`, generated manifests, reviewed map | Stop if maps are dangling, unreviewed, missing must-have evidence, generated candidates are not accepted, or one-long-source highlight windows lack section/motion/matrix evidence. | Material generation / curator review |
| 4 | Coverage Gate | Are needs covered, thin, missing, or broken? | `gap-analyzer.md`, `shooting-brief.md`, `route.md` | `lineage-link`, `material-delta`, `material-revision`, `contract-dry-build`, `contract-run` pre-BUILD gate | `material_delta.json`, `shooting_brief.json`, `revision_decisions.json`, `revised_segment_contract.json` | BUILD only if `delta.ok == true` and `ready_for_build == true`, or accepted revision/waiver re-gates cleanly. | Material Truth / Story revision |
| 5 | BUILD Planning | Which accepted windows become timeline clips, sequence beats, opening, arc, audio/subtitle/effect cues? | `editor.md`, `audio-director.md`, `subtitle-director.md`, `effects-director.md` | `contract-adapt`, `contract-dry-build`, `rank-local`, `match-mv`, `voiceover-provider-plan`, internal VD/SRP planning in `contract-run` | `generated_mv_script.json`, `rough_cut_plan.json`, `timeline_build.json`, `audio_build_handoff.json`, `subtitle_voiceover_build_handoff.json`, `voiceover_provider_plan.json`, `narration_manifest.json`, `effect_handoff.json`, SRP traces, `sfx_cues`, subtitle plan | Stop if planning creates GAP, unrenderable windows, bad window ranges, required voiceover is not ready/deferred, or contract/runtime mismatch. | Material Truth / Coverage Gate |
| 6 | Official Render | Produce the canonical video. | `editor.md` | `contract-run`, `script-run`, `assemble`, `merge-final`, `burnsub`, `mix-audio`, `sfx-mix`, `gen-bgm`, `music-fetch` | `final.mp4`, `subtitles.srt`, `artifact_manifest.json`, `state.json` | Pass only if canonical render path succeeds and artifacts are current. | BUILD Planning / runtime fix |
| 7 | Verify | Does the output match story, material truth, subtitles, audio, and technical constraints? | `verify.md` | `verify`, `verify-evidence`, `final-product-verify`, `timeline-audit`, `broll-audit`, `new-visual-audit`, `black-frame-audit`, `caption-audit`, `keyframe-grid`, `visual-audit`, `semantic-novelty-audit`, `action-progression-audit`, `replay-acceptance` | `verify_result.json`, `final_product_verify_bundle.json`, audit reports, contact sheet, review report | Stop on tier-1 defects; tier-2 findings route to quality/brownfield work. | Material Truth or Brownfield Edit |
| 8 | Workbench Draft Review | Can a human/agent inspect and patch the material composition without changing truth? | `dashboard.md`, `brownfield-edit.md` | `tools/workbench_server.py`, `tools/preview_timeline.py`, `tools/timeline_patch.py`, `workbench-handoff-validate`, `workbench-draft-rerender` | `preview_timeline.json`, `timeline_patch.json`, `patched_draft_timeline.json`, `workbench_contract_patch.json`, draft export | Drafts must not overwrite canonical timeline/map/final. | Brownfield Edit / official rerender |
| 9 | Brownfield Edit / Finishing | What small reviewed fixes or finishing assets are needed after verify/review? | `brownfield-edit.md`, `video-effect-factory.md`, `remotion-effect-worker.md`, `effects-director.md`, `subtitle-director.md`, `audio-director.md` | `effect-revision-request`, `effect-revision-draft`, `effect-revision-apply`, `light-effects-plan`, `remotion-prompt-pack`, `remotion-worker-smoke`, `remotion-worker-outputs`, `remotion-composite-draft`, `workbench-draft-rerender` | `effect_revision_request.json`, `effect_design_map.json`, `effect_contract.json`, `effect_review.json`, `effect_handoff.json`, `remotion_prompt_pack.json`, `remotion_effect_review.json`, non-canonical draft composite | If it changes material truth, return to Stage 3/4. If finishing-only, review the effect handoff, draft/rerender, then verify. | Verify or Material Truth |
| 10 | Delivery | What can be handed off, with what limitations? | `route.md`, `verify.md`, `dashboard.md` | `dashboard`, `state`, `run-layout-validate`, `operator-flow-acceptance` | `final.mp4`, `review_report.md`, `contact_sheet.jpg`, `run_layout.json`, delivery notes | Do not mark complete without output path, verify evidence, and known limitations. | Verify / Brownfield Edit |

## Reviewer Policy

Reviewer Layer is above technical `VERIFY`.

Use it to decide which professional perspective should review an artifact
before the next stage. Keep it lightweight:

| Policy | Reviewers | Use case |
|---|---|---|
| `light` | `material_producer`, `technical_verify` | smoke tests, internal demos, quick iteration |
| `normal` | `story_director`, `material_producer`, `editorial_timeline`, `technical_verify` | most user-facing videos |
| `deep` | `literary_editor`, `story_director`, `material_producer`, `generated_material_art_director`, `editorial_timeline`, `audio_subtitle_reviewer`, `effect_reviewer`, `technical_verify` | story-heavy, generated, formal, or high-risk videos |

Technical `VERIFY` remains deterministic delivery checking. Literary,
screenwriting, director, art, and timeline reviews are creative or editorial
reviews and should usually produce `revise` / `advisory` outcomes, not automatic
delivery hard blocks.

See `docs/artifact-reviewer-map.md`.

Command:

```powershell
python video_tools.py reviewer-policy --level normal --out reviewer_policy_packet.json
python video_tools.py reviewer-flow-acceptance --level deep --scenario all --out reviewer_flow_acceptance.json
```

## Stage Detail

### 0. Intake

Use when the user has only a goal or vague media direction.

Minimum capture:

- target audience;
- desired duration;
- genre/template route;
- input state: `material_available`, `text_available`, `idea_only`, or
  `unknown`;
- entry_path: `material-first`, `structure-first`, or `needs-context`;
- available material path, available text/article/outline/script/story, or
  generated-material permission;
- whether the project is teaching, personal video, event recap, brand, or
  storybook/comic;
- required language/subtitles/voiceover;
- delivery format and review expectations.

Route rule:

- For **material-first** teaching, personal video, event recap, or brand work,
  run material-map early. Existing media is the story source and constraint;
  generation is fallback for diagrams, chapter cards, symbolic bridges, or
  missing non-proof visuals.
- For **structure-first** generated storybook/comic/story/teaching work, the
  structure route can lead, then `material_needs.json` drives generated or
  captured material.
- For **needs-context**, ask focused questions first; do not start Story Soul,
  Material Truth, generated fallback, or BUILD.
- `existing-material-first` maps to `material-first`; `story-first` maps to
  `structure-first`; hybrid is not a primary Stage 0 entry path. Partial
  material enters `material-first`, then `material_delta.json` decides which
  beats are covered, missing, generated, reshot, rewritten, dropped, or waived.

Useful commands:

```powershell
python video_tools.py project-init ...
python video_tools.py project-new-run ...
python video_tools.py video-intent-plan project_brief.json --out video_intent.json
python video_tools.py video-intent-acceptance --out video_intent_acceptance.json
python video_tools.py commands-manifest
python video_tools.py workflow-manifest
```

Stage 0 artifact ownership:

- `project_brief.json` / `brief.json` is raw input.
- `video_intent.json` is the canonical Stage 0 input-state / entry-path
  decision.
- `route_decision.json` is legacy/compat unless a current harness explicitly
  requires it.
- `input_state` records `material_available`, `text_available`, `idea_only`, or
  `unknown`.
- `entry_path` records `material-first`, `structure-first`, or `needs-context`;
  hybrid is not a primary Stage 0 entry path.

Multi-agent packet route:

```powershell
python video_tools.py route-task-next RUN_DIR --out route_subagent_task.json
python video_tools.py route-task-accept --task route_subagent_task.json --result route_subagent_result.json --state-out route_orchestrator_state.json
python video_tools.py route-orchestrator-acceptance RUN_DIR --route existing-material-first --stage-count 4 --out route_orchestrator_acceptance.json
```

Do not start BUILD here.

### Upstream Line Before Material Truth

Use `docs/upstream-story-route.md` when the project needs narrative quality,
generated material, a fairy-tale/comic route, or an event film with emotional
framing.

Stable order:

```text
Role / Literary Lens
  -> Blueprint Interview
  -> Story Soul Package
  -> Director Shot Plan
  -> Contract Compile
  -> Material-Ready Handoff
```

This line is complete only when it produces or validates:

- `blueprint.md` / `blueprint.json` when prose blueprint is used;
- `story_soul_blueprint.json` or the split story-world/concept/beat artifacts;
- `director_shot_plan.json`;
- `segment_contract.json`;
- `material_needs.json`;
- optional `effect_intent_plan.json`;
- selected `review_policy`.

After that, enter Material Truth. Do not let Story Soul skip the material-map
stage.

### 1. Story Soul

Purpose: prevent technically valid but soulless videos.

Inputs:

- project brief;
- audience;
- moral/theme;
- style;
- rough duration.

Outputs:

- `story_world`;
- `creative_concept`;
- `screenplay_beats`;
- `director_shot_plan`;
- `material_needs`;
- `generation_manifest`;
- review checklist.

Tool:

```powershell
python video_tools.py story-soul-blueprint brief.json --out-dir out
python video_tools.py story-soul-to-contract --story-dir out --out segment_contract.json
```

Quality checks:

- each beat has `conflict_or_turn`;
- each beat has `sensory_anchor`;
- each beat has `intended_viewer_feeling`;
- each shot has `director_intent`.

### 2. Director Shot Plan / Contract

Purpose: turn story into executable requirements.

Key artifacts:

- `segment_contract.json`;
- `material_needs.json`;
- `effect_intent_plan.json`;
- subtitle/audio intent.

Useful commands:

```powershell
python video_tools.py validate-needs material_needs.json
python video_tools.py effect-intent-plan ...
python video_tools.py spec-review segment_contract.json ...
python video_tools.py contract-dry-build segment_contract.json ...
```

Stop if:

- a must-have need lacks a clear purpose;
- a need has no count/fallback policy;
- effect intent is backend-specific too early;
- subtitles/voiceover language is unclear.

If an effect is story-significant or user-requested, route it through Effect
Factory before worker build:

```text
effect_intent_plan.json
  -> effect_design_map.json
  -> effect_contract.json
  -> backend handoff
```

Read `skills/video-effect-factory.md` for the contract shape. Do not send vague
phrases like "make it cooler" directly to a worker.

### 3. Material Truth

Purpose: prove what material exists and what each scene can satisfy.

Real material route:

```powershell
python video_tools.py project-material-map --maps-dir maps --out project_material_map.json
python video_tools.py material-map-lifecycle --out-dir run --needs material_needs.json --material-db materials_db.json --contract segment_contract.json
```

One-long-source highlight route:

```powershell
python video_tools.py source-section-map --video source.mp4 --out run\source_section_map.json --soundtrack-probe run\source_soundtrack_probe_report.json
python video_tools.py source-motion-profile --video source.mp4 --out-dir run\source_motion_profile --soundtrack-probe run\source_soundtrack_probe_report.json --sample-sec 1
python video_tools.py source-material-matrix --source source.mp4 --out-dir run\source_matrix --window-sec 12
python video_tools.py source-dialogue-script --json3 run\source\subs.en.json3 --out-dir run\dialogue_script --rough-windows run\rough_dialogue_windows.json --target-sec 90
python video_tools.py source-highlight-plan --source source.mp4 --out-dir run --target-sec 75
python tools\safe_highlight_cut.py --rough-cut-plan run\rough_cut_plan.json --out run\single_source_highlight_preview.mp4 --report run\highlight_cut_report.json
python video_tools.py final-product-verify run\single_source_highlight_preview.mp4 --out-dir run\final_product_verify
python tools\write_delivery_gate_report.py --run run --json
python tools\package_verified_preview.py --run run --json
python tools\verified_preview_review_decision.py --run run --decision accept_promote --reviewer operator --json
python tools\promote_verified_preview.py --run run --reviewer operator --json
python tools\write_delivery_gate_report.py --run run --json
```

Use `source_section_map.json`, `source_motion_profile.json`,
`source_motion_points.jpg`, `source_material_matrix.json`, and
`source_material_matrix_contact_sheet.jpg` before selecting highlight windows.
The section map is the big structure pass, the motion profile is local
edit-point evidence, and the matrix is the eye/ear review pass: visual windows
plus extracted source audio and `source_soundtrack_probe_report.json`. Do not
treat a purely time-based `source_highlight_plan.py` output as enough evidence
for practical, training, ending, speech, music, or event-content selection.
For dialogue/podcast/interview routes, use `source-dialogue-script` after a
correct subtitle or reviewed ASR transcript is available. The soft target
duration must not override complete sentence boundaries or natural speech flow.
Package and promote only after preview verification: `delivery_candidate.mp4`
is reviewable, `verified_preview_review_decision.json` records the explicit
accept/revise/rebuild/reject decision, `final.mp4` exists only after
`accept_promote` plus explicit promotion, and the final delivery gate must pass
after promotion.
If the operator chooses `revise_workbench`, the review decision writes
`workbench_revision_request.json`; rebuild `workbench_handoff.json` so the
Workbench/Brownfield agent reads `preview_timeline.json`, the revision request,
and any review report before drafting patches. This is a draft-only repair path
and must not write `final.mp4`.

Generated material route:

```powershell
python video_tools.py material-generation-fallback --material-delta material_delta.json --out material_generation_fallback.json
python video_tools.py generated-image-provider-packet --fallback material_generation_fallback.json --out generated_provider_packet.json
python video_tools.py generated-material-import --provider-outputs provider_outputs.json --out-dir generated_material
python video_tools.py generated-material-review --project-map generated_project_material_map.json --decisions review_decisions.json --out reviewed_project_material_map.json
```

Visual diversity / label route:

```powershell
python video_tools.py visual-diversity-review ...
python video_tools.py visual-family-normalize ...
python video_tools.py visual-diversity-coverage ...
```

Rules:

- Generated files are candidates until `generated-material-review` accepts them.
- `project_material_map.json` is a projection, not a second truth source.
- If new material is added, rerun material map / delta. Do not patch coverage by hand.

### 4. Coverage / Revision Gate

Purpose: decide whether the project can build.

Commands:

```powershell
python video_tools.py lineage-link ...
python video_tools.py material-delta --needs material_needs.json --project-map project_material_map.json --out material_delta.json
python video_tools.py material-revision --contract segment_contract.json --delta material_delta.json --decisions revision_decisions.json ...
```

Decision outcomes:

- `covered`: enough accepted/candidate renderable evidence.
- `thin`: some evidence but below count.
- `missing`: none.
- `excess`: more than needed.
- `invalid`: broken references or malformed inputs.

Gate rule:

```text
delta.ok == true AND delta.ready_for_build == true
```

If false:

- collect/reshoot/generate material;
- shorten/rewrite/drop segment;
- explicit waiver only when appropriate;
- never silently substitute wrong material.

### 5. BUILD Planning

Purpose: select material and create the actual render plan.

Core capabilities currently active:

- need-aware material retrieval;
- shot-aware bad-window avoidance via `avoid_ranges` / `bad_ranges`;
- photo map-ranked renderability;
- VD2 visual diversity soft selection;
- SRP1 segment sequence planner;
- SRP2 opening/hook planner;
- SRP3 story arc allocation hints;
- KBF1 stable still-photo motion.

KBF1 owner: BUILD renderer (`video_pipeline_core/mv_cut.py`). Still photos must
render through a 30fps input loop and 4K dynamic scale/crop/downsample path.
Do not reintroduce ffmpeg `zoompan` for canonical photo motion; it has known
jitter with animated x/y. Long stills should prefer `hold` or restrained center
push over very slow pan, because sub-pixel pan can read as stepping.

Commands:

```powershell
python video_tools.py contract-adapt ...
python video_tools.py contract-dry-build ...
python video_tools.py rank-local ...
python video_tools.py match-mv ...
```

Most BUILD planning is invoked through:

```powershell
python video_tools.py contract-run segment_contract.json --material-db materials_db.json --music bgm.mp3 --out final.mp4 --mat-dir run
```

Do not bypass `contract-run` gates for official output.

### 6. Official Render

Purpose: create canonical `final.mp4`.

Commands:

```powershell
python video_tools.py contract-run ...
python video_tools.py script-run ...
python video_tools.py mix-audio ...
python video_tools.py sfx-mix ...
python video_tools.py burnsub ...
python video_tools.py assemble ...
python video_tools.py merge-final ...
```

Output ownership:

- `final.mp4` is canonical only after the current run writes it.
- If pre-BUILD gate blocks, stale final is quarantined and must not be reported
  as current output.

### 7. Verify

Purpose: evaluate the result and route fixes.

Commands:

```powershell
python video_tools.py verify ...
python video_tools.py final-product-verify final.mp4 --out-dir verify_final
python video_tools.py black-frame-audit ...
python video_tools.py caption-audit ...
python video_tools.py timeline-audit ...
python video_tools.py new-visual-audit ...
python video_tools.py visual-audit ...
python video_tools.py verify-evidence ...
```

Routing:

- wrong/missing material -> Stage 3/4;
- black/blank/cut frames -> Stage 3 or shot-aware window update;
- subtitles/audio drift -> Stage 8/9;
- effect/finishing issue -> Stage 9;
- story thinness -> Stage 1/2.

### 8. Workbench Draft Review

Purpose: inspect and patch composition without changing canonical truth.

Commands:

```powershell
python tools/test_tiers.py --tier workbench
python tools/workbench_server.py --artifact-root RUN_DIR --port 8770
python tools/workbench_frontend_smoke.py --artifact-root RUN_DIR
node tools\workbench_browser_layout_smoke.mjs --artifact-root RUN_DIR
python tools/preview_timeline.py build --artifact-root RUN_DIR --out preview_timeline.json
python tools/timeline_patch.py validate --timeline preview_timeline.json --patch timeline_patch.json
python tools/timeline_patch.py apply --timeline preview_timeline.json --patch timeline_patch.json --out patched_draft_timeline.json
python video_tools.py workbench-draft-rerender ...
```

Use the `workbench` tier as the default preflight for Dashboard/Workbench
frontend migration. It covers the SPA shell render/i18n guard and the native
Workbench server/API/core/material helper smokes. Keep the browser layout smoke
for viewport-sensitive changes and the frontend smoke for Workbench-previewable
run folders with editable clips.

`workbench_frontend_smoke.py` is stricter than the layout smoke. It requires a
Workbench-previewable run folder with `timeline.json`, `draft_timeline.json`, or
`timeline.plan`, plus enough material data for at least one editable clip.
Use the browser layout smoke for layout-only checks, or build
`preview_timeline.json` from a valid timeline before using the frontend smoke.
For a self-contained fixture:

```powershell
python tools/workbench_frontend_smoke.py --artifact-root .tmp/workbench_frontend_smoke_fixture --init-fixture
python tools/workbench_frontend_smoke.py --artifact-root .tmp/workbench_frontend_smoke_fixture --exercise-replace
```

`--init-fixture` refuses non-empty folders by default. Use it only with
disposable `.tmp` paths, or add `--force-init-fixture` when intentionally
recreating that scratch fixture.

Supported draft actions:

- set duration;
- set source window;
- move clip;
- replace clip from material map;
- insert clip from material map;
- subtitle/audio/effect marker drafts.

Boundary:

- Workbench can suggest `workbench_contract_patch.json`.
- Backend must review/apply before official rerender.
- The native video monitor, playback controls, and four lower timeline lanes are
  protected during frontend migration. Run `tools/workbench_frontend_smoke.py`
  and `tools/workbench_browser_layout_smoke.mjs` before and after changes
  touching the iframe shell, monitor, playback controls, timeline lanes, or
  related responsive layout. Against the merged `/workbench` route, the browser
  layout smoke also rejects protected editor selectors in the outer SPA shell
  (`monitor-box`, `timeline-wrap`, `clip-video`, `wb-monitor`, `wb-timeline`,
  `track-lane`, `lane-video`) so Dashboard cannot silently duplicate the native
  monitor or four-track editor.

### 9. Brownfield Edit / Effects

Purpose: bounded post-review fixes.

Ffmpeg/light effect route:

```powershell
python video_tools.py light-effects-plan ...
python video_tools.py effect-revision-request ...
python video_tools.py effect-revision-draft ...
python video_tools.py effect-revision-apply ...
```

Remotion adapter route:

```powershell
python video_tools.py remotion-prompt-pack ...
python video_tools.py remotion-worker-smoke --dry-run ...
python video_tools.py remotion-worker-outputs ...
python video_tools.py remotion-composite-draft ...
```

Remotion boundary:

- `remotion_prompt_pack.json` is a worker handoff.
- `remotion_effect_review.json` must accept outputs.
- `remotion_composite_draft_report.json` is non-canonical unless promoted by a
  reviewed route.
- This does not replace `contract-run`.

Effect Factory route:

```text
effect need / review gap
  -> effect_design_map.json
  -> effect_contract.json
  -> remotion-effect-worker or light-effect backend
  -> effect_review.json
  -> effect_handoff.json
```

Use this route for designed openings, transitions, title cards, photo-wall
treatments, lightning/crack/heart/sakura/fire visuals, or material-first
finishing assets. It is the design/review layer; `remotion-effect-worker.md` is
the Remotion builder.

### 10. Delivery

Purpose: final handoff.

Minimum handoff:

- `final.mp4`;
- `review_report.md` or verify summary;
- `contact_sheet.jpg` when visual review is expected;
- `subtitles.srt` when subtitles matter;
- `run_layout.json` / artifact list;
- known limitations and unresolved warnings.

Commands:

```powershell
python video_tools.py dashboard ...
python video_tools.py state ...
python video_tools.py run-layout-validate ...
python video_tools.py operator-flow-acceptance ...
```

## Skill-to-Tool Index

| Skill | Primary role | Main tool(s) |
|---|---|---|
| `video-intent-planner.md` | Stage 0 route decision and `video_intent.json` | `video-intent-plan`, `video-intent-acceptance` |
| `video-workflow.md` | route selection and operator flow | `project-init`, `project-new-run`, `workflow-manifest` |
| `video-pipeline.md` | overall pipeline guidance | `commands-manifest`, `workflow-manifest`, `operator-flow-acceptance` |
| `route.md` | canonical route and delivery decisions | `state`, `run-layout-validate`, `operator-flow-acceptance`, `route-task-next`, `route-task-accept`, `route-orchestrator-acceptance` |
| `story-soul-blueprint.md` | creative soul / narrative device / shot plan | `story-soul-blueprint` |
| `blueprint-interview.md` | interactive story intake | `blueprint-coverage`, `blueprint-compile`, `blueprint-to-contract` |
| `writer.md` | screenplay/voiceover wording | `story-soul-blueprint`, `blueprint-to-contract` |
| `director.md` | shot purposes and visual design | `validate-needs`, `contract-dry-build` |
| `audio-director.md` | BGM, voiceover, cue intent | `gen-bgm`, `music-fetch`, `mix-audio`, `sfx-mix` |
| `subtitle-director.md` | subtitle plan and fixes | `srt`, `mksrt`, `caption-audit` |
| `effects-director.md` | neutral effect intent and finishing route | `effect-intent-plan`, `light-effects-plan`, `remotion-prompt-pack` |
| `video-effect-factory.md` | designed effect side branch: design map, contract, backend handoff, review | `effect-revision-*`, `remotion-prompt-pack`, `remotion-worker-outputs`, handoff artifacts |
| `remotion-effect-worker.md` | bounded Remotion backend worker | `remotion-worker-smoke`, `remotion-worker-outputs`, `remotion-composite-draft`, `tools/remotion_worker_bridge.mjs` |
| `material-map.md` | material truth lifecycle and single-source highlight planning | `project-material-map`, `material-map-lifecycle`, `material-delta`, `source-section-map`, `source-motion-profile`, `source-dialogue-script`, `tools/source_material_matrix.py`, `tools/source_highlight_plan.py`, `tools/safe_highlight_cut.py` |
| `curator.md` | material review/labeling | `visual-diversity-review`, `visual-family-normalize` |
| `material-generation-fallback.md` | convert missing/thin material into generation jobs | `material-generation-fallback`, `generated-image-provider-packet` |
| `generated-material-producer.md` | execute/import/review generated material | `image-agent-prompt-handoff`, `codex-imagegen-provider-fill`, `generated-material-produce`, `generated-material-import`, `generated-material-review` |
| `gap-analyzer.md` | gap interpretation and routes | `material-delta`, `supply-review`, `material-revision` |
| `shooting-brief.md` | collect/reshoot guidance | `lineage-link`, `material-revision` |
| `editor.md` | official BUILD and render | `contract-run`, `script-run`, `assemble`, `merge-final` |
| `verify.md` | quality and delivery checks | `verify`, `final-product-verify`, `black-frame-audit`, `timeline-audit`, `verify-evidence` |
| `dashboard.md` | dashboard/review surface | `dashboard`, `story-map`, `serve` |
| `brownfield-edit.md` | post-review bounded edits | `timeline_patch.py`, `workbench-draft-rerender`, `effect-revision-*` |
| `artifact-reviewer-map.md` | reviewer role/eval policy | `reviewer-policy`, `reviewer-flow-acceptance` |

## Artifact Flow

```text
project brief / `video_intent.json`
  -> story_soul_blueprint.json
  -> segment_contract.json + material_needs.json + effect_intent_plan.json
  -> per-asset maps / project_material_map.json
  -> material_delta.json
  -> revision_decisions.json / revised_segment_contract.json (if needed)
  -> contract-run
  -> timeline_build.json + final.mp4 + subtitles.srt
  -> verify_result.json + review reports
  -> Workbench draft patches or Brownfield edits if needed
  -> verified delivery
```

Generated-material branch:

```text
material_delta missing/thin
  -> material_generation_fallback.json
  -> generated_provider_packet.json
  -> image_agent_prompt_handoff.json
  -> provider output files
  -> generated-material-import
  -> generated-material-review
  -> reviewed project_material_map.json
  -> fresh material_delta
```

Effects branch:

```text
effect_intent_plan.json / effect need
  -> video-effect-factory
  -> effect_design_map.json
  -> effect_contract.json
  -> light-effects-plan for ffmpeg-supported effects OR
     remotion-effect-worker for designed Remotion assets
  -> effect_review.json / remotion_effect_review.json
  -> effect_handoff.json / remotion_effect_handoff.json
  -> Workbench/Brownfield review
```

Workbench branch:

```text
timeline_build.json + material maps
  -> preview_timeline.json
  -> timeline_patch.json
  -> patched_draft_timeline.json
  -> workbench_contract_patch.json
  -> backend review / rerender
```

## Legacy Alias Map

| Legacy label | Current route |
|---|---|
| M6 | Material Truth + Coverage Gate |
| M6a | Needs / lineage contract |
| M6b | Material delta + pre-BUILD gate |
| M6c | Delta-driven revision |
| M6d | Independent material-map lifecycle skill |
| M6e | Real-case material-map acceptance |
| VD1 | visual labels / consistency evidence |
| VD2 | visual diversity BUILD soft selection |
| SRP1 | segment sequence planner |
| SRP2 | opening/hook planner |
| SRP3 | story arc planner |
| KBF1 | still-photo motion stabilization (`mv_cut`, no `zoompan`) |
| FX / Node14 | Brownfield Edit / Effects finishing route |
| Effect Factory | Designed-effects side branch; calls Remotion worker or light backends |
| Dashboard | read/review shell |
| Workbench | draft edit shell |

## What To Do When Something Fails

| Symptom | Likely owner | Route |
|---|---|---|
| Story feels generic / soulless | Story Soul | Stage 1/2 |
| Wrong material selected | Material Truth or need join | Stage 3/4 |
| Missing material | Material Truth / generated fallback | Stage 3 |
| Black/cut frame selected | Material map scene quality | Stage 3/5 |
| Photo motion jitter | Renderer still treatment | Stage 5/6 |
| Too repetitive visually | VD2 labels / material variety | Stage 3/5 |
| Subtitle wrong or unreadable | Subtitle director / Brownfield | Stage 8/9 |
| Audio cue wrong | Audio director / Brownfield | Stage 8/9 |
| Effect missing | Effects director / Brownfield | Stage 9 |
| Workbench patch looks good but final unchanged | Expected boundary | Apply through backend route / rerender |
| `final.mp4` exists after a blocked build | Stale final handling bug | Stage 4/6 gate |

## Current Stable Use Cases

| Route | Status | Notes |
|---|---|---|
| Existing-material event film | stable backend route | Proven on 67th-material E2E; quality depends on map richness. |
| Generated comic/storybook | stable light route | Proven with generated panels; needs strong Story Soul and generated review rubric. |
| Workbench draft review | stable draft route | Good for timing/window/subtitle/audio/effect marker review; not final parity. |
| Remotion effect adapter | stable draft E2E | Prompt-pack/worker/review/composite path exists; still non-canonical. |
| Full template library | not yet complete | Build on top of this map; do not change route per template. |

## Minimal Agent Checklist

Before starting:

- Identify current stage.
- Read the stage skill.
- Confirm canonical input artifacts exist.
- Run the stage tool, not a custom script, unless the tool is missing.

Before BUILD:

- `material_delta.ok == true`
- `ready_for_build == true`
- no stale generated candidates pretending to be accepted
- no Workbench draft treated as canonical

Before delivery:

- `final.mp4` exists from current run
- verify/audit evidence exists
- subtitles/audio/effect expectations are stated
- unresolved limitations are listed
