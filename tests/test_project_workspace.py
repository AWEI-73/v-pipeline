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

    def test_create_run_dir_writes_machine_readable_layout_manifest(self):
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

            manifest_path = Path(run["run_dir"]) / "run_layout.json"
            self.assertTrue(manifest_path.is_file())
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["artifact_role"], "run_layout")
            self.assertEqual(manifest["version"], 1)
            self.assertEqual(manifest["project_dir"], str(Path(project["project_dir"])))
            self.assertEqual(manifest["run_dir"], str(Path(run["run_dir"])))
            self.assertEqual(manifest["folders"]["spec"], "spec")
            self.assertEqual(manifest["folders"]["build"], "build")
            self.assertEqual(manifest["folders"]["verify"], "verify")
            self.assertEqual(manifest["folders"]["materials_selected"], "materials/selected")
            self.assertEqual(manifest["artifact_classes"]["canonical"], [
                "segment_contract.json",
                "material_needs.json",
                "project_material_map.json",
                "materials_db.json",
                "timeline.json",
                "final.mp4",
                "state.json",
                "artifact_manifest.json",
            ])
            self.assertIn("timeline_patch.json", manifest["artifact_classes"]["workbench_draft"])
            self.assertIn("workbench_proxy", manifest["artifact_classes"]["derived_cache_dirs"])
            self.assertEqual(manifest["artifact_classes"]["orchestration"], [
                "video_intent.json",
                "route_orchestrator_state.json",
                "route_subagent_task.json",
                "route_subagent_result.json",
                "route_orchestrator_acceptance.json",
            ])
            route_state = json.loads((Path(run["run_dir"]) / "route_orchestrator_state.json").read_text(encoding="utf-8"))
            self.assertEqual(route_state["artifact_role"], "route_orchestrator_state")
            self.assertEqual(route_state["current_stage"], 0)
            self.assertEqual(route_state["status"], "ready")

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

    def test_validate_run_layout_accepts_new_project_run(self):
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
            (Path(run["run_dir"]) / "timeline.json").write_text("[]", encoding="utf-8")
            (Path(run["run_dir"]) / "timeline_patch.json").write_text(
                json.dumps({"patches": []}),
                encoding="utf-8",
            )
            (Path(run["run_dir"]) / "video_intent.json").write_text(
                json.dumps({"artifact_role": "video_intent"}),
                encoding="utf-8",
            )

            report = project_workspace.validate_run_layout(run["run_dir"])

            self.assertTrue(report["ok"], report["errors"])
            self.assertEqual(report["artifact_role"], "run_layout_validation")
            self.assertEqual(report["present_artifacts"]["canonical"], ["timeline.json"])
            self.assertEqual(report["present_artifacts"]["workbench_draft"], ["timeline_patch.json"])
            self.assertEqual(report["present_artifacts"]["orchestration"], [
                "route_orchestrator_state.json",
                "video_intent.json",
            ])
            self.assertEqual(report["folders"]["spec"]["status"], "ok")

    def test_validate_run_layout_fails_closed_on_missing_or_bad_layout(self):
        with tempfile.TemporaryDirectory() as d:
            run_dir = Path(d) / "run"
            run_dir.mkdir()

            missing = project_workspace.validate_run_layout(run_dir)
            self.assertFalse(missing["ok"])
            self.assertEqual(missing["errors"][0]["code"], "missing_layout")

            (run_dir / "run_layout.json").write_text("{bad", encoding="utf-8")
            malformed = project_workspace.validate_run_layout(run_dir)
            self.assertFalse(malformed["ok"])
            self.assertEqual(malformed["errors"][0]["code"], "malformed_layout")

    def test_validate_run_layout_rejects_unsafe_and_duplicate_ownership(self):
        with tempfile.TemporaryDirectory() as d:
            run_dir = Path(d) / "run"
            run_dir.mkdir()
            layout = project_workspace.build_run_layout(run_dir.parent, run_dir)
            layout["folders"]["escape"] = "../outside"
            layout["artifact_classes"]["workbench_draft"].append("final.mp4")
            (run_dir / "run_layout.json").write_text(
                json.dumps(layout),
                encoding="utf-8",
            )

            report = project_workspace.validate_run_layout(run_dir)

            self.assertFalse(report["ok"])
            codes = {e["code"] for e in report["errors"]}
            self.assertIn("unsafe_folder_path", codes)
            self.assertIn("duplicate_artifact_owner", codes)

    def test_validate_run_layout_rejects_cache_dir_as_file(self):
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
            thumbs = Path(run["run_dir"]) / "workbench_thumbs"
            thumbs.write_text("not a directory", encoding="utf-8")

            report = project_workspace.validate_run_layout(run["run_dir"])

            self.assertFalse(report["ok"])
            self.assertIn("cache_path_not_directory", {e["code"] for e in report["errors"]})

    def test_video_tools_run_layout_validate_writes_report_and_fails_invalid(self):
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
            out = Path(d) / "layout_validation.json"

            with redirect_stdout(StringIO()):
                video_tools.cmd_run_layout_validate(
                    SimpleNamespace(run_dir=run["run_dir"], out=str(out))
                )
            self.assertTrue(json.loads(out.read_text(encoding="utf-8"))["ok"])

            (Path(run["run_dir"]) / "run_layout.json").unlink()
            with self.assertRaises(Exception):
                with redirect_stdout(StringIO()):
                    video_tools.cmd_run_layout_validate(
                        SimpleNamespace(run_dir=run["run_dir"], out=None)
                    )


if __name__ == "__main__":
    unittest.main()
