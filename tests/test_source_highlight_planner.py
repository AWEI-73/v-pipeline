import json
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core.source_highlight_planner import (
    build_highlight_selection_plan,
    build_source_timeline_map,
    write_source_highlight_plan,
)


class SourceHighlightPlannerTests(unittest.TestCase):
    def test_builds_timeline_map_from_audio_energy(self):
        probe = {
            "features": {
                "energy_curve": [
                    {"start_sec": 0, "end_sec": 12, "relative_energy": 0.1},
                    {"start_sec": 12, "end_sec": 24, "relative_energy": 0.2},
                    {"start_sec": 24, "end_sec": 36, "relative_energy": 0.55},
                    {"start_sec": 96, "end_sec": 108, "relative_energy": 0.25},
                ]
            }
        }
        timeline = build_source_timeline_map(
            "source.mp4",
            soundtrack_probe=probe,
            window_sec=12,
            duration_probe=lambda _source: 108,
        )

        self.assertEqual(timeline["artifact_role"], "source_timeline_map")
        self.assertEqual(len(timeline["windows"]), 9)
        roles = {window["timeline_role"] for window in timeline["windows"]}
        self.assertIn("opening", roles)
        self.assertIn("practice_highlight", roles)
        self.assertIn("ending", roles)

    def test_selection_plan_honors_chinese_practice_and_ending_intent(self):
        timeline = build_source_timeline_map(
            "source.mp4",
            soundtrack_probe={
                "features": {
                    "energy_curve": [
                        {"start_sec": 36, "end_sec": 48, "relative_energy": 0.7},
                        {"start_sec": 96, "end_sec": 108, "relative_energy": 0.2},
                    ]
                }
            },
            window_sec=12,
            duration_probe=lambda _source: 108,
        )

        plan = build_highlight_selection_plan(
            timeline,
            intent="\u5be6\u7fd2\u985e\u5225\u7cbe\u83ef\uff0c\u7d50\u5c3e\uff0c\u97f3\u6a02\u91cd\u88dc",
            target_sec=60,
            clip_sec=10,
        )

        self.assertEqual(plan["artifact_role"], "highlight_selection_plan")
        self.assertIn("internship", plan["intent_tokens"])
        self.assertIn("ending", plan["intent_tokens"])
        self.assertLessEqual(plan["planned_duration_sec"], 60)
        roles = {clip["role"] for clip in plan["clips"]}
        self.assertIn("opening", roles)
        self.assertIn("practice_highlight", roles)
        self.assertIn("ending", roles)
        self.assertLessEqual(sum(1 for clip in plan["clips"] if clip["role"] == "ending"), 2)
        self.assertEqual(plan["rough_cut_plan"]["clips"], plan["clips"])

    def test_writer_persists_canonical_artifacts(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            source = out / "source.mp4"
            source.write_bytes(b"placeholder")
            probe = out / "soundtrack_probe_report.json"
            probe.write_text(
                json.dumps(
                    {
                        "features": {
                            "energy_curve": [
                                {"start_sec": 24, "end_sec": 36, "relative_energy": 0.8}
                            ]
                        }
                    }
                ),
                encoding="utf-8",
            )

            result = write_source_highlight_plan(
                source,
                out_dir=out,
                soundtrack_probe_path=probe,
                intent="\u5be6\u7fd2\u7cbe\u83ef\u7d50\u5c3e",
                target_sec=40,
                window_sec=12,
                clip_sec=10,
                duration_probe=lambda _source: 72,
            )

            self.assertTrue(result["ok"])
            for name in ("source_timeline_map.json", "highlight_selection_plan.json", "rough_cut_plan.json"):
                self.assertTrue((out / name).is_file())
            rough = json.loads((out / "rough_cut_plan.json").read_text(encoding="utf-8"))
            self.assertEqual(rough["route"], "single_source_highlight")


if __name__ == "__main__":
    unittest.main()
