import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from video_pipeline_core.workbench_project import (
    build_workbench_project,
    resolve_workbench_project,
    validate_workbench_project,
    write_workbench_project,
)
from tools.workbench_project import main


class WorkbenchProjectTest(unittest.TestCase):
    def _make_sources(self, root: Path) -> dict[str, Path]:
        source = root / "source"
        source.mkdir()
        media = source / "clip.mp4"
        media.write_bytes(b"video-source")
        timeline = source / "timeline_build.json"
        timeline.write_text(json.dumps({
            "artifact_role": "timeline_view",
            "clips": [{
                "id": "clip-1",
                "asset_id": "asset-1",
                "source": "clip.mp4",
                "in_seconds": 1.0,
                "out_seconds": 4.0,
                "target_duration_sec": 3.0,
            }],
        }), encoding="utf-8")
        material_map = source / "project_material_map.json"
        material_map.write_text(json.dumps({
            "artifact_role": "project_material_map",
            "assets": [{"asset_id": "asset-1", "source": str(media)}],
        }), encoding="utf-8")
        candidate = source / "final.mp4"
        candidate.write_bytes(b"candidate")
        subtitles = source / "subtitles.srt"
        subtitles.write_text(
            "1\n00:00:00,000 --> 00:00:02,000\nHello\n",
            encoding="utf-8",
        )
        return {
            "timeline": timeline,
            "material_map": material_map,
            "candidate_video": candidate,
            "subtitles": subtitles,
        }

    def test_build_write_validate_and_resolve_exact_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            refs = self._make_sources(base)
            project_root = base / "workbench"
            manifest = build_workbench_project(
                project_root=project_root,
                project_id="case-1",
                display_name="Case One",
                artifact_paths=refs,
            )
            path = write_workbench_project(project_root, manifest)
            validation = validate_workbench_project(project_root)
            loaded, resolved = resolve_workbench_project(project_root)

            self.assertEqual(path, project_root / "workbench_project.json")
            self.assertTrue(validation["ok"], validation["errors"])
            self.assertEqual(loaded["artifact_role"], "workbench_project")
            self.assertEqual(resolved, {key: value.resolve() for key, value in refs.items()})
            self.assertTrue(manifest["policy"]["canonical_artifacts_read_only"])
            self.assertEqual(manifest["policy"]["draft_write_root"], ".")
            for detail in manifest["artifacts"].values():
                self.assertRegex(detail["sha256"], r"^[0-9a-f]{64}$")

    def test_validation_fails_closed_after_referenced_artifact_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            refs = self._make_sources(base)
            project_root = base / "workbench"
            manifest = build_workbench_project(
                project_root=project_root,
                project_id="case-1",
                display_name="Case One",
                artifact_paths=refs,
            )
            write_workbench_project(project_root, manifest)
            refs["timeline"].write_text("{}", encoding="utf-8")

            validation = validate_workbench_project(project_root)
            with self.assertRaises(ValueError):
                resolve_workbench_project(project_root)

        self.assertFalse(validation["ok"])
        self.assertIn("artifact_hash_mismatch", {e["code"] for e in validation["errors"]})

    def test_requires_pipeline_candidate_timeline_and_material_map(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            only_timeline = root / "timeline.json"
            only_timeline.write_text("{}", encoding="utf-8")

            with self.assertRaises(ValueError):
                build_workbench_project(
                    project_root=root / "workbench",
                    project_id="incomplete",
                    display_name="Incomplete",
                    artifact_paths={"timeline": only_timeline},
                )

    def test_public_cli_creates_and_validates_landing(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            refs = self._make_sources(base)
            project_root = base / "workbench"
            out = StringIO()
            with redirect_stdout(out):
                create_rc = main([
                    "create",
                    "--project-root", str(project_root),
                    "--project-id", "cli-case",
                    "--display-name", "CLI case",
                    "--timeline", str(refs["timeline"]),
                    "--material-map", str(refs["material_map"]),
                    "--candidate-video", str(refs["candidate_video"]),
                    "--subtitles", str(refs["subtitles"]),
                ])
            with redirect_stdout(StringIO()):
                validate_rc = main(["validate", "--project-root", str(project_root)])

        self.assertEqual(create_rc, 0, out.getvalue())
        self.assertEqual(validate_rc, 0)

    def test_public_scripts_are_directly_invocable_from_repo_root(self):
        root = Path(__file__).resolve().parents[1]
        scripts = (
            "tools/workbench_project.py",
            "tools/preview_timeline.py",
            "tools/workbench_server.py",
            "tools/dashboard_server.py",
        )
        for script in scripts:
            with self.subTest(script=script):
                completed = subprocess.run(
                    [sys.executable, script, "--help"],
                    cwd=root,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertIn("usage:", completed.stdout.lower())


if __name__ == "__main__":
    unittest.main()
