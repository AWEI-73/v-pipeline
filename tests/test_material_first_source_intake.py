import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from tools.material_first_landing_case import run_material_first_landing_case
from video_pipeline_core.asset_paths import is_absolute_path_string


def _jpg(path: Path, color: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (80, 45), color=color).save(path, "JPEG")


def _write_verdict(path: Path, asset_count: int = 3) -> None:
    roles = ["opening", "training", "closing"]
    assets = []
    for index in range(asset_count):
        role = roles[index % len(roles)]
        assets.append({
            "asset_id": f"real_{index + 1:04d}",
            "coarse_status": "keep",
            "visual_role": [role],
            "quality": "good",
            "usable_ranges": [{"start": 0.0, "end": 4.0}],
            "visual_evidence": [f"{role} evidence"],
        })
    path.write_text(json.dumps({
        "artifact_role": "material_wall_review_verdict",
        "version": 1,
        "reviewer": "test:source-intake",
        "assets": assets,
    }), encoding="utf-8")


class MaterialFirstSourceIntakeTest(unittest.TestCase):
    def test_accepted_assets_are_imported_to_run_asset_store_with_relative_refs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "external_source"
            _jpg(source / "opening" / "opening.jpg", "red")
            _jpg(source / "training" / "training.jpg", "green")
            _jpg(source / "closing" / "closing.jpg", "blue")
            verdict = root / "material_wall_review_verdict.json"
            _write_verdict(verdict)

            result = run_material_first_landing_case(
                root / "run",
                source_dir=source,
                wall_verdict=verdict,
                max_assets=3,
            )

            self.assertTrue(result["ok"], result)
            run = root / "run"
            project_map = json.loads((run / "project_material_map.json").read_text(encoding="utf-8"))
            materials_db = json.loads((run / "materials_db.json").read_text(encoding="utf-8"))
            rough_cut = json.loads((run / "rough_cut_plan.json").read_text(encoding="utf-8"))
            timeline = json.loads((run / "timeline_build.json").read_text(encoding="utf-8"))

            for asset_id in ("real_0001", "real_0002", "real_0003"):
                self.assertTrue((run / "assets" / "materials" / f"{asset_id}.jpg").exists(), asset_id)

            material_refs = {asset["source"] for asset in project_map["assets"]}
            self.assertEqual(material_refs, {
                "assets/materials/real_0001.jpg",
                "assets/materials/real_0002.jpg",
                "assets/materials/real_0003.jpg",
            })
            self.assertTrue(all(not is_absolute_path_string(ref) for ref in material_refs))
            self.assertTrue(all(item["path"].startswith("assets/materials/") for item in materials_db["files"]))
            self.assertTrue(all(clip["source_path"].startswith("assets/materials/") for clip in rough_cut["clips"]))
            self.assertTrue(all(clip["source_path"].startswith("assets/materials/") for clip in timeline["clips"]))
            self.assertTrue(all("original_source" in item for item in materials_db["files"]))
            self.assertTrue(all("source_path_hash" in item["original_source"] for item in materials_db["files"]))

    def test_rejected_and_corrupt_assets_are_not_copied_to_asset_store(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "external_source"
            _jpg(source / "opening" / "opening.jpg", "red")
            _jpg(source / "training" / "training.jpg", "green")
            _jpg(source / "closing" / "closing.jpg", "blue")
            (source / "closing" / "corrupt.mp4").write_bytes(b"not a real mp4")
            verdict = root / "material_wall_review_verdict.json"
            _write_verdict(verdict)

            result = run_material_first_landing_case(
                root / "run",
                source_dir=source,
                wall_verdict=verdict,
                max_assets=4,
            )

            self.assertTrue(result["ok"], result)
            run = root / "run"
            materials_db = json.loads((run / "materials_db.source_candidates.json").read_text(encoding="utf-8"))
            rejected = materials_db.get("rejects") or []
            self.assertTrue(any(item.get("reason") == "invalid_media" for item in rejected))
            self.assertFalse((run / "assets" / "materials" / "real_0004.mp4").exists())
            copied = sorted(path.name for path in (run / "assets" / "materials").glob("*"))
            self.assertEqual(copied, ["real_0001.jpg", "real_0002.jpg", "real_0003.jpg"])

    def test_duplicate_basenames_get_unique_asset_store_refs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "external_source"
            _jpg(source / "opening" / "same.jpg", "red")
            _jpg(source / "training" / "same.jpg", "green")
            _jpg(source / "closing" / "same.jpg", "blue")
            verdict = root / "material_wall_review_verdict.json"
            _write_verdict(verdict)

            result = run_material_first_landing_case(
                root / "run",
                source_dir=source,
                wall_verdict=verdict,
                max_assets=3,
            )

            self.assertTrue(result["ok"], result)
            run = root / "run"
            refs = sorted(
                asset["source"]
                for asset in json.loads((run / "project_material_map.json").read_text(encoding="utf-8"))["assets"]
            )
            self.assertEqual(refs, [
                "assets/materials/real_0001.jpg",
                "assets/materials/real_0002.jpg",
                "assets/materials/real_0003.jpg",
            ])


if __name__ == "__main__":
    unittest.main()
