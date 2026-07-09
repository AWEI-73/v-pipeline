# 2026-07-08 Effect Factory Integration Completion

## Goal

Complete the missing production-line handoff from story/effect intent to actual reviewable effect assets. Prior rounds created opener/closer/effect intent documents, but the pipeline did not route those intents into Effect Factory / Remotion Effect Worker outputs. This round must make that gap explicit and produce bounded, non-final effect proof artifacts for opener, closer, and title/transition treatments.

This is not a final film render. It is an effect-line integration completion pass.

## Source Basis

Use these prior outputs as read-only input:

- `.tmp\soul_first_real_material_planning_20260708-060509`
- `.tmp\shot_level_material_proof_completion_20260708-080727`

Relevant prior artifacts:

- `opening_design_brief.json`
- `closing_design_brief.json`
- `effect_intent_plan.json`
- `title_subtitle_strategy.json`
- `render_facing_shot_plan.json`
- `shot_level_material_proof_plan.json`
- `shot_level_review_packet.md`
- `production_line_completion_map.json`

Real source input remains read-only:

`C:\Users\user\Downloads\微電影素材\_整理後`

## Owner Zone

Editable paths:

- New output root under `.tmp\effect_factory_integration_completion_*`
- Run-local artifacts inside that fresh output root
- `video_pipeline_core/*effect*factory*.py`
- `video_pipeline_core/*effect*contract*.py`
- `video_pipeline_core/*effect*handoff*.py`
- `video_pipeline_core/*remotion*effect*.py`
- `video_pipeline_core/*title*effect*.py`
- `tools/*effect*factory*.py`
- `tools/*effect*contract*.py`
- `tools/*effect*handoff*.py`
- `tools/*remotion*effect*.py`
- `tools/*title*effect*.py`
- Relevant tests under `tests/`
- `docs/branch-contract-registry.md`
- `docs/branch-contract-registry.json`
- `docs/video-pipeline-operating-map.md`
- `docs/pipeline-decision-tree.md`
- `docs/construction-guides/work-orders/2026-07-08-effect-factory-integration-completion-report.md`

## Forbidden Zone

Read-only paths:

- `C:\Users\user\Downloads\微電影素材\_整理後`
- `.tmp\soul_first_real_material_planning_20260708-060509`
- `.tmp\shot_level_material_proof_completion_20260708-080727`
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

1. Create a fresh no-final output root. Do not mutate prior soul-first or shot-level outputs.
2. Produce `effect_line_gap_audit.json`. It must show that prior outputs had `effect_intent_plan.json` but no actual effect assets, no effect handoff, and no effect preview proof.
3. Produce `effect_design_map.json` covering at least:
   - opener memory-wall/title reveal
   - story-to-training-MV transition
   - training chapter title treatment
   - closing memory-wall/payoff
4. Produce `effect_contract.json` using Effect Factory contract concepts:
   - `effect_id`
   - `effect_role`
   - `style_family`
   - `story_function`
   - display/copy text
   - duration
   - visual primitives
   - motion primitives
   - controls
   - negative rules
   - review questions
   - backend policy
5. Use existing reviewed source/frame evidence where possible. Build `effect_collage_refs.json` or equivalent from shot-level frame evidence for opener/closer memory-wall assets. Do not treat effect refs as material proof.
6. Choose a backend per effect:
   - Remotion worker route for memory-wall/title reveal, film-strip/story-to-MV transition, and designed title treatments when available.
   - ffmpeg/light-effect fallback only when explicitly declared.
   - If rendering cannot be done, produce a failed/blocked worker output with reason; do not silently downgrade to static text.
7. Produce a worker handoff artifact such as `remotion_prompt_pack.json` or `effect_worker_handoff.json`. It must be bounded: effect asset producer only, not final assembly owner.
8. Produce reviewable effect evidence. At minimum one of these per required effect:
   - playable preview clip
   - rendered effect asset
   - contact sheet
   - still/keyframe sequence
   - explicit failed job with reason
9. Produce `effect_review.json` that checks:
   - story intent match
   - visual distinction
   - text readability
   - safe area
   - no mojibake or literal question-mark corruption
   - negative rules
   - required effect evidence exists
10. Produce `effect_handoff.json` declaring:
    - bounded finishing asset route
    - owns_final_delivery=false
    - owns_material_truth=false
    - final assembly owner remains ffmpeg/contract-run
    - accepted assets or blocked jobs
    - next action
11. Update `production_line_completion_map.json` in the fresh output root. The effect factory node must no longer stay at pure intent. It must become `ready_for_human_effect_review`, `partial`, or `blocked` with evidence.
12. Produce `effect_line_review_packet.md` for the user. It must explain what opener/closer/title transition assets exist or failed, how they relate to the story, and what should be reviewed before a render rehearsal.
13. If adding/changing tools, write red-first tests. If no code changes are made, run an executable pinned-Python artifact check that verifies required artifacts and evidence.

## Red-First Verification

Before implementation, capture failing evidence that the current production line has effect intent but no actual effect handoff/assets. Acceptable red-first evidence:

- Prior `production_line_completion_map.json` marks opener/closer/effect intent ready while no `effect_handoff.json` or worker output exists.
- Prior shot-level output has no `effect_contract.json`, no `remotion_prompt_pack.json`, and no effect preview evidence.
- A new validator fails because required effect-line artifacts are missing.

Use pinned interpreter:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest <focused_tests_for_changed_modules>
```

If no code changes are made, use a pinned Python precheck that exits non-zero and records the missing effect-line handoff/assets.

## Acceptance Commands

Use `C:\Users\user\miniconda3\python.exe` for every Python command. Do not use bare `python` or `pytest`.

If code/tests are changed, expected exit code `0`:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest <new_or_changed_focused_tests>
```

Run the effect-line generator/check with pinned Python. The exact command is delegated, but it must write all required artifacts under the fresh `.tmp\effect_factory_integration_completion_*` root and exit `0` unless a real stop-loss is reached.

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
- No `final.mp4`, `final_v*.mp4`, or full-film render was created.
- `effect_line_gap_audit.json`, `effect_design_map.json`, `effect_contract.json`, `effect_review.json`, `effect_handoff.json`, `effect_line_review_packet.md`, and `production_line_completion_map.json` exist.
- Each required effect has review evidence or an explicit failed/blocked job reason.
- Effect artifacts do not claim material truth or final delivery ownership.
- Prior soul-first and shot-level outputs were not modified.
- Generated JSON/Markdown text decodes with UTF-8 and contains no `\ufffd` or suspicious repeated literal question-mark runs.

## Stop-Loss Limits

- If prior soul-first or shot-level proof outputs are missing, stop.
- If no reviewed frame/material refs are available for a required memory-wall effect, stop or mark the effect blocked; do not use arbitrary unreviewed media.
- If Remotion/backend tooling is unavailable, produce a blocked worker output and review packet; do not pretend a static title card is an effect asset.
- If Chinese text becomes mojibake or literal question marks, stop and repair artifact writing before continuing.
- Do not render full film.
- Do not write `story_human_review_decision.json`.
- Do not claim legal/music approval.
- Do not change VoxCPM behavior.

## Delegated Decisions

- Exact route implementation: existing Effect Factory tools, Remotion prompt-pack route, ffmpeg/light-effect fallback, or run-local artifacts.
- Exact visual style family, as long as it matches the story contract and is declared in `effect_contract.json`.
- Exact copy text for opener/closer/title treatments, as long as it avoids generic labels and passes UTF-8 checks.
- Whether to produce playable previews or contact-sheet/keyframe evidence, depending on backend availability.
- Whether effect-line status is ready, partial, or blocked, based only on evidence.

## Final Report Requirements

Write `docs/construction-guides/work-orders/2026-07-08-effect-factory-integration-completion-report.md` with:

- Output root and command/exit-code table.
- Red-first evidence.
- Effect gap audit summary.
- Effect contracts created.
- Backend route used per effect.
- Preview/contact-sheet/keyframe evidence paths or blocked job reasons.
- Effect review results.
- Effect handoff status.
- Production-line completion update.
- Confirmation that no full-film render/final media or final approval was written.
- Deviations, blockers, and next recommended work.
