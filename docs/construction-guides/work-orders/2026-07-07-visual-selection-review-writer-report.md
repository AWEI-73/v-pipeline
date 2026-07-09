# Visual Selection Review Writer Report

Date: 2026-07-07

## Changed Files

- `video_pipeline_core/visual_selection_review_decision.py`
- `tools/write_visual_selection_review.py`
- `tests/test_visual_selection_review_decision.py`
- `docs/video-pipeline-operating-map.md`
- `docs/pipeline-decision-tree.md`
- `docs/branch-contract-registry.md`
- `docs/branch-contract-registry.json`
- `docs/construction-guides/work-orders/2026-07-07-visual-selection-review-writer-report.md`

## Red-First Evidence

Command:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_visual_selection_review_decision
```

Exit code: 1

Expected failure:

```text
ModuleNotFoundError: No module named 'video_pipeline_core.visual_selection_review_decision'
FAILED (errors=1)
```

## Implemented Behavior

- Added `build_visual_selection_review` and `write_visual_selection_review`.
- Added `tools/write_visual_selection_review.py`.
- CLI reads candidates from `--candidates PATH` or `--run RUN_DIR`.
- Default run smoke writes to `--out-dir`; it writes into `--run` only with
  `--write-to-run`.
- Fixture modes support `accepted-valid`, `rejected`, and `needs-repick`.
- Accepted visual review requires reviewer, non-token source, visual evidence,
  forbidden-role flag checks, and reason.
- Accepted newcomer/basic selections fail closed when supervisor/director/
  portrait is marked as primary visual.
- Accepted supervisor source speech requires video, audio, and speech evidence.
- Rejected and `needs_repick` write review items but remain gate-blocking.
- Review artifacts explicitly do not clear story approval or legal/music
  approval.

## Smoke Output

- Fresh smoke output root: `.tmp/visual_selection_review_writer_20260707-145226`
- Read-only source run:
  `.tmp/graduation_v2_creative_repair_20260707-122858/run`
- Final artifact check:
  `.tmp/visual_selection_review_writer_20260707-145226/final_artifact_check.json`
- V2 unchanged proof: `v2_unchanged_against_prior_snapshot=true`
- UTF-8/no-corruption: `true`

Created review artifacts:

- `.tmp/visual_selection_review_writer_20260707-145226/accepted_valid/visual_selection_review.json`
- `.tmp/visual_selection_review_writer_20260707-145226/rejected/visual_selection_review.json`
- `.tmp/visual_selection_review_writer_20260707-145226/needs_repick/visual_selection_review.json`
- `.tmp/visual_selection_review_writer_20260707-145226/acceptance_accepted_valid/visual_selection_review.json`
- `.tmp/visual_selection_review_writer_20260707-145226/acceptance_rejected/visual_selection_review.json`
- `.tmp/visual_selection_review_writer_20260707-145226/acceptance_needs_repick/visual_selection_review.json`

Smoke gate results:

- accepted-valid: `gate_pass=true`, blocking `[]`
- rejected: `gate_pass=false`, blocking `visual_selection_rejected`
- needs-repick: `gate_pass=false`, blocking `visual_selection_needs_repick`

The V2 run exposed two current visual-selection candidates through its
story/material map: `newcomer_training_start` and `supervisor_source_speech`.

## Acceptance Commands

- `C:\Users\user\miniconda3\python.exe -m unittest tests.test_visual_selection_review_decision` -> exit 0, `Ran 6 tests ... OK`
- `C:\Users\user\miniconda3\python.exe -m unittest tests.test_visual_selection_review_decision tests.test_graduation_film_blueprint_catalog` -> exit 0, `Ran 28 tests ... OK`
- `C:\Users\user\miniconda3\python.exe -m unittest tests.test_visual_selection_review_decision tests.test_graduation_film_blueprint_catalog tests.test_delivery_gate tests.test_pipeline_home` -> exit 0, `Ran 173 tests ... OK`
- `C:\Users\user\miniconda3\python.exe tools\write_visual_selection_review.py --help` -> exit 0
- `C:\Users\user\miniconda3\python.exe tools\write_visual_selection_review.py --run ".tmp\graduation_v2_creative_repair_20260707-122858\run" --out-dir ".tmp\visual_selection_review_writer_20260707-145226\acceptance_accepted_valid" --fixture accepted-valid --json` -> exit 0, `gate_pass=true`
- `C:\Users\user\miniconda3\python.exe tools\write_visual_selection_review.py --run ".tmp\graduation_v2_creative_repair_20260707-122858\run" --out-dir ".tmp\visual_selection_review_writer_20260707-145226\acceptance_rejected" --fixture rejected --json` -> exit 0, `gate_pass=false`
- `C:\Users\user\miniconda3\python.exe tools\write_visual_selection_review.py --run ".tmp\graduation_v2_creative_repair_20260707-122858\run" --out-dir ".tmp\visual_selection_review_writer_20260707-145226\acceptance_needs_repick" --fixture needs-repick --json` -> exit 0, `gate_pass=false`
- `C:\Users\user\miniconda3\python.exe -c "import json; json.load(open('docs/branch-contract-registry.json', encoding='utf-8')); print('json ok')"` -> exit 0, `json ok`
- `git diff --check` -> exit 0. Git emitted LF-to-CRLF warnings only; no whitespace errors.

## Deviations / Blockers

- No render, delivery gate semantics, VoxCPM, music provider, Downloads,
  deliveries, env/venv, reference repo, or existing `.tmp` run artifacts were
  modified.
- The CLI fixture mode currently applies one fixture decision style to all
  candidates in the input. This is enough for the required smoke and tests; a
  later operator UX can add per-beat command-line overrides if needed.
- Existing unrelated untracked work-order/report files remain untouched.

## Next Recommended Work

Use `tools/write_visual_selection_review.py` to create an accepted
`visual_selection_review.json` for the V2 run only after a real visual review
has confirmed the sensitive beats. Then rerun `tools/visual_selection_gate.py`
against the run or copied review output before any further render-facing
production work.
