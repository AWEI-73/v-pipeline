"""Material intake funnel Stage 1: classify_asset (pure, content-agnostic).

Defaults encode the 結訓 policy (horizontal / >=1080 / >=3s); other film types
pass different policy params — the engine is general.
"""
import unittest

import video_tools as vt


class IngestWorkDirsTest(unittest.TestCase):
    """衍生檔(.converted/.keyframes)不可污染來源素材夾(回歸:之前寫進 src)。"""

    def test_derives_from_out_db_dir_not_source(self):
        def norm(p):
            import re
            return re.sub(r'^[a-zA-Z]:', '', p.replace("\\", "/"))
        cnv, kf = vt._ingest_work_dirs("/data/微電影素材", "/work/_pool/materials_db.json")
        self.assertTrue(norm(cnv).startswith("/work/_pool"))
        self.assertTrue(norm(kf).startswith("/work/_pool"))
        self.assertFalse(norm(cnv).startswith("/data/微電影素材"))   # 不碰來源

    def test_explicit_work_dir_wins(self):
        def norm(p):
            import re
            return re.sub(r'^[a-zA-Z]:', '', p.replace("\\", "/"))
        cnv, kf = vt._ingest_work_dirs("/data/src", "/data/src/db.json", work_dir="/tmp/wd")
        self.assertEqual(norm(cnv), "/tmp/wd/.converted")
        self.assertEqual(norm(kf), "/tmp/wd/.keyframes")

    def test_default_db_in_source_keeps_derived_in_source(self):
        def norm(p):
            import re
            return re.sub(r'^[a-zA-Z]:', '', p.replace("\\", "/"))
        # 沒給 --out → db 寫在 src → 衍生檔落 src(使用者自己選 src 當輸出,合理)
        cnv, kf = vt._ingest_work_dirs("/data/src", "/data/src/materials_db.json")
        self.assertTrue(norm(cnv).startswith("/data/src"))


class ClassifyAssetTest(unittest.TestCase):
    def test_horizontal_hd_long_video_usable(self):
        r = vt.classify_asset(1920, 1080, duration_sec=55.0)
        self.assertTrue(r["usable"])
        self.assertEqual(r["orientation"], "horizontal")
        self.assertEqual(r["kind"], "long")
        self.assertEqual(r["reasons"], [])

    def test_vertical_clip_filtered(self):
        r = vt.classify_asset(720, 1280, duration_sec=26.0)
        self.assertFalse(r["usable"])
        self.assertEqual(r["orientation"], "vertical")
        self.assertTrue(any("orientation" in x for x in r["reasons"]))
        self.assertTrue(any("res_short" in x for x in r["reasons"]))  # 720 < 1080 too

    def test_low_res_horizontal_filtered(self):
        r = vt.classify_asset(1280, 720, duration_sec=20.0)
        self.assertFalse(r["usable"])
        self.assertEqual(r["res_short"], 720)
        self.assertEqual(r["reasons"], ["res_short=720<1080"])

    def test_too_short_filtered(self):
        r = vt.classify_asset(1920, 1080, duration_sec=2.0)
        self.assertFalse(r["usable"])
        self.assertEqual(r["kind"], "short")
        self.assertTrue(any("too_short" in x for x in r["reasons"]))

    def test_photo_usable_either_orientation(self):
        r = vt.classify_asset(4032, 3024, is_photo=True)
        self.assertTrue(r["usable"])
        self.assertEqual(r["kind"], "photo")

    def test_duration_buckets(self):
        self.assertEqual(vt.classify_asset(1920, 1080, 3.0)["kind"], "short")
        self.assertEqual(vt.classify_asset(1920, 1080, 12.0)["kind"], "clip")
        self.assertEqual(vt.classify_asset(1920, 1080, 60.0)["kind"], "long")
        self.assertEqual(vt.classify_asset(1920, 1080, 200.0)["kind"], "verylong")

    def test_policy_parameterized_vertical_project(self):
        # a vertical-shorts project: same engine, different policy
        r = vt.classify_asset(720, 1280, duration_sec=26.0,
                              target_orientation="vertical", min_short_side=720)
        self.assertTrue(r["usable"])   # now vertical 720 is fine

    def test_square_not_filtered_by_orientation(self):
        r = vt.classify_asset(1080, 1080, duration_sec=10.0)
        self.assertEqual(r["orientation"], "square")
        self.assertNotIn("orientation", " ".join(r["reasons"]))


class ParseResTest(unittest.TestCase):
    def test_parses(self):
        self.assertEqual(vt._parse_res("1920x1080"), (1920, 1080))
        self.assertEqual(vt._parse_res("720X1280"), (720, 1280))

    def test_bad_returns_zero(self):
        self.assertEqual(vt._parse_res(None), (0, 0))
        self.assertEqual(vt._parse_res("?"), (0, 0))


class ClassifyEntryTest(unittest.TestCase):
    def test_video_entry(self):
        e = {"type": "video", "metadata": {"resolution": "1920x1080", "duration_sec": 55.0}}
        c = vt._classify_entry(e)
        self.assertTrue(c["usable"])
        self.assertEqual(c["orientation"], "horizontal")
        self.assertEqual(c["kind"], "long")

    def test_vertical_video_flagged(self):
        e = {"type": "video", "metadata": {"resolution": "720x1280", "duration_sec": 26.0}}
        self.assertFalse(vt._classify_entry(e)["usable"])

    def test_photo_entry(self):
        e = {"type": "photo", "metadata": {"resolution": "4032x3024"}}
        c = vt._classify_entry(e)
        self.assertTrue(c["usable"])
        self.assertEqual(c["kind"], "photo")


class FormatMaterialMapTest(unittest.TestCase):
    def test_groups_by_folder_with_usable_count_and_caption(self):
        files = [
            {"type": "video", "path": "/m/拖拉電纜/a.mov", "tags_from_path": ["拖拉電纜"],
             "classify": {"usable": True, "kind": "long"}, "vlm_caption": "學員拉電纜"},
            {"type": "video", "path": "/m/拖拉電纜/b.mov", "tags_from_path": ["拖拉電纜"],
             "classify": {"usable": False, "kind": "clip", "reasons": ["res_short=720<1080"]},
             "vlm_caption": "模糊畫面"},
            {"type": "photo", "path": "/m/合照/c.jpg", "tags_from_path": ["合照"],
             "classify": {"usable": True, "kind": "photo"}, "vlm_caption": "大合照"},
        ]
        m = vt.format_material_map(files)
        self.assertIn("## 拖拉電纜  （2 檔，1 可用）", m)
        self.assertIn("學員拉電纜", m)
        self.assertIn("⚠️res_short=720<1080", m)      # filtered reason shown
        self.assertIn("## 合照  （1 檔，1 可用）", m)

    def test_empty(self):
        self.assertEqual(vt.format_material_map([]), "")


class MatchScriptToMaterialTest(unittest.TestCase):
    def test_no_hint_and_zero_score_candidates_remain_gap(self):
        segments = [{
            "segment": 7,
            "visual_desc": "活線作業與高空工作",
            "layout": "montage",
        }]
        files = [{
            "path": "unrelated_group_photo.jpg",
            "classify": {"usable": True},
            "vlm_caption": None,
        }]

        result = vt.match_script_to_material(segments, files)

        self.assertEqual(result["assignments"][0]["picks"], [])
        self.assertTrue(result["assignments"][0]["gap"])

    def _db(self):
        return [
            {"path": "/m/拖拉電纜/a.mov", "vlm_caption": "工人在戶外拖拉電纜施工",
             "classify": {"usable": True}},
            {"path": "/m/班級日常生活/b.mov", "vlm_caption": "學員在教室上課聽講",
             "classify": {"usable": True}},
            {"path": "/m/低畫質/c.mov", "vlm_caption": "工人拖拉電纜",
             "classify": {"usable": False}},   # not usable → excluded
        ]

    def test_matches_by_hint_and_caption(self):
        segs = [{"segment": 1, "visual_desc": "學員戶外拖拉電纜施工", "material_hint": "拖拉電纜"}]
        r = vt.match_script_to_material(segs, self._db())
        self.assertFalse(r["assignments"][0]["gap"])
        self.assertEqual(r["assignments"][0]["picks"][0]["path"], "/m/拖拉電纜/a.mov")

    def test_hint_restricts_folder(self):
        segs = [{"segment": 1, "visual_desc": "教室上課", "material_hint": "班級日常生活"}]
        r = vt.match_script_to_material(segs, self._db())
        self.assertEqual(r["assignments"][0]["picks"][0]["path"], "/m/班級日常生活/b.mov")

    def test_gap_when_no_usable_clip_in_hint(self):
        segs = [{"segment": 1, "visual_desc": "結訓大合照", "material_hint": "大合照",
                 "must_include": "大合照"}]
        r = vt.match_script_to_material(segs, self._db())
        self.assertTrue(r["assignments"][0]["gap"])
        self.assertEqual(len(r["gaps"]), 1)
        self.assertTrue(r["gaps"][0]["must_include"])     # critical gap flagged

    def test_unusable_clip_excluded(self):
        # 低畫質 clip has matching caption but classify.usable=False → not picked
        segs = [{"segment": 1, "visual_desc": "拖拉電纜", "material_hint": "低畫質"}]
        r = vt.match_script_to_material(segs, self._db())
        self.assertTrue(r["assignments"][0]["gap"])


class CaptionMatchScoreTest(unittest.TestCase):
    def test_overlap_scores_higher(self):
        hi = vt._caption_match_score("學員拖拉電纜", "工人在戶外拖拉電纜施工")
        lo = vt._caption_match_score("學員拖拉電纜", "教室裡上課聽講")
        self.assertGreater(hi, lo)


if __name__ == "__main__":
    unittest.main()
