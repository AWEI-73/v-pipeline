<!-- DOCUMENT_ROLE: CURRENT_HANDOFF -->

# Current Handoff: Hermes Video Pipeline

Read `RUNBOOK.md` first for the operational entry, then use this handoff for
the current machine-readable work pointer.

<!-- HANDOFF_STATE_START -->
{
  "artifact_role": "current_handoff_state",
  "version": 1,
  "updated_at": "2026-07-18T20:48:53+08:00",
  "state": "WAITING_OWNER_CANON67_STAGE4_STORYBOARD_V3_VERDICT",
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
    "owner_watches_the_315_second_storyboard_v3",
    "owner_confirms_the_three_reported_visual_corrections",
    "owner_returns_the_remaining_story_rhythm_and_finishing_verdict"
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
    "path": ".tmp/canon67_editorial_reconstruction_v2/stage4_storyboard_v3/review/owner_correction_closure.json",
    "sha256": "1509abddef431b2bf1656a823470ef2615f618152631bfdb4345f88471f343a7"
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
- Stage 4 storyboard v3 is a 315.022-second, six-chapter review candidate with
  visible supported-unit labels, the approved 39.34-second supervisor speech,
  and 12/12 unchanged subtitles. All 11 half-second timeline walls were
  inspected. The reported cable near-repeat, blood-donation crane mismatch, and
  ending crane mismatch are resolved. All 15 selected HEIC clips are now bound
  to source-hashed Material Map review proxies; no stale `.converted` path is
  present in the v3 timeline. Overall story rhythm and finishing taste remain
  pending, and the paper edit is not picture-locked.
- Multi-role retrieval is role-bound: every video clip carries a stable
  `clip_id` and `need_id`; scenes with multiple accepted edges are matched
  against the current role. Stage 4 must pass this gate before any render.
- The last full-suite evidence is 2,906 tests PASS with one skipped at
  `b404ab9d`; it is now STALE after the bounded HEIC-cache and timeline-review
  contract patch. Focused evidence is authoritative until a later campaign
  closure reruns the full suite.
- The old Stage 3–8, complete-pool Stage 3, Stage 3.5, and prior Stage 4 work
  orders remain durable history. No worker construction is currently
  authorized; the only next action is the owner's storyboard v3 verdict.
- The Integrator retains product judgment and final acceptance. Rendering,
  finishing, upload, creative approval, and delivery are not authorized.
