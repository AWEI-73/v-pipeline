[WORKER REPORT - REVIEW MODE]

# Global Route Closure, Signature, And Doc Hygiene Report

## Summary

Route-control closure was implemented without rendering, packaging, media edits, or approval artifacts.

The existing signature-lock edits were preserved and treated as in-scope. Additional closure layers now cover:

- route stage / registry / next-action / reviewer-registry integrity
- fail-closed agentic review signatures for present visual/effect review artifacts
- lightweight top-level docs/reference hygiene
- structured factory improvement-loop backlog generation from QA/review findings

One acceptance deviation remains: the literal wildcard `unittest` command from the work order fails under Windows/PowerShell because `unittest` receives the wildcard strings as module names. Equivalent `unittest discover -p` pattern commands pass and are recorded below, but they are not represented as the original command passing.

## Changed Files

Signature-lock carryover preserved:

- `video_pipeline_core/graduation_product_route_runner.py`
- `video_pipeline_core/reviewer_registry.py`
- `video_pipeline_core/visual_selection_review_decision.py`
- `video_pipeline_core/next_action_vocabulary.py`
- `tests/test_graduation_product_route_runner.py`

New route-control closure:

- `video_pipeline_core/route_closure_integrity.py`
- `tools/route_closure_integrity.py`
- `tests/test_route_closure_integrity.py`

New docs/reference hygiene:

- `video_pipeline_core/doc_reference_hygiene.py`
- `tools/doc_reference_hygiene.py`
- `tests/test_doc_reference_hygiene.py`

New factory improvement loop:

- `video_pipeline_core/factory_improvement_loop.py`
- `tools/factory_improvement_loop.py`
- `tests/test_factory_improvement_loop.py`

Canonical docs/registry updates:

- `docs/branch-contract-registry.json`
- `docs/branch-contract-registry.md`
- `docs/INDEX.md`
- `docs/video-pipeline-operating-map.md`

Report:

- `docs/construction-guides/work-orders/2026-07-09-global-route-closure-signature-doc-hygiene-report.md`

Work order doc was already present as untracked input evidence:

- `docs/construction-guides/work-orders/2026-07-09-global-route-closure-signature-doc-hygiene.md`

## Route / Signature Closure Result

Implemented:

- `ROUTE_STAGES` signed-review stages now declare `review_artifact`.
- Present-but-unsigned `visual_selection_review.json` blocks with `next_action=sign_review`.
- Present-but-unsigned `effect_review.json` / `effect_director_review.json` blocks with `next_action=sign_review`.
- `visual_selection_review_decision.build_visual_selection_review()` writes a `review_signature` using `sign_review`.
- `visual_selection_reviewer` is registered in `reviewer_registry`.
- `sign_review` is included in `NEXT_ACTION_VOCABULARY`.
- `route_closure_integrity` validates:
  - missing/unknown owner
  - missing/invalid kind
  - signed-review stage missing review artifact
  - unregistered review artifact
  - stage artifact missing from registry closure surface
  - invalid stage next actions

Registry closure additions:

- `shot_level_material_proof_plan.json` registered under Material Map.
- `render_handoff.json` registered under Soundtrack Arranger.
- `effect_review.json` registered under Effect Factory.

## Doc / Reference Hygiene Result

Implemented:

- `doc_reference_hygiene` classifies root-level `docs/*.md` files as:
  - referenced by canonical surfaces
  - explicitly exempt
  - orphan canonical docs
- Current top-level docs classify without orphan canonical docs.
- Explicit exemptions remain small and machine-readable:
  - `docs/build-capability-alignment.md`
  - `docs/capcut-pipeline-integration-design.md`
  - `docs/dashboard-node-skill-output-spec.md`
  - `docs/windows-native-migration-spec.md`

Docs updated lightly:

- `docs/INDEX.md` adds the closure hygiene tool row.
- `docs/branch-contract-registry.md/json` records route closure as machine facts and lists new tools.
- `docs/video-pipeline-operating-map.md` adds the new tools to the film-canon route tool index.

No broad doc migration was performed.

## Factory Improvement Loop Result

Implemented:

- `factory_improvement_loop.build_factory_improvement_backlog()`
- `tools/factory_improvement_loop.py`

Rendered QA / no-skip findings now become structured backlog items with:

- `owner_branch`
- `product_level_impact`
- `proposed_acceptance_hook`
- `golden_path_worthy`
- `auto_edits_media=false`
- `updates_golden_path=false`

The loop does not edit media, render outputs, or golden-path docs.

## Red-First Evidence

Red command:

- `C:\Users\user\miniconda3\python.exe -m unittest tests.test_route_closure_integrity tests.test_doc_reference_hygiene tests.test_factory_improvement_loop`
- Exit: `1`
- Failure reason: six `ModuleNotFoundError` errors for missing:
  - `video_pipeline_core.route_closure_integrity`
  - `video_pipeline_core.doc_reference_hygiene`
  - `video_pipeline_core.factory_improvement_loop`

Second red/structural command after initial implementation:

- Same command
- Exit: `1`
- Failure reason:
  - route closure found unregistered current route artifacts:
    - `shot_level_material_proof_plan.json`
    - `render_handoff.json`
    - `effect_review.json`
  - doc hygiene found `docs/INDEX.md` self-classification gap

Green command:

- `C:\Users\user\miniconda3\python.exe -m unittest tests.test_route_closure_integrity tests.test_doc_reference_hygiene tests.test_factory_improvement_loop`
- Exit: `0`
- Result: `Ran 6 tests ... OK`

Existing signature-lock carryover evidence:

- `C:\Users\user\miniconda3\python.exe -m unittest tests.test_graduation_product_route_runner tests.test_reviewer_registry tests.test_review_signature`
- Exit: `0`
- Result: `Ran 23 tests ... OK`

## Commands And Exit Codes

Acceptance command:

- `C:\Users\user\miniconda3\python.exe -m unittest tests.test_graduation_product_route_runner tests.test_reviewer_registry tests.test_review_signature`
- Exit: `0`
- Result: `Ran 23 tests ... OK`

Acceptance command:

- `C:\Users\user\miniconda3\python.exe -m unittest tests.test_branch_registry_integrity tests.test_interactive_skill_flow_docs`
- Exit: `0`
- Result: `Ran 13 tests ... OK`

Acceptance command as written:

- `C:\Users\user\miniconda3\python.exe -m unittest tests.test_*route*_integrity* tests.test_*doc*_hygiene* tests.test_*factory*_improvement*`
- Exit: `1`
- Result: `unittest` tried to import literal module names containing `*` and failed with `ModuleNotFoundError`.

Supplemental equivalent pattern commands:

- `C:\Users\user\miniconda3\python.exe -m unittest discover -s tests -p "test_*route*_integrity*.py"`
- Exit: `0`
- Result: `Ran 3 tests ... OK`

- `C:\Users\user\miniconda3\python.exe -m unittest discover -s tests -p "test_*doc*_hygiene*.py"`
- Exit: `0`
- Result: `Ran 2 tests ... OK`

- `C:\Users\user\miniconda3\python.exe -m unittest discover -s tests -p "test_*factory*_improvement*.py"`
- Exit: `0`
- Result: `Ran 1 test ... OK`

Acceptance command:

- `C:\Users\user\miniconda3\python.exe -m unittest tests.test_graduation_product_route_runner tests.test_rendered_product_qa tests.test_no_skip_execution_trace tests.test_pipeline_home tests.test_delivery_gate tests.test_delivery_gate_report`
- Exit: `0`
- Result: `Ran 174 tests ... OK`

Acceptance command:

- `C:\Users\user\miniconda3\python.exe -c "import json; json.load(open('docs/branch-contract-registry.json', encoding='utf-8')); print('json ok')"`
- Exit: `0`
- Result: `json ok`

Final checks:

- `C:\Users\user\miniconda3\python.exe - <UTF-8/no-corruption check script>`
- Exit: `0`
- Result: checked 5 generated/updated Markdown/JSON files

- `git diff --check`
- Exit: `0`
- Result: existing CRLF warnings only; no whitespace errors

## Deviations

- The literal wildcard `unittest` acceptance command does not work under the current Windows/PowerShell execution path. It failed before code assertions ran. Equivalent `unittest discover -p` pattern commands were run and passed.
- No separate `.tmp` output root was created because the work order owner zone did not include one. Evidence is in tests, code, docs, and this report.

## Blockers / Stop-Loss

No delivery gate semantic change was required.

No media was rendered, packaged, delivered, or modified.

No story, transcript, legal/music, or delivery approval artifact was written.

Reviewer-found blocker:

- Direct execution of the three new CLI tools initially failed with `ModuleNotFoundError: No module named 'video_pipeline_core'` because the tools did not add the repository root to `sys.path`.
- The work-order wildcard `unittest` command also failed on this Windows/PowerShell path because `unittest` received literal module names containing `*`.

Post-review repair:

- `tools/route_closure_integrity.py`, `tools/doc_reference_hygiene.py`, and `tools/factory_improvement_loop.py` now add the repository root to `sys.path`, matching existing direct CLI tools.
- `tests/test_route_closure_integrity.py`, `tests/test_doc_reference_hygiene.py`, and `tests/test_factory_improvement_loop.py` now verify direct CLI execution.
- The work-order acceptance command was updated to use `unittest discover -p` patterns instead of literal wildcard module names.

Remaining blocker: none for route-closure tooling. Product/media delivery remains out of scope for this work order.

## Advisory Next Work

Advisory next work is to normalize the wildcard acceptance command in a future work order or repo convention, for example by pinning `unittest discover -p` commands for Windows. Do not broaden this into media/content repair.

## Final output prompt

You are reviewing unverified worker evidence for Global Route Closure, Signature, And Doc Hygiene. Verify claims and artifacts before accepting conclusions.

Report path:
- `docs/construction-guides/work-orders/2026-07-09-global-route-closure-signature-doc-hygiene-report.md`

Must-read artifacts:
- `video_pipeline_core/route_closure_integrity.py`
- `video_pipeline_core/doc_reference_hygiene.py`
- `video_pipeline_core/factory_improvement_loop.py`
- `docs/branch-contract-registry.json`
- `tests/test_route_closure_integrity.py`

Key claims to verify:
- Present visual/effect review artifacts now fail closed unless they carry a valid `review_signature`.
- Route closure integrity checks route stage owner/kind/artifact/review registration against registry facts.
- Top-level doc/reference hygiene classifies canonical docs and reports orphans.
- Rendered-QA/no-skip findings can become structured factory improvement backlog items.
- No media, delivery package, or approval artifact was written.
- One literal wildcard `unittest` acceptance command still exits `1`; equivalent discover-pattern commands pass.

Current blocker:
- Work-order wildcard `unittest` command is not executable as written on this Windows/PowerShell path.

Product-level objective:
- Keep route-control facts machine-checkable so production route progress cannot depend on unsigned reviews, orphan docs, or narrative-only QA findings.

Scope / stop-loss:
- Do not render, package, deliver, modify media, or change delivery gate semantics. Treat this report as unverified evidence.

Next likely work:
- Verify the diff and decide whether to amend future Windows acceptance commands to use `unittest discover -p` patterns instead of literal wildcard module names.
