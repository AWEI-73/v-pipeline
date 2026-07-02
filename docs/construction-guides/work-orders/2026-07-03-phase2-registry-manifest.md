# Work Order: Phase 2 - Registry Becomes the Executable Manifest

Date: 2026-07-03
Parent plan: `docs/construction-guides/2026-07-03-convergence-single-pipeline-plan.md`
Prerequisite: Phase 1 merged.
Estimated effort: 1 day, split into three pieces. Each piece is one
review-loop unit: implement -> tests green -> Codex review -> next piece.
Do NOT start piece N+1 before piece N is green.

## Files you may create

- `video_pipeline_core/next_action_vocabulary.py`
- `tests/test_branch_registry_integrity.py`
- `video_tools.py` new subcommand `registry-audit` (piece 3 only)

## Files you may modify

- `docs/branch-contract-registry.json` (piece 2 only)

## Files you must NOT modify

- `video_pipeline_core/dashboard_state.py` — read-only reference in this
  phase. If the vocabulary work reveals a typo'd or dead next_action literal,
  record it in the review notes; do not fix it here.
- `runtime.py`, delivery-gate code, `skills/`, all other docs.

## Piece 1 - Vocabulary module + integrity test (existing fields only)

1. Create `video_pipeline_core/next_action_vocabulary.py`:
   - Export `NEXT_ACTION_VOCABULARY: frozenset[str]`.
   - Seed = every string literal assigned to `next_action` in
     `video_pipeline_core/dashboard_state.py` (enumerate them by reading the
     source; there are literals in both kebab-case like `soundtrack-arrange`
     and snake_case like `fix_timeline_or_assembly` — keep both styles
     verbatim, no normalization) UNION every value in any `next_actions`
     array in `docs/branch-contract-registry.json`.
   - One comment line stating: this set is the closed vocabulary; adding a
     new next_action requires adding it here first.
2. Create `tests/test_branch_registry_integrity.py` with these test methods:
   - `test_registry_parses`: JSON loads, has `branches` list with the 7 known
     branch_ids: `main-pipeline`, `material-map`, `soundtrack-arranger`,
     `subtitle-voiceover`, `effect-factory`, `workbench-brownfield`,
     `verify-delivery`.
   - `test_skills_exist`: every path in every branch's `skills[]` exists.
   - `test_docs_exist`: every path in every branch's `docs[]` exists.
   - `test_registry_next_actions_in_vocabulary`: every `next_actions` value
     is in `NEXT_ACTION_VOCABULARY` (containment, one direction only).
   - `test_dashboard_state_literals_in_vocabulary`: regex-scrape
     `video_pipeline_core/dashboard_state.py` source for
     `next_action\s*=\s*"([^"]+)"` and assert every capture is in the
     vocabulary. Scrape the file as text; do not import-and-execute paths
     that need a live run folder.
3. Acceptance: `python -m unittest tests.test_branch_registry_integrity -v`
   green; full suite green.

## Piece 2 - Add stages[] to the registry

1. Extend each of the 7 branch entries in
   `docs/branch-contract-registry.json` with a `stages[]` array. Exact
   per-stage schema — these 7 keys, no more:

   ```json
   {
     "stage": "<short-id>",
     "skill": "skills/<file>.md",
     "artifacts_in": [],
     "artifacts_out": [],
     "gate": "<gate-name-or-null>",
     "next_actions_on_pass": [],
     "next_actions_on_fail": []
   }
   ```

2. Source of stage content: `docs/pipeline-decision-tree.md` section per
   branch + the branch's existing `canonical_outputs`. Where the prose tree
   and the registry disagree, the registry's existing fields win; flag the
   disagreement in review notes instead of inventing a resolution.
3. Every `artifacts_out` name must exist in
   `docs/interface-contracts/pipeline-product-artifact-dictionary.json`. If
   an artifact is genuinely canonical but missing from the dictionary, add it
   to the dictionary in the same commit and say so in review notes.
4. Extend the integrity test:
   - `test_stage_skills_exist`: every `stages[].skill` exists on disk.
   - `test_stage_artifacts_in_dictionary`: every `artifacts_out` name appears
     in the artifact dictionary.
   - `test_stage_next_actions_in_vocabulary`: pass/fail arrays ⊆ vocabulary.
   - New vocabulary entries needed by `stages[]` go into
     `next_action_vocabulary.py` in the same commit.
5. Acceptance: full suite green. Registry version field bumped to 2.

## Piece 3 - registry-audit command

1. Add `registry-audit` subcommand to `video_tools.py`:
   - Loads the registry and `docs/pipeline-decision-tree.md`.
   - Checks: every branch_id appears as a heading or explicit label in the
     decision tree; every gate named in `stages[].gate` appears somewhere in
     the tree prose; report any tree section heading that names a branch with
     no registry entry.
   - Exit 0 when clean; exit 1 with a line-per-finding report on drift.
   - Pure read-only: writes nothing except optional
     `docs/generated/registry-audit-report.md` behind a `--write-report`
     flag.
2. Add `tests/test_registry_audit.py`: run the audit in-process against the
   real files (must pass), then against a temp-copied registry with one
   seeded fake branch_id (must fail with exit 1).
3. Acceptance: `python video_tools.py registry-audit` exits 0; full suite
   green.

## Out of scope for this order

- Renaming or moving any skill file (that is Phase 3, and it depends on this
  order's tests existing first).
- Normalizing next_action naming style.
- Changing what dashboard_state emits.

## Evidence to hand back per piece

- New/changed file diff.
- `python -m unittest tests.test_branch_registry_integrity -v` output.
- Full-suite tail (`python -m unittest discover -s tests`) showing OK count.
