import unittest

from video_pipeline_core import material_retrieval


class MaterialRetrievalRepeatCapTest(unittest.TestCase):
    def _map(self, asset_id, source, caption, start=0.0):
        return {
            "asset_id": asset_id,
            "asset_type": "video",
            "source": source,
            "scenes": [{
                "start": start,
                "end": start + 8.0,
                "caption": caption,
                "function": "establish",
                "visual_family": "group",
                "angle_scale": "wide",
                "satisfies": [{"need_id": "need_a", "status": "accepted"}],
            }],
        }

    def test_plan_ranked_windows_respects_cross_segment_source_repeat_cap(self):
        segment = {
            "segment": 2,
            "visual_desc": "training group",
            "material_fit": {"need_refs": ["need_a"]},
        }
        maps = [
            self._map("a", "same.mp4", "training group"),
            self._map("b", "fresh.mp4", "training group"),
        ]
        history = [{"source": "same.mp4"}]

        slots = material_retrieval.plan_ranked_windows(
            segment,
            maps,
            limit=1,
            clip_dur=4.0,
            history=history,
            max_source_repeats=1,
        )

        self.assertEqual(slots[0]["source"], "fresh.mp4")
        self.assertEqual(slots[0]["source_repeat_count"], 0)

    def test_plan_ranked_windows_counts_selected_sources_within_segment(self):
        segment = {
            "segment": 1,
            "visual_desc": "training group",
            "material_fit": {"need_refs": ["need_a"]},
        }
        maps = [
            self._map("a", "same.mp4", "training group", start=0.0),
            self._map("b", "same.mp4", "training group", start=10.0),
            self._map("c", "fresh.mp4", "training group", start=20.0),
        ]

        slots = material_retrieval.plan_ranked_windows(
            segment,
            maps,
            limit=2,
            clip_dur=4.0,
            max_source_repeats=1,
        )

        self.assertEqual([slot["source"] for slot in slots], ["same.mp4", "fresh.mp4"])


if __name__ == "__main__":
    unittest.main()
