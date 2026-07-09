# Visual Selection Gate For Token Candidates Report

Date: 2026-07-07

## Changed Files

- `video_pipeline_core/visual_selection_gate.py`
- `tools/visual_selection_gate.py`
- `video_pipeline_core/graduation_film_blueprint_catalog.py`
- `tests/test_graduation_film_blueprint_catalog.py`
- `docs/video-pipeline-operating-map.md`
- `docs/pipeline-decision-tree.md`
- `docs/branch-contract-registry.md`
- `docs/branch-contract-registry.json`
- `docs/construction-guides/work-orders/2026-07-07-visual-selection-gate-token-candidates-report.md`

## Red-First Evidence

Command:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_graduation_film_blueprint_catalog
```

Exit code: 1

Expected red output:

```text
ModuleNotFoundError: No module named 'video_pipeline_core.visual_selection_gate'
FAILED (errors=1)
```

The red test introduced the missing visual-selection gate contract before any
production helper/CLI code was added.

## Implemented Behavior

- Added `video_pipeline_core.visual_selection_gate.evaluate_visual_selection_gate`.
- Added `tools/visual_selection_gate.py --run ... --out-dir ... --json`.
- Token/folder/path matches are now treated as candidate evidence only.
- Sensitive beats require accepted visual confirmation evidence before
  render-facing acceptance:
  - `newcomer_training_start`
  - `basic_training`
  - `supervisor_source_speech`
  - `teacher_class_intro`
  - `opening_story`
  - `closing_story`
- Rejected and `needs_repick` selections block.
- Newcomer/basic selections block when marked supervisor/director/portrait as
  the primary visual.
- Supervisor source speech blocks unless video, audio, and speech evidence are
  present.
- Graduation catalog token/folder assignments now include
  `visual_selection_role=candidate`, `render_facing_status=candidate_only`, and
  `requires_visual_selection_gate=true`.
- Docs/registry now list the visual-selection gate in the film-canon product
  route contract.

## Fresh Output Root And Smoke

- Fresh output root: `.tmp/visual_selection_gate_token_candidates_20260707-130839`
- V2 run inspected read-only:
  `.tmp/graduation_v2_creative_repair_20260707-122858/run`
- V2 read-only snapshot check: unchanged.
- V2 smoke artifact:
  `.tmp/visual_selection_gate_token_candidates_20260707-130839/v2_smoke/visual_selection_gate.json`
- V2 smoke result: `pass=false`.
- V2 blocked token-only selections:
  - `newcomer_training_start`
  - `supervisor_source_speech`
- V2 smoke did not mutate the V2 run.

Note: the V2 run's visible story/material map did not expose a
`basic_training` source path. The required `basic_training` V2-pattern fixture
is covered by the red-first/unit tests with `工安早會/IMG_2124.JPG`.

## Accepted Fixture Result

Accepted visual-evidence fixture:

- `newcomer_training_start`: `工安早會/IMG_2120.JPG`
- `basic_training`: `工安早會/IMG_2124.JPG`
- `supervisor_source_speech`: `主任勉勵/IMG_2141.MOV`

Result:

- `accepted_visual_evidence_fixture_pass=true`
- `accepted_visual_evidence_count=3`
- Output:
  `.tmp/visual_selection_gate_token_candidates_20260707-130839/accepted_visual_evidence_fixture_result.json`

## Acceptance Commands

- `C:\Users\user\miniconda3\python.exe -m unittest tests.test_graduation_film_blueprint_catalog` -> exit 0, `Ran 22 tests ... OK`
- `C:\Users\user\miniconda3\python.exe -m unittest tests.test_graduation_film_blueprint_catalog tests.test_delivery_gate tests.test_pipeline_home` -> exit 0, `Ran 167 tests ... OK`
- `C:\Users\user\miniconda3\python.exe tools\visual_selection_gate.py --run ".tmp\graduation_v2_creative_repair_20260707-122858\run" --out-dir ".tmp\visual_selection_gate_token_candidates_20260707-130839\acceptance_cli" --json` -> exit 0, report `pass=false` with token-only blocks.
- `C:\Users\user\miniconda3\python.exe -c "import json; json.load(open('docs/branch-contract-registry.json', encoding='utf-8')); print('json ok')"` -> exit 0, `json ok`
- `git diff --check` -> exit 0. Git emitted LF-to-CRLF working-copy warnings only; no whitespace errors.

## UTF-8 / No-Corruption

Final artifact check:

`.tmp/visual_selection_gate_token_candidates_20260707-130839/final_artifact_check.json`

Result:

- `utf8_no_corruption=true`
- `corrupt_files=[]`

## Deviations / Blockers

- No render implementation, delivery gate semantics, VoxCPM, music
  provider/download logic, Downloads, deliveries, env/venv, reference repo, or
  existing `.tmp` run artifacts were edited.
- The CLI exits 0 when it successfully writes a gate report, even when the
  report itself has `pass=false`. The pass/block truth is in the JSON artifact.
- Existing unrelated untracked work-order/report files remain in the working
  tree and were not reverted.

## Next Recommended Work

Add an operator visual-review writer for `visual_selection_review.json`, so a
human or explicit agent visual review can intentionally accept, reject, or mark
repick for each sensitive render-facing beat before the production worker
renders.
