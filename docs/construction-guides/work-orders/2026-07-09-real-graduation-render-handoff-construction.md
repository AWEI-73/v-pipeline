# Real Graduation Render Handoff Construction

## Goal

Build the missing `render_handoff.json` for the real graduation route from already reviewed route evidence, then rerun the graduation product route harness in no-render mode to prove the route reaches the render-rehearsal boundary without skipping product-route, visual, effect, music/subtitle, or compose handoff evidence.

This round constructs and reviews the render handoff only. It is not final render approval, story approval, transcript approval, legal/music approval, delivery approval, or package approval.

## Owner Zone

- `.tmp/real_graduation_render_handoff_construction_*`
- `docs/construction-guides/work-orders/2026-07-09-real-graduation-render-handoff-construction-report.md`

## Forbidden Zone

- `.tmp/real_graduation_effect_handoff_review_promotion_20260709-003642/**`
- any existing `.tmp/**` run outside the fresh owner root
- `C:\Users\user\Downloads\微電影素材\_整理後/**`
- `deliveries/**`
- `video_pipeline_core/**`
- `tools/**`
- `tests/**`
- `skills/**`
- `.env`
- `.venv_voxcpm/**`
- `reference repo/**`

## Required Pieces

1. Verify the current blocker from:
   - `docs/construction-guides/work-orders/2026-07-09-real-graduation-effect-handoff-review-promotion-report.md`
   - `.tmp/real_graduation_effect_handoff_review_promotion_20260709-003642/no_render_out/graduation_product_route_harness_result.json`
   - `.tmp/real_graduation_effect_handoff_review_promotion_20260709-003642/no_render_out/pipeline_execution_trace.json`
   - `.tmp/real_graduation_effect_handoff_review_promotion_20260709-003642/final_artifact_check.json`
2. Create a fresh owner root and a fresh run copy from `.tmp/real_graduation_effect_handoff_review_promotion_20260709-003642/run`.
3. Inventory the run-local inputs that may feed render handoff:
   - `render_rehearsal_entry_packet.json`
   - `shot_level_material_proof_plan.json`
   - `visual_selection_gate.json`
   - `visual_selection_review.json`
   - `effect_handoff.json`
   - `effect_contract.json`
   - `audio_subtitle_review_handoff.json`
   - `music_manifest.json`
   - `soundtrack_probe_report.json`
   - `subtitles.srt`
   - `deliverable_safe_script.json`
4. Write `render_handoff_provenance.json` explaining which reviewed artifacts are used and which are deliberately not used.
5. Write `render_handoff_review.json` with status `accepted_for_render_rehearsal`, `revision_requested`, `rejected`, or `insufficient_evidence`.
6. If accepted, write run-local `render_handoff.json` with at least:
   - `artifact_role: render_handoff`
   - `version`
   - `route: graduation_training_film`
   - `ok: true`
   - `next_action: ready_for_render_rehearsal`
   - `final_delivery_claimed: false`
   - references to visual, effect, music/subtitle, subtitle, script, and provenance artifacts
   - a bounded scope statement that this handoff is not final delivery approval
7. Rerun `tools/run_graduation_product_route.py --mode no-render` on the fresh run and record the trace/result.
8. Write `final_artifact_check.json` covering prior-run immutability, handoff status, trace depth/stage order, stop gate/reason, and whether rendered QA/no-skip were reached.

## Red-First Verification

- First run a read-only precheck that confirms the prior promoted run currently stops at `compose_render_handoff` with `missing render_handoff.json`; record exit code and observed stop gate.
- If the precheck cannot prove that blocker, stop and report `prior_blocker_not_reproducible`.

## Acceptance Commands

Use `C:\Users\user\miniconda3\python.exe`; do not use bare `python` or `pytest`.

- `C:\Users\user\miniconda3\python.exe -m unittest tests.test_graduation_product_route_runner tests.test_rendered_product_qa tests.test_no_skip_execution_trace` expected exit code `0`
- `C:\Users\user\miniconda3\python.exe tools\run_graduation_product_route.py --run "<fresh-run>" --source-root "C:\Users\user\Downloads\微電影素材\_整理後" --mode no-render --out-dir "<fresh-out>\no_render_out" --json` expected exit code `0` after accepted handoff
- `C:\Users\user\miniconda3\python.exe -c "<UTF-8 artifact check for generated JSON/Markdown>"` expected exit code `0`
- `git diff --check` expected exit code `0`; existing CRLF warnings may be reported

## Stop-Loss Limits

- If reviewed visual/effect/music/subtitle evidence is missing, write `insufficient_evidence`; do not write accepted `render_handoff.json`.
- If the handoff cannot identify render-facing sources without relying on unreviewed or copied-only evidence, write `revision_requested`; do not promote.
- If the harness still stops at `compose_render_handoff`, report exact evidence; do not patch harness or write a dummy handoff.
- If the next blocker is story/human review, transcript review, legal/music review, UNKNOWN, REPAIR, rendered candidate missing, or rendered QA missing, stop and classify it separately.
- Do not render unless the harness no-render run returns `pass=true` and the work remains inside the fresh owner root. If rendering is attempted, it must be followed by rendered QA and no-skip trace in the same fresh root.
- Do not create `story_human_review_decision.json`, `human_transcript_review_decision.json`, legal/music approval artifacts, delivery packages, or formal `final.mp4` delivery claims.

## Delegated Decisions

- The worker may decide whether existing reviewed evidence is sufficient to produce a render-handoff contract.
- The worker may choose the exact fresh output root suffix.
- The worker may choose the internal shape of `render_handoff.json` beyond the required fields, as long as it is compatible with the existing harness and explicitly traceable to reviewed inputs.
- The worker may stop after no-render reaches `ready_for_render_rehearsal` without rendering if render inputs still need a separate render-owner round.

## Report Format

Start with `[WORKER REPORT - REVIEW MODE]`.

Include:

- output root and fresh run path
- prior blocker verification
- inventory of render-handoff inputs
- handoff decision status and reason
- `render_handoff.json` summary if written
- harness rerun result, trace depth, stage order, stop gate, and stop reason
- rendered QA/no-skip status if reached
- commands and exit codes
- deviations and stop-loss blockers
- advisory next recommended work
- `Final output prompt`: concise index only, not a report copy. Include report path, 3-5 must-read artifacts, 4-6 key claims, current blocker, product-level objective, scope/stop-loss, and next likely work. It must frame this report as unverified evidence and require claim/artifact verification.
