import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from video_pipeline_core import project_workspace
import video_tools


class ProjectWorkspaceTest(unittest.TestCase):
    def test_default_project_root_is_outside_repo_home_folder(self):
        import os
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            with patch.dict("os.environ", {}, clear=True), \
                 patch.object(Path, "home", return_value=home):
                root = project_workspace.default_project_root()
        expected = home / "Desktop" / "video_project" if os.name == "nt" else home / "video_pipeline_projects"
        self.assertEqual(root, expected)

    def test_init_project_creates_external_layout_and_active_pointer(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "projects"
            repo = Path(d) / "repo"
            result = project_workspace.init_project("ETF Demo", root=root, repo_dir=repo)
            active = json.loads((repo / ".project" / "active.json").read_text(encoding="utf-8"))
            self.assertEqual(result["project_name"], "ETF Demo")
            self.assertEqual(result["project_slug"], "etf-demo")
            self.assertTrue((root / "etf-demo" / "input").is_dir())
            self.assertTrue((root / "etf-demo" / "input" / "materials").is_dir())
            self.assertTrue((root / "etf-demo" / "runs").is_dir())
            self.assertEqual(active["project_root"], "../projects")
            self.assertEqual(active["active_project"], "etf-demo")
            self.assertIsNone(active["active_run"])
            resolved_project, resolved_run = project_workspace.resolve_active_pointer(active, repo_dir=repo)
            self.assertEqual(resolved_project.resolve(), (root / "etf-demo").resolve())
            self.assertIsNone(resolved_run)

    def test_create_run_dir_updates_active_pointer(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "projects"
            repo = Path(d) / "repo"
            project = project_workspace.init_project("ETF Demo", root=root, repo_dir=repo)
            run = project_workspace.create_run_dir(
                project["project_dir"],
                label="baseline",
                repo_dir=repo,
                timestamp="20260605-153000",
            )
            active = json.loads((repo / ".project" / "active.json").read_text(encoding="utf-8"))
            self.assertEqual(Path(run["run_dir"]).name, "20260605-153000-baseline")
            self.assertTrue((Path(run["run_dir"]) / "materials").is_dir())
            self.assertTrue((Path(run["run_dir"]) / "materials" / "selected").is_dir())
            self.assertTrue((Path(run["run_dir"]) / "materials" / "generated").is_dir())
            self.assertTrue((Path(run["run_dir"]) / "spec").is_dir())
            self.assertTrue((Path(run["run_dir"]) / "build").is_dir())
            self.assertTrue((Path(run["run_dir"]) / "verify").is_dir())
            self.assertTrue((Path(run["run_dir"]) / "nodes").is_dir())
            self.assertTrue((Path(run["run_dir"]) / "brownfield").is_dir())
            self.assertEqual(run["selected_materials_dir"], str(Path(run["run_dir"]) / "materials" / "selected"))
            self.assertEqual(active["active_run"], "runs/20260605-153000-baseline")
            _project_dir, resolved_run = project_workspace.resolve_active_pointer(active, repo_dir=repo)
            self.assertEqual(resolved_run.resolve(), Path(run["run_dir"]).resolve())

    def test_video_tools_project_commands_use_repo_active_pointer(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "projects"
            repo = Path(d) / "repo"
            with patch.object(project_workspace, "REPO_DIR", repo):
                with redirect_stdout(StringIO()):
                    video_tools.cmd_project_init(SimpleNamespace(name="ETF Demo", root=str(root)))
                    video_tools.cmd_project_new_run(
                        SimpleNamespace(project=None, label="first-cut")
                    )

            active = json.loads((repo / ".project" / "active.json").read_text(encoding="utf-8"))
            self.assertEqual(active["active_project"], "etf-demo")
            self.assertIn("first-cut", active["active_run"])
            _project_dir, active_run = project_workspace.resolve_active_pointer(active, repo_dir=repo)
            self.assertTrue((active_run / "logs").is_dir())

    def test_run_layout_names_are_stable_for_detection(self):
        expected = [
            "spec",
            "build",
            "verify",
            "materials/raw",
            "materials/selected",
            "materials/generated",
            "materials/stock",
            "nodes",
            "logs",
            "thumbs",
            "brownfield",
        ]
        self.assertEqual(project_workspace.RUN_LAYOUT, expected)


if __name__ == "__main__":
    unittest.main()
