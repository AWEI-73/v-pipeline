# Work Order: Phase 4 - Golden-Path Convergence Smoke

Date: 2026-07-03
Parent plan: `docs/construction-guides/2026-07-03-convergence-single-pipeline-plan.md`
Prerequisite: Phase 2.5 merged. (Phase 3 is NOT a prerequisite.)
Estimated effort: 1-2 days, four pieces, sequential.
This order allows bounded fixes to pipeline core modules (pieces 2-4). Every
fix must be test-first: commit contains the red test turned green, and the
diff to the core module is the minimum that turns it.

## Hard constraints for the smoke (all pieces)

- No network. No Pexels calls, no downloads, no provider calls.
- No real render. BUILD is exercised only through
  `python video_tools.py contract-dry-build <contract> --out-dir DIR`.
- Everything runs in a temp directory; the repo tree and `runs/` stay
  untouched after the test.
- Fixture source: `examples/genre_tests/stock_story_e2e/` (brief.json,
  blueprint.json, segment_contract.json, material_categories.json). Copy
  into the temp run dir; never mutate the fixture.

## Files you may create

- `video_pipeline_core/e2e_smoke.py`
- `tests/test_e2e_smoke.py`
- `video_tools.py`: new subcommand `e2e-smoke` (+ its one-line
  classification in `video_pipeline_core/tool_command_catalog.py` — same
  requirement Piece 3 of Phase 2 hit)

## Files you may modify (pieces 2-4 only, minimum diff, test-first)

- `video_pipeline_core/spec_review.py`, `video_pipeline_core/delivery_gate.py`,
  `video_pipeline_core/dashboard_state.py`, and at most one further core
  module per piece if the red test proves it owns the defect. Name the
  module and the reason in the execution report before editing it.

## Files you must NOT modify

- `runtime.py` CLI surface, skills, docs, registry, fixtures, all tests
  outside the files named above.
- Never weaken an existing test to make the smoke pass.

## Piece 1 - Smoke harness (no fixes yet)

1. Implement `video_pipeline_core/e2e_smoke.py` driving this chain in a temp
   run dir, reusing existing pipeline functions (do not reimplement logic):
   1. copy fixture brief + segment_contract into the run dir;
   2. run SPEC review (reuse `video_pipeline_core/spec_review.py`);
   3. run contract dry build via the same code path as
      `video_tools.py contract-dry-build`;
   4. simulate verify by writing a minimal passing `verify_result` artifact
      the same shape the real verifier emits (derive the shape from existing
      tests/fixtures, not by hand-crafting new fields);
   5. after each step, load dashboard state and record
      `state.json.next_action`.
   The smoke PASSES when the recorded next_action sequence reaches a
   terminal action (member of the vocabulary, no repeat-without-progress
   loop, no unknown action) and FAILS with the stalled action named.
2. Add `e2e-smoke` subcommand: `python video_tools.py e2e-smoke --case
   stock_story` (case name maps to the fixture dir; only this case for now).
   Exit 0 on pass, 1 on stall, with the step-by-step next_action trace
   printed either way.
3. `tests/test_e2e_smoke.py`:
   - `test_smoke_chain_reaches_terminal` — the happy path above.
   - Three defect probes, each written honestly against current behavior;
     mark with `unittest.expectedFailure` ONLY if it actually fails today:
     - `test_target_length_enforced`: a contract whose segment durations sum
       to far more than `target_length` must be flagged before/at dry build.
     - `test_render_output_path_does_not_stall`: a render artifact landing
       outside the canonical artifact path must still produce a non-stalled
       next_action.
     - `test_revise_director_routes_to_supply_revision`: the
       `revise:director` outcome must route to the supply-revision path,
       not a dead end.
   - In the execution report, state for each probe: passes today / xfail.
4. Acceptance: focused test green (xfails allowed); full suite green; CLI
   exits 0 on the happy path.
   Commit: `Add golden-path e2e smoke harness`.

## Pieces 2-4 - Turn each xfail green (one commit each)

Order: target_length (piece 2), render-path stall (piece 3),
revise:director routing (piece 4).

For each piece:

1. If piece 1 showed the probe already passes, record that in the report,
   skip the piece, and do not invent work.
2. Otherwise: remove the `expectedFailure` marker (red), implement the
   minimum fix in the owning core module (green), full suite green.
3. Behavior contracts:
   - Piece 2: exceeding `target_length` beyond tolerance is a SPEC-review /
     dry-build failure with an actionable message, not a silent pass. Take
     the tolerance from existing contract fields if one exists; otherwise
     use +/-10% and record that choice.
   - Piece 3: dashboard state must classify a present-but-mislocated render
     output as a repairable state with a vocabulary next_action, never a
     stall. Do not silently promote the mislocated file.
   - Piece 4: `revise:director` must hand off to the existing
     director-supply-revision mechanism (`director_supply_revision`); check
     git history for it before writing anything new.
   Commits: `Enforce target_length at spec review and dry build`,
   `Route mislocated render output to repairable state`,
   `Route revise:director through supply revision`.

## Evidence to hand back

- Diff per piece; focused + full-suite tails per piece.
- The printed next_action trace of a passing `e2e-smoke` run.
- Execution report appended under `## Phase 4`, including per-probe
  pass/xfail ground truth from piece 1 and any module ownership notes.
