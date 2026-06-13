import json
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core import capability_manifest


class CapabilityManifestTest(unittest.TestCase):
    def test_manifest_is_generated_from_runtime_capabilities(self):
        manifest = capability_manifest.build_capability_manifest()

        self.assertEqual(manifest["artifact_role"], "capability_manifest")
        self.assertIn("fade", manifest["capabilities"]["transitions"])
        self.assertIn("slow_push", manifest["capabilities"]["still_treatments"])
        self.assertIn("whoosh", manifest["capabilities"]["sfx_cues"])
        self.assertIn("window", manifest["capabilities"]["patch_types"])
        self.assertIn("duck", manifest["capabilities"]["audio_policies"])
        self.assertIn("agent", manifest["capabilities"]["judge_modes"])
        self.assertIn("arbitrary_effects", manifest["unsupported"])

    def test_writer_emits_traceable_json_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "capability_manifest.json"
            result = capability_manifest.write_capability_manifest(out)
            saved = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(result, str(out))
        self.assertEqual(saved["capability_manifest_version"], 1)

