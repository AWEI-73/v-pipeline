# Work Order: Canon 67 150-Second L1 Picture Composition

Date: 2026-07-13
Owner: integrator / main-pipeline
Worker: one fresh Luna session, single writer
Target state: `WAITING_OWNER_150S_FINAL_PICTURE_VERDICT`

## Goal And Context

Turn the integrator-approved L0 v2 packet into one silent, reviewable
150-second L1 picture candidate. Use the registered Material Map rough-cut
executor and reuse the already tuned smooth photo-motion logic from `mv_cut`
through one shared core helper. Do not build another renderer. Then prove the
full path with accountable render/verify receipts and an L5 owner review packet.

Read in order:

1. `AGENTS.md`
2. `RUNBOOK.md`
3. `HANDOFF_CURRENT.md`
4. `docs/superpowers/specs/2026-07-13-canon67-150s-picture-first-longform-design.md`
5. `docs/superpowers/plans/2026-07-13-canon67-150s-l1-picture-composition-plan.md`
6. `.tmp/canon67_150s_picture_first_longform/l0_revision_v2/review/integrator_verdict_v2.json`
7. this work order and its execution companion
8. the L0/L1/L5 portions of `skills/editing-loop-director.md` and the
   capability/SOP portions of `skills/material-map.md` and `skills/verify.md`

The accepted proposal has SHA-256
`87686deb7139e26b6246b9d32b4ce46d0c85834963d97899126fe39f90845309`:
42 distinct clip IDs, 26 videos, 16 stills, three 50-second sections. The
integrator verdict adds one non-blocking correction: asset
`asset-e10caebd47184496` shows seven people, not six. Do not mutate the sealed
L0 packet; carry the correction forward in L1 metadata.

## Owner And Forbidden Zones

The worker may modify or create only:

- `video_pipeline_core/still_motion.py`;
- `video_pipeline_core/mv_cut.py`;
- `video_pipeline_core/edit_artifacts.py`;
- `tools/rough_cut_plan_execute.py`;
- `tests/test_still_motion.py`;
- `tests/test_rough_cut_plan_execute.py`;
- `.tmp/canon67_150s_picture_first_longform/l1_picture_candidate/**`;
- `.tmp/canon67_150s_picture_first_longform/campaign_status.json`;
- `HANDOFF_CURRENT.md` only for the final cursor/state block.

Everything else is read-only. In particular, do not modify the L0/L0R runs,
the accepted proposal/verdict, Product Spec, Skills, registry/capability cards,
other tools/tests, source media, Workbench, route runners, or artifact
dictionaries. Do not stage existing dirty files, reset, stash, rebase, amend,
push, upload, clean, or create a worktree. One writer; no subagents.

## Ordered Outcomes

### 1. Bounded existing-tool connection

Capture red-first evidence, then make `cap.material-map.rough-cut-plan-execute.v1`
correctly render recognized still images for their requested duration using the
existing smooth `slow_push`, `pan_right`, `detail_push`, and `pan_left`
treatments while preserving video seek/trim behavior. Extract the pure filter
policy from `mv_cut` into `video_pipeline_core/still_motion.py`; keep MV
compatibility wrappers and make `edit_artifacts` consume the shared mode tuple.
Preserve `clip_id`, `asset_id`, `source_type`, source hash, and treatment in the
report. Do not use the older `vt_effects` zoompan path. Add no new CLI,
Capability, renderer, dependency, route, private ffmpeg script, or fallback.

Run and require exit `0`:

```powershell
C:/Users/user/miniconda3/python.exe -m unittest tests.test_still_motion tests.test_rough_cut_plan_execute tests.test_kenburns_smoothness tests.test_mv_cut tests.test_edit_artifacts tests.test_material_rough_cut -v
C:/Users/user/miniconda3/python.exe video_tools.py registry-audit --json
C:/Users/user/miniconda3/python.exe video_tools.py dispatch-capabilities --id cap.material-map.rough-cut-plan-execute.v1 --json
```

Commit only the two authorized code/test files before initializing the run.

### 2. Input freeze and accountability initialization

Read back these frozen inputs before initialization:

- `inputs/mixed_media_probe_rough_cut_plan.json` SHA-256
  `2f99f8d3e615fd9d99d558b7ea4b7e66a6c1286d3d114ce92f3bc4427282502f`;
- `inputs/combined_rough_cut_plan.json` SHA-256
  `8a4dadf40dd13b74ea0f39724e61fd15eb2e7fbe304aa94467177ae839dc2c0d`;
- `inputs/source_hash_manifest.json` SHA-256
  `7c5f48219990121cf6d22848914e5c667df701c27737f55f834b0bc976235ac1`.

Verify `42/42` source paths and hashes. Initialize exactly once:

```powershell
C:/Users/user/miniconda3/python.exe video_tools.py capability-run --initialize --contract docs/construction-guides/work-orders/2026-07-13-canon67-150s-l1-picture-composition.execution.json --json
```

### 3. Mixed-media proof before long render

Execute exactly once:

```powershell
C:/Users/user/miniconda3/python.exe video_tools.py capability-run --contract docs/construction-guides/work-orders/2026-07-13-canon67-150s-l1-picture-composition.execution.json --step-id L1.mixed-media-render-probe --json
```

Require a PASS receipt plus: duration `4.0 +/- 0.1` seconds, 120 frames at
30 fps, two traceable clips, a full two-second photo-motion window, different
early/late photo-frame hashes, frozen treatment read-back, and no audio stream.
If this objective proof fails, stop before the 150-second render as
`STRUCTURAL_MIXED_MEDIA_L1_RENDER_CAPABILITY_GAP`.

### 4. Full L1 render and registered L5 verify

After the probe passes, execute each step exactly once and in order:

```powershell
C:/Users/user/miniconda3/python.exe video_tools.py capability-run --contract docs/construction-guides/work-orders/2026-07-13-canon67-150s-l1-picture-composition.execution.json --step-id L1.render-150s-picture-candidate --json
C:/Users/user/miniconda3/python.exe video_tools.py capability-run --contract docs/construction-guides/work-orders/2026-07-13-canon67-150s-l1-picture-composition.execution.json --step-id L5.verify-150s-picture-candidate --json
```

Require 1280x720 H.264 at 30 fps, `150.0 +/- 0.5` seconds, 42 traceable
clips in accepted order, three 50-second sections, no audio stream, all 16
frozen photo treatments, no still duration adjustment, render report `ok=true`,
and final verify `pass=true`.
This is a review candidate, not delivery.

Then run bounded evidence tools:

```powershell
C:/Users/user/miniconda3/python.exe tools/rendered_product_qa.py --run .tmp/canon67_150s_picture_first_longform/l1_picture_candidate --out-dir .tmp/canon67_150s_picture_first_longform/l1_picture_candidate/l5/rendered_product_qa --json
C:/Users/user/miniconda3/python.exe video_tools.py perception-field-check .tmp/canon67_150s_picture_first_longform/l1_picture_candidate/final.mp4 --out .tmp/canon67_150s_picture_first_longform/l1_picture_candidate/l5/perception
```

### 5. Evidence-carrying review packet

Write the exact artifacts listed in the implementation plan. The packet must
include the accepted L0 verdict verbatim, semantic trace, render/video hashes,
duration/stream/decode/black evidence, no-audio policy, min/median/max shot
duration, repetition/category/family/fatigue reports, full-film perception
wall, objective-versus-taste findings, six-field carry-forward records, an
unset owner verdict template, and a run-bound agent attestation.

The agent must actually inspect the rendered wall/candidate. QA proves media
health, not story taste. Creative quality remains `UNKNOWN` until owner review.

### 6. Strict closure and final validation

Strict closure writes to the contract `accountability_root`, not to
`final/strict_closure`:

```powershell
C:/Users/user/miniconda3/python.exe tools/no_skip_execution_trace.py --run .tmp/canon67_150s_picture_first_longform/l1_picture_candidate --contract docs/construction-guides/work-orders/2026-07-13-canon67-150s-l1-picture-composition.execution.json --out-dir .tmp/canon67_150s_picture_first_longform/l1_picture_candidate/accountability --json
```

Require exit `0`. Then run:

```powershell
C:/Users/user/miniconda3/python.exe -m unittest tests.test_still_motion tests.test_rough_cut_plan_execute tests.test_kenburns_smoothness tests.test_mv_cut tests.test_edit_artifacts tests.test_material_rough_cut tests.test_capability_execution_contract tests.test_final_product_verify tests.test_rendered_product_qa -v
C:/Users/user/miniconda3/python.exe -m unittest discover -s tests
git diff --check
```

All must exit `0`. Run the full suite only once, at the end, with a 1,200,000
ms outer timeout.

## Stop-Loss

Stop at the last green state if a sealed/protected/source hash drifts; the red
test does not describe the observed still defect; the mixed probe fails; an
accountability command is nonzero; a required edit falls outside the owner
zone; a second renderer/route would be required; the same failure class recurs
after one LOCAL correction; or focused/full/strict validation stays nonzero.
Do not delete accountability state, fabricate receipts, loosen acceptance,
retry long render, or hide a picture defect with text/audio/effects.

## Worker Report And Final State

Report commits, exact commands/exit codes, red/green evidence, receipts,
candidate and packet hashes, source/hash read-back, objective/taste findings,
deviations, skipped items, blind spots, pre/post git status, and the exact full
suite result. On success set the cursor to
`WAITING_OWNER_150S_FINAL_PICTURE_VERDICT`; keep
`human_creative_approval=false` and `final_delivery_claimed=false`. Do not
upload or claim delivery.
