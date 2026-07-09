# 2026-07-08 Shot-Level Material Proof Completion

## Goal

Turn the completed soul-first no-render package into a shot-level, human-reviewable material proof package. This round must bridge the gap between "the story structure is valid" and "the next render rehearsal has enough concrete shot evidence to begin."

Do not render final media. Do not rework the story from scratch. The job is to complete the missing editor layer: shot pool, per-beat proof/support role, old compiled-video risk, thin certification/check proof, supervisor transcript readiness, and a concrete render rehearsal entry decision.

## Source Basis

Use this prior output as the planning basis:

`.tmp\soul_first_real_material_planning_20260708-060509`

Key prior artifacts:

- `story_contract.json`
- `screenplay_beats.json`
- `director_shot_plan.json`
- `material_needs.json`
- `story_to_material_map.json`
- `story_material_negotiation.json`
- `material_delta.json`
- `creative_gap_strategy.json`
- `render_facing_shot_plan.json`
- `no_render_review_packet.md`
- `production_line_completion_map.json`

Real source input remains read-only:

`C:\Users\user\Downloads\微電影素材\_整理後`

## Owner Zone

Editable paths:

- New output root under `.tmp\shot_level_material_proof_completion_*`
- Run-local artifacts inside that fresh output root
- `video_pipeline_core/*shot*proof*.py`
- `video_pipeline_core/*material*proof*.py`
- `video_pipeline_core/*material*gap*.py`
- `video_pipeline_core/*source*speech*.py`
- `video_pipeline_core/*transcript*review*.py`
- `video_pipeline_core/*render*facing*.py`
- `tools/*shot*proof*.py`
- `tools/*material*proof*.py`
- `tools/*material*gap*.py`
- `tools/*source*speech*.py`
- `tools/*transcript*review*.py`
- `tools/*render*facing*.py`
- Relevant tests under `tests/`
- `docs/branch-contract-registry.md`
- `docs/branch-contract-registry.json`
- `docs/video-pipeline-operating-map.md`
- `docs/pipeline-decision-tree.md`
- `docs/construction-guides/work-orders/2026-07-08-shot-level-material-proof-completion-report.md`

## Forbidden Zone

Read-only paths:

- `C:\Users\user\Downloads\微電影素材\_整理後`
- `.tmp\soul_first_real_material_planning_20260708-060509`
- Existing `.tmp\graduation_v*` runs
- Existing `.tmp\v6_*` runs
- Existing `.tmp\voxcpm_provider_leadin_artifact_diagnostic_*` runs
- `deliveries\`
- `.env`, `.env.*`
- `.venv_voxcpm\`
- `reference repo\`
- VoxCPM reference/source repository
- Existing final media artifacts
- `story_human_review_decision.json` in any run
- Git branch/commit/push operations

## Required Pieces

1. Create a fresh no-render output root. Copy or reference prior soul-first artifacts as read-only inputs; do not mutate them.
2. Produce `shot_level_material_proof_plan.json`. For every screenplay beat, list candidate shots with:
   - `shot_id`
   - `beat_id`
   - `source_relative_path`
   - `asset_kind`
   - `planned_start_sec`
   - `planned_duration_sec`
   - `shot_function`
   - `proof_or_support`
   - `raw_or_compiled_risk`
   - `repeat_policy`
   - `fallback_if_rejected`
3. Produce `shot_pool_inventory.json` with per-section shot counts and duration capacity. It must distinguish raw footage/photos from old compiled videos and source-folder music/video files.
4. Produce `compiled_source_risk_audit.json`. Any source under old compiled/music/final-like folders must be classified as:
   - `raw_usable`
   - `compiled_reference_only`
   - `needs_human_review`
   - `reject_for_primary_proof`
5. Produce `certification_gap_completion_plan.json`. It must decide whether certification/check is shortened, source-searched, replaced by standards/check language, or blocked pending raw proof. Do not fake this beat with old compiled footage.
6. Produce `supervisor_transcript_review_packet.md` and `supervisor_transcript_review_packet.json`. They must identify candidate supervisor speech takes, current transcript status, why human transcript approval is needed, and what would be used in a render rehearsal.
7. Produce `render_rehearsal_entry_packet.json`. It must state whether a future 5-minute render rehearsal may start, and under what profile:
   - `music_subtitle_only`
   - `source_speech_plus_music`
   - `narrated_optional`
   It must not require VoxCPM for the no-narration route.
8. Produce `shot_level_review_packet.md` for the user. It should show, in human language, what each section will use, what is thin, what is risky, and what must be approved or replaced.
9. Update `production_line_completion_map.json` in the fresh output root. It must show whether the shot-level proof layer is `ready`, `partial`, `blocked`, or `missing`, and how this changes the next render rehearsal entry point.
10. If adding/changing tools, write red-first tests. If no code changes are made, run an executable pinned-Python artifact check that verifies all required files and fields.

## Red-First Verification

Before implementation, capture failing evidence that the prior soul-first package is not yet render-proof-ready. Acceptable red-first evidence:

- `render_facing_shot_plan.json` lacks shot ids, per-shot durations, or raw/compiled risk classification.
- `material_delta.json` has thin certification/check proof.
- Supervisor/source speech transcript approval remains unresolved.

Use pinned interpreter:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest <focused_tests_for_changed_modules>
```

If no code changes are made, use a pinned Python precheck that exits non-zero and records missing shot-level proof fields.

## Acceptance Commands

Use `C:\Users\user\miniconda3\python.exe` for every Python command. Do not use bare `python` or `pytest`.

If code/tests are changed, expected exit code `0`:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest <new_or_changed_focused_tests>
```

Run the no-render artifact generator/check with pinned Python. The exact command is delegated, but it must write all required artifacts under the fresh `.tmp\shot_level_material_proof_completion_*` root and exit `0` unless a real stop-loss is reached.

Registry parse, if registry JSON is edited:

```powershell
C:\Users\user\miniconda3\python.exe -c "import json; json.load(open('docs/branch-contract-registry.json', encoding='utf-8')); print('json ok')"
```

Expected exit code `0`:

```powershell
git diff --check
```

Final artifact check, run with pinned Python, must verify:

- Fresh output root exists.
- No final/rendered media was created.
- Required artifacts listed in Required Pieces exist.
- Every beat has at least one candidate shot or an explicit blocked/thin decision.
- Old compiled/final/music-folder sources are not silently primary proof.
- Certification/check has an explicit gap decision.
- Supervisor transcript review packet exists.
- `render_rehearsal_entry_packet.json` does not require VoxCPM for no-narration profiles.
- Prior soul-first output and V-runs were not modified.
- Generated JSON/Markdown text decodes with UTF-8 and contains no `\ufffd` or suspicious repeated literal question-mark runs.

## Stop-Loss Limits

- If prior soul-first package is missing, stop.
- If real source folder is missing, stop after preflight.
- If shot-level evidence cannot be produced beyond folder/file-name guesses, stop as `shot_material_evidence_too_shallow`.
- If certification/check relies only on old compiled footage, mark it thin or blocked; do not promote it to primary proof.
- If supervisor speech cannot be transcript-reviewed, mark source speech blocked; do not fake transcript approval.
- Do not render.
- Do not write `story_human_review_decision.json`.
- Do not claim legal/music approval.
- Do not change VoxCPM behavior in this round.

## Delegated Decisions

- Exact schema field names beyond required artifact names and required concepts.
- Whether to add reusable tools or produce run-local artifacts only.
- Exact shot counts per beat, as long as capacity and risk are explicit.
- Exact render rehearsal profile recommendation.
- Whether the five-minute route may proceed with certification shortened, based on evidence.

## Final Report Requirements

Write `docs/construction-guides/work-orders/2026-07-08-shot-level-material-proof-completion-report.md` with:

- Output root and command/exit-code table.
- Red-first evidence.
- Shot pool summary by section.
- Compiled-source risk audit summary.
- Certification/check gap decision.
- Supervisor transcript review status.
- Render rehearsal entry recommendation and profile.
- Human shot-level review packet path.
- Production-line completion update.
- Confirmation that no render/final media or final approval was written.
- Deviations, blockers, and next recommended work.
