"""Photo-stack renderer (opt-in) tests — no network (fetch is injected)."""
import unittest

from video_pipeline_core import mv_cut


def _enum_seg(segment=2, items=("Ethiopia", "Colombia", "Guatemala")):
    return {
        "segment": segment,
        "layout": "montage",
        "pace": "fast",
        "source": "stock",
        "search_query": "coffee beans origin",
        "visual_desc": "三產地咖啡豆",
        "editing_intent": {"content_pattern": "enumeration"},
        "material_treatment": {"treatment": "photo_stack_beat", "items": list(items),
                               "label_per_item": True},
    }


class StackItemsTests(unittest.TestCase):
    def test_detects_treatment(self):
        self.assertEqual(mv_cut._stack_items(_enum_seg()),
                         ["Ethiopia", "Colombia", "Guatemala"])

    def test_detects_content_pattern_only(self):
        s = {"editing_intent": {"content_pattern": "enumeration"},
             "material_treatment": {"items": ["a", "b"]}}
        self.assertEqual(mv_cut._stack_items(s), ["a", "b"])

    def test_none_when_no_items(self):
        self.assertIsNone(mv_cut._stack_items({"editing_intent": {"content_pattern": "enumeration"}}))

    def test_none_for_plain_segment(self):
        self.assertIsNone(mv_cut._stack_items({"segment": 1, "layout": "montage"}))


class AllocateStackTests(unittest.TestCase):
    def test_stack_segment_gets_one_clip_per_item(self):
        segs = [_enum_seg(items=("a", "b", "c", "d"))]
        alloc = mv_cut.allocate_segments(segs, total_dur=20.0)
        self.assertEqual(alloc[0]["n_clips"], 4)

    def test_stack_stills_are_beat_fast_not_full_budget(self):
        # one enumeration seg over a 30s budget must NOT make 30/3=10s stills;
        # each still is ~stack_shot_sec (beat-fast), independent of the budget.
        segs = [_enum_seg(items=("a", "b", "c"))]
        alloc = mv_cut.allocate_segments(segs, total_dur=30.0, stack_shot_sec=0.7)
        self.assertEqual(alloc[0]["clip_dur"], 0.7)
        self.assertLess(alloc[0]["clip_dur"], 2.0)

    def test_plain_montage_unchanged(self):
        segs = [{"segment": 1, "layout": "montage", "pace": "fast"}]
        alloc = mv_cut.allocate_segments(segs, total_dur=20.0)
        self.assertGreaterEqual(alloc[0]["n_clips"], 1)  # round(20/1.5) ~ 13, unaffected by stack


class StackPlannerTests(unittest.TestCase):
    def test_produces_labeled_stills(self):
        seg = _enum_seg()
        a = {"n_clips": 3, "clip_dur": 0.7, "budget": 2.1}
        calls = []

        def fake_fetch(query, out):
            calls.append(query)
            return out, "pexels-photo"

        slots, entry, msgs = mv_cut._plan_stock_stack_segment(
            seg, a, mat_dir="/tmp", items=seg["material_treatment"]["items"],
            _fetch_photo=fake_fetch)
        self.assertEqual(len(slots), 3)
        # each slot is a labeled still carrying its item name
        labels = [sl["text"]["label"] for sl in slots]
        self.assertEqual(labels, ["Ethiopia", "Colombia", "Guatemala"])
        self.assertTrue(all(sl["is_photo"] for sl in slots))
        self.assertEqual(entry["treatment"], "photo_stack_beat")
        # per-item query included the item name
        self.assertTrue(any("Ethiopia" in q for q in calls))

    def test_gap_when_fetch_fails(self):
        seg = _enum_seg(items=("x", "y"))
        a = {"n_clips": 2, "clip_dur": 1.0, "budget": 2.0}

        def no_photo(query, out):
            return None, None

        slots, entry, msgs = mv_cut._plan_stock_stack_segment(
            seg, a, mat_dir="/tmp", items=["x", "y"], _fetch_photo=no_photo)
        self.assertEqual(len(slots), 0)
        self.assertEqual(entry["picked_scores"], [mv_cut.GAP, mv_cut.GAP])


if __name__ == "__main__":
    unittest.main()
