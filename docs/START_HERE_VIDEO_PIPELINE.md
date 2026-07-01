# Start Here: Hermes Video Pipeline

Date: 2026-06-25
Status: canonical entrypoint for agents and operators

Read this first when you need to run, debug, or extend the video pipeline.

## What This Project Is

Hermes is a contract-first video pipeline:

```text
Video Intent Planner
  -> input state / entry_path
  -> story/design contract
  -> material truth, via Material Map branch when needed
  -> designed effects, via Effect Factory branch when needed
  -> soundtrack plan, via Soundtrack Arranger branch when needed
  -> BUILD
  -> verify/review
  -> draft edit or delivery
```

There is one main route with Stage 0 child contracts, and three active major
side branches:

```text
Main route: Video Pipeline Route
  -> Stage 0 child contracts: material_contract, soundtrack_contract,
     material_scan_decision, effect_policy, subtitle_voiceover_contract
  -> Material Map branch: material truth, coverage, generated candidates
  -> Effect Factory branch: designed effect assets, worker build, effect review
  -> Soundtrack Arranger branch: music/song/voice intent, source candidates,
     license manifest, audio-director handoff
```

Do not treat generated files, Workbench patches, stale reports, or old final
videos as truth. They must re-enter the route through their owning artifacts.

Shared skill boundary:

- Every pipeline skill must obey `skills/pipeline-boundary.md`.
- Stage 0 entry lock applies before story, material-map, generated fallback,
  Workbench, Brownfield, effects, Remotion, `contract-run`, or render.
- Do not direct-cut from a fuzzy request. A request like "help me cut a
  graduation ceremony video" must first produce or refresh `video_intent.json`.
- If `video_intent.json.required_followup_questions` is non-empty, stop and ask
  before entering the next branch.

## Route Boundary

Route is the traffic controller for the pipeline. It owns stage decisions,
handoffs, stop/go gates, expected artifacts, and return loops. It does not own
renderer internals, provider account/auth, Dashboard editing behavior, or
Workbench draft promotion.

Route owns:

- Stage 0 input-state and entry-path decision.
- Greenfield / brownfield / hybrid badge selection.
- `next_action`, `handoff_to`, and route task packet shape.
- Review stop points before continuing.
- Expected artifacts and freshness checks.
- Return routes when material truth, generated outputs, Workbench drafts, or
  reviewer gates change the state.

Route must stop instead of continuing when:

- route-changing intent or material information is missing;
- Material Map has candidate/thin/missing must-have needs;
- generated provider outputs have not passed import and explicit review;
- `material_delta.json` blocks ready-for-build;
- reviewer aggregation or hard-gate reviewer blocks;
- Workbench draft artifacts need agent/backend review.
- `final.mp4` is only a draft/render candidate unless complete-video delivery
  validation also proves required audio, narration, music, and subtitles.

Dashboard and Material Map are review surfaces. They may save review decision
artifacts, but they must not silently rewrite canonical truth. Workbench may
write draft patches; backend/agent review decides whether those patches become
official pipeline changes.

## Read Order

1. `docs/START_HERE_VIDEO_PIPELINE.md` -- this file.
2. `docs/pipeline-decision-tree.md` -- operator decision tree for the main
   Stage 0-10 route, Material Map, Effect Factory, Audio Communication, and
   cross-cutting Review / Verify / Delivery Gate branch.
3. `docs/video-pipeline-end-to-end-line.md` -- one-page line from intent to
   delivery, including input state, entry path, and return loops.
4. `docs/video-pipeline-operating-map.md` -- stage-by-stage operating manual:
   skills, tools, artifacts, gates, return routes.
5. `docs/canonical-video-pipeline-route.md` -- canonical stage definitions and
   legacy alias mapping.
6. `docs/upstream-story-route.md` -- full upstream line from role/literary lens
   through blueprint, Story Soul, Director Shot Plan, contract compile, and
   material-ready handoff.
7. `docs/artifact-reviewer-map.md` -- lightweight reviewer policy:
   `light / normal / deep` and reviewer roles.
8. `docs/material-map-lifecycle.md` -- material needs, maps, delta, revision,
   lifecycle stages, and build handoff.
9. `docs/effect-factory-route.md` -- designed-effects side branch: design map,
   contract, worker handoff, review, and bounded effect asset handoff.
10. `docs/soundtrack-arranger-route.md` -- music/song/BGM/voice intent branch:
   `soundtrack_plan.json`, `music_source_candidates.json`,
   `sound_license_manifest.json`, and `audio_director_handoff.json`.
11. `docs/stage-boundary-matrix.md` -- worker/maintainer boundary matrix for
   Main Pipeline, Material Map branch, Effect Factory branch, Soundtrack /
   Audio branch, and Subtitle / Voiceover branch.
12. `docs/construction-guides/stage0-10-route-alignment-plan.md` -- current
   construction guide for keeping Stage 0-10 and child contracts aligned.
13. `docs/build-capability-alignment.md` -- which capabilities truly affect
   BUILD/render today.
14. `docs/route-orchestrator-harness.md` -- optional multi-agent task packet
   and fail-closed acceptance harness.
15. `docs/route-agent-runner-protocol.md` -- how Codex/Claude/Gemini or a
   human worker should consume `route_subagent_task.json`.
16. `RUNBOOK.md` -- current local command examples and Windows execution notes.
17. `docs/INDEX.md` -- broader documentation index and historical links.

## Main Skill Entry

Use:

```text
skills/video-pipeline-route.md
```

That is the operator skill for the full route.

Stage 0 uses:

```text
skills/video-intent-planner.md
```

It writes the canonical `video_intent.json` artifact:

```powershell
python video_tools.py video-intent-plan project_brief.json --out video_intent.json
```

Stage 0 artifact ownership:

- `project_brief.json` / `brief.json` is raw input.
- `video_intent.json` is the canonical Stage 0 input-state / entry-path
  decision.
- `route_decision.json` is legacy/compat unless a current harness explicitly
  requires it.

Other skills are role-specific:

- story: `story-soul-blueprint.md`, `writer.md`, `director.md`
- material: `material-map.md`, `curator.md`, `material-generation-fallback.md`,
  `generated-material-producer.md`
- build: `editor.md`, `audio-director.md`, `subtitle-director.md`
- effects: `effects-director.md`, `video-effect-factory.md`,
  `remotion-effect-worker.md`
- soundtrack: `soundtrack-arranger.md` owns `soundtrack_plan.json` and
  `sound_license_manifest.json`; `audio-director.md` executes TTS/mix/ducking.
- review: `verify.md`, `dashboard.md`, `brownfield-edit.md`

`video-effect-factory.md` is the upper effect route. It does not replace
`remotion-effect-worker.md`; it decides/records the effect contract, calls the
worker when Remotion is appropriate, reviews the result, and hands off bounded
effect assets.

## Choose The Route

Stage 0 is **Video Intent Planner**. It is the upstream role that asks what kind
of video this is, who it is for, what material or text exists, whether
generation is allowed, and which route owns the next handoff. It may behave like a storybook
writer, teacher, event director, personal-memory editor, or brand editor
depending on the brief, but it does not write the type-specific template.

Its canonical artifact is `video_intent.json`, with:

- `input_state`
- `entry_path`
- `video_type`
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

First decide **input state** before deciding how much structure or story
invention is allowed. This is the top-level split:

```text
Video Intent Planner
  -> input_state: material_available | text_available | idea_only | unknown
  -> entry_path: material-first | structure-first | needs-context
  -> route-specific story/design/material work
```

- **material-first**: the user has existing or partial footage/photos/material.
  Run material-map early, let available material reveal people, scenes, actions,
  emotions, timeline, and gaps, then use interaction to remove ambiguity and
  build the structure. generation is fallback only for missing/non-proof
  support for teaching and personal video routes.
  `material_scan_decision` is the Stage 0 child decision for this first
  observation step: default to quick inventory over all materials, unless the
  user specifies a folder/file scope. Do not treat it as another entry path.
- **structure-first**: the user has no usable material but has text, an article,
  an outline, a story, or a developed idea. Clarify the structure first, then
  derive material needs and route missing visuals through existing generated
  material fallback.
- **needs-context**: the brief is too vague to choose a handoff. Ask focused
  questions before Story Soul, Material Truth, or BUILD.

`handoff_packet` records the next owner, first action, required inputs, expected
outputs, and return point. For `material-first`, the first action is
`material_map_quick_inventory` and expected outputs include
`project_material_map.json` and `material_delta.json`.

Legacy compatibility:

- `existing-material-first` maps to `material-first` when material exists.
- `story-first` maps to `structure-first` when text/idea leads.
- hybrid is not a primary Stage 0 entry path.
- `hybrid` is not a primary Stage 0 entry path; partial material enters
  `material-first`, then material delta decides generation, reshoot, rewrite,
  drop, or waiver.

If the project starts from a story, essay, life experience, fairy tale, or
emotion-heavy event brief, use `docs/upstream-story-route.md` before Material
Truth. The upstream line is:

```text
Role / Literary Lens
  -> Blueprint Interview
  -> Story Soul Package
  -> Director Shot Plan
  -> Contract Compile
  -> Material-Ready Handoff
```

### Existing material

Use when the user already has real footage/images.

```text
Video Intent Planner
  -> Material Map quick inventory
  -> story/design skeleton constrained by the map
  -> Material Map review / need satisfies edges
  -> Material Delta
  -> BUILD
  -> Verify
  -> Workbench/Brownfield if needed
```

Do not route to generated storybook only because the style is comic, picture
book, or illustrated. If real material exists, inspect it first and let
material-delta decide which beats still need generation.

### Generated material

Use for comics, picture books, synthetic story videos, or missing footage.

```text
Video Intent Planner
  -> Literary / Role Lens if story quality matters
  -> Story Soul Blueprint
  -> Material Needs
  -> Material Generation Fallback
  -> Generated Provider Packet
  -> Generated Material Import
  -> Generated Material Review
  -> Fresh Delta
  -> BUILD
```

### Hybrid material

Use when some real material exists and some needs require generation/reshoot.

```text
Project Material Map + Generated Candidates
  -> Explicit Review
  -> Fresh Material Delta
  -> Revision or BUILD
```

### Workbench / Brownfield

Use after a render or review when the user wants bounded local changes.

```text
Workbench draft patch
  -> backend handoff
  -> Brownfield edit / rerender
  -> Verify
```

## Review Policy

The route may declare:

```json
{
  "review_policy": {
    "level": "light | normal | deep"
  }
}
```

- `light`: material producer + technical verify.
- `normal`: story director + material producer + timeline + technical verify.
- `deep`: adds literary editor, generated art director, audio/subtitle, effects,
  and delivery review.

See `docs/artifact-reviewer-map.md`.

Do not turn every review into a hard gate. Gate strength depends on reviewer
role and artifact.

Current E2E review hardening source:

```text
docs/construction-guides/agent-orchestration/2026-06-22-integrated-e2e-review-action-plan.md
```

Use it when fixing silent green failures, runner orchestration, generated
material acceptance, material truth precedence, or final QA dimensions. It is a
construction review, not a replacement for the canonical route docs.

## Core Commands

List commands:

```powershell
python video_tools.py --help
python video_tools.py commands-manifest
python video_tools.py workflow-manifest
python video_tools.py video-intent-plan project_brief.json --out video_intent.json
python video_tools.py video-intent-acceptance --out video_intent_acceptance.json
```

Common official render:

```powershell
python video_tools.py contract-run segment_contract.json `
  --material-db materials_db.json `
  --music bgm.mp3 `
  --out final.mp4 `
  --mat-dir run
```

Multi-agent route packet:

```powershell
python video_tools.py route-task-next RUN_DIR --out route_subagent_task.json
python video_tools.py route-task-accept `
  --task route_subagent_task.json `
  --result route_subagent_result.json `
  --state-out route_orchestrator_state.json
python video_tools.py route-orchestrator-acceptance RUN_DIR `
  --route existing-material-first `
  --stage-count 4 `
  --out route_orchestrator_acceptance.json
```

Material lifecycle:

```powershell
python video_tools.py material-map-lifecycle --out-dir run `
  --needs material_needs.json `
  --material-db materials_db.json `
  --contract segment_contract.json
```

Material-first boundary acceptance:

```powershell
python tools/material_first_boundary_acceptance.py `
  --out RUN_DIR `
  --source-dir MATERIAL_SOURCE_DIR `
  --wall-verdict material_wall_review_verdict.json `
  --max-assets 12 `
  --json
```

This is the current local acceptance entry for material-first runs before
render. It runs Stage 2/3 material wall handoff, Stage 4 build smoke, and Stage
5 final-review smoke, then writes
`material_first_boundary_acceptance_report.json`. `pipeline_home.py` and the
Dashboard state read this report as the compact handoff result. If it fails,
follow its `failed_stage`, `blocking`, and `next_action` instead of continuing
to render. Workers must use the operator-provided material folder exactly: do not substitute `--source-dir`; if the specified folder is missing, stop and
report `blocked` instead of selecting a neighboring folder.

Material-first Remotion MemoryPhotoWall boundary acceptance:

```powershell
python tools/remotion_material_first_memory_acceptance.py `
  --run-dir RUN_DIR `
  --project-map project_material_map.json `
  --wall-verdict material_wall_review_verdict.json `
  --wall-request verify/material_wall/material_wall_request.json `
  --json
```

Use this only when validating the bounded Remotion effect path for reviewed
material-first refs. Read `skills/remotion-effect-worker.md` and
`docs/construction-guides/remotion-effect-build-api-plan.md` before changing the
effect contract. The output
`remotion_material_first_memory_acceptance_report.json` proves the
MemoryPhotoWall artifact chain is reviewable. The promotion surface is
`remotion_effect_handoff.json`, which lists accepted finishing assets and
evidence for later Workbench / ffmpeg adoption. Neither artifact is **final
delivery** and neither must be treated as `final.mp4` verification; this is
not final delivery.

Effect Factory route acceptance:

```powershell
python tools/effect_factory_route_acceptance.py `
  --out RUN_DIR `
  --request "electric lightning opening with readable title" `
  --effect-role opening_title `
  --duration-sec 4 `
  --json
```

Use this before claiming the Effect Factory line is wired. It starts from a
semantic request, writes `visual_technique_plan.json`, confirms the translated
parameters, runs `effect_capability_review.json`, builds
`remotion_prompt_pack.json`, creates dry-run `remotion_worker_outputs.json`,
validates `remotion_effect_review.json`, and writes `effect_handoff.json` plus
`effect_factory_route_acceptance_report.json`. It does not write `final.mp4`.

Generated material handoff:

```powershell
python video_tools.py material-generation-fallback ...
python video_tools.py generated-image-provider-packet ...
python video_tools.py generated-material-import ...
python video_tools.py generated-material-review ...
```

Workbench:

```powershell
python tools/test_tiers.py --tier workbench
python tools/workbench_server.py --artifact-root RUN_DIR --port 8770
python tools/workbench_frontend_smoke.py --artifact-root RUN_DIR
node tools\workbench_browser_layout_smoke.mjs --artifact-root RUN_DIR
```

Use the `workbench` tier as the default preflight before Dashboard/Workbench
frontend migration. It runs the SPA shell render/i18n guard plus the native
Workbench server/API/core/material smoke tests, and it executes child processes
with `TMP` / `TEMP` pointed at `.tmp/test-temp` so Windows user-temp corruption
does not look like a Workbench regression.

`workbench_frontend_smoke.py` needs a Workbench-previewable run folder: one
with `timeline.json`, `draft_timeline.json`, or `timeline.plan`, plus enough
material data for at least one editable clip. If the run is layout-only or has
no preview timeline yet, run the browser layout smoke first or build
`preview_timeline.json` from a valid timeline before using the frontend smoke.
For a self-contained local check, create a tiny previewable fixture and run both
draft paths:

```powershell
python tools/workbench_frontend_smoke.py --artifact-root .tmp/workbench_frontend_smoke_fixture --init-fixture
python tools/workbench_frontend_smoke.py --artifact-root .tmp/workbench_frontend_smoke_fixture --exercise-replace
```

`--init-fixture` refuses non-empty folders by default. Use it only with
disposable `.tmp` paths, or add `--force-init-fixture` when intentionally
recreating that scratch fixture.

Run the fast frontend smoke plus browser layout smoke before and after any
frontend change touching the Workbench iframe shell, native video monitor,
playback controls, or four timeline lanes. These are guards for the protected
editing surface, not canonical render validators. Against the merged
`/workbench` route, the browser layout smoke also rejects protected editor
selectors in the outer SPA shell (`monitor-box`, `timeline-wrap`, `clip-video`,
`wb-monitor`, `wb-timeline`, `track-lane`, `lane-video`) so the shell cannot
quietly grow a duplicate monitor or four-track editor.

## Before You Claim Success

Check:

- current run wrote `final.mp4`;
- output duration is consistent with `brief.target_length` or has an explicit
  waiver;
- for a real deliverable, run complete-video validation and require:
  `delivery_requirements.json`, `narration_manifest.json`,
  `music_manifest.json`, `audio_mix_report.json`, `subtitles.srt`, and a
  `final.mp4` with the required media streams;
- rendered subtitles are readable on screen; text matching the script is not
  enough if the rendered text is clipped or outside the safe area;
- generated-material routes must also prove story, character, and segment
  consistency in `generated_material_review.json`; a generated image existing is
  not enough;
- generated-material routes must not count duplicated or failed-quality images
  as full coverage without waiver;
- generated-material routes must preserve prompt lineage:
  `material_generation_fallback.json` must be `ok=true` with generation jobs,
  `generated_provider_packet.json` must list non-empty jobs with `job_id`,
  `need_id`, `prompt`, and `target_file`, and every accepted generated asset
  must trace back to one of those prompt jobs;
- generated prompt jobs must include minimal truth controls. Use
  `source_truth=generated | reference_guided_generated | composite` and
  `truth_usage=support | illustrative | transition`. If an image is generated
  from real material references, include `reference_controls.reference_assets`.
  Reference-guided generation may support story/atmosphere/transition needs,
  but must not be used as proof of a real event or person;
- real-material / montage routes must provide `frame_evidence.json` with
  inspected frame refs, visual observations, and `semantic_match=true` for the
  selected material;
- VLM/content-alignment findings from material selection must surface in final
  QA or dashboard review instead of disappearing after selection;
- narration cannot be a fallback tone/cue unless the delivery requirements
  explicitly allow fallback; required narration must reference usable audio
  files through `narration_manifest.json`;
- if `effect_intent_plan.json` or `transition_plan.json` declares planned
  effects, delivery must include `effect_render_verification.json` proving the
  effects were actually rendered; use the existing `keyframe-grid` /
  `visual-audit` evidence path (`keyframe_grid.jpg`, `visual_audit.json`) as the
  sampled render evidence instead of inventing a separate montage tool;
- after visual BUILD and Audio Director both finish, assemble final media with
  `tools/final_av_assemble.py` rather than ad hoc ffmpeg. `assembly_report.json`
  must record the selected audio and whether original source audio was mapped;
  replace-music routes should show `source_audio_mapped:false`;
- if the soundtrack placement depends on music understanding, run
  `tools/soundtrack_probe.py` and set
  `delivery_requirements.requires_soundtrack_probe=true`; delivery must then
  include a non-empty `soundtrack_probe_report.json` with `features`,
  `sections`, `editing_fit`, and `section_fit`;
- required review text artifacts must be readable UTF-8 and must not contain
  mojibake placeholders such as `????`;
- subtitle/narration language must match the delivery requirements;
- material delta / revision gates were fresh;
- generated candidates were explicitly reviewed;
- Workbench patches did not overwrite canonical artifacts;
- verify/audit evidence exists;
- reviewer outputs have no unresolved `revise`, `soft_block`, or `hard_block`;
- `--complete-video` has no warning channel: warnings are promoted to errors so
  the result is either pass or blocked;
- unresolved limitations are stated.

If a failure is creative, go back to Story Soul / reviewer layer.
If a failure is material, go back to material map / delta.
If a failure is finishing, use Workbench / Brownfield.
If a failure is technical delivery, use Verify / render fix.

Focused local check:

```powershell
python tools/validate_pipeline_run_folder.py RUN_DIR --complete-video
```
