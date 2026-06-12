import tempfile
import unittest
from pathlib import Path

from video_pipeline_core import presentation_feel_audit as pfa


class PresentationFeelAuditTest(unittest.TestCase):
    def test_old_presentation_style_fixture_triggers_at_least_three_detectors(self):
        assembly = {
            "mode": "rhythmic_mv",
            "segments": [
                {"segment": 1, "execution_plan": {"subtitles": {"placement": "center"}}},
                {"segment": 2},
            ],
        }
        timeline = {
            "clips": [
                {
                    "segment": 1,
                    "source_path": "slide.jpg",
                    "duration_sec": 6.0,
                    "timeline_in_sec": 0.0,
                    "still_treatment": {"mode": "slow_push"},
                    "text_overlay": {"narrative": "A large centered explanation"},
                },
                {
                    "segment": 1,
                    "source_path": "slide.jpg",
                    "duration_sec": 4.0,
                    "timeline_in_sec": 6.0,
                    "still_treatment": {"mode": "slow_push"},
                    "text_overlay": {"narrative": "More centered explanation"},
                },
                {
                    "segment": 1,
                    "source_path": "slide.jpg",
                    "duration_sec": 4.0,
                    "timeline_in_sec": 10.0,
                    "still_treatment": {"mode": "slow_push"},
                    "text_overlay": {"narrative": "Still explaining"},
                },
                {
                    "segment": 2,
                    "source_path": "static.mp4",
                    "start_sec": 0.0,
                    "duration_sec": 5.0,
                    "timeline_in_sec": 14.0,
                    "text_overlay": "none",
                },
            ]
        }

        result = pfa.audit_presentation_feel(
            assembly,
            timeline,
            {"max_still_hold_sec_by_mode": {"rhythmic_mv": 3.0}},
            motion_probe=lambda _clip: 0.95,
        )

        checks = {finding["check"] for finding in result["findings"]}
        self.assertFalse(result["pass"])
        self.assertGreaterEqual(len(checks), 3)
        self.assertIn("static_photo_too_long", checks)
        self.assertIn("no_foreground_motion", checks)
        self.assertIn("repeated_push_in", checks)
        self.assertIn("text_blocks_dominate", checks)

    def test_varied_layered_timeline_passes(self):
        assembly = {
            "mode": "rhythmic_mv",
            "segments": [{"segment": 1}, {"segment": 2}, {"segment": 3}],
        }
        timeline = {
            "clips": [
                {
                    "segment": 1,
                    "source_path": "a.mp4",
                    "start_sec": 0.0,
                    "duration_sec": 2.0,
                    "timeline_in_sec": 0.0,
                    "composition_layers": 2,
                    "text_overlay": "none",
                },
                {
                    "segment": 2,
                    "source_path": "b.jpg",
                    "duration_sec": 2.0,
                    "timeline_in_sec": 2.0,
                    "still_treatment": {"mode": "pan_left"},
                    "composition_layers": 2,
                    "text_overlay": {"label": "Place"},
                },
                {
                    "segment": 3,
                    "source_path": "c.jpg",
                    "duration_sec": 2.0,
                    "timeline_in_sec": 4.0,
                    "still_treatment": {"mode": "detail_push"},
                    "composition_layers": 2,
                    "text_overlay": "none",
                },
            ]
        }

        result = pfa.audit_presentation_feel(
            assembly, timeline, motion_probe=lambda _clip: 0.1
        )

        self.assertTrue(result["pass"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["score"], 100)

    def test_writer_outputs_stable_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "presentation_feel_audit.json"
            result = pfa.write_presentation_feel_audit(
                {"segments": []},
                {"clips": []},
                out,
            )

            self.assertEqual(result, str(out))
            self.assertTrue(out.exists())
            self.assertIn('"artifact_role": "presentation_feel_audit"', out.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
