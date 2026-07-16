# Work Order: Canon 67 accepted 385s paper edit compile and picture preview

Date: 2026-07-16
Status: EXECUTED — review preview produced; formal owner revision verdict remains unrecorded
Owner state: `revision_0012.json`
Target stop: `WAITING_INTEGRATOR_CANON67_385S_PICTURE_PREVIEW_REVIEW`

## Goal and fixed decisions

Compile the owner-accepted Stage 5 paper edit into an executable L1 v4 plan
and one real-motion 385-second review preview. This is a picture/subtitle
review artifact, not final finishing or delivery.

The worker does not own story decisions. These values are fixed:

| Segment | Seconds |
|---|---:|
| seg01 | 26.00 |
| seg02 | 24.00 |
| seg03 | 36.00 |
| seg04 | 68.00 |
| seg05 | 85.00 |
| seg06 | 30.00 |
| seg07 | 52.00 |
| seg08 | 39.34 |
| seg09 | 0.00 |
| seg10 | 24.66 |
| **Total** | **385.00** |

Third act is `A_REAL_SUPERVISOR_WITNESS`. Ending copy is exactly:

- `第67期養成班｜結訓`
- `每一次準備，都是穩定的開始。`

## Read first

1. `AGENTS.md`
2. `.tmp/canon67_540s_route_acceptance/accepted_chain/revision_0012.json`
   — SHA-256 `b6c3064846a01ee8c6f64a43df6b16448805c6e2e28a93d5159cb09ec9c46aa9`
3. `.tmp/canon67_540s_route_acceptance/stage5/paper_edit_v1/paper_edit_ab.json`
   — SHA-256 `5a1a9f34187d0e5431b8a52c4b9a6400b845308265d7c2772213e19cf93f47c8`
4. `.tmp/canon67_540s_route_acceptance/stage5/paper_edit_v1/owner_verdict.json`
   — SHA-256 `80505a3c70d1a351316081528b83b8bd17b2782312fe933ca064ed697947749c`
5. `.tmp/editing_loop_39s_integrated_campaign/wave_p/human_transcript_review_decision.json`
   — SHA-256 `5d40c6ed1555fe9e08e51fa398295fef16f28496efa76e671287ff1efc5dc046`
6. `.tmp/editing_loop_39s_integrated_campaign/wave_r/l1/rough_cut_plan.json`
   — SHA-256 `815b85b6d7f4a61068e2a26e951e82b56e8e0f86fd2f43ef410cfc0f946deb66`
7. `.tmp/canon67_540s_route_acceptance/stage5/l1_revision_v4/integrator_input/source_binding_map.json`
   — SHA-256 `41962bfa8ef82166c2c4e828c47141af292c703a6a824699f8f16a8383b86b9d`
8. `.tmp/canon67_540s_route_acceptance/stage5/l1_revision_v4/integrator_input/frame_budget_30fps.json`
   — SHA-256 `8b079aae669e6e4e9a2a683bba3a130cb4154fc04a749beecbc64b9a5a944670`
9. `.tmp/canon67_540s_route_acceptance/stage6/paper_edit_preview_v1/integrator_input/one_frame_review_deviation.json`
   — SHA-256 `9f40a30ab779ba13721e9302fdf746604246369f3739f85cf04272b6eae8c4eb`

The binding map is the integrator-approved bridge between the 39-second pilot
aliases and Material Map canonical asset IDs. It is input truth for this order;
the worker must not rediscover, rewrite, or replace it.

The frame budget resolves the 30fps representation boundary. Semantic/audio
seconds remain the owner-approved decimal values, while picture durations use
the exact integer frame counts in that file. Direct binary-float equality is
forbidden.

## Owner zone

The worker may create or modify only:

- `.tmp/canon67_540s_route_acceptance/stage5/l1_revision_v4/**`
- `.tmp/canon67_540s_route_acceptance/stage5/effects/seg10_memory_ending_v4/**`
- `.tmp/canon67_540s_route_acceptance/stage6/paper_edit_preview_v1/**`

## Frozen / forbidden zone

Read-only:

- `revision_0000.json` through `revision_0012.json`, all accepted deltas and receipts;
- `stage5/paper_edit_v1/**`;
- all source media, Material Map, L1 v1-v3, 39s Wave P/R artifacts;
- production code, tools, tests, Skills, registry, RUNBOOK, HANDOFF and campaign status;
- `stage5/l1_revision_v4/integrator_input/source_binding_map.json` inside the
  owner directory is additionally frozen read-only;
- `stage5/l1_revision_v4/integrator_input/frame_budget_30fps.json` inside the
  owner directory is additionally frozen read-only;
- `stage6/paper_edit_preview_v1/integrator_input/one_frame_review_deviation.json`
  inside the owner directory is additionally frozen read-only;
- git index and history.

Do not create a new renderer, route, helper, private ffmpeg bypass, waiver, or
replacement transcript. Do not run full suite. Do not commit, stage, push,
upload, or claim delivery.

## Ordered pieces

### 0. Freeze and preflight

Record the exact hashes above, current HEAD/status, and source hash from the
approved transcript binding. Validate revision 12 with the existing public
global-editorial-state CLI. Stop on drift.

The prior stopped attempt is accepted as Task 0 evidence. Its repeated
source-binding failure is classified as a specification gap: pilot aliases are
not canonical Material Map IDs. On continuation, validate the frozen binding
map once and resume at Task 1; do not repeat the failed ad-hoc matching method.

The second stopped attempt is also accepted as preflight evidence. Its exact
duration assertion exposed a contract contradiction: 39.34 and 24.66 seconds
are not independently representable as integer frames at 30fps. Validate the
frozen frame budget once, then resume Task 1 without direct float equality.

The third stopped attempt completed Tasks 1 and 2. The integrator independently
confirmed the picture hash and decoded `11549` frames. Preserve that picture;
do not render it again. Exact picture-frame equality remains an objective FAIL,
but the frozen deviation authorizes completion of the internal review artifact
because semantic/audio duration is 385 seconds and the picture differs by one
30fps frame. This exception is not final-delivery evidence or renderer
certification.

### 1. Compile L1 v4

Create a fresh v4 plan from L1 v3 plus the accepted paper-edit delta:

- for the embedded 39-second plan, replace each pilot alias with the exact
  `canonical_asset_id` and `source_sha256` in the frozen binding map; path is the
  identity join key, and pilot alias text is never used as canonical identity;

- exact segment and total durations from the fixed table;
- preserve the table as semantic/audio seconds; allocate picture frames exactly
  as the frozen 30fps frame budget (`11550` total frames = `385.000` seconds);
- use tolerance `<= 0.000001` seconds for semantic sums; seg08 picture is 1180
  frames and seg10 picture is 740 frames, while the approved speech still ends
  sample-accurately at timeline `360.34` seconds;
- no video window over-allocation and no identical repeated source window;
- seg02 photo holds 3–5 seconds rather than 9 seconds each;
- seg03 retains safety-equipment motion anchors and uses formation stills only
  as support/transition;
- seg04 uses only `cable_operation`; remove `technical_height` filler;
- seg05 orders preparation -> ascent -> operation -> wide scale -> completion;
- seg06 uses `placement_preference_selection`, never classroom instruction;
- seg07 uses breadth montage but groups the same event family contiguously;
- seg08 embeds the complete 39.34-second approved speech/picture plan without
  reordering or deleting dialogue time;
- seg09 remains zero and 13/13 deferred;
- seg10 uses only the accepted truthful memory-to-group-photo ending.

Write plan, duration/window report, semantic diff from v3, and a timestamped
review index. No new asset may enter without an existing reviewed Material Map
reference and source hash.

### 2. Build bounded seg10 v4 effect asset

Use the existing MemoryPhotoWall capability and the same five reviewed v3
photos. Do not modify renderer code.

- Render a fresh 40-second effect with the accepted two lines visible only in
  the final 32–40 second hold.
- The 385-second plan consumes only source window `15.34–40.00`, yielding
  exactly 24.66 seconds: full wall -> convergence -> single group photo.
- No per-card machine caption; contain/face-safe treatment; no departure claim.

If the existing public capability cannot express this with configuration,
stop as STRUCTURAL. Do not patch production code in this order.

### 3. Build the 385-second review preview

Use existing public composition surfaces to create one actual-motion review
MP4 at 1280x720, 30 fps:

- no BGM and no final sound design;
- silence outside seg08;
- seg08 preserves the complete original speech at timeline `321.00–360.34`;
- burn or overlay the exact 12 owner-approved cues shifted by +321.00 seconds;
- show the accepted factual segment review caption at each active segment
  start, visually separate from bottom-center speech subtitles;
- use the accepted seg10 copy exactly; no other story copy is authorized.

This preview must remain review-only and may contain an AAC track solely to
carry silence plus the original supervisor speech.

Continuation rule: use the existing picture whose SHA-256 is
`d31e6395a0e81a6141efafe38a4ac1b9dcd84298d5294b83cd8a6ff1d597d582`
and existing 385-second audio whose SHA-256 is
`7d6721a731e4105fefc4116a78b8435663f329111b168dfea29a953cb2df2d73`.
Do not repeat picture rendering. Mux, apply the exact approved subtitles and
review captions, then continue to Task 4.

### 4. Verify and package

Write:

- machine-readable plan/read-back and source-hash report;
- subtitle exact-equality and speech-continuity evidence;
- ffprobe/media-health report;
- per-segment contact sheets plus one owner review index;
- worker report with command ledger, deviations, skips, and final status.

Stop at `WAITING_INTEGRATOR_CANON67_385S_PICTURE_PREVIEW_REVIEW` with
`human_creative_approval=false` and `final_delivery_claimed=false`.

## Acceptance

Expected exit `0`:

```powershell
C:\Users\user\miniconda3\python.exe tools\global_editorial_state.py validate --state .tmp\canon67_540s_route_acceptance\accepted_chain\revision_0012.json --json
C:\Users\user\miniconda3\python.exe -m unittest tests.test_rough_cut_plan_execute tests.test_source_speech_subtitle_qa tests.test_caption_audit tests.test_remotion_worker_bridge -v
git diff --check
```

Read-back must prove:

- semantic plan total within `0.000001` of 385.000 seconds;
- record the exact-picture contract as FAIL: expected `11550`, actual `11549`;
  preserve this finding and verify the final review container/audio duration is
  385.000 seconds without claiming the renderer achieved exact frame parity;
- semantic segment seconds match the fixed table, and rendered segment frames
  match the frozen frame budget; do not require impossible direct equality
  between 39.34/24.66 seconds and their individual 30fps picture durations;
- seg08 source hash, 39.34-second speech window, 12/12 approved text and timing;
- seg09 zero; seg10 24.66; no 540-second padding;
- no BGM; exact ending copy; no source mutation;
- all new artifacts lie inside the owner zone.

## Stop-loss

One LOCAL correction per failure class. Stop at the last green state on:

- frozen hash drift;
- required out-of-zone edit;
- production-code or schema change;
- repeated failure class;
- inability to preserve complete speech or exact approved text;
- duration achieved by duplicated windows, fake holds, or source mutation.

Report PASS / FAIL / UNKNOWN separately. Worker report text is not acceptance;
the Integrator will independently recheck the material evidence.
