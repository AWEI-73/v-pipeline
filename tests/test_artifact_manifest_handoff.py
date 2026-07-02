import json
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core.artifact_manifest import (
    handoff_manifest_key,
    register_handoff,
)
from tools.pipeline_interface_audit import audit_dictionary


class TestArtifactManifestHandoff(unittest.TestCase):
    def setUp(self):
        self.project_root = Path(__file__).resolve().parent.parent
        self.dict_path = self.project_root / "docs" / "interface-contracts" / "pipeline-api-dictionary.json"
        self.registry_path = self.project_root / "docs" / "branch-contract-registry.json"

    def test_register_handoff_records_flat_artifacts_and_handoffs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            handoff_path = root / "audio_director_handoff.json"
            handoff_path.write_text("{}", encoding="utf-8")

            manifest = register_handoff(
                root,
                artifact_path=handoff_path,
                owner_branch="soundtrack-arranger",
                status="accepted",
                updated_by="tools/soundtrack_flow_acceptance.py",
                interface_id="soundtrack_arranger.to.audio_director.handoff",
                next_action="audio_director_mix_or_build",
            )

            self.assertEqual(manifest["audio_director_handoff"], "audio_director_handoff.json")
            self.assertEqual(
                manifest["artifacts"]["audio_director_handoff"]["owner_branch"],
                "soundtrack-arranger",
            )
            self.assertEqual(
                manifest["handoffs"]["audio_director_handoff"]["interface_id"],
                "soundtrack_arranger.to.audio_director.handoff",
            )
            self.assertEqual(
                manifest["handoffs"]["audio_director_handoff"]["next_action"],
                "audio_director_mix_or_build",
            )

    def test_register_handoff_preserves_existing_manifest_entries(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "artifact_manifest.json").write_text(
                json.dumps({
                    "artifact_role": "artifact_manifest",
                    "artifact_manifest_version": 1,
                    "video_intent": "video_intent.json",
                    "artifacts": {
                        "video_intent": {
                            "path": "video_intent.json",
                            "status": "present",
                        }
                    },
                }),
                encoding="utf-8",
            )
            handoff_path = root / "effect_handoff.json"
            handoff_path.write_text("{}", encoding="utf-8")

            manifest = register_handoff(
                root,
                artifact_path=handoff_path,
                owner_branch="effect-factory",
                status="accepted",
                updated_by="tools/effect_factory_route_acceptance.py",
            )

            self.assertEqual(manifest["video_intent"], "video_intent.json")
            self.assertIn("video_intent", manifest["artifacts"])
            self.assertIn("effect_handoff", manifest["handoffs"])

    def test_handoff_manifest_key_rejects_non_json(self):
        with self.assertRaises(ValueError):
            handoff_manifest_key("final.mp4")

    def test_audit_rejects_branch_handoff_without_manifest_registrable_output(self):
        with tempfile.TemporaryDirectory() as temp:
            temp_dict = Path(temp) / "bad_dict.json"
            data = json.loads(self.dict_path.read_text(encoding="utf-8-sig"))
            for face in data["interfaces"]:
                if face["api_id"] == "soundtrack_arranger.to.audio_director.handoff":
                    face["response"]["outputs"] = ["debug_report.json"]
                    break
            temp_dict.write_text(json.dumps(data, indent=2), encoding="utf-8")

            errors, _, _ = audit_dictionary(temp_dict, self.registry_path, self.project_root)
            self.assertTrue(any("branch_handoff response.outputs must include" in err for err in errors))


if __name__ == "__main__":
    unittest.main()
