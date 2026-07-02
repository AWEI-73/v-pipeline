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

    def test_selection_plan_uses_reviewed_source_material_matrix(self):
        timeline = build_source_timeline_map(
            "source.mp4",
            soundtrack_probe={
                "features": {
                    "energy_curve": [
                        {"start_sec": 0, "end_sec": 12, "relative_energy": 0.2},
                        {"start_sec": 12, "end_sec": 24, "relative_energy": 0.9},
                        {"start_sec": 24, "end_sec": 36, "relative_energy": 0.1},
                    ]
                }
            },
            window_sec=12,
            duration_probe=lambda _source: 48,
        )
        matrix = {
            "artifact_role": "source_material_matrix",
            "windows": [
                {
                    "window_id": "win_001",
                    "visual": {
                        "review_status": "reviewed",
                        "content_type": "irrelevant_title_card",
                        "usable_for": [],
                    },
                    "selection": {"decision": "reject", "reject_reason": "not useful"},
                },
                {
                    "window_id": "win_002",
                    "visual": {
                        "review_status": "reviewed",
                        "content_type": "satellite_instrument_explainer",
                        "usable_for": ["practice_highlight", "technical_detail"],
                    },
                    "selection": {"decision": "keep"},
                },
            ],
        }

        timeline = build_source_timeline_map(
            "source.mp4",
            soundtrack_probe={},
            source_material_matrix=matrix,
            window_sec=12,
            duration_probe=lambda _source: 48,
        )
        plan = build_highlight_selection_plan(
            timeline,
            intent="technical detail highlight",
            target_sec=24,
            clip_sec=10,
        )

        selected_ids = plan["selected_window_ids"]
        self.assertIn("win_002", selected_ids)
        self.assertNotIn("win_001", selected_ids)
        reviewed_clip = next(clip for clip in plan["clips"] if clip["window_id"] == "win_002")
        self.assertEqual(reviewed_clip["visual_decision"], "keep")
        self.assertIn("reviewed material matrix", reviewed_clip["selection_reason"])

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

    def test_writer_accepts_source_material_matrix_path(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            source = out / "source.mp4"
            source.write_bytes(b"placeholder")
            matrix = out / "source_material_matrix.json"
            matrix.write_text(json.dumps({
                "artifact_role": "source_material_matrix",
                "windows": [
                    {
                        "window_id": "win_000",
                        "visual": {
                            "review_status": "reviewed",
                            "content_type": "bad_opening",
                            "usable_for": [],
                        },
                        "selection": {"decision": "reject", "reject_reason": "bad"},
                    },
                    {
                        "window_id": "win_001",
                        "visual": {
                            "review_status": "reviewed",
                            "content_type": "strong_mission_visual",
                            "usable_for": ["opening", "highlight"],
                        },
                        "selection": {"decision": "keep"},
                    },
                ],
            }), encoding="utf-8")

            result = write_source_highlight_plan(
                source,
                out_dir=out,
                source_material_matrix_path=matrix,
                intent="mission highlight",
                target_sec=20,
                window_sec=12,
                clip_sec=10,
                duration_probe=lambda _source: 36,
            )

            self.assertTrue(result["ok"])
            self.assertIn("win_001", result["selected_window_ids"])
            self.assertNotIn("win_000", result["selected_window_ids"])


if __name__ == "__main__":
    unittest.main()
