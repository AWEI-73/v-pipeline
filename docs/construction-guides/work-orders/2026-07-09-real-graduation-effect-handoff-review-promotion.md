# Real Graduation Effect Handoff Review Promotion

## Goal

Clear the real graduation route's current `effect_handoff` blocker without skipping the route harness. Review the existing Effect Factory package as technical render evidence, write a fresh accept/revise/reject decision, and rerun the graduation route harness from a fresh run copy to prove whether the route gets past `effect_handoff` or stops at the next real blocker.

This is technical effect-handoff acceptance only. It is not final story approval, final creative approval, legal/music approval, or delivery approval.

## Owner Zone

- `.tmp/real_graduation_effect_handoff_review_promotion_*`
- `docs/construction-guides/work-orders/2026-07-09-real-graduation-effect-handoff-review-promotion-report.md`

## Forbidden Zone

- `.tmp/real_graduation_route_harness_to_render_rehearsal_20260709-001944/**`
- `.tmp/effect_factory_integration_completion_20260708-154117/**`
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

1. Verify the prior real-route blocker from:
   - `docs/construction-guides/work-orders/2026-07-08-real-graduation-route-harness-to-render-rehearsal-report.md`
   - `.tmp/real_graduation_route_harness_to_render_rehearsal_20260709-001944/no_render_out/graduation_product_route_harness_result.json`
   - `.tmp/real_graduation_route_harness_to_render_rehearsal_20260709-001944/no_render_out/pipeline_execution_trace.json`
   - `.tmp/real_graduation_route_harness_to_render_rehearsal_20260709-001944/run/effect_handoff.json`
2. Inventory the Effect Factory package from `.tmp/effect_factory_integration_completion_20260708-154117`, including `effect_line_review_packet.md`, `effect_review.json`, `effect_handoff.json`, `remotion_worker_outputs.json`, contact sheets, and keyframes.
3. Produce `effect_handoff_review_decision.json` in the fresh owner root with one status:
   - `accepted_for_render_rehearsal`
   - `revision_requested`
   - `rejected`
   - `insufficient_evidence`
4. If accepted, create a fresh run copy under the owner root and replace only that run-local `effect_handoff.json` with a promoted technical handoff that is clearly bounded to render rehearsal.
5. Rerun `tools/run_graduation_product_route.py --mode no-render` on the fresh run copy after acceptance, and record the new trace/result.
6. Do not render unless no-render reaches the render-rehearsal boundary with no human-review, legal/music, unknown, or repair blocker. If render is attempted, it must be through the route harness and must be followed by rendered QA and no-skip trace.
7. Write `final_artifact_check.json` covering prior-run immutability, decision status, harness trace depth/stage order, and whether rendered QA/no-skip were reached.

## Red-First Verification

- First run a read-only precheck that confirms the prior route currently stops at `effect_handoff` with `ready_for_human_review`; record its exit code and the observed stop gate.
- If the precheck cannot prove that blocker, stop and report `prior_blocker_not_reproducible`.

## Acceptance Commands

Use `C:\Users\user\miniconda3\python.exe`; do not use bare `python` or `pytest`.

- `C:\Users\user\miniconda3\python.exe -m unittest tests.test_graduation_product_route_runner tests.test_rendered_product_qa tests.test_no_skip_execution_trace` expected exit code `0`
- `C:\Users\user\miniconda3\python.exe tools\run_graduation_product_route.py --run "<fresh-run>" --source-root "C:\Users\user\Downloads\微電影素材\_整理後" --mode no-render --out-dir "<fresh-out>\no_render_out" --json` expected exit code `0` only after `accepted_for_render_rehearsal`; skip and explain for revise/reject/insufficient evidence
- `C:\Users\user\miniconda3\python.exe -c "<UTF-8 artifact check for generated JSON/Markdown>"` expected exit code `0`
- `git diff --check` expected exit code `0`; existing CRLF warnings may be reported

## Stop-Loss Limits

- If effect contact sheets/keyframes are missing, unreadable, or not mapped to opener/transition/title/closing intent, write `insufficient_evidence`; do not promote.
- If `effect_review.json` has blocking issues, write `revision_requested` or `rejected`; do not promote.
- If the harness still stops at `effect_handoff` after promotion, report the exact gate evidence; do not patch harness or gate semantics.
- If the next blocker is story/human review, legal/music review, source transcript review, UNKNOWN, REPAIR, or missing rendered candidate, stop and classify it separately.
- Do not create `story_human_review_decision.json`, `human_transcript_review_decision.json`, legal/music approval artifacts, or delivery packages.

## Delegated Decisions

- The worker may decide whether the existing effect evidence is technically acceptable for render rehearsal, but must cite artifact paths and reasons.
- The worker may choose the exact fresh output root suffix.
- The worker may choose the promoted run-local handoff shape only if it remains compatible with the existing harness and clearly says it is not final creative approval.
- The worker may choose not to render even if no-render passes, if any required render-facing evidence is still missing.

## Report Format

Start the report with `[WORKER REPORT - REVIEW MODE]`.

Include:

- output root and fresh run path
- prior blocker verification
- effect package inventory and reviewed evidence
- decision status and reason
- harness rerun result, trace depth, stage order, stop gate, and stop reason
- rendered QA/no-skip status if reached
- commands and exit codes
- deviations and stop-loss blockers
- next recommended work as advisory only
- a final section titled `Final output prompt` containing a standalone copy-paste prompt for the next manager/worker. It must include key factual results from this report, frame the report as unverified evidence, require verification of claims/artifacts, keep the product-level objective visible, classify blockers, respect scope/stop-loss, and align the next step with product-level done-evidence.
