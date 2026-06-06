"""SPEC 合約層 validator(canonical JSON)。對應 skills/spec-contract.md。
Node 0-1 brief gate;Node 3 segment_contract 後續加入。"""
import json
import unittest
from pathlib import Path

from video_pipeline_core import spec_contract as sc

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


class ValidateBriefTest(unittest.TestCase):
    def test_example_brief_is_valid(self):
        brief = json.loads((EXAMPLES / "brief_graduation_mv.json").read_text(encoding="utf-8"))
        r = sc.validate_brief(brief)
        self.assertTrue(r["ok"], r["errors"])
        self.assertEqual(r["errors"], [])

    def test_missing_required_fields_fail(self):
        r = sc.validate_brief({"video_type": "graduation_mv"})
        self.assertFalse(r["ok"])
        self.assertTrue(any("spec_start_mode" in e for e in r["errors"]))
        self.assertTrue(any("can_reshoot" in e for e in r["errors"]))

    def test_illegal_enum_fails(self):
        r = sc.validate_brief({"video_type": "graduation_mv", "spec_start_mode": "vibes",
                               "can_reshoot": True, "fallback_policy": "reshoot_first"})
        self.assertFalse(r["ok"])
        self.assertTrue(any("spec_start_mode" in e for e in r["errors"]))

    def test_can_reshoot_must_be_bool(self):
        r = sc.validate_brief({"video_type": "graduation_mv", "spec_start_mode": "script_first",
                               "can_reshoot": "yes", "fallback_policy": "reshoot_first"})
        self.assertFalse(r["ok"])

    def test_quality_fields_warn_not_block(self):
        r = sc.validate_brief({"video_type": "graduation_mv", "spec_start_mode": "script_first",
                               "can_reshoot": True, "fallback_policy": "reshoot_first"})
        self.assertTrue(r["ok"])              # 必填齊 → ok
        self.assertTrue(r["warnings"])        # 但缺 must_include/tone… → 軟提醒

    def test_non_dict(self):
        self.assertFalse(sc.validate_brief("nope")["ok"])


class ValidateSegmentContractTest(unittest.TestCase):
    def test_example_contract_is_valid(self):
        c = json.loads((EXAMPLES / "segment_contract_graduation_mv.json").read_text(encoding="utf-8"))
        r = sc.validate_segment_contract(c)
        self.assertTrue(r["ok"], r["errors"])

    def _seg(self, **over):
        base = {"core": {"section_role": "montage", "story_purpose": "x", "timeline_source": "beat"},
                "material_fit": {"visual_desc": "v", "reason": "r"},
                "audio": {"role": "music", "reason": "r"},
                "visual_style": {"layout": "montage", "pace": "fast", "reason": "r"},
                "text_layer": "none"}
        base.update(over)
        return base

    def test_missing_core_story_purpose_fails(self):
        seg = self._seg(core={"section_role": "montage", "timeline_source": "beat"})
        r = sc.validate_segment_contract([seg])
        self.assertFalse(r["ok"])
        self.assertTrue(any("story_purpose" in e for e in r["errors"]))

    def test_illegal_timeline_source(self):
        seg = self._seg(core={"section_role": "x", "story_purpose": "y", "timeline_source": "vibes"})
        self.assertFalse(sc.validate_segment_contract([seg])["ok"])

    def test_audio_role_and_reason_required(self):
        self.assertFalse(sc.validate_segment_contract([self._seg(audio={"role": "music"})])["ok"])
        self.assertFalse(sc.validate_segment_contract([self._seg(audio={"role": "boom", "reason": "r"})])["ok"])

    def test_text_present_needs_reason(self):
        seg = self._seg(text_layer={"label": "礙子拆線"})   # 有字無 reason
        self.assertFalse(sc.validate_segment_contract([seg])["ok"])
        seg2 = self._seg(text_layer={"label": "礙子拆線", "reason": "標註紀實"})
        self.assertTrue(sc.validate_segment_contract([seg2])["ok"])

    def test_review_required_warns_for_opening(self):
        seg = self._seg(core={"section_role": "opening", "story_purpose": "x", "timeline_source": "fixed"})
        r = sc.validate_segment_contract([seg])
        self.assertTrue(r["ok"])   # warning 不擋
        self.assertTrue(any("review_required" in w for w in r["warnings"]))

    def test_empty_contract_fails(self):
        self.assertFalse(sc.validate_segment_contract({"segments": []})["ok"])

    def test_stock_first_without_search_query_warns(self):
        seg = self._seg(material_fit={"category": "x", "visual_desc": "城市", "reason": "r"})
        c = {"material_source_mode": "stock_first", "story_truth_level": "conceptual", "segments": [seg]}
        r = sc.validate_segment_contract(c)
        self.assertTrue(r["ok"])
        self.assertTrue(any("search_query" in w for w in r["warnings"]))
        # 有 search_query → 不再警告
        seg2 = self._seg(material_fit={"category": "x", "visual_desc": "城市",
                                       "search_query": "city street", "reason": "r"})
        r2 = sc.validate_segment_contract({"material_source_mode": "stock_first", "segments": [seg2]})
        self.assertFalse(any("search_query" in w for w in r2["warnings"]))

    def test_material_categories_vocab_loads(self):
        cats = sc.load_material_categories(EXAMPLES / "material_categories.json")
        self.assertIn("hands_on_training", cats)
        self.assertIn("speech", cats)
        self.assertIn("collection_instructions", cats["speech"])

    def test_example_contract_categories_valid_against_vocab(self):
        cats = sc.load_material_categories(EXAMPLES / "material_categories.json")
        c = json.loads((EXAMPLES / "segment_contract_graduation_mv.json").read_text(encoding="utf-8"))
        r = sc.validate_segment_contract(c, categories=set(cats))
        self.assertTrue(r["ok"], r["errors"])

    def test_illegal_category_fails_when_vocab_given(self):
        seg = self._seg(material_fit={"category": "nonsense", "visual_desc": "x", "reason": "r"})
        r = sc.validate_segment_contract([seg], categories={"hands_on_training", "speech"})
        self.assertFalse(r["ok"])
        self.assertTrue(any("category" in e for e in r["errors"]))

    def test_must_include_without_collection_instructions_warns(self):
        seg = self._seg(material_fit={"category": "speech", "visual_desc": "致詞",
                                      "must_include": "主任", "reason": "r"})
        r = sc.validate_segment_contract([seg])
        self.assertTrue(r["ok"])
        self.assertTrue(any("collection_instructions" in w for w in r["warnings"]))

    def test_editing_grammar_enums(self):
        seg = self._seg(editing_grammar={"role": "hero", "beat_alignment": "music",
                                         "compressibility": "locked", "reason": "高潮不可縮"})
        self.assertTrue(sc.validate_segment_contract([seg])["ok"])
        bad = self._seg(editing_grammar={"role": "superstar", "reason": "x"})
        self.assertFalse(sc.validate_segment_contract([bad])["ok"])


class BuildLayerVocabTest(unittest.TestCase):
    """鎖住 Node 9-14 canonical 詞彙(skill 契約與未來程式須一致)。"""

    def test_execution_route_status(self):
        self.assertIn("ready", sc.EXECUTION_ROUTE_STATUS)
        self.assertIn("needs_reshoot", sc.EXECUTION_ROUTE_STATUS)
        self.assertIn("blocked", sc.EXECUTION_ROUTE_STATUS)

    def test_verify_status(self):
        self.assertEqual(set(sc.VERIFY_STATUS), {"pass", "warn", "fail", "blocked"})

    def test_editor_decisions(self):
        for d in ("approve", "auto_fix", "route_change", "human_review", "block", "rerender"):
            self.assertIn(d, sc.EDITOR_DECISIONS)

    def test_render_modes(self):
        self.assertEqual(set(sc.RENDER_MODES), {"preview", "review", "final", "segment_debug"})

    def test_timeline_tracks(self):
        self.assertIn("audio_original", sc.TIMELINE_TRACKS)
        self.assertIn("text_overlay", sc.TIMELINE_TRACKS)


class FallbackRouteTest(unittest.TestCase):
    def test_not_collected_yet_is_collect_not_failure(self):
        r = sc.suggest_fallback_route("missing", material_collected=False)
        self.assertEqual(r["selected_route"], "collect_material")
        self.assertFalse(r["review_required"])

    def test_covered_is_none(self):
        self.assertEqual(sc.suggest_fallback_route("covered")["selected_route"], "none")

    def test_identity_sensitive_never_silent_stock(self):
        r = sc.suggest_fallback_route("missing", identity_sensitive=True, can_reshoot=True)
        self.assertEqual(r["selected_route"], "reshoot")
        self.assertIn("stock_bridge", r["rejected_routes"])
        self.assertIn("generated", r["rejected_routes"])
        self.assertTrue(r["review_required"])

    def test_identity_sensitive_no_reshoot_goes_review(self):
        r = sc.suggest_fallback_route("missing", identity_sensitive=True, can_reshoot=False)
        self.assertEqual(r["selected_route"], "dashboard_review")
        self.assertIn("stock_bridge", r["rejected_routes"])

    def test_must_include_never_silent_stock(self):
        # must_include 缺口即使非 identity/proof 也不可 stock_bridge(隊呼/大合照=真實的)
        r = sc.suggest_fallback_route("missing", must_include=True, section_role="montage",
                                      can_reshoot=True)
        self.assertEqual(r["selected_route"], "reshoot")
        self.assertIn("stock_bridge", r["rejected_routes"])
        self.assertTrue(r["review_required"])

    def test_proof_critical_routes_reshoot(self):
        r = sc.suggest_fallback_route("weak", proof_critical=True)
        self.assertEqual(r["selected_route"], "reshoot")
        self.assertTrue(r["review_required"])

    def test_opening_weak_routes_review_unless_allowed(self):
        r = sc.suggest_fallback_route("weak", section_role="opening")
        self.assertEqual(r["selected_route"], "dashboard_review")
        r2 = sc.suggest_fallback_route("weak", section_role="opening",
                                       explicitly_allowed=["stock_bridge"])
        self.assertNotEqual(r2["selected_route"], "dashboard_review")

    def test_mood_bridge_allows_stock(self):
        r = sc.suggest_fallback_route("missing", section_role="montage")
        self.assertEqual(r["selected_route"], "stock_bridge")
        self.assertFalse(r["review_required"])

    def test_filler_prefers_drop(self):
        r = sc.suggest_fallback_route("missing", section_role="filler")
        self.assertEqual(r["selected_route"], "drop_segment")


if __name__ == "__main__":
    unittest.main()
