# Scripted Delivery / Verify Gates Hardening Report

Date: 2026-07-06

## Files changed

Changed by this round:

- `video_pipeline_core/delivery_gate.py`
- `tools/pipeline_home.py`
- `tests/test_delivery_gate.py`
- `tests/test_pipeline_home.py`
- `docs/construction-guides/work-orders/2026-07-06-scripted-delivery-verify-gates-hardening-report.md`

Observed but not touched by this worker:

- `AGENTS.md` already had working-tree differences when checked at the end of the round.

No changes were made to `final_product_verify`, provider/runtime code, `.env`, `.venv_voxcpm`, Downloads, reference repo, or production-cut tooling.

## Red-first evidence

### UTF-8 / CJK

Red command:

`C:\Users\user\miniconda3\python.exe -m unittest tests.test_delivery_gate`

Exit code: 1.

Observed failure included missing scripted text corruption blocks. The new fixture expected `corrupt_script_text`, `corrupt_narration_manifest`, `corrupt_subtitles`, and `corrupt_subtitle_alignment`; the current gate did not report all required blocking rules.

### Subtitle

Same red command and exit code: 1.

Observed failures:

- Missing `subtitle_audio_alignment_report.json` was not fail-closed.
- `subtitle_audio_alignment_report.json` with `ok=false` did not produce the required alignment block.
- Subtitle text not corresponding to audible audio was not blocked when it was not labeled editorial.

### Source speech

Same red command and exit code: 1.

Observed failures:

- A story contract requiring source speech could still pass with only VoxCPM narration evidence.
- `source_speech_preservation_report.json` status `preserved` did not require an audio mix track carrying source speech or preserved original audio.

### Story-to-material

Red commands:

`C:\Users\user\miniconda3\python.exe -m unittest tests.test_delivery_gate`

Exit code: 1.

Observed failures:

- Agent-inferred story mappings passed silently without a visible `story_human_review_required` warning.
- Required story beats absent from `story_to_material_map.json` did not block.

`C:\Users\user\miniconda3\python.exe -m unittest tests.test_pipeline_home`

Exit code: 1.

Tail:

`AssertionError: 'story human review' not found in 'delivery gate passed and final.mp4 exists'`

## Implemented rules

Blocking rules:

- `corrupt_script_text`: `script.json` contains mojibake/repeated question marks, replacement characters, or lacks expected CJK text.
- `corrupt_narration_manifest`: narration manifest contains corrupt text or lacks expected CJK text.
- `corrupt_subtitles`: subtitles contain mojibake/repeated question marks or replacement characters.
- `corrupt_subtitle_alignment`: subtitle alignment report carries corrupt or missing expected CJK text.
- `missing_subtitle_audio_alignment_report`: subtitles are required and audible narration/source-speech evidence exists, but no alignment report exists.
- `subtitle_audio_alignment_failed`: alignment report exists with `ok=false`.
- `unlabeled_editorial_subtitles`: subtitles that do not correspond to audible audio are not labeled as editorial captions.
- `missing_source_speech_preservation_evidence`: story inputs require visible/source speech but neither preservation nor rejection evidence exists.
- `source_speech_not_mixed`: source speech is marked preserved but the audio mix report does not include source speech/preserved-original-audio.
- `invalid_source_speech_rejection`: rejection evidence is missing or does not state a concrete unusable reason.
- `missing_story_to_material_map`: story contract has required beats but no usable story-to-material map exists.
- `story_required_beats_uncovered`: required story beats are absent from the story-to-material map.
- `story_to_final_alignment_failed`: story-to-final alignment report explicitly fails.

Warning/limitation-style visible rule:

- `story_human_review_required`: technical delivery may pass, but agent-filled or inferred story mapping remains visible as needing human creative review. `pipeline_home` now includes this warning in its pass reason and does not present the state as unqualified creative approval.

## Acceptance

`C:\Users\user\miniconda3\python.exe -m unittest tests.test_delivery_gate tests.test_delivery_gate_report tests.test_pipeline_home tests.test_final_product_verify`

Exit code: 0.

Tail:

`Ran 149 tests in 9.302s`

`OK`

`C:\Users\user\miniconda3\python.exe -m unittest tests.test_delivery_gate`

Exit code: 0.

Tail:

`Ran 59 tests in 4.167s`

`OK`

`C:\Users\user\miniconda3\python.exe tools\write_delivery_gate_report.py --run "C:\Users\user\Desktop\video_pipeline\.tmp\scripted_real_material_production_run_20260706-131200\run" --json`

Exit code: 0.

Result: `pass=true`, `blocking=[]`, `warnings=[story_human_review_required]`, summary showed video and audio streams present with duration about 65.04 seconds.

`C:\Users\user\miniconda3\python.exe tools\pipeline_home.py --run "C:\Users\user\Desktop\video_pipeline\.tmp\scripted_real_material_production_run_20260706-131200\run" --json`

Exit code: 0.

Result: `mode=done`, `cursor=complete`, `status=DONE`, reason included `story human review required: story-to-material mapping includes agent-filled or inferred choices; technical delivery still needs human creative review`.

`git diff --check`

Exit code: 0.

Tail: only line-ending warnings for working-copy files; no whitespace errors.

## Repaired scripted run smoke

Run path:

`C:\Users\user\Desktop\video_pipeline\.tmp\scripted_real_material_production_run_20260706-131200\run`

Delivery gate status:

- Pass: true
- Blocking: none
- Warning: `story_human_review_required`
- Waivers: none

Pipeline home status:

- `DONE`
- Not an unqualified creative approval; the reason explicitly carries the human story-review requirement.

## Deviations

- `story_human_review_required` was implemented as a warning, not a blocking rule, because the work order allows technical delivery to pass when only human creative review is outstanding.
- `final_product_verify` files were not changed. The existing repo pattern allowed the delivery gate to consume the required artifacts directly, and the acceptance suite for `tests.test_final_product_verify` remained green.
- Existing `AGENTS.md` working-tree changes were left untouched.

## Post-review fixes

An independent review found three merge blockers before PR creation:

- English names such as `Zhang` were incorrectly treated as a Chinese-language signal.
- `story_human_review_required` still returned `pipeline_home` as `DONE/complete`.
- Source-speech preservation was triggered by broad words such as `director` instead of explicit source-speech evidence.

Fixes applied after review:

- Chinese/CJK expectation now uses existing CJK text or explicit language/locale fields such as `zh`, `zh-*`, `Chinese`, or `Mandarin`; it does not scan arbitrary prose for `zh`.
- `pipeline_home` returns `mode=waiting`, `cursor=human_story_review`, and `next_action_class=review_stop` when the delivery gate passes but `story_human_review_required` is present.
- Source-speech preservation now requires explicit source-speech evidence/policy such as `evidence_type=source_speech`, `source_speech_policy`, or a source-speech beat id, not incidental director/instructor wording.

Focused post-review tests:

- `test_scripted_gate_does_not_treat_zhang_as_chinese_language_signal`
- `test_scripted_gate_does_not_require_source_speech_for_director_approved_visual_montage`
- `test_passed_scripted_delivery_gate_exposes_human_review_warning`

## Blockers

No implementation blocker was hit. No node was stopped for provider/runtime scope. No product decision was required beyond the work-order delegated choice to surface story review as a visible warning.

## Next recommended work

Run the next scripted real-material production attempt with these hardened gates enabled, then add or require a human review artifact for `story_to_material_map.json` so `story_human_review_required` can be cleared intentionally instead of remaining as a technical-candidate limitation.
