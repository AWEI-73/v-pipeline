import json
import tempfile
import types
import unittest
from pathlib import Path

from video_pipeline_core import material_needs as mn
from video_pipeline_core import project_material_map as pmm
from video_tools import cmd_project_material_map


def _asset_map(asset_id, scenes, *, asset_type="video", duration=10.0, speech=None):
    return {"artifact_role": "material_map", "version": 1, "asset_id": asset_id,
            "asset_type": asset_type, "source": f"/m/{asset_id}.mp4",
            "duration_sec": duration, "scenes": scenes, "speech": speech or []}


class AggregationTest(unittest.TestCase):
    def test_multiple_maps_aggregate_deterministically(self):
        a = _asset_map("clipB", [{"start": 0, "end": 3, "caption": "x"}])
        b = _asset_map("clipA", [{"start": 0, "end": 2}])
        m1 = pmm.build_project_material_map([a, b])
        m2 = pmm.build_project_material_map([b, a])   # reversed input order
        self.assertEqual(m1, m2)                       # deterministic
        self.assertEqual([x["asset_id"] for x in m1["assets"]], ["clipA", "clipB"])

    def test_metrics_report_counts_and_coverage_truthfully(self):
        a = _asset_map("a", [
            {"start": 0, "end": 3, "caption": "reviewed", "visual_family": "wide_muster"},
            {"start": 3, "end": 6},                     # unreviewed, unlabeled
        ])
        result = pmm.build_project_material_map([a])
        met = result["metrics"]
        self.assertEqual(met["asset_count"], 1)
        self.assertEqual(met["scene_count"], 2)
        self.assertEqual(met["reviewed_scene_ratio"], 0.5)
        self.assertEqual(met["visual_label_coverage"], 0.5)

    def test_scene_evidence_is_preserved_verbatim(self):
        scene = {"start": 0, "end": 3, "caption": "c", "motion_peaks": [1.0],
                 "visual_family": "fam", "angle_scale": "wide"}
        result = pmm.build_project_material_map([_asset_map("a", [scene])])
        self.assertEqual(result["assets"][0]["scenes"][0], scene)


class ReferenceIntegrityTest(unittest.TestCase):
    def _needs(self):
        return mn.migrate_material_needs({"project": "p", "needs": [
            {"need_id": "nd_keep", "category": "c", "type": "t", "purpose": "x"}]})

    def test_unknown_satisfies_reference_fails_when_needs_present(self):
        bad = _asset_map("a", [{"start": 0, "end": 3,
                                "satisfies": [{"need_id": "ghost", "status": "accepted"}]}])
        with self.assertRaises(ValueError):
            pmm.build_project_material_map([bad], needs=self._needs())

    def test_known_satisfies_reference_passes_and_summarizes(self):
        good = _asset_map("a", [{"start": 0, "end": 3,
                                 "satisfies": [{"need_id": "nd_keep", "status": "accepted"}]}])
        result = pmm.build_project_material_map([good], needs=self._needs())
        self.assertEqual(len(result["needs"]), 1)
        self.assertEqual(result["satisfaction_summary"]["nd_keep"]["accepted"][0]["asset_id"], "a")

    def test_invalid_needs_fail_the_build(self):
        invalid = {"project": "p", "needs": [{"category": "c", "type": "t", "purpose": "x"}]}  # no id
        with self.assertRaises(ValueError):
            pmm.build_project_material_map([_asset_map("a", [])], needs=invalid)


class ExistingMaterialFirstTest(unittest.TestCase):
    def test_project_without_needs_is_valid(self):
        result = pmm.build_project_material_map([_asset_map("a", [{"start": 0, "end": 2}])])
        self.assertEqual(result["needs"], [])
        self.assertEqual(result["satisfaction_summary"], {})
        self.assertEqual(result["metrics"]["asset_count"], 1)

    def test_empty_project_metrics_are_zero(self):
        result = pmm.build_project_material_map([])
        self.assertEqual(result["metrics"],
                         {"asset_count": 0, "scene_count": 0,
                          "reviewed_scene_ratio": 0, "visual_label_coverage": 0})


class CliTest(unittest.TestCase):
    def test_cli_writes_project_material_map(self):
        d = Path(tempfile.mkdtemp())
        maps_dir = d / "maps"
        maps_dir.mkdir()
        (maps_dir / "a.map.json").write_text(
            json.dumps(_asset_map("a", [{"start": 0, "end": 3, "caption": "c"}])),
            encoding="utf-8")
        out = d / "project_material_map.json"
        args = types.SimpleNamespace(maps_dir=str(maps_dir), needs=None, out=str(out))
        cmd_project_material_map(args)
        written = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(written["artifact_role"], "project_material_map")
        self.assertEqual(written["metrics"]["asset_count"], 1)


if __name__ == "__main__":
    unittest.main()
