# Work Order: Story Human Review Decision Writer

Date: 2026-07-06

## Goal

Add an operator-facing command that writes `story_human_review_decision.json`
for a scripted delivery run.

The visible capability: after a human reviews `story_to_material_map.json`, the
operator can run one pinned command to approve, request revision, or reject the
story/material mapping without hand-writing JSON. The resulting artifact must be
accepted by the existing delivery gate and `pipeline_home.py` states.

This follows the scripted human review closure drill, which proved the gate
state machine works but left the operator step as manual JSON editing.

## Owner Zone

- `tools/write_story_human_review_decision.py`
- `tests/test_write_story_human_review_decision.py`
- `docs/video-pipeline-operating-map.md`
- `docs/pipeline-decision-tree.md`
- `docs/branch-contract-registry.md`
- `docs/branch-contract-registry.json`
- `docs/construction-guides/work-orders/2026-07-06-story-human-review-decision-writer-report.md`

## Forbidden Zone

- `video_pipeline_core/`
- Existing delivery gate behavior, except through tests that prove integration
- Existing provider/runtime code
- Render tools
- VoxCPM / music / subtitle branches
- `.env`
- `.venv_voxcpm/`
- `reference repo/`
- `Downloads/`
- Existing `.tmp/` runs except read-only smoke inspection
- Git commit, branch, push, or PR operations

## Required Interpreter

Use this interpreter for every Python command:

`C:\Users\user\miniconda3\python.exe`

Do not use bare `python`, `pytest`, or another environment.

## Required Command Behavior

Create:

`tools/write_story_human_review_decision.py`

The tool must accept a run directory and write:

`<run>/story_human_review_decision.json`

Required behavior:

- Read `story_contract.json` from the run directory.
- Discover required story beat ids from `required_story_beats` or `beats`.
- Support decisions:
  - `approved`
  - `revision_requested`
  - `rejected`
- Require human reviewer evidence:
  - accept `--reviewer human` or equivalent repo-style option
  - non-human reviewer must fail closed unless explicitly writing a non-human
    dry artifact is a documented non-delivery mode
- For `approved`:
  - support approving all required beats without typing them one by one
  - support explicit approved beat ids
  - fail closed if approval does not cover all required beats
- For `revision_requested`:
  - require concrete notes
  - write notes into the decision artifact
- For `rejected`:
  - require concrete notes or rejected beat ids
  - write evidence into the decision artifact
- Write UTF-8 JSON with stable keys and `artifact_role` set to
  `story_human_review_decision`.
- Print JSON summary to stdout by default or with `--json`.
- Never modify media files or unrelated run artifacts.

## Red-First Requirements

Before implementing the tool, add focused failing tests proving:

- Missing tool import/command currently fails.
- Approved all beats should create an artifact that makes `pipeline_home.py`
  report `DONE / complete`.
- Partial approval should fail and must not silently clear review.
- `revision_requested` should create an artifact that routes to
  `REPAIR / human_story_review`.
- `rejected` should create an artifact that routes to
  `REPAIR / human_story_review`.
- Notes are required for revision/rejection.
- The artifact is valid UTF-8 and contains no replacement character.

## Acceptance Commands

Run and report exit codes:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_write_story_human_review_decision
C:\Users\user\miniconda3\python.exe -m unittest tests.test_write_story_human_review_decision tests.test_delivery_gate tests.test_pipeline_home
C:\Users\user\miniconda3\python.exe tools\write_story_human_review_decision.py --help
C:\Users\user\miniconda3\python.exe -c "import json; json.load(open('docs/branch-contract-registry.json', encoding='utf-8')); print('json ok')"
git diff --check
```

Also run a smoke test in a new `.tmp/` output directory:

1. Build or copy a lightweight scripted run fixture with a `final.mp4`,
   `delivery_gate.json`, `story_contract.json`, and `story_to_material_map.json`.
2. Use the new command to write an approved decision.
3. Run `tools/pipeline_home.py --run <fixture> --json` and confirm
   `DONE / complete`.
4. Repeat revision and rejected cases and confirm repair routing.

## Stop-Loss

Stop and report without broader patching if:

- Making this command work appears to require changing delivery gate semantics.
- The tool needs provider/runtime/render/media changes.
- Existing closure drill behavior regresses.
- Any command needs a Python interpreter other than
  `C:\Users\user\miniconda3\python.exe`.

## Delegated Decisions

- Exact CLI flag names, as long as `--help` is clear and tests cover them.
- Exact JSON field order and optional metadata fields.
- Whether the command defaults to JSON stdout or requires `--json`.
- Whether smoke fixtures use copied `final.mp4` or minimal placeholder media,
  as long as `pipeline_home.py` observes the expected states.
- Exact wording of operator-facing errors.

## Final Report Requirements

Write:

`docs/construction-guides/work-orders/2026-07-06-story-human-review-decision-writer-report.md`

The report must include:

- Files changed
- CLI examples for approved, revision_requested, and rejected
- Red-first evidence
- Acceptance commands and exit codes
- Smoke output root and per-case states
- UTF-8 / no-corruption check result
- Deviations, if any
- Stop-loss reason, if stopped
- Next recommended work grounded only in this round

