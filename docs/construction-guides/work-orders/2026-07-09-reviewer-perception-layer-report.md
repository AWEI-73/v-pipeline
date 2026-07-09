[WORKER REPORT - REVIEW MODE]

## Summary

Built the reviewer perception layer as observation-only modules: sampling plan,
sampling coverage report, canonical montage wall sidecar, soundtrack sampling
anchors/spectrogram support, migrated contact-sheet call sites, and a frozen
verify/review compound vocabulary test.

Full repository acceptance is not green. The perception-chain acceptance command
passes, but `unittest discover` still fails on existing registry/dictionary/skill
ownership checks outside this work order's owner zone.

## Files Changed

- `video_pipeline_core/sampling_planner.py`
- `video_pipeline_core/sampling_coverage.py`
- `video_pipeline_core/montage_wall.py`
- `video_pipeline_core/soundtrack_probe.py`
- `video_pipeline_core/material_understanding_matrix.py`
- `video_pipeline_core/source_material_matrix.py`
- `video_pipeline_core/remotion_acceptance.py`
- `video_tools.py`
- `tools/generated_material_flow_acceptance.py`
- `tools/story_to_generated_material_e2e.py`
- `tools/srp_real67_review_demo.py`
- `tests/test_perception_chain.py`
- `tests/test_soundtrack_probe.py`
- `tests/test_next_action_verify_review_vocabulary.py`
- `docs/construction-guides/work-orders/2026-07-09-reviewer-perception-layer-report.md`

## Artifacts Created

- `sampling_plan.json` is produced by `video_pipeline_core.sampling_planner.write_sampling_plan`.
- `sampling_coverage_report.json` is produced by `video_pipeline_core.sampling_coverage.write_sampling_coverage_report` and `video_tools.py sampling-coverage`.
- Wall PNG plus `montage_wall.json` are produced by `video_pipeline_core.montage_wall.write_montage_wall` and `video_tools.py montage-wall`.
- Existing contact-sheet call sites now also create adjacent `.json` montage wall sidecars.
- Test-created artifacts were temporary fixture outputs under `%TEMP%`; no stable fixture render was kept.

## Commands And Exit Codes

- `C:\Users\user\miniconda3\python.exe -m unittest tests.test_perception_chain.PerceptionChainSmokeTest.test_planner_writes_contract_with_baseline_and_audio_reasons -v` -> exit 1 before Piece 1 implementation, then exit 0.
- `C:\Users\user\miniconda3\python.exe -m unittest tests.test_perception_chain.PerceptionChainSmokeTest.test_sampling_coverage_report_fails_closed_and_cli_writes_json -v` -> exit 1 before Piece 2 implementation, then exit 0.
- `C:\Users\user\miniconda3\python.exe -m unittest tests.test_perception_chain.PerceptionChainSmokeTest.test_chain_writes_sampling_coverage_and_montage_wall_artifacts -v` -> exit 1 before Piece 3 implementation, then exit 0.
- `C:\Users\user\miniconda3\python.exe -m unittest tests.test_soundtrack_probe.SoundtrackProbeTest.test_emits_sampling_anchors_and_optional_spectrogram -v` -> exit 1 before Piece 4 implementation, then exit 0.
- `C:\Users\user\miniconda3\python.exe -m unittest tests.test_perception_chain.PerceptionChainSmokeTest.test_existing_contact_sheet_helpers_write_canonical_sidecars -v` -> exit 1 before Piece 5 migration, then exit 0.
- `C:\Users\user\miniconda3\python.exe -m unittest tests.test_next_action_verify_review_vocabulary -v` -> exit 1 with current offender listed, then exit 0 after grandfather allowlist.
- `C:\Users\user\miniconda3\python.exe -m unittest tests.test_source_material_matrix -v` -> exit 0.
- `C:\Users\user\miniconda3\python.exe -m unittest tests.test_generated_material_flow_acceptance -v` -> exit 0.
- `C:\Users\user\miniconda3\python.exe -m unittest tests.test_story_to_generated_material_e2e -v` -> exit 0.
- `C:\Users\user\miniconda3\python.exe -m unittest tests.test_remotion_transition_acceptance -v` -> exit 0.
- `C:\Users\user\miniconda3\python.exe -m unittest tests.test_video_tools_command_catalog -v` -> exit 0 after local command classification fix.

## Acceptance Results

- `C:\Users\user\miniconda3\python.exe -m unittest tests.test_perception_chain -v` -> PASS, exit 0, 4 tests.
- `C:\Users\user\miniconda3\python.exe -m unittest discover -s tests` -> FAIL, exit 1, 2581 tests run, 5 failures, 1 skipped.

Failing full-discover tests:

- `test_branch_contract_registry.BranchContractRegistryTest.test_registry_has_required_branches_and_contract_fields`
- `test_product_artifact_dictionary_audit.TestProductArtifactDictionaryAudit.test_product_dictionary_audits_ok`
- `test_registry_audit.RegistryAuditCliTest.test_real_registry_passes`
- `test_skill_index.SkillIndexTest.test_registry_claimed_skills_have_same_owner`
- `test_skill_tool_contracts.SkillToolContractsTest.test_audit_reports_clean_skill_tool_contracts`

## Blockers / Stop-Loss Events

- Full acceptance is blocked by registry/dictionary/skill ownership failures involving `film-canon-product-route`, `docs/branch-contract-registry.json`, `docs/pipeline-decision-tree.md`, `skills/`, and unowned `tools/` entries. These paths are outside this work order's owner zone and docs/skills are forbidden except this report file.

## Deviations

- Added one extra local commit after the six piece commits: `Classify reviewer perception video_tools commands`. Reason: acceptance exposed unclassified `sampling-coverage` and `montage-wall` commands; this was fixable inside owner-zone file `video_tools.py` without touching `tool_command_catalog.py`.
- Did not edit `video_pipeline_core/tool_command_catalog.py` even though it is the normal catalog source, because it is outside the owner zone.
- Did not fix the remaining full-discover failures because they require forbidden docs/skills/registry/tool ownership edits.

## Advisory Next Work

- Run a separate registry/product-dictionary cleanup work order for the five remaining full-discover failures.
- Consider adding `sampling-coverage` and `montage-wall` to the canonical command catalog in a future owner-approved pass.
- Decide whether still-contact sidecars should be surfaced in higher-level matrix JSON for all consumers; source matrix now exposes `contact_sheet_index`, material matrix keeps the existing visual shape for compatibility.

## Final Output Prompt

Report path:
`docs/construction-guides/work-orders/2026-07-09-reviewer-perception-layer-report.md`

Must-read artifacts:
`video_pipeline_core/sampling_planner.py`, `video_pipeline_core/sampling_coverage.py`,
`video_pipeline_core/montage_wall.py`, `tests/test_perception_chain.py`,
`tests/test_next_action_verify_review_vocabulary.py`.

Key claims to verify:
The perception chain is deterministic and observation-only; planner, coverage,
and wall artifacts cross-reference each other; migrated contact-sheet call sites
produce canonical montage sidecars; no vocabulary file was modified for Piece 6.

Current blocker:
Full `unittest discover` remains red on registry/dictionary/skill ownership
checks outside this work order's owner zone.

Product-level objective:
Provide a canonical eye/ear perception chain for future reviewer skill
consumption without quality judgment or asset promotion.

Scope and stop-loss:
Treat this report as unverified evidence until the remaining full-suite blocker
is resolved by an owner-approved registry/docs/skills cleanup. Do not claim
whole-repo acceptance from the perception-chain pass alone.

Next likely work:
Create a separate work order to repair the film-canon route registry,
product artifact dictionary, skill index, and skill tool ownership contracts.
