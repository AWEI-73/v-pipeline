# 2026-07-08 Reference Film Teardown Product Standard Report

## Result

Status: completed as reference teardown and product-standard package.

Output root:

```text
.tmp\reference_film_teardown_product_standard_20260708-161322
```

No new film was rendered. No `story_human_review_decision.json` was written. The reference films in Downloads were read-only.

## Red-First Evidence

Command:

```powershell
C:\Users\user\miniconda3\python.exe -c "from pathlib import Path; import sys,json; roots=[Path('.tmp/soul_first_real_material_planning_20260708-060509'),Path('.tmp/shot_level_material_proof_completion_20260708-080727'),Path('.tmp/effect_factory_integration_completion_20260708-154117')]; names=['reference_product_standard.json','reference_structure_timeline.json','gap_against_current_pipeline.json','next_render_rehearsal_spec.json']; ..."
```

Exit code: 1.

Observed:

```text
missing_reference_standard_artifacts 12
```

The prior soul-first, shot-level, and effect-factory packages had no reference-film teardown standard, no structure timeline, no pipeline gap comparison, and no next rehearsal spec aligned to the finished reference.

## Reference Preflight

Primary reference:

```text
C:\Users\user\Downloads\微電影素材\_整理後\67期結訓影片-終.mp4
```

Secondary candidate:

```text
C:\Users\user\Downloads\微電影素材\_整理後\最終版的最終版.mp4
```

Both candidates existed and had matching size, duration, stream layout, and first-16MB SHA-256 hash.

Primary ffprobe summary:

- duration: 564.455 seconds
- size: 605074690 bytes
- video stream: h264, duration 564.433333 seconds
- audio stream: aac, duration 564.455011 seconds

Duplicate relationship recorded:

```text
duration_size_and_first_16mb_hash_match
```

## Sampling And Evidence

Sampling strategy:

- first 60 seconds at 1 fps
- representative middle MV window at 1 fps
- representative speech/intro window at 1 fps
- final 60 seconds at 1 fps
- no full-film extraction

Windows:

- `opener_first_60s`: 60 frames
- `middle_mv_window`: 60 frames
- `speech_intro_window`: 60 frames
- `ending_last_60s`: 60 frames

Contact sheets:

- `contact_sheets\opener_first_60s_contact_sheet.jpg`
- `contact_sheets\middle_mv_window_contact_sheet.jpg`
- `contact_sheets\speech_intro_window_contact_sheet.jpg`
- `contact_sheets\ending_last_60s_contact_sheet.jpg`

## Structure Timeline Summary

`reference_structure_timeline.json` uses representative sampling and confidence-scored section boundaries:

- `s01_opener_title_hook`: 0-45s, confidence medium
- `s02_training_mv_modules`: 45-300s, confidence medium
- `s03_speech_or_formal_remarks`: 300-380s, confidence low
- `s04_teacher_class_intro_activity`: 380-500s, confidence low_to_medium
- `s05_closing_payoff_coda`: 500-564.455s, confidence medium

The low-confidence sections are intentionally marked because this round did not perform transcript-level listening or manual full-film annotation.

## Effect / Subtitle / Music Audit

`reference_effect_subtitle_music_audit.json` records these product observations:

- opener should be a designed title hook with material presence, not plain static text
- section changes should use rhythm/title/motion grammar
- chapter titles should enter, hold briefly, and clear before unrelated footage
- speech/name/context text must be readable and bounded
- source speech requires transcript review and a ducking plan
- music leads the MV body, but legal/music approval is not claimed
- closing should use callback, memory-wall, or payoff language rather than abrupt stop

## Shot Reuse / Product Design Observations

`reference_shot_reuse_map.json` uses sampled-frame average-hash clusters to approximate reuse. This is not a full scene detector.

Policy extracted:

- repeated footage is acceptable when used as callback, rhythm, or emphasis
- repeated footage as filler should be marked and avoided
- old compiled/final-like videos may be reference/support but should not become primary proof without explicit approval

## Product Standards Extracted

`reference_product_standard.json` defines standards for future graduation film runs:

- A complete product needs opener hook, long training MV body, authority/formal moment or honest bridge, teacher/class or people context, activity/belonging montage, and closing payoff.
- Training MV body should remain the longest section.
- Titles must enter, hold, and exit; persistent side rail is not the product default.
- Source speech subtitles require transcript review.
- Opener and closer need reviewable effect assets.
- Story-to-MV transitions should be designed rather than accidental cuts.
- Music may lead the MV body, but legal approval is not implied by metadata.
- Raw footage/photos are preferred proof; compiled/final-like videos remain support/reference unless explicitly approved.
- Five-minute rehearsals should target 240-300s.
- Ten-minute route requires stronger source speech, people sections, and more raw certification/check proof.

## Gap Against Current Pipeline

`gap_against_current_pipeline.json` compares the reference standard to:

- `.tmp\soul_first_real_material_planning_20260708-060509`
- `.tmp\shot_level_material_proof_completion_20260708-080727`
- `.tmp\effect_factory_integration_completion_20260708-154117`

Summary:

- reference teardown: covered by this round
- story structure: partial
- raw shot-level proof: partial
- certification/check proof: blocked
- source speech handling: blocked
- opener/closer effect line: partial, ready for human effect review
- title/subtitle behavior: partial
- music/legal evidence: partial, not legally approved
- five-minute rehearsal entry: partial, ready only after review/limitations are accepted

## Next Render Rehearsal Spec

`next_render_rehearsal_spec.json` recommends:

```text
music_subtitle_only
```

Target duration:

```text
240-300 seconds
```

Required sections:

- designed opener
- training MV body as longest section
- certification/check shortened or bridged
- teacher/class/people context
- designed closing payoff

Effect assets to use or revise:

```text
.tmp\effect_factory_integration_completion_20260708-154117\effect_handoff.json
```

Source speech handling:

```text
exclude formal supervisor source speech from music_subtitle_only route unless human transcript review is completed
```

Certification/check handling:

```text
shorten or use standards/check bridge until raw certification proof is found
```

## Commands

Red-first precheck:

```powershell
C:\Users\user\miniconda3\python.exe -c "<missing reference-standard artifact precheck>"
```

Exit code: 1, expected red-first failure.

Reference candidate preflight:

```powershell
C:\Users\user\miniconda3\python.exe -c "<Unicode-safe candidate path exists/is_file/size check>"
```

Exit code: 0.

Reference ffprobe check:

```powershell
C:\Users\user\miniconda3\python.exe -c "<ffprobe both reference candidates>"
```

Exit code: 0.

Reference teardown generator:

```powershell
C:\Users\user\miniconda3\python.exe -
```

Exit code: 0.

Final artifact check:

```powershell
C:\Users\user\miniconda3\python.exe -c "import json; from pathlib import Path; root=Path('.tmp/reference_film_teardown_product_standard_20260708-161322'); check=json.load(open(root/'final_artifact_check.json',encoding='utf-8')); print(json.dumps(check,ensure_ascii=False,indent=2)); raise SystemExit(0 if check.get('status')=='ok' else 1)"
```

Exit code: 0.

UTF-8/no-corruption check:

```powershell
C:\Users\user\miniconda3\python.exe -c "from pathlib import Path; root=Path('.tmp/reference_film_teardown_product_standard_20260708-161322'); bad=[]; count=0; ..."
```

Exit code: 0.

Output:

```text
checked 12
bad []
```

`git diff --check`:

```powershell
git diff --check
```

Exit code: 0.

Output contained existing CRLF warnings only for unrelated tracked files.

## Final Artifact Check

`final_artifact_check.json` status:

```text
ok
```

Verified:

- fresh output root exists
- no new rendered final film was created
- all required teardown artifacts exist
- primary reference exists and has ffprobe evidence
- opener, middle, and ending contact sheets exist
- product standard contains product-level standards, not only technical metadata
- gap comparison references prior soul/shot/effect packages
- next render rehearsal spec is actionable
- prior outputs were not mutated by teardown artifacts
- generated JSON/Markdown decodes as UTF-8 with no replacement characters or suspicious repeated question marks

## Human Review Packet

Review packet:

```text
.tmp\reference_film_teardown_product_standard_20260708-161322\reference_teardown_review_packet.md
```

## Deviations

- No reusable tool or test was added. The work order delegated implementation route, and a run-local teardown package satisfied the required artifacts without code changes.
- Section boundaries are heuristic and confidence-scored. Low-confidence areas are marked instead of invented.
- Audio/music observations are product-level and visual-sampling-based; no legal/music approval or transcript approval is claimed.
- Frame extraction was representative, not full-film extraction: 240 total frames across four 60-second windows.

## Blockers

- Supervisor/source speech remains blocked pending human transcript review.
- Certification/check proof remains blocked or must be shortened/bridged until raw proof is found.
- Human effect review is still required before using effect assets in a render rehearsal.
- Music/legal approval remains unclaimed.

## Next Recommended Work

Review:

- `.tmp\reference_film_teardown_product_standard_20260708-161322\reference_teardown_review_packet.md`
- `.tmp\reference_film_teardown_product_standard_20260708-161322\reference_product_standard.json`
- `.tmp\reference_film_teardown_product_standard_20260708-161322\next_render_rehearsal_spec.json`

If accepted, start the next `music_subtitle_only` five-minute render rehearsal using both:

- `.tmp\shot_level_material_proof_completion_20260708-080727\render_rehearsal_entry_packet.json`
- `.tmp\effect_factory_integration_completion_20260708-154117\effect_handoff.json`

The rehearsal should follow the reference standard and keep source speech excluded unless transcript review is completed.
