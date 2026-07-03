import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from video_pipeline_core import asset_store


class AssetStoreTest(unittest.TestCase):
    def test_ingest_assets_hardlinks_and_updates_project_material_map(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = root / "run"
            source_dir = root / "incoming"
            run.mkdir()
            source_dir.mkdir()
            source = source_dir / "clip.mp4"
            source.write_bytes(b"clip")

            result = asset_store.ingest_assets(run, source_dir)
            dest = run / "assets" / "clip.mp4"
            project_map = json.loads((run / "project_material_map.json").read_text(encoding="utf-8"))

            self.assertTrue(result["ok"])
            self.assertEqual(result["ingested"][0]["method"], "hardlink")
            self.assertTrue(dest.exists())
            self.assertEqual(os.stat(source).st_ino, os.stat(dest).st_ino)
            self.assertEqual(project_map["assets"][0]["source"], "assets/clip.mp4")
            self.assertEqual(project_map["assets"][0]["path"], "assets/clip.mp4")

    def test_ingest_assets_copies_when_hardlink_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = root / "run"
            source_dir = root / "incoming"
            run.mkdir()
            source_dir.mkdir()
            (source_dir / "photo.jpg").write_bytes(b"photo")

            with patch("video_pipeline_core.asset_store.os.link", side_effect=OSError("cross-device")):
                result = asset_store.ingest_assets(run, source_dir)

            self.assertEqual(result["ingested"][0]["method"], "copy")
            self.assertEqual((run / "assets" / "photo.jpg").read_bytes(), b"photo")

    def test_gc_assets_reports_and_deletes_orphans(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            assets = run / "assets"
            assets.mkdir()
            (assets / "keep.mp4").write_bytes(b"keep")
            (assets / "orphan.mp4").write_bytes(b"orphan")
            (run / "project_material_map.json").write_text(
                json.dumps({
                    "artifact_role": "project_material_map",
                    "assets": [{"source": "assets/keep.mp4"}],
                }),
                encoding="utf-8",
            )

            report = asset_store.gc_assets(run)
            deleted = asset_store.gc_assets(run, delete=True)

            self.assertEqual(report["orphan_count"], 1)
            self.assertEqual(report["orphans"][0]["path"], "assets/orphan.mp4")
            self.assertFalse(report["orphans"][0]["deleted"])
            self.assertEqual(deleted["orphan_count"], 1)
            self.assertTrue(deleted["orphans"][0]["deleted"])
            self.assertTrue((assets / "keep.mp4").exists())
            self.assertFalse((assets / "orphan.mp4").exists())


if __name__ == "__main__":
    unittest.main()
