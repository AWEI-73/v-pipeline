# Work Order: Canon 67 Stage 3 complete-pool material truth

Date: 2026-07-17
Owner: `main-pipeline` integrator
Worker profile: one long-running high-capability agent
Target state: `WAITING_INTEGRATOR_CANON67_STAGE3_LARGE_POOL_MATERIAL_MAP_REVIEW`

## 0. Outcome

Build the first complete-pool, evidence-carrying Material Map for the Canon 67
editorial reconstruction. The worker must use the repository's registered
material intake, wall, matrix, Material Map, and project-map surfaces plus the
`material-map` and `curator` skills. It may make bounded visual observations,
but it may not select a cut, rewrite the story, render a candidate, or promote
folder names into facts.

This is a Stage 3 truth-building job, not a Stage 5 picture-edit job.

Expected pool accounting:

- 306 total source files;
- 302 media files: 214 images and 88 videos;
- four non-media files;
- 19 reference-only media exclusions;
- 283 candidate media;
- 81 previously reviewed assets eligible for source-hash-bound reuse;
- 202 candidate media requiring new coarse review.

## 1. Read and freeze first

Read completely before acting:

1. `AGENTS.md`
2. `RUNBOOK.md`
3. `HANDOFF_CURRENT.md`
4. this work order
5. `skills/material-map.md`
6. `skills/curator.md`
7. `docs/material-map-lifecycle.md`
8. `docs/decisions/2026-07-17-canon67-complete-pool-course-taxonomy.md`

Freeze these inputs by exact SHA-256:

| Artifact | SHA-256 |
|---|---|
| `.tmp/canon67_editorial_reconstruction_v2/stage2_ambiguity_v2/complete_pool_correction.json` | `66008810a8cf97ce1cdea8af92863b3c724fc0b8d93929591f98fc068a12738b` |
| `.tmp/canon67_editorial_reconstruction_v2/stage2_ambiguity_v2/material_inventory_summary.json` | `b67a0b344bfd8e1ed85835d736a9e1e1004fc1b7620c34947ec7eeff814b58dd` |
| `.tmp/canon67_editorial_reconstruction_v2/stage2_ambiguity_v2/story_decision_packet.json` | `13ba6b15a433dfa99aa5f38f177d77882eadad14ab2680e17cf0c7e1b8ea5875` |
| `.tmp/canon67_editorial_reconstruction_v2/stage2_ambiguity_v2/segment_story_contract.json` | `694dd73736645736c4f2e4cb0b031d60294c312f6de4ed143c48f38e5d171735` |
| `.tmp/canon67_editorial_reconstruction_v2/stage2_ambiguity_v2/evidence_need_map.json` | `f46895f5cf2bdbbb0628f68dea4e751fad8663c0ae3c2a60a43cf376ebc2f6b0` |
| `.tmp/canon67_editorial_reconstruction_v2/stage2_ambiguity_v2/ambiguity_gate_report.json` | `f9263270d792055e90dc583f3708e29c0eed940da450e100b0ed4a55e7df70f9` |
| `.tmp/canon67_540s_route_acceptance/stage3/project_material_map_l0_v1.json` | `9dcb970b7a8c9bbb053567c35ab4ea259630e21514a9309e320d33ee1c10f6b2` |

The source root is the `source_dir` recorded in the frozen inventory. Do not
hard-code another source root and do not mutate source files.

Write the frozen-hash read-back, source-root existence check, pre-work HEAD,
branch, and exact `git status --short` to:

`.tmp/canon67_editorial_reconstruction_v2/stage3_large_pool_v2/preflight/frozen_input_audit.json`

Stop on any frozen-input drift or missing source root.

## 2. Authority, ownership, and forbidden zones

### Worker-owned output zone

The worker may create or replace only:

`.tmp/canon67_editorial_reconstruction_v2/stage3_large_pool_v2/**`

### Frozen and forbidden

Do not modify:

- source media;
- either Stage 2 ambiguity package;
- `.tmp/canon67_540s_route_acceptance/**`;
- `.tmp/canon67_editorial_reconstruction_v2/accepted/**`;
- existing candidates, timelines, captions, audio, or renders;
- production code, `tools/**`, `video_pipeline_core/**`, tests, skills,
  registries, specs, `RUNBOOK.md`, `HANDOFF_CURRENT.md`, or campaign state;
- git index/history, remote state, or worktree layout.

Do not use Canon 66 or the final Canon 67 reference film as candidate media.
They may remain named in the exclusion ledger only.

Do not create run-local Python/PowerShell helper scripts to bypass a missing
public surface. A missing surface is a factory gap, not permission to improvise
a second pipeline.

## 3. Fixed truth and display policy

The accepted Stage 2 policy is:

1. act/chapter cards may express the approved story structure;
2. formal course/activity labels require visual evidence;
3. plain-language explanations are review captions, not factual title cards;
4. folder names are retrieval priors, not ground truth;
5. an empty folder is not evidence that the course occurred;
6. provisional labels cannot satisfy an evidence need, emit a formal course
   label, or enter a canonical picture plan;
7. the 81-asset map is a reviewed subset, not the complete pool.

`keep` in the coarse Material Wall verdict means "keep in the candidate
material pool for mapping". It does not mean final picture selection.

## 4. Ordered tasks

### Task 0 — Preflight and public-surface discovery

1. Complete Section 1 read/freeze.
2. Read `--help` for every public command before first use.
3. Record the exact command argv, start/end time, exit code, and output paths in
   `final/command_log.json`.
4. Create `run_metadata.json` with task identity, actor identifier if the
   harness exposes one, wall-clock start, and both approval flags false. Never
   invent model identity or token counts.

PASS evidence: frozen audit and clean owner-zone initialization.
FAIL: any frozen drift, missing source root, or attempted write outside the
owner zone.

### Task 1 — Rebuild complete intake and policy accounting

Use the registered surfaces, beginning with:

```powershell
python video_tools.py ingest-meta "<frozen source_dir>" `
  --out .tmp/canon67_editorial_reconstruction_v2/stage3_large_pool_v2/intake/materials_db.source.json `
  --work-dir .tmp/canon67_editorial_reconstruction_v2/stage3_large_pool_v2/intake/derived
```

Also run `tools/material_quick_inventory.py` into the owner zone and compare it
with the frozen Stage 2 inventory.

Produce:

- `intake/source_identity_manifest.json`;
- `intake/reference_only_exclusions.json`;
- `intake/material_pool_accounting.json`.

The accounting must bind each candidate to a stable asset id, source path,
media type, byte size, and SHA-256. The 19 reference-only media and four
non-media files remain explicit exclusions. No source item may disappear.

PASS: exact 306/302/214/88/4/19/283 read-back and 283 unique candidate source
hash bindings.
UNKNOWN is not allowed for inventory counts. Stop on count drift.

### Task 2 — Hash-bound reuse and bounded batch plan

Match the 283 candidates against the prior 81-asset map by source SHA-256, not
by asset id, basename, path, or folder name alone.

Produce:

- `review/reuse_ledger.json` with `reused`, `changed`, and `not_previously_seen`;
- `review/review_batch_plan.json`;
- `review/duplicate_cluster_candidates.json`.

Requirements:

- exactly 81 assets may be reused only if all source hashes match;
- all other candidate assets enter review batches of at most 24;
- group batches by top-level folder/media type and then apparent activity
  family where possible;
- every one of the 283 candidates must have exactly one accounting state;
- duplicate candidates remain visible until evidence confirms the duplicate;
- reuse prior semantic labels only as source-hash-bound evidence, never as a
  reason to skip the current source-accounting check.

If the exact prior reviewed count differs from 81, stop and report the mismatch
instead of changing the target.

### Task 3 — Complete-pool coarse visual immersion

Use `video_tools.py material-wall-build` with bounded wall sizes. No wall may
contain more than 24 photos; use a smaller bounded video-strip batch when needed
for readability. Inspect every generated wall with an actual image-viewing
surface and record every opened wall id in `review/wall_access_log.json`.

For each visual asset, record only controlled fields:

- `asset_id` and source hash;
- folder prior;
- observed content tags;
- apparent activity family;
- shot scale/composition;
- people/action/result/transition roles;
- coarse quality and duplicate candidate;
- evidence reference (`wall_id`, cell, and sampled times for video);
- confidence;
- `review_status`: `reviewed`, `provisional`, `deferred`, `excluded`, or
  `duplicate`.

Use at least three spread time samples for each video unless duration or decode
failure makes that impossible. Record the exact reason in the exception queue.
HEIC/HEIF must use the registered `heic_review_jpeg` proxy while preserving
`source_photo`. A missing proxy becomes `photo_proxy_failed`; it is never a
silent skip.

Write:

- `review/material_wall_review_verdict.json`;
- `review/materials_db.wall_reviewed.json` by invoking the public
  `material-wall-review-apply` surface;
- `review/coarse_observation_ledger.json`;
- `review/exception_queue.json`.

Short controlled labels are required; per-asset essays are forbidden.

### Task 4 — Coarse maps, selective deep review, and evidence edges

Build deterministic per-asset maps for all 283 candidate media with the public
`material-map --selected-only` surface. Use fast mode for the first complete
pass. Deep-review only:

- exception-queue items;
- likely story anchors for the 47 Stage 2 evidence needs;
- assets whose provisional family could change a formal course label;
- likely speech-bearing assets;
- duplicate disputes.

Use `material_understanding_matrix.py` in batches of at most 24 for deep visual
review. ASR is allowed only for likely speech candidates and must not be run
over the full pool.

Produce:

- `maps/**.map.json` for all mapped candidates;
- `maps/materials_db.mapped.json`;
- `review/deep_review_ledger.json`;
- `review/material_map_review_verdict.json` containing only visually supported
  scene/evidence decisions.

Apply the verdict with the registered `material-map-review-apply` surface.
Provisional records may carry retrieval hints, but they must have no
`satisfies` edge.

### Task 5 — Aggregate project truth and course coverage

Build the aggregate map with the registered `project-material-map` surface.

Required artifacts:

- `project_material_map_v2.json`;
- `material_pool_accounting.final.json`;
- `course_activity_family_catalog.json`;
- `formal_course_evidence_coverage.json`;
- `story_evidence_need_coverage.json`;
- `establish_action_result_coverage.json`;
- `deferred_due_to_material.json`.

Each formal course/activity label must be one of:

- `confirmed_visual_evidence`;
- `provisional_visual_hypothesis`;
- `unsupported_by_current_pool`;
- `owner_fact_required`.

Only the first status can authorize a future formal course title card. A
provisional label may assist retrieval but may not satisfy a Stage 2 need.

The 47 evidence needs must each report `covered`, `weak`, `missing`, or
`blocked`, with asset/scene evidence refs for covered/weak results. This is
coverage evidence, not picture selection.

### Task 6 — Human-scale owner review packet

Create `owner_review/owner_review_index.md` and
`owner_review/owner_verdict_template.json`.

The index must begin with:

1. exact pool accounting;
2. confirmed course/activity families and their visual examples;
3. provisional or conflicting classifications;
4. evidence-needs coverage summary;
5. duplicate/exclusion/exception queue;
6. the 81 reused versus 202 newly reviewed distinction;
7. links to all walls and ledgers.

Show representative evidence rather than forcing the owner to inspect all 283
items. Keep the complete evidence reachable for integrator audit.

The owner template asks only for factual/taxonomy disputes and whether Stage 4
paper-edit work may begin. It must not ask for final creative approval or
delivery approval.

### Task 7 — Validation and worker report

Run focused validation only:

```powershell
python -m unittest `
  tests.test_material_inventory_summary `
  tests.test_material_understanding_matrix `
  tests.test_material_wall `
  tests.test_material_map `
  tests.test_material_map_review_apply `
  tests.test_project_material_map `
  tests.test_material_map_relation_docs -v
python tools/skill_tool_contract_audit.py --json
git diff --check
```

Do not run the full suite: this work order forbids production/test changes and
therefore does not earn a full-suite run.

Create `final/worker_report.md` containing:

- PASS/FAIL/UNKNOWN table for every task;
- pre/post HEAD and exact git status;
- every command and exit code, or a link to `command_log.json`;
- output path and SHA-256 for every required artifact;
- exact pool/batch/reuse/review/defer/duplicate counts;
- wall ids actually opened by the agent;
- deviations, one-retry events, skips, and blind spots;
- wall-clock, render count (`0`), tool-call count if available, agent turns if
  available, Human review minutes (`UNKNOWN`), and blast radius;
- `human_creative_approval=false`;
- `final_delivery_claimed=false`.

## 5. Delegated judgment

The worker may DECIDE:

- controlled observed-content tags;
- apparent activity-family hypotheses;
- representative samples and deep-review priority;
- confidence, duplicate candidates, and exception routing;
- whether a candidate appears capable of establish/action/result/transition
  use.

The worker must leave UNKNOWN or request owner review for:

- exact formal course names not visually established;
- people identity, roster truth, or institutional facts;
- whether two visually similar activities are officially different courses;
- emotional quality or final story value;
- any decision that would alter the Stage 2 story or segment contract.

## 6. Acceptance matrix

| Item | PASS condition |
|---|---|
| Frozen inputs | all seven hashes match |
| Complete pool | 306 total, 302 media, 283 candidates, 19 reference exclusions, four non-media |
| Accounting | every candidate appears exactly once; no unexplained asset |
| Reuse | 81 source-hash matches; 202 newly reviewed candidates |
| Walls | every generated wall opened; bounded sizes; access log complete |
| Photos | HEIC/HEIF proxy or explicit exception; no silent skip |
| Videos | three spread samples or explicit bounded failure reason |
| Maps | 283 candidate maps or explicit mapped/skipped accounting whose totals equal 283 |
| Evidence | provisional assets have no satisfies edges |
| Course labels | only visually confirmed labels are title-card eligible |
| Story needs | all 47 needs classified with evidence refs for covered/weak |
| Owner packet | concise summary plus reachable complete evidence |
| Scope | no picture plan, render, audio, subtitle, effect, upload, or delivery artifact |
| Validation | focused tests/audit/diff-check exit 0; full suite not run |

## 7. Stop-loss

- One LOCAL correction is allowed per failure class. If the same class recurs,
  classify it STRUCTURAL and stop at the last green state.
- Stop immediately on frozen hash/count drift, source mutation, or reference
  media entering the candidate pool.
- If a registered public tool cannot express the required bounded operation,
  write `final/factory_gap.json`, stop the affected task, and do not create a
  private helper or modify production code.
- A factual ambiguity is not a structural failure: mark it provisional or
  UNKNOWN, add it to the owner packet, and continue other independent batches.
- A single unreadable asset does not erase the pool: record the exception and
  preserve exact accounting.
- Do not retry expensive whole-pool work merely to fix a report-path or display
  issue; preserve evidence and correct the local artifact once.

## 8. Legal completion state

Legal success requires all objective acceptance rows to pass and the run to
stop at:

`WAITING_INTEGRATOR_CANON67_STAGE3_LARGE_POOL_MATERIAL_MAP_REVIEW`

This state means the integrator may audit the complete-pool Material Map and
prepare an owner taxonomy/coverage review. It does not authorize Stage 4 paper
edit, picture lock, rendering, creative approval, or delivery.

Always preserve:

```text
human_creative_approval=false
final_delivery_claimed=false
```
