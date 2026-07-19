# Work Order: V Pipeline Editorial Reviewer convergence

Date: 2026-07-19
Owner branch: `verify-delivery`
Worker profile: LUNA high/xhigh or equivalent bounded implementation worker
Starting HEAD: `a2c0f9f553aa5b429df94eab02f610920b8b39cb`
Target state: `WAITING_INTEGRATOR_EDITORIAL_REVIEWER_CONVERGENCE_REVIEW`

## 0. Outcome

Converge the repository's existing reviewer registry, timeline-review packet,
Verify tools, and review policy into one discoverable **V Pipeline Editorial
Reviewer** operating surface.

This is not a new Stage, orchestrator, renderer, or automatic LLM runtime.
The runtime reviewer is one agent with multiple rubric lenses. Existing role
names remain valid artifact vocabulary for backward compatibility; they do not
mean multiple reviewer agents must be dispatched.

The reviewer must:

1. inspect persisted eye/ear/heart evidence before requesting new evidence;
2. identify strengths, evidence gaps, and material findings;
3. bind every material finding to reproducible evidence;
4. recommend one primary existing route/capability and at most one fallback;
5. write review artifacts only;
6. never repair, mutate canonical state, approve creative quality, or claim
   delivery.

The implementation is complete only when a fresh reviewer can use one skill
entry, reuse an existing timeline packet, validate a structured review, and
route a finding without inventing a new tool or Stage.

## 1. Architectural map

Current -> desired:

- reviewer roles + role runner + aggregation + timeline walls + Verify tools
  -> one reviewer identity using those roles as rubric lenses;
- repeated whole-film inspection -> hash-bound evidence reuse and delta scope;
- free-form critique -> evidence-bound finding plus bounded proposal;
- reviewer output that can be interpreted as a gate -> findings/advice only,
  with deterministic gates and Human/Orchestrator retaining authority.

Non-goals:

- no second pipeline;
- no `contract-run` LLM auto invocation;
- no multi-reviewer consensus engine;
- no automatic repair;
- no mass rename of historical Hermes artifacts;
- no receipt-as-tool-side-effect rollout in this work order;
- no Canon 67 delivery closure or S9 audio repair;
- no Code Review Graph dependency, MCP registration, hook, or repo config.

## 2. Read first

Read completely, using explicit UTF-8:

1. `AGENTS.md`
2. `RUNBOOK.md`
3. `HANDOFF_CURRENT.md`
4. this work order
5. `docs/artifact-reviewer-map.md`
6. `docs/video-pipeline-operating-map.md`
7. `docs/branch-contract-registry.json` entry `verify-delivery`
8. `docs/interface-contracts/pipeline-product-artifact-dictionary.json`
9. `skills/INDEX.md`
10. `skills/verify.md`
11. `skills/pipeline-boundary.md`
12. `skills/editing-loop-director.md` read-only
13. `video_pipeline_core/reviewer_registry.py`
14. `video_pipeline_core/reviewer_role_runner.py`
15. `video_pipeline_core/reviewer_aggregation.py`
16. `video_pipeline_core/timeline_review_packet.py`
17. `tools/reviewer_flow_acceptance.py`
18. `tools/timeline_review_packet.py`
19. the focused tests named below

Use codebase-memory-mcp first for code discovery and impact analysis. Keep it
enabled and primary. Do not add Code Review Graph to the repository or Codex
configuration; its external CLI evaluation is integrator-owned.

## 3. Baseline and preservation

Record pre-work branch, HEAD, `git status --short`, and hashes of all files in
the owner zone. The starting worktree contains an unrelated S9 audio patch.
Preserve it byte-for-byte and do not stage it.

Known dirty files, all forbidden in this work order:

- `skills/brownfield-edit.md`
- `skills/capcut-assisted-finishing.md`
- `skills/editing-loop-director.md`
- `tests/test_audio_handoff_acceptance.py`
- `tests/test_audio_mix_plan_executor.py`
- `tests/test_soundtrack_arranger.py`
- `video_pipeline_core/audio_handoff_acceptance.py`
- `video_pipeline_core/audio_mix_plan_executor.py`
- `video_pipeline_core/soundtrack_arranger.py`

Frozen baseline hashes:

- `docs/artifact-reviewer-map.md`:
  `015cb77aa81ff9367b12c401b48ae13f61bc916c2b4280ec9faf0ad8e8d1885b`
- `skills/verify.md`:
  `9a4e060c95a64c291982845da5c5750b4045d8288a046233d06ea9850bcb02de`
- `video_pipeline_core/reviewer_registry.py`:
  `903de48672fc51aa903d84a49dd5f441ddf763e24e80b018f9b8625f75996fd9`
- `video_pipeline_core/timeline_review_packet.py`:
  `d2fbb9e5966af331d56355741e326cfe3e8ff22a5448875f05320a4171fd6703`

These hashes are pre-work evidence, not a prohibition on authorized edits.

## 4. Owner zone

The worker may edit only:

- `docs/artifact-reviewer-map.md`
- `docs/video-pipeline-operating-map.md`
- `docs/branch-contract-registry.json`
- `docs/interface-contracts/pipeline-product-artifact-dictionary.json`
- `skills/INDEX.md`
- `skills/verify.md`
- `skills/editorial-reviewer.md` (new)
- `video_pipeline_core/reviewer_registry.py`
- `video_pipeline_core/timeline_review_packet.py`
- `video_pipeline_core/editorial_reviewer.py` (new only if the reuse audit
  proves the two existing modules cannot own the missing validator cleanly)
- `tools/editorial_reviewer.py` (same condition as above)
- `tests/test_reviewer_registry.py`
- `tests/test_timeline_review_packet.py`
- `tests/test_editorial_reviewer.py` (new only when a new module is justified)
- `tests/test_reviewer_flow_acceptance.py`
- `.tmp/editorial_reviewer_convergence/**`
- this work order append-only for the final worker stop report

All other paths are forbidden. In particular, do not edit `RUNBOOK.md`,
`HANDOFF_CURRENT.md`, `video_tools.py`, production render/audio/subtitle/effect
code, source media, Canon 67 accepted artifacts, git history, or the dirty S9
files above.

Do not create an execution companion for this coding task. It does not execute
a production capability DAG. The worker report, tests, registry audits, and
the immutable acceptance packet are the evidence surface.

## 5. Task A — Reuse audit before code

Create:

`.tmp/editorial_reviewer_convergence/reuse_audit.json`

It must map each required behavior to an existing owner or a proven gap:

- reviewer identity and rubric vocabulary;
- artifact review validation;
- timeline wall generation;
- audio/subtitle binding;
- artifact hash binding;
- evidence reuse/delta scope;
- finding validation;
- proposal route/capability validation;
- Stage placement;
- tool/skill discovery.

For every row record `reuse`, `extend`, or `new_adapter_required`, with exact
symbol/file evidence. Adding `editorial_reviewer.py` is allowed only when this
audit shows why extending `reviewer_registry.py` or
`timeline_review_packet.py` would violate ownership or create cyclic concerns.

Acceptance: no new code before this artifact exists and parses as UTF-8 JSON.

## 6. Task B — One reviewer identity, multiple lenses

Update the reviewer contract additively so that:

1. runtime identity is `editorial_reviewer`;
2. existing `reviewer_role` values remain valid as `rubric_lenses` and legacy
   artifact roles;
3. a review may use one or more registered lenses without implying multiple
   agent dispatches;
4. the reviewer authority is `findings_and_proposals_only`;
5. canonical mutation, repair, creative approval, and delivery claim are
   explicitly forbidden;
6. empty material findings are valid when strengths and evidence limitations
   are honestly recorded;
7. the reviewer is not instructed to agree, attack, or maximize finding count.

The skill language must define the stance as:

> Understand the intended outcome, inspect evidence, surface consequential
> differences, explain why they matter, and propose the smallest existing
> route that could resolve them. Preserve strengths. Do not manufacture faults.

Do not delete legacy reviewer roles or break `artifact_review` version 1.

## 7. Task C — Evidence manifest and reuse contract

Add or extend a machine-readable evidence manifest. Prefer extending
`timeline_review_packet.json`; create a separate manifest only if backward
compatibility requires it.

Minimum fields:

- `subject`: path, artifact role, full SHA-256, duration, media role;
- `picture_stream_fingerprint` when a stream probe can supply it;
- `audio_stream_fingerprint` or explicit unbound state;
- `subtitle_fingerprint`, text authority, or explicit unbound state;
- `evidence_items[]`: kind, path, SHA-256, generator capability, covered
  timeline window, source/subject binding, limitations;
- `generated_at`, generator version;
- `reuse_policy` and `invalidated_by`;
- `parent_manifest` for a delta review when used.

Required reuse behavior:

- identical picture stream, audio-only change: reuse wall/index evidence and
  re-probe audio;
- identical picture/audio, subtitle-only change: reuse walls/audio and
  regenerate subtitle binding evidence;
- bounded picture change: mark only intersecting wall pages stale;
- unknown or mismatched subject/hash: fail closed, never silently reuse;
- evidence may be read from a prior immutable packet, but the new review must
  record exactly what was reused and what was regenerated.

Do not build a cache daemon or database. This is a manifest contract and
bounded file reuse only.

## 8. Task D — Finding and proposal schema

Strengthen validation without breaking version-1 artifacts. A v2 review or an
additive `editorial_review` block must require:

Top level:

- `artifact_role`, `version`, `status`;
- `reviewer_identity`;
- `review_mode`: `full_context` or `cold_start`;
- `rubric_lenses`;
- `subject` and evidence-manifest binding;
- `inspection_scope` and `not_inspected`;
- `strengths[]`;
- `findings[]`;
- `evidence_gaps[]`;
- `human_creative_approval=false`;
- `final_delivery_claimed=false`.

Each finding requires:

- stable `finding_id` and `rubric_id`;
- `class`: `objective | process | structural_candidate | taste`;
- `priority`, `confidence`;
- `observation` separate from `interpretation`;
- `why_it_matters`;
- `fixable_at`: `clip | segment | story | process | future_project`;
- `target`: segment/clip/timeline window when applicable;
- `evidence_refs[]`, each resolving to a manifest item and bounded coordinate;
- `falsification_test` or explicit `human_taste_only`;
- exactly one primary `proposed_fix`, and at most one fallback.

Each proposed fix requires:

- `route`: existing Stage return route or `no_existing_route`;
- `capability_id`: existing registered capability or null only with
  `no_existing_route`;
- `target`;
- `expected_change`;
- `expected_unchanged`;
- `rerun_gates`;
- `requires_owner_or_integrator_verdict=true`.

Rules:

- `objective` and `process` may fail closed only when deterministic evidence
  proves the claim;
- `structural_candidate` is advisory until calibrated by owner verdicts;
- `taste` never becomes a machine PASS/FAIL and is capped at three findings,
  sorted by owner-value;
- story/future-project findings do not automatically reopen this candidate;
- unknown capability IDs fail validation;
- unresolved evidence references fail validation;
- no finding may contain a repair command or mutate an artifact.

## 9. Task E — Stage policy and discovery

Document one reviewer surface across Stage 0–10 without making every Stage a
mandatory review stop.

Required policy:

- Stage 0–2: on major story choice or requested A/B comparison;
- Stage 3: targeted Material Map audit, not full-pool reinspection;
- Stage 4–5: paper-edit/story-structure review before expensive render;
- Stage 6: candidate review only after build evidence exists;
- Stage 7–8: primary eye/ear/heart timeline review plus deterministic Verify;
- Stage 9: incremental review of the changed layer/window only;
- Stage 10: process/artifact-integrity review, never creative self-approval.

Add `skills/editorial-reviewer.md` as the one discoverable human/agent entry.
It must use a tool contract with no duplicate canonical ownership. Existing
Verify tools remain canonically owned by `skills/verify.md`; the new skill may
reference them as supporting tools.

Register the skill in `skills/INDEX.md` under `verify-delivery`. Add only the
minimum branch-registry/artifact-dictionary entries required for new artifacts
or capability IDs. Do not register aliases that duplicate an existing tool.

New documentation should use `V Pipeline` as the product name and may mention
`Hermes V Pipeline` once as a legacy alias. Do not mass-rename historical
artifacts, Python symbols, or archived decisions.

## 10. Task F — Admission fixtures

Create a fresh immutable acceptance root:

`.tmp/editorial_reviewer_convergence/admission_v1/`

Use small text/JSON fixtures and existing tiny media fixtures. Do not render a
long video. Prove:

1. a clean packet can return no material findings without inventing faults;
2. a contradictory claim is reported with evidence;
3. insufficient evidence returns UNKNOWN/evidence gap;
4. a taste observation cannot become deterministic FAIL;
5. an unknown capability proposal is rejected;
6. a valid existing route/capability proposal passes;
7. prior evidence with unchanged hashes is reused;
8. audio-only change reuses visual evidence but invalidates audio evidence;
9. picture change invalidates intersecting wall evidence;
10. reviewer output cannot claim creative approval or delivery;
11. legacy version-1 artifact reviews still validate;
12. one `editorial_reviewer` identity can apply multiple rubric lenses.

Also create an onboarding test based only on frozen text evidence for the known
S9 governance pattern. It should be able to flag, when present:

- stale handoff/current-state claim;
- missing work order;
- missing receipt/attestation/manifest;
- output sample-rate decision not recorded;
- latest finding absent from the ledger.

This fixture tests reviewer usefulness; it must not inspect or mutate the live
dirty S9 patch and must not repair those issues.

## 11. Red-first and validation

Required RED evidence before implementation:

- version-1 validator accepts a materially incomplete v2-shaped finding;
- no one-agent/multi-lens contract is discoverable;
- stale/mismatched evidence reuse is not rejected by a validator.

Then run focused GREEN tests:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest `
  tests.test_reviewer_registry `
  tests.test_reviewer_flow_acceptance `
  tests.test_timeline_review_packet `
  tests.test_skill_index `
  tests.test_skill_tool_contracts `
  tests.test_pipeline_skill_boundaries -v
```

If a new reviewer module is justified, include
`tests.test_editorial_reviewer`.

Run:

```powershell
C:\Users\user\miniconda3\python.exe tools/skill_tool_contract_audit.py --json
C:\Users\user\miniconda3\python.exe video_tools.py reviewer-flow-acceptance --level deep --scenario all --artifact-dir .tmp/editorial_reviewer_convergence/flow --out .tmp/editorial_reviewer_convergence/reviewer_flow_acceptance.json
git diff --check
```

Full suite is run once only after all focused, registry, UTF-8, JSON, hash, and
acceptance checks pass. If full suite is already marked STALE by an unrelated
dirty patch and cannot be attributed safely, report it as UNKNOWN and stop for
integrator direction; do not modify the unrelated patch.

## 12. Stop-loss

Stop at the last green state when:

- the same failure class recurs after one LOCAL correction;
- an edit outside the owner zone is required;
- backward compatibility would require deleting or changing version-1 review
  semantics;
- the worker would need to add a new Stage, route runner, LLM runtime, cache
  service, or repair authority;
- a proposed capability duplicates an existing registered tool;
- the dirty S9 patch drifts from its pre-work hashes/status;
- a test would require changing production render/audio/subtitle/effect code.

Do not hide a structural gap with a run-local script, hand-written PASS JSON,
allowlist, monkey patch, or private ffmpeg command.

## 13. Final report

Write:

`.tmp/editorial_reviewer_convergence/final/worker_report.md`

Include:

- pre/post branch, HEAD, status;
- exact changed files and commits, if any;
- reuse audit decisions;
- RED/GREEN commands and exit codes;
- focused/full-suite result and trust boundary;
- registry/tool ownership counts;
- acceptance artifact paths and SHA-256 values;
- evidence reuse proof;
- all deviations, retries, skips, blind spots, and UNKNOWN items;
- confirmation that the unrelated S9 dirty patch was unchanged;
- `human_creative_approval=false`;
- `final_delivery_claimed=false`.

Legal success state:

`WAITING_INTEGRATOR_EDITORIAL_REVIEWER_CONVERGENCE_REVIEW`
