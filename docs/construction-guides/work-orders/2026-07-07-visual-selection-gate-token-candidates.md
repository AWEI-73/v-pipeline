# Work Order: Visual Selection Gate For Token Candidates

Date: 2026-07-07

## Goal

Fix the production-line gap exposed by Graduation V1/V2: token/folder-name
material classification is useful as a cheap candidate pool, but it must not be
accepted as final visual selection for rendered story beats.

Visible capability to prove: graduation production can keep the low-cost
token-based catalog, but render-facing selections for sensitive beats must pass
a visual confirmation gate first.

## Failure Being Fixed

V1/V2 selected paths such as `工安早會/IMG_2120.JPG` for newcomer/basic-training
beats because the folder/file path matched tokens. The actual visual content was
not reliably confirmed, so supervisor/director imagery could appear in
newcomer/basic-skill sections.

This is a structural issue:

```text
path-token catalog -> worker guesses final clip -> render
```

Correct target:

```text
path-token catalog -> visual candidate check -> accepted visual selection -> render
```

## Owner Zone

- New helper under `video_pipeline_core/` for visual-selection gating
- New CLI under `tools/` if useful
- `video_pipeline_core/graduation_film_blueprint_catalog.py` only if needed to
  mark token catalog outputs as candidates, not accepted selections
- `tests/test_graduation_film_blueprint_catalog.py`
- New focused test under `tests/` if cleaner
- `docs/video-pipeline-operating-map.md`
- `docs/pipeline-decision-tree.md`
- `docs/branch-contract-registry.md`
- `docs/branch-contract-registry.json`
- `docs/construction-guides/work-orders/2026-07-07-visual-selection-gate-token-candidates-report.md`

## Forbidden Zone

- Render implementation
- Delivery gate semantics
- VoxCPM / voiceover provider implementation
- Music provider/download implementation
- Existing `.tmp/` runs
- `Downloads/` writes
- `deliveries/`
- `.env`
- `.venv_voxcpm/`
- `reference repo/`
- Git commit, branch, push, or PR operations

## Required Interpreter

Use this interpreter for every Python command:

`C:\Users\user\miniconda3\python.exe`

Do not use bare `python`, `pytest`, or another environment.

## Required Semantics

Token/folder/path matches are candidate evidence only.

Any render-facing visual selection for these sensitive beats must include
visual confirmation evidence:

- `newcomer_training_start`
- `basic_training`
- `supervisor_source_speech`
- `teacher_class_intro`
- `opening_story`
- `closing_story`

Minimum accepted selection record:

- beat/module id
- source-relative path
- candidate source, e.g. `token_folder_match`
- representative frame/contact-sheet path or frame evidence reference
- visual confirmation status: `accepted`, `rejected`, or `needs_repick`
- reviewer type: `human`, `agent_visual_review`, or `deterministic_probe`
- reason
- forbidden-role flags checked for the beat

Render-facing selections must fail closed when:

- visual confirmation is missing
- status is not `accepted`
- candidate source is token-only
- newcomer/basic visual is marked supervisor/director/portrait as primary
- supervisor source speech lacks video + audio/speech evidence

## Suggested Artifacts

Names may vary, but the behavior must be present:

- `visual_selection_candidates.json`
- `visual_selection_review.json`
- `visual_selection_gate.json`
- `visual_selection_contact_sheet.jpg` or referenced frame evidence

## Red-First Requirements

Before implementation, add failing tests or smoke evidence proving:

- A token-only `newcomer_training_start` selection currently passes or lacks a
  blocker.
- A token-only `basic_training` selection currently passes or lacks a blocker.
- A supervisor source-speech selection without audio/speech evidence currently
  passes or lacks a blocker.
- Accepted selections with visual evidence pass.
- Rejected / needs_repick selections block.

Use the V2 failure pattern as a fixture:

- `newcomer_training_start` from `工安早會/IMG_2120.JPG`
- `basic_training` from `工安早會/IMG_2124.JPG`
- `supervisor_source_speech` from `主任勉勵/IMG_2141.MOV`

The tests do not need to inspect the real images visually. It is enough to prove
the contract requires explicit visual confirmation evidence before render.

## Real-Run Smoke

Run a read-only smoke against:

`.tmp\graduation_v2_creative_repair_20260707-122858\run`

Expected outcome:

- Current V2 token/path-derived newcomer/basic selections should not be treated
  as final accepted selections unless a new visual review artifact explicitly
  accepts them.
- The smoke should produce a visual-selection gate report showing which beats
  are blocked or need review.
- Do not modify the V2 run.

## Acceptance Commands

Run and report exit codes:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_graduation_film_blueprint_catalog
C:\Users\user\miniconda3\python.exe -m unittest tests.test_graduation_film_blueprint_catalog tests.test_delivery_gate tests.test_pipeline_home
C:\Users\user\miniconda3\python.exe <visual-selection-tool> --run ".tmp\graduation_v2_creative_repair_20260707-122858\run" --out-dir "<fresh-out>" --json
C:\Users\user\miniconda3\python.exe -c "import json; json.load(open('docs/branch-contract-registry.json', encoding='utf-8')); print('json ok')"
git diff --check
```

Also run a final artifact check that prints:

- fresh output root
- V2 run read-only check
- sensitive beat statuses
- blocked token-only selections
- accepted visual-evidence selections in test fixtures
- UTF-8/no-corruption result

## Stop-Loss

Stop and report if:

- Implementing this requires render/gate/provider changes.
- The only way to pass is to fake visual review.
- The smoke would need to modify existing V2 run artifacts.
- Chinese paths or artifact text cannot be read/written as explicit UTF-8.

## Delegated Decisions

- Exact helper/tool names.
- Exact visual-selection schema beyond required fields.
- Whether to integrate the gate into graduation helper outputs now or expose a
  separate validation tool first.
- Whether deterministic probes, agent visual review, or human review are
  represented as separate reviewer types, as long as token-only never counts as
  accepted.
- Exact wording of docs updates.

## Final Report Requirements

Write:

`docs/construction-guides/work-orders/2026-07-07-visual-selection-gate-token-candidates-report.md`

The report must include:

- Files changed
- Red-first evidence
- Implemented behavior
- Real V2 smoke output root and status
- Acceptance command exit codes
- Confirmation that no render/provider/music/VoxCPM changes were made
- Confirmation that existing V2 run was not modified
- Deviations / blockers
- Next recommended work grounded in this gate

