# Work Order: Canon 67 grilling transfer v2

Date: 2026-07-18
Owner: `main-pipeline` integrator
Basis: `2026-07-18-canon67-grilling-stage3-5-transfer-test.md`

## Goal

Re-run the bounded Stage 0–2 → Stage 3 transfer after the semantic placeholder
guard and the registered editorial-to-retrieval adapter were added. Prove that
the owner decisions survive into a real ranker-backed paper edit. This is still
a sandbox transfer test; do not render a final candidate or claim delivery.

## Owner zone

Only write:

`.tmp/canon67_grilling_stage3_5_transfer_v2/**`

Everything else is read-only, including the prior v1 sandbox, source media,
accepted maps, production code, tests, Skills, registry, docs, Git index/history,
and campaign state. Do not commit, stage, push, upload, or mutate source media.

## Ordered work

1. Re-read the v1 frozen interaction answer sheet and create fresh Stage 2
   proposal artifacts. Use real decision text; generic values such as
   `owner-approved evidence statement`, `TBD`, or `placeholder` are invalid.
2. Run the public Stage 2 validator. It must exit 0 and its compaction audit
   must map each decision to concrete downstream values, not only filenames.
3. Build Stage 3 selections from the public ranker. Invoke
   `tools/picture_plan_retrieval_report.py` with
   `--evidence-map stage2/evidence_need_map.proposed.json`; do not copy the v1
   picture plan or hand-pick around Top-K.
4. Produce Stage 3 coverage/rejection artifacts and stop for integrator review.

## Acceptance

- Stage 2 validator: exit 0, `ready_for_stage3=true`.
- No placeholder marker in required story, segment, or evidence text.
- Every `N_*` reference in the segment contract resolves to an entry in the
  evidence-need map; dangling need IDs fail closed.
- Retrieval report: exit 0, adapter metadata present, selected clips in
  role-specific Top-K, zero overrides.
- Focused tests: `tests.test_editorial_ambiguity` and
  `tests.test_picture_plan_retrieval_gate` exit 0.
- `tools/skill_tool_contract_audit.py --json` exit 0; `git diff --check` exit 0.
- All source hashes and frozen inputs match; pre/post Git status identical.

## Stop-loss

One LOCAL correction per failure class. On recurrence, stop at the last green
state and write `final/factory_gap.json`. Never add a private crosswalk,
manual override, or stale-plan reuse.

Keep `human_creative_approval=false` and `final_delivery_claimed=false`.

Legal success state:

`WAITING_INTEGRATOR_CANON67_GRILLING_STAGE3_TRANSFER_V2_REVIEW`
