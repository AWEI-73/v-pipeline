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

## Branch Summary

| Branch | Owns | Key Outputs | Must Stop On | Returns To |
|---|---|---|---|---|
| Main Pipeline | Stage 0, route, BUILD eligibility, delivery promotion | `video_intent.json`, `segment_contract.json`, `delivery_requirements.json`, `final.mp4` | unresolved follow-up questions, unknown cursor, unresolved child contract, delivery gate block | child branches or delivery |
| Material Map | material truth, source understanding, scene-to-need edges, deltas | `project_material_map.json`, `material_delta.json`, `source_material_matrix.json`, `dialogue_edit_script.json`, `rough_cut_plan.json` | unreviewed scope, `await_map_review`, missing satisfies edges, unreviewed generated candidates | main route, story/structure, Workbench, Verify |
| Soundtrack Arranger | music/song/BGM planning, source/license, probe, Audio Director handoff | `soundtrack_plan.json`, `sound_license_manifest.json`, `soundtrack_probe_report.json`, `audio_mix_plan.json`, `audio_build_handoff.json` | missing license/source, reference-only song, unresolved speech preservation, failed audio acceptance | main route, Workbench, Verify |
| Subtitle / Voiceover | subtitle readability, narration provider, VoxCPM bridge, BUILD handoff | `subtitle_voiceover_handoff_acceptance.json`, `subtitle_voiceover_build_handoff.json`, `voiceover_provider_plan.json`, `narration_manifest.json`, `subtitles.srt` | missing captions, failed caption audit, missing narration audio, unavailable provider without fallback | main route, Workbench, Verify |
| Effect Factory | semantic effect translation, visual technique parameters, worker handoff, effect review | `visual_technique_plan.json`, `effect_contract.json`, `remotion_prompt_pack.json`, `remotion_effect_review.json`, `effect_handoff.json` | unconfirmed parameters, missing required effect evidence, unsupported backend, generic output | main route, Workbench, Verify |
| Workbench / Brownfield | draft-only patching, preview timeline edits, route-back handoff | `preview_timeline.json`, `timeline_patch.json`, `patched_draft_timeline.json`, `workbench_handoff.json`, `workbench_review_report.json` | stale material refs, canonical truth mutation, owner-less patch, caller expects `final.mp4` | owning branch or main route |
| Verify / Delivery Gate | fail-closed review, final evidence, package/promote decisions | `verify_result.json`, `delivery_gate.json`, `final_product_verify_bundle.json`, `verified_preview_package.json`, `verified_preview_review_decision.json` | missing/stale evidence, semantic gate fail, reviewer block | repair owner or delivery promotion |

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

## Design Boundary

The registry is a contract map, not a template library. It does not decide the
creative contents of a film, effect, soundtrack, or cut. It only makes branch
ownership, artifact writes, stop gates, and return routes explicit and
testable.
