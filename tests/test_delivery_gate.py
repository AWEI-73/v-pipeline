import unittest
import wave
from pathlib import Path
from tempfile import TemporaryDirectory

from video_pipeline_core.delivery_gate import evaluate_complete_video_delivery, evaluate_delivery_gate
from tools.validate_pipeline_run_folder import validate_run_folder


class DeliveryGateTest(unittest.TestCase):
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
        self.assertEqual(result["next_action"], "revise_material_selection_or_review")

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
  "requires_subtitles": true
}""",
                encoding="utf-8",
            )
            (root / "narration_manifest.json").write_text(
                """{
  "artifact_role": "narration_manifest",
  "version": 1,
  "segments": [{"id": "n1", "text": "第一幕開始", "audio_ref": "narration.wav"}]
}""",
                encoding="utf-8",
            )
            self._write_silent_wav(root / "narration.wav")
            (root / "music_manifest.json").write_text(
                """{
  "artifact_role": "music_manifest",
  "version": 1,
  "tracks": [{"id": "m1", "source": "generated_bgm.wav"}]
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
                "1\n00:00:00,000 --> 00:00:03,000\n第一幕開始\n",
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
            '  "requires_subtitles": true\n'
            "}",
            encoding="utf-8",
        )
        (root / "narration_manifest.json").write_text(
            """{
  "artifact_role": "narration_manifest",
  "version": 1,
  "segments": [{"id": "n1", "text": "第一幕開始", "audio_ref": "narration.wav"}]
}""",
            encoding="utf-8",
        )
        self._write_silent_wav(root / "narration.wav")
        (root / "music_manifest.json").write_text(
            """{
  "artifact_role": "music_manifest",
  "version": 1,
  "tracks": [{"id": "m1", "source": "generated_bgm.wav"}]
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

    def _write_silent_wav(self, path):
        with wave.open(str(path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(16000)
            wav.writeframes(b"\x00\x00" * 16000)
