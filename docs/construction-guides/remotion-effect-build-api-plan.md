# Remotion Effect Build API Construction Plan

## Purpose

This guide defines the construction path for the Brownfield Remotion effects line.
The goal is not to add more attractive one-off templates. The goal is to make
effects controllable by story, material review, visual technique parameters,
and build parameters.

Current problem:

```text
thin upstream understanding
-> thin prompt parameters
-> conservative worker templates
-> attractive demos that do not necessarily serve the edit
```

Target shape:

```text
semantic visual request / material wall / montage review
-> visual_technique_plan.json
-> effect_intent_plan.effects[].prompt_parameters
-> Remotion component worker
-> preview + contact sheet + review gate
```

Remotion remains a bounded effect asset producer. It must not own `final.mp4`,
material-map decisions, rough-cut selection, or segment contract rewriting.

For v1, keep the route small:

- v1 control surface is `effect_build_spec` inside existing `prompt_parameters`.
- `visual_technique_plan.json` is the upstream translation artifact. It converts
  natural-language style intent into visual primitives, motion primitives,
  render strategy candidates, and controls.
- Existing template dictionaries are examples / known treatments. They are not
  the semantic source of truth.
- The Remotion worker still receives concrete controls through existing
  `effect_intent_plan.effects[].prompt_parameters`.

Do not add `effect_story_planner.json` to the current mainline artifact chain.
`effect_story_planner.json` is a future optional extraction only if the upstream
planning role grows beyond the technique translator.

## Design Boundary

### Upstream understanding

Upstream is allowed to be fuzzy, but it must provide enough context:

- story function: emotional setup, recap memory, profile moment, transition build,
  montage acceleration, closing reflection
- material profile: photos, videos, vertical footage, group shots, speaker shots,
  low-information stills
- pacing intent: slow, medium, fast
- density intent: low, medium, high
- reviewed material refs and optional reviewer notes
- desired viewer feeling

Upstream does not decide frame-by-frame animation. It decides the technique
language: style family, visual primitives, motion primitives, render strategy,
and controls. The worker decides how to implement those controls frame by frame.

### Existing templates are examples

The existing files below are useful, but they are not the main translation
dictionary:

- `examples/training_recap_effect_dictionary.json`
- `examples/remotion_effect_capability_manifest.json`
- prior runs under `runs/remotion_category_boundary/`
- prior runs under `runs/remotion_visual_quality/`

Treat them as example treatments and capability evidence. A semantic request
such as "日式櫻花飄逸" should first become a technique plan such as particles,
drift, fall, parallax, soft palette, and canvas/Three render strategy. It should
not be forced into a fixed training recap template unless that template is a
natural match.

## Contract-First Flow

Do not add a new Remotion component just because a probe looks attractive. The
route must move in this order:

1. Convert fuzzy direction into structured `effect_build_spec` parameters.
2. Validate the spec against a small supported component registry.
3. Preserve the spec inside existing `prompt_parameters`.
4. Let `remotion_prompt_pack.json` carry it into the worker.
5. Render only a short preview / effect asset.
6. Produce contact sheet, keyframes, and review report.
7. Convert accepted review into `effect_render_verification.json`.
8. Promote the pattern back into the Brownfield pipeline only after evidence is
   reviewable.

Unsupported components must fail closed. The worker must not silently treat a
new effect name as a generic template.

Current supported build-spec components:

| component | Purpose | Main template |
| --- | --- | --- |
| `MemoryPhotoWall` | slow emotional photo wall / recap memory setup | `memory_photo_wall` |
| `StoryToMVTransition` | story half to MV / montage pacing shift | `film_strip_transition_card` |

Common neutral parameters should stay reusable:

- `story_function`: opening emotion, memory recap, chapter transition,
  montage acceleration, closing reflection
- `pacing`: slow / medium / fast
- `density`: low / medium / high
- `reveal_mode`: one_by_one / cascade / full_plate
- `camera_motion`: slow_push_in / static / drift
- `accent_light`: soft_warm / none / highlight

Component-specific fields are allowed only after the generic intent is clear.
For example, `impact_moment_sec` belongs to `StoryToMVTransition`; it should not
become a global field for unrelated overlays.

### Effect story planner role

The planner is currently a role, not a required artifact. It translates fuzzy
understanding into an effect role and then writes that decision into
`effect_build_spec` under existing `prompt_parameters`.

Example future standalone shape:

```json
{
  "segment_id": "opening_memory",
  "story_function": "emotional_setup",
  "material_profile": "mostly_photos_group_and_training",
  "pacing": "slow",
  "density": "low",
  "effect_role": "memory_photo_wall",
  "duration_sec": 10
}
```

Do not implement this as a new file in v1 unless the mainline contract has
already proven too cramped. Keeping the control surface in
`prompt_parameters.effect_build_spec` is what prevents a parallel Remotion
route from forming.

### Effect build spec

Build spec is the precise worker control surface:

```json
{
  "artifact_role": "effect_build_spec",
  "version": 1,
  "effects": [
    {
      "effect_id": "fx_memory_wall_01",
      "component": "MemoryPhotoWall",
      "duration_sec": 10,
      "material_refs": [],
      "story_function": "emotional_setup",
      "pacing": "slow",
      "density": "low",
      "reveal_mode": "one_by_one",
      "reveal_interval_sec": 1.2,
      "hold_after_full_wall_sec": 2.0,
      "camera_motion": "slow_push_in",
      "caption_mode": "minimal",
      "accent_light": "soft_warm",
      "exit_transition": "soft_light"
    }
  ]
}
```

### Remotion worker

Worker executes the build spec. It may understand Remotion timing and composition
rules, but it must not become the director:

- convert seconds to frames
- sequence photos with frame-accurate timing
- derive layout from density and media count
- derive easing from pacing
- render preview and transparent/rendered asset
- produce contact sheet/keyframes for review

It must not approve material truth or silently replace missing story intent.

## First Component: MemoryPhotoWall v1

This is the first hardening target because it directly serves Brownfield edits.
It tests material refs, timing, pacing, density, emotional reveal, contact-sheet
review, and Remotion parameterization.

Required parameters:

```json
{
  "component": "MemoryPhotoWall",
  "duration_sec": 6,
  "material_refs": [
    {
      "ref_id": "group_photo",
      "path": "reviewed_stills/group_photo.jpg",
      "label": "班級合照",
      "visual_role": "people_group"
    }
  ],
  "story_function": "emotional_setup",
  "pacing": "slow",
  "density": "low",
  "reveal_mode": "one_by_one",
  "camera_motion": "slow_push_in",
  "caption_mode": "minimal",
  "accent_light": "soft_warm"
}
```

Worker-derived behavior:

- `duration_sec` controls composition duration.
- `pacing=slow` uses long reveal intervals and editorial ease-in-out.
- `density=low` shows fewer, larger cards with more negative space.
- `reveal_mode=one_by_one` makes contact sheets show visible progression.
- `camera_motion=slow_push_in` applies a gentle global scale/drift.
- `caption_mode=minimal` limits text to small labels or one short title.
- `accent_light=soft_warm` adds restrained warmth without hiding proof imagery.

## Second Component: StoryToMVTransition v1

This component handles the common training-recap shift from story setup into a
more rhythmic MV / montage section. It should not behave like a static chapter
card. It must communicate a pacing change.

Required parameters:

```json
{
  "component": "StoryToMVTransition",
  "duration_sec": 4,
  "section_from": "story",
  "section_to": "montage",
  "pacing_shift": "slow_to_fast",
  "impact_moment_sec": 2.2,
  "thumbnail_acceleration": "medium",
  "motion_grammar": [
    "film_rail",
    "thumbnail_acceleration",
    "flash_wipe",
    "hard_cut_bars"
  ],
  "phase_labels": ["STORY", "MONTAGE"],
  "light_sweep": "warm",
  "film_strip_motion": "accelerating",
  "caption_mode": "phase_labels"
}
```

Worker-derived behavior:

- `duration_sec` controls composition duration.
- `section_from` and `section_to` control readable phase labels.
- `pacing_shift=slow_to_fast` increases motion energy after the impact moment.
- `impact_moment_sec` controls the flash / shutter / hard-bar timing.
- `thumbnail_acceleration` controls thumbnail rail speed and motion trail.
- `motion_grammar` gates optional layers so the worker can be strong without
  being unbounded.
- `light_sweep=warm` adds a transition sweep but must not hide source imagery.
- `caption_mode=phase_labels` keeps text functional instead of decorative.

This component initially maps to the existing `film_strip_transition_card`
template and `story_to_mv_film_transition` variant. The build spec is the
preferred control surface; the older prompt fields remain compatible.

## Initial API Mapping

`effect_intent_plan.effects[].prompt_parameters.effect_build_spec` may carry the
build spec into the existing prompt-pack path. The prompt-pack should preserve it
inside:

```text
remotion_prompt_pack.jobs[].props.prompt_parameters.effect_build_spec
```

The worker then exposes it as:

```js
JOB.promptParameters.effect_build_spec
```

This keeps the current route intact while making the build surface explicit.

For Brownfield material-first runs, reviewed media refs may arrive from two
places:

- `remotion_prompt_pack.jobs[].props.collage_media_refs`
- `remotion_prompt_pack.jobs[].props.prompt_parameters.effect_build_spec.material_refs`

`MemoryPhotoWall` treats the build-spec `material_refs` as the authoritative
fallback when `collage_media_refs` is empty. This keeps the effect contract in
the existing `prompt_parameters` channel while still allowing older collage
templates to use the legacy field.

For video assets, do not pass full source clips into the photo-wall contract.
Use the reviewed keyframes that already exist in `material_wall_request.json`.
The intended bridge is:

```text
material_wall_request.batches[].assets[].frames[].image_path
-> effect_collage_media_refs.collage_media_refs[].path
-> effect_build_spec.material_refs[]
-> Remotion worker entry data images
```

Future work may promote `effect_build_spec.json` to a standalone artifact once
the first component is stable.

The mainline artifact chain remains:

```text
effect_intent_plan.json
-> effect_revision_request.json
-> remotion_prompt_pack.json
-> remotion_worker_outputs.json
-> remotion_effect_review.json
-> effect_render_verification.json
-> remotion_effect_handoff.json
-> optional remotion_composite_draft.mp4
-> ffmpeg / contract-run final assembly
```

## Tests First

Required focused tests:

1. Prompt pack preserves `effect_build_spec`.
2. Worker entry for `MemoryPhotoWall` includes:
   - `isMemoryPhotoWall`
   - `memoryWallSlots`
   - `memoryRevealIntervalFrames`
   - `holdAfterFullWallFrames`
   - `slowPushInScale`
   - `minimalCaption`
   - media refs embedded as data URLs when local files are small
3. One-by-one reveal cannot collapse into all photos appearing at frame 0.
4. Unknown extreme effects must not be falsely claimed as supported renderers.
5. Worker entry for `StoryToMVTransition` includes:
   - `isStoryToMvBuildSpec`
   - `storyToMvPhaseLabels`
   - `buildSpecMotionGrammar`
   - `impactMomentFrame`
   - `thumbnailAccelerationStrength`
   - `pacingShift`
   - film rail / flash / hard bar layers gated by the build spec

## Probe And Review

Use a short Brownfield probe, not a full E2E:

```text
runs/remotion_memory_photo_wall_probe/<timestamp>
```

Use existing reviewed stills when available:

```text
runs/remotion_real_spec_training_link/20260624-training-link-v1/reviewed_stills
```

Use material-wall reviewed video keyframes when the source is mostly video:

```powershell
python video_tools.py effect-collage-refs `
  --project-map project_material_map.json `
  --wall-verdict material_wall_review_verdict.json `
  --wall-request material_wall_request.json `
  --out effect_collage_media_refs.json
```

The `--wall-request` input is important for video-heavy Brownfield projects
because the material wall already contains selected keyframes. Without it, a
video-only material map can pass review but still produce no usable photo-wall
refs.

Outputs to keep:

- `effect_intent_plan.json`
- `effect_revision_request.json`
- `timeline_build.json`
- `remotion_prompt_pack.json`
- `jobs/*.json`
- `*.preview.mp4`
- `remotion_visual_probe.html`
- `remotion_contact_sheet.svg`
- contact sheet / keyframe images
- review report

Worker output acceptance is fail-closed:

- every rendered job must match a prompt-pack `job_id`
- every rendered job must include `preview_file`
- every rendered job must include `rendered_asset`
- every rendered job must include at least one existing `evidence_refs[]` file
- evidence should normally be a contact sheet or keyframe image

If a worker creates video files but no review evidence, it is not reviewable and
must not become a pending Workbench review item.

After Workbench/Brownfield review accepts the Remotion output, convert it into
delivery-gate evidence:

```powershell
python video_tools.py effect-render-verification `
  --effect-intent-plan effect_intent_plan.json `
  --remotion-review remotion_effect_review.json `
  --out effect_render_verification.json `
  --root RUN_DIR
```

This artifact is the bridge from Remotion review into
`delivery_gate.evaluate_complete_video_delivery`. It must list each planned
effect, whether it was rendered, and the evidence refs that prove it can be
reviewed. Missing accepted review items or missing evidence keep `pass=false`.

Current material-first probe:

```text
runs/remotion_material_first_memory_probe/20260625-000000
```

Verified boundary:

- material-wall video keyframes produced `effect_collage_media_refs`
- `effect_build_spec.material_refs` preserved those refs
- Remotion worker entry embedded three material-wall keyframes as data images
- dry-run worker output produced review evidence
- `remotion_visual_probe.html` and `remotion_contact_sheet.svg` showed the
  same refs through a review-only visual probe
- accepted review produced passing `effect_render_verification.json`
- no `final.mp4` was written

Formal material-first boundary harness:

```powershell
python tools/remotion_material_first_memory_acceptance.py `
  --run-dir runs/remotion_material_first_memory_acceptance/<timestamp> `
  --project-map project_material_map.json `
  --wall-verdict material_wall_review_verdict.json `
  --wall-request verify/material_wall/material_wall_request.json `
  --max-refs 3 `
  --json
```

This harness is the repeatable acceptance check for the minimal bridge. It
writes:

- `effect_collage_media_refs.json`
- `effect_intent_plan.json`
- `effect_revision_request.json`
- `timeline_build.json`
- `remotion_prompt_pack.json`
- `remotion_worker_outputs.json`
- `remotion_effect_review.json`
- `effect_render_verification.json`
- `remotion_effect_handoff.json`
- `remotion_visual_probe.html`
- `remotion_contact_sheet.svg`
- `remotion_material_first_memory_acceptance_report.json`

It must not write `final.mp4`, must not run `contract-run`, and must not
composite a draft. It is an artifact-chain gate plus a review-only visual probe,
not final delivery.

`remotion_effect_handoff.json` is the promotion surface for later Workbench or
ffmpeg adoption. It must declare:

- `artifact_role=remotion_effect_handoff`;
- `boundary.role=bounded_finishing_asset_producer`;
- `boundary.owns_final_delivery=false`;
- `boundary.owns_material_truth=false`;
- accepted Remotion assets and evidence refs;
- preview/contact-sheet evidence;
- `next_action=human_review_or_promote_effect_assets_to_ffmpeg_timeline`.

The handoff is not a delivery-pass artifact. It only says which reviewed
finishing assets are available.

Latest real-run evidence:

```text
runs/remotion_material_first_memory_acceptance/20260625-000000
```

That run selected three `material_wall_keyframe` refs, produced one
`MemoryPhotoWall` prompt-pack job, accepted the dry-run worker evidence, wrote
`remotion_visual_probe.html` / `remotion_contact_sheet.svg`, and produced
passing `effect_render_verification.json` plus `remotion_effect_handoff.json`.

State visibility:

- `tools/pipeline_home.py --run <RUN_DIR> --json` must surface
  `source=remotion_material_first_memory_acceptance_report.json` and include
  `remotion_effect_handoff.json` in `read` when it exists.
- `video_pipeline_core.dashboard_state.load_dashboard_state(<RUN_DIR>)` must
  surface the report under
  `artifacts.remotion_material_first_memory_acceptance_report` and the handoff
  under `artifacts.remotion_effect_handoff`.
- A passed report sets dashboard `next_action` to
  `ready_for_human_effect_review_or_pipeline_promotion`, but `run.pass` remains
  false because this is not final delivery.
- A failed report sets dashboard `next_action` from the report and emits an
  error finding for `remotion_material_first_memory_acceptance_report`.

Outputs to clean after review:

- `.mov` intermediates
- `remotion_project`

## Done Criteria For v1

MemoryPhotoWall v1 is acceptable when:

- contract artifacts can drive the component without free-form manual edits
- preview duration is 6-12 seconds and matches build spec
- contact sheet clearly shows sequential reveal progression
- photos are readable and not hidden by effects
- the result is visibly different from the old fast collage/title template
- focused unit tests pass
- `node --check tools/remotion_worker_bridge.mjs` passes
- no `final.mp4` is written
