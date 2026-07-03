import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path, PurePosixPath, PureWindowsPath


ROOT = Path(__file__).resolve().parents[1]
VIDEO_TOOLS = ROOT / "video_tools.py"


class AssetPathResolverTest(unittest.TestCase):
    def test_to_asset_ref_relativizes_paths_under_run_dir(self):
        from video_pipeline_core.asset_paths import to_asset_ref

        ref = to_asset_ref(
            PureWindowsPath("C:/runs/demo"),
            PureWindowsPath("C:/runs/demo/assets/clip.mp4"),
        )

        self.assertEqual(ref.ref, "assets/clip.mp4")
        self.assertTrue(ref.portable)

    def test_to_asset_ref_preserves_external_absolute_with_marker(self):
        from video_pipeline_core.asset_paths import to_asset_ref

        ref = to_asset_ref(
            PurePosixPath("/runs/demo"),
            PurePosixPath("/mnt/source/clip.mp4"),
        )

        self.assertEqual(ref.ref, "/mnt/source/clip.mp4")
        self.assertFalse(ref.portable)

    def test_resolve_asset_ref_joins_relative_and_passes_absolute(self):
        from video_pipeline_core.asset_paths import resolve_asset_ref

        self.assertEqual(
            resolve_asset_ref(PureWindowsPath("C:/runs/demo"), "assets/clip.mp4"),
            PureWindowsPath("C:/runs/demo/assets/clip.mp4"),
        )
        self.assertEqual(
            resolve_asset_ref(PurePosixPath("/runs/demo"), "/mnt/source/clip.mp4"),
            PurePosixPath("/mnt/source/clip.mp4"),
        )


class AssetPathAuditCliTest(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(VIDEO_TOOLS), "asset-path-audit", *args],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def test_warn_mode_reports_absolute_paths_but_exits_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            (run_dir / "project_material_map.json").write_text(
                json.dumps({
                    "artifact_role": "project_material_map",
                    "assets": [{"path": "C:/source/clip.mp4"}],
                }),
                encoding="utf-8",
            )

            proc = self.run_cli(str(run_dir), "--json")

        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        report = json.loads(proc.stdout)
        self.assertEqual(report["finding_count"], 1)
        self.assertEqual(report["families"]["material"]["finding_count"], 1)

    def test_strict_mode_fails_only_for_configured_strict_families(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            (run_dir / "unrelated.json").write_text(
                json.dumps({"artifact_role": "unrelated", "path": "/tmp/absolute.mp4"}),
                encoding="utf-8",
            )

            proc = self.run_cli(str(run_dir), "--strict", "--json")

        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        report = json.loads(proc.stdout)
        self.assertEqual(report["strict_finding_count"], 0)

    def test_strict_mode_fails_for_material_family_absolute_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            (run_dir / "project_material_map.json").write_text(
                json.dumps({
                    "artifact_role": "project_material_map",
                    "assets": [{"source": "/tmp/external/clip.mp4"}],
                }),
                encoding="utf-8",
            )

            proc = self.run_cli(str(run_dir), "--strict", "--json")

        self.assertEqual(proc.returncode, 1)
        report = json.loads(proc.stdout)
        self.assertEqual(report["strict_finding_count"], 1)

    def test_strict_mode_fails_for_build_family_absolute_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            (run_dir / "timeline_build.json").write_text(
                json.dumps({
                    "artifact_role": "timeline_build",
                    "clips": [{"source_path": "/tmp/source/clip.mp4"}],
                }),
                encoding="utf-8",
            )

            proc = self.run_cli(str(run_dir), "--strict", "--json")

        self.assertEqual(proc.returncode, 1)
        report = json.loads(proc.stdout)
        self.assertEqual(report["strict_finding_count"], 1)


if __name__ == "__main__":
    unittest.main()
