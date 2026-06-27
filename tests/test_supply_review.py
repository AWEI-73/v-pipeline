import unittest
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from video_pipeline_core.curator import build_material_coverage
from video_pipeline_core.supply_review import fallback_maps_from_coverage, review_supply


def _map(asset_id, asset_type, scene_count=1):
    return {
        "asset_id": asset_id,
        "asset_type": asset_type,
        "scenes": [{"start": i, "end": i + 1} for i in range(scene_count)],
    }


class SupplyReviewTest(unittest.TestCase):
    def test_supply_review_cli_accepts_utf8_bom_contract_and_maps(self):
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            maps_dir = root / "maps"
            maps_dir.mkdir()
            contract_path = root / "segment_contract.json"
            contract_path.write_text(
                json.dumps({
                    "segments": [{
                        "segment": 1,
                        "requested_duration_sec": 3,
                        "target_shot_sec": 3,
                        "material_map_ids": ["v1"],
                    }]
                }, ensure_ascii=False),
                encoding="utf-8-sig",
            )
            (maps_dir / "v1.map.json").write_text(
                json.dumps(_map("v1", "video", 3), ensure_ascii=False),
                encoding="utf-8-sig",
            )

            proc = subprocess.run(
                [
                    sys.executable,
                    "video_tools.py",
                    "supply-review",
                    str(contract_path),
                    "--maps-dir",
                    str(maps_dir),
                ],
                cwd=repo,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["segments"][0]["feasibility"], "ok")

    def test_coverage_fallback_counts_positive_pick_as_one_window(self):
        coverage = {"assignments": [{"segment": 1, "picks": [
            {"path": "one.mp4", "score": 0.5},
            {"path": "wrong.mp4", "score": 0},
            {"path": "one.jpg", "score": 0.5},
        ]}]}
        maps = fallback_maps_from_coverage(coverage)
        self.assertEqual(len(maps), 2)
        self.assertEqual({item["asset_type"] for item in maps}, {"video", "photo"})

    def test_stock_first_downloaded_files_feed_supply_without_vlm_caption(self):
        segments = [
            {"segment": 1, "source": "stock", "requested_duration_sec": 5,
             "target_shot_sec": 3, "visual_desc": "sunrise", "search_query": "sunrise"},
            {"segment": 2, "source": "stock", "requested_duration_sec": 5,
             "target_shot_sec": 3, "visual_desc": "forest", "search_query": "forest"},
        ]
        files = [
            {"path": "/run/materials/seg1_stock.mp4", "type": "video",
             "vlm_caption": None, "classify": {"usable": True}},
            {"path": "/run/materials/seg2_stock.mp4", "type": "video",
             "vlm_caption": None, "classify": {"usable": True}},
        ]

        coverage = build_material_coverage(segments, files)
        maps = fallback_maps_from_coverage(coverage)
        result = review_supply({"segments": segments}, maps, coverage_map=coverage)

        self.assertEqual([len(a["picks"]) for a in coverage["assignments"]], [1, 1])
        self.assertEqual([s["estimated_effective_shots"] for s in result["segments"]], [1, 1])
        self.assertNotEqual([s["feasibility"] for s in result["segments"]], ["gap", "gap"])

    def test_coverage_map_assignments_select_sources_and_preserve_gap(self):
        contract = {"segments": [
            {"segment": 1, "requested_duration_sec": 8, "target_shot_sec": 2},
            {"segment": 2, "requested_duration_sec": 8, "target_shot_sec": 2},
        ]}
        maps = [
            dict(_map("v1", "video", 4), source="one.mp4"),
            dict(_map("p1", "photo"), source="one.jpg"),
        ]
        coverage = {"assignments": [
            {"segment": 1, "picks": [{"path": "one.mp4"}, {"path": "one.jpg"}]},
            {"segment": 2, "picks": [], "gap": True},
        ]}
        result = review_supply(contract, maps, coverage_map=coverage)
        self.assertEqual(result["segments"][0]["estimated_effective_shots"], 2)
        self.assertEqual(result["segments"][0]["feasibility"], "thin")
        self.assertEqual(result["segments"][1]["feasibility"], "gap")

    def test_target_duration_allocates_requested_duration_by_weight(self):
        contract = {"segments": [
            {"segment": 1, "weight": 1},
            {"segment": 2, "weight": 3},
        ]}
        result = review_supply(contract, [], target_duration_sec=40)
        self.assertEqual(result["segments"][0]["requested_duration_sec"], 10)
        self.assertEqual(result["segments"][1]["requested_duration_sec"], 30)

    def test_thin_segment_recommends_shorten_from_actual_supply(self):
        contract = {
            "segments": [{
                "segment": 1,
                "requested_duration_sec": 30,
                "target_shot_sec": 2,
                "material_map_ids": ["v1", "v2", "p1", "p2", "p3"],
            }]
        }
        maps = [
            _map("v1", "video", 8),
            _map("v2", "video", 8),
            _map("p1", "photo"),
            _map("p2", "photo"),
            _map("p3", "photo"),
        ]

        result = review_supply(contract, maps)
        segment = result["segments"][0]

        self.assertEqual(segment["estimated_effective_shots"], 7)
        self.assertEqual(segment["max_honest_duration_sec"], 14.0)
        self.assertEqual(segment["feasibility"], "thin")
        self.assertEqual(segment["action"], "shorten_or_merge")

    def test_no_material_is_gap(self):
        result = review_supply(
            {"segments": [{"segment": "live-line", "requested_duration_sec": 10}]},
            [],
        )
        segment = result["segments"][0]
        self.assertEqual(segment["feasibility"], "gap")
        self.assertEqual(segment["action"], "await_material")

    def test_enough_material_is_ok(self):
        maps = [_map(f"p{i}", "photo") for i in range(5)]
        result = review_supply(
            {"segments": [{
                "segment": 1,
                "requested_duration_sec": 10,
                "target_shot_sec": 2,
                "material_map_ids": [m["asset_id"] for m in maps],
            }]},
            maps,
        )
        self.assertEqual(result["segments"][0]["feasibility"], "ok")

    def test_need_refs_select_canonical_satisfies_edges_without_coverage(self):
        maps = [
            dict(_map("p1", "photo"), scenes=[{
                "start": 0,
                "end": 0,
                "satisfies": [{"need_id": "nd_intro", "status": "accepted"}],
            }]),
            dict(_map("p2", "photo"), scenes=[{
                "start": 0,
                "end": 0,
                "satisfies": [{"need_id": "nd_intro", "status": "candidate"}],
            }]),
            dict(_map("p3", "photo"), scenes=[{
                "start": 0,
                "end": 0,
                "satisfies": [{"need_id": "nd_intro", "status": "accepted"}],
            }]),
            dict(_map("wrong", "photo"), scenes=[{
                "start": 0,
                "end": 0,
                "satisfies": [{"need_id": "nd_other", "status": "accepted"}],
            }]),
        ]

        result = review_supply({"segments": [{
            "segment": 1,
            "requested_duration_sec": 10,
            "target_shot_sec": 4,
            "material_fit": {"need_refs": ["nd_intro"]},
        }]}, maps)

        segment = result["segments"][0]
        self.assertEqual(segment["estimated_effective_shots"], 3)
        self.assertEqual(segment["unique_sources"], 3)
        self.assertEqual(segment["max_honest_duration_sec"], 12.0)
        self.assertEqual(segment["feasibility"], "ok")

    def test_need_refs_ignore_rejected_edges_and_do_not_fallback_to_coverage(self):
        maps = [
            dict(_map("p1", "photo"), source="matched.jpg", scenes=[{
                "start": 0,
                "end": 0,
                "satisfies": [{"need_id": "nd_intro", "status": "rejected"}],
            }]),
        ]
        coverage = {"assignments": [{"segment": 1, "picks": [{"path": "matched.jpg"}]}]}

        result = review_supply({"segments": [{
            "segment": 1,
            "requested_duration_sec": 4,
            "target_shot_sec": 4,
            "material_fit": {"need_refs": ["nd_intro"]},
        }]}, maps, coverage_map=coverage)

        segment = result["segments"][0]
        self.assertEqual(segment["estimated_effective_shots"], 0)
        self.assertEqual(segment["feasibility"], "gap")

    def test_need_refs_filter_matching_scenes_before_counting_video_windows(self):
        maps = [dict(_map("v1", "video"), scenes=[
            {"start": 0, "end": 4,
             "satisfies": [{"need_id": "nd_intro", "status": "accepted"}]},
            {"start": 4, "end": 8,
             "satisfies": [{"need_id": "nd_other", "status": "accepted"}]},
            {"start": 8, "end": 12,
             "satisfies": [{"need_id": "nd_other", "status": "accepted"}]},
        ])]

        result = review_supply({"segments": [{
            "segment": 1,
            "requested_duration_sec": 8,
            "target_shot_sec": 4,
            "material_fit": {"need_refs": ["nd_intro"]},
        }]}, maps)

        segment = result["segments"][0]
        self.assertEqual(segment["estimated_effective_shots"], 1)
        self.assertEqual(segment["max_honest_duration_sec"], 4.0)
        self.assertEqual(segment["feasibility"], "thin")

    def test_fast_mode_single_scene_video_counts_duration_not_scene_count(self):
        maps = [dict(_map("director_speech", "video"), scenes=[
            {"start": 0, "end": 70, "kind": "fast_scan_whole_video"},
        ])]

        result = review_supply({"segments": [{
            "segment": 1,
            "requested_duration_sec": 20,
            "target_shot_sec": 3,
            "material_map_ids": ["director_speech"],
        }]}, maps)

        segment = result["segments"][0]
        self.assertGreaterEqual(segment["estimated_effective_shots"], 6)
        self.assertGreaterEqual(segment["max_honest_duration_sec"], 20)
        self.assertEqual(segment["feasibility"], "ok")


if __name__ == "__main__":
    unittest.main()
