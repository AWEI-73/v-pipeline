# Decision-Tree Orphan Re-Homing

Date: 2026-07-09
Status: in progress (Claude executing, not delegated)

## Goal

Close the pipeline's registration closed loop so that no important node is an
orphan. Concretely: make `tests/test_branch_registry_integrity` green and drive
`tools/orphan_audit.py` `candidate_tools` to zero (only the intentional
`skills/INDEX.md` catalog may remain), without changing any pipeline behaviour.

This is a registration/consistency pass, not a feature change. The functional
code was already banked on branch `backfill/graduation-route-rehoming`
(commits `37003d1b`, `ce05e0f7`, `4d9462d3`). 201 targeted feature tests are
green; only registry-integrity was red — including at HEAD, because
`film-canon-product-route` was committed as a branch but the vocabulary,
artifact dictionary, and integrity test were never updated to match.

## Principle (why this is the fix, not more patching)

The pipeline already has three registration surfaces:

- `video_pipeline_core/node_registry.py` — the 14-node main state machine
  (`runtime.py`), each node with `verify_fn` (mechanical verify).
- `video_pipeline_core/reviewer_registry.py` — 9 reviewer roles +
  `validate_review_artifact()` (the agentic-review signature contract).
- `docs/branch-contract-registry.json` — the decision-tree registry (8
  branches), guarded by `tests/test_branch_registry_integrity`.

Horizontal **craft branches** (material-map, soundtrack-arranger,
subtitle-voiceover, effect-factory, verify-delivery) own reusable capability
and their own gates. Vertical **product routes** (film-canon-product-route,
workbench-brownfield) compose the craft branches; they must not re-implement a
craft branch's gate. The graduation route grew its gate tools on a hardcoded
harness stage list instead of registering them into the craft branch that owns
them — that is the orphan source.

## Evidence (as of this work order)

- `orphan_audit` `candidate_tools` = 10, all graduation gate tools.
- `test_branch_registry_integrity` fails 5 tests: stale 7-branch expectation,
  56 unregistered `next_action` literals (registry + stage + core code), and a
  set of stage `artifacts_in/out` values not in the artifact dictionary — of
  which ~26 are real artifacts and ~7 are prose that leaked into the artifact
  fields.

## Owner Zone

- `video_pipeline_core/next_action_vocabulary.py`
- `docs/branch-contract-registry.json`
- `docs/interface-contracts/pipeline-product-artifact-dictionary.json`
- `tests/test_branch_registry_integrity.py` (only the stale expected branch set)
- `tools/orphan_audit.py` (only to honor branch-level `tools` during ref
  collection)
- `docs/pipeline-decision-tree.md`, `docs/effect-factory-route.md` (owner-tool
  references only)
- this work-order file

## Forbidden Zone

- Any gate tool's behaviour, any `verify_fn`, any `.mp4`/render path.
- `.tmp/**`, `deliveries/**`, `output/**`, `.env`, provider runtimes.
- Do not invent new next_actions or artifacts to make tests pass — only
  register ones already used by committed code/registry, and fix genuine
  malformed entries.

## Tasks

### T1 — Fix the stale integrity test
`tests/test_branch_registry_integrity.test_registry_parses` expects 7 branches.
Add `film-canon-product-route` so the expected set matches the 8 real branches.

### T2 — Register the 56 missing next_actions
Add every literal below to `NEXT_ACTION_VOCABULARY` (closed frozenset). These
are already used by committed registry entries and `video_pipeline_core/*.py`:

```
build_subtitle_audio_alignment_report, confirm_training_catalog_assignments,
connect_valid_music_source, create_rendered_product_qa_owner_tool,
discover_source_root_music, dispatch_production_worker, dispatch_voiceover_voxcpm,
do_not_assemble_final_media, document_music_source_license_or_usage,
human_review_graduation_story_shell, human_review_story_to_material_map,
human_transcript_review, install_or_connect_voxcpm_runtime,
label_editorial_captions_or_repair_subtitles, map_missing_story_beats_to_material,
map_story_beats_to_material, preserve_source_speech_or_write_rejection_report,
probe_supervisor_source_speech, provide_narration_manifest, ready_for_render_rehearsal,
regenerate_readiness_from_decision_path, regenerate_script_utf8,
regenerate_subtitle_audio_alignment_utf8, remix_with_preserved_source_speech,
repair_effect_director_findings, repair_montage_design, repair_or_complete_upstream_gate,
repair_product_route, repair_rejected_story_material_mapping, repair_source_speech_evidence,
repair_source_speech_subtitles, repair_story_to_final_alignment, repair_subtitle_audio_alignment,
repair_title_effect_lifecycle, repair_voiceover_leadin, repair_voiceover_output,
repick_visual_material, rerun_voiceover_with_voxcpm, retarget_opening_or_closing_story,
return_to_story_or_material_map, revise_story_material_mapping, route_trace_complete,
route_voiceover_voxcpm_or_attach_no_narration_approval, run_independent_voiceover_asr,
run_no_skip_execution_trace, run_rendered_product_qa, run_visual_selection_gate,
run_visual_selection_review, run_voiceover_output_probe, run_voxcpm_runtime_check,
select_valid_delivery_music_source, write_montage_design_plan,
write_product_route_review_decision, write_source_speech_rejection_evidence,
write_title_effect_lifecycle_plan, write_visual_selection_review
```

### T3 — Fix prose that leaked into stage artifact fields
In `docs/branch-contract-registry.json`, these `artifacts_in`/`artifacts_out`
values are prose, not artifacts. Replace with the real artifact name or move to
the correct semantic field:
```
"decision path when review decision was written in a prior folder"
"fixture source tree or read-only real source metadata"
"film_type"
"graduation film direction"
"product route dry-run artifacts"
"story_to_material_map.json or render-facing visual selections"
"visual_selection_review.json when explicit visual review exists"
```

### T4 — Register the ~26 real artifacts in the dictionary
Add dictionary entries (`artifact_name`, `owner_branch`, `purpose`, minimal
`functional_parameters`) for the real artifacts. Owner mapping:
- **film-canon-product-route**: film_canon.json, graduation_film_canon.json,
  film_blueprint.json, graduation_film_blueprint_A.json, graduation_film_blueprint_B.json,
  catalog_map.json, reviewed_catalog_map.json, training_catalog_map.real_source.json,
  story_shell.json, story_shell_A.json, story_shell_B.json, story_retarget_diff_A_to_B.json,
  story_material_planning_handoff.json, product_route_review_decision.json,
  product_route_review_packet.json, production_readiness_gate.json,
  production_readiness_plan.json, production_worker_handoff_prompt.md, review_packet.json,
  graduation_real_source_review_packet.json, visual_selection_candidates.json,
  visual_selection_gate.json, visual_selection_review.json
- **subtitle-voiceover**: audio_subtitle_review_handoff.json, audio_subtitle_review_requirements.json
- **effect-factory**: opener_closer_design_handoff.json

### T5 — Re-home the 10 orphan tools into their craft branch
Add a branch-level `tools` array to two branches, and make `orphan_audit`
honor branch tools (add `refs.update(branch.get("tools", []))` in
`collect_direct_refs`).
- **subtitle-voiceover** (7): agent_transcript_repair, independent_voiceover_asr_qa,
  source_speech_subtitle_qa, voiceover_leadin_qa, voiceover_output_qa,
  voxcpm_leadin_diagnostic, write_human_transcript_review_decision
- **effect-factory** (3): effect_director_review, montage_design_review,
  title_effect_lifecycle_qa

(Confirm `montage_design_review` really belongs to effect-factory vs
main-pipeline editorial before wiring; adjust if its module purpose says
otherwise.)

## Acceptance Commands

Use `C:\Users\user\miniconda3\python.exe`.

- `... -m unittest tests.test_branch_registry_integrity` → exit 0.
- `... tools/orphan_audit.py --json-only` then assert `candidate_tools` is `[]`
  (or only `skills/INDEX.md` for skills) → exit 0.
- `... -m unittest tests.test_pipeline_home tests.test_graduation_product_route_runner`
  → exit 0 (no regression in state-machine detection).
- `git diff --check` → exit 0 (existing CRLF warnings only).

## Stop-Loss

- If a missing next_action or artifact does not actually appear in committed
  code/registry, do NOT register it — report it as a real dangling reference.
- If a tool's true owner branch is ambiguous, stop and flag rather than guess.
- Do not touch gate behaviour or verify_fns.
