import unittest

from video_pipeline_core import material_needs as mn


def _legacy():
    return {
        "project": "67th",
        "based_on_script": "script.json",
        "segments": [
            {"segment": 1, "section": "opening", "needs": [
                {"id": "1.1", "category": "靜態照片", "type": "往期合照",
                 "count": 3, "purpose": "建立傳承感", "fallback_tier": 1,
                 "fallback_options": ["65期合照"], "must_have": True},
                {"id": "1.2", "category": "字幕對應", "type": "標題卡",
                 "count": 1, "purpose": "開場主題", "fallback_tier": 3,
                 "must_have": True},
            ]},
            {"segment": 2, "section": "course", "needs": [
                {"id": "2.1", "category": "動作鏡頭", "type": "攀爬",
                 "count": 2, "purpose": "呈現課程動作", "fallback_tier": 2,
                 "must_have": False},
            ]},
        ],
    }


class NeedIdStabilityTest(unittest.TestCase):
    def test_need_id_is_not_segment_derived_and_is_stable(self):
        a = mn.normalize_material_needs(_legacy())
        b = mn.normalize_material_needs(_legacy())
        ids_a = [n["need_id"] for n in a["needs"]]
        ids_b = [n["need_id"] for n in b["needs"]]
        self.assertEqual(ids_a, ids_b)                 # deterministic
        self.assertTrue(all(i.startswith("nd_") for i in ids_a))
        self.assertNotIn("1.1", ids_a)                 # not the segment-local id
        # legacy id preserved only as a human reference
        self.assertEqual(a["needs"][0]["display_id"], "1.1")
        self.assertEqual(a["needs"][0]["segment_hint"], 1)

    def test_renumbering_segment_does_not_change_need_id(self):
        original = mn.normalize_material_needs(_legacy())["needs"][0]["need_id"]
        moved = _legacy()
        moved["segments"][0]["segment"] = 9            # chapter renumber
        after = mn.normalize_material_needs(moved)["needs"][0]["need_id"]
        self.assertEqual(original, after)

    def test_distinct_needs_get_distinct_ids(self):
        ids = [n["need_id"] for n in mn.normalize_material_needs(_legacy())["needs"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_explicit_need_id_is_preserved(self):
        flat = {"project": "p", "needs": [
            {"need_id": "keepme", "category": "c", "type": "t", "purpose": "x"}]}
        self.assertEqual(
            mn.normalize_material_needs(flat)["needs"][0]["need_id"], "keepme")

    def test_identical_content_disambiguated(self):
        flat = {"project": "p", "needs": [
            {"category": "c", "type": "t", "purpose": "x"},
            {"category": "c", "type": "t", "purpose": "x"},
        ]}
        ids = [n["need_id"] for n in mn.normalize_material_needs(flat)["needs"]]
        self.assertEqual(len(set(ids)), 2)


class ValidatorTest(unittest.TestCase):
    def test_valid_needs_pass(self):
        result = mn.validate_material_needs(_legacy())
        self.assertTrue(result["ok"], result["errors"])

    def test_missing_required_field_is_error(self):
        bad = {"project": "p", "needs": [{"category": "c", "purpose": "x"}]}  # no type
        result = mn.validate_material_needs(bad)
        self.assertFalse(result["ok"])
        self.assertTrue(any("missing type" in e for e in result["errors"]))

    def test_bad_fallback_tier_is_error(self):
        bad = {"project": "p", "needs": [
            {"category": "c", "type": "t", "purpose": "x", "fallback_tier": 9}]}
        self.assertFalse(mn.validate_material_needs(bad)["ok"])

    def test_must_have_tier1_without_fallback_warns(self):
        risky = {"project": "p", "needs": [
            {"category": "動作鏡頭", "type": "唯一實拍", "purpose": "證明事件",
             "fallback_tier": 1, "must_have": True}]}  # tier1 + must_have + no fallback
        result = mn.validate_material_needs(risky)
        self.assertTrue(any("deadlock" in w for w in result["warnings"]))

    def test_empty_needs_warns_not_errors(self):
        result = mn.validate_material_needs({"project": "p", "segments": []})
        self.assertTrue(result["ok"])
        self.assertTrue(any("no needs" in w for w in result["warnings"]))


class SatisfiesEdgeTest(unittest.TestCase):
    def _map(self):
        return {"asset_id": "clipA", "scenes": [
            {"start": 0, "end": 3}, {"start": 3, "end": 6}]}

    def test_apply_verdict_sets_scene_satisfies_with_lineage(self):
        m = self._map()
        mn.apply_satisfaction_verdict(m, {
            "reviewer": "agent", "at": "2026-06-14",
            "scenes": [{"scene_index": 0, "satisfies": [
                {"need_id": "nd_x", "status": "accepted", "note": "傳承合照"}]}]})
        edge = m["scenes"][0]["satisfies"][0]
        self.assertEqual(edge["need_id"], "nd_x")
        self.assertEqual(edge["status"], "accepted")
        self.assertEqual(edge["lineage"]["reviewer"], "agent")
        self.assertEqual(edge["lineage"]["at"], "2026-06-14")
        self.assertNotIn("satisfies", m["scenes"][1])   # untouched scene

    def test_status_transition_records_previous_status(self):
        m = self._map()
        mn.apply_satisfaction_verdict(m, {"scenes": [
            {"scene_index": 0, "satisfies": [{"need_id": "nd_x", "status": "candidate"}]}]})
        mn.apply_satisfaction_verdict(m, {"scenes": [
            {"scene_index": 0, "satisfies": [{"need_id": "nd_x", "status": "accepted"}]}]})
        edge = m["scenes"][0]["satisfies"][0]
        self.assertEqual(edge["status"], "accepted")
        self.assertEqual(edge["lineage"]["previous_status"], "candidate")

    def test_default_status_is_candidate(self):
        m = self._map()
        mn.apply_satisfaction_verdict(m, {"scenes": [
            {"scene_index": 0, "satisfies": [{"need_id": "nd_x"}]}]})
        self.assertEqual(m["scenes"][0]["satisfies"][0]["status"], "candidate")

    def test_invalid_status_rejected(self):
        with self.assertRaises(ValueError):
            mn.make_satisfaction("nd_x", "approved")

    def test_out_of_range_scene_index_ignored(self):
        m = self._map()
        mn.apply_satisfaction_verdict(m, {"scenes": [
            {"scene_index": 9, "satisfies": [{"need_id": "nd_x", "status": "accepted"}]}]})
        self.assertNotIn("satisfies", m["scenes"][0])

    def test_summarize_inverts_edges_without_routing(self):
        m1 = self._map()
        mn.apply_satisfaction_verdict(m1, {"scenes": [
            {"scene_index": 0, "satisfies": [{"need_id": "nd_x", "status": "accepted"}]},
            {"scene_index": 1, "satisfies": [{"need_id": "nd_y", "status": "candidate"}]}]})
        summary = mn.summarize_satisfaction([m1])
        self.assertEqual(summary["nd_x"]["accepted"][0],
                         {"asset_id": "clipA", "scene_index": 0})
        self.assertEqual(summary["nd_y"]["candidate"][0]["scene_index"], 1)
        self.assertNotIn("nd_x", summary["nd_y"]["candidate"][0])  # no cross-talk


class BackwardCompatTest(unittest.TestCase):
    def test_existing_material_map_without_satisfies_is_unaffected(self):
        # no needs, no satisfies — pure existing-material flow stays valid
        m = {"asset_id": "a", "scenes": [{"start": 0, "end": 2}]}
        self.assertEqual(mn.summarize_satisfaction([m]), {})

    def test_flat_canonical_input_roundtrips(self):
        flat = {"project": "p", "needs": [
            {"need_id": "nd_1", "category": "c", "type": "t", "purpose": "x",
             "count": 1, "fallback_tier": 2, "must_have": False}]}
        out = mn.normalize_material_needs(flat)
        self.assertEqual(out["needs"][0]["need_id"], "nd_1")
        self.assertEqual(out["needs"][0]["segment_hint"] if "segment_hint" in out["needs"][0] else None, None)


if __name__ == "__main__":
    unittest.main()
