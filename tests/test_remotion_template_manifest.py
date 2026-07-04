import json
import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path

import video_tools


class RemotionTemplateManifestTest(unittest.TestCase):
    def _reference_review_fixture(self) -> Path:
        return (
            Path(__file__).resolve().parent
            / "fixtures"
            / "remotion"
            / "effect_reference_review_67"
            / "20260624-strong-montage"
            / "effect_reference_strong_montage_review.json"
        )

    def test_manifest_covers_training_recap_dictionary_templates_with_support_status(self):
        from video_pipeline_core.effect_template_dictionary import load_effect_template_dictionary
        from video_pipeline_core.remotion_template_manifest import build_remotion_template_manifest

        dictionary = load_effect_template_dictionary()
        manifest = build_remotion_template_manifest(dictionary)

        template_ids = {t["template_id"] for t in dictionary["templates"]}
        manifest_ids = {t["template_id"] for t in manifest["templates"]}

        self.assertEqual(manifest["artifact_role"], "remotion_effect_capability_manifest")
        self.assertEqual(manifest["version"], 1)
        self.assertEqual(manifest_ids, template_ids)
        self.assertTrue(all(t["concrete_worker_support"] for t in manifest["templates"]))
        self.assertTrue(all(t["status"] == "verified" for t in manifest["templates"]))
        opening = next(t for t in manifest["templates"] if t["template_id"] == "training_opening_title")
        self.assertEqual(opening["component_family"], "title_reveal")
        self.assertIn("training_opening_title", manifest["template_ids"])

    def test_manifest_records_reference_review_and_verify_evidence(self):
        from video_pipeline_core.remotion_template_manifest import write_remotion_template_manifest

        review_path = self._reference_review_fixture()
        self.assertTrue(review_path.is_file())

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "remotion_effect_capability_manifest.json"
            manifest = write_remotion_template_manifest(out, reference_review_path=review_path)
            saved = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(saved, manifest)
        self.assertEqual(
            manifest["reference_reviews"][0]["artifact"],
            str(review_path),
        )
        self.assertEqual(manifest["verify_evidence"]["visual_audit"]["pass"], True)
        self.assertEqual(manifest["verify_evidence"]["black_frame_audit"]["pass"], False)
        self.assertEqual(
            manifest["verify_evidence"]["black_frame_audit"]["next_action"],
            "formalize_or_fix_black_transition_plates",
        )

    def test_video_tools_command_writes_manifest(self):
        review_path = self._reference_review_fixture()
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "remotion_effect_capability_manifest.json"
            video_tools.cmd_remotion_template_manifest(SimpleNamespace(
                out=str(out),
                dictionary=None,
                reference_review=str(review_path),
            ))
            manifest = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(manifest["artifact_role"], "remotion_effect_capability_manifest")
        self.assertEqual(manifest["summary"]["template_count"], 10)
        self.assertEqual(manifest["summary"]["verified_count"], 10)


if __name__ == "__main__":
    unittest.main()
