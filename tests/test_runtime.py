import os
import sys
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from video_pipeline_core import runtime_orchestrator
from video_pipeline_core.project_workspace import init_project, create_run_dir, resolve_active_pointer

class TestRuntime(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory structure for testing
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.root_path = Path(self.tmp_dir.name)
        self.repo_dir = self.root_path / "repo"
        self.projects_dir = self.root_path / "projects"
        self.repo_dir.mkdir(parents=True, exist_ok=True)
        self.projects_dir.mkdir(parents=True, exist_ok=True)

        # Mock the repository root and project workspace default root
        self.repo_root_patcher = patch("video_pipeline_core.runtime_orchestrator.REPO_ROOT", self.repo_dir)
        self.mock_repo_root = self.repo_root_patcher.start()
        
        self.default_root_patcher = patch("video_pipeline_core.project_workspace.default_project_root", return_value=self.projects_dir)
        self.default_root_patcher.start()
        
        # Patch resolve_python to return a dummy executable
        self.python_patcher = patch("video_pipeline_core.runtime_orchestrator.resolve_python", return_value="dummy_python")
        self.python_patcher.start()

    def tearDown(self):
        self.python_patcher.stop()
        self.default_root_patcher.stop()
        self.repo_root_patcher.stop()
        self.tmp_dir.cleanup()

    def _setup_project(self, project_name="test_proj", custom_root=None):
        root = custom_root or self.projects_dir
        proj_info = init_project(project_name, root=root, repo_dir=self.repo_dir)
        project_dir = Path(proj_info["project_dir"])
        contract_data = {
            "style": "mv",
            "music": {"query": "lofi calm"},
            "segments": [{"segment": 1, "source": "stock"}]
        }
        (project_dir / "input" / "segment_contract.json").write_text(json.dumps(contract_data), encoding="utf-8")
        (project_dir / "input" / "brief.json").write_text(json.dumps({"title": "Test Brief"}), encoding="utf-8")
        return project_dir

    def _setup_run(self, project_dir, label="test-run"):
        run_info = create_run_dir(project_dir, label=label, repo_dir=self.repo_dir)
        run_dir = Path(run_info["run_dir"])
        return run_dir

    @patch("subprocess.run")
    def test_fresh_run_compiles_video(self, mock_run):
        # Set up a mock project and contract
        project_dir = self._setup_project("fresh_proj")
        
        # Write input brief and contract
        contract_data = {
            "style": "mv",
            "music": {"query": "lofi calm"},
            "segments": [{"segment": 1, "source": "stock"}]
        }
        (project_dir / "input" / "segment_contract.json").write_text(json.dumps(contract_data), encoding="utf-8")
        (project_dir / "input" / "brief.json").write_text(json.dumps({"title": "Test Brief"}), encoding="utf-8")
        
        # Create the run dir
        run_dir = self._setup_run(project_dir)
        
        # Mock subprocess.run to return a success code, and mock load_dashboard_state
        mock_run.return_value = MagicMock(returncode=0)
        
        states = [
            # first iteration: missing final.mp4
            {
                "run": {"next_action": "missing_artifact:final.mp4", "pass": False},
                "nodes": [], "findings": []
            },
            # second iteration: completed
            {
                "run": {"next_action": "complete_review_final", "pass": True, "final": "final.mp4"},
                "nodes": [], "findings": []
            }
        ]
        
        call_count = 0
        def load_state_side_effect(*args, **kwargs):
            nonlocal call_count
            res = states[call_count]
            call_count += 1
            if call_count == 2:
                (run_dir / "final.mp4").write_text("dummy video", encoding="utf-8")
                (run_dir / "verify_result.json").write_text('{"pass": true}', encoding="utf-8")
            return res
        
        with patch("video_pipeline_core.runtime_orchestrator.load_dashboard_state", side_effect=load_state_side_effect):
            with self.assertRaises(SystemExit) as cm:
                runtime_orchestrator.run_orchestrator(project_name="fresh_proj", args=MagicMock(contract=None, brief=None, music=None, material_db=None))
            
            self.assertEqual(cm.exception.code, 0)
            
            # Verify initial files were copied to run directory
            self.assertTrue((run_dir / "segment_contract.json").exists())
            self.assertTrue((run_dir / "brief.json").exists())
            
            # Verify subprocess.run was called for music fetch and contract-run compilation
            music_called = False
            compile_called = False
            for call in mock_run.call_args_list:
                args_list = call[0][0]
                if "music-fetch" in args_list:
                    music_called = True
                if "contract-run" in args_list:
                    compile_called = True
            
            self.assertTrue(music_called)
            self.assertTrue(compile_called)

    def test_completed_resume_exits_immediately(self):
        project_dir = self._setup_project("complete_proj")
        run_dir = self._setup_run(project_dir)
        
        # Write mock files to satisfy strict completion checks
        (run_dir / "final.mp4").write_text("dummy video", encoding="utf-8")
        (run_dir / "verify_result.json").write_text('{"pass": true}', encoding="utf-8")
        
        state_data = {
            "run": {"next_action": "complete_review_final", "pass": True, "final": "final.mp4"},
            "nodes": [], "findings": []
        }
        with patch("video_pipeline_core.runtime_orchestrator.load_dashboard_state", return_value=state_data):
            with self.assertRaises(SystemExit) as cm:
                runtime_orchestrator.run_orchestrator(project_name="complete_proj", args=MagicMock(contract=None, brief=None, music=None, material_db=None))
            self.assertEqual(cm.exception.code, 0)

    def test_verify_failed_exits_with_error(self):
        project_dir = self._setup_project("failed_proj")
        run_dir = self._setup_run(project_dir)
        
        state_data = {
            "run": {"next_action": "verify_failed", "pass": False, "score": 47.5},
            "findings": [{"type": "error", "message": "Subtitle verification failed"}],
            "nodes": []
        }
        with patch("video_pipeline_core.runtime_orchestrator.load_dashboard_state", return_value=state_data):
            with self.assertRaises(SystemExit) as cm:
                runtime_orchestrator.run_orchestrator(project_name="failed_proj", args=MagicMock(contract=None, brief=None, music=None, material_db=None))
            self.assertEqual(cm.exception.code, 1)

    def test_await_material_arrived_triggers_rebuild(self):
        project_dir = self._setup_project("await_proj")
        run_dir = self._setup_run(project_dir)
        
        # Create input materials folder and place a mock material file
        materials_input_dir = project_dir / "input" / "materials"
        materials_input_dir.mkdir(parents=True, exist_ok=True)
        arrived_file = materials_input_dir / "seg2_user.mp4"
        arrived_file.write_text("dummy_video", encoding="utf-8")
        
        # Write initial contract (segment 2 source is stock/missing)
        contract_data = {
            "segments": [
                {"segment": 1, "source": "stock"},
                {"segment": 2, "source": "stock"}
            ]
        }
        (run_dir / "segment_contract.json").write_text(json.dumps(contract_data), encoding="utf-8")
        
        # Create files to be cleaned up
        (run_dir / "state.json").write_text("{}", encoding="utf-8")
        (run_dir / "final.mp4").write_text("{}", encoding="utf-8")
        
        states = [
            {
                "run": {"next_action": "await_material"},
                "blocking": [{"segment": 2, "reason": "Awaiting seg2"}],
                "nodes": [], "findings": []
            },
            {
                "run": {"next_action": None},
                "nodes": [], "findings": []
            }
        ]
        
        with patch("video_pipeline_core.runtime_orchestrator.load_dashboard_state", side_effect=states):
            with self.assertRaises(SystemExit) as cm:
                runtime_orchestrator.run_orchestrator(project_name="await_proj", args=MagicMock(contract=None, brief=None))
            self.assertEqual(cm.exception.code, 0)
            
        # Verify:
        # 1. material file copied to raw materials
        self.assertTrue((run_dir / "materials" / "raw" / "seg2_user.mp4").exists())
        # 2. contract updated to source=local and file points to new location
        updated_contract = json.loads((run_dir / "segment_contract.json").read_text(encoding="utf-8"))
        self.assertEqual(updated_contract["segments"][1]["source"], "local")
        self.assertTrue("seg2_user.mp4" in updated_contract["segments"][1]["file"])
        # 3. old artifacts cleared
        self.assertFalse((run_dir / "state.json").exists())
        self.assertFalse((run_dir / "final.mp4").exists())

    def test_await_material_not_arrived_exits(self):
        project_dir = self._setup_project("await_no_proj")
        run_dir = self._setup_run(project_dir)
        
        # Simulate state load: await_material, but no arrived files
        state_data = {
            "run": {"next_action": "await_material"},
            "blocking": [{"segment": 2, "reason": "Awaiting seg2"}],
            "nodes": [], "findings": []
        }
        with patch("video_pipeline_core.runtime_orchestrator.load_dashboard_state", return_value=state_data):
            with self.assertRaises(SystemExit) as cm:
                runtime_orchestrator.run_orchestrator(project_name="await_no_proj", args=MagicMock(contract=None, brief=None))
            self.assertEqual(cm.exception.code, 0)

    @patch("subprocess.run")
    def test_wait_for_generated_provider_arrived_triggers_rebuild(self, mock_run):
        project_dir = self._setup_project("gen_proj")
        run_dir = self._setup_run(project_dir)
        
        # Write request json
        requests_data = {
            "items": [{"segment": 1, "provider": "antigravity", "prompt": "conceptual scene"}]
        }
        (run_dir / "generated_asset_requests.json").write_text(json.dumps(requests_data), encoding="utf-8")
        
        # Simulate generated asset arrived
        gen_dir = run_dir / "materials" / "generated"
        gen_dir.mkdir(parents=True, exist_ok=True)
        (gen_dir / "seg1_generated.jpg").write_text("dummy_image", encoding="utf-8")
        
        # Create artifacts to clean up
        (run_dir / "state.json").write_text("{}", encoding="utf-8")
        (run_dir / "final.mp4").write_text("{}", encoding="utf-8")
        
        states = [
            {
                "run": {"next_action": "wait_for_generated_provider"},
                "nodes": [], "findings": []
            },
            {
                "run": {"next_action": None},
                "nodes": [], "findings": []
            }
        ]
        
        with patch("video_pipeline_core.runtime_orchestrator.load_dashboard_state", side_effect=states):
            with self.assertRaises(SystemExit) as cm:
                runtime_orchestrator.run_orchestrator(project_name="gen_proj", args=MagicMock(contract=None, brief=None, music=None, material_db=None))
            self.assertEqual(cm.exception.code, 0)
            
        # Verify:
        # 1. generated-manifest tool called
        manifest_called = False
        for call in mock_run.call_args_list:
            args_list = call[0][0]
            if "generated-manifest" in args_list:
                manifest_called = True
        self.assertTrue(manifest_called)
        
        # 2. old artifacts cleared
        self.assertFalse((run_dir / "state.json").exists())
        self.assertFalse((run_dir / "final.mp4").exists())

    @patch("subprocess.run")
    @patch("video_pipeline_core.runtime_orchestrator.run_orchestrator")
    def test_rerun_node_12_runs_verification_directly_without_deleting_final(self, mock_orchestrate, mock_run):
        project_dir = self._setup_project("rerun_proj")
        run_dir = self._setup_run(project_dir)
        
        # Write final.mp4 and verify artifacts
        final_mp4 = run_dir / "final.mp4"
        final_mp4.write_text("video", encoding="utf-8")
        verify_result = run_dir / "verify_result.json"
        verify_result.write_text("{}", encoding="utf-8")
        state_file = run_dir / "state.json"
        state_file.write_text("{}", encoding="utf-8")
        
        # Call rerun_node for node "12"
        runtime_orchestrator.rerun_node("12", project_name="rerun_proj", args=MagicMock())
        
        # Verify:
        # 1. final.mp4 is NOT deleted!
        self.assertTrue(final_mp4.exists())
        # 2. verify_result.json and state.json are deleted!
        self.assertFalse(verify_result.exists())
        self.assertFalse(state_file.exists())
        
        # 3. verify command is run directly via subprocess.run
        verify_called = False
        state_cmd_called = False
        for call in mock_run.call_args_list:
            args_list = call[0][0]
            if "verify" in args_list:
                verify_called = True
            if "state" in args_list:
                state_cmd_called = True
        self.assertTrue(verify_called)
        self.assertTrue(state_cmd_called)
        
        # 4. run_orchestrator is called to resume
        mock_orchestrate.assert_called_once()

    def test_custom_project_root_pointer_resolution(self):
        # Create a custom project root outside of default location
        custom_root = self.root_path / "custom_projects_folder"
        custom_root.mkdir(parents=True, exist_ok=True)
        
        # Initialize project with root
        proj_info = init_project("custom_root_proj", root=custom_root, repo_dir=self.repo_dir)
        project_dir = Path(proj_info["project_dir"])
        run_dir = self._setup_run(project_dir)
        
        # Check active.json
        active_json = self.repo_dir / ".project" / "active.json"
        self.assertTrue(active_json.exists())
        
        # Call _get_project_and_run with no project name
        resolved_proj, resolved_run = runtime_orchestrator._get_project_and_run()
        
        self.assertEqual(resolved_proj.resolve(), project_dir.resolve())
        self.assertEqual(resolved_run.resolve(), run_dir.resolve())

    @patch("subprocess.run")
    def test_non_repo_cwd_resolution(self, mock_run):
        # Change current working directory to a temporary directory outside the repo
        outside_dir = self.root_path / "outside_dir"
        outside_dir.mkdir(parents=True, exist_ok=True)
        orig_cwd = os.getcwd()
        try:
            os.chdir(outside_dir)
            
            project_dir = self._setup_project("outside_proj")
            # Create contract and brief
            contract_data = {"style": "mv", "music": {"query": "test"}, "segments": []}
            (project_dir / "input" / "segment_contract.json").write_text(json.dumps(contract_data), encoding="utf-8")
            (project_dir / "input" / "brief.json").write_text(json.dumps({}), encoding="utf-8")
            
            # Place categories file
            (project_dir / "input" / "material_categories.json").write_text("{}", encoding="utf-8")
            
            run_dir = self._setup_run(project_dir)
            
            # Run one iteration of loop
            states = [
                {"run": {"next_action": "missing_artifact:final.mp4"}, "nodes": [], "findings": []},
                {"run": {"next_action": None}, "nodes": [], "findings": []}
            ]
            
            with patch("video_pipeline_core.runtime_orchestrator.load_dashboard_state", side_effect=states):
                with self.assertRaises(SystemExit):
                    runtime_orchestrator.run_orchestrator(project_name="outside_proj", args=MagicMock(contract=None, brief=None, music=None, material_db=None))
            
            # Verify that the subprocess commands use absolute paths for video_tools.py
            tools_path_found = False
            for call in mock_run.call_args_list:
                args_list = call[0][0]
                # Look for absolute video_tools.py path
                for arg in args_list:
                    if "video_tools.py" in arg:
                        p = Path(arg)
                        self.assertTrue(p.is_absolute())
                        tools_path_found = True
            self.assertTrue(tools_path_found)
            
        finally:
            os.chdir(orig_cwd)

    def test_revise_director_exits(self):
        project_dir = self._setup_project("revise_dir_proj")
        self._setup_run(project_dir)
        
        state_data = {
            "run": {"next_action": "revise:director:segment_contract.json"},
            "nodes": [],
            "findings": []
        }
        with patch("video_pipeline_core.runtime_orchestrator.load_dashboard_state", return_value=state_data):
            with self.assertRaises(SystemExit) as cm:
                runtime_orchestrator.run_orchestrator(project_name="revise_dir_proj", args=MagicMock(contract=None, brief=None))
            self.assertEqual(cm.exception.code, 0)

    def test_retry_curator_exits(self):
        project_dir = self._setup_project("retry_cur_proj")
        self._setup_run(project_dir)
        
        state_data = {
            "run": {"next_action": "retry:curator:search_query"},
            "nodes": [],
            "findings": []
        }
        with patch("video_pipeline_core.runtime_orchestrator.load_dashboard_state", return_value=state_data):
            with self.assertRaises(SystemExit) as cm:
                runtime_orchestrator.run_orchestrator(project_name="retry_cur_proj", args=MagicMock(contract=None, brief=None))
            self.assertEqual(cm.exception.code, 0)

class TestAuditRouting(unittest.TestCase):
    def test_resolve_audit_route_none_when_no_audit_findings(self):
        dash_state = {"findings": [{"type": "error", "message": "unrelated"}],
                      "artifacts": {}}
        self.assertIsNone(runtime_orchestrator.resolve_audit_route(dash_state))

    def test_resolve_audit_route_picks_smallest_affected_node(self):
        dash_state = {
            "findings": [
                {"type": "error", "node": 12, "artifact": "visual_audit",
                 "message": "visual_audit failed"},
                {"type": "error", "node": 11, "artifact": "timeline_invariants",
                 "message": "timeline_invariants failed"},
            ],
            "artifacts": {
                "timeline_invariants": {"pass": False, "next_action": "fix_timeline_or_assembly"},
                "visual_audit": {"pass": False, "next_action": "node_13_rerender"},
            },
        }
        route = runtime_orchestrator.resolve_audit_route(dash_state)
        self.assertIsNotNone(route)
        self.assertEqual(route["artifact"], "timeline_invariants")
        self.assertEqual(route["node"], "11")
        self.assertEqual(route["next_action"], "fix_timeline_or_assembly")
        self.assertIn("editor_review", route["skill"])


class TestRuntimeAuditIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.root_path = Path(self.tmp_dir.name)
        self.repo_dir = self.root_path / "repo"
        self.projects_dir = self.root_path / "projects"
        self.repo_dir.mkdir(parents=True, exist_ok=True)
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        self.repo_root_patcher = patch("video_pipeline_core.runtime_orchestrator.REPO_ROOT", self.repo_dir)
        self.repo_root_patcher.start()
        self.default_root_patcher = patch("video_pipeline_core.project_workspace.default_project_root", return_value=self.projects_dir)
        self.default_root_patcher.start()
        self.python_patcher = patch("video_pipeline_core.runtime_orchestrator.resolve_python", return_value="dummy_python")
        self.python_patcher.start()

    def tearDown(self):
        self.python_patcher.stop()
        self.default_root_patcher.stop()
        self.repo_root_patcher.stop()
        self.tmp_dir.cleanup()

    def test_failing_audit_blocks_completion(self):
        import io
        from contextlib import redirect_stdout
        from video_pipeline_core.project_workspace import init_project, create_run_dir

        proj_info = init_project("audit_proj", root=self.projects_dir, repo_dir=self.repo_dir)
        project_dir = Path(proj_info["project_dir"])
        (project_dir / "input" / "segment_contract.json").write_text(
            json.dumps({"style": "mv", "segments": [{"segment": 1, "source": "stock"}]}),
            encoding="utf-8")
        (project_dir / "input" / "brief.json").write_text(
            json.dumps({"title": "Audit"}), encoding="utf-8")
        run_info = create_run_dir(project_dir, label="audit-run", repo_dir=self.repo_dir)
        run_dir = Path(run_info["run_dir"])
        (run_dir / "final.mp4").write_text("dummy", encoding="utf-8")
        (run_dir / "verify_result.json").write_text('{"pass": true}', encoding="utf-8")

        # Verify passes, but a deterministic timeline audit failed -> must not complete.
        state_data = {
            "run": {"next_action": "complete_review_final", "pass": True, "final": "final.mp4"},
            "nodes": [],
            "findings": [{"type": "error", "node": 11, "artifact": "timeline_invariants",
                          "message": "timeline_invariants failed: fix_timeline_or_assembly"}],
            "artifacts": {"timeline_invariants": {"pass": False,
                                                  "next_action": "fix_timeline_or_assembly"}},
        }
        buf = io.StringIO()
        with patch("video_pipeline_core.runtime_orchestrator.load_dashboard_state", return_value=state_data):
            with redirect_stdout(buf):
                with self.assertRaises(SystemExit) as cm:
                    runtime_orchestrator.run_orchestrator(
                        project_name="audit_proj",
                        args=MagicMock(contract=None, brief=None, music=None, material_db=None))
        out = buf.getvalue()
        self.assertEqual(cm.exception.code, 0)
        self.assertNotIn("completed successfully", out)
        self.assertIn("timeline_invariants", out)


if __name__ == "__main__":
    unittest.main()
