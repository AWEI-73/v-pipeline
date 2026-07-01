import json
import tempfile
import unittest
from pathlib import Path


class RunArtifactIndexTest(unittest.TestCase):
    def test_classifies_run_artifacts_by_review_value(self):
        from video_pipeline_core.run_artifact_index import build_run_artifact_index

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "video_intent.json").write_text("{}", encoding="utf-8")
            (root / "effect_factory_route_acceptance_report.json").write_text("{}", encoding="utf-8")
            (root / "segment_contract.json").write_text("{}", encoding="utf-8")
            (root / "effect_contract.json").write_text("{}", encoding="utf-8")
            (root / "effect_handoff.json").write_text("{}", encoding="utf-8")
            (root / "remotion_effect_review.json").write_text("{}", encoding="utf-8")
            (root / "remotion_contact_sheet.jpg").write_bytes(b"jpg")
            (root / "preview.mp4").write_bytes(b"video")
            (root / ".tmp").mkdir()
            (root / ".tmp" / "frame_0001.png").write_bytes(b"png")

            index = build_run_artifact_index(root)

        by_class = {
            artifact_class: {item["path"] for item in items}
            for artifact_class, items in index["classes"].items()
        }
        self.assertIn("video_intent.json", by_class["decision"])
        self.assertIn("effect_factory_route_acceptance_report.json", by_class["decision"])
        self.assertIn("segment_contract.json", by_class["contract"])
        self.assertIn("effect_contract.json", by_class["contract"])
        self.assertIn("effect_handoff.json", by_class["handoff"])
        self.assertIn("remotion_effect_review.json", by_class["evidence"])
        self.assertIn("remotion_contact_sheet.jpg", by_class["evidence"])
        self.assertIn("preview.mp4", by_class["asset"])
        self.assertIn(".tmp/frame_0001.png", by_class["debug"])
        self.assertEqual(index["review_priority"], ["decision", "contract", "handoff", "evidence"])

    def test_cli_writes_index_json(self):
        import subprocess

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "delivery_gate.json").write_text("{}", encoding="utf-8")
            proc = subprocess.run(
                [
                    "python",
                    "tools/run_artifact_index.py",
                    "--run",
                    str(root),
                    "--json",
                ],
                cwd=Path(__file__).resolve().parents[1],
                capture_output=True,
                text=True,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["artifact_role"], "run_artifact_index")
            self.assertTrue((root / "run_artifact_index.json").exists())

    def test_classifies_material_and_audio_route_artifacts(self):
        from video_pipeline_core.run_artifact_index import build_run_artifact_index

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in [
                "project_material_map.json",
                "reviewed_project_material_map.json",
                "materials_db.json",
                "soundtrack_plan.json",
                "sound_license_manifest.json",
                "music_manifest.json",
                "audio_mix_plan.json",
                "narration_manifest.json",
            ]:
                (root / name).write_text("{}", encoding="utf-8")
            for name in [
                "material_delta.json",
                "material_first_boundary_acceptance_report.json",
                "supply_review.json",
                "soundtrack_flow_acceptance_report.json",
                "audio_handoff_acceptance.json",
                "subtitle_voiceover_handoff_acceptance.json",
            ]:
                (root / name).write_text("{}", encoding="utf-8")
            for name in [
                "audio_director_handoff.json",
                "subtitle_voiceover_build_handoff.json",
            ]:
                (root / name).write_text("{}", encoding="utf-8")
            for name in [
                "material_matrix_review.md",
                "source_transcript.json",
                "soundtrack_probe_report.json",
            ]:
                (root / name).write_text("{}", encoding="utf-8")

            index = build_run_artifact_index(root)

        by_class = {
            artifact_class: {item["path"] for item in items}
            for artifact_class, items in index["classes"].items()
        }
        self.assertIn("project_material_map.json", by_class["contract"])
        self.assertIn("sound_license_manifest.json", by_class["contract"])
        self.assertIn("material_delta.json", by_class["decision"])
        self.assertIn("soundtrack_flow_acceptance_report.json", by_class["decision"])
        self.assertIn("audio_director_handoff.json", by_class["handoff"])
        self.assertIn("subtitle_voiceover_build_handoff.json", by_class["handoff"])
        self.assertIn("material_matrix_review.md", by_class["evidence"])
        self.assertIn("source_transcript.json", by_class["evidence"])
        self.assertIn("soundtrack_probe_report.json", by_class["evidence"])

    def test_classifies_single_source_highlight_artifacts_without_frame_noise(self):
        from video_pipeline_core.run_artifact_index import build_run_artifact_index

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in [
                "highlight_selection_plan.json",
                "highlight_cut_report.json",
                "delivery_gate.json",
                "verified_preview_package.json",
                "final_product_verify_bundle.json",
            ]:
                (root / name).write_text("{}", encoding="utf-8")
            for name in [
                "rough_cut_plan.json",
                "source_timeline_map.json",
            ]:
                (root / name).write_text("{}", encoding="utf-8")
            (root / "source_section_map.json").write_text("{}", encoding="utf-8")
            motion = root / "source_motion_profile"
            motion.mkdir()
            (motion / "source_motion_profile.json").write_text("{}", encoding="utf-8")
            frames = motion / "motion_frames"
            frames.mkdir()
            (frames / "motion_0001.jpg").write_bytes(b"jpg")
            matrix = root / "source_matrix"
            matrix.mkdir()
            (matrix / "source_material_matrix.json").write_text("{}", encoding="utf-8")
            (matrix / "source_material_matrix_contact_sheet.jpg").write_bytes(b"jpg")
            matrix_frames = matrix / "source_matrix_frames"
            matrix_frames.mkdir()
            (matrix_frames / "win_000.jpg").write_bytes(b"jpg")
            (root / "single_source_highlight_preview.mp4").write_bytes(b"mp4")
            (root / "delivery_candidate.mp4").write_bytes(b"mp4")

            index = build_run_artifact_index(root)

        by_class = {
            artifact_class: {item["path"] for item in items}
            for artifact_class, items in index["classes"].items()
        }
        self.assertIn("highlight_selection_plan.json", by_class["decision"])
        self.assertIn("highlight_cut_report.json", by_class["decision"])
        self.assertIn("delivery_gate.json", by_class["decision"])
        self.assertIn("verified_preview_package.json", by_class["decision"])
        self.assertIn("final_product_verify_bundle.json", by_class["decision"])
        self.assertIn("rough_cut_plan.json", by_class["contract"])
        self.assertIn("source_timeline_map.json", by_class["contract"])
        self.assertIn("source_section_map.json", by_class["evidence"])
        self.assertIn("source_motion_profile/source_motion_profile.json", by_class["evidence"])
        self.assertIn("source_matrix/source_material_matrix.json", by_class["evidence"])
        self.assertIn("source_matrix/source_material_matrix_contact_sheet.jpg", by_class["evidence"])
        self.assertIn("single_source_highlight_preview.mp4", by_class["asset"])
        self.assertIn("delivery_candidate.mp4", by_class["asset"])
        self.assertIn("source_motion_profile/motion_frames/motion_0001.jpg", by_class["debug"])
        self.assertIn("source_matrix/source_matrix_frames/win_000.jpg", by_class["debug"])

    def test_classifies_story_first_provider_handoff_artifacts(self):
        from video_pipeline_core.run_artifact_index import build_run_artifact_index

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "video_intent.json").write_text("{}", encoding="utf-8")
            (root / "project_brief.json").write_text("{}", encoding="utf-8")
            (root / "material_generation_fallback.json").write_text("{}", encoding="utf-8")
            (root / "story_first_provider_happy_path_report.json").write_text("{}", encoding="utf-8")
            story = root / "story_blueprint"
            story.mkdir()
            for name in [
                "creative_concept.json",
                "director_shot_plan.json",
                "generation_manifest.json",
                "material_needs.json",
                "screenplay_beats.json",
                "story_world.json",
            ]:
                (story / name).write_text("{}", encoding="utf-8")
            (story / "review_checklist.md").write_text("review", encoding="utf-8")
            packet = root / "provider_packet"
            packet.mkdir()
            (packet / "generated_provider_packet.json").write_text("{}", encoding="utf-8")
            (packet / "generated_provider_outputs.template.json").write_text("{}", encoding="utf-8")
            (packet / "generated_provider_prompts.md").write_text("prompts", encoding="utf-8")
            handoff = packet / "image_agent_handoff"
            handoff.mkdir()
            (handoff / "image_agent_prompt_handoff.json").write_text("{}", encoding="utf-8")
            (handoff / "image_agent_prompt.md").write_text("prompt", encoding="utf-8")

            index = build_run_artifact_index(root)

        by_class = {
            artifact_class: {item["path"] for item in items}
            for artifact_class, items in index["classes"].items()
        }
        self.assertIn("material_generation_fallback.json", by_class["decision"])
        self.assertIn("story_first_provider_happy_path_report.json", by_class["decision"])
        self.assertIn("story_blueprint/director_shot_plan.json", by_class["contract"])
        self.assertIn("provider_packet/generated_provider_outputs.template.json", by_class["contract"])
        self.assertIn("provider_packet/generated_provider_packet.json", by_class["handoff"])
        self.assertIn("provider_packet/image_agent_handoff/image_agent_prompt_handoff.json", by_class["handoff"])
        self.assertIn("story_blueprint/review_checklist.md", by_class["evidence"])
        self.assertIn("provider_packet/generated_provider_prompts.md", by_class["evidence"])
        self.assertIn("provider_packet/image_agent_handoff/image_agent_prompt.md", by_class["evidence"])


if __name__ == "__main__":
    unittest.main()
