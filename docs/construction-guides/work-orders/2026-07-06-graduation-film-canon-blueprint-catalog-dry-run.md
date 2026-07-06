# Work Order: Graduation Film Canon Blueprint Catalog Dry Run

Date: 2026-07-06

## Goal

Start the upper product route for graduation training films by adding a
reviewable dry-run that produces a film canon, blueprint, story shell, and
training catalog map before render.

The visible capability to prove: given the user's graduation-film direction and
real or fixture material metadata, the pipeline can describe what kind of film
it is making, how the story shell wraps the long training MV catalog, and how
material should be organized for later production or story retargeting.

Do not render a new film in this round.

## Background

The existing real-material scripted approved happy path proved the technical
chain:

`source material -> final.mp4 -> delivery gate -> human approval -> package`

It also exposed product-quality gaps: weak opening/closing, unclear theme,
audio/subtitle intelligibility issues, vertical footage treatment, and lack of a
structured training MV catalog.

Read:

- `docs/construction-guides/happy-paths/real-material-scripted-approved-happy-path.md`

## Owner Zone

- New or updated graduation-film canon/blueprint/catalog helper under `tools/`
  and/or `video_pipeline_core/`
- Focused tests under `tests/`
- `docs/video-pipeline-operating-map.md`
- `docs/pipeline-decision-tree.md`
- `docs/branch-contract-registry.md`
- `docs/branch-contract-registry.json`
- `docs/construction-guides/work-orders/2026-07-06-graduation-film-canon-blueprint-catalog-dry-run-report.md`

## Forbidden Zone

- Render pipeline implementation
- VoxCPM / voiceover provider implementation
- Soundtrack provider/download implementation
- Delivery gate semantics
- Existing approved delivery package under `deliveries/`
- Existing `.tmp/` runs
- `Downloads/`
- `.env`
- `.venv_voxcpm/`
- `reference repo/`
- Git commit, branch, push, or PR operations

## Required Interpreter

Use this interpreter for every Python command:

`C:\Users\user\miniconda3\python.exe`

Do not use bare `python`, `pytest`, or another environment.

## Required Product Structure

The dry-run must encode this graduation-film canon:

1. `opening_story`
2. `training_mv_catalog`
3. `supervisor_speech`
4. `teacher_class_intro`
5. `closing_story`

The training MV catalog is the longest body section and must support these
modules:

- `basic_training`
- `advanced_training`
- `certification`
- `physical_activity`
- `encouragement_activity`
- `daily_life_optional`
- extensible `special_activity`

Rules:

- Hot-blooded music belongs mainly in `training_mv_catalog`.
- Opening and closing are story/design sections, not plain white cards.
- Supervisor speech preserves source speech only when useful and must require
  subtitle/intelligibility evidence.
- Teacher/class introduction may use effects and intro music, but must remain
  readable.
- Story changes should primarily retarget opening story, closing story,
  transition logic, and module ordering/emphasis; the training catalog map should
  be reusable where material still fits.

## Required Artifacts

Produce a dry-run output folder under `.tmp/` containing:

- `graduation_film_canon.json`
- `graduation_film_blueprint.json`
- `story_shell.json`
- `training_catalog_map.json`
- `story_retargeting_notes.json`
- `graduation_dry_run_review_packet.md`
- `graduation_dry_run_review_packet.json`

The artifacts must be UTF-8, with no replacement characters and no question-mark
placeholder runs.

## Red-First Requirements

Before implementation, add focused failing tests proving:

- The graduation film canon artifact does not yet exist or cannot be produced.
- The canon requires the five fixed sections.
- The training MV catalog requires the listed module families.
- The story shell can change the theme without changing the canon.
- The catalog map marks agent-filled material/category assignments as requiring
  human confirmation.
- The dry-run does not render `final.mp4` and does not write
  `story_human_review_decision.json`.

## Dry-Run Inputs

Use a fixture source tree by default so tests do not depend on Downloads.

Optionally run one read-only smoke against:

`C:\Users\user\Downloads\微電影素材\_整理後`

If using the real source folder, do not write into it. The real-source smoke may
stop at inventory/category evidence if media probing would be too expensive.

## Acceptance Commands

Run and report exit codes:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_graduation_film_blueprint_catalog
C:\Users\user\miniconda3\python.exe -m unittest tests.test_graduation_film_blueprint_catalog tests.test_soundtrack_arranger tests.test_pipeline_home
C:\Users\user\miniconda3\python.exe -c "import json; json.load(open('docs/branch-contract-registry.json', encoding='utf-8')); print('json ok')"
git diff --check
```

Also run a fresh `.tmp/` smoke that prints:

- output root
- canon sections
- blueprint theme
- story shell title/hook/payoff
- training catalog module counts
- agent-filled / needs-human-confirmation counts
- whether `final.mp4` exists
- whether `story_human_review_decision.json` exists

Expected: no `final.mp4`; no `story_human_review_decision.json`.

## Stop-Loss

Stop and report without broad patching if:

- Implementing this requires changing render, delivery gate semantics, VoxCPM,
  soundtrack provider, or approved delivery package contents.
- The dry-run can only work by hard-coding the previous approved run.
- The catalog map cannot mark uncertain assignments for human review.
- UTF-8 or Chinese text cannot be written cleanly without mojibake.

## Delegated Decisions

- Choose helper/tool names and module placement based on repo conventions.
- Choose exact JSON schemas as long as required fields are present.
- Choose fixture material names and category examples.
- Choose whether real-source smoke is run, as long as fixture acceptance is
  deterministic.
- Choose the exact review packet layout.

## Final Report Requirements

Write:

`docs/construction-guides/work-orders/2026-07-06-graduation-film-canon-blueprint-catalog-dry-run-report.md`

The report must include:

- Files changed
- Red-first evidence
- Implemented artifact schemas
- Fixture dry-run output root
- Optional real-source smoke result, if run
- Canon sections and training module coverage
- Story shell / retargeting behavior
- Confirmation that no render or human approval was written
- UTF-8/no-corruption result
- Commands and exit codes
- Deviations, if any
- Stop-loss reason, if stopped
- Next recommended work grounded only in this round

