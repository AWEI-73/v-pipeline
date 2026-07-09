# 2026-07-09 Global Route Closure, Signature, And Doc Hygiene

## Goal

Finish the repository-level closure layer for the video pipeline without changing rendered media behavior: every product-route stage must be mechanically registered, every stage must declare verify/review ownership, every agentic review that can affect route progression must use the shared `sign_review` signature shape, and top-level docs/reference material must be classified so route facts do not become orphan prose.

Background source: user requested full closure for the factory route, unified signature handling, and lightweight doc/reference hygiene. Current graduation route already has a thin wrapper and partial signature enforcement; this work should generalize and harden that closure, not restart the product route.

## Owner Zone

- `video_pipeline_core/graduation_product_route_runner.py`
- `video_pipeline_core/reviewer_registry.py`
- `video_pipeline_core/visual_selection_review_decision.py`
- `video_pipeline_core/next_action_vocabulary.py`
- `video_pipeline_core/*route*_integrity*.py`
- `video_pipeline_core/*doc*_hygiene*.py`
- `video_pipeline_core/*factory*_improvement*.py`
- `tools/*route*_integrity*.py`
- `tools/*doc*_hygiene*.py`
- `tools/*factory*_improvement*.py`
- `tests/test_graduation_product_route_runner.py`
- `tests/test_*route*_integrity*.py`
- `tests/test_*doc*_hygiene*.py`
- `tests/test_*factory*_improvement*.py`
- `docs/branch-contract-registry.json`
- `docs/branch-contract-registry.md`
- `docs/pipeline-decision-tree.md`
- `docs/video-pipeline-operating-map.md`
- `docs/INDEX.md`
- `docs/reference-repos-map.md`
- `docs/construction-guides/work-orders/2026-07-09-global-route-closure-signature-doc-hygiene-report.md`

## Forbidden Zone

- `Downloads/`
- `deliveries/`
- existing `.tmp/` production, rehearsal, diagnostic, and delivery runs
- media outputs including `final*.mp4`, rendered previews, audio mixes, subtitles from prior runs
- `.env`, `.venv*`, `reference repo/`, VoxCPM runtime folders
- `video_pipeline_core/delivery_gate.py` unless a failing acceptance command proves route-closure output is unreadable by the existing gate
- `tools/pipeline_home.py` unless a failing acceptance command proves route-closure status cannot be surfaced
- unrelated docs outside the owner zone

## Required Pieces

1. Preserve and verify the current signature-lock edits. Do not revert the existing uncommitted changes in the five signature-related files. Confirm visual selection review and effect review signing both fail closed when a present review artifact lacks `review_signature`.
2. Add or extend a route-closure integrity check that treats the route stage table, branch registry, next-action vocabulary, and reviewer registry as machine facts. It must detect missing owner, missing kind, invalid verify/review kind, invalid next action, signed-review stages without review artifacts, and stage artifacts that are not represented in the route/registry closure surface.
3. Unify agentic review signature expectations. Agentic review artifacts that can advance a route must either carry a valid `review_signature` built by `sign_review`, or be explicitly classified as `human_review` / `verify` and not agentic. The rule must be testable with fixtures, not prose.
4. Add lightweight docs/reference hygiene. Root-level `docs/*.md` files that are canonical route/operator facts must be referenced by `docs/INDEX.md`, `docs/branch-contract-registry.md/json`, `docs/pipeline-decision-tree.md`, `docs/video-pipeline-operating-map.md`, or `docs/reference-repos-map.md`. Work-order reports, archive, generated, setup, runbook, and reference-only folders may be classified/exempt, but the exemption list must be explicit and tested.
5. Add the missing factory improvement loop skeleton. It should convert review/rendered-QA/no-skip findings into a structured backlog or improvement artifact with owner branch, product-level impact, proposed acceptance hook, and whether it is golden-path-worthy. It must not auto-edit media or silently update the golden path.
6. Update operator docs only where they are the canonical map for the new closure checks. Do not expand narrative docs just to explain implementation details.

## Red-First Verification

- Add or preserve failing tests for present-but-unsigned `visual_selection_review.json` and `effect_review.json`.
- Add failing tests for at least one route-closure orphan: a stage with invalid/missing kind or a signed-review stage with no review artifact.
- Add failing tests for at least one doc hygiene orphan: a root-level canonical doc not listed in the chosen index/reference surface.
- Add failing tests for the factory improvement loop: a rendered QA finding must become a structured improvement item instead of disappearing into a report.

If the current working tree already contains one red/green behavior, record that as an existing red-first carryover and add red-first coverage for the next uncovered behavior instead.

## Acceptance Commands

Run with the pinned interpreter only:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_graduation_product_route_runner tests.test_reviewer_registry tests.test_review_signature
C:\Users\user\miniconda3\python.exe -m unittest tests.test_branch_registry_integrity tests.test_interactive_skill_flow_docs
C:\Users\user\miniconda3\python.exe -m unittest discover -s tests -p "test_*route*_integrity*.py"
C:\Users\user\miniconda3\python.exe -m unittest discover -s tests -p "test_*doc*_hygiene*.py"
C:\Users\user\miniconda3\python.exe -m unittest discover -s tests -p "test_*factory*_improvement*.py"
C:\Users\user\miniconda3\python.exe -m unittest tests.test_graduation_product_route_runner tests.test_rendered_product_qa tests.test_no_skip_execution_trace tests.test_pipeline_home tests.test_delivery_gate tests.test_delivery_gate_report
C:\Users\user\miniconda3\python.exe -c "import json; json.load(open('docs/branch-contract-registry.json', encoding='utf-8')); print('json ok')"
git diff --check
```

Expected exit code for every command: `0`. Existing CRLF warnings from `git diff --check` are acceptable; whitespace errors are not.

## Stop-Loss Limits

- Do not render, package, deliver, or modify any media.
- Do not write `story_human_review_decision.json`, transcript approval, legal/music approval, or delivery approval artifacts.
- If the doc hygiene check would require rehoming or rewriting more than five existing docs, stop and report the classified orphan list instead of performing a broad doc migration.
- If route closure requires changing delivery gate semantics, stop and report the exact unreadable artifact contract.
- If the existing signature-lock changes conflict with this work order, preserve the code facts and report the conflict before editing further.

## Delegated Decisions

- Names of new integrity/hygiene/factory-loop helper modules and CLI tools may follow repo conventions.
- The doc hygiene exemption list may be small and pragmatic, as long as it is machine-readable and tested.
- The factory improvement artifact may be JSON-only in this round.
- The worker may choose whether the route-closure check is one combined CLI or multiple focused CLIs, provided tests can run independently.
- The worker may update existing docs in the owner zone instead of creating new docs when that keeps the canonical map smaller.

## Evidence Format

The final report must start with `[WORKER REPORT - REVIEW MODE]` and include:

- changed files
- route/signature closure result
- doc/reference hygiene result
- factory improvement loop result
- commands and exit codes
- red-first evidence
- deviations
- blockers / stop-loss
- next recommended work, advisory only
- final output prompt for the next manager/worker, concise index format only: report path, 3-5 must-read artifacts, 4-6 key claims, current blocker, product-level objective, scope/stop-loss, and next likely work. The prompt must frame the report as unverified evidence and require claim/artifact verification before further planning.
