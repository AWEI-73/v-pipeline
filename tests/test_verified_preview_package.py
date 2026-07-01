import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core.verified_preview_package import package_verified_preview


def _write(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


class VerifiedPreviewPackageTest(unittest.TestCase):
    def test_packages_verified_preview_without_creating_final_mp4(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            preview = root / "single_source_highlight_preview.mp4"
            preview.write_bytes(b"preview")
            _write(root / "delivery_gate.json", {
                "artifact_role": "delivery_gate",
                "pass": True,
                "blocking": [],
            })
            _write(root / "final_product_verify" / "final_product_verify_bundle.json", {
                "artifact_role": "final_product_verify_bundle",
                "pass": True,
                "video": str(preview),
            })
            _write(root / "highlight_cut_report.json", {
                "artifact_role": "highlight_cut_report",
                "out": str(preview),
            })

            package = package_verified_preview(root)

            self.assertEqual(package["artifact_role"], "verified_preview_package")
            self.assertEqual(package["status"], "ready_for_operator_delivery_review")
            self.assertEqual(package["source_video"], "single_source_highlight_preview.mp4")
            self.assertEqual(package["packaged_video"], "delivery_candidate.mp4")
            self.assertFalse(package["promotes_to_final_mp4"])
            self.assertTrue((root / "delivery_candidate.mp4").exists())
            self.assertFalse((root / "final.mp4").exists())
            saved = json.loads((root / "verified_preview_package.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["next_action"], "operator_review_or_explicit_final_promotion")

    def test_requires_passing_delivery_gate(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "single_source_highlight_preview.mp4").write_bytes(b"preview")
            _write(root / "delivery_gate.json", {
                "artifact_role": "delivery_gate",
                "pass": False,
            })
            _write(root / "final_product_verify_bundle.json", {
                "artifact_role": "final_product_verify_bundle",
                "pass": True,
            })

            with self.assertRaises(ValueError):
                package_verified_preview(root)

    def test_requires_passing_final_product_verify(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "single_source_highlight_preview.mp4").write_bytes(b"preview")
            _write(root / "delivery_gate.json", {
                "artifact_role": "delivery_gate",
                "pass": True,
            })
            _write(root / "final_product_verify_bundle.json", {
                "artifact_role": "final_product_verify_bundle",
                "pass": False,
            })

            with self.assertRaises(ValueError):
                package_verified_preview(root)

    def test_cli_writes_package(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            preview = root / "single_source_highlight_preview.mp4"
            preview.write_bytes(b"preview")
            _write(root / "delivery_gate.json", {
                "artifact_role": "delivery_gate",
                "pass": True,
                "blocking": [],
            })
            _write(root / "final_product_verify_bundle.json", {
                "artifact_role": "final_product_verify_bundle",
                "pass": True,
                "video": str(preview),
            })
            _write(root / "highlight_cut_report.json", {
                "artifact_role": "highlight_cut_report",
                "out": str(preview),
            })
            proc = subprocess.run(
                ["python", "tools/package_verified_preview.py", "--run", str(root), "--json"],
                cwd=Path(__file__).resolve().parents[1],
                capture_output=True,
                text=True,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["artifact_role"], "verified_preview_package")
            self.assertTrue((root / "delivery_candidate.mp4").exists())


if __name__ == "__main__":
    unittest.main()
