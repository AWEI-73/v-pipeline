# Hermes Branch Contract Registry

Status: current MVP branch contract index

This file summarizes `docs/branch-contract-registry.json`. The JSON file is the
machine-readable source for branch ownership checks. This Markdown file is the
operator-facing short map.

Use this registry after `RUNBOOK.md` chooses a route and before dispatching a
worker. It answers five questions:

1. Who owns this work?
2. What artifacts may that owner write?
3. What evidence must exist before the branch can return?
4. What must stop the branch?
5. Where does the branch return?

## Global Rules

- Existing run state wins: inspect `tools/pipeline_home.py` before writing.
- Whole-video requests enter Stage 0 first.
- Side branches are child lanes unless the request is bounded branch-only work.
- Branch outputs are not canonical delivery until the owning gate accepts them.
- Delivery readiness is decided by delivery gate evidence, not
  `verify_result.pass` alone.
- Rendered rehearsal or verified preview candidates must carry
  `pipeline_execution_trace.json` and `no_skip_contract_decision.json`; copied
  or run-local self-authored gate JSON cannot clear preview verification.

## Branch Summary

| Branch | Owns | Key Outputs | Must Stop On | Returns To |
|---|---|---|---|---|
| Main Pipeline | Stage 0, route, BUILD eligibility, delivery promotion | `video_intent.json`, `segment_contract.json`, `delivery_requirements.json`, `final.mp4` | unresolved follow-up questions, unknown cursor, unresolved child contract, delivery gate block | child branches or delivery |
| Material Map | material truth, source understanding, scene-to-need edges, deltas | `project_material_map.json`, `material_delta.json`, `source_material_matrix.json`, `dialogue_edit_script.json`, `rough_cut_plan.json` | unreviewed scope, `await_map_review`, missing satisfies edges, unreviewed generated candidates | main route, story/structure, Workbench, Verify |
| Soundtrack Arranger | music/song/BGM planning, source-root music discovery, human-declared music-use basis, source/license evidence, probe, Audio Director handoff | `soundtrack_plan.json`, `music_source_candidates.json`, `sound_license_manifest.json`, `soundtrack_probe_report.json`, `audio_mix_plan.json`, `audio_build_handoff.json` | missing source evidence or music-use basis, reference-only song, missing file/probe/vocal clearance, unresolved speech preservation, failed audio acceptance | main route, Workbench, Verify |
| Subtitle / Voiceover | subtitle readability, narration provider, VoxCPM bridge, BUILD handoff | `subtitle_voiceover_handoff_acceptance.json`, `subtitle_voiceover_build_handoff.json`, `voiceover_provider_plan.json`, `narration_manifest.json`, `subtitles.srt` | missing captions, failed caption audit, missing narration audio, unavailable provider without fallback | main route, Workbench, Verify |
| Effect Factory | semantic effect translation, visual technique parameters, worker handoff, effect review | `visual_technique_plan.json`, `effect_contract.json`, `remotion_prompt_pack.json`, `remotion_effect_review.json`, `effect_handoff.json` | unconfirmed parameters, missing required effect evidence, unsupported backend, generic output | main route, Workbench, Verify |
| Workbench / Brownfield | draft-only patching, preview timeline edits, route-back handoff | `preview_timeline.json`, `timeline_patch.json`, `patched_draft_timeline.json`, `workbench_handoff.json`, `workbench_review_report.json` | stale material refs, canonical truth mutation, owner-less patch, caller expects `final.mp4` | owning branch or main route |
| Verify / Delivery Gate | fail-closed review, final evidence, rendered product QA, package/promote decisions | `verify_result.json`, `delivery_gate.json`, `video_only_delivery_waiver.json`, `final_product_verify_bundle.json`, `verified_preview_package.json`, `verified_preview_review_decision.json`, `story_human_review_decision.json`, `agent_transcript_repair_suggestions.json`, `subtitles.draft.srt`, `human_transcript_review_decision.json`, `voiceover_output_qa.json`, `voiceover_leadin_qa.json`, `voxcpm_provider_leadin_diagnostic.json`, `lead_in_trim_probe.json`, `provider_leadin_classification.json`, `title_effect_lifecycle_qa.json`, `source_speech_subtitle_qa.json`, `pipeline_execution_trace.json`, `gate_authenticity_audit.json`, `rendered_product_qa.json`, `no_skip_contract_decision.json` | missing/stale evidence, semantic gate fail, reviewer block, visible video-only limitation, unresolved human story review, unresolved human transcript review, voiceover style/control leakage, voiceover lead-in mismatch, unresolved VoxCPM provider lead-in classification, persistent title/effect overlays, incomplete source-speech subtitle coverage, missing pipeline execution trace, copied/run-local/unknown gate artifact, missing rendered product QA frame evidence | repair owner or delivery promotion |
| Film Canon Product Route | registered film canon selection, pre-render story shell/catalog dry-run, visual-selection confirmation, product-route readiness gate, thin route execution harness | graduation artifacts or common `film_canon.json`, `film_blueprint.json`, `story_shell.json`, `catalog_map.json`, `review_packet.*`, `product_route_review_decision.json`, `reviewed_catalog_map.json`, `visual_selection_gate.json`, `production_readiness_gate.json`, `pipeline_execution_trace.json`, `graduation_product_route_harness_result.json` | unknown film type, render requested, token-only sensitive visual selection, non-human approval treated as ready, pending review counted as missing, revision/rejected routed to production, missing human-confirmation flags, harness stop-loss gate | story/product review or production worker handoff |

## How To Use

1. Read `RUNBOOK.md`.
2. If a run exists, run:

   ```powershell
   python tools\pipeline_home.py --run RUN_DIR --json
   ```

3. Use `docs/pipeline-decision-tree.md` to choose the current owner.
4. Check `docs/branch-contract-registry.json` for the owner branch:
   - `entry_conditions`
   - `required_inputs`
   - `canonical_outputs`
   - `handoff_outputs`
   - `stop_gates`
   - `forbidden_writes`
   - `return_to`
5. Dispatch only the bounded owner. Stop at the first gate that applies.

For scripted story delivery, write `story_human_review_decision.json` with
`tools\write_story_human_review_decision.py`; do not hand-edit the decision
artifact. Only `--reviewer human` decisions may clear
`story_human_review_required`.

For film-canon product routes, write `product_route_review_decision.json` with
`tools\write_product_route_review_decision.py`, then regenerate readiness with
`tools\film_canon_readiness.py --decision-path ...`. This approval only clears
the product-route readiness gate; it is not final story or delivery approval.
Use `tools\run_graduation_product_route.py` to execute the locked graduation
route checks without creating a new pipeline. It records
`pipeline_execution_trace.json` and stops at the first upstream owner gate.
For graduation render-facing visual selections, run
`tools\visual_selection_gate.py`. Token/folder/path matches remain candidates
until `visual_selection_review.json` records accepted visual evidence for the
sensitive beat.
Write that review artifact with `tools\write_visual_selection_review.py`; the
writer only records visual-selection review and does not clear story, delivery,
or legal/music approval.

For final-candidate QA hardening, run:

- `tools\voiceover_output_qa.py` to fail closed on voiceover style/control
  leakage or missing output probe evidence.
- `tools\title_effect_lifecycle_qa.py` to require title/effect start/end timing
  and evidence that cards clear before the next section.
- `tools\source_speech_subtitle_qa.py` to require source-speech subtitle later
  coverage or an explicit human transcript review route.
- `tools\independent_voiceover_asr_qa.py` to require independent ASR evidence
  for generated voiceover/final narration; provider manifest text alone cannot
  clear voiceover output QA.
- `tools\agent_transcript_repair.py` to convert ASR cues into
  `agent_transcript_repair_suggestions.json` and `subtitles.draft.srt`.
  Agent suggestions are draft-only and require
  `human_transcript_review_decision.json` before transcript approval.
- `tools\voiceover_leadin_qa.py` to compare expected narration with
  independent ASR and block extra spoken lead-in tokens before the script.
- `tools\voxcpm_leadin_diagnostic.py` to diagnose repeated VoxCPM lead-in
  artifacts with a provider matrix, trim probes, and
  `provider_leadin_classification.json`. Do not assemble final media from this
  diagnostic; route back to voiceover repair first.
- `tools\effect_director_review.py` to review actual frame/video evidence for
  lingering overlays, obstruction, composition, style match, and title
  disappearance.
- `tools\montage_design_review.py` to require opener/MV montage story role,
  shot functions, timing, title sync, and transition rationale.
- `tools\no_skip_execution_trace.py` to audit rendered rehearsal/preview
  candidates. It classifies gate artifacts as pipeline-tool generated,
  run-local generated, copied from prior, missing owner tool, or unknown, and
  blocks preview verification when `pipeline_execution_trace.json` or rendered
  product QA frame/contact-sheet evidence is missing.
- `tools\rendered_product_qa.py` to inspect rendered candidates with ffprobe
  and sampled frame/contact-sheet evidence before no-skip trace.

## Design Boundary

The registry is a contract map, not a template library. It does not decide the
creative contents of a film, effect, soundtrack, or cut. It only makes branch
ownership, artifact writes, stop gates, and return routes explicit and
testable.
