# 2026-07-08 Music Policy And Reference Script Package

## Goal

Complete one combined worker round:

1. Harden the music-use policy so internal rehearsal/review candidates may use source-folder or human-specified music when a human-declared music-use basis exists.
2. Produce a no-render, reference-aligned alternate graduation-film script package that uses that policy and matches the reference standard's level of detail.

This task must not render media, download music, write final approval artifacts, or claim legal approval.

## Construction Basis

Read these first:

- `docs/construction-guides/work-orders/2026-07-08-human-declared-music-use-policy.md`
- `docs/construction-guides/work-orders/2026-07-08-reference-aligned-pipeline-gap-analysis-report.md`

The first document is authoritative for code/test/docs policy changes. The second document is authoritative for the alternate script package.

## Owner Zone

Editable paths:

- `video_pipeline_core/soundtrack_arranger.py`
- `video_pipeline_core/audio_handoff_acceptance.py`
- `tools/soundtrack_arranger.py`
- `tools/soundtrack_flow_acceptance.py`
- `tools/video_tools.py`
- `tests/test_soundtrack_arranger.py`
- `tests/test_audio_handoff_acceptance.py`
- `tests/test_soundtrack_flow_acceptance.py`
- `docs/soundtrack-arranger-route.md`
- `docs/branch-contract-registry.md`
- `docs/branch-contract-registry.json`
- `docs/video-pipeline-operating-map.md`
- `docs/pipeline-decision-tree.md`
- `docs/construction-guides/work-orders/2026-07-08-music-subtitle-only-five-minute-render-rehearsal.md`
- Fresh output root under `.tmp\reference_aligned_alternate_script_*`
- `docs/construction-guides/work-orders/2026-07-08-music-policy-and-reference-script-package-report.md`

## Forbidden Zone

Read-only paths:

- `C:\Users\user\Downloads\微電影素材\_整理後`
- `deliveries\`
- Existing `.tmp\` runs except read-only construction inputs named above
- Existing final media artifacts
- `.env`, `.env.*`
- `.venv_voxcpm\`
- `reference repo\`
- VoxCPM reference/source repository
- Story approval artifacts such as any `story_human_review_decision.json`
- Human transcript approval artifacts
- Render outputs
- Visual-selection, transcript, VoxCPM, and effect-factory code unless a directly failing soundtrack-policy test proves the dependency
- Git branch/commit/push operations

## Required Pieces

1. Implement the human-declared music-use policy from the music policy work order.
   - Internal/rehearsal use can proceed on human-declared basis.
   - Pipeline records source evidence and the human basis.
   - Pipeline does not claim legal approval without explicit rights evidence.
   - Missing file, reference-only, probe, vocal-conflict, and section mismatch blockers stay intact.

2. Produce the reference-aligned alternate script package.
   - Use a fresh `.tmp\reference_aligned_alternate_script_*` root.
   - Do not render.
   - Do not write `story_human_review_decision.json`.
   - Default to music + subtitles; narration/VoxCPM is optional test-only.
   - Use the new music-use policy wording: record `music_use_basis`, not legal approval.

3. Required script artifacts:
   - `reference_aligned_script_brief.json`
   - `alternate_story_contract.json`
   - `alternate_screenplay_beats.json`
   - `alternate_render_facing_script.md`
   - `alternate_render_facing_script.json`
   - `alternate_section_timing_plan.json`
   - `alternate_material_mapping_notes.json`
   - `alternate_effect_title_subtitle_plan.json`
   - `script_gap_decisions.json`
   - `human_review_packet.md`
   - `final_artifact_check.json`
   - `script_package_report.md`

## Script Requirements

- Write a different graduation-film story package; do not copy the reference beat-for-beat.
- Match the reference standard's detail density.
- Include opening story, training MV, people/context, and designed closing.
- Include a coherent thesis, not just a course list.
- Explain why training modules are ordered that way.
- Specify opener/closer effect intent and title/subtitle pockets.
- Do not rely on supervisor source speech unless marked transcript-review-required.
- Shorten or bridge certification/check unless raw proof is available.
- Produce both a current-capacity 210-230s cut and a 240-300s extension plan.
- Map each major beat to raw proof, support, bridge, effect/title, or blocked.

## Red-First Verification

Before implementation, capture failing evidence for the music policy gap:

- Source-folder or user-specified music with a human-declared internal-use basis currently blocks or remains unavailable because legal review is missing.

Record the command and failure in the final report.

Before producing the script package, record the precondition that no alternate script package exists in the fresh output root.

## Acceptance Commands

Use:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_soundtrack_arranger tests.test_audio_handoff_acceptance tests.test_soundtrack_flow_acceptance
```

Expected exit code: `0`.

Run:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_soundtrack_arranger tests.test_audio_handoff_acceptance tests.test_soundtrack_flow_acceptance tests.test_delivery_gate tests.test_pipeline_home
```

Expected exit code: `0`.

Run a final artifact check for the fresh script output root with `C:\Users\user\miniconda3\python.exe`. It must verify all required script artifacts exist, all generated JSON/Markdown decodes as UTF-8, no `\ufffd`, no suspicious repeated literal question-mark runs, no final media, no story approval artifact, and no legal approval claim.

Validate registry JSON:

```powershell
C:\Users\user\miniconda3\python.exe -c "import json; json.load(open('docs/branch-contract-registry.json', encoding='utf-8')); print('json ok')"
```

Run:

```powershell
git diff --check
```

Expected exit code: `0`, except existing CRLF warnings may be reported if already present.

## Stop-Loss Limits

Stop and report instead of broadening if:

- The task would require render, music download/search, or prior-run edits.
- Passing requires declaring legal approval without explicit evidence.
- `reference_only`, missing audio files, probe failures, or vocal conflicts would be allowed into the mix.
- The script package cannot be grounded in the reference gap analysis.
- Chinese text would need to be written through unsafe PowerShell raw text.

## Delegated Decisions

- Exact enum/field names for the human-declared music-use basis.
- Exact CLI flag names if needed.
- Exact alternate story theme, as long as it is different from the reference and satisfies the script requirements.
- Exact script artifact schemas, as long as the required artifacts and final checks pass.
- Exact output root suffix.

## Final Report Requirements

Write:

```text
docs/construction-guides/work-orders/2026-07-08-music-policy-and-reference-script-package-report.md
```

Include:

- Files changed.
- Fresh script output root.
- Red-first evidence and command exit code.
- Acceptance command exit codes.
- Final music-use policy fields/statuses.
- Before/after example for source-folder or user-provided music.
- Script artifact paths and short story summary.
- Confirmation that no render, download, legal approval, story approval, prior run edit, Downloads edit, env/venv edit, or delivery package edit occurred.
- Deviations, blockers, and next recommended work.
