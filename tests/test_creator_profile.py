"""creator_profile — P2 stable creator/channel defaults."""
import json
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core import creator_profile as cp


class CreatorProfileDefaultsTest(unittest.TestCase):
    def test_default_profile_shape(self):
        p = cp.default_creator_profile()
        self.assertEqual(p["artifact_role"], "creator_profile")
        self.assertEqual(p["profile_version"], 1)
        for section in ("brand", "platform_defaults", "subtitle_defaults",
                        "editing_defaults", "audio_defaults", "outro_defaults"):
            self.assertIn(section, p)

    def test_validate_rejects_bad_version(self):
        with self.assertRaises(ValueError):
            cp.validate_creator_profile({"profile_version": 2})

    def test_load_merges_partial_override(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "creator_profile.json"
            path.write_text(json.dumps({
                "profile_version": 1,
                "platform_defaults": {"platform": "tiktok"},
            }), encoding="utf-8")
            loaded = cp.load_creator_profile(path)
            self.assertEqual(loaded["platform_defaults"]["platform"], "tiktok")
            # unspecified sections still present from defaults
            self.assertIn("editing_defaults", loaded)

    def test_write_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "creator_profile.json"
            cp.write_creator_profile(path)
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved["artifact_role"], "creator_profile")
            self.assertEqual(saved["profile_version"], 1)


class ResolveDefaultsTest(unittest.TestCase):
    def _profile(self):
        p = cp.default_creator_profile()
        p["platform_defaults"]["platform"] = "youtube"
        p["platform_defaults"]["aspect_ratio"] = "16:9"
        p["editing_defaults"]["render_profile"] = "no_effects"
        p["editing_defaults"]["max_source_repeats"] = 2
        p["audio_defaults"]["ducking"] = True
        return p

    def test_empty_brief_uses_creator_defaults(self):
        out = cp.resolve_defaults(self._profile(), brief={})
        self.assertEqual(out["resolved"]["platform"], "youtube")
        self.assertEqual(out["resolved"]["max_source_repeats"], 2)
        self.assertEqual(out["sources"]["platform"], "creator_profile")
        # provenance lists creator-applied keys
        self.assertIn("platform", out["applied"])

    def test_brief_always_overrides_creator(self):
        out = cp.resolve_defaults(self._profile(),
                                  brief={"platform": "tiktok", "aspect_ratio": "9:16"})
        self.assertEqual(out["resolved"]["platform"], "tiktok")
        self.assertEqual(out["resolved"]["aspect_ratio"], "9:16")
        self.assertEqual(out["sources"]["platform"], "brief")
        # creator still fills the keys the brief did not set
        self.assertEqual(out["sources"]["render_profile"], "creator_profile")
        # overridden keys are not counted as creator-applied
        self.assertNotIn("platform", out["applied"])
        self.assertIn("render_profile", out["applied"])

    def test_missing_values_are_omitted(self):
        # a profile with no music_style set -> key absent from resolved
        out = cp.resolve_defaults(cp.default_creator_profile(), brief={})
        self.assertNotIn("music_style", out["resolved"])

    def test_none_inputs_safe(self):
        out = cp.resolve_defaults(None, brief=None)
        self.assertEqual(out["resolved"], {})
        self.assertEqual(out["applied"], [])

    def test_unsupported_aspect_ratio_reports_required_followup(self):
        out = cp.resolve_defaults(self._profile(), brief={"aspect_ratio": "32:9"})

        self.assertNotIn("aspect_ratio", out["resolved"])
        self.assertEqual(out["sources"]["aspect_ratio"], "invalid")
        questions = " ".join(out["required_followup_questions"]).lower()
        self.assertIn("aspect ratio", questions)
        self.assertIn("16:9", questions)


class CreatorProfileCliTest(unittest.TestCase):
    def test_init_writes_default_profile(self):
        import video_tools
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as d:
            out = str(Path(d) / "creator_profile.json")
            video_tools.cmd_creator_profile(
                SimpleNamespace(init=True, out=out, profile=None, brief=None))
            saved = json.loads(Path(out).read_text(encoding="utf-8"))
            self.assertEqual(saved["artifact_role"], "creator_profile")

    def test_resolve_against_brief(self):
        import io
        import video_tools
        from contextlib import redirect_stdout
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as d:
            prof = Path(d) / "creator_profile.json"
            prof.write_text(json.dumps({
                "profile_version": 1,
                "platform_defaults": {"platform": "youtube"},
                "editing_defaults": {"max_source_repeats": 2},
            }), encoding="utf-8")
            brief = Path(d) / "brief.json"
            brief.write_text(json.dumps({"platform": "tiktok"}), encoding="utf-8")
            buf = io.StringIO()
            with redirect_stdout(buf):
                video_tools.cmd_creator_profile(
                    SimpleNamespace(init=False, out=None, profile=str(prof), brief=str(brief)))
            out = json.loads(buf.getvalue())
            self.assertEqual(out["resolved"]["platform"], "tiktok")
            self.assertEqual(out["sources"]["platform"], "brief")
            self.assertIn("max_source_repeats", out["applied"])


if __name__ == "__main__":
    unittest.main()
