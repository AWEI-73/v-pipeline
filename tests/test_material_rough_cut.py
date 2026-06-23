import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core.material_rough_cut import build_rough_cut_plan


def _contract():
    return {
        "segments": [
            {
                "segment": 1,
                "requested_duration_sec": 4,
                "material_fit": {"need_refs": ["nd_opening"]},
            },
            {
                "segment": 2,
                "requested_duration_sec": 6,
                "material_fit": {"need_refs": ["nd_closing"]},
            },
        ]
    }


def _project_map():
    return {
        "artifact_role": "project_material_map",
        "assets": [
            {
                "asset_id": "clip-a",
                "asset_type": "video",
                "source": "materials/a.mp4",
                "scenes": [
                    {
                        "scene_index": 0,
                        "start": 2.0,
                        "end": 8.0,
                        "caption": "opening cohort",
                        "satisfies": [{"need_id": "nd_opening", "status": "accepted"}],
                    }
                ],
            },
            {
                "asset_id": "clip-b",
                "asset_type": "video",
                "source": "materials/b.mp4",
                "scenes": [
                    {
                        "scene_index": 0,
                        "start": 10.0,
                        "end": 20.0,
                        "caption": "closing group",
                        "satisfies": [{"need_id": "nd_closing", "status": "accepted"}],
                    }
                ],
            },
        ],
    }


class MaterialRoughCutTest(unittest.TestCase):
    def test_builds_timeline_from_reviewed_scene_to_need_edges(self):
        plan = build_rough_cut_plan(_contract(), _project_map())

        self.assertTrue(plan["ok"], plan)
        self.assertEqual(plan["artifact_role"], "rough_cut_plan")
        self.assertEqual(plan["clip_count"], 2)
        self.assertEqual(plan["total_duration_sec"], 10.0)
        first = plan["clips"][0]
        self.assertEqual(first["segment"], 1)
        self.assertEqual(first["need_id"], "nd_opening")
        self.assertEqual(first["source_path"], "materials/a.mp4")
        self.assertEqual(first["start_sec"], 2.0)
        self.assertEqual(first["duration_sec"], 4.0)
        self.assertEqual(first["scene_id"], "clip-a:0")

    def test_flags_missing_segment_material_without_inventing_clip(self):
        contract = _contract()
        project_map = _project_map()
        project_map["assets"][1]["scenes"][0]["satisfies"][0]["status"] = "rejected"

        plan = build_rough_cut_plan(contract, project_map)

        self.assertFalse(plan["ok"])
        self.assertEqual(plan["clip_count"], 1)
        self.assertEqual(plan["gaps"][0]["segment"], 2)
        self.assertEqual(plan["gaps"][0]["need_id"], "nd_closing")

    def test_records_source_repeat_count_for_review(self):
        project_map = _project_map()
        project_map["assets"][1]["asset_id"] = "clip-a"
        project_map["assets"][1]["source"] = "materials/a.mp4"

        plan = build_rough_cut_plan(_contract(), project_map)

        self.assertEqual(plan["clips"][0]["source_repeat_count"], 1)
        self.assertEqual(plan["clips"][1]["source_repeat_count"], 2)
        self.assertEqual(plan["source_repetition"]["materials/a.mp4"], 2)

    def test_cuts_requested_duration_from_reviewed_usable_range(self):
        contract = {
            "segments": [
                {
                    "segment": 1,
                    "requested_duration_sec": 20,
                    "material_fit": {"need_refs": ["nd_opening"]},
                }
            ]
        }
        project_map = {
            "assets": [
                {
                    "asset_id": "clip-a",
                    "asset_type": "video",
                    "source": "materials/a.mp4",
                    "scenes": [
                        {
                            "scene_index": 0,
                            "start": 0.0,
                            "end": 50.0,
                            "caption": "full raw clip",
                            "satisfies": [
                                {
                                    "need_id": "nd_opening",
                                    "status": "accepted",
                                    "usable_range": {"start": 12.0, "end": 42.0},
                                }
                            ],
                        }
                    ],
                }
            ],
        }

        plan = build_rough_cut_plan(contract, project_map)

        self.assertTrue(plan["ok"], plan)
        self.assertEqual(plan["clips"][0]["start_sec"], 12.0)
        self.assertEqual(plan["clips"][0]["duration_sec"], 20.0)
        self.assertEqual(plan["clips"][0]["available_range_sec"], 30.0)

    def test_cli_writes_rough_cut_and_timeline_build(self):
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = root / "segment_contract.json"
            project_map = root / "project_material_map.json"
            out = root / "rough_cut_plan.json"
            timeline = root / "timeline_build.json"
            contract.write_text(json.dumps(_contract()), encoding="utf-8")
            project_map.write_text(json.dumps(_project_map()), encoding="utf-8")

            proc = subprocess.run(
                [
                    sys.executable,
                    "tools/material_rough_cut.py",
                    "--contract",
                    str(contract),
                    "--project-map",
                    str(project_map),
                    "--out",
                    str(out),
                    "--timeline-out",
                    str(timeline),
                ],
                cwd=repo,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue(out.exists())
            self.assertTrue(timeline.exists())
            payload = json.loads(timeline.read_text(encoding="utf-8"))
            self.assertEqual(len(payload["clips"]), 2)


if __name__ == "__main__":
    unittest.main()
