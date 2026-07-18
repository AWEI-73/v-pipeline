<!-- DOCUMENT_ROLE: CURRENT_HANDOFF -->

# Current Handoff: Hermes Video Pipeline

Read `RUNBOOK.md` first for the operational entry, then use this handoff for
the current machine-readable work pointer.

<!-- HANDOFF_STATE_START -->
{
  "artifact_role": "current_handoff_state",
  "version": 1,
  "updated_at": "2026-07-18T19:50:00+08:00",
  "state": "WAITING_OWNER_CANON67_STAGE4_STORYBOARD_V2_VERDICT",
  "active_work_order": "docs/construction-guides/work-orders/2026-07-18-canon67-stage4-storyboard-review-revision-v2.md",
  "active_spec": "docs/decisions/2026-07-18-canon67-stage3-5-story-revision-and-role-bound-retrieval.md",
  "active_skill": "skills/editing-loop-director.md",
  "active_run_root": ".tmp/canon67_editorial_reconstruction_v2",
  "authoritative_state_artifact": ".tmp/canon67_editorial_reconstruction_v2/accepted/accepted_story_revision_v4.json",
  "authoritative_state_sha256": "eb4b04cebeace082907aca77b1cc128d4f086731379ba1f9c7db9cd2bac6fba6",
  "authoritative_state_field": "status",
  "campaign_status_artifact": ".tmp/canon67_editorial_reconstruction_v2/campaign_status.json",
  "campaign_status_field": "state",
  "next_actions": [
    "owner_watches_the_315_second_storyboard_v2",
    "owner_reviews_the_f01_to_f06_resolution_matrix",
    "owner_returns_the_five_pending_story_and_finishing_decisions"
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
    "path": ".tmp/canon67_editorial_reconstruction_v2/stage4_storyboard_v2/review/timeline_review_v2/owner_review_index.md",
    "sha256": "2e8b48ca58bf3326a960a15be796e46d5f0349c03853eff75298a6e7631d85ac"
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
- Stage 4 storyboard v2 is now a 315-second, six-chapter review candidate with
  visible supported-unit labels, the approved 39.34-second supervisor speech,
  and 12/12 unchanged subtitles. All 11 horizontal review walls were inspected.
  F01–F04 are resolved in this candidate, F05 is structurally resolved with
  owner taste pending, and F06 remains deferred to finishing. The paper edit is
  not picture-locked.
- Multi-role retrieval is role-bound: every video clip carries a stable
  `clip_id` and `need_id`; scenes with multiple accepted edges are matched
  against the current role. Stage 4 must pass this gate before any render.
- Current HEAD full-suite evidence is 2,906 tests PASS with one skipped. The
  explicit silent-timeline audio policy and late-speech waveform verification
  are committed at `b404ab9d`.
- The old Stage 3–8, complete-pool Stage 3, Stage 3.5, and prior Stage 4 work
  orders remain durable history. No worker construction is currently
  authorized; the only next action is the owner's storyboard v2 verdict.
- The Integrator retains product judgment and final acceptance. Rendering,
  finishing, upload, creative approval, and delivery are not authorized.
