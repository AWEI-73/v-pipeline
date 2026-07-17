<!-- DOCUMENT_ROLE: CURRENT_HANDOFF -->

# Current Handoff: Hermes Video Pipeline

Read `RUNBOOK.md` first for the operational entry, then use this handoff for
the current machine-readable work pointer.

<!-- HANDOFF_STATE_START -->
{
  "artifact_role": "current_handoff_state",
  "version": 1,
  "updated_at": "2026-07-18T00:39:32+08:00",
  "state": "WAITING_STAGE4_CANON67_ROLE_BOUND_PAPER_EDIT_DISPATCH",
  "active_work_order": null,
  "active_spec": "docs/decisions/2026-07-18-canon67-stage3-5-story-revision-and-role-bound-retrieval.md",
  "active_skill": "skills/editor.md",
  "active_run_root": ".tmp/canon67_editorial_reconstruction_v2",
  "authoritative_state_artifact": ".tmp/canon67_editorial_reconstruction_v2/accepted/accepted_story_revision_v3.json",
  "authoritative_state_sha256": "230432997756b877f7046133a049cddfa3f0cfa8b79472bf9864975217428e6e",
  "authoritative_state_field": "decision_id",
  "campaign_status_artifact": ".tmp/canon67_editorial_reconstruction_v2/campaign_status.json",
  "campaign_status_field": "state",
  "next_actions": [
    "construct_stage4_paper_edit_from_base_editorial_state_plus_accepted_story_revision_v3",
    "bind_every_multi_role_picture_clip_to_stable_clip_id_and_need_id",
    "validate_the_true_shape_picture_plan_with_project_material_map_v3_before_render"
  ],
  "do_not_do": [
    "do_not_rerun_or_rewatch_the_complete_283_asset_pool",
    "do_not_reopen_the_five_stage3_5_story_decisions_without_new_evidence",
    "do_not_treat_filename_or_folder_prior_as_accepted_truth",
    "do_not_validate_a_multi_role_segment_with_one_segment_wide_candidate_list",
    "do_not_use_manual_override_to_hide_a_role_ranking_mismatch",
    "do_not_reuse_old_385_second_clip_order",
    "do_not_use_reference_or_canon66_media_as_source",
    "do_not_bypass_registered_material_map_and_retrieval_surfaces",
    "do_not_run_full_pool_asr_or_music_analysis",
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
    "path": ".tmp/canon67_editorial_reconstruction_v2/stage3_5_targeted_gap_closure_v1/final/integrator_acceptance_v1.md",
    "sha256": "d64d7f4343a5ffa52e2c6e384cb9f760875603e70d8c429e420f2f268c063426"
  }
}
<!-- HANDOFF_STATE_END -->

## Current Durable Context

- Owner's results-report skeleton, causal preference, truthful duration range,
  approved supervisor speech/subtitles, and roster deferral remain accepted
  inputs. Reference-film and Canon 66 pixels stay excluded.
- The complete source inventory remains 306 files, with 283 candidate media.
  Material Map v3 is accepted byte-for-byte at SHA-256
  `704a1fed801218530d206665bf906f67a60ad28f216e3c954ee195b23775962c`:
  283 exact source bindings, all prior 16 accepted edges preserved, and 15 new
  evidence-bound edges. Whole-pool immersion must not be repeated.
- Stage 2 v2 carries an eleven-segment composition grammar, 47 picture/speech
  evidence needs, and a three-level external-audience display policy: chapter
  cards, visually verified course labels, and review-only plain captions. Empty
  folder names are retrieval hints, not facts.
- Stage 3.5 story revisions are accepted for paper-edit construction: A02=12s,
  A07=0s merged into A04/A05, A09=39.34s with bounded cue/cutaway policy,
  A10=18s process-only, and A11=24s with two callbacks plus one final group
  photo. The truthful Stage 4 target is 360.34 seconds before timing review.
- Multi-role retrieval is role-bound: every video clip carries a stable
  `clip_id` and `need_id`; scenes with multiple accepted edges are matched
  against the current role. Stage 4 must pass this gate before any render.
- The one full-suite run reached 2,899 tests with one related legacy-fixture
  failure. The fixture now carries the required candidate edge and the affected
  42-test set passes; final-HEAD full-suite status remains UNKNOWN because the
  suite was intentionally not run a second time.
- The old Stage 3–8, complete-pool Stage 3, and Stage 3.5 work orders remain
  durable history and retired. Stage 4 paper-edit dispatch is the only next
  production action.
- The Integrator retains product judgment and final acceptance. Rendering,
  finishing, upload, creative approval, and delivery are not authorized.
