import json
import tempfile
import types
import unittest
from pathlib import Path

from video_pipeline_core import material_needs as mn
from video_pipeline_core.vt_core import ToolError
from video_tools import cmd_validate_needs


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


class MigrationTest(unittest.TestCase):
    def test_migration_allocates_non_segment_ids(self):
        canon = mn.migrate_material_needs(_legacy())
        ids = [n["need_id"] for n in canon["needs"]]
        self.assertTrue(all(i.startswith("nd_") for i in ids))
        self.assertNotIn("1.1", ids)                       # not segment-local id
        self.assertEqual(canon["needs"][0]["display_id"], "1.1")
        self.assertEqual(canon["needs"][0]["segment_hint"], 1)

    def test_renumbering_segment_does_not_change_id(self):
        before = mn.migrate_material_needs(_legacy())["needs"][0]["need_id"]
        moved = _legacy()
        moved["segments"][0]["segment"] = 9
        after = mn.migrate_material_needs(moved)["needs"][0]["need_id"]
        self.assertEqual(before, after)

    def test_existing_need_id_is_preserved(self):
        flat = {"project": "p", "needs": [
            {"need_id": "keepme", "category": "c", "type": "t", "purpose": "x"}]}
        self.assertEqual(
            mn.migrate_material_needs(flat)["needs"][0]["need_id"], "keepme")

    def test_migration_is_idempotent(self):
        once = mn.migrate_material_needs(_legacy())
        twice = mn.migrate_material_needs(once)
        self.assertEqual([n["need_id"] for n in once["needs"]],
                         [n["need_id"] for n in twice["needs"]])

    def test_content_identical_fresh_needs_disambiguated_with_note(self):
        flat = {"project": "p", "needs": [
            {"category": "c", "type": "t", "purpose": "x"},
            {"category": "c", "type": "t", "purpose": "x"},
        ]}
        canon = mn.migrate_material_needs(flat)
        ids = [n["need_id"] for n in canon["needs"]]
        self.assertEqual(len(set(ids)), 2)
        self.assertIn("migration_notes", canon)


class IdentityStabilityTest(unittest.TestCase):
    def test_editing_purpose_type_category_does_not_change_id(self):
        """F1: once a need has an id, content edits must not regenerate it."""
        canon = mn.migrate_material_needs(_legacy())
        nid = canon["needs"][0]["need_id"]
        canon["needs"][0]["purpose"] = "完全改寫的用途"
        canon["needs"][0]["type"] = "新型別"
        canon["needs"][0]["category"] = "新類別"
        re = mn.migrate_material_needs(canon)        # M6c-style revision pass
        self.assertEqual(re["needs"][0]["need_id"], nid)


class ValidatorTest(unittest.TestCase):
    def test_migrated_needs_validate_ok(self):
        result = mn.validate_material_needs(mn.migrate_material_needs(_legacy()))
        self.assertTrue(result["ok"], result["errors"])

    def test_canonical_need_without_id_is_error(self):
        """Validation never allocates: a missing need_id must surface."""
        result = mn.validate_material_needs(
            {"project": "p", "needs": [{"category": "c", "type": "t", "purpose": "x"}]})
        self.assertFalse(result["ok"])
        self.assertTrue(any("missing need_id" in e for e in result["errors"]))

    def test_duplicate_explicit_id_fails(self):
        """F2: explicit duplicate join key is an error, not a silent suffix."""
        dup = {"project": "p", "needs": [
            {"need_id": "same", "category": "c", "type": "t", "purpose": "x"},
            {"need_id": "same", "category": "c", "type": "t", "purpose": "y"},
        ]}
        result = mn.validate_material_needs(dup)
        self.assertFalse(result["ok"])
        self.assertTrue(any("duplicate need_id same" in e for e in result["errors"]))

    def test_must_have_string_false_fails(self):
        """F4: 'false' string must not be coerced to True."""
        bad = {"project": "p", "needs": [
            {"need_id": "n1", "category": "c", "type": "t", "purpose": "x",
             "must_have": "false"}]}
        result = mn.validate_material_needs(bad)
        self.assertFalse(result["ok"])
        self.assertTrue(any("must_have must be boolean" in e for e in result["errors"]))

    def test_invalid_count_fails(self):
        """F4: invalid count is an error, not a silent 'treated as 1'."""
        for bad_count in (0, -2, "3", 2.5, True):
            bad = {"project": "p", "needs": [
                {"need_id": "n1", "category": "c", "type": "t", "purpose": "x",
                 "count": bad_count}]}
            result = mn.validate_material_needs(bad)
            self.assertFalse(result["ok"], f"count={bad_count!r} should fail")
            self.assertTrue(any("positive integer" in e for e in result["errors"]))

    def test_missing_required_field_is_error(self):
        bad = {"project": "p", "needs": [{"need_id": "n1", "category": "c", "purpose": "x"}]}
        result = mn.validate_material_needs(bad)
        self.assertFalse(result["ok"])
        self.assertTrue(any("missing type" in e for e in result["errors"]))

    def test_bad_fallback_tier_is_error(self):
        for bad_tier in (9, 0, "1", True, 1.0):
            bad = {"project": "p", "needs": [
                {"need_id": "n1", "category": "c", "type": "t", "purpose": "x",
                 "fallback_tier": bad_tier}]}
            result = mn.validate_material_needs(bad)
            self.assertFalse(result["ok"], f"fallback_tier={bad_tier!r} should fail")
            self.assertTrue(any("fallback_tier must be an integer" in e
                                for e in result["errors"]))

    def test_must_have_tier1_without_fallback_warns(self):
        risky = {"project": "p", "needs": [
            {"need_id": "n1", "category": "動作鏡頭", "type": "唯一實拍",
             "purpose": "證明事件", "fallback_tier": 1, "must_have": True}]}
        result = mn.validate_material_needs(risky)
        self.assertTrue(result["ok"])      # warning, not error
        self.assertTrue(any("deadlock" in w for w in result["warnings"]))


class SatisfiesEdgeTest(unittest.TestCase):
    def _map(self):
        return {"asset_id": "clipA", "scenes": [
            {"start": 0, "end": 3}, {"start": 3, "end": 6}]}

    def test_apply_verdict_sets_scene_satisfies_with_lineage(self):
        m = self._map()
        mn.apply_satisfaction_verdict(m, {
            "reviewer": "agent", "at": "2026-06-14",
            "scenes": [{"scene_index": 0, "satisfies": [
                {"need_id": "nd_x", "status": "accepted", "note": "傳承合照"}]}]},
            valid_need_ids={"nd_x"})
        edge = m["scenes"][0]["satisfies"][0]
        self.assertEqual(edge["status"], "accepted")
        self.assertEqual(edge["lineage"]["reviewer"], "agent")
        self.assertEqual(edge["lineage"]["at"], "2026-06-14")
        self.assertNotIn("satisfies", m["scenes"][1])

    def test_unknown_need_reference_fails(self):
        """F3: a typo'd need_id must not form a phantom edge."""
        m = self._map()
        with self.assertRaises(ValueError):
            mn.apply_satisfaction_verdict(m, {"scenes": [
                {"scene_index": 0, "satisfies": [{"need_id": "typo"}]}]},
                valid_need_ids={"nd_x"})

    def test_status_transition_records_previous_status(self):
        m = self._map()
        mn.apply_satisfaction_verdict(m, {"scenes": [
            {"scene_index": 0, "satisfies": [{"need_id": "nd_x", "status": "candidate"}]}]},
            valid_need_ids={"nd_x"})
        mn.apply_satisfaction_verdict(m, {"scenes": [
            {"scene_index": 0, "satisfies": [{"need_id": "nd_x", "status": "accepted"}]}]},
            valid_need_ids={"nd_x"})
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

    def test_need_ids_helper_feeds_reference_check(self):
        canon = mn.migrate_material_needs(_legacy())
        ids = mn.need_ids(canon)
        good = next(iter(ids))
        m = self._map()
        mn.apply_satisfaction_verdict(m, {"scenes": [
            {"scene_index": 0, "satisfies": [{"need_id": good, "status": "accepted"}]}]},
            valid_need_ids=ids)
        self.assertEqual(m["scenes"][0]["satisfies"][0]["need_id"], good)

    def test_summarize_inverts_edges_without_routing(self):
        m1 = self._map()
        mn.apply_satisfaction_verdict(m1, {"scenes": [
            {"scene_index": 0, "satisfies": [{"need_id": "nd_x", "status": "accepted"}]},
            {"scene_index": 1, "satisfies": [{"need_id": "nd_y", "status": "candidate"}]}]},
            valid_need_ids={"nd_x", "nd_y"})
        summary = mn.summarize_satisfaction([m1])
        self.assertEqual(summary["nd_x"]["accepted"][0],
                         {"asset_id": "clipA", "scene_index": 0})
        self.assertEqual(summary["nd_y"]["candidate"][0]["scene_index"], 1)


class CliTest(unittest.TestCase):
    def _write(self, obj):
        tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        json.dump(obj, tmp)
        tmp.close()
        return tmp.name

    def test_invalid_input_raises_for_nonzero_exit(self):
        # missing need_id (strict, no --migrate) must fail the CLI
        path = self._write({"project": "p", "needs": [
            {"category": "c", "type": "t", "purpose": "x"}]})
        args = types.SimpleNamespace(needs=path, migrate=False, out=None)
        with self.assertRaises(ToolError):
            cmd_validate_needs(args)

    def test_out_not_written_on_failure(self):
        path = self._write({"project": "p", "needs": [
            {"need_id": "n1", "category": "c", "type": "t", "purpose": "x",
             "must_have": "false"}]})  # invalid type -> validation fails
        out = Path(tempfile.gettempdir()) / "should_not_exist_needs.json"
        if out.exists():
            out.unlink()
        args = types.SimpleNamespace(needs=path, migrate=False, out=str(out))
        with self.assertRaises(ToolError):
            cmd_validate_needs(args)
        self.assertFalse(out.exists())

    def test_migrate_valid_input_writes_canonical(self):
        path = self._write({"project": "p", "segments": [{"segment": 1, "needs": [
            {"id": "1.1", "category": "c", "type": "t", "purpose": "x",
             "count": 2, "fallback_tier": 2, "must_have": False}]}]})
        out = Path(tempfile.mkdtemp()) / "canon.json"
        args = types.SimpleNamespace(needs=path, migrate=True, out=str(out))
        cmd_validate_needs(args)  # must not raise
        written = json.loads(out.read_text(encoding="utf-8"))
        self.assertTrue(written["needs"][0]["need_id"].startswith("nd_"))


class BackwardCompatTest(unittest.TestCase):
    def test_existing_material_map_without_satisfies_is_unaffected(self):
        m = {"asset_id": "a", "scenes": [{"start": 0, "end": 2}]}
        self.assertEqual(mn.summarize_satisfaction([m]), {})

    def test_permissive_apply_without_valid_ids_still_works(self):
        m = {"asset_id": "a", "scenes": [{"start": 0, "end": 2}]}
        mn.apply_satisfaction_verdict(m, {"scenes": [
            {"scene_index": 0, "satisfies": [{"need_id": "nd_x"}]}]})
        self.assertEqual(m["scenes"][0]["satisfies"][0]["need_id"], "nd_x")


if __name__ == "__main__":
    unittest.main()
