# Work Order: Phase 2.5 - Registry Manifest Hardening

Date: 2026-07-03
Parent plan: `docs/construction-guides/2026-07-03-convergence-single-pipeline-plan.md`
Prerequisite: Phase 2 merged (commits a1d6a7ea, c5b9585f, 01deaaef).
Origin: Phase 2 review findings. Both findings trace to under-specification in
the Phase 2 work order, not to construction errors. Incremental fix; no revert.
Estimated effort: 0.5 day, two pieces, sequential.

## Files you may modify

- `docs/branch-contract-registry.json`
- `video_pipeline_core/next_action_vocabulary.py`
- `tests/test_branch_registry_integrity.py`

## Files you must NOT modify

- `video_pipeline_core/dashboard_state.py`, `video_pipeline_core/delivery_gate.py`,
  and every other emitter module — read-only. If a scraped literal looks like a
  typo or dead action, record it in the execution report; do not fix emitters.
- `docs/interface-contracts/pipeline-product-artifact-dictionary.json` — the
  product dictionary's narrow scope (decision-plan artifacts) is deliberate;
  do not widen it.
- Skills, runtime.py, video_tools.py, all other docs.

## Piece 1 - Validate stage artifacts against both dictionaries; restore the canonical spine

Problem found in review: `stages[].artifacts_out` was fitted to the 8-entry
product dictionary, so the manifest omits the pipeline's canonical spine
(`video_intent.json`, `segment_contract.json`, `final.mp4` — all present in
`docs/interface-contracts/pipeline-api-dictionary.json`, which the Phase 2
order failed to mention).

1. In `tests/test_branch_registry_integrity.py`, change the artifact check to
   validate `artifacts_out` (and now also `artifacts_in`) against the UNION of:
   - `pipeline-product-artifact-dictionary.json` `artifacts[].artifact_name`;
   - every artifact name mentioned in
     `pipeline-api-dictionary.json` (extract the name set from its
     `interfaces` structure; inspect the file and pick the narrowest field
     that yields artifact filenames).
2. Enrich the registry stages so each branch's stages mention the canonical
   artifacts that gate it. Minimum required additions:
   - `main-pipeline` stage0: `artifacts_out` gains `video_intent.json`;
     add one stage `contract-compile` between stage0 and build-eligibility
     with `artifacts_out: ["segment_contract.json"]`, skill
     `skills/spec-contract.md`, gate `spec-review`.
   - `main-pipeline` build-eligibility: `artifacts_out` gains nothing new,
     but `verify-delivery` branch's final stage must list `final.mp4` and
     `final_promotion_report.json` in `artifacts_out` if the API dictionary
     names them (verify before adding; if a name is absent from both
     dictionaries, record it in the report instead of adding it).
   - Source for any further enrichment: each branch's own
     `canonical_outputs` — a stage may only list artifacts already present
     in that branch's `canonical_outputs`.
3. Bump registry `version` to 3.
4. Acceptance: focused test green; full suite green;
   `python video_tools.py registry-audit` still exits 0.

## Piece 2 - Close the vocabulary over all emitters

Problem found in review: the scrape covers only `dashboard_state.py` (24
assignment sites), but `video_pipeline_core/` has ~228 `next_action`
assignment/dict-literal sites across 44 files (`delivery_gate.py` alone has
73). Known escapee: `effect_factory_boundary.py` emits
`revise_effect_factory_contract`, which is not in the vocabulary.

1. In `tests/test_branch_registry_integrity.py`, extend
   `test_dashboard_state_literals_in_vocabulary` (rename to
   `test_core_next_action_literals_in_vocabulary`) to scrape every `*.py`
   file directly under `video_pipeline_core/` (not subpackages, not `.html`)
   with BOTH patterns:
   - `next_action\s*=\s*"([^"]+)"`
   - `"next_action"\s*:\s*"([^"]+)"`
2. Run the scrape, collect every literal not yet in
   `NEXT_ACTION_VOCABULARY`, and add them all to
   `video_pipeline_core/next_action_vocabulary.py` verbatim (no
   normalization, no dedup across naming styles).
3. In the execution report, list: the full set of newly added literals, and
   any that look like typos, dead code, or style duplicates (for example the
   pre-existing `effect-factory-contract` vs `effect_factory_contract`
   pair). Flag only; do not change them.
4. Acceptance: focused test green; full suite green.

## Out of scope

- Normalizing kebab/snake naming (deferred to a dedicated decision after
  Phase 4).
- Adding more stages beyond Piece 1's minimum (stage granularity will be
  driven by Phase 4's smoke requirements).
- Touching any emitter module.

## Evidence to hand back

- Diff per piece, committed separately:
  - Piece 1: `Validate stage artifacts against both dictionaries`
  - Piece 2: `Close next_action vocabulary over core emitters`
- `python -m unittest tests.test_branch_registry_integrity -v` output.
- Full-suite tail showing OK count.
- Updated execution report appended to
  `docs/construction-guides/work-orders/2026-07-03-phase1-2-execution-report.md`
  under a new `## Phase 2.5` heading.
