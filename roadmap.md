---
title: Hermes Video Pipeline — Canonical Roadmap
type: project
status: active
updated: 2026-06-20
tags: [project, video, pipeline, roadmap, agent-workflow]
---

# Hermes Video Pipeline — Canonical Roadmap

This file is now the **current-state roadmap and navigation index**. Long-form
implementation history was moved out to `docs/roadmap-history/` so agents do not
confuse historical plans with active direction.

Read order for agents:

1. `README.md`
2. `roadmap.md` (this file)
3. `docs/START_HERE_VIDEO_PIPELINE.md`
4. `docs/video-pipeline-end-to-end-line.md`
5. `docs/video-pipeline-operating-map.md`
6. `docs/canonical-video-pipeline-route.md`
7. `docs/upstream-story-route.md`
8. `docs/artifact-reviewer-map.md`
9. `RUNBOOK.md`
10. `docs/INDEX.md`
11. Topic-specific docs linked below

## Current Canonical State

### Backend

The backend is stable through the material-map lifecycle and BUILD handoff:

- Material supply/demand lifecycle M6a-M6e is complete as backend
  infrastructure.
- `contract-run` revalidates material needs, maps, delta, revisions, and gate
  status before BUILD.
- Map-ranked retrieval, visual diversity soft selection, photo map-ranked
  renderability, SRP1/SRP2/SRP3, opening/ending bookends, and Workbench draft
  handoff are implemented.
- Existing known quality gaps are now creative/input issues more than core
  contract issues: weak upstream story concept, thin material plans, black/cut
  windows in raw footage, and human sign-off.

Canonical material-map summary:

- `docs/material-map-lifecycle.md`

Canonical full-route summary:

- `docs/canonical-video-pipeline-route.md`

Canonical upstream story route:

- `docs/upstream-story-route.md`

Reviewer layer:

- `reviewer-policy` materializes light/normal/deep reviewer sets and eval
  principles.
- `reviewer-flow-acceptance` proves normal route, upstream story, and
  effects/brownfield reviewer coverage without calling an LLM reviewer.
- Reviewer artifacts remain guidance/gates for their owned route; they do not
  replace `material_delta`, `verify`, or canonical BUILD outputs.

### Frontend

Dashboard and Workbench are separate surfaces:

- Dashboard = read/review/node-status surface.
- Workbench = interactive preview, draft timeline patching, limited export, and
  contract patch handoff.
- Workbench writes draft artifacts only; official final render remains backend
  ffmpeg / `contract-run`.

Frontend references:

- `docs/workbench-dashboard-integration.md`
- `docs/decisions/2026-06-16-native-preview-engine.md`
- `dashboard/README.md`

## Active Direction

### ISF1 Interactive Skill Flow

Status: implemented / accepted as current process contract.

Purpose: solidify the interactive operating flow without freezing story
templates. Agents should acquire missing parameters through skills, emit
canonical artifacts, and stop at explicit gates instead of guessing.

Decision:

- `docs/decisions/2026-06-19-interactive-skill-flow.md`

Canonical entry:

```text
video-pipeline
  -> Video Intent Planner / video-workflow when the request is vague
  -> material availability split before story depth
  -> story-soul-blueprint when story soul / narrative device is thin
  -> material-map when material truth, coverage, delta, or handoff is needed
  -> generated-material-producer when missing material may be generated
  -> runtime / Workbench / verify for BUILD, draft review, and delivery
```

Rules:

- This is process solidification, not template solidification.
- Stage 0 now explicitly decides `material availability` before deeper story
  work:
  - `existing-material-first`: run material-map early; existing media is the
    story source and constraint. For teaching and personal video routes,
    generation is fallback only.
  - `story-first`: no usable material exists, or the route is explicitly
    generated/storybook; story/design intent leads before material generation.
  - `hybrid`: some real material exists and missing beats route through
    material-delta, generation/reshoot/rewrite/drop/waiver decisions.
- `storyboard_panel_locked=true` applies to comic/photo/storybook/panel
  narration; stretch the panel or generate more panels instead of auto-filling
  unrelated panels.
- Workbench remains a draft patch surface; official render remains backend
  ffmpeg / `contract-run`.
- Historical roadmap sections are evidence only, not active flow instruction.

### Quality Stabilization Sequence

Status: active queue, execute in order.

Source of this queue:

- human review of recent generated/storybook and 67th-material outputs;
- renderer/code inspection;
- frame sampling of still-photo motion showing visible Ken Burns jitter;
- real E2E findings around black/cut windows, generated-material review depth,
  story-blueprint thinness, Workbench edit limits, and Remotion effect adapter
  boundaries.

Each increment must follow the same closure loop:

```text
roadmap alignment
-> TDD / focused tests
-> implementation
-> BUILD or render-path verification
-> short E2E when behavior affects output
-> review report / finding correction
-> only then move to the next increment
```

Ordered increments:

| Order | Increment | Why now | Minimum acceptance |
|---|---|---|---|
| 1 | KBF1 photo motion stabilization | Still-photo Ken Burns is core to generated storybook/comic videos; current zoom/pan can visibly jitter on slow pushes and off-center focus. | **Complete 2026-06-20.** `_photo_vf` now avoids truncation/fixed-pixel pan steps, keeps runtime-safe 1080p zoompan output, and has focused + short true-render probe evidence. |
| 2 | Shot-aware window selection / black-transition avoidance | Real 67th-material tests exposed black/cut frames from naive fixed-window selection. | **Complete 2026-06-20; hardened 2026-06-20.** `plan_ranked_windows` consumes scene `avoid_ranges`/`bad_ranges`, first backfills from lower-ranked clean windows, and if all usable candidates are bad it falls back to the least-bad slot with `window_quality_fallback=true` instead of silently dropping the segment. Photos ignore video bad ranges. |
| 3 | Generated material review rubric | Generated route is functional, but review must score story fit, style consistency, character continuity, and need coverage, not just file existence. | **Complete 2026-06-20.** `generated_material_quality_review.json` now records rubric dimensions (`story_fit`, `style_consistency`, `character_continuity`, `camera_language`, `truth_boundary`, `need_coverage`) for both offline renderer and provider-import flows; style/character anchor failures fail the quality gate; generated-material E2E stays green. |
| 4 | Story Soul / Director Shot Plan template thickness | Technically valid videos can still lack narrative soul if the blueprint behaves like a parameter sheet. | **Complete 2026-06-20; BUILD passthrough/ranking hardened 2026-06-20; effectiveness reporting hardened 2026-06-20; zero-flip diagnosis split 2026-06-21.** Story Soul beats carry `conflict_or_turn`, `sensory_anchor`, `intended_viewer_feeling`, and `emotional_movement`; `compile_contract` now preserves film-level `story_soul.narrative_device` and beat-level soul fields into `segment.core`; `director_intent.material_prompt_requirements` reaches `material_fit`. BUILD `rank_scenes` consumes these as soft `soul` evidence only after need/text/function/pace has admitted a candidate. The 67th fuller replay now reports `bsa1_soul_selection` on/off flip count and distinguishes `soul_intent_empty`, `material_semantics_too_thin`, and `no_tie_opportunity`; the current 67th planning-only replay is 12 comparable segments / 0 flips / 0 positive-soul segments / 12 tie groups with `diagnosis=soul_intent_empty`, so a real 67th soul acceptance must start from a story-soul blueprint before testing scene-ingest semantics. |
| 5 | Workbench replace/insert material patch | Workbench can adjust timing/windows, but practical review needs bounded material replacement/insertion without making Workbench canonical truth. | **Complete 2026-06-20.** `replace_clip` already existed; `insert_clip` is now supported in `timeline_patch` and Workbench core as draft-only material-map-resolved ops. Validation blocks bad asset/scene/position/duration, patched drafts never overwrite canonical timeline/material truth, and JS/Python focused tests are green. |
| 6 | Remotion effect adapter E2E | Effects should support prompt-driven rich visuals, but Remotion must remain an adapter/draft route until reviewed. | **Complete 2026-06-20.** The E2E now proves effect revision request -> Remotion prompt pack -> worker smoke outputs -> pending review -> accepted review -> non-canonical composite draft, keeps `final.mp4` untouched, and surfaces `next_action: workbench_review_remotion_composite_draft`. |

### Next Strategic Work: Creative Blueprint / Story Soul Layer

Status: implemented as SSB1 baseline; continue with real creative acceptance.

Current problem: the pipeline can enforce material truth, but the upstream story
blueprint can still be too thin if the agent treats it as a parameter sheet. It
can produce a technically valid video that still lacks narrative soul.

Next work should build a reusable upstream creative layer, not add more BUILD
parameters:

```text
Story World / Information Intake
  -> Creative Concept / Narrative Device
  -> Screenplay Beats
  -> Director Shot Plan
  -> material_needs + generation_manifest
  -> Material Map Lifecycle
  -> BUILD
```

Target first increment:

- `SSB1 Story Soul Blueprint Skill`
- Design reference: `docs/story-soul-blueprint-skills.md`

### VIP Video Intent Planner — Upstream Role Generalization

Status: design accepted 2026-06-21
(`docs/decisions/2026-06-21-video-intent-material-availability-split.md`). Stage 0
material-availability split is solidified in commit `9fea4f3`. The per-type
planners below are planned, not yet built.

Problem: the most upstream role is still story-centric — `story-soul-blueprint`
assumes a narrative/fiction author. Real requests are broader (teaching cuts,
event recaps, personal memory films, brand shorts). The upstream role should be a
**video intent planner / narrative-intent designer**, not always a fiction
writer, and should branch to a type-appropriate planner.

This generalizes — does not replace — the pipeline. Everything below the planner
is unchanged:

```text
video-intent-planner
  -> material availability (existing-material-first | story-first | hybrid)   [done: 9fea4f3]
  -> video type detection
  -> type-specific planner (story | teaching | memory | event | brand | ...)
  -> material_needs
  -> material_map -> material_delta -> BUILD -> VERIFY / Workbench
```

Two intake sources (both already named in the design):

1. facts extracted from material — who appears, which scenes, which actions,
   which events, what usable emotion/shots exist.
2. interactive supplement — who these people are, what matters most, for whom,
   intended effect (move | teach | commemorate | sell | persuade), what must
   not be used.

Video type detection (Stage 0.5, after availability):
`storybook | teaching | personal-memory | graduation-event | brand-product |
documentary | music-video`.

Per-type planner outputs — each is a bounded skill; only the story branch exists
today:

| Type | Planner skill | Produces | Built |
|---|---|---|---|
| storybook / fiction | `story-soul-blueprint` (existing) | character, world, conflict, emotional arc, storyboard | yes |
| teaching | `teaching-structure-planner` (new) | audience, learning goals, chapter order, key points, common mistakes, demo material | no |
| personal-memory | `memory-story-planner` (new) | people & relationships, key events, timeline, memory anchors, intended feeling | no |
| graduation / event | `event-recap-planner` (new) | training journey, shared memories, representative sessions, climax, departure/completion feel | no |
| brand / product | `brand-short-planner` (later) | message, audience, value prop, proof points, CTA | no |
| documentary / music-video | (later) | — | no |

Bounded increments — build in route priority, not all at once:

- **VIP0 Naming + entry skill.** Add `video-intent-planner` (a.k.a.
  `video-brief-interview`) as the named upstream skill that runs availability +
  type detection and dispatches. Keep `story-soul-blueprint` for the story
  branch. Acceptance: route-acceptance harness asserts the planner asks purpose /
  audience / material availability / type and dispatches to the correct branch;
  existing story route stays green.
- **VIP1 teaching-structure-planner.** First non-fiction planner (teaching is
  route-2 priority, structurally stable). Acceptance: a teaching brief + screen
  recordings produce `material_needs` with chapter order + key points, routed
  existing-material-first, generation not defaulted; one real teaching-case E2E.
- **VIP2 event-recap-planner.** The graduation/67th route. Acceptance: wired into
  the 67th harness so `soul_intent_segments` goes 0 -> N — this closes the
  `soul_intent_empty` diagnosis recorded in the Quality Stabilization row 4.
- **VIP3 memory-story-planner.** Personal video. Deferred until teaching + event
  prove the non-fiction planner pattern.

Discipline / boundaries (from the decision doc and review session):

- Skill/role discipline first. Do NOT add a runtime schema for video-type until a
  real run proves a machine-readable field is needed beyond existing brief fields.
- Per-type planners are bounded templates on a thin shared intake. Keep the
  intake general; keep each planner deep + bounded. Do not let the intake layer
  absorb type-specific logic (that is how a thin general layer bloats into a
  framework).
- A type is not "shipped" until its reference / skill / prompt is written to the
  same spec quality as `story-soul-blueprint`.

### Open Threads — 2026-06-20/21 Review Session

Captured so they are not lost; not yet scheduled increments.

- **BSA1 effectiveness on the ship route.** Run the soul on/off diff
  (`disable_soul_ranking`) on the generated storybook route, not only the 67th
  case, to confirm `soul` actually flips selections on the route being packaged
  first. Acceptance: storybook diff shows `soul_intent_segments > 0` and
  `flip_count > 0`, or a conscious decision to keep BSA1 inert-but-present.
- **Packaging (storybook first).** Wrap engine + ffmpeg + dashboard in one
  launch unit (Docker), host on a single shared machine, do not per-user install.
  Workbench gets a two-mode UX: Review default (player + linear scene list +
  replace/insert + export) and Edit advanced (current timeline behind a toggle).
  Keep effects out of the colleague default view until preview spec-sync lands.
- **Effect preview spec-sync.** One canonical preset -> visual-parameter table
  consumed by both `buildEffectPreviewStyle` (JS preview) and the Remotion render
  path, so the monitor preview matches the final render. Ref:
  `docs/decisions/2026-06-20-effect-preview-drift-review.md`.
- **SPEC / node convergence (evidence-led).** Before consolidating SPEC or
  upstream nodes, identify which gates/audits have never changed an output (empty
  `findings` across `.tmp` runs) and which upstream nodes never produce a distinct
  result; only those are safe to merge or demote. Do not consolidate a layer that
  is still actively changing.

### Generated Storybook Route

Status: verified as a viable route; not yet a polished production template.

The Snow White generated-storybook E2E proved that the generic route is valid:

```text
story intent
  -> story soul / screenplay beats
  -> material_needs
  -> generation fallback
  -> provider packet
  -> generated images as material assets
  -> generated material review
  -> fresh material_delta
  -> contract-run BUILD
  -> Chinese subtitles + review artifacts
```

Evidence:

- `docs/decisions/2026-06-20-snow-white-generated-storybook-e2e.md`
- `.tmp/snow_white_storybook_e2e/final_snow_white_zh.mp4` generated during
  validation: 18 panels, 270.134s, 18/18 material coverage, verify pass.

Current conclusion:

- This is not the fastest way to make a one-off slideshow, but it is the right
  shape for reusable story routes because generated assets stay traceable
  through material-map review, delta coverage, and official BUILD.
- Start with a universal generated-story flow, then add template routes on top:
  fairy tale, moral lesson, comic recap, explainer, and training story.
- The main remaining weakness is creative direction, not backend plumbing:
  generated panels passed coverage but still need stronger camera language,
  character consistency checks, and per-beat pacing design.

Route hardening to consider before template expansion:

- provider-output mapping must be explicit; never infer image order from
  "latest N generated files";
- Chinese subtitle artifacts must be written and verified as UTF-8 before BUILD;
- storybook/comic routes should use `storyboard_panel_locked=true`;
- long narration should request more panels or intentional longer panel holds,
  not auto-fill unrelated accepted panels.

Expected outputs:

- `story_world.json`
- `creative_concept.json`
- `screenplay_beats.json`
- `director_shot_plan.json`
- `material_needs.json`
- `generation_manifest.json` / `material_generation_fallback.json`
- `review_checklist.md`

Acceptance intent:

- A graduation/training film should not be reduced to "course A, course B,
  course C".
- The skill must extract a core metaphor/narrative device, such as the 66th
  graduation film example: "0.66% of life spent in training center" and a
  report-writing memory frame.
- Every beat must declare its story function, emotional movement, required
  visual actions, material count, and fallback.
- Material quantity must be estimated honestly before BUILD. If available or
  generated material cannot support the promised duration, the plan must shorten
  or request material instead of pretending success.

Implementation direction:

- Start with one composite skill: `skills/story-soul-blueprint.md`.
- Keep existing `writer`, `director`, and `material-map` skills. The new skill
  feeds them richer upstream artifacts; it does not replace them.
- Do not split into multiple skills until the composite skill has passed at
  least one real graduation/training acceptance case and one generated
  comic/photo story acceptance case.
- Once proven, the composite sections may be split into:
  `story-world-intake`, `narrative-device`, `screenplay-beat-architect`, and
  `material-prompt-compiler`.
- The layer must compile toward existing canonical artifacts rather than create
  a second BUILD schema.

### SSB1 Story Soul Blueprint Skill

Status: implemented / accepted as baseline scaffolding.

Canonical files:

- Skill: `skills/story-soul-blueprint.md`
- Tool: `video_tools.py story-soul-blueprint`
- Module: `video_pipeline_core/story_soul_blueprint.py`
- Tests: `tests/test_story_soul_blueprint.py`

Flow:

```text
project_brief.json
  -> story_world.json
  -> creative_concept.json
  -> screenplay_beats.json
  -> director_shot_plan.json
  -> material_needs.json
  -> generation_manifest.json
  -> review_checklist.md
```

Current acceptance:

- Training/graduation brief produces a report-writing memory frame and `0.66%`
  metaphor instead of a course list.
- Generated comic brief produces enough panel estimates for a one-minute story
  and all shot-plan items prefer generated images.
- Generic brief without a story subject fails closed.

Boundary:

- SSB1 is deterministic baseline scaffolding. It gives agents a stronger
  artifact shape and minimum story logic; it is not a substitute for a human or
  high-end writer model improving the prose.

### SSB1→GMP End-To-End Acceptance

Status: implemented / accepted for contract-chain proof.

Tool:

- `tools/story_to_generated_material_e2e.py`

Flow:

```text
project brief
  -> story-soul-blueprint artifacts
  -> material_delta missing
  -> material_generation_fallback
  -> generated_material_produce
  -> generated_material_review
  -> material_delta covered
```

Current case:

- `postcard_city_sky`
- 5 screenplay beats
- 5 material needs
- 21 generated storyboard panels
- initial delta: `missing=5`
- after generation: `thin=5`, `missing=0`
- after review: `covered=5`, `thin=0`, `missing=0`

Boundary: this proves the contract chain and material counts. The deterministic
storyboard cards are not final art; real GPT image / Gemini outputs must enter
through `generated-material-import` before review.

### MGF1 Material Generation Fallback Skill

Status: implemented / accepted for provider-neutral generated-material fallback.

Purpose: when M6 delta proves some needs are `missing` or `thin`, produce a
provider-neutral generated-material job list without pretending generated
assets are real footage.

Canonical files:

- Skill: `skills/material-generation-fallback.md`
- Tool: `video_tools.py material-generation-fallback`
- Module: `video_pipeline_core/material_generation_fallback.py`

Flow:

```text
material_delta.json
  + optional story_world / creative_concept / screenplay_beats / director_shot_plan
  -> material_generation_fallback.json
  -> external provider / imagegen / Gemini / Antigravity
  -> generated files re-ingested into material-map
  -> satisfies(candidate)
  -> material_delta fresh rerun
  -> reviewer accept / revision
  -> BUILD
```

Hard boundaries:

- `material_delta.ok=false` produces no jobs.
- Only `missing` / `thin` needs produce jobs.
- Generated assets enter as `candidate`, never `accepted`.
- Generated assets must carry `source_type=generated` and
  `must_not_claim_real_event=true`.
- This skill does not bypass M6 gate, material-map review, or Workbench
  canonical separation.

Practical use:

- Good for comic/photo stories, symbolic memory frames, chapter bridges,
  abstract transitions, and non-identifying reenactment inserts.
- Not valid for real-person proof, official speeches, identity-sensitive
  scenes, or event evidence.

### GMP1 Generated Material Producer Skill

Status: implemented / accepted for offline and provider-output material flow.

Purpose: execute MGF1 jobs into generated files and write the artifacts needed
for the material-map lifecycle to review them.

Canonical files:

- Skill: `skills/generated-material-producer.md`
- Tool: `video_tools.py generated-material-produce`
- Module: `video_pipeline_core/generated_material_producer.py`

Flow:

```text
material_generation_fallback.json + material_needs.json
  -> generated images / provider outputs
  -> generated_asset_manifest.json
  -> generated_material_maps/*.map.json
  -> project_material_map.json
  -> generated_material_quality_review.json
```

Hard boundaries:

- generated assets remain `source=generated`.
- generated assets are `candidate` satisfies edges, never accepted evidence.
- `test_pil` renderer is only an offline flow/proof renderer; final art should
  use Gemini / Antigravity / imagegen or another provider that writes the same
  output shape.
- quality review records explicit rubric dimensions: `story_fit`,
  `style_consistency`, `character_continuity`, `camera_language`,
  `truth_boundary`, and `need_coverage`. It is still not a human aesthetic
  sign-off.

### GMP2 Provider Output Intake + Style/Character Lock

Status: implemented / accepted for provider-output import.

Purpose: accept real generated files from GPT image / Gemini / Antigravity
without letting arbitrary files bypass material-map truth boundaries.

Canonical files:

- Tool: `video_tools.py generated-material-import`
- Module function:
  `generated_material_producer.produce_generated_materials_from_provider_outputs`
- Tests: `tests/test_generated_material_provider_intake.py`

Input shape:

```json
{
  "items": [
    {
      "job_id": "gen_hero",
      "file": "provider/hero-a.png",
      "provider": "codex_imagegen",
      "style_anchors": ["watercolor", "soft ink line"],
      "character_anchors": ["lead apprentice", "amber lantern"]
    }
  ]
}
```

Rules:

- every `job_id` must match a planned generation job.
- each job must provide at least `panel_count` readable image files.
- relative provider file paths resolve relative to the provider output JSON.
- style/character anchors declared by `style_profile.json` must be present in
  provider output metadata; mismatch fails the quality gate.
- successful imports still produce `candidate` material-map evidence only.

### GMP2.5 Real Image Provider Packet

Status: implemented / accepted for real image-provider handoff.

Purpose: force real generated-image work through explicit model/provider
execution instead of relying on the offline `test_pil` renderer.

Canonical files:

- Tool: `video_tools.py generated-image-provider-packet`
- Tool: `video_tools.py codex-imagegen-provider-fill`
- Module: `video_pipeline_core/generated_image_provider_packet.py`
- Tests: `tests/test_generated_image_provider_packet.py`
- Skill: `skills/generated-material-producer.md`

Flow:

```text
material_generation_fallback.json
  -> generated-image-provider-packet
  -> agent calls real image provider
  -> codex-imagegen-provider-fill OR manual generated_provider_outputs.json
  -> generated-material-import
  -> generated-material-review
```

Rules:

- the packet writes `generated_provider_packet.json`,
  `generated_provider_prompts.md`, and
  `generated_provider_outputs.template.json`;
- every panel gets a deterministic `target_file` under `provider_outputs/`;
- provider candidates can include Codex imagegen, Gemini, Antigravity, or other
  configured model tools;
- formal route acceptance requires explicit provider output mapping
  (`job_id -> file`) before `generated_provider_outputs.json` is accepted;
- copying from the newest `~/.codex/generated_images` session is allowed only
  for local smoke, not for formal route acceptance or final generated-material
  evidence;
- `test_pil` is rejected as a final-art provider in this path;
- the backend still does not trust model output until import + review pass.

### GMP2.6 Storyboard Panel-Locked Rendering Boundary

Status: documented / acceptance-proven.

Purpose: preserve story semantics for generated comic/photo narratives.

Evidence:

- Real Codex imagegen E2E produced 21 manga-style panels for
  `Rooftop Postcard`.
- Normal BUILD auto-fill made a technically valid story MV, but reused panels
  to fill long TTS narration.
- A panel-locked render stretched each image to its TTS segment duration,
  yielding a better comic/storybook video: one panel per narration beat,
  21/21 panels used exactly once.

Rule:

```text
storyboard_panel_locked=true
  -> one generated panel owns one narration/story beat
  -> stretch panel duration / Ken Burns for long voiceover
  -> generate more panels or shorten narration if visual support is too thin
  -> do not auto-fill with other accepted panels from the same need
```

Normal auto-fill remains correct for event MV / recap / course montage cases
where accepted shots under the same need are interchangeable enough to cover
duration.

### GMP3 Generated-Material Skill Acceptance Harness

Status: implemented / accepted for small generated-material flow replay.

Purpose: prove the generated-material skill can be driven from the beginning of
a small project, not just unit-tested in isolation.

Tool:

- `tools/generated_material_flow_acceptance.py`

Flow under test:

```text
material_needs.json with no material
  -> material_delta missing
  -> material_generation_fallback jobs
  -> generated_material_produce images/maps/review
  -> project_material_map with candidate satisfies
  -> material_delta rerun
  -> director-style score/report
```

Acceptance cases:

- `Rain Station Apprentice`: watercolor comic, lead apprentice + amber lantern,
  4 generated panels, score 88/100.
- `Rooftop Postcard`: manga watercolor, red scarf courier + postcard, 4
  generated panels, score 85/100.

Important reading: the expected post-generation state is `thin`, not `covered`,
because generated assets remain candidate until reviewer promotion.

### GMP4 Generated Candidate Review / Promotion

Status: implemented / accepted for generated candidate promotion.

Purpose: safely promote generated material-map candidates after explicit review.

Canonical files:

- Tool: `video_tools.py generated-material-review`
- Module: `video_pipeline_core/generated_material_review.py`
- Tests: `tests/test_generated_material_review.py`

Flow:

```text
project_material_map with generated candidate edges
  -> generated_material_review.json verdict
  -> reviewed_project_material_map.json
  -> material_delta fresh rerun
```

Rules:

- only generated `candidate` edges can be reviewed by this tool.
- each decision requires reviewer, reason, asset_id, scene_index, need_id, and
  status `accepted` or `rejected`.
- accepted edges can satisfy material_delta; rejected edges remain visible but
  do not count as coverage.
- unknown asset/scene/need, non-generated targets, bad status, or missing reason
  fails closed.

Acceptance harness update:

- `tools/generated_material_flow_acceptance.py` now applies an explicit review
  verdict in both comic cases.
- Post-generation delta: `thin=2`.
- Post-review delta: `covered=2`, `thin=0`.

## Next Phase — Effects / Brownfield Edit / Node14

Status: active next development direction.

Purpose: add tasteful, bounded visual effects now that material truth, generated
material fallback, Workbench draft review, and story-soul scaffolding are
stable enough. This is not a switch to a Remotion final renderer.

Canonical decision:

- `docs/decisions/2026-06-19-effects-node14-roadmap-alignment.md`

Current proven foundation:

- `effects-director` owns visual-style intent: color grade, title card,
  transition, and motion-graphic intent.
- `build_profile.render_profile` already supports `no_effects`,
  `light_effects`, and `motion_graphics`.
- `contract-run` can write `light_effects_plan.json`,
  `light_effects_manifest.json`, `light_effects_baseline_review.json`,
  `motion_graphics_contract.json`, `motion_graphics_render_plan.json`, and
  `motion_graphics_manifest.json` when enabled.
- Dashboard Brownfield/Node14 can surface effects artifacts and gaps.
- Workbench can show draft effect intent markers, but it is not the official
  final renderer.
- Remotion is installed and now has a bounded Brownfield/Node14 adapter
  foundation for prompt-driven effect authoring. It remains optional: canonical
  delivery stays ffmpeg / `contract-run`, and Remotion outputs must become
  reviewed artifacts before they can be composited.

Planned increments:

### FX0 Effects Status Cleanup

Goal: normalize docs and tests around current effect ownership before adding
new capabilities.

Acceptance:

- roadmap, effects-director, dashboard docs, and build-profile boundaries agree.
- Brownfield Edit is described as revision/effects orchestration, with Node14
  kept as the compatibility implementation node. It is not a mandatory render
  stage for every film.
- Remotion is explicitly optional / preview / reference only.

### FX1 Effect Asset Spec

Status: implemented / accepted for neutral effect contract.

Goal: define effect assets as first-class, reviewable material-like inputs
without mixing them with event evidence.

Expected artifacts:

- `effect_asset_spec.json`
- `effect_asset_manifest.json`
- `effect_intent_plan.json`

Canonical files:

- Tool: `video_tools.py effect-intent-plan`
- Module: `video_pipeline_core/effect_contract.py`
- Tests: `tests/test_effect_contract.py`

Rules:

- effect assets may be overlays, particles, light leaks, lower thirds,
  transition plates, title textures, or generated motion backgrounds.
- effect assets carry `asset_role=effect`, not event material coverage.
- generated effect assets must keep `source_type=generated` and must not satisfy
  real-event material needs.
- missing optional effects should warn, not block, unless the contract marks
  the effect as `required_for_story`.
- neutral SPEC forbids backend-specific fields such as Remotion component names,
  props, fps, or `durationFrames`; those belong to FX2/FX3 adapters.

### FX2 Effect Build Wiring

Status: implemented / accepted for first ffmpeg-backed E2E path; broader effect
recipe coverage remains active work.

Goal: make `light_effects` / `motion_graphics` build outputs visible and
measurable in real renders.

Implemented:

- `light_effects` can merge a validated FX1 `effect_intent_plan.json` into
  `light_effects_plan.json`.
- `video_tools.py light-effects-plan --effect-intent-plan ...` exposes the same
  path for offline planning.
- `contract-run` can consume an explicit top-level `effect_intent_plan_ref`
  when `render_profile=light_effects` or `effects_enabled=true`.
- Declared `effect_intent_plan_ref` is strict and fail-closed: missing,
  malformed, or invalid plans stop before render with
  `stage=effect_intent_plan` and `next_action=revise:effects(effect_intent_plan)`.
- Effects that do not allow `ffmpeg_light_effects` are preserved as
  `external_effect` / `pending_backend`, making the Brownfield/Node14 or
  Remotion adapter gap visible instead of pretending it rendered.
- `motion_graphics` can project ffmpeg-safe `title_card` / `lower_third`
  effect intents into timed ASS overlays using the actual BUILD timeline.
- E2E regression proves `effect_intent_plan_ref -> contract-run -> final.mp4`
  with one composited lower-third and one explicit Remotion-only gap.

Acceptance:

- an enabled `light_effects` build writes plan, manifest, baseline review, and
  at least one visible rendered effect in a real ffmpeg output. **Met for
  lower-third via `tests/test_effects_e2e.py`.**
- effect outputs are traced back to segment/clip/effect id. **Met for
  `source_effect_id`.**
- no duplicate text burn: canonical text ownership remains singular.
- failed effect render produces a Brownfield-visible gap instead of pretending
  success. **Met for `external_effect` / pending backend.**

### FX3 Brownfield Edit / Node14 Revision Orchestration

Goal: use Brownfield Edit for local effect fixes, Workbench patches, optional
finishing adjustments, and reviewed second-build handoff without restarting the
whole pipeline. Node14 remains the compatibility implementation node for
existing effect revision artifacts.

Status: **FX3a COMPLETE (2026-06-19)** for deterministic effect gap routing.

Acceptance:

- `light_effects_baseline_review.json` gaps can be converted into
  `effect_revision_request.json` by:

  ```bash
  python video_tools.py effect-revision-request \
    --baseline-review light_effects_baseline_review.json \
    --light-effects-plan light_effects_plan.json \
    --out effect_revision_request.json
  ```

- Route semantics are bounded:
  - ffmpeg-safe missing render outputs -> `implement_or_wire_effect_recipe`;
  - `external_effect` / pending backend outputs -> `route_to_node14_or_remotion_adapter`.
- The artifact is a Node14 request list only. It does **not** render, mutate
  `final.mp4`, patch canonical `effect_intent_plan.json`, or invoke Remotion.
- Dashboard/Node14 reads `effect_revision_request.json`; pending requests take
  precedence over the raw baseline gap warning.
- Real E2E evidence: `tests/test_effects_e2e.py` proves a lower-third renders,
  while the Remotion-only page-turn gap becomes a Node14 adapter request.

Status: **FX3b COMPLETE (2026-06-19)** for request-to-draft conversion.

- `effect_revision_request.json` can be converted into non-canonical draft
  artifacts by:

  ```bash
  python video_tools.py effect-revision-draft \
    --request effect_revision_request.json \
    --out-patch effect_recipe_patch.json \
    --effect-intent-plan effect_intent_plan.json \
    --out-intent-draft revised_effect_intent_plan.draft.json
  ```

- `effect_recipe_patch.json` is a Node14 review artifact only. It proposes
  `wire_effect_recipe` or `build_node14_adapter`, but does not render or mutate
  canonical inputs.
- `revised_effect_intent_plan.draft.json` is a wrapper around a validator-clean
  inner `effect_intent_plan`; it is explicitly `draft_only`.
- Dashboard/Node14 surfaces pending `effect_recipe_patch.json` before pending
  `effect_revision_request.json`.

Status: **FX3c COMPLETE (2026-06-19)** for explicit reviewed draft application.

- `revised_effect_intent_plan.draft.json` can be reviewed into a separate
  canonical effect-intent plan by:

  ```bash
  python video_tools.py effect-revision-apply \
    --draft revised_effect_intent_plan.draft.json \
    --out effect_intent_plan.reviewed.json \
    --reviewer REVIEWER \
    --reason "accepted Node14 effect draft" \
    --accept
  ```

- The command fails closed without `--accept`, a non-empty reviewer, and a
  non-empty reason.
- The original `effect_intent_plan.json` and draft wrapper are never overwritten.
- E2E evidence: `tests/test_effects_e2e.py` runs
  `effect_intent_plan_ref -> contract-run -> baseline gap -> revision request
  -> revised draft -> explicit reviewed apply -> second contract-run`.
- The second render proves the reviewed plan is consumable by canonical BUILD.
  It does **not** claim the unresolved Remotion adapter gap is implemented.

Still deferred:

- Workbench draft effect-intent ingestion into Node14 request artifacts.
- Automatic overwrite/application of revised `effect_intent_plan.json` into the
  original canonical input.
- Canonical Remotion/Node14 delivery integration.

### FX4 Remotion Prompt-Driven Adapter Boundary

Goal: use Remotion where it is strongest: prompt-driven opening/title/transition
and overlay authoring inside Brownfield Edit, without making it a required main
BUILD dependency.

Rules:

- Do not make Remotion a required dependency for normal BUILD.
- Do not claim browser preview equals final ffmpeg output unless a specific
  effect has a parity test.
- Prompt is payload, not pipeline logic. The stable handoff is:
  `effect_revision_request.json` -> `remotion_prompt_pack.json` ->
  `remotion_worker_outputs.json` -> `remotion_effect_review.json`.
- Worker outputs are review candidates only. Unreviewed Remotion files must not
  enter canonical delivery.
- If a Remotion component/output is useful, export it as a reviewed effect asset
  or reviewed effect plan before final ffmpeg composite.

Status: **FX4a-FX4e COMPLETE (2026-06-20)** for adapter artifact contracts,
optional worker smoke, true Remotion worker bridge, and non-canonical draft
composite.

Implemented:

- `video_pipeline_core/remotion_effects.py`
- `python video_tools.py remotion-prompt-pack --request effect_revision_request.json --effect-intent-plan effect_intent_plan.json [--timeline timeline_build.json] --out remotion_prompt_pack.json`
- `python video_tools.py remotion-worker-smoke --prompt-pack remotion_prompt_pack.json --out-dir remotion_effects --out-worker-outputs remotion_worker_outputs.json [--command "..."]`
- `python video_tools.py remotion-worker-outputs --prompt-pack remotion_prompt_pack.json --worker-outputs remotion_worker_outputs.json --out-review remotion_effect_review.json`
- `python video_tools.py remotion-composite-draft --review remotion_effect_review.json --base-video workbench_export.mp4 --out remotion_composite_draft.mp4 --report-out remotion_composite_report.json`
- `node tools/remotion_worker_bridge.mjs --job-json JOB.json --preview-file PREVIEW.mp4 --rendered-asset OVERLAY.mov --project-root REMOTION_PROJECT --remotion-bin REMOTION_BIN`

Artifact semantics:

- `remotion_prompt_pack.json` converts only
  `route_to_node14_or_remotion_adapter` gaps into prompt jobs. ffmpeg recipe
  gaps stay in FX3.
- Jobs include source effect id, role, component family, prompt, timing, output
  target hints, and acceptance criteria.
- `remotion_worker_outputs.json` is produced by an external Remotion-capable
  worker/agent. `remotion-worker-smoke` can run an explicit worker command, or
  a dry-run for contract smoke tests. Validation fails closed on unknown job ids,
  missing files, bad durations, duplicate jobs, or malformed status.
- `tools/remotion_worker_bridge.mjs` is the bounded optional worker command used
  in local FX4e acceptance. It converts a prompt-pack job JSON into a Remotion
  composition, renders a ProRes alpha overlay plus h264 preview, and refuses
  protected canonical outputs.
- `remotion_effect_review.json` is the Workbench/Brownfield review artifact.
  It does not accept the output into BUILD by itself.
- `remotion-composite-draft` consumes only accepted `remotion_effect_review`
  items and writes a non-canonical draft video. It refuses protected canonical
  outputs such as `final.mp4`.

Deferred inside effects:

- full Remotion-like final renderer;
- arbitrary free-form VFX without a prompt-pack/review contract;
- paid/closed CapCut effect packs as required dependencies;
- automatic Remotion output promotion into canonical delivery without review;
- full Audio Graph V2.

## Stable Foundations — Do Not Reopen Without Evidence

These areas are considered settled unless a fresh run proves a contract bug:

- M6 material-map lifecycle and gate: `docs/material-map-lifecycle.md`
- Native preview / Workbench draft layer:
  `docs/decisions/2026-06-16-native-preview-engine.md`
- Dashboard/Workbench integration:
  `docs/workbench-dashboard-integration.md`
- Tool/run layout consolidation:
  `docs/repository-consolidation-map.md`,
  `docs/decisions/2026-06-17-tool-surface-and-run-layout-consolidation.md`
- Effects baseline and current gap reporting:
  `docs/decisions/2026-06-11-effects-baseline-and-recipe-order.md`
- Working loop and TDD evidence rules:
  `docs/decisions/2026-06-14-working-loop-and-tdd-evidence.md`

## Deferred / Later

These remain intentionally deferred until a concrete run proves they are needed:

- Deep semantic function vocabulary F2.
- VD3 or advanced visual understanding.
- Remotion-like final renderer.
- Arbitrary free-form advanced VFX.
- Full Audio Graph V2.
- Dashboard OAuth / hosted runtime control.
- Large repo/module refactors that do not directly unblock a user-visible flow.

## Historical Archive

The previous long-form roadmap was archived losslessly here:

- `docs/roadmap-history/2026-06-18-roadmap-pre-split.md`

Use it for evidence only. It contains historical sections for:

- Material phase M0-M6 and MM/BR/VD/MR/SRP work.
- Sensory phase S1-S4.
- Effects phase E1-E7.
- Convergence work C0-C6.
- Windows migration and early VERIFY tool packs.
- Native preview / Workbench / effect / operator-flow acceptance notes.

The archive is not current instruction unless this roadmap or a current decision
document links to a specific section.

## Current Engineering Rule

When adding new work:

1. Put creative intent above the material-map lifecycle.
2. Keep runtime contracts deterministic and testable.
3. Do not mix historical roadmap text into active instructions.
4. Add a short decision doc for significant architecture changes.
5. Run focused tests and relevant full regression before claiming completion.
