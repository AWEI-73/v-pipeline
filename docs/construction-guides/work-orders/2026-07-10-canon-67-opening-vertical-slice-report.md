[WORKER REPORT - REVIEW MODE]

# Canon 67 Opening Vertical Slice — Stop-Loss Evidence Report

## Disposition

**STOP-LOSS: BLOCKED.** The real candidate and all opening-specific technical
gates passed, but the required full suite exited `1` with two integration
failures that require edits outside the Work Order Owner Zone. Per the Work
Order, no waiver, QA relaxation, external-owner edit, further implementation
commit, delivery claim, or creative approval was made.

The last committed green checkpoint is `a7d0bb33 Render bounded edit decisions
to final mp4`. The later precision repair and Piece 5 implementation remain
uncommitted as preserved evidence. No Piece 5 or report commit was created.

## Commits And Changed Files

Committed construction checkpoints:

1. `fdbe086f Assign render handoff to main composition`
   - `docs/branch-contract-registry.json`
   - `docs/branch-contract-registry.md`
   - `tests/test_graduation_product_route_runner.py`
   - `tests/test_graduation_route_registry_consistency.py`
   - `video_pipeline_core/graduation_product_route_runner.py`
2. `2545b07d Compose and verify beat aligned cuts`
   - `tests/test_beat_cut_composer.py`
   - `tools/verify_beat_cut_alignment.py`
   - `video_pipeline_core/beat_cut_composer.py`
3. `c6f1a317 Carry opening graphics through edit decisions`
   - `examples/graduation_opening_slice_request.json`
   - `tests/test_compile_edit_decision_plan.py`
   - `tests/test_motion_graphics.py`
   - `video_pipeline_core/edit_decision_plan.py`
   - `video_pipeline_core/motion_graphics.py`
4. `a7d0bb33 Render bounded edit decisions to final mp4`
   - `tests/test_edit_decision_renderer.py`
   - `video_pipeline_core/edit_decision_renderer.py`

Uncommitted owner-zone construction evidence at Stop-Loss:

- `tests/test_compile_edit_decision_plan.py` (renderer settings carriage red/green repair)
- `tests/test_edit_decision_renderer.py` (non-frame-boundary duration regression)
- `tests/test_graduation_opening_slice.py` (lifecycle-frame acceptance regression)
- `tools/run_graduation_opening_slice.py`
- `video_pipeline_core/edit_decision_plan.py`
- `video_pipeline_core/edit_decision_renderer.py`
- `video_pipeline_core/graduation_opening_slice.py`
- this report

No existing user-owned dirty file was cleaned or overwritten.

## Red-First Evidence

Initial red command (exit `1`):

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_graduation_product_route_runner.GraduationProductRouteRunnerTest.test_music_subtitle_stage_does_not_consume_main_render_handoff tests.test_graduation_product_route_runner.GraduationProductRouteRunnerTest.test_compose_render_handoff_requires_ok_main_pipeline_ownership tests.test_graduation_route_registry_consistency.GraduationRouteRegistryConsistencyTest.test_registry_assigns_render_handoff_to_main_pipeline_composition tests.test_compile_edit_decision_plan.CompileEditDecisionPlanTest.test_carries_accepted_opening_graphics_and_generated_poetry_card tests.test_motion_graphics.MotionGraphicsTest.test_ffmpeg_libass_writes_progressive_typewriter_dialogues tests.test_beat_cut_composer.BeatCutComposerTest.test_composes_fifteen_distinct_assets_on_real_beat_anchors tests.test_edit_decision_renderer.EditDecisionRendererTest.test_renders_canonical_decision_with_owned_manifest_and_streams tests.test_graduation_opening_slice.GraduationOpeningSliceTest.test_acceptance_rejects_timing_only_title_qa_without_rendered_frames -v
```

Relevant red excerpts:

- Music stage: `AssertionError: True is not false` when only main-owned `render_handoff.json` was present.
- Compose stage: `AssertionError: True is not false` for a handoff lacking `ok=true`/`owner=main-pipeline`.
- Registry: `render_handoff.json` absent from Main Pipeline canonical outputs.
- Canonical composition: `overlays` was `[]` instead of the accepted opening overlay.
- Typewriter: expected three `Dialogue:` events, got one.
- Composer, renderer, and opening-slice modules were absent.

Additional red evidence:

- `tests.test_beat_cut_composer...test_verifier_cli_writes_a_failing_alignment_report_without_repairing_timeline` exited `1` before the verifier existed.
- Opening settings carriage red test exited `1`: `None != {'fps': 30, 'resolution': '1920x1080'}`.
- Duration precision red test exited `1`: `0.067... not less than or equal to 0.033333...`.

## Acceptance Command Evidence

| Command | Exit | Final output / tail | Status |
|---|---:|---|---|
| Required focused unittest command | 0 | `Ran 84 tests in 16.585s` / `OK` | PASS |
| `C:\Users\user\miniconda3\python.exe video_tools.py registry-audit --json` | 0 | `"finding_count": 0` | PASS |
| `C:\Users\user\miniconda3\python.exe video_tools.py interface-audit` | 0 | `"invalid_command_refs": []` | PASS |
| Required `tools\run_graduation_opening_slice.py ... --json` final attempt | 0 | `"pass": true`, `"title_lifecycle_contact_sheet": "run/lifecycle_contact_sheet.jpg"` | PASS |
| Required `tools\verify_beat_cut_alignment.py ... --json` | 0 | `"within_one_frame_ratio": 1.0`, `"pass": true` | PASS |
| Required `ffprobe ... final.mp4` | 0 | `"duration": "44.024000"`; H.264 video 1920x1080 + AAC audio | PASS |
| Required `tools\rendered_product_qa.py ... --json` | 0 | `"pass": true`, `"blocking": []`, `"warnings": []` | PASS |
| Required `video_tools.py asset-path-audit ... --strict --json` | 0 | `"strict_finding_count": 0` | PASS |
| `C:\Users\user\miniconda3\python.exe -m unittest discover -s tests` first attempt | 124 | local watchdog elapsed; child later ended without recoverable stdout/exit | UNKNOWN |
| `C:\Users\user\miniconda3\python.exe -m unittest discover -s tests` retry | 1 | `Ran 2599 tests in 997.139s` / `FAILED (failures=2, skipped=1)` | FAIL — Stop-Loss |
| Required `git diff --check` | 0 | no whitespace errors; only CRLF conversion warnings | PASS |

The two full-suite failures were:

1. `test_branch_registry_integrity.BranchRegistryIntegrityTest.test_stage_artifacts_in_dictionary`: `render_handoff.json` is now declared in Main Pipeline BUILD outputs but is absent from `docs/interface-contracts/pipeline-product-artifact-dictionary.json`, a file outside the Owner Zone.
2. `test_skill_tool_contracts.SkillToolContractsTest.test_audit_reports_clean_skill_tool_contracts`: `tools/run_graduation_opening_slice.py` and `tools/verify_beat_cut_alignment.py` are unowned until declared in `skills/**`, which is Forbidden Zone.

These are structural ownership/interface failures, not candidate-render failures. Repair would require the prohibited artifact dictionary and skills contract edits; therefore work stopped.

## Real Candidate Artifacts

Final technical-review output root:

- `C:\Users\user\Desktop\video_pipeline\.tmp\canon_67_opening_slice_acceptance\opening_slice_acceptance.json`
- `C:\Users\user\Desktop\video_pipeline\.tmp\canon_67_opening_slice_acceptance\creative_review_packet.md`
- `C:\Users\user\Desktop\video_pipeline\.tmp\canon_67_opening_slice_acceptance\source_provenance.json`
- `C:\Users\user\Desktop\video_pipeline\.tmp\canon_67_opening_slice_acceptance\beat_cut_alignment_report.json`
- `C:\Users\user\Desktop\video_pipeline\.tmp\canon_67_opening_slice_acceptance\rendered_qa\rendered_product_qa.json`
- `C:\Users\user\Desktop\video_pipeline\.tmp\canon_67_opening_slice_acceptance\run\edit_decision_plan.json`
- `C:\Users\user\Desktop\video_pipeline\.tmp\canon_67_opening_slice_acceptance\run\timeline_build.json`
- `C:\Users\user\Desktop\video_pipeline\.tmp\canon_67_opening_slice_acceptance\run\render_handoff.json`
- `C:\Users\user\Desktop\video_pipeline\.tmp\canon_67_opening_slice_acceptance\run\render_input_manifest.json`
- `C:\Users\user\Desktop\video_pipeline\.tmp\canon_67_opening_slice_acceptance\run\render_command_manifest.json`
- `C:\Users\user\Desktop\video_pipeline\.tmp\canon_67_opening_slice_acceptance\run\final.mp4`
- `C:\Users\user\Desktop\video_pipeline\.tmp\canon_67_opening_slice_acceptance\run\title_effect_lifecycle_qa.json`
- `C:\Users\user\Desktop\video_pipeline\.tmp\canon_67_opening_slice_acceptance\run\lifecycle_frames\`
- `C:\Users\user\Desktop\video_pipeline\.tmp\canon_67_opening_slice_acceptance\run\lifecycle_contact_sheet.jpg`

Preserved failed attempts:

- `C:\Users\user\Desktop\video_pipeline\.tmp\canon_67_opening_slice_acceptance_failed_settings_boundary\` — missing canonical settings boundary.
- `C:\Users\user\Desktop\video_pipeline\.tmp\canon_67_opening_slice_acceptance_failed_duration_alignment\` — pre-precision output duration `44.067` seconds.

## Rendered Technical Evidence

- `opening_slice_acceptance.json`: `pass=true`; `duration_sec=44.024`; duration tolerance is `0.033333...` seconds at 30fps.
- `ffprobe`: H.264 video at 1920x1080 and AAC audio; video/audio streams each report 44.000 seconds, container duration reports 44.024 seconds.
- Montage: 15 distinct accepted assets, 17 total timeline clips (title photo, generated black poetry card, 15 montage cuts).
- Beat alignment: 14 intended internal boundaries; 14 within one frame; ratio `1.0`; each measured delta is `0.0` frames; target timeline end is exactly `44.0` seconds.
- Rendered product QA: `pass=true`, zero blocking findings, and sampled frame/contact-sheet evidence exists under `rendered_qa/`.
- Lifecycle QA: `pass=true`, 12 rendered enter/hold/exit frames across title plus three poem lines, with `run/lifecycle_contact_sheet.jpg` as the contact sheet. A visual read-back was performed; it shows the photo/title progression and black poetry-card text frames. This is technical evidence only, not creative approval.
- Flags remain pinned: `human_creative_approval=false`; `final_delivery_claimed=false`.

## Provenance And Reference-Film Exclusion

`source_provenance.json` records 221 existing accepted non-reference assets,
15 selected montage assets, and `reference_film_selected_as_footage=false`.
The candidate timeline contains no `67期結訓影片-終.mp4` reference; all 16
non-generated selections (one title photo plus 15 montage photos) trace to
accepted catalog records. Direct read-back found:

- `reference_in_timeline=False`
- `non_generated_all_accepted=True`
- `montage_distinct_asset_count=15`

## Deviations, Skips, And Blockers

- Deviation: the first real run stopped before rendering because `settings` was not carried through the canonical edit-decision boundary. It was preserved, fixed by a red-green canonical field carriage repair, and rerun in a new fresh root.
- Deviation: the next real render passed rendered QA but produced `44.067` seconds. It was preserved; a non-frame-boundary red regression test led to one bounded final precision re-encode repair. The final candidate is within one frame.
- Deviation: the first full-suite invocation exceeded the local 10-minute watchdog, so its result is explicitly UNKNOWN rather than treated as a pass.
- Blocker: the second full-suite invocation failed on the external artifact dictionary and `skills/**` tool-ownership contracts. Both are Forbidden Zone; no repair was attempted.
- Skip: no delivery promotion, no PR/push, no human creative approval, no QA relaxation, no source-tree write, and no reference-film footage use.

## Exact Git Status At Stop-Loss

```text
 M AGENTS.md
 M tests/test_compile_edit_decision_plan.py
 M tests/test_edit_decision_renderer.py
 M video_pipeline_core/edit_decision_plan.py
 M video_pipeline_core/edit_decision_renderer.py
?? docs/construction-guides/2026-07-10-canon-67th-film-gap-table.md
?? docs/construction-guides/work-orders/2026-07-10-canon-67-opening-vertical-slice-report.md
?? docs/construction-guides/work-orders/2026-07-10-canon-67-opening-vertical-slice.md
?? r
?? supply_review.json
?? tests/test_graduation_opening_slice.py
?? tools/run_graduation_opening_slice.py
?? video_pipeline_core/graduation_opening_slice.py
```

The pre-existing dirty `AGENTS.md`, work order/gap-table files, and
`supply_review.json` were retained. `r` is an untracked test-side artifact
(`composited`) observed after the full suite and was not removed because it is
outside the Owner Zone.

## Final-Output Prompt

Treat this report and the candidate artifacts as **unverified technical
evidence**. Independently inspect the two Forbidden-Zone integration failures,
the final video/frame evidence, source provenance, and all acceptance outputs
before deciding whether to authorize the required dictionary/skills-contract
work and before any creative or delivery decision.
