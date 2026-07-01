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


if __name__ == "__main__":
    unittest.main()
