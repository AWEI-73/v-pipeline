import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.pipeline_home import summarize_run


def _write(root, name, payload):
    path = Path(root) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


class PipelineHomeTest(unittest.TestCase):
    def test_material_first_intent_routes_to_stage2(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "video_intent.json", {
                "artifact_role": "video_intent",
                "entry_path": "material-first",
                "video_type": "graduation-event",
            })

            summary = summarize_run(tmp)

            self.assertEqual(summary["mode"], "run")
            self.assertEqual(summary["cursor"], "stage2_material_map")
            self.assertIn("video_intent.json", summary["read"])

    def test_material_acceptance_with_stage0_soundtrack_contract_routes_to_soundtrack_before_render(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "material_first_boundary_acceptance_report.json", {
                "artifact_role": "material_first_boundary_acceptance_report",
                "ok": True,
                "next_action": "ready_for_render_or_human_review",
                "stages": [
                    {"stage": "stage2_3_material_wall_to_review_apply", "ok": True},
                    {"stage": "stage4_build", "ok": True},
                    {"stage": "stage5_final_review", "ok": True},
                ],
                "stage0_contracts": {
                    "soundtrack": {
                        "artifact_role": "stage0_soundtrack_intent",
                        "status": "requested",
                        "music_role": "mixed",
                        "handoff_to": "soundtrack-arranger",
                    }
                },
            })

            summary = summarize_run(tmp)

            self.assertEqual(summary["mode"], "run")
            self.assertEqual(summary["cursor"], "soundtrack_arranger")
            self.assertEqual(summary["next"], "soundtrack-arrange")
            self.assertIn("soundtrack", summary["reason"])

    def test_structure_first_intent_routes_to_stage1(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "video_intent.json", {
                "artifact_role": "video_intent",
                "entry_path": "structure-first",
                "video_type": "storybook",
            })

            summary = summarize_run(tmp)

            self.assertEqual(summary["mode"], "run")
            self.assertEqual(summary["cursor"], "stage1_story_blueprint")
            self.assertIn("video_intent.json", summary["read"])

    def test_needs_context_intent_is_clean_waiting_state_not_repair(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "video_intent.json", {
                "artifact_role": "video_intent",
                "entry_path": "needs-context",
                "route": "needs-context",
                "required_followup_questions": [
                    "Who is the audience?",
                    "Do you already have material?",
                ],
            })

            summary = summarize_run(tmp)

            self.assertEqual(summary["mode"], "waiting")
            self.assertEqual(summary["status"], "WAITING")
            self.assertEqual(summary["cursor"], "stage0_video_intent")
            self.assertEqual(summary["next"], "ask_followup_questions")
            self.assertIn("Who is the audience?", summary["reason"])

    def test_intent_semantic_route_hint_routes_to_brownfield_workbench(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "video_intent.json", {
                "artifact_role": "video_intent",
                "entry_path": "material-first",
                "route": "material-first",
                "semantic_route_hint": "brownfield-edit",
            })

            summary = summarize_run(tmp)

            self.assertEqual(summary["mode"], "run")
            self.assertEqual(summary["cursor"], "workbench_draft_review")
            self.assertEqual(summary["next"], "workbench-handoff-validate")

    def test_intent_semantic_route_hint_routes_to_final_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "video_intent.json", {
                "artifact_role": "video_intent",
                "entry_path": "material-first",
                "route": "material-first",
                "semantic_route_hint": "final-review",
            })

            summary = summarize_run(tmp)

            self.assertEqual(summary["mode"], "run")
            self.assertEqual(summary["cursor"], "stage5_final_review")
            self.assertEqual(summary["next"], "verify_existing_final_or_delivery_gate")

    def test_intent_semantic_route_hint_routes_to_effect_factory(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "video_intent.json", {
                "artifact_role": "video_intent",
                "entry_path": "structure-first",
                "route": "structure-first",
                "semantic_route_hint": "effect-factory",
                "required_followup_questions": [],
            })

            summary = summarize_run(tmp)

            self.assertEqual(summary["mode"], "run")
            self.assertEqual(summary["cursor"], "effect_factory_parameter_review")
            self.assertEqual(summary["next"], "visual-technique-plan")

    def test_whole_video_deferred_effect_hint_preserves_material_first_mainline(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "video_intent.json", {
                "artifact_role": "video_intent",
                "entry_path": "material-first",
                "route": "material-first",
                "semantic_route_hint": "effect-factory",
                "effect_policy": {
                    "artifact_role": "stage0_effect_policy",
                    "status": "requested",
                    "activation": "defer_to_brownfield_or_segment_review",
                    "required_now": False,
                    "handoff_to": "video-effect-factory_when_segment_requires_effect",
                },
                "required_followup_questions": [
                    "Which section needs the effect, and what story function should it serve?"
                ],
            })

            summary = summarize_run(tmp)

            self.assertEqual(summary["mode"], "run")
            self.assertEqual(summary["cursor"], "stage2_material_map")
            self.assertEqual(summary["next"], "material-map lifecycle / material acquisition")

    def test_needs_context_with_route_hint_does_not_bypass_waiting_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "video_intent.json", {
                "artifact_role": "video_intent",
                "entry_path": "needs-context",
                "route": "needs-context",
                "semantic_route_hint": "effect-factory",
                "required_followup_questions": ["Which text should appear in the opening effect?"],
            })

            summary = summarize_run(tmp)

            self.assertEqual(summary["mode"], "waiting")
            self.assertEqual(summary["cursor"], "stage0_video_intent")
            self.assertIn("route hint held for later", summary["reason"])

    def test_needs_context_with_empty_questions_still_does_not_bypass_waiting_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "video_intent.json", {
                "artifact_role": "video_intent",
                "entry_path": "needs-context",
                "route": "needs-context",
                "semantic_route_hint": "final-review",
                "required_followup_questions": [],
            })

            summary = summarize_run(tmp)

            self.assertEqual(summary["mode"], "waiting")
            self.assertEqual(summary["cursor"], "stage0_video_intent")
            self.assertEqual(summary["next"], "ask_followup_questions")
            self.assertIn("needs context", summary["reason"])

    def test_story_blueprint_routes_to_material_map(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "story_world.json", {"artifact_role": "story_world"})
            _write(tmp, "screenplay_beats.json", {"artifact_role": "screenplay_beats"})
            _write(tmp, "material_needs.json", {"artifact_role": "material_needs"})

            summary = summarize_run(tmp)

            self.assertEqual(summary["mode"], "run")
            self.assertEqual(summary["cursor"], "stage2_material_map")
            self.assertIn("material_needs.json", summary["read"])

    def test_material_wall_handoff_ready_routes_to_review_apply_with_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "material_wall_handoff_report.json", {
                "artifact_role": "material_wall_handoff_report",
                "ready_for_mapping": True,
                "selected_asset_ids": ["a", "b", "c"],
                "rejected_asset_ids": ["d"],
                "duplicate_asset_ids": ["e"],
                "missing_need_ids": [],
                "duplicate_need_ids": [],
            })

            summary = summarize_run(tmp)

            self.assertEqual(summary["mode"], "run")
            self.assertEqual(summary["cursor"], "stage3_review_apply")
            self.assertIn("selected=3", summary["reason"])
            self.assertIn("rejected=1", summary["reason"])
            self.assertIn("material_wall_handoff_report.json", summary["read"])

    def test_material_wall_handoff_missing_need_routes_to_repair(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "material_wall_handoff_report.json", {
                "artifact_role": "material_wall_handoff_report",
                "ready_for_mapping": False,
                "selected_asset_ids": ["a", "b"],
                "rejected_asset_ids": [],
                "duplicate_asset_ids": [],
                "missing_need_ids": ["nd_training"],
                "duplicate_need_ids": ["nd_opening"],
            })

            summary = summarize_run(tmp)

            self.assertEqual(summary["mode"], "repair")
            self.assertEqual(summary["cursor"], "stage2_material_wall_review")
            self.assertIn("missing needs: nd_training", summary["reason"])
            self.assertIn("duplicate needs: nd_opening", summary["reason"])

    def test_build_ready_lifecycle_routes_to_stage4(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "material_map_lifecycle.json", {
                "artifact_role": "material_map_lifecycle",
                "stage": "build_ready",
                "can_build": True,
                "next_action": "build",
                "refs": {
                    "material_delta": "material_delta.json",
                    "project_material_map": "project_material_map.json",
                },
            })

            summary = summarize_run(tmp)

            self.assertEqual(summary["mode"], "run")
            self.assertEqual(summary["cursor"], "stage4_dry_build")
            self.assertIn("boundary_smoke.py", summary["next"])
            self.assertIn("material_delta.json", summary["read"])

    def test_segment_contract_routes_to_stage4_without_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "segment_contract.json", {
                "artifact_role": "segment_contract",
                "segments": [],
            })

            summary = summarize_run(tmp)

            self.assertEqual(summary["mode"], "run")
            self.assertEqual(summary["cursor"], "stage4_dry_build")
            self.assertIn("segment_contract.json", summary["read"])

    def test_timeline_routes_to_stage5_without_verify(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "timeline_build.json", {"artifact_role": "timeline_build"})
            _write(tmp, "editor_review.json", {"artifact_role": "editor_review"})

            summary = summarize_run(tmp)

            self.assertEqual(summary["mode"], "run")
            self.assertEqual(summary["cursor"], "stage5_final_review")
            self.assertIn("timeline_build.json", summary["read"])

    def test_await_map_review_routes_to_repair(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "material_map_lifecycle.json", {
                "artifact_role": "material_map_lifecycle",
                "stage": "await_map_review",
                "can_build": False,
                "next_action": "await_map_review",
                "refs": {
                    "material_delta": "material_delta.json",
                    "project_material_map": "project_material_map.json",
                },
            })

            summary = summarize_run(tmp)

            self.assertEqual(summary["mode"], "repair")
            self.assertEqual(summary["cursor"], "stage3_review_apply")
            self.assertEqual(summary["resume"], "stage4_dry_build")
            self.assertIn("await_map_review", summary["reason"])

    def test_verify_pass_routes_to_done(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "final.mp4").write_bytes(b"fake video")
            _write(tmp, "verify_result.json", {
                "artifact_role": "verify_result",
                "pass": True,
                "score": 98,
            })

            summary = summarize_run(tmp)

            self.assertEqual(summary["mode"], "done")
            self.assertEqual(summary["cursor"], "complete")
            self.assertIsNone(summary["next"])

    def test_verify_pass_overrides_stale_build_ready_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "final.mp4").write_bytes(b"fake video")
            _write(tmp, "material_map_lifecycle.json", {
                "artifact_role": "material_map_lifecycle",
                "stage": "build_ready",
                "can_build": True,
            })
            _write(tmp, "verify_result.json", {
                "artifact_role": "verify_result",
                "pass": True,
                "score": 99,
            })

            summary = summarize_run(tmp)

            self.assertEqual(summary["mode"], "done")
            self.assertEqual(summary["cursor"], "complete")

    def test_failed_boundary_report_routes_to_repair(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "boundary_report.json", {
                "artifact_role": "boundary_report",
                "stage": "stage5_final_review",
                "pass": False,
                "regressions": ["expected blocking artifact 'caption_audit'"],
                "refs": {"final_review": "actual/final_review_boundary.json"},
            })

            summary = summarize_run(tmp)

            self.assertEqual(summary["mode"], "repair")
            self.assertEqual(summary["cursor"], "stage5_final_review")
            self.assertIn("caption_audit", summary["reason"])
            self.assertIn("actual/final_review_boundary.json", summary["read"])

    def test_material_first_acceptance_ready_routes_to_human_review_or_render(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "material_first_boundary_acceptance_report.json", {
                "artifact_role": "material_first_boundary_acceptance_report",
                "route": "material-first",
                "ok": True,
                "next_action": "ready_for_render_or_human_review",
                "failed_stage": None,
                "stages": [
                    {"stage": "stage2_3_material_wall_to_review_apply", "ok": True},
                    {"stage": "stage4_build", "ok": True},
                    {"stage": "stage5_final_review", "ok": True},
                ],
            })
            _write(tmp, "timeline_build.json", {"artifact_role": "timeline_build"})
            _write(tmp, "editor_review.json", {"artifact_role": "editor_review"})

            summary = summarize_run(tmp)

            self.assertEqual(summary["mode"], "run")
            self.assertEqual(summary["cursor"], "stage5_final_review")
            self.assertEqual(summary["next"], "ready_for_render_or_human_review")
            self.assertEqual(summary["source"], "material_first_boundary_acceptance_report.json")
            self.assertIn("3/3 stages passed", summary["reason"])

    def test_soundtrack_blocks_override_material_first_ready_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "material_first_boundary_acceptance_report.json", {
                "artifact_role": "material_first_boundary_acceptance_report",
                "route": "material-first",
                "ok": True,
                "next_action": "ready_for_render_or_human_review",
                "failed_stage": None,
                "stages": [
                    {"stage": "stage2_3_material_wall_to_review_apply", "ok": True},
                    {"stage": "stage4_build", "ok": True},
                    {"stage": "stage5_final_review", "ok": True},
                ],
            })
            _write(tmp, "soundtrack_plan.json", {
                "artifact_role": "soundtrack_plan",
                "sections": [{"section_id": "mv_climax", "music_role": "song"}],
            })
            _write(tmp, "sound_license_manifest.json", {
                "artifact_role": "sound_license_manifest",
                "delivery_allowed": False,
                "blocked_reasons": ["license_missing"],
            })
            _write(tmp, "audio_director_handoff.json", {
                "artifact_role": "audio_director_handoff",
                "ready_for_audio_director": False,
                "blocks": ["license_missing"],
            })

            summary = summarize_run(tmp)

            self.assertEqual(summary["mode"], "repair")
            self.assertEqual(summary["cursor"], "soundtrack_review")
            self.assertEqual(summary["next"], "resolve_soundtrack_license_or_reference_only")
            self.assertEqual(summary["source"], "audio_director_handoff.json")

    def test_soundtrack_role_fallback_review_blocks_before_audio_director(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "soundtrack_plan.json", {
                "artifact_role": "soundtrack_plan",
                "stage0_soundtrack_contract": {
                    "music_role": "mixed",
                    "fallback_policy": {"role_fallback": "song_to_bgm_requires_review"},
                },
                "sections": [{"section_id": "mv_climax", "music_role": "song"}],
            })
            _write(tmp, "sound_license_manifest.json", {
                "artifact_role": "sound_license_manifest",
                "delivery_allowed": False,
                "blocked_reasons": ["role_fallback_requires_review"],
            })
            _write(tmp, "audio_director_handoff.json", {
                "artifact_role": "audio_director_handoff",
                "ready_for_audio_director": False,
                "blocks": ["role_fallback_requires_review"],
            })

            summary = summarize_run(tmp)

            self.assertEqual(summary["mode"], "repair")
            self.assertEqual(summary["cursor"], "soundtrack_review")
            self.assertEqual(summary["next"], "resolve_soundtrack_license_or_reference_only")
            self.assertIn("role_fallback_requires_review", summary["reason"])

    def test_material_first_acceptance_failed_routes_to_failed_stage(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "material_first_boundary_acceptance_report.json", {
                "artifact_role": "material_first_boundary_acceptance_report",
                "route": "material-first",
                "ok": False,
                "next_action": "repair:stage2_3_material_wall_to_review_apply",
                "failed_stage": "stage2_3_material_wall_to_review_apply",
                "stages": [{
                    "stage": "stage2_3_material_wall_to_review_apply",
                    "ok": False,
                    "blocking": [{"rule": "stage_exception", "message": "requires at least 3 usable media files"}],
                }],
            })

            summary = summarize_run(tmp)

            self.assertEqual(summary["mode"], "repair")
            self.assertEqual(summary["cursor"], "stage2_3_material_wall_to_review_apply")
            self.assertEqual(summary["next"], "repair:stage2_3_material_wall_to_review_apply")
            self.assertIn("requires at least 3 usable media files", summary["reason"])
            self.assertIn("material_first_boundary_acceptance_report.json", summary["read"])

    def test_soundtrack_handoff_blocks_route_when_license_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "soundtrack_plan.json", {
                "artifact_role": "soundtrack_plan",
                "sections": [{"section_id": "mv_climax", "music_role": "song"}],
            })
            _write(tmp, "sound_license_manifest.json", {
                "artifact_role": "sound_license_manifest",
                "delivery_allowed": False,
                "blocked_reasons": ["license_missing"],
            })
            _write(tmp, "audio_director_handoff.json", {
                "artifact_role": "audio_director_handoff",
                "ready_for_audio_director": False,
                "blocks": ["license_missing"],
            })

            summary = summarize_run(tmp)

            self.assertEqual(summary["mode"], "repair")
            self.assertEqual(summary["cursor"], "soundtrack_review")
            self.assertEqual(summary["next"], "resolve_soundtrack_license_or_reference_only")
            self.assertEqual(summary["source"], "audio_director_handoff.json")
            self.assertIn("license_missing", summary["reason"])
            self.assertIn("soundtrack_plan.json", summary["read"])
            self.assertIn("sound_license_manifest.json", summary["read"])
            self.assertIn("audio_director_handoff.json", summary["read"])

    def test_soundtrack_handoff_ready_routes_to_audio_director(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "soundtrack_plan.json", {
                "artifact_role": "soundtrack_plan",
                "sections": [{"section_id": "warm_story", "music_role": "bgm"}],
            })
            _write(tmp, "sound_license_manifest.json", {
                "artifact_role": "sound_license_manifest",
                "delivery_allowed": True,
                "blocked_reasons": [],
            })
            _write(tmp, "audio_director_handoff.json", {
                "artifact_role": "audio_director_handoff",
                "ready_for_audio_director": True,
                "blocks": [],
            })

            summary = summarize_run(tmp)

            self.assertEqual(summary["mode"], "run")
            self.assertEqual(summary["cursor"], "audio_director")
            self.assertEqual(summary["next"], "tts_mix_ducking_or_audio_director")
            self.assertEqual(summary["source"], "audio_director_handoff.json")

    def test_audio_handoff_acceptance_block_routes_to_repair(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "audio_handoff_acceptance.json", {
                "artifact_role": "audio_handoff_acceptance",
                "ok": False,
                "blocking": [{"rule": "reference_only_source", "message": "reference_only source cannot enter audio mix plan"}],
                "next_action": "repair_audio_handoff",
            })

            summary = summarize_run(tmp)

            self.assertEqual(summary["mode"], "repair")
            self.assertEqual(summary["cursor"], "audio_handoff_acceptance")
            self.assertEqual(summary["next"], "repair_audio_handoff")
            self.assertIn("reference_only_source", summary["reason"])

    def test_audio_mix_plan_ready_routes_to_audio_mix(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "audio_handoff_acceptance.json", {
                "artifact_role": "audio_handoff_acceptance",
                "ok": True,
                "blocking": [],
                "accepted_track_count": 1,
                "next_action": "audio_mix_plan_ready",
            })
            _write(tmp, "audio_mix_plan.json", {
                "artifact_role": "audio_mix_plan",
                "ready_for_mix": True,
                "tracks": [{"section_id": "mv_climax", "audio_file": "audio/sources/mv.mp3"}],
            })

            summary = summarize_run(tmp)

            self.assertEqual(summary["mode"], "run")
            self.assertEqual(summary["cursor"], "audio_mix")
            self.assertEqual(summary["next"], "mix_audio_from_audio_mix_plan")
            self.assertIn("1 accepted track", summary["reason"])

    def test_audio_build_handoff_routes_to_build_audio_handoff(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "final_audio.wav", "audio")
            _write(tmp, "audio_mix_report.json", {
                "artifact_role": "audio_mix_report",
                "ok": True,
                "audio_stream_present": True,
            })
            _write(tmp, "audio_build_handoff.json", {
                "artifact_role": "audio_build_handoff",
                "selected_audio": str(Path(tmp) / "final_audio.wav"),
                "selection_reason": "audio_ready_final_audio",
                "audio_ready": True,
            })

            summary = summarize_run(tmp)

            self.assertEqual(summary["mode"], "run")
            self.assertEqual(summary["cursor"], "audio_build_handoff")
            self.assertEqual(summary["next"], "continue_build_or_material_gate")
            self.assertEqual(summary["source"], "audio_build_handoff.json")

    def test_subtitle_voiceover_build_handoff_routes_to_build_handoff(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "subtitle_voiceover_handoff_acceptance.json", {
                "artifact_role": "subtitle_voiceover_handoff_acceptance",
                "ok": True,
                "next_action": "subtitle_voiceover_build_handoff_ready",
            })
            _write(tmp, "subtitle_voiceover_build_handoff.json", {
                "artifact_role": "subtitle_voiceover_build_handoff",
                "subtitle_ready": True,
                "voiceover_ready": False,
                "subtitles": str(Path(tmp) / "subtitles.srt"),
                "caption_audit": str(Path(tmp) / "caption_audit.json"),
            })

            summary = summarize_run(tmp)

            self.assertEqual(summary["mode"], "run")
            self.assertEqual(summary["cursor"], "subtitle_voiceover_build_handoff")
            self.assertEqual(summary["next"], "continue_build_or_material_gate")
            self.assertEqual(summary["source"], "subtitle_voiceover_build_handoff.json")

    def test_remotion_material_first_memory_acceptance_ready_routes_to_effect_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "remotion_material_first_memory_acceptance_report.json", {
                "artifact_role": "remotion_material_first_memory_acceptance_report",
                "ok": True,
                "failed_stage": None,
                "next_action": "ready_for_human_effect_review_or_pipeline_promotion",
                "summary": {
                    "selected_ref_count": 3,
                    "evidence_kinds": ["material_wall_keyframe"],
                    "build_component": "MemoryPhotoWall",
                },
            })
            _write(tmp, "remotion_effect_handoff.json", {
                "artifact_role": "remotion_effect_handoff",
                "version": 1,
                "status": "ready_for_human_review",
                "accepted_assets": [{"job_id": "rm_fx_material_memory_wall_01"}],
            })

            summary = summarize_run(tmp)

            self.assertEqual(summary["mode"], "run")
            self.assertEqual(summary["cursor"], "remotion_material_first_memory_acceptance")
            self.assertEqual(summary["next"], "ready_for_human_effect_review_or_pipeline_promotion")
            self.assertEqual(summary["source"], "remotion_material_first_memory_acceptance_report.json")
            self.assertIn("MemoryPhotoWall", summary["reason"])
            self.assertIn("3 refs", summary["reason"])
            self.assertIn("remotion_effect_handoff.json", summary["read"])
            self.assertIn("handoff ready", summary["reason"])

    def test_effect_factory_boundary_acceptance_ready_routes_to_effect_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "effect_factory_boundary_acceptance_report.json", {
                "artifact_role": "effect_factory_boundary_acceptance_report",
                "ok": True,
                "failed_stage": None,
                "next_action": "ready_for_human_effect_review_or_pipeline_promotion",
                "summary": {
                    "effect_count": 4,
                    "job_count": 4,
                    "rendered_count": 4,
                    "semantic_diversity_ok": True,
                    "canonical_final_exists": False,
                },
                "style_signatures": [
                    {"style_family": "electric_lightning_energy"},
                    {"style_family": "earthquake_crack_impact"},
                    {"style_family": "mothers_day_heart_stage"},
                    {"style_family": "warm_legacy_fire"},
                ],
            })
            _write(tmp, "effect_handoff.json", {
                "artifact_role": "effect_handoff",
                "version": 1,
                "status": "ready_for_human_review",
                "accepted_assets": [{"job_id": "rm_fx_opening_lightning_01"}],
            })

            summary = summarize_run(tmp)

            self.assertEqual(summary["mode"], "run")
            self.assertEqual(summary["cursor"], "effect_factory_boundary")
            self.assertEqual(summary["next"], "ready_for_human_effect_review_or_pipeline_promotion")
            self.assertEqual(summary["source"], "effect_factory_boundary_acceptance_report.json")
            self.assertIn("4 semantic families", summary["reason"])
            self.assertIn("4/4 dry-run worker outputs", summary["reason"])
            self.assertIn("effect_handoff.json", summary["read"])

    def test_effect_factory_boundary_acceptance_failed_routes_to_repair(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "effect_factory_boundary_acceptance_report.json", {
                "artifact_role": "effect_factory_boundary_acceptance_report",
                "ok": False,
                "failed_stage": "effect_factory_boundary",
                "next_action": "revise_effect_factory_contract",
                "validation_errors": ["jobs[0].evidence_refs must include at least one review evidence file"],
            })

            summary = summarize_run(tmp)

            self.assertEqual(summary["mode"], "repair")
            self.assertEqual(summary["cursor"], "effect_factory_boundary")
            self.assertEqual(summary["next"], "revise_effect_factory_contract")
            self.assertIn("evidence_refs", summary["reason"])

    def test_visual_technique_candidate_routes_to_parameter_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "visual_technique_plan.json", {
                "artifact_role": "visual_technique_plan",
                "version": 1,
                "style_family": "electric_lightning_energy",
                "effect_role": "opening_title",
                "handoff_to": "review_candidate_parameters",
                "candidate_options": [
                    {"option_id": "restrained"},
                    {"option_id": "balanced"},
                    {"option_id": "expressive"},
                ],
            })

            summary = summarize_run(tmp)

            self.assertEqual(summary["mode"], "repair")
            self.assertEqual(summary["cursor"], "effect_factory_parameter_review")
            self.assertEqual(summary["next"], "review_visual_technique_plan_or_rerun_with_confirmed")
            self.assertIn("electric_lightning_energy/opening_title", summary["reason"])
            self.assertIn("restrained, balanced, expressive", summary["reason"])
            self.assertIn("visual_technique_plan.json", summary["read"])

    def test_visual_technique_review_routes_to_apply(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "visual_technique_plan.json", {
                "artifact_role": "visual_technique_plan",
                "version": 1,
                "style_family": "electric_lightning_energy",
                "effect_role": "opening_title",
                "handoff_to": "review_candidate_parameters",
                "candidate_options": [{"option_id": "balanced"}],
            })
            _write(tmp, "visual_technique_review.json", {
                "artifact_role": "visual_technique_review",
                "decision": "accept",
                "selected_option": "balanced",
                "reviewer": "user",
            })

            summary = summarize_run(tmp)

            self.assertEqual(summary["mode"], "repair")
            self.assertEqual(summary["cursor"], "effect_factory_parameter_review_apply")
            self.assertEqual(summary["next"], "visual-technique-review-apply")
            self.assertIn("selected=balanced", summary["reason"])
            self.assertIn("visual_technique_review.json", summary["read"])

    def test_visual_technique_confirmed_routes_to_effect_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "visual_technique_plan.json", {
                "artifact_role": "visual_technique_plan",
                "version": 1,
                "style_family": "electric_lightning_energy",
                "effect_role": "opening_title",
                "handoff_to": "remotion_prompt_parameters",
            })

            summary = summarize_run(tmp)

            self.assertEqual(summary["mode"], "run")
            self.assertEqual(summary["cursor"], "effect_factory_contract")
            self.assertEqual(summary["next"], "effect_contract_or_remotion_prompt_pack")
            self.assertIn("confirmed", summary["reason"])
            self.assertEqual(summary["source"], "visual_technique_plan.json")

    def test_visual_technique_confirmed_file_takes_precedence_over_candidate_and_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "visual_technique_plan.json", {
                "artifact_role": "visual_technique_plan",
                "version": 1,
                "style_family": "electric_lightning_energy",
                "effect_role": "opening_title",
                "handoff_to": "review_candidate_parameters",
                "candidate_options": [{"option_id": "balanced"}],
            })
            _write(tmp, "visual_technique_review.json", {
                "artifact_role": "visual_technique_review",
                "decision": "accept",
                "selected_option": "balanced",
            })
            _write(tmp, "visual_technique_plan.confirmed.json", {
                "artifact_role": "visual_technique_plan",
                "version": 1,
                "style_family": "electric_lightning_energy",
                "effect_role": "opening_title",
                "handoff_to": "remotion_prompt_parameters",
            })

            summary = summarize_run(tmp)

            self.assertEqual(summary["mode"], "run")
            self.assertEqual(summary["cursor"], "effect_factory_contract")
            self.assertEqual(summary["next"], "effect_contract_or_remotion_prompt_pack")
            self.assertEqual(summary["source"], "visual_technique_plan.confirmed.json")
            self.assertIn("visual_technique_plan.confirmed.json", summary["read"])
            self.assertIn("visual_technique_review.json", summary["read"])

    def test_remotion_material_first_memory_acceptance_failed_routes_to_repair(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "remotion_material_first_memory_acceptance_report.json", {
                "artifact_role": "remotion_material_first_memory_acceptance_report",
                "ok": False,
                "failed_stage": "effect_collage_refs",
                "next_action": "provide_material_wall_keyframes_or_reviewed_stills",
                "errors": ["no reviewed material refs available for MemoryPhotoWall"],
            })

            summary = summarize_run(tmp)

            self.assertEqual(summary["mode"], "repair")
            self.assertEqual(summary["cursor"], "effect_collage_refs")
            self.assertEqual(summary["next"], "provide_material_wall_keyframes_or_reviewed_stills")
            self.assertIn("no reviewed material refs", summary["reason"])
            self.assertIn("remotion_material_first_memory_acceptance_report.json", summary["read"])

    def test_cli_prints_json_contract(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "material_map_lifecycle.json", {
                "artifact_role": "material_map_lifecycle",
                "stage": "await_map_review",
                "can_build": False,
                "next_action": "await_map_review",
            })

            proc = subprocess.run(
                [
                    sys.executable,
                    "tools/pipeline_home.py",
                    "--run",
                    tmp,
                    "--json",
                ],
                cwd=root,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["mode"], "repair")
            self.assertEqual(payload["cursor"], "stage3_review_apply")


if __name__ == "__main__":
    unittest.main()
