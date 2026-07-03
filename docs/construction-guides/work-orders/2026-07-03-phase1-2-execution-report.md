# Phase 1-2 Execution Report

Date: 2026-07-03

Scope:

- Work order: `docs/construction-guides/work-orders/2026-07-03-phase1-entry-contract.md`
- Work order: `docs/construction-guides/work-orders/2026-07-03-phase2-registry-manifest.md`
- Background plan: `docs/construction-guides/2026-07-03-convergence-single-pipeline-plan.md`

## Phase 1 - Entry Contract

Status: complete

Commit:

- `45492eee Slim entry contract to three-tier START_HERE`

Changes:

- Slimmed `docs/START_HERE_VIDEO_PIPELINE.md` to a Rule Zero plus three-tier entry contract.
- Reduced `HANDOFF_CURRENT.md` to a current handoff pointer instead of a second runbook.
- Reduced `CLAUDE.md` to the skill-first entry guard and minimal project facts.

Acceptance evidence:

- Tier 1 path count: 6.
- `docs/branch-contract-registry.json` appears in Tier 1.
- `HANDOFF_CURRENT.md` size: 1078 bytes.
- Tier 1 paths validated with `git ls-files`.
- Full suite after rerun: `Ran 2336 tests in 523.455s` / `OK`.

Notes:

- One unrelated generated-image provider test failed once during the first full-suite attempt, then passed standalone and passed in the rerun. No source change was made for that transient.

## Phase 2 Piece 1 - next_action Vocabulary

Status: complete

Commit:

- `a1d6a7ea Add next_action vocabulary and registry integrity tests`

Changes:

- Added `video_pipeline_core/next_action_vocabulary.py` as the closed `next_action` vocabulary source.
- Added registry integrity checks for registry parsing, skill/doc existence, registry next actions, and `dashboard_state.py` next-action literals.

Acceptance evidence:

- Focused test: `Ran 5 tests in 0.006s` / `OK`.
- Full suite: `Ran 2341 tests in 523.560s` / `OK`.

## Phase 2 Piece 2 - Stages Manifest

Status: complete

Commit:

- `c5b9585f Add stages manifest to branch contract registry`

Changes:

- Bumped `docs/branch-contract-registry.json` to version 2.
- Added `stages[]` manifests for all seven registered branches.
- Each stage records skill ownership, artifacts in/out, gate, pass next actions, and fail next actions.
- Extended registry integrity tests for exact stage shape, stage skills, stage artifacts, and stage next actions.

Acceptance evidence:

- Focused test: `Ran 8 tests in 0.009s` / `OK`.
- Full suite: `Ran 2344 tests in 521.097s` / `OK`.

Notes:

- No update to `docs/interface-contracts/pipeline-product-artifact-dictionary.json` was required; the stage manifest uses already-registered product artifacts.

## Phase 2 Piece 3 - registry-audit Command

Status: complete

Commit:

- `01deaaef Add registry-audit command`

Changes:

- Added `video_tools.py registry-audit`.
- The command reads `docs/branch-contract-registry.json` and `docs/pipeline-decision-tree.md`.
- It checks branch decision-tree coverage, stage gate coverage, and unmapped branch-like decision-tree headings.
- It is read-only by default and writes an optional Markdown report only with `--write-report`.
- Added `tests/test_registry_audit.py` with real-registry pass and fake-branch fail coverage.
- Added the new command to `video_pipeline_core/tool_command_catalog.py` as `verify`.

Acceptance evidence:

- CLI check: `Registry Audit: OK (7 branches, 13 stages)`.
- Focused test: `Ran 2 tests in 0.563s` / `OK`.
- Command catalog focused test after classification: `Ran 7 tests in 0.679s` / `OK`.
- First full-suite attempt failed only because `registry-audit` was unclassified in the command catalog.
- Full suite after catalog classification: `Ran 2346 tests in 521.666s` / `OK`.

Scope note:

- `video_pipeline_core/tool_command_catalog.py` was updated with one command classification because the repository's existing command-manifest test requires every `video_tools.py` dispatch command to be classified. This was a necessary CLI-surface alignment for Piece 3.

## Blockers / Contradictions

- No active blocker remains.
- The only work-order tension was Piece 3's command catalog classification. The new subcommand could not pass the existing full-suite governance test without that classification.

## Final Status

Phase 1 and Phase 2 are complete. The repo now has:

- a three-tier entry contract;
- a closed `next_action` vocabulary;
- a branch stage manifest;
- a registry-to-decision-tree audit command;
- focused tests and full-suite evidence for each committed piece.

## Phase 2.5

Status: complete

Commits:

- `d1079c75 Validate stage artifacts against both dictionaries`
- `92b90d72 Close next_action vocabulary over core emitters`

Changes:

- Bumped `docs/branch-contract-registry.json` to version 3.
- Added the Stage 0 `video_intent.json` output to the main pipeline manifest.
- Added a main-pipeline `contract-compile` stage with `segment_contract.json` output and `ready_for_build` / `revise:spec` next actions.
- Extended stage artifact validation to check both the product artifact dictionary and the pipeline API dictionary, including API inputs, outputs, and forbidden writes.
- Added `ready_for_build` and `revise:spec` to the closed next-action vocabulary.
- Replaced the dashboard-only next-action scrape with a core emitter scrape over direct `video_pipeline_core/*.py` files.
- Expanded `video_pipeline_core/next_action_vocabulary.py` to include currently emitted core `next_action` literals and registry stage actions verbatim.

Acceptance evidence:

- Focused registry tests after dictionary validation: `Ran 8 tests in 0.023s` / `OK`.
- `python video_tools.py registry-audit --json`: OK, 7 branches, 14 stages, 0 findings.
- Full suite after dictionary validation: `Ran 2346 tests in 557.758s` / `OK`.
- Focused registry tests after emitter closure: `Ran 8 tests in 0.028s` / `OK`.
- Full suite after emitter closure: `Ran 2346 tests in 555.751s` / `OK`.

Notes:

- `contract-compile.gate` was set to `BUILD` rather than `spec-review` because the current decision tree has normalized BUILD gate prose but no normalized `spec-review` gate label, and this phase did not allow changing the audit semantics or the decision-tree gate vocabulary.
- `final.mp4` was added to the verify-delivery stage artifact surface because the API dictionary mentions it through forbidden writes. `final_promotion_report.json` was not added because it is not currently named by the API dictionary.
- The core emitter vocabulary intentionally preserves existing literals exactly. Follow-up cleanup candidates remain: mixed dash/underscore effect-factory actions, colon/paren revise actions, generic actions such as `build` / `curator` / `handoff`, and node-number actions such as `node_12_verify`.

## Phase 4

Status: complete

Commits:

- `21e30115 Add golden-path e2e smoke harness`
- `b730bc00 Enforce target_length at spec review and dry build`
- `434a9d84 Route revise:director through supply revision`

Changes:

- Added `video_pipeline_core/e2e_smoke.py` and the `video_tools.py e2e-smoke` command.
- Added `tests/test_e2e_smoke.py` to lock the stock-story smoke trace, target-length enforcement, render-output path handling, and revise-director routing.
- Registered `e2e-smoke` in `video_pipeline_core/tool_command_catalog.py` as an acceptance command.
- Hardened `video_pipeline_core/spec_review.py` so `text_layer: none` / `auto` are not counted as narration seconds.
- Added explicit target-length enforcement through `brief.enforce_target_length`, `brief.strict_target_length`, or `contract.enforce_target_length`.
- Routed `revise:director(spec_review)` with `script_overreach` and usable `supply_review.json` evidence to `director_supply_revision`.
- Added `director_supply_revision` to the next-action vocabulary.

Acceptance evidence:

- `python video_tools.py e2e-smoke --case stock_story`: OK, final next action `complete_review_final`.
- Focused smoke tests after harness: `Ran 4 tests in 0.569s` / `OK (expected failures=2)`.
- Full suite after harness: `Ran 2350 tests in 685.789s` / `OK (expected failures=2)`.
- Target-length red test failed before implementation with `ready_for_build True is not false`.
- Focused target-length tests after fix: `Ran 29 tests in 1.898s` / `OK (expected failures=1)`.
- Full suite after target-length fix: `Ran 2350 tests in 718.951s` / `OK (expected failures=1)`.
- Revise-director red test failed before implementation by returning `revise:director(spec_review)` instead of `director_supply_revision`.
- Focused revise-director/dashboard/vocabulary tests after fix: `Ran 67 tests in 3.482s` / `OK`.
- Full suite after revise-director fix: `Ran 2350 tests in 713.904s` / `OK`.

Notes:

- The render-output-path probe was already green, so no code change was made for that piece. Existing coverage confirms an external final path from `artifact_manifest.json` plus a passing verify result does not stall on a missing canonical root `final.mp4`.
- Target-length enforcement is compatibility-preserving: strict mismatch blocks only when the brief or contract explicitly opts into enforcement, while severe non-enforced mismatch remains a warning.

## Phase 3

Status: partially complete; preservation blocker recorded

Commit:

- `3df58cfd Add skill ownership index and closure test`

Changes:

- Added `skills/INDEX.md` as the live skill ownership index.
- Added `tests/test_skill_index.py`.
- Every live `skills/*.md` file except `skills/INDEX.md` now has exactly one index row.
- Registry-claimed skills must appear in the index with matching owner branch ids.
- Index owners are constrained to branch ids from `docs/branch-contract-registry.json` plus `shared` and `archive`.
- `audio-director.md` is explicitly owned by `soundtrack-arranger, subtitle-voiceover`.
- `route.md` is marked as `archive` but left in place.
- The index records the known Stage 0 overlap: `video-workflow.md` and `video-intent-planner.md`.

Acceptance evidence:

- Focused skill-index tests after fix: `Ran 3 tests in 0.005s` / `OK`.
- Full suite after skill-index commit: `Ran 2353 tests in 680.805s` / `OK`.

Preservation check:

- `skills/route.md` was not moved to archive.
- The required preservation check found live knowledge in `skills/route.md` that is not equivalently covered by `docs/pipeline-decision-tree.md`, `docs/video-pipeline-operating-map.md`, `docs/canonical-video-pipeline-route.md`, or `skills/video-pipeline-route.md`.
- Missing preserved knowledge includes the Node 14 Revision Loop / Change Request Contract with `spec_delta`, `build_delta`, `verify_delta`, rerender/version route, `--only-seg`, `state.json next_action`, and dashboard overwrite semantics.
- Missing preserved knowledge also includes the two-axis layering explanation: orchestration/route vs SPEC/BUILD/VERIFY, with `state/decision_log` as the DECISION LOG layer and the only VERIFY-to-route interface.

Notes:

- Phase 3 Piece 2 is intentionally stopped per the work order's preservation gate. The safe next step is to migrate the remaining Node 14 and two-axis route knowledge into canonical route docs before archiving `skills/route.md`.
