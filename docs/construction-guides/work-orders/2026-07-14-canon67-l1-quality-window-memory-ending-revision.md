# Work Order: Canon 67 L1 quality ranking, source windows, and memory ending revision

## Goal and source

Apply the accepted decision in `docs/decisions/2026-07-14-canon67-teacher-all-or-none-memory-ending.md` to produce a proposed L1 v2 storyboard and a bounded seg10 effect preview. Do not render the full candidate.

Current evidence source:

- `.tmp/canon67_540s_route_acceptance/stage5/l1_owner_review/owner_review_summary.json`
- `.tmp/canon67_540s_route_acceptance/stage5/l1_picture_plan.json`
- `.tmp/canon67_540s_route_acceptance/stage3/project_material_map_l0_v1.json`

## Owner zone

- `video_pipeline_core/material_retrieval.py`
- `tests/test_material_retrieval.py`
- `tests/test_map_retrieval_wiring.py` only for a focused regression test directly required by this change
- `.tmp/canon67_540s_route_acceptance/stage4/segment_contract_v3.proposed.json`
- `.tmp/canon67_540s_route_acceptance/stage5/l1_revision_v2/**`
- `.tmp/canon67_540s_route_acceptance/stage5/effects/seg10_memory_ending/**`

## Read-only / forbidden zone

- All existing v1 Material Map, L1 plan, storyboard, ranking, verification, and source-media artifacts
- `skills/**`, registries, capability dictionaries, renderer code, subtitle/audio code, and `HANDOFF_CURRENT.md`
- No `rough_cut_plan.json`, full candidate, `final.mp4`, upload, stage, commit, or push

## Ordered outcomes

1. Freeze and verify current hashes. Preserve as before evidence: all 53 ranked candidates score only `need=4`, 30 selected videos start at zero, seg09 uses unresolved roster evidence, and seg10 contains five similar group images.
2. Red-first: add focused tests showing same-need direct/resolved/high-confidence evidence must outrank unresolved/support-only evidence. Preserve filename prior as non-admitting. If the existing ranker already satisfies a condition, record it rather than adding code.
3. Make the smallest green patch in `material_retrieval.py`. Keep need match as the admission gate; add only score-breakdown evidence needed to distinguish quality. Do not introduce a new ranker, schema, or route.
4. Write `segment_contract_v3.proposed.json` with the accepted 540-second table. Mark seg09 `deferred_all_or_none`, duration 0, `required_roster_count=13`, and owner-approved order/identity/source-hash as reopening gates.
5. Rebuild proposed selection using `rank_scenes`, `select_diverse_ranked_scenes`, and `plan_ranked_windows`. For long or ambiguous selected videos use the registered `source-highlight-plan` capability; do not hand-author zero starts. Preserve task causality inside technical sections even when visual families repeat.
6. Write `l1_picture_plan_v2.proposed.json`, ranking/window reports, and an ordered storyboard packet. Exclude the current seg09 source and every teacher/adviser card. Any selected `direct_story_evidence=false` or unresolved story function requires an explicit scarcity reason.
7. Use Effect Factory with the existing `memory_photo_wall` template and Remotion worker backend to create only a bounded 40-second seg10 preview and evidence. Required shape:
   - 0–8s: reviewed memory photos enter one by one;
   - 8–20s: photo cards accumulate with restrained depth and warm film/light-leak texture;
   - 20–32s: cards converge without covering faces;
   - 32–40s: one final group photograph, slow hold, then the two approved text lines.
   Negative rules: no unapproved names, no teacher roster, no fake departure footage, no rapid spinning, no blind pan, no face obstruction/cropping, no generic slideshow, no heavy fire/smoke.
8. Write `effect_design_map.json`, `effect_contract.json`, prompt pack, worker outputs, playable preview, contact-sheet evidence, effect review, and bounded effect handoff. The handoff must deny ownership of material truth, rough cut, final assembly, and final delivery.
9. Produce the v2 storyboard preview and owner verdict template. Stop at `WAITING_OWNER_L1_V2_STORYBOARD_AND_ENDING_EFFECT_VERDICT`.

## Acceptance

- Red test fails before the ranker patch; focused green tests exit 0 afterward.
- Existing `tests.test_material_retrieval`, `tests.test_picture_plan_retrieval_gate`, and relevant lightweight map-retrieval tests exit 0. Do not run the heavy real-render test class or the full suite.
- Frozen v1 hashes all match.
- Proposed duration ledger totals exactly 540 seconds; seg09 is 0 and seg10 is 40.
- No selected source has unresolved teacher/roster usage.
- Every proposed video window is in bounds and carries planner/highlight evidence; zero start requires explicit evidence that the accepted window begins at source zero.
- Storyboard and effect preview are playable and have no audio.
- Chinese JSON/Markdown text decodes as UTF-8 with no U+FFFD or suspicious repeated question marks.
- `git diff --check` exits 0.

## Stop-loss and report

One repair attempt per failure class. Stop at the last green state on owner-zone conflict, a repeated failure, required out-of-zone code, missing reviewed material refs, or unsupported Remotion capability. Report PASS/FAIL/UNKNOWN, exact commands and exit codes, changed files, artifacts/hashes, deviations, and blind spots. Keep `human_creative_approval=false` and `final_delivery_claimed=false`.
