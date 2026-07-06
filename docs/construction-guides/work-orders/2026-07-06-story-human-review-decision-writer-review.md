# Work Order: Story Human Review Decision Writer Review

Date: 2026-07-06

## Goal

Review and verify the completed `story_human_review_decision.json` writer before
it is committed to `master`.

The visible capability to protect: an operator can write a human story review
decision with a command, and the existing pipeline consumes it exactly like a
real human decision. The command must not become a shortcut that silently clears
`story_human_review_required` with partial approval, non-human review, missing
notes, corrupted text, or changed gate semantics.

## Owner Zone

- `docs/construction-guides/work-orders/2026-07-06-story-human-review-decision-writer-review-report.md`

## Review Scope

Read and review these current working-tree changes:

- `tools/write_story_human_review_decision.py`
- `tests/test_write_story_human_review_decision.py`
- `docs/video-pipeline-operating-map.md`
- `docs/pipeline-decision-tree.md`
- `docs/branch-contract-registry.md`
- `docs/branch-contract-registry.json`
- `docs/construction-guides/work-orders/2026-07-06-story-human-review-decision-writer.md`
- `docs/construction-guides/work-orders/2026-07-06-story-human-review-decision-writer-report.md`
- `docs/construction-guides/work-orders/2026-07-06-scripted-human-review-closure-drill.md`
- `docs/construction-guides/work-orders/2026-07-06-scripted-human-review-closure-drill-report.md`

## Forbidden Zone

- Do not edit `tools/`
- Do not edit `tests/`
- Do not edit `video_pipeline_core/`
- Do not edit provider/runtime/render/media branches
- Do not edit `.env`
- Do not edit `.venv_voxcpm/`
- Do not edit `reference repo/`
- Do not edit `Downloads/`
- Do not write into existing `.tmp/` runs
- Do not commit, branch, push, or create PRs

## Required Interpreter

Use this interpreter for every Python command:

`C:\Users\user\miniconda3\python.exe`

Do not use bare `python`, `pytest`, or another environment.

## Review Questions

Answer these directly in the report:

1. Does the command fail closed for non-human reviewer values?
2. Does approved require full required beat coverage?
3. Does partial approval avoid writing a misleading delivery-clearing artifact?
4. Do `revision_requested` and `rejected` require concrete notes or rejection
   evidence?
5. Does the command write UTF-8 JSON without replacement characters or
   question-mark placeholder runs?
6. Does the command leave delivery gate semantics unchanged?
7. Do docs and registry describe the operator step without overstating final
   delivery approval?
8. Are there large files, `.tmp` files, media files, or environment secrets in
   the working tree?

## Required Verification

Run and report exit codes:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_write_story_human_review_decision
C:\Users\user\miniconda3\python.exe -m unittest tests.test_write_story_human_review_decision tests.test_delivery_gate tests.test_pipeline_home
C:\Users\user\miniconda3\python.exe tools\write_story_human_review_decision.py --help
C:\Users\user\miniconda3\python.exe -c "import json; json.load(open('docs/branch-contract-registry.json', encoding='utf-8')); print('json ok')"
git diff --check
git status --short --branch --untracked-files=all
```

Also run at least one fresh `.tmp/` smoke that uses the command to create:

- approved decision and confirms `pipeline_home.py` reports `DONE / complete`
- revision decision and confirms `REPAIR / human_story_review`
- rejected decision and confirms `REPAIR / human_story_review`
- one expected-failure case for partial approval or non-human reviewer

## Stop-Loss

Stop after writing the review report if:

- Any verification command fails unexpectedly.
- The tool changes or depends on delivery gate semantics.
- The tool writes artifacts that can clear review without human approval.
- The tool requires edits outside the stated owner zone to pass.
- The working tree contains unexpected large/media/env files.

Do not fix code in this review round. Report findings with file paths and the
smallest reproduction command.

## Delegated Decisions

- Choose the exact smoke output root under `.tmp/`.
- Choose which expected-failure case to exercise if time is limited.
- Choose whether findings are blocking or non-blocking, but cite evidence.
- Choose whether to include concise excerpts from command output.

## Final Report Requirements

Write:

`docs/construction-guides/work-orders/2026-07-06-story-human-review-decision-writer-review-report.md`

The report must include:

- Overall verdict: pass, pass-with-notes, or blocked
- Findings first, ordered by severity
- Answers to all review questions
- Commands and exit codes
- Smoke output root and state results
- Working-tree hygiene result
- UTF-8/no-corruption result
- Whether this is ready for integrator commit/push
- Next recommended work grounded only in this review
