import json
import unittest
import wave
from pathlib import Path
from tempfile import TemporaryDirectory

from video_pipeline_core.delivery_gate import (
    apply_strict_lineage_closure_to_gate,
    evaluate_complete_video_delivery,
    evaluate_delivery_gate,
)
from tools.validate_pipeline_run_folder import validate_run_folder


class DeliveryGateTest(unittest.TestCase):
    def test_strict_lineage_closure_blocks_without_current_pass_no_skip(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            gate = apply_strict_lineage_closure_to_gate(root, {"pass": True})

        self.assertFalse(gate["pass"])
        self.assertEqual(gate["blocking"][0]["rule"], "strict_lineage_closure_required")
        self.assertEqual(gate["next_action"], "run_no_skip_execution_trace")

    def test_strict_lineage_closure_binds_matching_trace_and_hashes(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            accountability = root / "accountability"
            accountability.mkdir()
            trace = {
                "artifact_role": "pipeline_execution_trace",
                "version": 2,
                "run_instance_id": "run-1",
                "work_order_execution_contract": "contract.json",
                "work_order_execution_contract_sha256": "a" * 64,
                "lineage_summary": {
                    "root_step": "L1.example",
                    "leaf_step": "L10.delivery",
                    "ordered_step_ids": ["L1.example", "L10.delivery"],
                    "closure_status": "PASS",
                },
                "closure_scope": "pre_delivery",
                "sealed_through_step_id": "L1.example",
                "sealed_step_ids": ["L1.example"],
                "pending_terminal_step_ids": ["L10.delivery"],
            }
            decision = {
                "artifact_role": "no_skip_contract_decision",
                "version": 2,
                "ok": True,
                "final_state": "PASS",
                "run_instance_id": "run-1",
                "contract_path": "contract.json",
                "contract_sha256": "a" * 64,
                "lineage_summary": trace["lineage_summary"],
                "closure_scope": trace["closure_scope"],
                "sealed_through_step_id": trace["sealed_through_step_id"],
                "sealed_step_ids": trace["sealed_step_ids"],
                "pending_terminal_step_ids": trace["pending_terminal_step_ids"],
            }
            (accountability / "pipeline_execution_trace.json").write_text(json.dumps(trace), encoding="utf-8")
            (accountability / "no_skip_contract_decision.json").write_text(json.dumps(decision), encoding="utf-8")
            (accountability / "strict_accountability_closure_audit.json").write_text(
                json.dumps({
                    "artifact_role": "strict_accountability_closure_audit",
                    "ok": True,
                    "run_instance_id": "run-1",
                    "lineage_summary": trace["lineage_summary"],
                    "closure_scope": trace["closure_scope"],
                    "sealed_through_step_id": trace["sealed_through_step_id"],
                    "sealed_step_ids": trace["sealed_step_ids"],
                    "pending_terminal_step_ids": trace["pending_terminal_step_ids"],
                }),
                encoding="utf-8",
            )
            gate = apply_strict_lineage_closure_to_gate(root, {"pass": True})

        self.assertTrue(gate["pass"])
        self.assertEqual(gate["lineage_closure"]["closure_status"], "PASS")
        self.assertEqual(gate["lineage_closure"]["run_instance_id"], "run-1")
        self.assertEqual(len(gate["lineage_closure"]["closure_sha256"]), 64)
        self.assertEqual(len(gate["lineage_closure"]["trace_sha256"]), 64)
        self.assertEqual("pre_delivery", gate["lineage_closure"]["closure_scope"])
        self.assertEqual("L1.example", gate["lineage_closure"]["sealed_through_step_id"])
        self.assertEqual(["L10.delivery"], gate["lineage_closure"]["pending_terminal_step_ids"])

    def test_strict_lineage_closure_rejects_trace_contract_substitution(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            accountability = root / "accountability"
            accountability.mkdir()
            trace = {
                "artifact_role": "pipeline_execution_trace",
                "version": 2,
                "run_instance_id": "run-1",
                "work_order_execution_contract": "other-contract.json",
                "work_order_execution_contract_sha256": "b" * 64,
                "lineage_summary": {"closure_status": "PASS"},
            }
            decision = {
                "artifact_role": "no_skip_contract_decision",
                "version": 2,
                "ok": True,
                "final_state": "PASS",
                "run_instance_id": "run-1",
                "contract_path": "contract.json",
                "contract_sha256": "a" * 64,
                "lineage_summary": trace["lineage_summary"],
            }
            (accountability / "pipeline_execution_trace.json").write_text(json.dumps(trace), encoding="utf-8")
            (accountability / "no_skip_contract_decision.json").write_text(json.dumps(decision), encoding="utf-8")
            (accountability / "strict_accountability_closure_audit.json").write_text(json.dumps({"ok": True}), encoding="utf-8")
            gate = apply_strict_lineage_closure_to_gate(
                root,
                {"pass": True},
                expected_contract_path="contract.json",
                expected_contract_sha256="a" * 64,
            )

        self.assertFalse(gate["pass"])
        self.assertEqual(gate["blocking"][0]["rule"], "strict_lineage_closure_mismatch")

    def test_strict_lineage_closure_rejects_coverage_scope_mismatch(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            accountability = root / "accountability"
            accountability.mkdir()
            coverage = {
                "closure_scope": "pre_delivery",
                "sealed_through_step_id": "L1.example",
                "sealed_step_ids": ["L1.example"],
                "pending_terminal_step_ids": ["L10.delivery"],
            }
            trace = {
                "artifact_role": "pipeline_execution_trace",
                "version": 2,
                "run_instance_id": "run-1",
                "work_order_execution_contract": "contract.json",
                "work_order_execution_contract_sha256": "a" * 64,
                "lineage_summary": {"closure_status": "PASS"},
                **coverage,
            }
            decision = {
                "artifact_role": "no_skip_contract_decision",
                "version": 2,
                "ok": True,
                "final_state": "PASS",
                "run_instance_id": "run-1",
                "contract_path": "contract.json",
                "contract_sha256": "a" * 64,
                "lineage_summary": trace["lineage_summary"],
                **coverage,
            }
            decision["pending_terminal_step_ids"] = []
            closure = {
                "artifact_role": "strict_accountability_closure_audit",
                "ok": True,
                "run_instance_id": "run-1",
                "lineage_summary": trace["lineage_summary"],
                **coverage,
            }
            (accountability / "pipeline_execution_trace.json").write_text(json.dumps(trace), encoding="utf-8")
            (accountability / "no_skip_contract_decision.json").write_text(json.dumps(decision), encoding="utf-8")
            (accountability / "strict_accountability_closure_audit.json").write_text(json.dumps(closure), encoding="utf-8")

            gate = apply_strict_lineage_closure_to_gate(root, {"pass": True})

        self.assertFalse(gate["pass"])
        self.assertEqual("strict_lineage_closure_mismatch", gate["blocking"][0]["rule"])
        self.assertIn("pending_terminal_step_ids differ", gate["blocking"][0]["message"])

    def test_failed_existing_audit_blocks_delivery(self):
        result = evaluate_delivery_gate({
            "verify_result": {"pass": True},
            "broll_audit": {"pass": False, "next_action": "curator"},
        })

        self.assertFalse(result["pass"])
        self.assertEqual(result["next_action"], "curator")
        self.assertEqual(result["blocking"][0]["rule"], "failed_audit")

    def test_failed_new_visual_information_audit_blocks_delivery(self):
        result = evaluate_delivery_gate({
            "new_visual_information_audit": {"pass": False, "next_action": "curator"},
        })
        self.assertFalse(result["pass"])
        self.assertEqual(result["blocking"][0]["artifact"], "new_visual_information_audit")

    def test_unresolved_material_gap_blocks_delivery(self):
        result = evaluate_delivery_gate({
            "verify_result": {"pass": True},
            "material_coverage": {
                "gaps": [{"segment": 7, "must_include": False, "reason": "no live-line footage"}]
            },
        })

        self.assertFalse(result["pass"])
        self.assertEqual(result["next_action"], "await_material")
        self.assertEqual(result["blocking"][0]["rule"], "unresolved_gap")

    def test_stale_material_coverage_gap_does_not_override_ready_delta(self):
        result = evaluate_delivery_gate({
            "verify_result": {"pass": True},
            "material_coverage": {
                "gaps": [{"segment": 7, "must_include": False, "reason": "legacy gap"}]
            },
            "material_delta": {
                "artifact_role": "material_delta",
                "ok": True,
                "ready_for_build": True,
                "summary": {"covered": 1, "thin": 0, "missing": 0, "excess": 0},
            },
            "material_map_lifecycle": {
                "artifact_role": "material_map_lifecycle",
                "can_build": True,
                "next_action": "build",
            },
        })

        self.assertTrue(result["pass"])
        self.assertEqual(result["blocking"], [])

    def test_contract_run_ready_delta_without_lifecycle_suppresses_stale_coverage_gap(self):
        result = evaluate_delivery_gate({
            "verify_result": {"pass": True},
            "material_coverage": {
                "gaps": [{"segment": 4, "must_include": True, "reason": "legacy coverage gap"}]
            },
            "material_delta": {
                "artifact_role": "material_delta",
                "ok": True,
                "ready_for_build": True,
                "blocks_ready_for_build": False,
                "summary": {"covered": 0, "thin": 0, "missing": 0, "excess": 6},
            },
            "timeline_build": {"clips": [
                {"segment": 4, "source_path": "teacher_words_1.mov", "duration_sec": 6},
            ]},
        })

        self.assertTrue(result["pass"])
        self.assertEqual(result["blocking"], [])

    def test_all_present_gates_pass(self):
        result = evaluate_delivery_gate({
            "verify_result": {"pass": True},
            "broll_audit": {"pass": True},
            "editorial_qa": {"pass": True},
            "material_coverage": {"gaps": []},
        })

        self.assertTrue(result["pass"])
        self.assertIsNone(result["next_action"])

    def test_repeated_finished_master_source_blocks_delivery(self):
        result = evaluate_delivery_gate({
            "verify_result": {"pass": True},
            "timeline_build": {"clips": [
                {"segment": 1, "source_path": r"C:\素材\67期結訓影片-終.mp4", "duration_sec": 10},
                {"segment": 2, "source_path": r"C:\素材\67期結訓影片-終.mp4", "duration_sec": 12},
                {"segment": 3, "source_path": r"C:\素材\67期結訓影片-終.mp4", "duration_sec": 8},
            ]},
        })

        self.assertFalse(result["pass"])
        rules = {item["rule"] for item in result["blocking"]}
        self.assertIn("finished_master_as_source", rules)
        self.assertIn("repeated_source_over_limit", rules)
        self.assertEqual(result["next_action"], "revise_material_selection_or_review")

    def test_excessive_repeated_raw_source_blocks_delivery(self):
        result = evaluate_delivery_gate({
            "verify_result": {"pass": True},
            "timeline_build": {"clips": [
                {"segment": 1, "source_path": "raw_a.mov", "duration_sec": 10},
                {"segment": 2, "source_path": "raw_a.mov", "duration_sec": 10},
                {"segment": 3, "source_path": "raw_a.mov", "duration_sec": 10},
                {"segment": 4, "source_path": "raw_b.mov", "duration_sec": 10},
            ]},
        })

        self.assertFalse(result["pass"])
        self.assertEqual(result["blocking"][0]["rule"], "repeated_source_over_limit")

    def test_single_source_highlight_with_safe_cut_report_allows_repeated_source(self):
        result = evaluate_delivery_gate({
            "verify_result": {"pass": True},
            "segment_contract": {
                "artifact_role": "segment_contract",
                "mode": "single_source_highlight",
            },
            "highlight_cut_report": {
                "artifact_role": "highlight_cut_report",
                "strategy": "safe_reencode_highlight",
                "source_artifact": "rough_cut_plan",
                "stream_copy": False,
                "window_count": 3,
            },
            "timeline_build": {"clips": [
                {"segment": 1, "source_path": "raw_a.webm", "duration_sec": 20},
                {"segment": 2, "source_path": "raw_a.webm", "duration_sec": 20},
                {"segment": 3, "source_path": "raw_a.webm", "duration_sec": 20},
            ]},
        })

        self.assertTrue(result["pass"])
        self.assertEqual(result["blocking"], [])

    def test_rough_cut_plan_gaps_block_delivery(self):
        result = evaluate_delivery_gate({
            "verify_result": {"pass": True},
            "rough_cut_plan": {
                "artifact_role": "rough_cut_plan",
                "ok": False,
                "gaps": [{
                    "segment": 2,
                    "need_id": "nd_closing",
                    "reason": "no accepted scene satisfies the segment need",
                }],
            },
        })

        self.assertFalse(result["pass"])
        self.assertEqual(result["blocking"][0]["rule"], "rough_cut_gap")
        self.assertEqual(result["blocking"][0]["artifact"], "rough_cut_plan")

    def test_timeline_material_map_id_mismatch_blocks_delivery(self):
        result = evaluate_delivery_gate({
            "verify_result": {"pass": True},
            "segment_contract": {
                "segments": [{
                    "segment": 2,
                    "material_map_ids": ["commute_001"],
                    "material_fit": {"need_refs": ["need_commute_motion"]},
                }],
            },
            "project_material_map": {
                "artifact_role": "project_material_map",
                "assets": [
                    {
                        "asset_id": "commute_001",
                        "source": "commute.mp4",
                        "scenes": [{
                            "satisfies": [{"need_id": "need_commute_motion", "status": "accepted"}],
                        }],
                    },
                    {
                        "asset_id": "city_dawn_001",
                        "source": "city_dawn.mp4",
                        "scenes": [{
                            "satisfies": [{"need_id": "need_city_dawn", "status": "accepted"}],
                        }],
                    },
                ],
            },
            "timeline_build": {"clips": [{
                "segment": 2,
                "scene_id": "city_dawn_001:0",
                "source_path": "city_dawn.mp4",
                "duration_sec": 3,
            }]},
        })

        self.assertFalse(result["pass"])
        rules = {item["rule"] for item in result["blocking"]}
        self.assertIn("timeline_material_map_id_mismatch", rules)

    def test_timeline_need_ref_mismatch_blocks_delivery(self):
        result = evaluate_delivery_gate({
            "verify_result": {"pass": True},
            "segment_contract": {
                "segments": [{
                    "segment": 2,
                    "material_fit": {"need_refs": ["need_commute_motion"]},
                }],
            },
            "project_material_map": {
                "artifact_role": "project_material_map",
                "assets": [{
                    "asset_id": "city_dawn_001",
                    "source": "city_dawn.mp4",
                    "scenes": [{
                        "satisfies": [{"need_id": "need_city_dawn", "status": "accepted"}],
                    }],
                }],
            },
            "timeline_build": {"clips": [{
                "segment": 2,
                "scene_id": "city_dawn_001:0",
                "source_path": "city_dawn.mp4",
                "duration_sec": 3,
            }]},
        })

        self.assertFalse(result["pass"])
        rules = {item["rule"] for item in result["blocking"]}
        self.assertIn("timeline_need_ref_mismatch", rules)
        self.assertEqual(result["next_action"], "revise_material_selection_or_review")

    def test_timeline_direct_material_fields_block_mismatch_without_scene_id(self):
        result = evaluate_delivery_gate({
            "verify_result": {"pass": True},
            "segment_contract": {
                "segments": [{
                    "segment": 2,
                    "material_map_ids": ["commute_001"],
                    "material_fit": {"need_refs": ["need_commute_motion"]},
                }],
            },
            "timeline_build": {"clips": [{
                "segment": 2,
                "material_map_id": "city_dawn_001",
                "asset_id": "city_dawn_001",
                "need_id": "need_city_dawn",
                "source_path": "city_dawn.mp4",
                "duration_sec": 3,
            }]},
        })

        self.assertFalse(result["pass"])
        rules = {item["rule"] for item in result["blocking"]}
        self.assertIn("timeline_material_map_id_mismatch", rules)
        self.assertIn("timeline_need_ref_mismatch", rules)

    def test_quality_evidence_does_not_block_delivery(self):
        quality_roles = (
            "visual_audit",
            "presentation_feel_audit",
            "treatment_audit",
            "visual_fatigue_audit",
            "semantic_novelty_audit",
            "action_progression_audit",
            "editorial_qa",
        )
        result = evaluate_delivery_gate({
            role: {"pass": False, "next_action": "dashboard_review"}
            for role in quality_roles
        })
        self.assertTrue(result["pass"])
        self.assertEqual(result["blocking"], [])

    def test_stage0_child_contract_media_requirements_block_without_evidence(self):
        result = evaluate_delivery_gate({
            "verify_result": {"pass": True},
            "segment_contract": {
                "stage0_child_contracts": {
                    "soundtrack": {
                        "artifact_role": "stage0_soundtrack_intent",
                        "music_role": "mixed",
                        "handoff_to": "soundtrack-arranger",
                    },
                    "subtitle_voiceover": {
                        "artifact_role": "stage0_subtitle_voiceover_intent",
                        "language": "zh-TW",
                        "subtitle_required": True,
                        "voiceover_required": True,
                    },
                    "effect": {
                        "artifact_role": "stage0_effect_policy",
                        "activation": "route_to_effect_factory",
                        "required_now": True,
                    },
                },
                "segments": [],
            },
        })

        self.assertFalse(result["pass"])
        rules = {item["rule"] for item in result["blocking"]}
        self.assertIn("missing_stage0_soundtrack_evidence", rules)
        self.assertIn("missing_stage0_subtitle_evidence", rules)
        self.assertIn("missing_stage0_voiceover_evidence", rules)
        self.assertIn("missing_stage0_effect_evidence", rules)

    def test_stage0_child_contract_media_requirements_pass_with_evidence(self):
        result = evaluate_delivery_gate({
            "verify_result": {"pass": True},
            "segment_contract": {
                "stage0_child_contracts": {
                    "soundtrack": {"music_role": "bgm"},
                    "subtitle_voiceover": {
                        "language": "zh-TW",
                        "subtitle_required": True,
                        "voiceover_required": True,
                    },
                    "effect": {
                        "activation": "route_to_effect_factory",
                        "required_now": True,
                    },
                },
                "segments": [],
            },
            "music_manifest": {"tracks": [{"id": "bgm"}]},
            "audio_mix_report": {"audio_stream_present": True, "music_included": True, "narration_included": True},
            "narration_manifest": {"segments": [{"audio_ref": "voice.wav"}]},
            "subtitles": {"path": "subtitles.srt"},
            "effect_render_verification": {"pass": True, "verified_effects": [{"rendered": True, "evidence_refs": ["keyframe_grid.jpg"]}]},
        })

        self.assertTrue(result["pass"], result)

    def test_stage0_required_effect_accepts_remotion_effect_handoff_evidence(self):
        result = evaluate_delivery_gate({
            "verify_result": {"pass": True},
            "segment_contract": {
                "stage0_child_contracts": {
                    "effect": {
                        "artifact_role": "stage0_effect_policy",
                        "activation": "route_to_effect_factory",
                        "required_now": True,
                    },
                },
                "segments": [],
            },
            "remotion_effect_handoff": {
                "artifact_role": "remotion_effect_handoff",
                "status": "ready_for_human_review",
                "accepted_assets": [{
                    "job_id": "rm_fx_material_memory_wall_01",
                    "asset_path": "effects/memory_wall.mp4",
                }],
            },
        })

        self.assertTrue(result["pass"], result)

    def test_stage0_subtitle_voiceover_accepts_build_handoff_evidence(self):
        result = evaluate_delivery_gate({
            "verify_result": {"pass": True},
            "segment_contract": {
                "stage0_child_contracts": {
                    "subtitle_voiceover": {
                        "artifact_role": "stage0_subtitle_voiceover_intent",
                        "subtitle_required": True,
                        "voiceover_required": True,
                    },
                },
                "segments": [],
            },
            "subtitle_voiceover_build_handoff": {
                "artifact_role": "subtitle_voiceover_build_handoff",
                "subtitle_ready": True,
                "voiceover_ready": True,
                "subtitles": "subtitles.srt",
                "narration_manifest": "narration_manifest.json",
            },
        })

        self.assertTrue(result["pass"], result)

    def test_complete_video_gate_blocks_draft_render_without_delivery_artifacts(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "final.mp4").write_bytes(b"not a real video, probe is injected")

            result = evaluate_complete_video_delivery(root, probe={
                "ok": True,
                "streams": [{"codec_type": "video", "duration": "10.0"}],
                "format": {"duration": "10.0"},
            })

        self.assertFalse(result["pass"])
        rules = {item["rule"] for item in result["blocking"]}
        self.assertIn("missing_delivery_requirements", rules)
        self.assertIn("missing_audio_stream", rules)
        self.assertIn("missing_narration_manifest", rules)
        self.assertIn("missing_music_manifest", rules)
        self.assertIn("missing_audio_mix_report", rules)
        self.assertIn("missing_subtitles", rules)

    def test_complete_video_gate_applies_video_only_waiver_to_non_video_obligations(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "final.mp4").write_bytes(b"not a real video, probe is injected")
            (root / "delivery_requirements.json").write_text(
                json.dumps({
                    "artifact_role": "delivery_requirements",
                    "version": 1,
                    "requires_audio": True,
                    "requires_narration": True,
                    "requires_music": True,
                    "requires_subtitles": True,
                    "requires_soundtrack_probe": True,
                }),
                encoding="utf-8",
            )
            self._write_video_only_delivery_waiver(root)

            result = evaluate_complete_video_delivery(root, probe={
                "ok": True,
                "streams": [{"codec_type": "video", "duration": "10.0"}],
                "format": {"duration": "10.0"},
            })

        self.assertTrue(result["pass"], result)
        self.assertEqual(result["blocking"], [])
        self.assertEqual(result["waivers_applied"][0]["artifact"], "video_only_delivery_waiver.json")
        waived_rules = {item["rule"] for item in result["limitations"]}
        self.assertIn("missing_audio_stream", waived_rules)
        self.assertIn("missing_narration_manifest", waived_rules)
        self.assertIn("missing_music_manifest", waived_rules)
        self.assertIn("missing_audio_mix_report", waived_rules)
        self.assertIn("missing_subtitles", waived_rules)
        self.assertIn("missing_soundtrack_probe_report", waived_rules)

    def test_complete_video_gate_partial_video_only_waiver_leaves_unwaived_obligations_blocking(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "final.mp4").write_bytes(b"not a real video, probe is injected")
            (root / "delivery_requirements.json").write_text(
                json.dumps({
                    "artifact_role": "delivery_requirements",
                    "version": 1,
                    "requires_audio": True,
                    "requires_narration": True,
                    "requires_music": True,
                    "requires_subtitles": True,
                    "requires_soundtrack_probe": True,
                }),
                encoding="utf-8",
            )
            self._write_video_only_delivery_waiver(
                root,
                waives=["audio"],
                limitations=["Video-only handoff; no deliverable audio."],
            )

            result = evaluate_complete_video_delivery(root, probe={
                "ok": True,
                "streams": [{"codec_type": "video", "duration": "10.0"}],
                "format": {"duration": "10.0"},
            })

        self.assertFalse(result["pass"])
        blocking_rules = {item["rule"] for item in result["blocking"]}
        limitation_rules = {item["rule"] for item in result["limitations"]}
        self.assertIn("missing_audio_stream", limitation_rules)
        self.assertIn("missing_audio_mix_report", limitation_rules)
        self.assertNotIn("missing_audio_stream", blocking_rules)
        self.assertIn("missing_music_manifest", blocking_rules)
        self.assertIn("missing_soundtrack_probe_report", blocking_rules)
        self.assertIn("missing_subtitles", blocking_rules)
        self.assertIn("missing_narration_manifest", blocking_rules)
        self.assertNotIn("missing_music_manifest", limitation_rules)
        self.assertNotIn("missing_soundtrack_probe_report", limitation_rules)
        self.assertNotIn("missing_subtitles", limitation_rules)
        self.assertNotIn("missing_narration_manifest", limitation_rules)

    def test_complete_video_gate_rejects_invalid_video_only_waiver(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "final.mp4").write_bytes(b"not a real video, probe is injected")
            (root / "delivery_requirements.json").write_text(
                json.dumps({
                    "requires_audio": True,
                    "requires_music": True,
                }),
                encoding="utf-8",
            )
            self._write_video_only_delivery_waiver(root, reviewer="", waives=["audio", "unknown"])

            result = evaluate_complete_video_delivery(root, probe={
                "ok": True,
                "streams": [{"codec_type": "video", "duration": "10.0"}],
                "format": {"duration": "10.0"},
            })

        self.assertFalse(result["pass"])
        self.assertFalse(result["waivers_applied"])
        self.assertTrue(any(item.get("rule") == "invalid_video_only_delivery_waiver" for item in result["warnings"]))
        rules = {item["rule"] for item in result["blocking"]}
        self.assertIn("missing_audio_stream", rules)
        self.assertIn("missing_music_manifest", rules)

    def test_complete_video_gate_does_not_waive_missing_video_or_frame_evidence(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "final.mp4").write_bytes(b"not a real video, probe is injected")
            (root / "delivery_requirements.json").write_text(
                json.dumps({
                    "requires_audio": True,
                    "requires_frame_evidence": True,
                }),
                encoding="utf-8",
            )
            self._write_video_only_delivery_waiver(root)

            result = evaluate_complete_video_delivery(root, probe={
                "ok": True,
                "streams": [{"codec_type": "audio", "duration": "10.0"}],
                "format": {"duration": "10.0"},
            })

        self.assertFalse(result["pass"])
        rules = {item["rule"] for item in result["blocking"]}
        self.assertIn("missing_video_stream", rules)
        self.assertIn("missing_frame_evidence", rules)
        self.assertNotIn("missing_audio_stream", rules)

    def test_complete_video_gate_accepts_required_delivery_artifacts(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "final.mp4").write_bytes(b"not a real video, probe is injected")
            (root / "delivery_requirements.json").write_text(
                """{
  "artifact_role": "delivery_requirements",
  "version": 1,
  "requires_audio": true,
  "requires_narration": true,
  "requires_music": true,
  "requires_subtitles": true,
  "preferred_voiceover_provider": "voxcpm",
  "fallback_allowed": false
}""",
                encoding="utf-8",
            )
            self._write_voxcpm_evidence(root)
            (root / "narration_manifest.json").write_text(
                """{
  "artifact_role": "narration_manifest",
  "version": 1,
  "provider": "voxcpm",
  "segments": [{"id": "n1", "text": "第一幕開始", "audio_ref": "narration.wav"}]
}""",
                encoding="utf-8",
            )
            self._write_silent_wav(root / "narration.wav")
            self._write_valid_music_evidence(root)
            (root / "audio_mix_report.json").write_text(
                """{
  "artifact_role": "audio_mix_report",
  "version": 1,
  "audio_stream_present": true,
  "narration_included": true,
  "music_included": true
}""",
                encoding="utf-8",
            )
            (root / "subtitles.srt").write_text(
                "1\n00:00:00,000 --> 00:00:03,000\n第一幕開始\n",
                encoding="utf-8",
            )
            (root / "subtitle_audio_alignment_report.json").write_text(
                json.dumps({
                    "artifact_role": "subtitle_audio_alignment_report",
                    "ok": True,
                    "items": [{"type": "voxcpm_transcript", "text": "第一幕開始", "corresponds_to_audible_audio": True}],
                }, ensure_ascii=False),
                encoding="utf-8",
            )

            result = evaluate_complete_video_delivery(root, probe={
                "ok": True,
                "streams": [
                    {"codec_type": "video", "duration": "10.0"},
                    {"codec_type": "audio", "duration": "10.0"},
                ],
                "format": {"duration": "10.0"},
            })

        self.assertTrue(result["pass"])
        self.assertEqual(result["blocking"], [])

    def test_complete_video_gate_blocks_placeholder_final_with_clear_finding(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_complete_delivery_artifacts(root)

            result = evaluate_complete_video_delivery(root)

        self.assertFalse(result["pass"])
        media_blocks = [
            item for item in result["blocking"]
            if item.get("artifact") == "final.mp4" and item.get("rule") == "media_probe_failed"
        ]
        self.assertTrue(media_blocks, result)
        self.assertIn("not a valid playable media file", media_blocks[0]["message"])

    def test_complete_video_gate_uses_subtitle_voiceover_build_handoff_refs(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "handoff").mkdir()
            (root / "final.mp4").write_bytes(b"not a real video, probe is injected")
            (root / "delivery_requirements.json").write_text(
                """{
  "artifact_role": "delivery_requirements",
  "version": 1,
  "requires_audio": true,
  "requires_narration": true,
  "requires_music": true,
  "requires_subtitles": true,
  "preferred_voiceover_provider": "voxcpm",
  "fallback_allowed": false,
  "language": "zh-TW"
}""",
                encoding="utf-8",
            )
            self._write_voxcpm_evidence(root)
            (root / "subtitle_voiceover_build_handoff.json").write_text(
                """{
  "artifact_role": "subtitle_voiceover_build_handoff",
  "version": 1,
  "subtitle_ready": true,
  "voiceover_ready": true,
  "subtitles": "handoff/subtitles.srt",
  "narration_manifest": "handoff/narration_manifest.json"
}""",
                encoding="utf-8",
            )
            (root / "handoff" / "narration_manifest.json").write_text(
                """{
  "artifact_role": "narration_manifest",
  "version": 1,
  "segments": [{"id": "n1", "text": "完成交接。", "audio_ref": "handoff/narration.wav"}]
}""",
                encoding="utf-8",
            )
            self._write_silent_wav(root / "handoff" / "narration.wav")
            self._write_valid_music_evidence(root)
            (root / "audio_mix_report.json").write_text(
                """{
  "artifact_role": "audio_mix_report",
  "version": 1,
  "audio_stream_present": true,
  "narration_included": true,
  "music_included": true
}""",
                encoding="utf-8",
            )
            (root / "handoff" / "subtitles.srt").write_text(
                "1\n00:00:00,000 --> 00:00:03,000\n完成交接。\n",
                encoding="utf-8",
            )
            (root / "subtitle_audio_alignment_report.json").write_text(
                json.dumps({
                    "artifact_role": "subtitle_audio_alignment_report",
                    "ok": True,
                    "items": [{"type": "voxcpm_transcript", "text": "完成交接。", "corresponds_to_audible_audio": True}],
                }, ensure_ascii=False),
                encoding="utf-8",
            )

            result = evaluate_complete_video_delivery(root, probe={
                "ok": True,
                "streams": [
                    {"codec_type": "video", "duration": "10.0"},
                    {"codec_type": "audio", "duration": "10.0"},
                ],
                "format": {"duration": "10.0"},
            })

        self.assertTrue(result["pass"], result)
        self.assertEqual(result["blocking"], [])

    def test_complete_video_gate_blocks_unreadable_review_artifacts_and_language_mismatch(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_complete_delivery_artifacts(root, language="zh-TW", subtitles="English only subtitle")
            (root / "agent_interaction_log.md").write_text("Agent: status pass \ue123", encoding="utf-8")

            result = evaluate_complete_video_delivery(root, probe=self._probe_with_audio_video())

        self.assertFalse(result["pass"])
        rules = {item["rule"] for item in result["blocking"]}
        self.assertIn("corrupt_review_artifact", rules)
        self.assertIn("subtitle_language_mismatch", rules)

    def test_complete_video_gate_blocks_generated_material_without_consistency_review(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_complete_delivery_artifacts(root)
            (root / "material_generation_fallback.json").write_text("{}", encoding="utf-8")
            (root / "generated_provider_packet.json").write_text("{}", encoding="utf-8")
            (root / "generated_material_review.json").write_text(
                """{
  "artifact_role": "generated_material_review",
  "version": 1,
  "pass": true,
  "accepted_assets": ["scene_01.png"],
  "findings": ["????"]
}""",
                encoding="utf-8",
            )

            result = evaluate_complete_video_delivery(root, probe=self._probe_with_audio_video())

        self.assertFalse(result["pass"])
        rules = {item["rule"] for item in result["blocking"]}
        self.assertIn("corrupt_generated_material_review", rules)
        self.assertIn("missing_generated_material_consistency_review", rules)

    def test_complete_video_gate_accepts_generated_material_with_consistency_review(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_complete_delivery_artifacts(root)
            (root / "material_generation_fallback.json").write_text(
                """{
  "artifact_role": "material_generation_fallback",
  "version": 1,
  "ok": true,
  "generation_jobs": [{"job_id": "job_01", "need_id": "need_01"}]
}""",
                encoding="utf-8",
            )
            (root / "scene_01.png").write_bytes(b"fake image bytes")
            (root / "generated_provider_packet.json").write_text(
                """{
  "artifact_role": "generated_provider_packet",
  "version": 1,
  "jobs": [
    {
      "job_id": "job_01",
      "need_id": "need_01",
      "asset_id": "scene_01.png",
      "target_file": "scene_01.png",
      "prompt": "bright picture book scene",
      "truth_controls": {
        "source_truth": "generated",
        "truth_usage": "illustrative",
        "must_disclose_generated": true
      }
    }
  ]
}""",
                encoding="utf-8",
            )
            (root / "generated_material_review.json").write_text(
                """{
  "artifact_role": "generated_material_review",
  "version": 1,
  "pass": true,
  "accepted_assets": ["scene_01.png"],
  "consistency_review": {
    "pass": true,
    "story_match": true,
    "character_consistency": true,
    "segment_alignment": true,
    "findings": ["all generated assets match the locked story bible"]
  }
}""",
                encoding="utf-8",
            )

            result = evaluate_complete_video_delivery(root, probe=self._probe_with_audio_video())

        self.assertTrue(result["pass"])

    def test_complete_video_gate_blocks_generated_material_without_prompt_jobs(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_complete_delivery_artifacts(root)
            (root / "material_generation_fallback.json").write_text(
                """{
  "artifact_role": "material_generation_fallback",
  "version": 1,
  "ok": false,
  "generation_jobs": []
}""",
                encoding="utf-8",
            )
            (root / "generated_provider_packet.json").write_text(
                """{
  "artifact_role": "generated_provider_packet",
  "version": 1,
  "jobs": []
}""",
                encoding="utf-8",
            )
            (root / "generated_material_review.json").write_text(
                """{
  "artifact_role": "generated_material_review",
  "version": 1,
  "pass": true,
  "accepted_assets": ["scene_01.png"],
  "consistency_review": {"pass": true}
}""",
                encoding="utf-8",
            )

            result = evaluate_complete_video_delivery(root, probe=self._probe_with_audio_video())

        self.assertFalse(result["pass"])
        rules = {item["rule"] for item in result["blocking"]}
        self.assertIn("generated_fallback_not_ok", rules)
        self.assertIn("generated_provider_packet_has_no_jobs", rules)

    def test_complete_video_gate_blocks_accepted_generated_asset_without_prompt_lineage(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_complete_delivery_artifacts(root)
            (root / "material_generation_fallback.json").write_text(
                """{
  "artifact_role": "material_generation_fallback",
  "version": 1,
  "ok": true,
  "generation_jobs": [{"job_id": "job_01", "need_id": "need_01"}]
}""",
                encoding="utf-8",
            )
            (root / "generated_provider_packet.json").write_text(
                """{
  "artifact_role": "generated_provider_packet",
  "version": 1,
  "jobs": [
    {
      "job_id": "job_01",
      "need_id": "need_01",
      "asset_id": "scene_02.png",
      "target_file": "scene_02.png",
      "prompt": "wrong asset"
    }
  ]
}""",
                encoding="utf-8",
            )
            (root / "generated_material_review.json").write_text(
                """{
  "artifact_role": "generated_material_review",
  "version": 1,
  "pass": true,
  "accepted_assets": ["scene_01.png"],
  "consistency_review": {"pass": true}
}""",
                encoding="utf-8",
            )

            result = evaluate_complete_video_delivery(root, probe=self._probe_with_audio_video())

        self.assertFalse(result["pass"])
        rules = {item["rule"] for item in result["blocking"]}
        self.assertIn("accepted_generated_asset_missing_prompt_lineage", rules)

    def test_complete_video_gate_blocks_generated_job_without_truth_controls(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_complete_delivery_artifacts(root)
            (root / "material_generation_fallback.json").write_text(
                """{
  "artifact_role": "material_generation_fallback",
  "version": 1,
  "ok": true,
  "generation_jobs": [{"job_id": "job_01", "need_id": "need_01"}]
}""",
                encoding="utf-8",
            )
            (root / "scene_01.png").write_bytes(b"fake image bytes")
            (root / "generated_provider_packet.json").write_text(
                """{
  "artifact_role": "generated_provider_packet",
  "version": 1,
  "jobs": [
    {
      "job_id": "job_01",
      "need_id": "need_01",
      "asset_id": "scene_01.png",
      "target_file": "scene_01.png",
      "prompt": "bright picture book scene"
    }
  ]
}""",
                encoding="utf-8",
            )
            (root / "generated_material_review.json").write_text(
                """{
  "artifact_role": "generated_material_review",
  "version": 1,
  "pass": true,
  "accepted_assets": ["scene_01.png"],
  "consistency_review": {"pass": true}
}""",
                encoding="utf-8",
            )

            result = evaluate_complete_video_delivery(root, probe=self._probe_with_audio_video())

        self.assertFalse(result["pass"])
        rules = {item["rule"] for item in result["blocking"]}
        self.assertIn("generated_provider_job_missing_truth_controls", rules)

    def test_complete_video_gate_accepts_reference_guided_generated_with_reference_assets(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_complete_delivery_artifacts(root)
            (root / "reference.jpg").write_bytes(b"fake reference bytes")
            (root / "scene_01.png").write_bytes(b"fake image bytes")
            (root / "material_generation_fallback.json").write_text(
                """{
  "artifact_role": "material_generation_fallback",
  "version": 1,
  "ok": true,
  "generation_jobs": [{"job_id": "job_01", "need_id": "need_01"}]
}""",
                encoding="utf-8",
            )
            (root / "generated_provider_packet.json").write_text(
                """{
  "artifact_role": "generated_provider_packet",
  "version": 1,
  "jobs": [
    {
      "job_id": "job_01",
      "need_id": "need_01",
      "asset_id": "scene_01.png",
      "target_file": "scene_01.png",
      "prompt": "reference guided support image",
      "reference_controls": {
        "mode": "style_reference",
        "reference_assets": ["reference.jpg"],
        "preserve": ["warm classroom palette"],
        "avoid": ["fake proof moment"]
      },
      "truth_controls": {
        "source_truth": "reference_guided_generated",
        "truth_usage": "support",
        "must_disclose_generated": true
      }
    }
  ]
}""",
                encoding="utf-8",
            )
            (root / "generated_material_review.json").write_text(
                """{
  "artifact_role": "generated_material_review",
  "version": 1,
  "pass": true,
  "accepted_assets": ["scene_01.png"],
  "consistency_review": {"pass": true}
}""",
                encoding="utf-8",
            )

            result = evaluate_complete_video_delivery(root, probe=self._probe_with_audio_video())

        self.assertTrue(result["pass"])

    def test_complete_video_gate_blocks_narration_fallback_without_explicit_waiver(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_complete_delivery_artifacts(root)
            (root / "narration_manifest.json").write_text(
                """{
  "artifact_role": "narration_manifest",
  "version": 1,
  "source": "fallback sine cue because TTS failed",
  "segments": [{"id": "n1", "text": "第一幕開始", "audio_ref": "narration.wav"}]
}""",
                encoding="utf-8",
            )
            (root / "narration.wav").write_bytes(b"not really probed in this assertion")

            result = evaluate_complete_video_delivery(root, probe=self._probe_with_audio_video())

        self.assertFalse(result["pass"])
        rules = {item["rule"] for item in result["blocking"]}
        self.assertIn("narration_declares_fallback", rules)

    def test_complete_video_gate_requires_frame_evidence_for_real_material_route(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_complete_delivery_artifacts(root)
            (root / "video_intent.json").write_text(
                """{
  "artifact_role": "video_intent",
  "route": "existing-material-first",
  "material_availability": "existing_real_material"
}""",
                encoding="utf-8",
            )

            result = evaluate_complete_video_delivery(root, probe=self._probe_with_audio_video())

        self.assertFalse(result["pass"])
        rules = {item["rule"] for item in result["blocking"]}
        self.assertIn("missing_frame_evidence", rules)

    def test_complete_video_gate_accepts_real_material_route_with_frame_evidence(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_complete_delivery_artifacts(root)
            (root / "video_intent.json").write_text(
                """{
  "artifact_role": "video_intent",
  "route": "existing-material-first",
  "material_availability": "existing_real_material"
}""",
                encoding="utf-8",
            )
            (root / "frame_evidence.json").write_text(
                """{
  "artifact_role": "frame_evidence",
  "version": 1,
  "pass": true,
  "inspected_assets": [
    {
      "asset_id": "real_01",
      "frames": [{"time_sec": 1.0, "ref": "frames/real_01_001.jpg"}],
      "observations": ["學員正在進行訓練操作"],
      "semantic_match": true
    }
  ]
}""",
                encoding="utf-8",
            )

            result = evaluate_complete_video_delivery(root, probe=self._probe_with_audio_video())

        self.assertTrue(result["pass"])

    def test_complete_video_gate_requires_effect_render_verification_when_effects_are_planned(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_complete_delivery_artifacts(root)
            (root / "effect_intent_plan.json").write_text(
                """{
  "artifact_role": "effect_intent_plan",
  "version": 1,
  "effects": [{"effect_id": "e1", "type": "lower_third", "render_required": true}]
}""",
                encoding="utf-8",
            )

            result = evaluate_complete_video_delivery(root, probe=self._probe_with_audio_video())

        self.assertFalse(result["pass"])
        rules = {item["rule"] for item in result["blocking"]}
        self.assertIn("missing_effect_render_verification", rules)

    def test_complete_video_gate_accepts_verified_rendered_effects(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_complete_delivery_artifacts(root)
            (root / "effect_intent_plan.json").write_text(
                """{
  "artifact_role": "effect_intent_plan",
  "version": 1,
  "effects": [{"effect_id": "e1", "type": "lower_third", "render_required": true}]
}""",
                encoding="utf-8",
            )
            (root / "effect_render_verification.json").write_text(
                """{
  "artifact_role": "effect_render_verification",
  "version": 1,
  "pass": true,
  "verified_effects": [
    {
      "effect_id": "e1",
      "kind": "lower_third",
      "rendered": true,
      "evidence_refs": ["frames/e1_sample.jpg"]
    }
  ]
}""",
                encoding="utf-8",
            )

            result = evaluate_complete_video_delivery(root, probe=self._probe_with_audio_video())

        self.assertTrue(result["pass"])

    def test_complete_video_gate_uses_artifact_manifest_branch_handoff_paths(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            handoff = root / "handoff"
            handoff.mkdir()
            (root / "final.mp4").write_bytes(b"not a real video, probe is injected")
            (root / "delivery_requirements.json").write_text(
                json.dumps({
                    "artifact_role": "delivery_requirements",
                    "version": 1,
                    "requires_audio": True,
                    "requires_narration": True,
                    "requires_music": True,
                    "requires_subtitles": True,
                    "requires_soundtrack_probe": True,
                    "requires_effect_render_verification": True,
                    "preferred_voiceover_provider": "voxcpm",
                    "fallback_allowed": False,
                }),
                encoding="utf-8",
            )
            (root / "artifact_manifest.json").write_text(
                json.dumps({
                    "artifact_role": "artifact_manifest",
                    "subtitle_voiceover_build_handoff": "handoff/subtitle_voiceover_build_handoff.json",
                    "narration_manifest": "handoff/narration_manifest.json",
                    "voiceover_provider_plan": "handoff/voiceover_provider_plan.json",
                    "voxcpm_runtime_check": "handoff/voxcpm_runtime_check.json",
                    "music_manifest": "handoff/music_manifest.json",
                    "audio_mix_report": "handoff/audio_mix_report.json",
                    "soundtrack_probe_report": "handoff/soundtrack_probe_report.json",
                    "effect_render_verification": "handoff/effect_render_verification.json",
                    "subtitle_audio_alignment_report": "handoff/subtitle_audio_alignment_report.json",
                }),
                encoding="utf-8",
            )
            (handoff / "subtitle_voiceover_build_handoff.json").write_text(
                json.dumps({
                    "artifact_role": "subtitle_voiceover_build_handoff",
                    "subtitle_ready": True,
                    "voiceover_ready": True,
                    "subtitles": "handoff/subtitles.srt",
                    "narration_manifest": "handoff/narration_manifest.json",
                }),
                encoding="utf-8",
            )
            (handoff / "subtitles.srt").write_text(
                "1\n00:00:00,000 --> 00:00:03,000\n完成這段精神傳承\n",
                encoding="utf-8",
            )
            (handoff / "subtitle_audio_alignment_report.json").write_text(
                json.dumps({
                    "artifact_role": "subtitle_audio_alignment_report",
                    "ok": True,
                    "items": [{"type": "voxcpm_transcript", "text": "完成這段精神傳承", "corresponds_to_audible_audio": True}],
                }, ensure_ascii=False),
                encoding="utf-8",
            )
            (handoff / "narration_manifest.json").write_text(
                json.dumps({
                    "artifact_role": "narration_manifest",
                    "provider": "voxcpm",
                    "segments": [{"id": "n1", "text": "完成這段精神傳承", "audio_ref": "handoff/narration.wav"}],
                }, ensure_ascii=False),
                encoding="utf-8",
            )
            (handoff / "voxcpm_runtime_check.json").write_text(
                json.dumps({
                    "artifact_role": "voxcpm_runtime_check",
                    "version": 1,
                    "ok_to_execute": True,
                    "voxcpm_repo": "reference repo/VoxCPM-main",
                }),
                encoding="utf-8",
            )
            (handoff / "voiceover_provider_plan.json").write_text(
                json.dumps({
                    "artifact_role": "voiceover_provider_plan",
                    "version": 1,
                    "requested_provider": "voxcpm",
                    "selected_provider": "voxcpm",
                    "provider_available": True,
                    "fallback_allowed": False,
                    "fallback_used": False,
                }),
                encoding="utf-8",
            )
            self._write_silent_wav(handoff / "narration.wav")
            (handoff / "music_manifest.json").write_text(
                json.dumps({
                    "artifact_role": "music_manifest",
                    "source_type": "licensed_library",
                    "license_note": "test fixture licensed-library metadata",
                    "tracks": [{"id": "bgm", "source_type": "licensed_library", "source_ref": "licensed_music.wav", "license_note": "test fixture licensed-library metadata"}],
                    "cues": [{"track_id": "bgm", "start_sec": 0.0, "end_sec": 10.0}],
                }),
                encoding="utf-8",
            )
            (handoff / "audio_mix_report.json").write_text(
                json.dumps({
                    "artifact_role": "audio_mix_report",
                    "audio_stream_present": True,
                    "narration_included": True,
                    "music_included": True,
                    "peak_dbfs": -3.0,
                }),
                encoding="utf-8",
            )
            (handoff / "soundtrack_probe_report.json").write_text(
                json.dumps({
                    "artifact_role": "soundtrack_probe_report",
                    "pass": True,
                    "features": {"mean_dbfs": -18.0, "peak_dbfs": -3.0},
                    "sections": [{"start_sec": 0.0, "end_sec": 10.0}],
                    "editing_fit": {"speech_underlay": "low"},
                    "section_fit": [{"section_id": "closing", "fit": "medium"}],
                }),
                encoding="utf-8",
            )
            (handoff / "effect_render_verification.json").write_text(
                json.dumps({
                    "artifact_role": "effect_render_verification",
                    "pass": True,
                    "verified_effects": [{
                        "effect_id": "closing_glow",
                        "rendered": True,
                        "evidence_refs": ["handoff/effect_sample.jpg"],
                    }],
                }),
                encoding="utf-8",
            )

            result = evaluate_complete_video_delivery(root, probe=self._probe_with_audio_video())

        self.assertTrue(result["pass"], result)

    def test_complete_video_gate_blocks_stale_manifest_audio_mix_path(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_complete_delivery_artifacts(root)
            (root / "artifact_manifest.json").write_text(
                json.dumps({
                    "artifact_role": "artifact_manifest",
                    "audio_mix_report": "handoff/missing_audio_mix_report.json",
                }),
                encoding="utf-8",
            )

            result = evaluate_complete_video_delivery(root, probe=self._probe_with_audio_video())

        self.assertFalse(result["pass"])
        rules = {item["rule"] for item in result["blocking"]}
        self.assertIn("artifact_manifest_stale", rules)
        self.assertIn("missing_audio_mix_report", rules)

    def test_complete_video_gate_reads_nested_artifact_manifest_paths(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_complete_delivery_artifacts(root)
            handoff = root / "handoff"
            handoff.mkdir()
            (root / "audio_mix_report.json").unlink()
            (handoff / "audio_mix_report.json").write_text(
                json.dumps({
                    "artifact_role": "audio_mix_report",
                    "version": 1,
                    "audio_stream_present": True,
                    "narration_included": True,
                    "music_included": True,
                }),
                encoding="utf-8",
            )
            (root / "artifact_manifest.json").write_text(
                json.dumps({
                    "artifact_role": "artifact_manifest",
                    "artifacts": {
                        "audio_mix_report": {"path": "handoff/audio_mix_report.json"},
                    },
                }),
                encoding="utf-8",
            )

            result = evaluate_complete_video_delivery(root, probe=self._probe_with_audio_video())

        self.assertTrue(result["pass"], result)

    def _write_complete_delivery_artifacts(self, root, *, language=None, subtitles="第一幕開始"):
        (root / "final.mp4").write_bytes(b"not a real video, probe is injected")
        language_line = f'  "language": "{language}",\n' if language else ""
        (root / "delivery_requirements.json").write_text(
            "{\n"
            '  "artifact_role": "delivery_requirements",\n'
            '  "version": 1,\n'
            f"{language_line}"
            '  "requires_audio": true,\n'
            '  "requires_narration": true,\n'
            '  "requires_music": true,\n'
            '  "requires_subtitles": true,\n'
            '  "preferred_voiceover_provider": "voxcpm",\n'
            '  "fallback_allowed": false\n'
            "}",
            encoding="utf-8",
        )
        (root / "voxcpm_runtime_check.json").write_text(
            """{
  "artifact_role": "voxcpm_runtime_check",
  "version": 1,
  "ok_to_execute": true,
  "voxcpm_repo": "reference repo/VoxCPM-main"
}""",
            encoding="utf-8",
        )
        (root / "voiceover_provider_plan.json").write_text(
            """{
  "artifact_role": "voiceover_provider_plan",
  "version": 1,
  "requested_provider": "voxcpm",
  "selected_provider": "voxcpm",
  "provider_available": true,
  "fallback_allowed": false,
  "fallback_used": false
}""",
            encoding="utf-8",
        )
        (root / "narration_manifest.json").write_text(
            """{
  "artifact_role": "narration_manifest",
  "version": 1,
  "provider": "voxcpm",
  "segments": [{"id": "n1", "text": "第一幕開始", "audio_ref": "narration.wav"}]
}""",
            encoding="utf-8",
        )
        self._write_silent_wav(root / "narration.wav")
        (root / "music_manifest.json").write_text(
            """{
  "artifact_role": "music_manifest",
  "version": 1,
  "source_type": "licensed_library",
  "license_note": "test fixture licensed-library metadata",
  "tracks": [{"id": "m1", "source_type": "licensed_library", "source_ref": "licensed_music.wav", "license_note": "test fixture licensed-library metadata"}],
  "cues": [{"track_id": "m1", "start_sec": 0.0, "end_sec": 10.0}]
}""",
            encoding="utf-8",
        )
        (root / "soundtrack_probe_report.json").write_text(
            """{
  "artifact_role": "soundtrack_probe_report",
  "version": 1,
  "pass": true,
  "audio_file": "licensed_music.wav",
  "duration_sec": 10.0,
  "features": {"mean_dbfs": -18.0, "peak_dbfs": -3.0},
  "sections": [{"start_sec": 0.0, "end_sec": 10.0, "role": "full_track"}],
  "editing_fit": {"montage": "medium"},
  "section_fit": [{"video_section": "all", "fit": "medium"}]
}""",
            encoding="utf-8",
        )
        (root / "audio_mix_report.json").write_text(
            """{
  "artifact_role": "audio_mix_report",
  "version": 1,
  "audio_stream_present": true,
  "narration_included": true,
  "music_included": true
}""",
            encoding="utf-8",
        )
        (root / "subtitles.srt").write_text(
            f"1\n00:00:00,000 --> 00:00:03,000\n{subtitles}\n",
            encoding="utf-8",
        )
        (root / "subtitle_audio_alignment_report.json").write_text(
            json.dumps({
                "artifact_role": "subtitle_audio_alignment_report",
                "version": 1,
                "ok": True,
                "items": [{
                    "type": "voxcpm_transcript",
                    "text": subtitles,
                    "corresponds_to_audible_audio": True,
                }],
            }, ensure_ascii=False),
            encoding="utf-8",
        )

    def test_complete_video_gate_accepts_existing_visual_audit_for_effect_evidence(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_complete_delivery_artifacts(root)
            (root / "effect_intent_plan.json").write_text(
                """{
  "artifact_role": "effect_intent_plan",
  "version": 1,
  "effects": [{"effect_id": "e1", "type": "lower_third", "render_required": true}]
}""",
                encoding="utf-8",
            )
            (root / "keyframe_grid.jpg").write_bytes(b"fake grid bytes")
            (root / "visual_audit.json").write_text(
                """{
  "artifact_role": "visual_audit",
  "version": 1,
  "pass": true,
  "grid": "keyframe_grid.jpg",
  "samples": [{"timestamp_sec": 1.0, "cell": 1}]
}""",
                encoding="utf-8",
            )
            (root / "effect_render_verification.json").write_text(
                """{
  "artifact_role": "effect_render_verification",
  "version": 1,
  "pass": true,
  "visual_audit_ref": "visual_audit.json",
  "keyframe_grid_ref": "keyframe_grid.jpg",
  "verified_effects": [
    {
      "effect_id": "e1",
      "kind": "lower_third",
      "rendered": true
    }
  ]
}""",
                encoding="utf-8",
            )

            result = evaluate_complete_video_delivery(root, probe=self._probe_with_audio_video())

        self.assertTrue(result["pass"])

    def test_complete_video_gate_blocks_preview_only_audio_mix_even_with_valid_media(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_complete_delivery_artifacts(root)
            (root / "audio_mix_report.json").write_text(
                json.dumps({
                    "artifact_role": "audio_mix_report",
                    "version": 1,
                    "ok": True,
                    "audio_stream_present": True,
                    "narration_included": True,
                    "music_included": True,
                    "peak_dbfs": -3.0,
                    "preview_only": True,
                    "delivery_allowed": False,
                    "usage_scope": "internal_technical_reference",
                    "external_publication_requires_rights_review": True,
                    "placements": [],
                }),
                encoding="utf-8",
            )

            result = evaluate_complete_video_delivery(root, probe=self._probe_with_audio_video())

        self.assertFalse(result["pass"])
        rules = {item["rule"] for item in result["blocking"]}
        self.assertIn("preview_only_audio_not_delivery_allowed", rules)

    def test_complete_video_gate_blocks_music_that_should_duck_but_did_not(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_complete_delivery_artifacts(root)
            (root / "audio_mix_report.json").write_text(
                """{
  "artifact_role": "audio_mix_report",
  "version": 1,
  "audio_stream_present": true,
  "narration_included": true,
  "music_included": true,
  "placements": [
    {
      "section_id": "director_words",
      "role": "music_bed",
      "ducking_policy": "duck_under_voice",
      "ducking_applied": false,
      "applied_volume": 1.0
    },
    {
      "section_id": "director_words",
      "role": "voice",
      "ducking_policy": "preserve_original_audio",
      "ducking_applied": false,
      "applied_volume": 1.0
    }
  ]
}""",
                encoding="utf-8",
            )

            result = evaluate_complete_video_delivery(root, probe=self._probe_with_audio_video())

        self.assertFalse(result["pass"])
        rules = {item["rule"] for item in result["blocking"]}
        self.assertIn("required_audio_ducking_not_applied", rules)

    def test_complete_video_gate_blocks_audio_mix_peak_too_hot(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_complete_delivery_artifacts(root)
            (root / "audio_mix_report.json").write_text(
                """{
  "artifact_role": "audio_mix_report",
  "version": 1,
  "audio_stream_present": true,
  "narration_included": true,
  "music_included": true,
  "peak_dbfs": -0.1
}""",
                encoding="utf-8",
            )

            result = evaluate_complete_video_delivery(root, probe=self._probe_with_audio_video())

        self.assertFalse(result["pass"])
        rules = {item["rule"] for item in result["blocking"]}
        self.assertIn("audio_mix_peak_too_hot", rules)

    def test_complete_video_gate_requires_soundtrack_probe_when_requested(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_complete_delivery_artifacts(root)
            (root / "soundtrack_probe_report.json").unlink()
            requirements = json.loads((root / "delivery_requirements.json").read_text(encoding="utf-8"))
            requirements["requires_soundtrack_probe"] = True
            (root / "delivery_requirements.json").write_text(
                json.dumps(requirements),
                encoding="utf-8",
            )

            result = evaluate_complete_video_delivery(root, probe=self._probe_with_audio_video())

        self.assertFalse(result["pass"])
        rules = {item["rule"] for item in result["blocking"]}
        self.assertIn("missing_soundtrack_probe_report", rules)

    def test_complete_video_gate_accepts_valid_soundtrack_probe_when_requested(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_complete_delivery_artifacts(root)
            requirements = json.loads((root / "delivery_requirements.json").read_text(encoding="utf-8"))
            requirements["requires_soundtrack_probe"] = True
            (root / "delivery_requirements.json").write_text(json.dumps(requirements), encoding="utf-8")
            (root / "soundtrack_probe_report.json").write_text(
                json.dumps({
                    "artifact_role": "soundtrack_probe_report",
                    "version": 1,
                    "pass": True,
                    "audio_file": "music.wav",
                    "duration_sec": 60.0,
                    "features": {"mean_dbfs": -18.0, "peak_dbfs": -2.0},
                    "sections": [{"start_sec": 0.0, "end_sec": 60.0, "role": "full_track"}],
                    "editing_fit": {"speech_underlay": "low", "montage": "medium"},
                    "section_fit": [{"video_section": "hotblooded_montage", "fit": "medium"}],
                }),
                encoding="utf-8",
            )

            result = evaluate_complete_video_delivery(root, probe=self._probe_with_audio_video())

        self.assertTrue(result["pass"], result)

    def test_complete_video_gate_requires_vocal_analysis_when_requested(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_complete_delivery_artifacts(root)
            requirements = json.loads((root / "delivery_requirements.json").read_text(encoding="utf-8"))
            requirements["requires_soundtrack_probe"] = True
            requirements["requires_vocal_conflict_check"] = True
            (root / "delivery_requirements.json").write_text(json.dumps(requirements), encoding="utf-8")
            (root / "soundtrack_probe_report.json").write_text(
                json.dumps({
                    "artifact_role": "soundtrack_probe_report",
                    "version": 1,
                    "pass": True,
                    "audio_file": "music.wav",
                    "duration_sec": 60.0,
                    "features": {
                        "mean_dbfs": -18.0,
                        "peak_dbfs": -2.0,
                        "vocal_analysis": {"has_vocals": "unknown", "method": "not_run"},
                    },
                    "sections": [{"start_sec": 0.0, "end_sec": 60.0, "role": "full_track"}],
                    "editing_fit": {"speech_underlay": "unknown", "montage": "medium"},
                    "section_fit": [{"video_section": "speech_underlay", "fit": "unknown"}],
                }),
                encoding="utf-8",
            )

            result = evaluate_complete_video_delivery(root, probe=self._probe_with_audio_video())

        self.assertFalse(result["pass"])
        rules = {item["rule"] for item in result["blocking"]}
        self.assertIn("soundtrack_probe_missing_vocal_analysis", rules)

    def test_scripted_gate_blocks_corrupt_chinese_text_across_script_narration_subtitles_and_alignment(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_complete_delivery_artifacts(root)
            (root / "script.json").write_text(
                json.dumps({
                    "artifact_role": "script",
                    "segments": [{"segment": "opening_bridge", "text": "????"}],
                }),
                encoding="utf-8",
            )
            (root / "narration_manifest.json").write_text(
                json.dumps({
                    "artifact_role": "narration_manifest",
                    "segments": [{"id": "n1", "text": "????", "audio_ref": "narration.wav"}],
                }),
                encoding="utf-8",
            )
            (root / "subtitles.srt").write_text(
                "1\n00:00:00,000 --> 00:00:03,000\n????\n",
                encoding="utf-8",
            )
            (root / "subtitle_audio_alignment_report.json").write_text(
                json.dumps({
                    "artifact_role": "subtitle_audio_alignment_report",
                    "ok": True,
                    "items": [{"type": "voxcpm_transcript", "text": "????"}],
                }),
                encoding="utf-8",
            )

            result = evaluate_complete_video_delivery(root, probe=self._probe_with_audio_video())

        self.assertFalse(result["pass"])
        rules = {item["rule"] for item in result["blocking"]}
        self.assertIn("corrupt_script_text", rules)
        self.assertIn("corrupt_narration_manifest", rules)
        self.assertIn("corrupt_subtitles", rules)
        self.assertIn("corrupt_subtitle_alignment", rules)

    def test_scripted_gate_blocks_missing_subtitle_audio_alignment_report(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_complete_delivery_artifacts(root)
            (root / "subtitle_audio_alignment_report.json").unlink()

            result = evaluate_complete_video_delivery(root, probe=self._probe_with_audio_video())

        self.assertFalse(result["pass"])
        rules = {item["rule"] for item in result["blocking"]}
        self.assertIn("missing_subtitle_audio_alignment_report", rules)

    def test_scripted_gate_blocks_false_alignment_and_unlabeled_editorial_subtitles(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_complete_delivery_artifacts(root, subtitles="Training montage begins now")
            (root / "subtitle_audio_alignment_report.json").write_text(
                json.dumps({
                    "artifact_role": "subtitle_audio_alignment_report",
                    "ok": False,
                    "items": [{
                        "type": "subtitle",
                        "text": "Training montage begins now",
                        "corresponds_to_audible_audio": False,
                    }],
                }),
                encoding="utf-8",
            )

            result = evaluate_complete_video_delivery(root, probe=self._probe_with_audio_video())

        self.assertFalse(result["pass"])
        rules = {item["rule"] for item in result["blocking"]}
        self.assertIn("subtitle_audio_alignment_failed", rules)
        self.assertIn("unlabeled_editorial_subtitles", rules)

    def test_scripted_gate_requires_source_speech_evidence_when_story_requires_visible_speaker(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_complete_delivery_artifacts(root)
            (root / "story_contract.json").write_text(
                json.dumps({
                    "artifact_role": "story_contract",
                    "required_story_beats": [
                        {"beat_id": "source_speech_instruction", "description": "Preserve visible speaker speech"},
                    ],
                }),
                encoding="utf-8",
            )
            (root / "story_to_material_map.json").write_text(
                json.dumps({
                    "artifact_role": "story_to_material_map",
                    "items": [{
                        "beat_id": "source_speech_instruction",
                        "evidence_type": "source_speech",
                        "selected_source_files": ["director.mp4"],
                    }],
                }),
                encoding="utf-8",
            )

            result = evaluate_complete_video_delivery(root, probe=self._probe_with_audio_video())

        self.assertFalse(result["pass"])
        rules = {item["rule"] for item in result["blocking"]}
        self.assertIn("missing_source_speech_preservation_evidence", rules)

    def test_scripted_gate_does_not_treat_zhang_as_chinese_language_signal(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_complete_delivery_artifacts(root, subtitles="Zhang opens the session.")
            script = {
                "artifact_role": "script",
                "language": "en",
                "segments": [{"segment": "opening", "text": "Zhang opens the session."}],
            }
            (root / "script.json").write_text(json.dumps(script), encoding="utf-8")
            (root / "narration_manifest.json").write_text(
                json.dumps({
                    "artifact_role": "narration_manifest",
                    "segments": [{"text": "Zhang opens the session.", "audio_ref": "narration.wav"}],
                }),
                encoding="utf-8",
            )
            (root / "subtitle_audio_alignment_report.json").write_text(
                json.dumps({
                    "artifact_role": "subtitle_audio_alignment_report",
                    "ok": True,
                    "items": [{
                        "type": "voxcpm_transcript",
                        "text": "Zhang opens the session.",
                        "corresponds_to_audible_audio": True,
                    }],
                }),
                encoding="utf-8",
            )

            result = evaluate_complete_video_delivery(root, probe=self._probe_with_audio_video())

        self.assertTrue(result["pass"], result)
        rules = {item["rule"] for item in result["blocking"]}
        self.assertNotIn("corrupt_script_text", rules)
        self.assertNotIn("corrupt_narration_manifest", rules)
        self.assertNotIn("corrupt_subtitle_alignment", rules)

    def test_scripted_gate_does_not_require_source_speech_for_director_approved_visual_montage(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_complete_delivery_artifacts(root)
            (root / "story_contract.json").write_text(
                json.dumps({
                    "artifact_role": "story_contract",
                    "required_story_beats": [
                        {"beat_id": "opening_montage", "description": "Director-approved opening montage, no interview audio required"},
                    ],
                }),
                encoding="utf-8",
            )
            (root / "story_to_material_map.json").write_text(
                json.dumps({
                    "artifact_role": "story_to_material_map",
                    "items": [{
                        "beat_id": "opening_montage",
                        "evidence_type": "visual_match",
                        "needs_human_confirmation": False,
                    }],
                }),
                encoding="utf-8",
            )

            result = evaluate_complete_video_delivery(root, probe=self._probe_with_audio_video())

        rules = {item["rule"] for item in result["blocking"]}
        self.assertNotIn("missing_source_speech_preservation_evidence", rules)

    def test_scripted_gate_blocks_preserved_source_speech_that_is_not_mixed(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_complete_delivery_artifacts(root)
            (root / "story_contract.json").write_text(
                json.dumps({
                    "artifact_role": "story_contract",
                    "required_story_beats": [
                        {"beat_id": "source_speech_instruction", "description": "Preserve visible speaker speech"},
                    ],
                }),
                encoding="utf-8",
            )
            (root / "story_to_material_map.json").write_text(
                json.dumps({
                    "artifact_role": "story_to_material_map",
                    "items": [{"beat_id": "source_speech_instruction", "evidence_type": "source_speech"}],
                }),
                encoding="utf-8",
            )
            (root / "source_speech_preservation_report.json").write_text(
                json.dumps({
                    "artifact_role": "source_speech_preservation_report",
                    "status": "preserved",
                    "preserved_audio": "source_speech.wav",
                }),
                encoding="utf-8",
            )

            result = evaluate_complete_video_delivery(root, probe=self._probe_with_audio_video())

        self.assertFalse(result["pass"])
        rules = {item["rule"] for item in result["blocking"]}
        self.assertIn("source_speech_not_mixed", rules)

    def test_scripted_gate_surfaces_human_review_required_for_agent_inferred_story_map(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_complete_delivery_artifacts(root)
            (root / "story_contract.json").write_text(
                json.dumps({
                    "artifact_role": "story_contract",
                    "required_story_beats": [
                        {"beat_id": "establish_gathering"},
                        {"beat_id": "training_process_detail"},
                    ],
                }),
                encoding="utf-8",
            )
            (root / "story_to_material_map.json").write_text(
                json.dumps({
                    "artifact_role": "story_to_material_map",
                    "items": [
                        {"beat_id": "establish_gathering", "evidence_type": "visual_match", "needs_human_confirmation": True},
                        {"beat_id": "training_process_detail", "evidence_type": "agent_inferred", "needs_human_confirmation": True},
                    ],
                }),
                encoding="utf-8",
            )
            (root / "story_to_final_alignment_report.json").write_text(
                json.dumps({"artifact_role": "story_to_final_alignment_report", "ok": True}),
                encoding="utf-8",
            )

            result = evaluate_complete_video_delivery(root, probe=self._probe_with_audio_video())

        self.assertTrue(result["pass"], result)
        visible_rules = {
            item["rule"]
            for item in [*result.get("warnings", []), *result.get("limitations", [])]
        }
        self.assertIn("story_human_review_required", visible_rules)

    def test_scripted_gate_clears_human_review_warning_after_human_approval(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_complete_delivery_artifacts(root)
            (root / "story_contract.json").write_text(
                json.dumps({
                    "artifact_role": "story_contract",
                    "required_story_beats": [
                        {"beat_id": "establish_gathering"},
                        {"beat_id": "training_process_detail"},
                    ],
                }),
                encoding="utf-8",
            )
            (root / "story_to_material_map.json").write_text(
                json.dumps({
                    "artifact_role": "story_to_material_map",
                    "items": [
                        {"beat_id": "establish_gathering", "evidence_type": "visual_match", "needs_human_confirmation": True},
                        {"beat_id": "training_process_detail", "evidence_type": "agent_inferred", "needs_human_confirmation": True},
                    ],
                }),
                encoding="utf-8",
            )
            (root / "story_to_final_alignment_report.json").write_text(
                json.dumps({"artifact_role": "story_to_final_alignment_report", "ok": True}),
                encoding="utf-8",
            )
            (root / "story_human_review_decision.json").write_text(
                json.dumps({
                    "artifact_role": "story_human_review_decision",
                    "version": 1,
                    "decision": "approved",
                    "reviewer": "human",
                    "approved_beat_ids": ["establish_gathering", "training_process_detail"],
                }),
                encoding="utf-8",
            )

            result = evaluate_complete_video_delivery(root, probe=self._probe_with_audio_video())

        self.assertTrue(result["pass"], result)
        visible_rules = {
            item["rule"]
            for item in [*result.get("warnings", []), *result.get("limitations", [])]
        }
        self.assertNotIn("story_human_review_required", visible_rules)

    def test_scripted_gate_agent_review_does_not_clear_human_review_warning(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_complete_delivery_artifacts(root)
            (root / "story_contract.json").write_text(
                json.dumps({"artifact_role": "story_contract", "required_story_beats": [{"beat_id": "establish_gathering"}]}),
                encoding="utf-8",
            )
            (root / "story_to_material_map.json").write_text(
                json.dumps({
                    "artifact_role": "story_to_material_map",
                    "items": [{"beat_id": "establish_gathering", "evidence_type": "agent_inferred", "needs_human_confirmation": True}],
                }),
                encoding="utf-8",
            )
            (root / "story_human_review_decision.json").write_text(
                json.dumps({
                    "artifact_role": "story_human_review_decision",
                    "decision": "approved",
                    "reviewer": "agent",
                    "approved_beat_ids": ["establish_gathering"],
                }),
                encoding="utf-8",
            )

            result = evaluate_complete_video_delivery(root, probe=self._probe_with_audio_video())

        self.assertTrue(result["pass"], result)
        visible_rules = {
            item["rule"]
            for item in [*result.get("warnings", []), *result.get("limitations", [])]
        }
        self.assertIn("story_human_review_required", visible_rules)

    def test_scripted_gate_revision_requested_blocks_completion(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_complete_delivery_artifacts(root)
            (root / "story_contract.json").write_text(
                json.dumps({"artifact_role": "story_contract", "required_story_beats": [{"beat_id": "establish_gathering"}]}),
                encoding="utf-8",
            )
            (root / "story_to_material_map.json").write_text(
                json.dumps({
                    "artifact_role": "story_to_material_map",
                    "items": [{"beat_id": "establish_gathering", "evidence_type": "agent_inferred", "needs_human_confirmation": True}],
                }),
                encoding="utf-8",
            )
            (root / "story_human_review_decision.json").write_text(
                json.dumps({
                    "artifact_role": "story_human_review_decision",
                    "decision": "revision_requested",
                    "reviewer_type": "human",
                    "revision_notes": ["Use the director explanation clip instead."],
                }),
                encoding="utf-8",
            )

            result = evaluate_complete_video_delivery(root, probe=self._probe_with_audio_video())

        self.assertFalse(result["pass"])
        rules = {item["rule"] for item in result["blocking"]}
        self.assertIn("story_human_review_revision_requested", rules)
        self.assertEqual(result["next_action"], "revise_story_material_mapping")

    def test_scripted_gate_rejected_human_review_blocks_completion(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_complete_delivery_artifacts(root)
            (root / "story_contract.json").write_text(
                json.dumps({"artifact_role": "story_contract", "required_story_beats": [{"beat_id": "establish_gathering"}]}),
                encoding="utf-8",
            )
            (root / "story_to_material_map.json").write_text(
                json.dumps({
                    "artifact_role": "story_to_material_map",
                    "items": [{"beat_id": "establish_gathering", "evidence_type": "agent_inferred", "needs_human_confirmation": True}],
                }),
                encoding="utf-8",
            )
            (root / "story_human_review_decision.json").write_text(
                json.dumps({
                    "artifact_role": "story_human_review_decision",
                    "decision": "rejected",
                    "reviewer": "human",
                    "rejected_beat_ids": ["establish_gathering"],
                }),
                encoding="utf-8",
            )

            result = evaluate_complete_video_delivery(root, probe=self._probe_with_audio_video())

        self.assertFalse(result["pass"])
        rules = {item["rule"] for item in result["blocking"]}
        self.assertIn("story_human_review_rejected", rules)
        self.assertEqual(result["next_action"], "repair_rejected_story_material_mapping")

    def test_scripted_gate_blocks_when_required_story_beats_are_uncovered(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_complete_delivery_artifacts(root)
            (root / "story_contract.json").write_text(
                json.dumps({
                    "artifact_role": "story_contract",
                    "required_story_beats": [
                        {"beat_id": "establish_gathering"},
                        {"beat_id": "source_speech_instruction"},
                    ],
                }),
                encoding="utf-8",
            )
            (root / "story_to_material_map.json").write_text(
                json.dumps({
                    "artifact_role": "story_to_material_map",
                    "items": [
                        {"beat_id": "establish_gathering", "evidence_type": "agent_inferred", "needs_human_confirmation": True},
                    ],
                }),
                encoding="utf-8",
            )

            result = evaluate_complete_video_delivery(root, probe=self._probe_with_audio_video())

        self.assertFalse(result["pass"])
        rules = {item["rule"] for item in result["blocking"]}
        self.assertIn("story_required_beats_uncovered", rules)

    def test_complete_video_gate_blocks_vocal_music_conflict_when_requested(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_complete_delivery_artifacts(root)
            requirements = json.loads((root / "delivery_requirements.json").read_text(encoding="utf-8"))
            requirements["requires_soundtrack_probe"] = True
            requirements["requires_vocal_conflict_check"] = True
            (root / "delivery_requirements.json").write_text(json.dumps(requirements), encoding="utf-8")
            (root / "soundtrack_probe_report.json").write_text(
                json.dumps({
                    "artifact_role": "soundtrack_probe_report",
                    "version": 1,
                    "pass": True,
                    "audio_file": "music.wav",
                    "duration_sec": 60.0,
                    "features": {
                        "mean_dbfs": -18.0,
                        "peak_dbfs": -2.0,
                        "vocal_analysis": {
                            "has_vocals": True,
                            "method": "faster_whisper",
                            "vocal_density": "high",
                            "vocal_ratio": 0.58,
                        },
                    },
                    "sections": [{"start_sec": 0.0, "end_sec": 60.0, "role": "full_track"}],
                    "editing_fit": {"speech_underlay": "low", "montage": "medium"},
                    "section_fit": [{"video_section": "speech_underlay", "fit": "low"}],
                }),
                encoding="utf-8",
            )

            result = evaluate_complete_video_delivery(root, probe=self._probe_with_audio_video())

        self.assertFalse(result["pass"])
        rules = {item["rule"] for item in result["blocking"]}
        self.assertIn("vocal_music_conflicts_with_voiceover", rules)

    def test_complete_video_gate_blocks_empty_soundtrack_probe(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_complete_delivery_artifacts(root)
            requirements = json.loads((root / "delivery_requirements.json").read_text(encoding="utf-8"))
            requirements["requires_soundtrack_probe"] = True
            (root / "delivery_requirements.json").write_text(json.dumps(requirements), encoding="utf-8")
            (root / "soundtrack_probe_report.json").write_text(
                json.dumps({
                    "artifact_role": "soundtrack_probe_report",
                    "version": 1,
                    "pass": True,
                    "audio_file": "music.wav",
                    "duration_sec": 60.0,
                    "features": {},
                    "sections": [],
                    "editing_fit": {},
                }),
                encoding="utf-8",
            )

            result = evaluate_complete_video_delivery(root, probe=self._probe_with_audio_video())

        self.assertFalse(result["pass"])
        rules = {item["rule"] for item in result["blocking"]}
        self.assertIn("soundtrack_probe_has_no_sections", rules)
        self.assertIn("soundtrack_probe_has_no_editing_fit", rules)

    def test_complete_video_gate_blocks_soundtrack_probe_without_section_fit(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_complete_delivery_artifacts(root)
            requirements = json.loads((root / "delivery_requirements.json").read_text(encoding="utf-8"))
            requirements["requires_soundtrack_probe"] = True
            (root / "delivery_requirements.json").write_text(json.dumps(requirements), encoding="utf-8")
            (root / "soundtrack_probe_report.json").write_text(
                json.dumps({
                    "artifact_role": "soundtrack_probe_report",
                    "version": 1,
                    "pass": True,
                    "audio_file": "music.wav",
                    "duration_sec": 60.0,
                    "features": {"mean_dbfs": -18.0, "peak_dbfs": -2.0},
                    "sections": [{"start_sec": 0.0, "end_sec": 60.0, "role": "full_track"}],
                    "editing_fit": {"montage": "medium"},
                    "section_fit": [],
                }),
                encoding="utf-8",
            )

            result = evaluate_complete_video_delivery(root, probe=self._probe_with_audio_video())

        self.assertFalse(result["pass"])
        rules = {item["rule"] for item in result["blocking"]}
        self.assertIn("soundtrack_probe_has_no_section_fit", rules)

    def test_complete_video_gate_blocks_visual_audit_evidence_without_samples(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_complete_delivery_artifacts(root)
            (root / "effect_intent_plan.json").write_text(
                """{
  "artifact_role": "effect_intent_plan",
  "version": 1,
  "effects": [{"effect_id": "e1", "type": "lower_third", "render_required": true}]
}""",
                encoding="utf-8",
            )
            (root / "keyframe_grid.jpg").write_bytes(b"fake grid bytes")
            (root / "visual_audit.json").write_text(
                """{
  "artifact_role": "visual_audit",
  "version": 1,
  "pass": true,
  "grid": "keyframe_grid.jpg",
  "samples": []
}""",
                encoding="utf-8",
            )
            (root / "effect_render_verification.json").write_text(
                """{
  "artifact_role": "effect_render_verification",
  "version": 1,
  "pass": true,
  "visual_audit_ref": "visual_audit.json",
  "keyframe_grid_ref": "keyframe_grid.jpg",
  "verified_effects": [
    {
      "effect_id": "e1",
      "kind": "lower_third",
      "rendered": true
    }
  ]
}""",
                encoding="utf-8",
            )

            result = evaluate_complete_video_delivery(root, probe=self._probe_with_audio_video())

        self.assertFalse(result["pass"])
        rules = {item["rule"] for item in result["blocking"]}
        self.assertIn("rendered_effect_has_no_evidence_refs", rules)

    def test_complete_video_run_folder_validation_promotes_warnings_to_errors(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rel in (
                "video_intent.json",
                "run_layout.json",
                "project_material_map.json",
                "reviewed_project_material_map.json",
                "material_delta.json",
                "segment_contract.json",
                "timeline.json",
                "timeline_build.json",
                "workbench_handoff.json",
                "workbench_review_report.json",
                "artifact_manifest.json",
                "verify_result.json",
                "HONEST_REVIEW.md",
                "agent_interaction_log.md",
            ):
                (root / rel).write_text("{}", encoding="utf-8")
            (root / "final.mp4").write_bytes(b"not a real video")

            result = validate_run_folder(root, complete_video=True)

        self.assertFalse(result["ok"])
        self.assertTrue(any("complete video warning promoted to error" in err for err in result["errors"]))
        self.assertEqual(result["warnings"], [])

    def _probe_with_audio_video(self):
        return {
            "ok": True,
            "streams": [
                {"codec_type": "video", "duration": "10.0"},
                {"codec_type": "audio", "duration": "10.0"},
            ],
            "format": {"duration": "10.0"},
        }

    def _write_video_only_delivery_waiver(
        self,
        root,
        *,
        reviewer="operator",
        reason="handoff picture only",
        at="2026-07-05T00:00:00+08:00",
        waives=None,
        limitations=None,
    ):
        if waives is None:
            waives = ["audio", "music", "subtitle", "narration", "soundtrack_license"]
        if limitations is None:
            limitations = ["Video-only handoff; no deliverable soundtrack, narration, or subtitles."]
        (root / "video_only_delivery_waiver.json").write_text(
            json.dumps({
                "artifact_role": "video_only_delivery_waiver",
                "version": 1,
                "scope": "video_only_delivery",
                "reviewer": reviewer,
                "reason": reason,
                "at": at,
                "waives": waives,
                "limitations": limitations,
            }),
            encoding="utf-8",
        )

    def _write_voxcpm_evidence(self, root):
        (root / "voxcpm_runtime_check.json").write_text(
            """{
  "artifact_role": "voxcpm_runtime_check",
  "version": 1,
  "ok_to_execute": true,
  "voxcpm_repo": "reference repo/VoxCPM-main"
}""",
            encoding="utf-8",
        )
        (root / "voiceover_provider_plan.json").write_text(
            """{
  "artifact_role": "voiceover_provider_plan",
  "version": 1,
  "requested_provider": "voxcpm",
  "selected_provider": "voxcpm",
  "provider_available": true,
  "fallback_allowed": false,
  "fallback_used": false
}""",
            encoding="utf-8",
        )

    def _write_valid_music_evidence(self, root):
        (root / "music_manifest.json").write_text(
            """{
  "artifact_role": "music_manifest",
  "version": 1,
  "source_type": "licensed_library",
  "license_note": "test fixture licensed-library metadata",
  "tracks": [{"id": "m1", "source_type": "licensed_library", "source_ref": "licensed_music.wav", "license_note": "test fixture licensed-library metadata"}],
  "cues": [{"track_id": "m1", "start_sec": 0.0, "end_sec": 10.0}]
}""",
            encoding="utf-8",
        )
        (root / "soundtrack_probe_report.json").write_text(
            """{
  "artifact_role": "soundtrack_probe_report",
  "version": 1,
  "pass": true,
  "audio_file": "licensed_music.wav",
  "duration_sec": 10.0,
  "features": {"mean_dbfs": -18.0, "peak_dbfs": -3.0},
  "sections": [{"start_sec": 0.0, "end_sec": 10.0, "role": "full_track"}],
  "editing_fit": {"montage": "medium"},
  "section_fit": [{"video_section": "all", "fit": "medium"}]
}""",
            encoding="utf-8",
        )

    def _write_silent_wav(self, path):
        with wave.open(str(path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(16000)
            wav.writeframes(b"\x00\x00" * 16000)
