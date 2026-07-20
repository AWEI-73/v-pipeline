<!-- DOCUMENT_ROLE: CURRENT_HANDOFF -->

# Current Handoff: V Pipeline

Read `RUNBOOK.md` first for the operational entry, then use this handoff for
the current machine-readable work pointer.

<!-- HANDOFF_STATE_START -->
{
  "artifact_role": "current_handoff_state",
  "version": 1,
  "updated_at": "2026-07-20T15:51:35+08:00",
  "state": "CLOSED_FIRST_LONGFORM_CASE_WITH_KNOWN_LIMITATIONS",
  "active_work_order": null,
  "active_spec": "docs/pilots/2026-07-20-canon67-first-longform-closure.md",
  "active_skill": null,
  "active_run_root": ".tmp/canon67_editorial_reconstruction_v2/closure_v1",
  "authoritative_state_artifact": ".tmp/canon67_editorial_reconstruction_v2/closure_v1/campaign_status.json",
  "authoritative_state_sha256": "d6f878eac407340ae2f09ae5f3894fc8fb73a3d04c9cb7eed95a81616c123f93",
  "authoritative_state_field": "state",
  "campaign_status_artifact": ".tmp/canon67_editorial_reconstruction_v2/closure_v1/campaign_status.json",
  "campaign_status_field": "state",
  "next_actions": [
    "select_a_second_better_annotated_longform_material_set",
    "measure_marginal_cost_against_canon67",
    "harden_tool_side_machine_receipts_before_the_second_case"
  ],
  "do_not_do": [
    "do_not_reopen_canon67_picture_story_or_finishing_without_new_owner_direction",
    "do_not_treat_the_retrospective_stage9_receipt_as_an_original_execution_receipt",
    "do_not_claim_music_legal_clearance",
    "do_not_claim_final_delivery",
    "do_not_expand_the_reviewer_before_transfer_evidence"
  ],
  "human_creative_approval": true,
  "final_delivery_claimed": false,
  "review_packet": {
    "path": ".tmp/canon67_editorial_reconstruction_v2/closure_v1/closure_manifest.json",
    "sha256": "27d07d542cea4b76802e9ca363d88c059ce30ad958a1bf4e3e4d1db26acbe26a"
  }
}
<!-- HANDOFF_STATE_END -->

## Current Durable Context

- Canon 67 is closed as the first accepted long-form case evidence. The
  accepted internal candidate is 315.022 seconds, SHA-256
  `10f9a1f2b6f75ddbe9ace15e7be62ebaa383020c21cb69f5363a7c70f8f59017`.
- The owner accepted the candidate with known limitations and explicitly did
  not reopen picture, story, or finishing. This is human creative approval for
  case closure, not final delivery or music-rights clearance.
- Stage 9 v3 applies one stable music duck across the full 236.00–275.34 second
  supervisor segment. The v2/v3 video elementary-stream SHA-256 is identical;
  only the audio stream changed.
- The original Stage 9 v3 fast path lacked a normal work-order/receipt chain.
  A retrospective receipt now binds the current inputs, outputs, stream hashes,
  QA, and Verify evidence while explicitly preserving the missing historical
  metadata as unknown.
- The fresh-context Editorial Reviewer produced three useful findings. They
  are accepted as calibration evidence and deferred to the next case rather
  than used to reopen Canon 67.
- Full suite evidence is 2,928 tests passed with one skipped. Post-suite changes
  are limited to closure metadata, this handoff, and the compact durable
  evidence note; 65 focused entry/document tests passed separately.

## Next Task Boundary

Do not continue refining Canon 67. The next product proof is a second long-form
case using better-annotated material. Before or as part of that case, make
machine receipts a normal side effect of the highest-value render, mix, review,
and verify tools. Measure wall-clock time, agent turns, render count, and human
review minutes against Canon 67.
