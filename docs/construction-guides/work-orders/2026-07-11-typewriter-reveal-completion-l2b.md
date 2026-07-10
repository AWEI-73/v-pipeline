# Progressive Typewriter Completion + L2B Work Order

Status: **AUTHORIZED FOR FOCUSED TDD AND L2B**

## Goal And Authority

Close the verified public-capability gap blocking `l5_f01`, then apply the exact
approved lifecycle to a fresh L2 candidate and stop for owner taste review.

Read in order:

1. `AGENTS.md`
2. this work order — sole construction basis
3. `docs/superpowers/specs/2026-07-11-typewriter-reveal-completion-design.md`
4. `docs/superpowers/plans/2026-07-11-typewriter-reveal-completion.md`
5. the parent campaign work order
6. `skills/editing-loop-director.md`
7. current L2A proposal/report

Owner authorization for this work order:

```text
AUTHORIZE_TYPEWRITER_REVEAL_COMPLETE_TDD_AND_L2B
opening_title_text: start=3.5s, reveal_complete=9.0s, end=11.0s
```

This authorization does not grant final L2 taste, creative approval or delivery.

## Owner Zone

Production/test edits are limited to:

- `video_pipeline_core/edit_decision_renderer.py`
- `video_pipeline_core/motion_graphics.py`
- `tests/test_edit_decision_renderer.py`
- `tests/test_motion_graphics.py`

Experimental writes are limited to:

- `.tmp/editing_loop_certification_campaign/l2/**`
- `.tmp/editing_loop_certification_campaign/campaign_status.md`

One focused capability commit is required. Do not stage experimental artifacts.

## Forbidden Zone

- candidate_v2 and every pre-existing `.tmp` tree are read-only;
- do not edit compiler, Product Spec, Skill, registries, dictionaries, other
  production/tests, raw media or unrelated dirty-tree files;
- do not add `static_hold`, another overlay, a helper, renderer, schema version,
  route, driver or run-local script;
- do not run full suite, stage unrelated files, push or open a PR.

## Ordered Outcomes

1. Freeze candidate_v2/hash and current git status.
2. Execute Tasks 1–2 of the focused plan red-first.
3. Run only:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_motion_graphics tests.test_edit_decision_renderer tests.test_compile_edit_decision_plan -v
```

4. Commit only the four authorized production/test files.
5. Store the authorization verbatim under the L2 owner-gate directory.
6. Create `candidate_l2` through the repo-owned
   `video_pipeline_core.edit_decision_renderer.render_edit_decision` path.
7. Apply only the `opening_title_text` lifecycle:
   `start_sec=3.5`, `reveal_complete_sec=9.0`, `end_sec=11.0`.
8. Generate a machine-readable semantic diff proving no protected layer changed.
9. Read back ASS timing and produce review frames/dynamic evidence around all
   three lifecycle boundaries.
10. Run fresh rendered QA and final-product verify on candidate_l2.
11. Stop at `WAITING_OWNER_FINAL_L2_TASTE_VERDICT`.

## Acceptance

- Red evidence demonstrates the new tests failed for the intended missing field.
- Focused/adjacent command exits `0`; no full-suite claim is made.
- Legacy no-field timing test proves backward compatibility.
- Invalid completion values fail before render.
- Generated ASS full-title state begins at exactly `9.00s` and ends at `11.00s`.
- Fresh candidate has video+audio, expected duration and no rendered QA blocker.
- Candidate_v2 hash remains
  `EE6EFC6FE624A3CF20A0C8A616480FF63C7C04E250168D806E7DF3777C7DC3B6`.
- Semantic diff shows only the approved title lifecycle field/timing changed.
- `human_creative_approval=false`; `final_delivery_claimed=false`.

## Stop-Loss And Report

One repair attempt per LOCAL failure class. Stop on repeated failure, required
out-of-zone edit, hash drift, nonzero material focused test, renderer bypass or
semantic spill into a protected layer.

Update `campaign_status.md` with commit, red/green commands and exits, hashes,
artifacts, semantic diff, ASS timing read-back, QA results, deviations and exact
git status. No maturity/certification update before the owner final taste verdict.
