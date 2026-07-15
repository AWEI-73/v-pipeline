# Work Order: Canon 67 L1 v3 renderability and MemoryPhotoWall bounded correction

## Goal and source

Correct the two verified failures from the integrator review of Canon 67 L1 v2:

1. the proposed 540-second picture plan assigns 78.551 seconds more timeline time than seven selected video windows can supply;
2. the 40-second `MemoryPhotoWall` preview ignores `final_group_photo_ref` and `final_copy.start_sec`, keeps the card wall during the final hold, and shows generic per-card captions.

Construction sources:

- `docs/construction-guides/work-orders/2026-07-14-canon67-l1-quality-window-memory-ending-revision.md`
- `docs/decisions/2026-07-14-canon67-teacher-all-or-none-memory-ending.md`
- `.tmp/canon67_540s_route_acceptance/stage5/l1_revision_v2/l1_picture_plan_v2.proposed.json`
- `.tmp/canon67_540s_route_acceptance/stage5/effects/seg10_memory_ending/effect_contract_seg10_memory_photo_wall_v2.proposed.json`
- the selected integrator review finding on `tools/remotion_worker_bridge.mjs:2117-2133`

This is a bounded correction. It does not authorize a full 540-second render, audio, subtitles, delivery, upload, registry promotion, or a new route/template family.

## Frozen evidence

- L1 v2 picture plan SHA-256: `6000e6974090f588d215407b3566cb98268118c00beb2ede2101cb620fd75195`
- seg10 v2 preview SHA-256: `7bcf000355532beec5b7b20f28ec998099b2563c93b51b0d0d195750e8db4712`
- `material_retrieval.py` SHA-256: `ca4e884864cb924888fff3f5c14a1c3984182d8a48599b4e8ab4048c300f8734`
- pre-work `remotion_worker_bridge.mjs` SHA-256: `7cfc0aa02522bf9b42de67193bbe38f4501a1cd1026b893c3956252615aa8ccc`
- pre-work bridge working-tree diff, default PowerShell pipeline command
  `git diff -- tools/remotion_worker_bridge.mjs | git hash-object --stdin`:
  `48e5a139e80983ead6000870a13d4c1a8a3f4c5b`
- the semantically equivalent binary/no-color serialization
  `git diff --no-ext-diff --no-color --binary -- tools/remotion_worker_bridge.mjs`
  may hash as `73ac4f4a85ddfc5ce1edb51e174188cdeea7e6c7`; this is an accepted
  serialization difference, not source drift
- `effect_layer_manifest.py` SHA-256: `1e13e50c0f535eec44402ef8a7cbf9b1e8873661590806de7b7fb7ddcf42ae34`
- `tests/test_remotion_worker_bridge.py` SHA-256: `a5f85845b92a13bd5537faa91b433bdd106c5dd5b31a17af937f534c6f90cd21`

Before editing, copy the current bridge and its `git diff` into the approved run-local evidence directory. These copies are evidence only and must not replace production files. The bridge file SHA-256, diff content, and `216 additions / 2 deletions` numstat are authoritative. A diff-object hash alone must not trigger stop-loss when those three checks match and the diff contains only the frozen `silk_stream` hunks.

## Owner zone

- `tools/remotion_worker_bridge.mjs`, limited to the existing `MemoryPhotoWall` implementation and the minimum conditional text-visibility expression it requires
- `tests/test_remotion_worker_bridge.py`, limited to the existing MemoryPhotoWall fixture/tests
- `.tmp/canon67_540s_route_acceptance/stage5/l1_revision_v3/**`
- `.tmp/canon67_540s_route_acceptance/stage5/effects/seg10_memory_ending_v3/**`

## Read-only / forbidden zone

- `video_pipeline_core/effect_layer_manifest.py`; its existing `silk_stream` change is unrelated and frozen
- every existing `silk_stream` hunk in `tools/remotion_worker_bridge.mjs`
- `video_pipeline_core/material_retrieval.py` and all retrieval/ranking production code
- all skills, registries, capability dictionaries, route runners, material maps, source media, v1/v2 artifacts, audio/subtitle code, `RUNBOOK.md`, `HANDOFF_CURRENT.md`, and `docs/INDEX.md`
- no new renderer, template family, route, helper tool, test file, `rough_cut_plan.json`, full candidate, `final.mp4`, upload, stage, commit, push, reset, cleanup, or full suite

## Ordered outcomes

### 1. Freeze and reproduce

- Verify every frozen hash above before editing.
- Reproduce the v2 duration defect from the plan: usable selected-window total `461.452`, planned total `540.0`, seven short clips, shortfall `78.551`.
- Preserve the v2 preview and a contact sheet proving that text appears before 32 seconds and the final hold remains a multi-card wall.

### 2. Red-first MemoryPhotoWall contract

Extend the existing MemoryPhotoWall test fixture with a 40-second contract containing:

- `phase_schedule` for enter, accumulate, converge, and final hold;
- `final_group_photo_ref`;
- `final_copy.line_1`, `line_2`, `start_sec=32`, `end_sec=40`;
- `caption_mode=none`.

Before the production edit, focused tests must fail because the generated entry does not implement:

- final-photo lookup by reviewed ref;
- 20–32 second convergence progress;
- a single final hero layer from 32 seconds;
- final-copy visibility restricted to its configured interval;
- suppression of per-card captions when caption mode is `none`.

Capture the red command, exit code, and failure tail.

### 3. Smallest MemoryPhotoWall implementation

Modify only the existing MemoryPhotoWall branch and its minimum text-opacity condition:

- keep 0–8 seconds as one-by-one reviewed photo entry;
- retain a restrained wall through 8–20 seconds;
- during 20–32 seconds, fade non-hero cards and move/scale the configured final photo toward the center;
- during 32–40 seconds, show only the configured final group photograph as the dominant hero image;
- use containment or another face-safe treatment; do not crop faces to fill the frame;
- hide both approved text lines before 32 seconds, fade them in after 32 seconds, and hide them after the configured end;
- render no per-card machine caption when `caption_mode=none`;
- keep the generic legacy MemoryPhotoWall behavior compatible when no final-photo/final-copy fields are supplied.

Do not touch `silk_stream`, the layer manifest, or generic effect registration.

### 4. Build an executable L1 v3 proposal

Starting from frozen v2 evidence, write a new proposal under `l1_revision_v3` using the existing ranker, diversity selector, `plan_ranked_windows`, and source-highlight evidence.

- Keep the accepted section durations: `30,45,55,95,105,45,65,60,0,40`.
- Keep seg09 at zero, seg10 at 40, and teacher/adviser selected count at zero.
- Do not inflate `duration_sec` or copy `planned_duration_sec` over a shorter video window.
- For every video clip, require `planned_duration_sec <= duration_sec`.
- Fill missing time with additional reviewed ranked assets or distinct non-overlapping evidenced windows. A reviewed photo may hold only with explicit `still_treatment`.
- Do not repeat an identical source window. A source may appear twice only when the windows do not overlap and have different documented story/action roles.
- Preserve setup/action/result causality inside technical sections.
- Select no unresolved story-function asset. Any `direct_story_evidence=false` selection still requires an explicit scarcity reason and evidence refs.
- The sum of all planned clip durations must equal exactly 540 seconds, and total renderable capacity must be at least 540 seconds.

Produce:

- `l1_picture_plan_v3.proposed.json`
- ranking and source-window reports
- `renderable_duration_capacity_report_v3.proposed.json`
- review-only storyboard plan and silent storyboard preview
- owner review index and verdict template

Do not mutate v2.

### 5. Render only the corrected 40-second seg10 preview

Create a new v3 effect packet beside, not over, v2. Use only the same five reviewed material refs and the existing Remotion worker bridge.

- Set `caption_mode=none`.
- Keep approved copy unchanged:
  - `最後一次，站成一個集體`
  - `下一站，各自把責任接住`
- Render a silent 1920x1080 40-second review preview and bounded rendered effect asset.
- Extract evidence frames at approximately 0, 8, 20, 28, 32, 36, and 39 seconds and assemble one contact sheet.
- The preview remains review-only: `production_handoff_allowed=false`, `human_creative_approval=false`, and `final_delivery_claimed=false`.

Do not rerun the legacy material-first dry-run as delivery acceptance; it cannot prove rendered phase behavior.

### 6. Acceptance packet and stop state

Write a v3 acceptance JSON that fails closed on:

- any video duration over-allocation;
- renderable capacity below 540 seconds;
- seg09/seg10/teacher-gate drift;
- unresolved selected material;
- missing effect frames or incorrect media duration/audio policy;
- missing configured final-photo/final-copy fields.

Stop at `WAITING_INTEGRATOR_L1_V3_STORYBOARD_AND_MEMORY_ENDING_REVIEW`. Do not claim owner taste approval or production handoff.

## Acceptance commands and evidence

Expected green commands:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_remotion_worker_bridge -v
C:\Users\user\miniconda3\python.exe -m unittest tests.test_remotion_effects tests.test_effect_build_spec -v
C:\Users\user\miniconda3\python.exe -m unittest tests.test_canon67_l1_quality_ranking tests.test_material_retrieval tests.test_picture_plan_retrieval_gate -v
git diff --check -- tools/remotion_worker_bridge.mjs tests/test_remotion_worker_bridge.py
```

All must exit `0`. Do not run the full suite.

The plan read-back must prove:

- exact 540.000 planned seconds;
- zero video clips where `planned_duration_sec > duration_sec`;
- zero unresolved selected clips;
- seg09=0, seg10=40, teacher/adviser selected=0;
- no repeated identical source window.

The effect read-back must prove:

- 40.000-second video, 1920x1080, no audio;
- source hashes still match the five reviewed refs;
- the generated entry contains the final-photo, convergence, and timed-copy implementation;
- the seven-frame contact sheet exists for integrator visual review.

## Stop-loss and report

One repair attempt per failure class. Stop at the last green state if:

- any authoritative frozen file/artifact hash drifts before editing; the two accepted bridge diff serializations above are not drift;
- a required edit falls outside the owner zone;
- reaching 540 seconds would require fake duration, duplicated windows, unreviewed media, or source mutation;
- the MemoryPhotoWall change requires registry, manifest, generic-layer, or route changes;
- a failure class recurs after one repair.

The report must contain exact changed files, pre/post hashes, the isolated bridge diff against its frozen pre-work copy, red/green commands and exit codes, artifact paths/hashes, plan capacity figures, deviations/skips/blockers, and the exact final dirty-tree status. Explicitly state that the pre-existing `silk_stream` hunks and `effect_layer_manifest.py` hash were preserved. Do not stage or commit.
