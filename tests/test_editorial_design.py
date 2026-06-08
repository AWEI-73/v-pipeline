"""Tests for video_pipeline_core.editorial_design.

Covers:
  - default_editorial_design (blueprint conversion of mode and energy curve)
  - validate_editorial_design (clean pass, blocklisted provider, path, filename, missing sections)
"""
import unittest

from video_pipeline_core.editorial_design import default_editorial_design, validate_editorial_design


class TestDefaultEditorialDesign(unittest.TestCase):
    """Test generating defaults from blueprints."""

    def test_default_without_blueprint(self):
        d = default_editorial_design()
        self.assertEqual(d["video_mode"], "training_recap")
        self.assertEqual(
            d["editorial_intent"]["energy_curve"],
            ["opening_calm", "training_active", "achievement_proud", "closing_emotional"],
        )

    def test_default_with_blueprint(self):
        blueprint = {
            "mode_hint": "rhythmic_mv",
            "beats": [
                {"intended_feeling": "calm_intro"},
                {"intended_feeling": "energy_build"},
                {"intended_feeling": "proud_payoff"},
            ],
        }
        d = default_editorial_design(blueprint)
        self.assertEqual(d["video_mode"], "rhythmic_mv")
        self.assertEqual(
            d["editorial_intent"]["energy_curve"],
            ["calm_intro", "energy_build", "proud_payoff"],
        )


class TestValidateEditorialDesign(unittest.TestCase):
    """Test validation and blocklist rules."""

    def test_validate_clean_default_passes(self):
        d = default_editorial_design()
        res = validate_editorial_design(d)
        self.assertTrue(res["ok"])
        self.assertEqual(len(res["errors"]), 0)

    def test_validate_missing_section_fails(self):
        d = default_editorial_design()
        d.pop("still_image_strategy")
        res = validate_editorial_design(d)
        self.assertFalse(res["ok"])
        self.assertTrue(any("Missing required section" in err for err in res["errors"]))

    def test_validate_provider_blocklist_fails(self):
        d = default_editorial_design()
        # Insert blocked word 'pexels'
        d["narration_strategy"]["speaker"] = "pexels_narrator"
        res = validate_editorial_design(d)
        self.assertFalse(res["ok"])
        self.assertTrue(any("blocked provider/template keyword" in err for err in res["errors"]))

    def test_validate_filename_blocklist_fails(self):
        d = default_editorial_design()
        # Insert filename 'bgm.mp3'
        d["music_strategy"]["mode"] = "bgm.mp3"
        res = validate_editorial_design(d)
        self.assertFalse(res["ok"])
        self.assertTrue(any("blocked filename pattern" in err for err in res["errors"]))

    def test_validate_path_blocklist_fails(self):
        d = default_editorial_design()
        # Insert file path
        d["effects_strategy"]["intensity"] = "/usr/local/effects"
        res = validate_editorial_design(d)
        self.assertFalse(res["ok"])
        self.assertTrue(any("blocked path pattern" in err for err in res["errors"]))


if __name__ == "__main__":
    unittest.main()
