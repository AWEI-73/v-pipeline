<!-- DOCUMENT_ROLE: CURRENT_HANDOFF -->

# Current Handoff: Hermes Video Pipeline

Read `RUNBOOK.md` first for the operational entry, then use this handoff for
the current machine-readable work pointer.

<!-- HANDOFF_STATE_START -->
{
  "artifact_role": "current_handoff_state",
  "version": 1,
  "updated_at": "2026-07-16T20:09:05+08:00",
  "state": "WAITING_OWNER_CANON67_385S_PICTURE_PREVIEW_VERDICT",
  "active_work_order": "docs/construction-guides/work-orders/2026-07-16-canon67-385s-paper-edit-compile-preview.md",
  "active_spec": ".tmp/canon67_540s_route_acceptance/stage1/story_soul_blueprint.json",
  "active_skill": "skills/video-pipeline-route.md",
  "active_run_root": ".tmp/canon67_540s_route_acceptance",
  "authoritative_state_artifact": ".tmp/canon67_540s_route_acceptance/accepted_chain/revision_0012.json",
  "authoritative_state_sha256": "b6c3064846a01ee8c6f64a43df6b16448805c6e2e28a93d5159cb09ec9c46aa9",
  "authoritative_state_field": "revision_id",
  "campaign_status_artifact": ".tmp/canon67_540s_route_acceptance/campaign_status.json",
  "campaign_status_field": "state",
  "next_actions": [
    "owner_watch_full_385s_review_preview",
    "owner_review_seg06_seg08_seg10_and_overall_pacing",
    "integrator_record_owner_picture_preview_verdict"
  ],
  "do_not_do": [
    "do_not_reuse_canon68_proxy_coverage_as_pass_evidence",
    "do_not_use_reference_or_canon66_media_as_source",
    "do_not_claim_creative_quality",
    "do_not_claim_final_delivery",
    "do_not_change_owner_accepted_paper_edit",
    "do_not_restore_540_second_quota",
    "do_not_add_seg09_teacher_sequence",
    "do_not_change_approved_supervisor_transcript",
    "do_not_add_bgm_or_final_mix",
    "do_not_upload_or_claim_delivery",
    "do_not_set_human_creative_approval",
    "do_not_rerender_before_owner_picture_preview_verdict",
    "do_not_treat_review_captions_as_delivery_graphics",
    "do_not_claim_exact_picture_frame_pass"
  ],
  "human_creative_approval": false,
  "final_delivery_claimed": false,
  "review_packet": {
    "path": ".tmp/canon67_540s_route_acceptance/stage6/paper_edit_preview_v1/canon67_385s_review_index.json",
    "sha256": "f0e1dc54eb4b1126db791902d5ed79183fd1bc09e88af411a285cd8c225a1e8f"
  }
}
<!-- HANDOFF_STATE_END -->

## Current Durable Context

- Owner accepted the 385-second Stage 5 paper edit in revision 12. The earlier
  540-second target is now a ceiling, not a quota; padding and duplicate windows
  remain forbidden.
- Canon 67 source media and the reviewed Material Map remain the only factual
  source. Reference films, Canon 66 media, and generated event/identity proof are
  excluded.
- Fixed decisions include seg03 at 36 seconds, complete approved 39.34-second
  supervisor speech in seg08, seg09 at zero with the 13/13 roster deferred, and
  the approved memory-to-group-photo ending copy in seg10.
- The bounded 385-second review preview has passed integrator technical review
  with one retained objective finding: its frozen picture is one frame short of
  the accepted frame budget. This is nonblocking for owner review but blocks an
  exact-frame PASS and renderer certification.
- Build and render now pause for the owner picture-preview verdict. Music, final
  mix, delivery graphics, finishing quality, upload, creative approval, and
  delivery remain outside this authorization.
