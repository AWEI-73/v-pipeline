import json
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core import build_profile


class BuildProfileTest(unittest.TestCase):
    def test_default_profile_prefers_agent_imagegen_and_safe_effects(self):
        profile = build_profile.default_build_profile()
        self.assertEqual(profile["artifact_role"], "build_profile")
        self.assertEqual(profile["fallback_visual_provider"], "assistant_imagegen")
        self.assertEqual(profile["motion_graphics_backend"], "ffmpeg_libass")
        self.assertFalse(profile["effects_enabled"])
        self.assertIn("assistant_imagegen", profile["provider_priority"])
        self.assertNotIn("comfyui", profile["provider_priority"])

    def test_load_override_preserves_unspecified_defaults(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "build_profile.json"
            p.write_text(json.dumps({
                "render_profile": "motion_graphics",
                "effects_enabled": True,
                "motion_graphics_backend": "html_playwright",
            }), encoding="utf-8")
            profile = build_profile.load_build_profile(p)
        self.assertEqual(profile["render_profile"], "motion_graphics")
        self.assertTrue(profile["effects_enabled"])
        self.assertEqual(profile["fallback_visual_provider"], "assistant_imagegen")
        self.assertEqual(profile["motion_graphics_backend"], "html_playwright")

    def test_rejects_comfyui_as_active_provider(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "bad_profile.json"
            p.write_text(json.dumps({"fallback_visual_provider": "comfyui"}), encoding="utf-8")
            with self.assertRaises(ValueError):
                build_profile.load_build_profile(p)

    def test_write_profile_is_traceable_artifact(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "build_profile.json"
            result = build_profile.write_build_profile(out)
            payload = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(result, str(out))
        self.assertEqual(payload["artifact_role"], "build_profile")
        self.assertEqual(payload["build_profile_version"], 1)


if __name__ == "__main__":
    unittest.main()
