import unittest

from video_pipeline_core.supply_review import fallback_maps_from_coverage, review_supply


def _map(asset_id, asset_type, scene_count=1):
    return {
        "asset_id": asset_id,
        "asset_type": asset_type,
        "scenes": [{"start": i, "end": i + 1} for i in range(scene_count)],
    }


class SupplyReviewTest(unittest.TestCase):
    def test_coverage_fallback_counts_positive_pick_as_one_window(self):
        coverage = {"assignments": [{"segment": 1, "picks": [
            {"path": "one.mp4", "score": 0.5},
            {"path": "wrong.mp4", "score": 0},
            {"path": "one.jpg", "score": 0.5},
        ]}]}
        maps = fallback_maps_from_coverage(coverage)
        self.assertEqual(len(maps), 2)
        self.assertEqual({item["asset_type"] for item in maps}, {"video", "photo"})

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
        self.assertEqual(result["segments"][0]["estimated_effective_shots"], 3)
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


if __name__ == "__main__":
    unittest.main()
