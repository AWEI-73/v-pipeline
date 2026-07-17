<!-- DOCUMENT_ROLE: CURRENT_HANDOFF -->

# Current Handoff: Hermes Video Pipeline

Read `RUNBOOK.md` first for the operational entry, then use this handoff for
the current machine-readable work pointer.

<!-- HANDOFF_STATE_START -->
{
  "artifact_role": "current_handoff_state",
  "version": 1,
  "updated_at": "2026-07-17T09:51:43+08:00",
  "state": "WAITING_OWNER_CANON67_STAGE2_AMBIGUITY_PACKAGE",
  "active_work_order": null,
  "active_spec": "docs/decisions/2026-07-17-progressive-editorial-ambiguity-loop.md",
  "active_skill": "skills/editorial-ambiguity-loop.md",
  "active_run_root": ".tmp/canon67_editorial_reconstruction_v2",
  "authoritative_state_artifact": ".tmp/canon67_editorial_reconstruction_v2/accepted/accepted_editorial_state_v2.json",
  "authoritative_state_sha256": "2041e6b9c879aa7737defa0f3d86198836822860a2345b16d2742bf219af25e7",
  "authoritative_state_field": "state_id",
  "campaign_status_artifact": ".tmp/canon67_editorial_reconstruction_v2/campaign_status.json",
  "campaign_status_field": "state",
  "next_actions": [
    "orchestrator_rebuild_canon67_stage2_story_decision_segment_grammar_and_evidence_needs",
    "owner_review_high_impact_story_and_segment_decisions",
    "run_stage2_ambiguity_gate_before_any_stage3_resume"
  ],
  "do_not_do": [
    "do_not_resume_the_retired_stage3_8_work_order_from_the_thin_stage2_state",
    "do_not_treat_segment_names_as_segment_composition_grammar",
    "do_not_let_stage3_reinterpret_story_jobs_or_need_ids",
    "do_not_reuse_old_385_second_picture_or_source_window_order",
    "do_not_use_reference_or_canon66_media_as_source",
    "do_not_bypass_retrieval_ranking_or_registered_public_tools",
    "do_not_pad_to_540_seconds",
    "do_not_add_partial_teacher_roster",
    "do_not_invent_literal_departure_or_first_person_trainee_voiceover",
    "do_not_change_approved_39_34_second_supervisor_speech_or_subtitles",
    "do_not_claim_creative_quality",
    "do_not_claim_final_delivery",
    "do_not_set_human_creative_approval"
  ],
  "human_creative_approval": false,
  "final_delivery_claimed": false,
  "review_packet": {
    "path": ".tmp/canon67_editorial_reconstruction_v2/accepted/acceptance_manifest.json",
    "sha256": "bef347cef1f14d452e2b5a4a950bb3b70bc0405cfc766d06dcc56311935e3f4e"
  }
}
<!-- HANDOFF_STATE_END -->

## Current Durable Context

- Owner's results-report skeleton, causal preference, truthful duration range,
  approved supervisor speech/subtitles, and roster deferral remain accepted
  inputs. Canon 67 source media and the reviewed Material Map remain the only
  factual source; reference-film and Canon 66 pixels stay excluded.
- The attempted Stage 3 run proved that the accepted Stage 2 state was too thin:
  it had segment labels and a causal direction, but no frozen per-segment
  composition grammar or evidence-need mapping. The worker therefore guessed
  new-to-old need mappings and changed accepted story jobs.
- `skills/editorial-ambiguity-loop.md` now defines the additive fix. Canon 67
  must produce hash-bound `story_decision_packet.json`,
  `segment_story_contract.json`, and `evidence_need_map.json`, then pass
  `tools/editorial_ambiguity.py validate` before Stage 3 may resume.
- The old Stage 3–8 work order remains durable history but is no longer active.
  No worker owns Stage 3–8 until the new Stage 2 package receives owner review.
- The Integrator retains product judgment and final acceptance. Rendering,
  finishing, upload, creative approval, and delivery are not authorized.
