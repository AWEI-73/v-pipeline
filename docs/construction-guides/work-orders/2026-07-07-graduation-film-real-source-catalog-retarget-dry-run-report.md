# Graduation Film Real-Source Catalog Retarget Dry Run Report

Date: 2026-07-07

## Files Changed

- `video_pipeline_core/graduation_film_blueprint_catalog.py`
- `tools/graduation_film_blueprint_catalog.py`
- `tests/test_graduation_film_blueprint_catalog.py`
- `docs/video-pipeline-operating-map.md`
- `docs/pipeline-decision-tree.md`
- `docs/branch-contract-registry.md`
- `docs/branch-contract-registry.json`
- `docs/construction-guides/work-orders/2026-07-07-graduation-film-real-source-catalog-retarget-dry-run-report.md`

## Red-First Evidence

- Command: `C:\Users\user\miniconda3\python.exe -m unittest tests.test_graduation_film_blueprint_catalog`
- Exit code: `1`
- Result: failed with `ImportError: cannot import name 'build_graduation_film_real_source_dry_run'`.

## Real Source Preflight

- Source root: `C:\Users\user\Downloads\微電影素材\_整理後`
- Exists: `true`
- Is directory: `true`
- File count: `306`
- Media count: `198`
- Access mode: read-only; no writes to Downloads.

## Output Root

- Output root: `.tmp\graduation_real_source_catalog_retarget_20260707-003240`
- Dry-run folder: `.tmp\graduation_real_source_catalog_retarget_20260707-003240\real_source_dry_run`

## Module Counts And Representative Paths

- `basic_training`: 49
  - `66期學長音樂檔/2基本.mp4`
  - `工安早會/IMG_2120.JPG`
  - `工安早會/IMG_2124.JPG`
- `advanced_training`: 7
  - `換桿/IMG_8346.MOV`
  - `換桿/IMG_8349.MOV`
  - `換桿/IMG_8351.JPG`
- `certification`: 0
- `physical_activity`: 13
  - `運動會/66期配四班隊呼.mp4`
  - `運動會/IMG_7594.JPG`
  - `運動會/IMG_7605.JPG`
- `encouragement_activity`: 0
- `daily_life_optional`: 23
  - `班級日常生活/IMG_0762.JPG`
  - `班級日常生活/IMG_1810.JPG`
  - `班級日常生活/IMG_2665.JPG`
- `supervisor_speech`: 20
  - `66期學長音樂檔/5主任的話.mp4`
  - `主任勉勵/IMG_2118.MOV`
  - `主任勉勵/IMG_2119.MOV`
- `teacher_class_intro`: 27
  - `各班團體照&導師/8/IMG_0369.JPG`
  - `各班團體照&導師/8/IMG_9668.JPG`
  - `各班團體照&導師/8/IMG_9687.JPG`
- `closing_story`: 2
  - `67期結訓影片-終.mp4`
  - `感謝導師/67期養成班0326-3.mp4`
- `special_activity`: 81
  - `0325素材/隊呼/66期配五班隊呼.mp4`
  - `0325素材/隊呼/66期配四班隊呼.mp4`
  - `66期學長空拍影片/MAX_0169.MP4`

## A/B Story Shell Summary

Story A:

- Title: `結訓影片故事版本 A`
- Theme: `從新人到現場人員`
- Hook: `從新人第一次走進現場，到能承擔任務的現場人員`
- Payoff: `把訓練中的每一次練習，落到未來現場的責任感`

Story B:

- Title: `結訓影片故事版本 B`
- Theme: `5.5 個月，把安全變成反射`
- Hook: `5.5 個月的重複練習，是為了讓安全成為第一個反應`
- Payoff: `結訓不是終點，是把安全變成反射的開始`

## Retarget Diff Summary

- Canon unchanged: `true`
- Catalog reuse: `mostly_reusable`
- Changed sections: `opening_story`, `closing_story`
- Human approval reusable: `false`
- Future artifacts to regenerate:
  - `graduation_film_blueprint_A.json`
  - `graduation_film_blueprint_B.json`
  - `story_shell_A.json`
  - `story_shell_B.json`
  - `story_to_material_map.json`
  - `narration_manifest.json`
  - `subtitles.srt`
  - `review_packet`

## Production Readiness Plan Summary

- `ready_for_render`: `false`
- `requires_human_review`: `true`
- Blocking reviews before production:
  - confirm agent-filled training catalog assignments
  - choose story shell A or B or retarget
  - confirm supervisor speech intelligibility
  - confirm teacher/class intro readability
  - confirm opening/closing design direction
- Next production handoffs:
  - `material_map_review`
  - `opener_closer_design_handoff`
  - `audio_subtitle_review_requirements`

## Opener / Closer Handoff Summary

- Sections: `opening_story`, `closing_story`
- Rule: opening and closing are story shell sections, not plain white cards.
- Rule: story shell can retarget by theme, but should not rewrite the training catalog core.
- Human choice required: `true`

## Audio / Subtitle Review Requirements Summary

- Requires supervisor speech subtitles: `true`
- Requires teacher/class intro readability: `true`
- Requires source speech intelligibility review: `true`
- Music policy: hot-blooded music belongs mainly in `training_mv_catalog`.

## No Render / No Approval

- `final.mp4` exists: `false`
- `story_human_review_decision.json` exists: `false`
- No render command was run.
- No human approval artifact was written.

## UTF-8 / No-Corruption

- Explicit check result: `utf8_no_corruption=true`
- Bad text artifacts: `[]`
- Checked generated `.json` and `.md` artifacts for UTF-8 decode, replacement characters, and `????` placeholder runs.

## Commands

- `C:\Users\user\miniconda3\python.exe -m unittest tests.test_graduation_film_blueprint_catalog`
  - Exit code: `1`
  - Purpose: red-first evidence.
- `C:\Users\user\miniconda3\python.exe -m unittest tests.test_graduation_film_blueprint_catalog`
  - Exit code: `0`
  - Result: `Ran 7 tests ... OK`
- `C:\Users\user\miniconda3\python.exe -m unittest tests.test_graduation_film_blueprint_catalog tests.test_soundtrack_arranger tests.test_pipeline_home`
  - Exit code: `0`
  - Result: `Ran 102 tests ... OK`
- `C:\Users\user\miniconda3\python.exe -c "from pathlib import Path; p=Path('C:/Users/user/Downloads/\u5fae\u96fb\u5f71\u7d20\u6750/_\u6574\u7406\u5f8c'); ..."`
  - Exit code: `0`
  - Result: `exists=True`, `is_dir=True`, `file_count=306`, `media_count=198`
- `C:\Users\user\miniconda3\python.exe tools\graduation_film_blueprint_catalog.py --source-root "C:\Users\user\Downloads\微電影素材\_整理後" --out-dir ".tmp\graduation_real_source_catalog_retarget_20260707-003240\real_source_dry_run" --json`
  - Exit code: `0`
  - Result: wrote all required real-source dry-run artifacts.
- `C:\Users\user\miniconda3\python.exe -c "... final explicit checks ..."`
  - Exit code: `0`
  - Result: printed output root, preflight, module counts, representative paths, A/B shells, retarget summary, no-render/no-approval, and UTF-8 result.
- `C:\Users\user\miniconda3\python.exe -c "import json; json.load(open('docs/branch-contract-registry.json', encoding='utf-8')); print('json ok')"`
  - Exit code: `0`
  - Result: `json ok`
- `git diff --check`
  - Exit code: `0`
  - Result: no whitespace errors; Git printed CRLF warnings for modified tracked docs.

## Deviations

- None.

## Stop-Loss

- Not stopped.
- No render, delivery gate semantics, VoxCPM, soundtrack provider, deliveries, or existing `.tmp` run changes were required.
- Downloads was read-only.

## Next Recommended Work

Hold a human product review on `graduation_real_source_review_packet.md`: confirm the A/B story shell direction, correct the agent-filled catalog assignments for modules with zero or weak coverage, and then produce a reviewed story-to-material map before any render attempt.
