# 2026-07-08 Music Policy And Reference Script Package Report

## Result

Status: completed.

Fresh script output root:

```text
.tmp\reference_aligned_alternate_script_20260708-165933
```

This round did not render media, download/search music, write `story_human_review_decision.json`, write transcript approval, edit Downloads, edit existing `.tmp` runs, edit env/venv/reference repo, or create a delivery package.

## Files Changed

Policy/code/tests/docs changed in this round:

- `video_pipeline_core/soundtrack_arranger.py`
- `video_pipeline_core/audio_handoff_acceptance.py`
- `tools/soundtrack_flow_acceptance.py`
- `tests/test_soundtrack_arranger.py`
- `tests/test_audio_handoff_acceptance.py`
- `tests/test_soundtrack_flow_acceptance.py`
- `docs/soundtrack-arranger-route.md`
- `docs/branch-contract-registry.md`
- `docs/branch-contract-registry.json`
- `docs/video-pipeline-operating-map.md`
- `docs/pipeline-decision-tree.md`
- `docs/construction-guides/work-orders/2026-07-08-music-subtitle-only-five-minute-render-rehearsal.md`
- `docs/construction-guides/work-orders/2026-07-08-music-policy-and-reference-script-package-report.md`

Fresh run-local script artifacts were written only under:

```text
.tmp\reference_aligned_alternate_script_20260708-165933
```

Note: the working tree already contained other modified/untracked files outside this task. They were not reverted or treated as this round's changes.

## Red-First Evidence

Command:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_soundtrack_arranger tests.test_audio_handoff_acceptance tests.test_soundtrack_flow_acceptance
```

Exit code: 1.

Observed failures:

- `test_human_declared_source_root_music_is_internal_rehearsal_usable_without_legal_approval`: source-root candidate still had `delivery_allowed=false`.
- `test_accepts_human_declared_source_folder_music_for_internal_rehearsal_without_legal_approval`: audio mix track did not carry `music_use_basis`.

This proved the policy gap before implementation.

## Music Policy Implemented

Final policy fields/statuses:

- `music_use_basis.status`: `human_declared_allowed`
- `music_use_basis.usage_scope`: `internal_rehearsal` or another internal/review scope
- `music_use_basis.declared_by`: `human`, `user`, or `operator`
- `music_use_basis.pipeline_legal_search_performed`: false unless a real legal search happened
- `music_use_basis.legal_approval_claimed`: false
- `music_use_basis.external_publication_requires_rights_review`: true
- selected source/user/manual music can carry `music_use_status=human_declared_internal_use`
- `sound_license_manifest.legal_approval_claimed=false`
- `audio_mix_plan.tracks[].legal_approval_claimed=false`

Allowed by policy:

- `source_folder_audio`
- `user_provided`
- `manual_import`
- `reviewed_manual`

Only for internal/rehearsal review when a human-declared basis is recorded.

Still blocked:

- `reference_only`
- missing audio file
- failed or missing probe when probe is required
- vocal conflict under voiceover/preserved speech
- section mismatch
- explicit denied/not-allowed status
- external publication/upload without separate rights review

## Before / After Music Example

Probe command:

```powershell
C:\Users\user\miniconda3\python.exe -c "<source-folder music before/after arrange_soundtrack probe>"
```

Exit code: 0.

Before:

```json
{
  "delivery_allowed": false,
  "blocks": ["license_missing"],
  "license_status": "source_folder_audio_requires_review"
}
```

After adding `music_use_basis.status=human_declared_allowed`:

```json
{
  "delivery_allowed": true,
  "blocks": [],
  "license_status": "human_declared_allowed",
  "music_use_status": "human_declared_internal_use",
  "legal_approval_claimed": false
}
```

## Script Package

Required artifacts written:

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

Short story summary:

```text
把手上的光交給明天
```

Thesis:

```text
這不是把課程排完，而是把一群人從生疏到能承擔現場責任的過程拍出來。
```

The script defaults to `music_subtitle_only`, uses music + subtitles as the main delivery mechanism, avoids depending on supervisor source speech, shortens/bridges certification/check, and maps each major beat to raw proof, support, bridge, effect/title, or blocked.

Timing:

- current-capacity cut: 214 seconds
- reference-target extension plan: 284 seconds

Music policy in the script package:

- `music_use_basis.status=human_declared_allowed`
- `usage_scope=internal_rehearsal`
- `legal_approval_claimed=false`
- external publication rights review still required

## Acceptance Commands

Focused soundtrack policy tests:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_soundtrack_arranger tests.test_audio_handoff_acceptance tests.test_soundtrack_flow_acceptance
```

Exit code: 0.

Output:

```text
Ran 34 tests in 9.425s
OK
```

Broader branch-impact tests:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_soundtrack_arranger tests.test_audio_handoff_acceptance tests.test_soundtrack_flow_acceptance tests.test_delivery_gate tests.test_pipeline_home
```

Exit code: 0.

Output:

```text
Ran 179 tests in 20.202s
OK
```

Fresh script final artifact check:

```powershell
C:\Users\user\miniconda3\python.exe -c "import json; from pathlib import Path; root=Path('.tmp/reference_aligned_alternate_script_20260708-165933'); check=json.load(open(root/'final_artifact_check.json',encoding='utf-8')); print(json.dumps(check,ensure_ascii=False,indent=2)); raise SystemExit(0 if check.get('status')=='ok' else 1)"
```

Exit code: 0.

UTF-8/no-corruption check:

```powershell
C:\Users\user\miniconda3\python.exe -c "from pathlib import Path; root=Path('.tmp/reference_aligned_alternate_script_20260708-165933'); bad=[]; count=0; ..."
```

Exit code: 0.

Output:

```text
checked 14
bad []
```

Registry JSON parse:

```powershell
C:\Users\user\miniconda3\python.exe -c "import json; json.load(open('docs/branch-contract-registry.json', encoding='utf-8')); print('json ok')"
```

Exit code: 0.

Output:

```text
json ok
```

Git diff check:

```powershell
git diff --check
```

Exit code: 0.

Output contained CRLF warnings only.

## Deviations

- `tools/video_tools.py` listed in the owner zone does not exist in this repo; the active root CLI is `video_tools.py`. No change was needed there because the tested operator-facing policy path is `tools/soundtrack_flow_acceptance.py --music-use-basis human_declared_internal_use`.
- The initial script package check failed because the current-capacity cut was 206 seconds. It was repaired within the fresh output root to 214 seconds before acceptance.
- No code was added for music download/search or rendering.

## Blockers

- Legal/music approval is not claimed. External upload/publication still requires separate human/operator rights review.
- Supervisor/source speech remains excluded unless human transcript review is completed.
- Certification/check remains bridge/shorten unless raw proof is found.
- Human story/material review is still required before using the alternate script for a render rehearsal.

## Next Recommended Work

Review:

```text
.tmp\reference_aligned_alternate_script_20260708-165933\human_review_packet.md
.tmp\reference_aligned_alternate_script_20260708-165933\alternate_render_facing_script.md
.tmp\reference_aligned_alternate_script_20260708-165933\alternate_section_timing_plan.json
```

If the story, certification bridge, effect/title plan, and internal music-use basis are accepted, start the next `music_subtitle_only` render rehearsal using the updated policy plus:

- `.tmp\shot_level_material_proof_completion_20260708-080727\render_rehearsal_entry_packet.json`
- `.tmp\effect_factory_integration_completion_20260708-154117\effect_handoff.json`
- `.tmp\reference_aligned_alternate_script_20260708-165933\alternate_render_facing_script.json`
