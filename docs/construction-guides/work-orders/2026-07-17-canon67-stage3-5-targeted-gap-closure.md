# Work Order: Canon 67 Stage 3.5 targeted story-evidence gap closure

Date: 2026-07-17
Owner: `main-pipeline` integrator
Worker profile: one high-capability bounded review worker
Target state: `WAITING_INTEGRATOR_CANON67_STAGE3_5_TARGETED_CLOSURE_REVIEW`

## 0. Goal and stop-loss decision

Close or truthfully defer the five story-evidence gaps left after the accepted
complete-pool Material Map. This is the last engineering/review pass before the
owner reorganizes or replaces the source pool. It must prove the incremental
Material Map loop on a real case; it must not deepen the whole repository or
force the current material to support a story it cannot carry.

The five gaps are:

- `A02_collective_identity`;
- `A07_technical_detail`;
- `A09_supervisor_witness`;
- `A10_placement_preference`;
- `A11_collective_landing`.

This work order is agentic evidence review plus canonical artifact application.
It is not an automated capability-execution campaign, so do not invent an
execution companion or invoke the strict capability receipt engine. Record an
agent attestation, complete command log, immutable input hashes, and public-tool
outputs instead.

## 1. Read and freeze first

Read completely:

1. `AGENTS.md`
2. `RUNBOOK.md`
3. `HANDOFF_CURRENT.md`
4. this work order
5. `skills/material-map.md`
6. `skills/curator.md`
7. `.tmp/canon67_editorial_reconstruction_v2/stage3_canonical_persistence_repair_v1/final/integrator_acceptance_v1.md`
8. the five segment records and their needs in the frozen Stage 2 artifacts

Freeze these exact inputs:

| Artifact | SHA-256 |
|---|---|
| accepted editorial state v2 | `2041e6b9c879aa7737defa0f3d86198836822860a2345b16d2742bf219af25e7` |
| Stage 2 segment story contract | `694dd73736645736c4f2e4cb0b031d60294c312f6de4ed143c48f38e5d171735` |
| Stage 2 evidence need map | `f46895f5cf2bdbbb0628f68dea4e751fad8663c0ae3c2a60a43cf376ebc2f6b0` |
| accepted Stage 3 project map v2 | `daaa35b18b6b315263a44f87a5f746179c13ed8b4aa575e845f2c486f815dad4` |
| Stage 3 retrieval replay summary | `9ee8cfcebcbb376f3728d01fe87d940d3022fa99873ce307b95a89e72e6189f7` |
| Stage 3 integrator acceptance | `6267f8f461b05e8d84637c32160624d1dadd1e5d3ac2f39c150c7ac7f6a5c87e` |
| approved 39.34s transcript decision | `5d40c6ed1555fe9e08e51fa398295fef16f28496efa76e671287ff1efc5dc046` |
| approved 39.34s speech/subtitle evidence | `58227e7482d639dd6be1e760a64793946e206fd2fcb9d358012e4600fee131ba` |

Write `preflight/frozen_input_audit.json`. Stop on any mismatch.

## 2. Owner and forbidden zones

Owner zone:

`.tmp/canon67_editorial_reconstruction_v2/stage3_5_targeted_gap_closure_v1/**`

Everything outside that root is read-only, including source media, Stage 2,
accepted state, Stage 3 v2, the approved transcript, production code, tests,
skills, registry, docs, `HANDOFF_CURRENT.md`, and git history/index.

Do not:

- re-review or re-hash the complete 283-asset pool;
- run full-pool ASR, music analysis, or a full render;
- use the reference film, Canon 66 material, or old 385-second clip order;
- convert filename/folder prior into accepted truth;
- change the 12 approved cues, 39.34-second source speech, or source hash;
- invent a complete teacher roster, speaker identity, placement outcome, or
  literal departure;
- modify Stage 2 story contracts or accepted editorial state;
- create a private Material Map/ranker/ASR implementation.

## 3. Build one bounded gap inventory

Use the accepted v2 map and public ranker to create:

- `gap_inventory.json`;
- `targeted_candidate_manifest.json`;
- one concise evidence packet per gap.

Start from current ranker candidates, accepted map evidence, and visually
related siblings. At most 48 unique source assets may enter targeted deep
review. Folder/name text may locate candidates but cannot accept them.

For each selected video, inspect enough temporal evidence to determine the
requested action/result, not merely one thumbnail. For each selected photo,
inspect real pixels or an existing hash-bound proxy. Every observation must
bind asset id, source hash, source window or image ref, and evidence artifact.

Do not pause for owner input mid-run. Unresolved facts go to the final owner
packet.

## 4. Segment-specific evidence rules

### A02 — collective identity

Try to prove the four roles `portrait_roll`, `shared_action`,
`formation_change`, and `collective_result` with at least eight unique windows
whose location, people scale, action, or composition materially differs.

Reject adjacent and non-adjacent semantic repetition. If the current pool
cannot provide eight meaningful windows, propose a shorter duration and list
the missing role; do not repeat near-identical group photos.

### A07 — technical detail

Deep-review only targeted candidates for `detail_establish`,
`hand_tool_action`, `component_change`, and `inspection_result`. Motion claims
require temporal strips or equivalent time evidence.

If all four roles cannot be supported with new information not already assigned
to A04/A05, set the proposal to `duration_sec=0` and
`merge_into=A04_or_A05`. This is a proposed story-contract revision, not an
automatic mutation.

### A09 — supervisor witness

Reuse the existing owner-approved transcript and source binding. Do not run new
full-pool ASR. Confirm the speaker source against the approved 39.34-second
evidence and preserve speaker open/return/close.

Create `a09_cue_cutaway_map.json` that groups the 12 approved cues into bounded
meaning windows and proposes two visually distinct cutaway families. Every
cutaway must answer the covered cue text and use a new or explicitly justified
callback window. When no relevant cutaway exists, retain the speaker anchor.

### A10 — placement preference

Use the owner-established event truth but prove the visible roles
`process_context`, `form_writing_action`, `ranking_or_choice_reference`, and
`choice_completion`. Do not name the supervisor or claim a final placement
result. General classroom footage is not enough.

### A11 — collective landing

Prove `memory_entry`, `technical_callback`, `life_callback`,
`final_group_photo`, and `ending_hold`. Reuse the already accepted
MemoryPhotoWall phase logic only as a design constraint; this work order does
not render it. Callbacks must be short, intentional, and distinct from a replay
of the earlier event.

## 5. Apply evidence through the public Material Map path

Create proposed review decisions only from visually or speech-bound evidence.
Copy the accepted v2 per-asset maps into the new immutable run root, then use
the registered `material-map-review-apply` and `project-material-map` surfaces
to produce:

- `review/material_map_review_verdict.targeted.json`;
- `project_material_map_v3.proposed.json`;
- `material_map_delta_v2_to_v3.json`;
- `deferred_due_to_material.targeted.json`.

Preserve all prior accepted edges. New accepted edges require evidence refs;
candidate-only results remain candidate. Never create an edge merely to make a
segment pass.

## 6. Replay and owner packet

Replay all eleven Stage 2 segments with the public rough-cut/ranking surfaces.
Produce:

- `retrieval_replay_v2/retrieval_replay_summary.json`;
- `retrieval_replay_v2/rough_cut_plan.proposed.json`;
- `retrieval_replay_v2/picture_plan_retrieval_report.json`;
- `owner_review/owner_review_index.md`;
- `owner_review/owner_verdict_template.json`.

Report both:

- union of public-ranker assets across all eleven segments;
- union for accepted/supported segments only.

Do not call candidate-only ranking "supported". Each gap must end as exactly
one of:

- `evidence_supported`;
- `owner_defer_recommended`;
- `material_gap_confirmed`;
- `story_revision_proposed`.

The owner index must be human-scale and show the evidence needed to decide each
gap without opening the full 283-asset pool.

## 7. Validation

Run the focused no-render suite:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest `
  tests.test_material_understanding_matrix `
  tests.test_material_map `
  tests.test_material_map_review_apply `
  tests.test_project_material_map `
  tests.test_material_retrieval `
  tests.test_material_rough_cut `
  tests.test_picture_plan_retrieval_gate -v
C:\Users\user\miniconda3\python.exe tools\skill_tool_contract_audit.py --json
git diff --check
```

Do not run the full suite unless production code or tests changed; they are
forbidden here.

Verify UTF-8/JSON, all evidence paths, output hashes, 283 map identities, prior
accepted-edge preservation, provisional-edge prohibition, and frozen input
immutability.

Write:

- `accountability/attestations/stage3_5_targeted_review.json` with the exact
  assets/evidence actually inspected by the agent;
- `final/command_log.json` with exact argv and exit code, not prose aliases;
- `final/artifact_sha256.json`;
- `final/worker_report.md` with PASS/FAIL/UNKNOWN, deviations and blind spots.

## 8. Stop-loss and legal state

- One LOCAL correction is allowed per failure class. A repeated class is
  STRUCTURAL; stop at the last green state.
- If a public tool cannot express the canonical apply/replay, write
  `final/factory_gap.json`; do not modify production code.
- Insufficient material is a valid outcome. Record it instead of retrying the
  whole pool or widening the story claim.
- No intermediate Human gate is required; complete the bounded packet and stop.
- `human_creative_approval=false` and `final_delivery_claimed=false` always.

Legal success state:

`WAITING_INTEGRATOR_CANON67_STAGE3_5_TARGETED_CLOSURE_REVIEW`

After integrator acceptance, the owner decides any remaining defer/story
revision. Only then may Stage 4 paper-edit construction begin.
