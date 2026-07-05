import tempfile
import unittest
from pathlib import Path

from PIL import Image

from video_pipeline_core.material_first_real_source_probe import build_material_first_real_source_probe


def _jpg(path: Path, color: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (80, 45), color=color).save(path, "JPEG")


class MaterialFirstRealSourceProbeTest(unittest.TestCase):
    def test_probe_imports_assets_and_passes_strict_asset_path_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "external_source"
            _jpg(source / "opening" / "open.jpg", "red")
            _jpg(source / "training" / "practice.jpg", "green")
            _jpg(source / "closing" / "close.jpg", "blue")
            _jpg(source / "extra" / "unused.jpg", "yellow")
            (source / "extra" / "corrupt.mp4").write_bytes(b"not a playable mp4")

            report = build_material_first_real_source_probe(
                source,
                root / ".tmp" / "material_first_real_source_probe",
                max_assets=4,
            )

            probe = root / ".tmp" / "material_first_real_source_probe"
            run = probe / "run"
            self.assertTrue(report["ok"], report)
            self.assertEqual(report["metrics"]["accepted_count"], 3)
            self.assertEqual(report["metrics"]["copied_count"], 3)
            self.assertGreaterEqual(report["metrics"]["corrupt_or_unreadable_count"], 1)
            self.assertTrue(report["metrics"]["asset_path_audit_strict_ok"])
            self.assertEqual(report["metrics"]["asset_path_audit_strict_finding_count"], 0)
            self.assertTrue((probe / "intake_report.json").exists())
            self.assertTrue((probe / "asset_path_audit_strict.json").exists())
            self.assertTrue((run / "assets" / "materials" / "real_0001.jpg").exists())
            self.assertTrue((run / "assets" / "materials" / "real_0002.jpg").exists())
            self.assertTrue((run / "assets" / "materials" / "real_0003.jpg").exists())
            self.assertFalse((run / "assets" / "materials" / "real_0004.jpg").exists())
            self.assertEqual(report["artifacts"]["asset_store"], "run/assets/materials")
            self.assertNotIn(str(source), str(report))


if __name__ == "__main__":
    unittest.main()
