# Work Order: Graduation Film Real-Source Catalog Retarget Dry Run

Date: 2026-07-07

## Goal

Advance the Graduation Film Product Route from fixture scaffold to a usable
real-source dry-run.

The visible capability to prove: using the existing graduation-film canon /
blueprint helper and the user's real source folder read-only, the pipeline can
produce a module-aware training catalog, two alternate story shells, a retarget
diff, and a production readiness packet that a human can use to decide the next
production run.

Do not render a new film in this round.

## Background

The prior scaffold round created the first helper and fixture dry-run:

- `video_pipeline_core/graduation_film_blueprint_catalog.py`
- `tools/graduation_film_blueprint_catalog.py`
- `tests/test_graduation_film_blueprint_catalog.py`

It was useful but too shallow: it did not scan the real source folder, did not
map the user's actual course folder names, did not produce an A/B story retarget
diff, and left mojibake in the report payoff text. This round must deepen that
route instead of starting a second implementation.

Read first:

- `docs/construction-guides/happy-paths/real-material-scripted-approved-happy-path.md`
- `docs/construction-guides/work-orders/2026-07-06-graduation-film-canon-blueprint-catalog-dry-run.md`
- `docs/construction-guides/work-orders/2026-07-06-graduation-film-canon-blueprint-catalog-dry-run-report.md`

## Owner Zone

- `video_pipeline_core/graduation_film_blueprint_catalog.py`
- `tools/graduation_film_blueprint_catalog.py`
- `tests/test_graduation_film_blueprint_catalog.py`
- `docs/video-pipeline-operating-map.md`
- `docs/pipeline-decision-tree.md`
- `docs/branch-contract-registry.md`
- `docs/branch-contract-registry.json`
- `docs/construction-guides/work-orders/2026-07-07-graduation-film-real-source-catalog-retarget-dry-run-report.md`

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

## Real Source Root

Use this folder read-only:

`C:\Users\user\Downloads\微電影素材\_整理後`

You may read directory names, file names, extensions, sizes, and lightweight
metadata. Do not write into it. Do not copy large media into repo. Do not render.

## Required Product Heuristics

The catalog route must understand the user's graduation film model:

- The long body section is `training_mv_catalog`.
- Opening and closing are story-shell sections that can be retargeted.
- Training modules should be inferred from folder/file signals and marked as
  agent-filled until reviewed.

At minimum, support these module signals:

- `basic_training`: foundation, basic, drill, 基礎, 基本, 工安, 體感, 拖拉電纜
- `advanced_training`: advanced, high-risk, 進階, 高階, 換桿, 活線, 登高
- `certification`: certification, test, exam, license, 檢定, 測驗, 證照, 認證
- `physical_activity`: physical, fitness, run, rope, 體能, 運動
- `encouragement_activity`: encouragement, morale, 勵進, 鼓勵, 士氣
- `daily_life_optional`: daily, life, lunch, dorm, 生活, 日常, 早餐, 午餐, 宿舍
- `supervisor_speech`: 主任, 主管, 勉勵, 致詞
- `teacher_class_intro`: 老師, 導師, 教師, 班級, 各班
- `closing_story`: 感謝, 結尾, 畢業, 結訓
- `special_activity`: fallback for unmatched usable material

Every assignment inferred by these rules must record:

- source-relative path
- module id
- signal(s) matched
- confidence or match reason
- `agent_filled=true`
- `needs_human_confirmation=true`

## Required Dry-Run Outputs

Create a fresh output root under `.tmp/` and write:

- `graduation_film_canon.json`
- `graduation_film_blueprint_A.json`
- `graduation_film_blueprint_B.json`
- `story_shell_A.json`
- `story_shell_B.json`
- `training_catalog_map.real_source.json`
- `story_retarget_diff_A_to_B.json`
- `production_readiness_plan.json`
- `opener_closer_design_handoff.json`
- `audio_subtitle_review_requirements.json`
- `graduation_real_source_review_packet.md`
- `graduation_real_source_review_packet.json`

Story shells:

- A: `從新人到現場人員`
- B: `5.5 個月，把安全變成反射`

The retarget diff must show:

- canon unchanged
- catalog map reusable or mostly reusable
- opening/closing story shell changed
- narration/theme text changed
- module order or emphasis changes, if any
- human approval cannot be reused
- which future artifacts would need regeneration

## Red-First Requirements

Before implementation, add failing tests proving:

- Real-source-style folder names such as `工安體感`, `拖拉電纜`, `換桿`, `活線作業`,
  `主任勉勵`, and `感謝導師` are not mapped deeply enough yet.
- A/B story shell retarget diff is missing or incomplete.
- Product review packet must contain module counts, representative source
  paths, retarget summary, and next production handoffs.
- Dry-run must not write `final.mp4` or `story_human_review_decision.json`.
- UTF-8 output must not contain replacement characters or question-mark
  placeholder runs.

## Acceptance Commands

Run and report exit codes:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_graduation_film_blueprint_catalog
C:\Users\user\miniconda3\python.exe -m unittest tests.test_graduation_film_blueprint_catalog tests.test_soundtrack_arranger tests.test_pipeline_home
C:\Users\user\miniconda3\python.exe tools\graduation_film_blueprint_catalog.py --source-root "C:\Users\user\Downloads\微電影素材\_整理後" --out-dir "<out-root>\real_source_dry_run" --json
C:\Users\user\miniconda3\python.exe -c "import json; json.load(open('docs/branch-contract-registry.json', encoding='utf-8')); print('json ok')"
git diff --check
```

Also run final explicit checks that print:

- output root
- source preflight exists/is_dir/file_count/media_count
- module counts for all graduation modules
- top representative source-relative paths per module
- A/B story titles, hooks, and payoffs
- retarget changed sections
- reuse/regenerate summary
- `final.mp4` exists false
- `story_human_review_decision.json` exists false
- UTF-8/no-corruption result

## Stop-Loss

Stop and report without broad patching if:

- Real source folder is missing or unreadable.
- The route needs render, gate, VoxCPM, soundtrack provider, or delivery package
  changes.
- The implementation writes into Downloads, deliveries, or existing `.tmp` runs.
- The only way to pass is hard-coding a single previous approved run.
- Chinese output cannot be produced without mojibake.

## Delegated Decisions

- Exact schema fields beyond the required content.
- Exact module scoring values.
- Whether unmatched files go to `special_activity` or an `unclassified` section,
  as long as the review packet exposes the count and examples.
- Exact review packet layout.
- Whether to include lightweight file sizes/extensions in the catalog map.

## Final Report Requirements

Write:

`docs/construction-guides/work-orders/2026-07-07-graduation-film-real-source-catalog-retarget-dry-run-report.md`

The report must include:

- Files changed
- Red-first evidence
- Real source preflight
- Output root
- Module counts and representative source-relative paths
- A/B story shell summary
- Retarget diff summary
- Production readiness plan summary
- Opener/closer handoff summary
- Audio/subtitle review requirements summary
- Confirmation that no render or human approval was written
- UTF-8/no-corruption result
- Commands and exit codes
- Deviations, if any
- Stop-loss reason, if stopped
- Next recommended work grounded only in this round

