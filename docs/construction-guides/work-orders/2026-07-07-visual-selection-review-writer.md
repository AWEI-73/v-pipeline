# Work Order: Visual Selection Review Writer

Date: 2026-07-07

## Goal

Add an operator-facing writer for `visual_selection_review.json` so graduation
production can turn rough token/path candidates into explicit visual review
decisions before render.

This continues the visual-selection gate work from:

- `docs/construction-guides/work-orders/2026-07-07-visual-selection-gate-token-candidates.md`
- `docs/construction-guides/work-orders/2026-07-07-visual-selection-gate-token-candidates-report.md`

Current state:

```text
token/path catalog -> visual_selection_gate blocks token-only candidates
```

Desired state:

```text
token/path catalog
  -> visual_selection_candidates.json
  -> operator/agent visual review writer
  -> visual_selection_review.json
  -> visual_selection_gate pass/block
```

The review writer must not claim final story approval or legal/music approval.
It only records visual-selection decisions for sensitive render-facing beats.

## Owner Zone

- `video_pipeline_core/visual_selection_review_decision.py`
- `tools/write_visual_selection_review.py`
- `tests/test_visual_selection_review_decision.py`
- `tests/test_graduation_film_blueprint_catalog.py` if needed for integration
- `docs/video-pipeline-operating-map.md`
- `docs/pipeline-decision-tree.md`
- `docs/branch-contract-registry.md`
- `docs/branch-contract-registry.json`
- `docs/construction-guides/work-orders/2026-07-07-visual-selection-review-writer-report.md`

## Forbidden Zone

- `video_pipeline_core/delivery_gate.py`
- `video_pipeline_core/material_first_render.py`
- `video_pipeline_core/material_first_review_promotion.py`
- `video_pipeline_core/voiceover_provider.py`
- `video_pipeline_core/soundtrack_arranger.py`
- Existing `.tmp/` run directories
- `Downloads/`
- `deliveries/`
- `.env*`
- `.venv*`
- `reference repo/`
- Git branch, commit, push, or PR operations

## Required Environment

Use the pinned interpreter:

```powershell
C:\Users\user\miniconda3\python.exe
```

Do not use bare `python` or `pytest`.

## Required Behavior

1. Add a writer CLI for `visual_selection_review.json`.
2. The CLI must read candidates from one of:
   - `--candidates PATH`
   - `--run RUN_DIR`, using the existing visual-selection candidate builder
3. The CLI must write `visual_selection_review.json` to `--out-dir` or to
   `--run` only when explicitly requested by a flag such as `--write-to-run`.
4. Default smoke mode must write to a fresh output folder, not mutate an
   existing run.
5. Supported decisions per sensitive beat:
   - `accepted`
   - `rejected`
   - `needs_repick`
6. `accepted` must require all of:
   - reviewer type is `human`, `agent_visual_review`, or `deterministic_probe`
   - non-token `candidate_source`, such as `agent_visual_review`
   - visual evidence reference: representative frame, contact sheet, or frame
     evidence ref
   - forbidden-role flags checked
   - reason/note
7. `newcomer_training_start` and `basic_training` accepted decisions must
   fail closed if forbidden-role flags mark supervisor, director, or portrait
   as the primary visual.
8. `supervisor_source_speech` accepted decision must require video, audio, and
   speech evidence.
9. `rejected` and `needs_repick` must require a reason and must remain gate
   blocking.
10. Non-human or missing reviewer decisions must fail closed and write no
    accepted review artifact.
11. The CLI must evaluate the written review with the existing
    `evaluate_visual_selection_gate` contract and print/write a summary.
12. Generated JSON must be explicit UTF-8 and must not corrupt Chinese paths.

## Red-First Verification

Before implementation, add focused failing tests proving the missing writer
behavior. At minimum cover:

- writer CLI/module does not exist yet
- accepted review for a sensitive beat cannot be generated without evidence
- accepted newcomer/basic with supervisor/director/portrait primary flag fails
- supervisor source speech accepted without audio/speech evidence fails
- rejected and `needs_repick` write review items but gate remains blocked
- accepted review with valid visual evidence passes the existing visual gate

Use V2-style paths in fixtures:

- `newcomer_training_start`: `工安早會/IMG_2120.JPG`
- `basic_training`: `工安早會/IMG_2124.JPG`
- `supervisor_source_speech`: `主任勉勵/IMG_2141.MOV`

Tests do not need to inspect real images visually. They must prove the artifact
contract requires explicit visual-review evidence before render-facing
acceptance.

## Required Smoke

Run a fresh smoke against the existing V2 run in read-only mode:

```text
.tmp\graduation_v2_creative_repair_20260707-122858\run
```

The smoke must:

- build or read visual-selection candidates from the V2 run
- write review output only under a fresh `.tmp\visual_selection_review_writer_*`
  output root
- create at least three fixture review cases:
  - accepted valid visual-evidence fixture
  - rejected fixture
  - needs_repick fixture
- prove the source V2 run is unchanged
- prove UTF-8/no-corruption for generated JSON

Do not modify V2 in place.

## Acceptance Commands

Expected exit code is `0` unless stated otherwise.

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_visual_selection_review_decision
C:\Users\user\miniconda3\python.exe -m unittest tests.test_visual_selection_review_decision tests.test_graduation_film_blueprint_catalog
C:\Users\user\miniconda3\python.exe -m unittest tests.test_visual_selection_review_decision tests.test_graduation_film_blueprint_catalog tests.test_delivery_gate tests.test_pipeline_home
C:\Users\user\miniconda3\python.exe tools\write_visual_selection_review.py --help
C:\Users\user\miniconda3\python.exe tools\write_visual_selection_review.py --run ".tmp\graduation_v2_creative_repair_20260707-122858\run" --out-dir "<fresh-out>" --fixture accepted-valid --json
C:\Users\user\miniconda3\python.exe tools\write_visual_selection_review.py --run ".tmp\graduation_v2_creative_repair_20260707-122858\run" --out-dir "<fresh-out>" --fixture rejected --json
C:\Users\user\miniconda3\python.exe tools\write_visual_selection_review.py --run ".tmp\graduation_v2_creative_repair_20260707-122858\run" --out-dir "<fresh-out>" --fixture needs-repick --json
C:\Users\user\miniconda3\python.exe -c "import json; json.load(open('docs/branch-contract-registry.json', encoding='utf-8')); print('json ok')"
git diff --check
```

Add a final artifact check command that prints:

- fresh output root
- created `visual_selection_review.json` paths
- accepted/rejected/needs_repick gate results
- V2 run unchanged true/false
- UTF-8/no-corruption true/false

## Stop-Loss Limits

Stop and report instead of broadening scope if:

- passing requires changing delivery gate semantics
- passing requires changing render, VoxCPM, or soundtrack behavior
- the only way to pass is to fake visual evidence
- the smoke requires modifying the existing V2 run
- Chinese paths cannot be written/read with explicit UTF-8

## Delegated Decisions

- Exact module/helper function names.
- Exact CLI argument layout, as long as required modes are present.
- Whether fixture modes are implemented as named presets or small JSON inputs.
- Exact summary JSON shape, as long as it includes gate pass/block truth.
- Whether docs describe the writer under film-canon route or visual-selection
  route, as long as the registry stays parseable.

## Report Requirements

Write:

```text
docs/construction-guides/work-orders/2026-07-07-visual-selection-review-writer-report.md
```

Include:

- changed files
- red-first command and failure
- acceptance commands with exit codes
- fresh smoke output root
- created review artifact paths
- accepted/rejected/needs_repick results
- V2 read-only unchanged proof
- UTF-8/no-corruption result
- deviations and blockers
- next recommended work

