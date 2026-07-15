<!-- DOCUMENT_ROLE: CURRENT_HANDOFF -->

# Current Handoff: Hermes Video Pipeline

Read `RUNBOOK.md` first for the operational entry, then use this handoff for
the current machine-readable work pointer.

<!-- HANDOFF_STATE_START -->
{
  "artifact_role": "current_handoff_state",
  "version": 1,
  "updated_at": "2026-07-15T22:35:09+08:00",
  "state": "WAITING_OWNER_CANON67_ALL_SEGMENT_EDITORIAL_REVIEW",
  "active_work_order": "docs/construction-guides/work-orders/2026-07-15-canon67-all-segment-editorial-calibration-long-task.md",
  "active_spec": ".tmp/canon67_540s_route_acceptance/stage1/story_soul_blueprint.json",
  "active_skill": "skills/video-pipeline-route.md",
  "active_run_root": ".tmp/canon67_540s_route_acceptance",
  "authoritative_state_artifact": ".tmp/canon67_540s_route_acceptance/accepted_chain/revision_0009.json",
  "authoritative_state_sha256": "fa341915cd45a5fe1670522b95b8a45bb94314c8835ece6d0107d196a74839a4",
  "authoritative_state_field": "revision_id",
  "campaign_status_artifact": ".tmp/canon67_540s_route_acceptance/campaign_status.json",
  "campaign_status_field": "state",
  "next_actions": [
    "integrator_review_canon67_all_segment_editorial_state",
    "owner_review_canon67_all_segment_editorial_packet"
  ],
  "do_not_do": [
    "do_not_reuse_canon68_proxy_coverage_as_pass_evidence",
    "do_not_use_reference_or_canon66_media_as_source",
    "do_not_render_before_material_delta_and_stage5_compile",
    "do_not_claim_creative_quality",
    "do_not_claim_final_delivery",
    "do_not_claim_picture_lock",
    "do_not_claim_render_permission",
    "do_not_set_human_creative_approval"
  ],
  "human_creative_approval": false,
  "final_delivery_claimed": false,
  "review_packet": {
   "path": ".tmp/canon67_540s_route_acceptance/all_segment_editorial_review/owner_review_index.md",
    "path": ".tmp/canon67_540s_route_acceptance/integrator_acceptance_v1/reviewer_findings.md",
    "sha256": "4154d4ffce4a8d33c5ae70ac9ce717ef663be0a572e886ace33b2a016e01ae43"
  }
}
<!-- HANDOFF_STATE_END -->

## Historical / Superseded Work In Flight Context

- The accepted 540-second, three-act, ten-beat story design has been retargeted
  from a future Canon 68 collection design to a Canon 67 candidate-production run.
  The story itself was not expanded or rewritten.
- Canon 67 raw material under `C:/Users/user/Downloads/微電影素材/_整理後`
  is now the primary source for this run. Every factual use still requires a
  fresh Material Map entry and source-hash evidence.
- Final/reference films, Canon 66 material, generated identity/event proof, and
  prior candidates are excluded as source evidence by
  `.tmp/canon67_540s_route_acceptance/stage0/source_policy.json`.
- The run must produce a real 540-second candidate film while proving legal
  Stage 0–10 and L0–L5 handoffs. Missing story proof must use formal fallback,
  collection, generation-as-support, or script revision rather than a fake PASS.
- Stage 4 is the current cursor. The expanded Material Map contains 81 source-
  hash-bound assets, 79 accepted need edges, and 55 independently hash-matched
  selected assets. The fresh delta is 14 covered / 4 thin / 2 optional missing,
  and its canonical lifecycle is `build_ready` with no waivers.
- BUILD is now allowed. Canonical render remains disabled until Stage 5 compiles
  the layered picture/audio/text/effect decisions and their review captions.
- Human creative approval and final delivery remain explicitly unclaimed.
