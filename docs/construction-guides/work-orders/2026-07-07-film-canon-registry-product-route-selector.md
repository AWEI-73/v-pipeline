# Work Order: Film Canon Registry Product Route Selector

Date: 2026-07-07

## Goal

Promote the current single graduation-film helper into a reusable Film Canon
Registry and Product Route Selector.

The visible capability to prove: the pipeline can select a product film type and
produce canon / blueprint / story shell / catalog map dry-run artifacts for more
than one film family, without hard-coding graduation-training logic as the only
route.

This should enable future products such as a child's daily memory film while
preserving the graduation training film route already started.

Do not render a video in this round.

## Current Context

The working tree already contains the graduation route scaffold and real-source
dry-run work:

- `video_pipeline_core/graduation_film_blueprint_catalog.py`
- `tools/graduation_film_blueprint_catalog.py`
- `tests/test_graduation_film_blueprint_catalog.py`

Build on this work. Do not replace it with an unrelated second implementation.

## Owner Zone

- New or updated film canon registry / product route selector module under
  `video_pipeline_core/`
- New or updated CLI under `tools/`
- New or updated tests under `tests/`
- `docs/video-pipeline-operating-map.md`
- `docs/pipeline-decision-tree.md`
- `docs/branch-contract-registry.md`
- `docs/branch-contract-registry.json`
- `docs/construction-guides/work-orders/2026-07-07-film-canon-registry-product-route-selector-report.md`

## Forbidden Zone

- Render pipeline implementation
- Delivery gate semantics
- VoxCPM / voiceover provider implementation
- Soundtrack provider/download implementation
- Existing approved delivery package under `deliveries/`
- Existing `.tmp/` runs
- `Downloads/` writes
- `.env`
- `.venv_voxcpm/`
- `reference repo/`
- Git commit, branch, push, or PR operations

## Required Interpreter

Use this interpreter for every Python command:

`C:\Users\user\miniconda3\python.exe`

Do not use bare `python`, `pytest`, or another environment.

## Required Canon Registry

Add a registry that can list and select film types.

Minimum supported film types:

1. `graduation_training_film`
2. `daily_kids_memory_film`

The selector must accept a film type and produce dry-run artifacts using that
canon.

### graduation_training_film

Must preserve the current route:

- opening story
- training MV catalog as longest body section
- supervisor speech
- teacher/class introduction
- closing story
- training modules: basic, advanced, certification, physical activity,
  encouragement, daily life optional, special activity

### daily_kids_memory_film

Add fixture-only support for this new product family.

Canonical sections:

- `opening_memory_hook`
- `daily_life_montage`
- `milestone_moments`
- `cute_funny_moments`
- `family_interaction`
- `closing_memory_note`

Catalog modules:

- `eating`
- `playing`
- `learning`
- `family`
- `outdoor`
- `school`
- `birthday_or_special_event`
- `random_cute_optional`

Rules:

- Warm or light music is preferred.
- Source laughter / child speech may be preserved if intelligible.
- Narration is optional.
- Date/place/title captions are useful; full subtitles are not always required.
- Human/family review remains required before external sharing.

## Required CLI Behavior

The CLI must support:

- listing supported film types
- running a dry-run for a selected `--film-type`
- writing the same category of artifacts as the current graduation dry-run, with
  film-type-specific names or common names that include `film_type`

Example shape:

```powershell
C:\Users\user\miniconda3\python.exe tools\film_canon_route.py --list --json
C:\Users\user\miniconda3\python.exe tools\film_canon_route.py --film-type graduation_training_film --source-root "<fixture>" --out-dir "<out>" --json
C:\Users\user\miniconda3\python.exe tools\film_canon_route.py --film-type daily_kids_memory_film --source-root "<fixture>" --out-dir "<out>" --json
```

Exact tool name is delegated, but the report must document it.

## Required Dry-Run Outputs

For each supported film type in fixture smoke, write:

- canon artifact
- blueprint artifact
- story shell artifact
- catalog map artifact
- review packet markdown
- review packet JSON

For `graduation_training_film`, preserve compatibility with existing
graduation artifact names or provide compatibility aliases so existing tests
continue to pass.

For `daily_kids_memory_film`, no real family media is required. Use fixture file
names only.

No dry-run may write:

- `final.mp4`
- `story_human_review_decision.json`

## Red-First Requirements

Before implementation, add failing tests proving:

- A film canon registry/list does not exist yet.
- `graduation_training_film` can be selected through the registry and still
  produces graduation sections/modules.
- `daily_kids_memory_film` can be selected and produces its own sections/modules.
- Unknown film type fails closed.
- Both dry-runs produce review packets and do not render or write human
  approval.
- UTF-8 output has no replacement characters or question-mark placeholder runs.

## Acceptance Commands

Run and report exit codes:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_graduation_film_blueprint_catalog
C:\Users\user\miniconda3\python.exe -m unittest tests.test_graduation_film_blueprint_catalog tests.test_soundtrack_arranger tests.test_pipeline_home
C:\Users\user\miniconda3\python.exe <selector-tool> --list --json
C:\Users\user\miniconda3\python.exe <selector-tool> --film-type graduation_training_film --source-root "<fixture>" --out-dir "<out-root>\graduation" --json
C:\Users\user\miniconda3\python.exe <selector-tool> --film-type daily_kids_memory_film --source-root "<fixture>" --out-dir "<out-root>\daily_kids" --json
C:\Users\user\miniconda3\python.exe -c "import json; json.load(open('docs/branch-contract-registry.json', encoding='utf-8')); print('json ok')"
git diff --check
```

Also run final checks that print:

- supported film types
- output roots
- per-film canon sections
- per-film catalog modules
- review packet paths
- `final.mp4` exists false
- `story_human_review_decision.json` exists false
- UTF-8/no-corruption result

## Stop-Loss

Stop and report without broad patching if:

- Supporting multiple film types requires render/gate/provider changes.
- The implementation breaks the existing graduation tests.
- The registry can only work by hard-coding the previous approved run.
- The new daily kids route requires real private family material.
- Chinese output cannot be produced without mojibake.

## Delegated Decisions

- Exact module/tool name.
- Whether registry data is code, JSON, or a hybrid.
- Exact artifact names, as long as compatibility is preserved for graduation
  outputs.
- Exact fixture file names for daily kids route.
- Exact review packet layout.

## Final Report Requirements

Write:

`docs/construction-guides/work-orders/2026-07-07-film-canon-registry-product-route-selector-report.md`

The report must include:

- Files changed
- Red-first evidence
- Registry design
- Supported film types
- Graduation smoke output summary
- Daily kids fixture smoke output summary
- CLI examples
- Confirmation that no render or human approval was written
- UTF-8/no-corruption result
- Commands and exit codes
- Deviations, if any
- Stop-loss reason, if stopped
- Next recommended work grounded only in this round

