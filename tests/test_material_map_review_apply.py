import json
import tempfile
import types
import unittest
from pathlib import Path

from video_tools import cmd_material_map_review_apply


def _asset_map(asset_id, scenes):
    return {
        "artifact_role": "material_map",
        "version": 1,
        "asset_id": asset_id,
        "asset_type": "video",
        "source": f"/media/{asset_id}.mp4",
        "duration_sec": 12.0,
        "scenes": scenes,
    }


def _needs():
    return {
        "artifact_role": "material_needs",
        "version": 1,
        "project": "review-apply",
        "needs": [
            {
                "need_id": "nd_opening",
                "category": "scene",
                "type": "opening",
                "purpose": "establish the cohort",
                "count": 1,
                "fallback_tier": 1,
                "must_have": False,
            }
        ],
    }


class MaterialMapReviewApplyCliTest(unittest.TestCase):
    def test_cli_applies_review_edges_to_asset_maps_and_project_map(self):
        root = Path(tempfile.mkdtemp())
        maps_dir = root / "maps"
        maps_dir.mkdir()
        (maps_dir / "clip-a.map.json").write_text(
            json.dumps(_asset_map("clip-a", [{"start": 0, "end": 4, "caption": "class opening"}])),
            encoding="utf-8",
        )
        needs_path = root / "material_needs.json"
        needs_path.write_text(json.dumps(_needs()), encoding="utf-8")
        verdict_path = root / "material_map_review_verdict.json"
        verdict_path.write_text(
            json.dumps({
                "artifact_role": "material_map_review_verdict",
                "version": 1,
                "reviewer": "agent:director",
                "at": "2026-06-22T12:00:00+08:00",
                "decisions": [
                    {
                        "asset_id": "clip-a",
                        "scene_index": 0,
                        "need_id": "nd_opening",
                        "status": "accepted",
                        "visual_evidence": [
                            "trainees are visible entering the training center",
                            "the shot clearly establishes the cohort and location"
                        ],
                        "note": "clear cohort establishing shot",
                    }
                ],
            }),
            encoding="utf-8",
        )
        out = root / "project_material_map.json"

        cmd_material_map_review_apply(types.SimpleNamespace(
            maps_dir=str(maps_dir),
            needs=str(needs_path),
            verdict=str(verdict_path),
            out=str(out),
        ))

        updated_asset = json.loads((maps_dir / "clip-a.map.json").read_text(encoding="utf-8"))
        edge = updated_asset["scenes"][0]["satisfies"][0]
        self.assertEqual(edge["need_id"], "nd_opening")
        self.assertEqual(edge["status"], "accepted")
        self.assertEqual(edge["lineage"]["reviewer"], "agent:director")
        self.assertEqual(edge["lineage"]["visual_evidence"][0],
                         "trainees are visible entering the training center")

        project_map = json.loads(out.read_text(encoding="utf-8"))
        accepted = project_map["satisfaction_summary"]["nd_opening"]["accepted"][0]
        self.assertEqual(accepted["asset_id"], "clip-a")
        self.assertEqual(accepted["scene_index"], 0)

    def test_cli_rejects_unknown_asset_id_in_verdict(self):
        root = Path(tempfile.mkdtemp())
        maps_dir = root / "maps"
        maps_dir.mkdir()
        (maps_dir / "clip-a.map.json").write_text(
            json.dumps(_asset_map("clip-a", [{"start": 0, "end": 4}])),
            encoding="utf-8",
        )
        needs_path = root / "material_needs.json"
        needs_path.write_text(json.dumps(_needs()), encoding="utf-8")
        verdict_path = root / "material_map_review_verdict.json"
        verdict_path.write_text(
            json.dumps({
                "reviewer": "agent:director",
                "decisions": [
                    {
                        "asset_id": "missing",
                        "scene_index": 0,
                        "need_id": "nd_opening",
                        "status": "accepted",
                    }
                ],
            }),
            encoding="utf-8",
        )

        with self.assertRaises(ValueError):
            cmd_material_map_review_apply(types.SimpleNamespace(
                maps_dir=str(maps_dir),
                needs=str(needs_path),
                verdict=str(verdict_path),
                out=str(root / "project_material_map.json"),
                material_db=None,
                skipped_policy=None,
            ))

    def test_cli_can_ignore_decisions_for_timeout_skipped_assets_with_report(self):
        root = Path(tempfile.mkdtemp())
        maps_dir = root / "maps"
        maps_dir.mkdir()
        (maps_dir / "clip-a.map.json").write_text(
            json.dumps(_asset_map("clip-a", [{"start": 0, "end": 4, "caption": "class opening"}])),
            encoding="utf-8",
        )
        needs_path = root / "material_needs.json"
        needs_path.write_text(json.dumps(_needs()), encoding="utf-8")
        material_db_path = root / "materials_db.mapped.json"
        material_db_path.write_text(json.dumps({
            "files": [
                {"id": "clip-a", "material_map_status": "mapped"},
                {
                    "id": "clip-skipped",
                    "material_map_status": "skipped",
                    "material_map_error": {"reason": "timeout"},
                },
            ],
        }), encoding="utf-8")
        verdict_path = root / "material_map_review_verdict.json"
        verdict_path.write_text(
            json.dumps({
                "reviewer": "agent:director",
                "decisions": [
                    {
                        "asset_id": "clip-skipped",
                        "scene_index": 0,
                        "need_id": "nd_opening",
                        "status": "accepted",
                        "visual_evidence": ["visible but timed out before map"],
                    },
                    {
                        "asset_id": "clip-a",
                        "scene_index": 0,
                        "need_id": "nd_opening",
                        "status": "accepted",
                        "visual_evidence": ["mapped opening shot"],
                    },
                ],
            }),
            encoding="utf-8",
        )
        out = root / "project_material_map.json"

        result = cmd_material_map_review_apply(types.SimpleNamespace(
            maps_dir=str(maps_dir),
            needs=str(needs_path),
            verdict=str(verdict_path),
            out=str(out),
            material_db=str(material_db_path),
            skipped_policy="ignore-with-report",
        ))

        self.assertEqual(result["ignored_decisions"], 1)
        self.assertEqual(result["ignored"][0]["asset_id"], "clip-skipped")
        self.assertEqual(result["ignored"][0]["reason"], "skipped_asset")
        project_map = json.loads(out.read_text(encoding="utf-8"))
        accepted = project_map["satisfaction_summary"]["nd_opening"]["accepted"]
        self.assertEqual(len(accepted), 1)
        self.assertEqual(accepted[0]["asset_id"], "clip-a")

    def test_cli_rejects_accepted_decision_without_visual_evidence(self):
        root = Path(tempfile.mkdtemp())
        maps_dir = root / "maps"
        maps_dir.mkdir()
        (maps_dir / "clip-a.map.json").write_text(
            json.dumps(_asset_map("clip-a", [{"start": 0, "end": 4}])),
            encoding="utf-8",
        )
        needs_path = root / "material_needs.json"
        needs_path.write_text(json.dumps(_needs()), encoding="utf-8")
        verdict_path = root / "material_map_review_verdict.json"
        verdict_path.write_text(
            json.dumps({
                "reviewer": "agent:director",
                "decisions": [
                    {
                        "asset_id": "clip-a",
                        "scene_index": 0,
                        "need_id": "nd_opening",
                        "status": "accepted",
                        "note": "folder name says opening",
                    }
                ],
            }),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ValueError, "visual_evidence"):
            cmd_material_map_review_apply(types.SimpleNamespace(
                maps_dir=str(maps_dir),
                needs=str(needs_path),
                verdict=str(verdict_path),
                out=str(root / "project_material_map.json"),
                material_db=None,
                skipped_policy=None,
            ))

    def test_cli_persists_reviewed_usable_range_on_satisfaction_edge(self):
        root = Path(tempfile.mkdtemp())
        maps_dir = root / "maps"
        maps_dir.mkdir()
        (maps_dir / "clip-a.map.json").write_text(
            json.dumps(_asset_map("clip-a", [{"start": 0, "end": 50, "caption": "practice"}])),
            encoding="utf-8",
        )
        needs_path = root / "material_needs.json"
        needs_path.write_text(json.dumps(_needs()), encoding="utf-8")
        verdict_path = root / "material_map_review_verdict.json"
        verdict_path.write_text(
            json.dumps({
                "reviewer": "agent:director",
                "decisions": [
                    {
                        "asset_id": "clip-a",
                        "scene_index": 0,
                        "need_id": "nd_opening",
                        "status": "accepted",
                        "visual_evidence": ["usable action starts after the setup"],
                        "usable_range": {"start": 12.0, "end": 42.0},
                    }
                ],
            }),
            encoding="utf-8",
        )

        cmd_material_map_review_apply(types.SimpleNamespace(
            maps_dir=str(maps_dir),
            needs=str(needs_path),
            verdict=str(verdict_path),
            out=str(root / "project_material_map.json"),
            material_db=None,
            skipped_policy=None,
        ))

        updated_asset = json.loads((maps_dir / "clip-a.map.json").read_text(encoding="utf-8"))
        edge = updated_asset["scenes"][0]["satisfies"][0]
        self.assertEqual(edge["usable_range"], {"start": 12.0, "end": 42.0})


if __name__ == "__main__":
    unittest.main()
