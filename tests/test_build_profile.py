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

    def test_verification_tools_default_off(self):
        profile = build_profile.default_build_profile()
        vt = profile["verification_tools"]
        self.assertEqual(set(vt), {"timeline_invariants", "broll_audit",
                                   "caption_audit", "keyframe_grid", "visual_audit",
                                   "presentation_feel_audit"})
        self.assertTrue(all(v is False for v in vt.values()))
        self.assertEqual(profile["keyframe_grid"], {"sample_count": 12, "columns": 4})
        self.assertEqual(profile["broll_policy"],
                         {"target_ratio": None, "max_source_repeats": None})

    def test_verification_tools_helper_defaults_missing_to_false(self):
        # a profile missing the key, or with a partial dict, is read safely
        self.assertEqual(
            build_profile.verification_tools({}),
            {"timeline_invariants": False, "broll_audit": False,
             "caption_audit": False, "keyframe_grid": False, "visual_audit": False,
             "presentation_feel_audit": False},
        )
        partial = {"verification_tools": {"timeline_invariants": True}}
        got = build_profile.verification_tools(partial)
        self.assertTrue(got["timeline_invariants"])
        self.assertFalse(got["broll_audit"])

    def test_profile_with_verification_tools_validates(self):
        profile = build_profile.default_build_profile()
        profile["verification_tools"]["timeline_invariants"] = True
        build_profile.validate_build_profile(profile)  # must not raise

    def test_render_backend_defaults_to_ffmpeg_unattended(self):
        profile = build_profile.default_build_profile()
        self.assertEqual(profile["render_backend"], "ffmpeg")
        self.assertFalse(profile["requires_human_or_computer_use"])

    def test_capcut_backend_is_allowed(self):
        profile = build_profile.default_build_profile()
        profile["render_backend"] = "capcut_draft"
        profile["requires_human_or_computer_use"] = True
        build_profile.validate_build_profile(profile)  # must not raise

    def test_unknown_render_backend_rejected(self):
        profile = build_profile.default_build_profile()
        profile["render_backend"] = "premiere"
        with self.assertRaises(ValueError):
            build_profile.validate_build_profile(profile)

    def test_visual_judge_defaults_to_agent(self):
        self.assertEqual(build_profile.default_build_profile()["visual_judge"], "agent")

    def test_visual_judge_rejects_unknown_mode(self):
        profile = build_profile.default_build_profile()
        profile["visual_judge"] = "cloud_api"
        with self.assertRaises(ValueError):
            build_profile.validate_build_profile(profile)

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
