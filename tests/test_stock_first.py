import copy
import unittest

from video_pipeline_core import contract_adapter
from video_pipeline_core import stock_first


class StockFirstTest(unittest.TestCase):
    def _contract(self):
        return {
            "style": "mv",
            "material_source_mode": "stock_first",
            "story_truth_level": "conceptual",
            "segments": [
                {
                    "segment": 1,
                    "core": {"section_role": "opening", "story_purpose": "建立城市清晨工作氛圍",
                             "timeline_source": "fixed", "review_required": False},
                    "material_fit": {"visual_desc": "城市清晨街道與工作車", "search_query": "city morning work truck",
                                     "fallback_policy": "stock_bridge", "reason": "概念情緒段"},
                    "audio": {"role": "music", "reason": "鋪陳"},
                    "visual_style": {"layout": "single", "pace": "hold", "reason": "建立氛圍"},
                    "text_layer": "none",
                },
                {
                    "segment": 2,
                    "core": {"section_role": "hold", "story_purpose": "指定學員本人心得",
                             "timeline_source": "fixed", "review_required": True},
                    "material_fit": {"visual_desc": "學員本人受訪", "must_include": "學員本人",
                                     "fallback_policy": "reshoot_first", "reason": "真實人物不可替代"},
                    "audio": {"role": "duck", "reason": "保留原音"},
                    "visual_style": {"layout": "single", "pace": "hold", "reason": "人物段"},
                    "text_layer": {"subtitle": "auto", "reason": "訪談字幕"},
                },
            ],
        }

    def test_build_stock_first_route_marks_allowed_and_protected_segments(self):
        route = stock_first.build_stock_first_route(self._contract())
        self.assertEqual(route["artifact_role"], "stock_first_route")
        self.assertEqual(route["segments"][0]["selected_route"], "stock_bridge")
        self.assertEqual(route["segments"][0]["source"], "stock")
        self.assertEqual(route["segments"][0]["node_trace"], ["Node 2", "Node 8", "Node 9"])
        self.assertEqual(route["segments"][1]["selected_route"], "reshoot")
        self.assertIn("stock_bridge", route["segments"][1]["rejected_routes"])

    def test_apply_stock_first_route_sets_source_and_search_query_only_when_allowed(self):
        contract = self._contract()
        routed = stock_first.apply_stock_first_route(contract)
        self.assertEqual(routed["segments"][0]["source"], "stock")
        self.assertEqual(routed["segments"][0]["material_fit"]["search_query"], "city morning work truck")
        self.assertNotIn("source", routed["segments"][1])
        self.assertNotIn("stock_first_route", contract)

    def test_contract_adapter_can_turn_stock_first_contract_into_stock_runtime_payload(self):
        contract = stock_first.apply_stock_first_route(self._contract())
        payload = contract_adapter.contract_to_mv_script(contract)
        self.assertEqual(payload["segments"][0]["source"], "stock")
        self.assertEqual(payload["segments"][0]["search_query"], "city morning work truck")
        self.assertNotEqual(payload["segments"][1].get("source"), "stock")

    def test_no_stock_first_mode_does_not_rewrite_contract(self):
        contract = self._contract()
        contract.pop("material_source_mode")
        routed = stock_first.apply_stock_first_route(copy.deepcopy(contract))
        self.assertNotIn("source", routed["segments"][0])

    def test_apply_stock_first_route_preserves_local_and_generated_sources(self):
        contract = self._contract()
        contract["segments"][0]["source"] = "local"
        contract["segments"][0]["file"] = "path/to/local.mp4"
        routed = stock_first.apply_stock_first_route(contract)
        self.assertEqual(routed["segments"][0]["source"], "local")
        self.assertEqual(routed["segments"][0]["file"], "path/to/local.mp4")


if __name__ == "__main__":
    unittest.main()
