import json
import os
import shutil
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import HTTPServer
from pathlib import Path

from tools.dashboard_server import (
    WORKBENCH_DRAFT_ARTIFACTS,
    DashboardHandler,
    classify_project_run,
    detect_profile,
    scan_project_runs,
)
from video_pipeline_core import project_workspace


class DashboardServerTest(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for artifacts
        self.test_dir = tempfile.mkdtemp()
        self.artifact_root = Path(self.test_dir)
        
        # Create a temporary directory for dashboard UI
        self.dashboard_dir_temp = tempfile.mkdtemp()
        self.dashboard_dir = Path(self.dashboard_dir_temp)
        
        # Create dummy HTML/CSS/JS files
        (self.dashboard_dir / "index.html").write_text("<html><div id=\"app\" data-app=\"hermes-spa-dashboard\"></div></html>", encoding="utf-8")
        src_dir = self.dashboard_dir / "src"
        src_dir.mkdir()
        (src_dir / "main.js").write_text("// SPA MAIN", encoding="utf-8")
        (src_dir / "base.css").write_text("/* SPA CSS */", encoding="utf-8")
        archive_dir = self.dashboard_dir / "archive"
        archive_dir.mkdir()
        (archive_dir / "dashboard_v1.html").write_text("<html>Dashboard HTML</html>", encoding="utf-8")
        (archive_dir / "dashboard_v1.css").write_text("/* CSS */", encoding="utf-8")
        (archive_dir / "dashboard_v1.js").write_text("// JS", encoding="utf-8")
        (self.dashboard_dir / "material_map_review.html").write_text("<html><div id=\"material-map-root\"></div></html>", encoding="utf-8")
        (self.dashboard_dir / "material_map_review.css").write_text("/* MM CSS */", encoding="utf-8")
        (self.dashboard_dir / "material_map_review.js").write_text("// MM JS", encoding="utf-8")

        # Set up handler with dynamic class mapping
        class TestBoundDashboardHandler(DashboardHandler):
            artifact_root = Path(self.test_dir).resolve()
            dashboard_dir = Path(self.dashboard_dir_temp).resolve()

        self.handler_class = TestBoundDashboardHandler
        self.server = None
        self.server_thread = None
        self.port = None

    def tearDown(self):
        # Stop server if running
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        if self.server_thread:
            self.server_thread.join()

        # Clean up temp directories
        shutil.rmtree(self.test_dir, ignore_errors=True)
        shutil.rmtree(self.dashboard_dir_temp, ignore_errors=True)

    def start_test_server(self):
        """Starts the server in a background thread on a random free port."""
        self.server = HTTPServer(("localhost", 0), self.handler_class)
        self.port = self.server.server_port
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()

    def test_profile_detection(self):
        # 1. Neither -> unknown
        self.assertEqual(detect_profile(self.artifact_root), "unknown")

        # 2. Has review_report.json + timeline.json -> review_demo
        (self.artifact_root / "review_report.json").write_text("{}", encoding="utf-8")
        (self.artifact_root / "timeline.json").write_text("{}", encoding="utf-8")
        self.assertEqual(detect_profile(self.artifact_root), "review_demo")

        # Clean up
        (self.artifact_root / "review_report.json").unlink()
        (self.artifact_root / "timeline.json").unlink()

        # 3. Has verify_evidence_bundle.json -> verify_bundle
        (self.artifact_root / "verify_evidence_bundle.json").write_text("{}", encoding="utf-8")
        self.assertEqual(detect_profile(self.artifact_root), "verify_bundle")

        # Clean up
        (self.artifact_root / "verify_evidence_bundle.json").unlink()

        # 4. Has delivery_gate.json -> verify_bundle
        (self.artifact_root / "delivery_gate.json").write_text("{}", encoding="utf-8")
        self.assertEqual(detect_profile(self.artifact_root), "verify_bundle")

    def test_project_scan_prioritizes_current_route_run_folders(self):
        stale = self.artifact_root / "old_placeholder"
        stale.mkdir()

        partial = self.artifact_root / "partial_material_map"
        partial.mkdir()
        (partial / "project_material_map.json").write_text("{}", encoding="utf-8")

        story = self.artifact_root / "story_real_run"
        story.mkdir()
        (story / "video_intent.json").write_text("{}", encoding="utf-8")
        (story / "reviewed_project_material_map.json").write_text("{}", encoding="utf-8")
        (story / "fresh_material_delta.json").write_text("{}", encoding="utf-8")
        (story / "timeline.json").write_text("{}", encoding="utf-8")

        legacy_finished = self.artifact_root / "legacy_finished_run"
        legacy_finished.mkdir()
        (legacy_finished / "timeline_build.json").write_text("{}", encoding="utf-8")
        (legacy_finished / "final.mp4").write_bytes(b"fake mp4")

        projects = scan_project_runs([self.artifact_root])
        names = [project["name"] for project in projects]

        self.assertIn("story_real_run", names)
        self.assertNotIn("old_placeholder", names)
        self.assertNotIn("partial_material_map", names)
        self.assertNotIn("legacy_finished_run", names)
        self.assertTrue(all(project["usable"] for project in projects))
        self.assertIn("material_map_reviewed", projects[0]["signals"])

    def test_project_scan_includes_pipeline_workbench_landing(self):
        landing = self.artifact_root / "current_pipeline_landing"
        landing.mkdir()
        (landing / "workbench_project.json").write_text(json.dumps({
            "artifact_role": "workbench_project",
            "version": 1,
            "project_id": "landing",
            "display_name": "Current landing",
            "artifacts": {},
        }), encoding="utf-8")

        projects = scan_project_runs([self.artifact_root])
        project = next(item for item in projects if item["name"] == "Current landing")

        self.assertIn("workbench_project", project["signals"])
        self.assertIn("V Pipeline", project["reason"])

    def test_project_scan_can_limit_to_top_level_run_folders(self):
        top_level = self.artifact_root / "top_level_story_run"
        top_level.mkdir()
        (top_level / "video_intent.json").write_text("{}", encoding="utf-8")
        (top_level / "reviewed_project_material_map.json").write_text("{}", encoding="utf-8")

        nested = self.artifact_root / "probe_wrapper" / "nested_output"
        nested.mkdir(parents=True)
        (nested / "video_intent.json").write_text("{}", encoding="utf-8")
        (nested / "reviewed_project_material_map.json").write_text("{}", encoding="utf-8")

        projects = scan_project_runs([self.artifact_root], max_depth=1)
        names = [project["name"] for project in projects]

        self.assertIn("top_level_story_run", names)
        self.assertNotIn("nested_output", names)

    def test_scan_available_projects_includes_workspace_runs_folder(self):
        workspace_run = Path.cwd() / "runs" / "dashboard_scan_fixture"
        workspace_run.mkdir(parents=True, exist_ok=True)
        try:
            (workspace_run / "video_intent.json").write_text("{}", encoding="utf-8")
            (workspace_run / "reviewed_project_material_map.json").write_text("{}", encoding="utf-8")
            (workspace_run / "fresh_material_delta.json").write_text("{}", encoding="utf-8")

            from tools.dashboard_server import scan_available_projects
            projects = scan_available_projects()
            paths = {project["path"] for project in projects}

            self.assertIn(str(workspace_run.resolve()), paths)
        finally:
            for child in workspace_run.glob("*"):
                child.unlink()
            workspace_run.rmdir()

    def test_scan_available_projects_only_indexes_curated_tmp_landings(self):
        from tools.dashboard_server import scan_available_projects

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            landing = base / ".tmp" / "workbench_projects" / "current"
            landing.mkdir(parents=True)
            (landing / "workbench_project.json").write_text(json.dumps({
                "artifact_role": "workbench_project",
                "version": 1,
                "project_id": "current",
                "display_name": "Current project",
                "artifacts": {},
            }), encoding="utf-8")
            historical_fixture = base / ".tmp" / "negative_fixture"
            historical_fixture.mkdir(parents=True)
            (historical_fixture / "video_intent.json").write_text("{}", encoding="utf-8")
            (historical_fixture / "reviewed_project_material_map.json").write_text("{}", encoding="utf-8")

            old_cwd = Path.cwd()
            try:
                os.chdir(base)
                projects = scan_available_projects()
            finally:
                os.chdir(old_cwd)

        paths = {project["path"] for project in projects}
        self.assertIn(str(landing.resolve()), paths)
        self.assertNotIn(str(historical_fixture.resolve()), paths)

    def test_project_run_last_modified_uses_signal_files_only(self):
        run = self.artifact_root / "run_with_media"
        media = run / "media"
        media.mkdir(parents=True)
        (run / "video_intent.json").write_text("{}", encoding="utf-8")
        (run / "reviewed_project_material_map.json").write_text("{}", encoding="utf-8")
        (run / "fresh_material_delta.json").write_text("{}", encoding="utf-8")
        (media / "large-unused.mp4").write_bytes(b"x")

        project = classify_project_run(run)

        self.assertTrue(project["usable"])
        self.assertGreater(project["last_modified"], 0)

    def test_legacy_dashboard_page_is_archived(self):
        root = Path(__file__).resolve().parent.parent / "dashboard"
        self.assertFalse((root / "dashboard_v1.html").exists())
        html = (root / "archive" / "dashboard_v1.html").read_text(encoding="utf-8")
        self.assertIn('id="btn-open-workbench"', html)
        self.assertIn("Workbench", html)

    def test_api_artifacts_surfaces_material_first_boundary_acceptance_report(self):
        report = {
            "artifact_role": "material_first_boundary_acceptance_report",
            "version": 1,
            "route": "material-first",
            "ok": True,
            "next_action": "ready_for_render_or_human_review",
            "failed_stage": None,
            "source_dir": "C:/fixture/materials",
            "stages": [
                {
                    "stage": "stage2_3_material_wall_to_review_apply",
                    "ok": True,
                    "next_action": None,
                    "blocking": [],
                    "report": "stage2_3_smoke_report.json",
                }
            ],
        }
        (self.artifact_root / "material_first_boundary_acceptance_report.json").write_text(
            json.dumps(report), encoding="utf-8"
        )

        self.start_test_server()
        with urllib.request.urlopen(f"http://localhost:{self.port}/api/artifacts") as response:
            payload = json.loads(response.read().decode("utf-8"))

        self.assertEqual(payload["material_first_boundary_acceptance_report"]["artifact_role"], report["artifact_role"])
        self.assertTrue(payload["material_first_boundary_acceptance_report"]["ok"])

    def test_spa_dashboard_declares_new_shell_and_real_api_modules(self):
        root = Path(__file__).resolve().parent.parent / "dashboard"
        html = (root / "index.html").read_text(encoding="utf-8")
        main_js = (root / "src" / "main.js").read_text(encoding="utf-8")
        workbench_api = (root / "src" / "api" / "workbenchApi.js").read_text(encoding="utf-8")
        workbench_view = (root / "src" / "views" / "WorkbenchView.js").read_text(encoding="utf-8")
        workbench_contract = (root / "workbench_native" / "API_CONTRACT.md").read_text(encoding="utf-8")
        workbench_layout_smoke = (Path(__file__).resolve().parent.parent / "tools" /
                                  "workbench_browser_layout_smoke.mjs").read_text(encoding="utf-8")
        app_header = (root / "src" / "components" / "AppHeader.js").read_text(encoding="utf-8")
        route_rail = (root / "src" / "components" / "VerticalRouteTimeline.js").read_text(encoding="utf-8")
        route_view = (root / "src" / "views" / "RouteOverviewView.js").read_text(encoding="utf-8")
        material_map_view = (root / "src" / "views" / "MaterialMapView.js").read_text(encoding="utf-8")
        layout_css = (root / "src" / "styles" / "layout.css").read_text(encoding="utf-8")
        views_css = (root / "src" / "styles" / "views.css").read_text(encoding="utf-8")
        route_review_spec = (Path(__file__).resolve().parent.parent / "docs" /
                             "construction-guides" / "dashboard" /
                             "dashboard-route-review-ux-spec.md").read_text(encoding="utf-8")

        self.assertIn('id="app"', html)
        self.assertIn('data-app="hermes-spa-dashboard"', html)
        self.assertIn('type="module"', html)
        self.assertIn("/src/main.js", html)
        self.assertNotIn("Control Index", html)
        self.assertNotIn("MODE_MOCKS", html)
        self.assertIn("RouteOverviewView", main_js)
        self.assertIn("MaterialMapView", main_js)
        self.assertIn("WorkbenchView", main_js)
        self.assertIn("/api/workbench/health", workbench_api)
        self.assertIn("workbenchHealth", workbench_view)
        self.assertIn('id="spa-project-select"', app_header)
        self.assertIn("fetchProjects", main_js)
        self.assertIn("data-stage", route_rail)
        self.assertIn("stage-detail-panel", route_view)
        self.assertIn("activeStage", main_js)
        self.assertIn("stage-file-list", route_view)
        self.assertIn("stageFileManifest", route_view)
        self.assertIn("stage-file-status", route_view)
        self.assertIn("renderBoundaryAcceptance", route_view)
        self.assertIn("material_first_boundary_acceptance_report", route_view)
        self.assertIn("邊界驗收", route_view)
        self.assertIn("boundary-acceptance-panel", views_css)
        self.assertIn("#app.app-workbench", layout_css)
        self.assertIn("width: min(1880px, calc(100vw - 16px));", layout_css)
        self.assertIn(".app-workbench .dashboard-canvas", layout_css)
        self.assertIn(".root-open-row", layout_css)
        self.assertIn("grid-template-columns: minmax(120px, 1fr) auto;", layout_css)
        self.assertIn(".app-workbench .root-open-form", layout_css)
        self.assertIn("workbench-studio-head", views_css)
        self.assertIn("workbench-run-strip", views_css)
        self.assertIn("workbench-native-handoff", views_css)
        self.assertIn(".primary-link", views_css)
        self.assertIn("Native Editor Protected Zone", workbench_contract)
        self.assertIn("video monitor / playback preview", workbench_contract)
        self.assertIn("four lower timeline lanes", workbench_contract)
        self.assertIn("playback controls", workbench_contract)
        self.assertIn("Dashboard white-box modules may mount beside this surface", workbench_contract)
        self.assertIn("must not duplicate", workbench_contract)
        self.assertIn("node tools\\workbench_browser_layout_smoke.mjs --url http://localhost:8765/workbench", workbench_contract)
        self.assertIn("python tools\\workbench_frontend_smoke.py --artifact-root .tmp\\workbench_frontend_smoke_fixture --init-fixture", workbench_contract)
        self.assertIn("--force-init-fixture", workbench_contract)
        self.assertIn("replace_clip", workbench_contract)
        self.assertIn("loses protected editor selectors", workbench_contract)
        self.assertIn("lane-video", workbench_contract)
        self.assertIn("hostMode", workbench_layout_smoke)
        self.assertIn("spa_shell", workbench_layout_smoke)
        self.assertIn("native_direct", workbench_layout_smoke)
        self.assertIn("forbiddenShellSelectors", workbench_layout_smoke)
        self.assertIn("SPA compatibility view must not duplicate native monitor/timeline selectors", workbench_layout_smoke)
        self.assertIn(".wb-transport", workbench_layout_smoke)
        self.assertIn("#btn-play", workbench_layout_smoke)
        self.assertIn("#scrubber", workbench_layout_smoke)
        self.assertIn("前往剪輯工作台", workbench_view)
        for forbidden in (
            "monitor-box",
            "timeline-wrap",
            "clip-video",
            "wb-monitor",
            "wb-timeline",
            "track-lane",
            "lane-video",
        ):
            self.assertNotIn(forbidden, workbench_view)
        self.assertIn("material-map-workspace", material_map_view)
        self.assertIn("mm-contract-paper", material_map_view)
        self.assertIn("mm-graph", material_map_view)
        self.assertIn("素材判斷契約紙", material_map_view)
        self.assertIn("可用區間", material_map_view)
        self.assertIn("粗剪切點", material_map_view)
        self.assertIn("sceneTimeRange", material_map_view)
        self.assertIn("thumbnail_url", material_map_view)
        self.assertIn("img.mm-thumb", views_css)
        self.assertIn("scene.usable_range", route_review_spec)
        self.assertIn("粗剪切點", route_review_spec)
        self.assertIn("backend review/apply", route_review_spec)
        self.assertIn("data-asset-id", material_map_view)
        self.assertIn("data-need-id", material_map_view)
        self.assertIn("selectedEvidence", main_js)
        self.assertIn("keydown", main_js)
        self.assertIn("Enter", main_js)
        self.assertIn("event.key === \" \"", main_js)
        self.assertIn("選擇 Run", app_header)
        self.assertIn("打開資料夾", app_header)
        self.assertIn("list=\"spa-project-paths\"", app_header)
        self.assertIn("datalist id=\"spa-project-paths\"", app_header)
        self.assertIn("data-root", app_header)

    def test_workbench_mockup_keeps_native_editor_shape(self):
        mockup = (Path(__file__).resolve().parent.parent / "dashboard" /
                  "archive" / "design_mockup.html").read_text(encoding="utf-8")

        self.assertIn("--timeline-height: clamp(248px, 25vh, 300px);", mockup)
        self.assertIn("flex: 1 1 calc(100vh - 58px - var(--timeline-height));", mockup)
        self.assertIn("flex: 0 0 var(--timeline-height);", mockup)
        self.assertIn("width: min(100%, 1080px, max(520px, calc((100vh - 444px) * 16 / 9)));", mockup)
        self.assertIn(".source-list {\n      display: grid;\n      gap: 8px;\n      min-height: 0;\n      overflow: auto;", mockup)
        self.assertIn("width: clamp(260px, 15vw, 320px);", mockup)
        self.assertIn("width: clamp(280px, 17vw, 340px);", mockup)
        self.assertIn(".track {\n      height: 38px;", mockup)
        self.assertIn(".lane {\n      position: relative;\n      height: 32px;", mockup)
        self.assertIn(".clip {\n      position: absolute;\n      top: 4px;\n      height: 24px;", mockup)
        self.assertIn(".clip-video::before", mockup)
        self.assertIn('<span class="track-label">影片</span>', mockup)
        self.assertIn('<span class="track-label">字幕</span>', mockup)
        self.assertIn('<span class="track-label">音訊</span>', mockup)
        self.assertIn('<span class="track-label">特效</span>', mockup)
        self.assertIn("點選不同軌道，左側會切換成該軌道可替換內容。", mockup)
        self.assertIn("這裡是黑盒工作檯：主要用來看、換、剪，不展示工程 JSON。", mockup)

    def test_workbench_migration_spec_declares_boundaries_and_phases(self):
        spec = (Path(__file__).resolve().parent.parent / "docs" /
                "construction-guides" / "dashboard" /
                "dashboard-spa-workbench-migration-spec.md").read_text(encoding="utf-8")
        frontend_plan = (Path(__file__).resolve().parent.parent / "docs" /
                         "construction-guides" / "dashboard" /
                         "dashboard-frontend-implementation-plan.md").read_text(encoding="utf-8")
        integration = (Path(__file__).resolve().parent.parent / "docs" /
                       "workbench-dashboard-integration.md").read_text(encoding="utf-8")
        dashboard_readme = (Path(__file__).resolve().parent.parent / "dashboard" /
                            "README.md").read_text(encoding="utf-8")
        start_here = (Path(__file__).resolve().parent.parent / "docs" /
                      "START_HERE_VIDEO_PIPELINE.md").read_text(encoding="utf-8")
        operating_map = (Path(__file__).resolve().parent.parent / "docs" /
                         "video-pipeline-operating-map.md").read_text(encoding="utf-8")

        self.assertIn("Workbench Migration Boundaries", spec)
        self.assertIn("Native Editor Protected Zone", spec)
        self.assertIn("video monitor / playback preview area", spec)
        self.assertIn("four lower timeline tracks", spec)
        self.assertIn("native Workbench route", spec)
        self.assertIn("Dashboard white-box views are imported into the native Workbench slide-over", spec)
        self.assertIn("Mount Dashboard white-box views only in the slide-over module host", spec)
        self.assertIn("Draft Artifact Contract", spec)
        self.assertIn("timeline_patch.json", spec)
        self.assertIn("patched_draft_timeline.json", spec)
        self.assertIn("workbench_handoff.json", spec)
        self.assertIn("Do not migrate by copying mock behavior from material_map_canvas.html", spec)
        self.assertIn("node tools\\workbench_browser_layout_smoke.mjs --artifact-root <run-folder>", spec)
        self.assertIn("native document directly", spec)
        self.assertIn("monitor-box", spec)
        self.assertIn("lane-video", spec)

        for text in (
            "The production Workbench route is now the native single-document app",
            "Dashboard SPA routes are white-box compatibility routes",
            "Keep the native video monitor / playback preview area and the native video/subtitle/audio/effect tracks unchanged",
            "The SPA Workbench view must remain a handoff/redirect surface",
            "node tools\\workbench_browser_layout_smoke.mjs --url http://localhost:8765/workbench",
        ):
            self.assertIn(text, frontend_plan)

        for doc in (integration, dashboard_readme):
            self.assertIn("video monitor / playback preview", doc)
            self.assertIn("video, subtitle, audio, and effect tracks", doc)
            self.assertIn("選擇 Run", doc)
            self.assertIn("打開資料夾", doc)
            self.assertIn("?root=...", doc)
            self.assertIn("tools\\dashboard_server.py", doc)
            self.assertIn("http://localhost:8765/workbench", doc)
            self.assertIn("node tests\\dashboard_spa_render_smoke.mjs", doc)
            self.assertIn("node tools\\workbench_browser_layout_smoke.mjs", doc)
            self.assertIn("Workbench-previewable run folder", doc)
            self.assertIn("monitor-box", doc)
            self.assertIn("lane-video", doc)
            self.assertIn(".tmp/test-temp", doc)

        for doc in (start_here, operating_map):
            self.assertIn("python tools/test_tiers.py --tier workbench", doc)
            self.assertIn("node tools\\workbench_browser_layout_smoke.mjs --artifact-root RUN_DIR", doc)
            self.assertIn("python tools/workbench_frontend_smoke.py --artifact-root RUN_DIR", doc)
            self.assertIn("playback controls", doc)
            self.assertIn("Workbench-previewable run folder", doc)
            self.assertIn("monitor-box", doc)
            self.assertIn("lane-video", doc)
            self.assertIn("Workbench", doc)

    def test_formal_frontend_static_text_is_traditional_chinese(self):
        root = Path(__file__).resolve().parent.parent / "dashboard"
        app_header = (root / "src" / "components" / "AppHeader.js").read_text(encoding="utf-8")
        top_nav = (root / "src" / "components" / "TopNav.js").read_text(encoding="utf-8")
        workbench_view = (root / "src" / "views" / "WorkbenchView.js").read_text(encoding="utf-8")
        main_js = (root / "src" / "main.js").read_text(encoding="utf-8")
        material_view = (root / "src" / "views" / "MaterialMapView.js").read_text(encoding="utf-8")
        native_html = (root / "workbench_native" / "index.html").read_text(encoding="utf-8")

        for text in (
            "影片剪輯工作台",
            "原生 Workbench 已是主頁面",
            "Run folder",
            "單文件架構",
            "前往剪輯工作台",
        ):
            self.assertIn(text, workbench_view)

        self.assertIn("app-workbench", main_js)
        self.assertIn('state.activeView === "workbench"', main_js)

        for text in (
            "影片剪輯室",
            "這支影片的素材",
            "字幕",
            "音樂",
            "這一段想怎麼改？",
            "換個畫面",
            "送出修改",
        ):
            self.assertIn(text, native_html)
        for jargon in (
            "SPEC契約",
            "source_duration_sec",
            "管線現況",
            "鏡頭契約",
            "Brownfield",
            "Human decision",
            "V Pipeline",
        ):
            self.assertNotIn(jargon, native_html)

    def test_static_routes_and_security(self):
        self.start_test_server()
        base_url = f"http://localhost:{self.port}"

        # Try fetching native Workbench home, SPA white-box routes, and legacy dashboard pages.
        html_resp = urllib.request.urlopen(f"{base_url}/").read()
        self.assertIn(b"wb-monitor", html_resp)
        self.assertIn(b"wb-timeline", html_resp)

        dash_resp = urllib.request.urlopen(f"{base_url}/dashboard").read()
        self.assertIn(b"hermes-spa-dashboard", dash_resp)

        material_resp = urllib.request.urlopen(f"{base_url}/material-map").read()
        self.assertIn(b"hermes-spa-dashboard", material_resp)

        workbench_resp = urllib.request.urlopen(f"{base_url}/workbench").read()
        self.assertIn(b"wb-monitor", workbench_resp)
        self.assertIn(b"wb-timeline", workbench_resp)

        main_resp = urllib.request.urlopen(f"{base_url}/src/main.js").read()
        self.assertEqual(main_resp, b"// SPA MAIN")

        css_resp = urllib.request.urlopen(f"{base_url}/src/base.css").read()
        self.assertEqual(css_resp, b"/* SPA CSS */")

        for route in ("/dashboard/legacy", "/dashboard_v1.html", "/dashboard_v1.css", "/dashboard_v1.js"):
            with self.subTest(route=route):
                with self.assertRaises(urllib.error.HTTPError) as cm:
                    urllib.request.urlopen(f"{base_url}{route}")
                self.assertEqual(cm.exception.code, 404)

        archived_dash_resp = urllib.request.urlopen(f"{base_url}/archive/dashboard_v1.html").read()
        self.assertEqual(archived_dash_resp, b"<html>Dashboard HTML</html>")

        # /dashboard is no longer the legacy page.
        self.assertNotEqual(dash_resp, b"<html>Dashboard HTML</html>")

    def test_formal_routes_do_not_serve_mock_prototype(self):
        self.start_test_server()
        base_url = f"http://localhost:{self.port}"

        for route in ("/dashboard", "/material-map"):
            with self.subTest(route=route):
                html = urllib.request.urlopen(f"{base_url}{route}").read().decode("utf-8")
                self.assertIn("hermes-spa-dashboard", html)
                self.assertNotIn("MODE_MOCKS", html)
                self.assertNotIn("material_map_canvas", html)
        for route in ("/", "/workbench"):
            with self.subTest(route=route):
                html = urllib.request.urlopen(f"{base_url}{route}").read().decode("utf-8")
                self.assertIn("wb-monitor", html)
                self.assertIn("wb-timeline", html)
                self.assertNotIn("MODE_MOCKS", html)
                self.assertNotIn("material_map_canvas", html)

    def test_legacy_dashboard_archive_route_and_static_security(self):
        self.start_test_server()
        base_url = f"http://localhost:{self.port}"

        dash_resp = urllib.request.urlopen(f"{base_url}/archive/dashboard_v1.html").read()
        self.assertEqual(dash_resp, b"<html>Dashboard HTML</html>")

        css_resp = urllib.request.urlopen(f"{base_url}/archive/dashboard_v1.css").read()
        self.assertEqual(css_resp, b"/* CSS */")

        # Write a dummy file to artifact root and fetch it via /static/
        dummy_file = self.artifact_root / "final.mp4"
        dummy_file.write_text("dummy video data", encoding="utf-8")

        static_resp = urllib.request.urlopen(f"{base_url}/static/final.mp4").read()
        self.assertEqual(static_resp, b"dummy video data")

        # Test Path Traversal security
        # Try to read file outside the artifact root using relative traversal (../)
        secret_file = Path(self.test_dir).parent / "leak_secret.txt"
        secret_file.write_text("secret_admin_token", encoding="utf-8")

        # The URL /static/../leak_secret.txt should be blocked (403 Forbidden or 404/400)
        try:
            # We must escape the /.. to pass urllib parser but let it hit the server
            req_url = f"{base_url}/static/../leak_secret.txt"
            urllib.request.urlopen(req_url)
            self.fail("Path traversal was not blocked!")
        except urllib.error.HTTPError as e:
            # Code should be 403 or 404
            self.assertIn(e.code, [403, 404, 400])

        # Clean up secret file
        if secret_file.exists():
            secret_file.unlink()

    def test_api_aggregation_resilience(self):
        self.start_test_server()
        base_url = f"http://localhost:{self.port}"

        # 1. Test empty directory - must not crash, should return nulls
        api_resp = urllib.request.urlopen(f"{base_url}/api/artifacts").read()
        data = json.loads(api_resp.decode("utf-8"))
        self.assertEqual(data["profile"], "unknown")
        self.assertIsNone(data["timeline"])
        self.assertIsNone(data["review_report"])
        self.assertEqual(data["workbench"]["mode"], "merged_dashboard_server")
        self.assertIn("tools/dashboard_server.py", data["workbench"]["command"])
        self.assertIn(str(self.artifact_root), data["workbench"]["command"])
        self.assertEqual(data["workbench"]["draft_summary"]["present_count"], 0)
        self.assertFalse(data["workbench"]["draft_artifacts"]["timeline_patch"]["exists"])

        # 2. Test malformed JSON files - must return error message in field, not crash
        (self.artifact_root / "timeline.json").write_text("{invalid json", encoding="utf-8")
        (self.artifact_root / "review_report.json").write_text('{"all_matched": true}', encoding="utf-8")

        api_resp2 = urllib.request.urlopen(f"{base_url}/api/artifacts").read()
        data2 = json.loads(api_resp2.decode("utf-8"))
        
        # timeline has error message
        self.assertIsInstance(data2["timeline"], dict)
        self.assertIn("error", data2["timeline"])
        self.assertIn("Malformed JSON", data2["timeline"]["error"])
        
        # review_report is correct
        self.assertEqual(data2["review_report"], {"all_matched": True})

    def test_control_status_api_returns_frontend_manifest(self):
        self.start_test_server()
        base_url = f"http://localhost:{self.port}"

        (self.artifact_root / "timeline.json").write_text(
            json.dumps([
                {"slot_index": 0, "duration_sec": 2.0},
                {"slot_index": 1, "duration_sec": 3.5, "window_quality_fallback": True},
            ]),
            encoding="utf-8",
        )
        (self.artifact_root / "final.mp4").write_bytes(b"fake")
        (self.artifact_root / "timeline_patch.json").write_text(
            json.dumps({"artifact_role": "timeline_patch", "version": 1, "patches": []}),
            encoding="utf-8",
        )
        (self.artifact_root / "workbench_review_report.json").write_text(
            json.dumps({"artifact_role": "workbench_review_report"}),
            encoding="utf-8",
        )
        from tools.workbench_handoff import build_handoff
        (self.artifact_root / "workbench_handoff.json").write_text(
            json.dumps(build_handoff(str(self.artifact_root))),
            encoding="utf-8",
        )

        api_resp = urllib.request.urlopen(f"{base_url}/api/control/status").read()
        data = json.loads(api_resp.decode("utf-8"))

        self.assertEqual(set(data), {
            "artifact_role",
            "version",
            "artifact_root",
            "dashboard",
            "workbench",
            "run_layout",
            "final_video",
            "timeline",
            "recommended_next_action",
        })
        self.assertEqual(data["artifact_role"], "frontend_control_status")
        self.assertEqual(data["version"], 1)
        self.assertEqual(data["artifact_root"], str(self.artifact_root.resolve()))
        self.assertEqual(set(data["dashboard"]), {"url", "mode"})
        self.assertEqual(data["dashboard"], {
            "url": "/dashboard",
            "mode": "read_only_review",
        })
        self.assertEqual(set(data["workbench"]), {
            "url",
            "health_url",
            "mode",
            "command",
            "draft_artifacts",
            "draft_summary",
        })
        self.assertEqual(data["workbench"]["url"], "/workbench")
        self.assertEqual(data["workbench"]["health_url"], "/api/workbench/health")
        self.assertEqual(data["workbench"]["mode"], "write_limited_draft_editor")
        self.assertIn("tools/dashboard_server.py", data["workbench"]["command"])
        self.assertEqual(set(data["workbench"]["draft_artifacts"]),
                         set(WORKBENCH_DRAFT_ARTIFACTS))
        self.assertTrue(data["workbench"]["draft_summary"]["agent_ready"])
        self.assertEqual(data["final_video"], {
            "exists": True,
            "path": "final.mp4",
        })
        self.assertEqual(data["timeline"], {
            "slot_count": 2,
            "duration_sec": 5.5,
            "quality_fallback_slots": 1,
        })
        self.assertEqual(data["run_layout"], {
            "exists": False,
            "path": None,
        })
        self.assertEqual(data["recommended_next_action"], "review_workbench_drafts")

    def test_control_and_artifacts_api_expose_run_layout_summary(self):
        self.start_test_server()
        base_url = f"http://localhost:{self.port}"

        for rel in project_workspace.RUN_LAYOUT:
            (self.artifact_root / rel).mkdir(parents=True, exist_ok=True)
        run_layout = project_workspace.build_run_layout(
            self.artifact_root.parent,
            self.artifact_root,
        )
        (self.artifact_root / "run_layout.json").write_text(
            json.dumps(run_layout),
            encoding="utf-8",
        )

        status_resp = urllib.request.urlopen(f"{base_url}/api/control/status").read()
        status = json.loads(status_resp.decode("utf-8"))
        self.assertEqual(status["run_layout"]["artifact_role"], "run_layout")
        self.assertEqual(status["run_layout"]["version"], 1)
        self.assertEqual(status["run_layout"]["path"], "run_layout.json")
        self.assertEqual(status["run_layout"]["folders"]["spec"], "spec")
        self.assertIn("timeline.json", status["run_layout"]["artifact_classes"]["canonical"])
        self.assertTrue(status["run_layout"]["policy"]["official_render_owned_by_backend"])
        self.assertTrue(status["run_layout"]["validation"]["ok"])
        self.assertEqual(status["run_layout"]["validation"]["error_count"], 0)

        artifacts_resp = urllib.request.urlopen(f"{base_url}/api/artifacts").read()
        artifacts = json.loads(artifacts_resp.decode("utf-8"))
        self.assertEqual(artifacts["run_layout"], status["run_layout"])

        (self.artifact_root / "run_layout.json").write_text("{bad", encoding="utf-8")
        status_resp = urllib.request.urlopen(f"{base_url}/api/control/status").read()
        status = json.loads(status_resp.decode("utf-8"))
        self.assertTrue(status["run_layout"]["exists"])
        self.assertEqual(status["run_layout"]["path"], "run_layout.json")
        self.assertIn("error", status["run_layout"])

    def test_control_status_next_action_contract(self):
        self.start_test_server()
        base_url = f"http://localhost:{self.port}"

        api_resp = urllib.request.urlopen(f"{base_url}/api/control/status").read()
        data = json.loads(api_resp.decode("utf-8"))
        self.assertEqual(data["recommended_next_action"], "run_pipeline_or_open_dashboard")
        self.assertFalse(data["final_video"]["exists"])
        self.assertIsNone(data["final_video"]["path"])

        (self.artifact_root / "final.mp4").write_bytes(b"fake")
        api_resp = urllib.request.urlopen(f"{base_url}/api/control/status").read()
        data = json.loads(api_resp.decode("utf-8"))
        self.assertEqual(data["recommended_next_action"], "open_dashboard_or_workbench")

        (self.artifact_root / "timeline_patch.json").write_text(
            json.dumps({"artifact_role": "timeline_patch", "version": 1, "patches": []}),
            encoding="utf-8",
        )
        (self.artifact_root / "workbench_review_report.json").write_text(
            json.dumps({"artifact_role": "workbench_review_report"}),
            encoding="utf-8",
        )
        from tools.workbench_handoff import build_handoff
        (self.artifact_root / "workbench_handoff.json").write_text(
            json.dumps(build_handoff(str(self.artifact_root))),
            encoding="utf-8",
        )
        api_resp = urllib.request.urlopen(f"{base_url}/api/control/status").read()
        data = json.loads(api_resp.decode("utf-8"))
        self.assertEqual(data["recommended_next_action"], "review_workbench_drafts")

    def test_control_workbench_health_reports_merged_runtime(self):
        self.start_test_server()
        base_url = f"http://localhost:{self.port}"

        api_resp = urllib.request.urlopen(f"{base_url}/api/control/workbench-health").read()
        data = json.loads(api_resp.decode("utf-8"))

        self.assertEqual(data["url"], "/api/workbench/health")
        self.assertIn("ok", data)
        self.assertIn("status", data)
        self.assertTrue(data["ok"])
        self.assertEqual(data["status"], "ok")

    def test_workbench_draft_artifact_status_is_read_only_and_hashes_present_files(self):
        self.start_test_server()
        base_url = f"http://localhost:{self.port}"

        (self.artifact_root / "preview_timeline.json").write_text(
            json.dumps({"artifact_role": "preview_timeline", "clips": []}),
            encoding="utf-8",
        )
        (self.artifact_root / "workbench_revision_request.json").write_text(
            json.dumps({
                "artifact_role": "workbench_revision_request",
                "issues": [{"description": "ending is weak"}],
                "next_action": "open_workbench_for_preview_revision",
            }),
            encoding="utf-8",
        )
        timeline_patch = {"patches": [{"op": "set_duration", "clip_id": "c1", "duration_sec": 2.5}]}
        contract_patch = {"patches": [{"op": "sync_clip", "clip_id": "c1"}]}
        (self.artifact_root / "timeline_patch.json").write_text(
            json.dumps(timeline_patch),
            encoding="utf-8",
        )
        (self.artifact_root / "workbench_contract_patch.json").write_text(
            json.dumps(contract_patch),
            encoding="utf-8",
        )
        (self.artifact_root / "timeline.json").write_text("[]", encoding="utf-8")

        api_resp = urllib.request.urlopen(f"{base_url}/api/artifacts").read()
        data = json.loads(api_resp.decode("utf-8"))

        drafts = data["workbench"]["draft_artifacts"]
        self.assertTrue(drafts["preview_timeline"]["exists"])
        self.assertTrue(drafts["workbench_revision_request"]["exists"])
        self.assertTrue(drafts["timeline_patch"]["exists"])
        self.assertTrue(drafts["workbench_contract_patch"]["exists"])
        self.assertFalse(drafts["patched_draft_timeline"]["exists"])
        self.assertEqual(drafts["preview_timeline"]["path"], "preview_timeline.json")
        self.assertEqual(drafts["workbench_revision_request"]["path"], "workbench_revision_request.json")
        self.assertEqual(drafts["timeline_patch"]["path"], "timeline_patch.json")
        self.assertEqual(drafts["workbench_contract_patch"]["path"], "workbench_contract_patch.json")
        self.assertGreater(drafts["timeline_patch"]["size_bytes"], 0)
        self.assertRegex(drafts["timeline_patch"]["sha256"], r"^[0-9a-f]{64}$")

        summary = data["workbench"]["draft_summary"]
        self.assertEqual(summary["present_count"], 4)
        self.assertEqual(
            summary["revision_next_action"],
            "open_workbench_for_preview_revision",
        )
        self.assertEqual(summary["timeline_edits"], 1)
        self.assertEqual(summary["contract_edits"], 1)

        status_resp = urllib.request.urlopen(f"{base_url}/api/control/status").read()
        status = json.loads(status_resp.decode("utf-8"))
        self.assertEqual(
            status["recommended_next_action"],
            "open_workbench_for_preview_revision",
        )
        self.assertFalse(summary["has_handoff"])
        self.assertFalse(summary["has_review_report"])
        self.assertFalse(summary["agent_ready"])

        self.assertFalse((self.artifact_root / "final.mp4").exists())

    def test_workbench_agent_ready_requires_handoff_and_review_report(self):
        self.start_test_server()
        base_url = f"http://localhost:{self.port}"

        (self.artifact_root / "timeline_patch.json").write_text(
            json.dumps({"artifact_role": "timeline_patch", "version": 1,
                        "patches": [{"op": "replace_clip"}]}),
            encoding="utf-8",
        )
        (self.artifact_root / "patched_draft_timeline.json").write_text(
            json.dumps({"artifact_role": "patched_draft_timeline", "plan": []}),
            encoding="utf-8",
        )
        from tools.workbench_handoff import build_handoff
        (self.artifact_root / "workbench_handoff.json").write_text(
            json.dumps(build_handoff(str(self.artifact_root))),
            encoding="utf-8",
        )
        api_resp = urllib.request.urlopen(f"{base_url}/api/artifacts").read()
        data = json.loads(api_resp.decode("utf-8"))
        summary = data["workbench"]["draft_summary"]
        self.assertTrue(summary["has_handoff"])
        self.assertFalse(summary["has_review_report"])
        self.assertFalse(summary["agent_ready"])
        self.assertTrue(summary["handoff_validation"]["ok"])

        (self.artifact_root / "workbench_review_report.json").write_text(
            json.dumps({"artifact_role": "workbench_review_report"}),
            encoding="utf-8",
        )
        (self.artifact_root / "workbench_handoff.json").write_text(
            json.dumps(build_handoff(str(self.artifact_root))),
            encoding="utf-8",
        )
        api_resp = urllib.request.urlopen(f"{base_url}/api/artifacts").read()
        data = json.loads(api_resp.decode("utf-8"))
        summary = data["workbench"]["draft_summary"]
        self.assertTrue(summary["has_handoff"])
        self.assertTrue(summary["has_review_report"])
        self.assertTrue(summary["agent_ready"])
        self.assertTrue(summary["handoff_validation"]["ok"])

    def test_workbench_agent_ready_requires_valid_handoff(self):
        self.start_test_server()
        base_url = f"http://localhost:{self.port}"

        (self.artifact_root / "workbench_handoff.json").write_text(
            json.dumps({
                "artifact_role": "workbench_handoff",
                "version": 1,
                "artifacts": {"timeline_patch": "timeline_patch.json"},
                "artifact_details": {
                    "timeline_patch": {
                        "path": "timeline_patch.json",
                        "size_bytes": 1,
                        "sha256": "0" * 64,
                    }
                },
            }),
            encoding="utf-8",
        )
        (self.artifact_root / "workbench_review_report.json").write_text(
            json.dumps({"artifact_role": "workbench_review_report"}),
            encoding="utf-8",
        )

        api_resp = urllib.request.urlopen(f"{base_url}/api/artifacts").read()
        data = json.loads(api_resp.decode("utf-8"))
        summary = data["workbench"]["draft_summary"]

        self.assertTrue(summary["has_handoff"])
        self.assertTrue(summary["has_review_report"])
        self.assertFalse(summary["handoff_validation"]["ok"])
        self.assertFalse(summary["agent_ready"])

    def test_timeline_and_subtitles_normalization(self):
        self.start_test_server()
        base_url = f"http://localhost:{self.port}"

        # 1. Create a dummy timeline.json with missing start/end times
        timeline_data = [
            {"segment": 1, "duration_sec": 3.5, "source": "video1.mp4", "role": "opening_role"},
            {"segment": 2, "duration_sec": 2.0, "source": "video2.mp4", "role": "beat_role"}
        ]
        (self.artifact_root / "timeline.json").write_text(json.dumps(timeline_data), encoding="utf-8")

        # 2. Create a dummy review_report.json with semantic drift and failed slots
        report_data = {
            "semantic_alignment": [
                {"segment": 1, "status": "drift", "reason": "out of sync"},
                {"segment": 2, "status": "matched"}
            ],
            "slot_render_check": {
                "failed_slots": [1]
            }
        }
        (self.artifact_root / "review_report.json").write_text(json.dumps(report_data), encoding="utf-8")

        # 3. Create a dummy SRT file
        srt_content = """1
00:00:01,000 --> 00:00:04,500
Hello World

2
00:00:04,500 --> 00:00:06,500
Second subtitle
"""
        (self.artifact_root / "review_subtitles.srt").write_text(srt_content, encoding="utf-8")

        # Fetch /api/artifacts
        api_resp = urllib.request.urlopen(f"{base_url}/api/artifacts").read()
        data = json.loads(api_resp.decode("utf-8"))

        # Verify timeline_slots normalized correctly
        slots = data["timeline_slots"]
        self.assertEqual(len(slots), 2)
        # Slot 0
        self.assertEqual(slots[0]["slot_index"], 0)
        self.assertEqual(slots[0]["start_sec"], 0.0)
        self.assertEqual(slots[0]["duration_sec"], 3.5)
        self.assertEqual(slots[0]["end_sec"], 3.5)
        self.assertEqual(slots[0]["status"], "drift")

        # Slot 1
        self.assertEqual(slots[1]["slot_index"], 1)
        self.assertEqual(slots[1]["start_sec"], 3.5)
        self.assertEqual(slots[1]["duration_sec"], 2.0)
        self.assertEqual(slots[1]["end_sec"], 5.5)
        self.assertEqual(slots[1]["status"], "render_failed")

        # Verify issues extracted
        issues = data["issues"]
        self.assertTrue(len(issues) >= 2)
        
        types = [iss["type"] for iss in issues]
        self.assertIn("semantic", types)
        self.assertIn("render", types)

        # Verify subtitles parsed
        subtitles = data["subtitles"]
        self.assertEqual(len(subtitles), 2)
        self.assertEqual(subtitles[0]["start_sec"], 1.0)
        self.assertEqual(subtitles[0]["end_sec"], 4.5)
        self.assertEqual(subtitles[0]["text"], "Hello World")

    def test_api_available_materials(self):
        self.start_test_server()
        base_url = f"http://localhost:{self.port}"

        # 1. Create a dummy materials directory and files
        materials_dir = self.artifact_root / "materials"
        materials_dir.mkdir(exist_ok=True)
        (materials_dir / "test_clip.mp4").write_text("mp4", encoding="utf-8")
        (materials_dir / "test_img.png").write_text("png", encoding="utf-8")
        (materials_dir / "random.txt").write_text("txt", encoding="utf-8") # should be ignored

        # 2. Write project_material_map.json
        pmap_data = {
            "assets": [
                {
                    "source": "materials/mapped_clip.mp4",
                    "asset_type": "video"
                }
            ]
        }
        (self.artifact_root / "project_material_map.json").write_text(json.dumps(pmap_data), encoding="utf-8")

        # Fetch materials API
        url = f"{base_url}/api/available_materials?root={urllib.parse.quote(str(self.artifact_root))}"
        resp = urllib.request.urlopen(url).read()
        materials = json.loads(resp.decode("utf-8"))

        names = [m["name"] for m in materials]
        self.assertIn("test_clip.mp4", names)
        self.assertIn("test_img.png", names)
        self.assertIn("mapped_clip.mp4", names)
        self.assertNotIn("random.txt", names)

    def test_write_endpoints_are_disabled_and_do_not_mutate_artifacts(self):
        self.start_test_server()
        base_url = f"http://localhost:{self.port}"

        tb_data = {
            "clips": [
                {
                    "segment": 1,
                    "source_path": "old_video.mp4",
                    "duration_sec": 3.0
                }
            ]
        }
        tb_path = self.artifact_root / "timeline_build.json"
        tb_path.write_text(json.dumps(tb_data), encoding="utf-8")

        t_data = [
            {
                "segment": 1,
                "source": "old_video.mp4",
                "duration_sec": 3.0
            }
        ]
        timeline_path = self.artifact_root / "timeline.json"
        timeline_path.write_text(json.dumps(t_data), encoding="utf-8")

        contract_path = self.artifact_root / "segment_contract.json"
        contract_data = {"music": {"source": "existing"}}
        contract_path.write_text(json.dumps(contract_data), encoding="utf-8")

        bgm_source = self.artifact_root / "candidate_bgm.mp3"
        bgm_source.write_bytes(b"not-real-audio")

        endpoints = [
            ("/api/swap_asset", {
                "root": str(self.artifact_root),
                "segment": 1,
                "source_path": "new_awesome_clip.mp4"
            }),
            ("/api/update_clip", {
                "root": str(self.artifact_root),
                "segment": 1,
                "duration": 5.5
            }),
            ("/api/save_review_settings", {
                "root": str(self.artifact_root),
                "aspect_ratio": "9:16",
                "color_lut": "warm",
                "playback_speed": 1.5,
                "bgm_volume": 80
            }),
            ("/api/swap_bgm", {
                "root": str(self.artifact_root),
                "bgm_path": str(bgm_source)
            }),
        ]

        for endpoint, payload in endpoints:
            req = urllib.request.Request(
                f"{base_url}{endpoint}",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with self.assertRaises(urllib.error.HTTPError) as cm:
                urllib.request.urlopen(req)
            self.assertEqual(cm.exception.code, 405)

        self.assertEqual(json.loads(tb_path.read_text(encoding="utf-8")), tb_data)
        self.assertEqual(json.loads(timeline_path.read_text(encoding="utf-8")), t_data)
        self.assertEqual(json.loads(contract_path.read_text(encoding="utf-8")), contract_data)
        self.assertFalse((self.artifact_root / "review_settings.json").exists())
        self.assertFalse((self.artifact_root / "bgm.mp3").exists())

    def test_control_promote_records_request_without_mutating_canonical_artifacts(self):
        self.start_test_server()
        base_url = f"http://localhost:{self.port}"

        timeline_path = self.artifact_root / "timeline.json"
        contract_path = self.artifact_root / "segment_contract.json"
        packet_path = self.artifact_root / "effect_revision_packet.json"
        timeline_data = {"artifact_role": "timeline", "plan": [{"segment": 1, "duration_sec": 3.0}]}
        contract_data = {"segments": [{"segment_id": "seg1", "duration_sec": 3.0}]}
        patched_timeline = {"artifact_role": "patched_draft_timeline", "plan": [{"segment": 1, "duration_sec": 5.0}]}
        contract_patch = {
            "artifact_role": "workbench_contract_patch",
            "base_contract_ref": "segment_contract.json",
            "changes": [{"op": "segment_duration_suggestion", "segment": "seg1", "to": {"requested_duration_sec": 5.0}}],
        }
        timeline_path.write_text(json.dumps(timeline_data), encoding="utf-8")
        contract_path.write_text(json.dumps(contract_data), encoding="utf-8")
        packet_path.write_text(json.dumps({"artifact_role": "revision_packet"}), encoding="utf-8")
        (self.artifact_root / "patched_draft_timeline.json").write_text(json.dumps(patched_timeline), encoding="utf-8")
        (self.artifact_root / "workbench_contract_patch.json").write_text(json.dumps(contract_patch), encoding="utf-8")

        req = urllib.request.Request(
            f"{base_url}/api/control/promote?root={urllib.parse.quote(str(self.artifact_root))}",
            data=b"{}",
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        payload = json.loads(urllib.request.urlopen(req).read().decode("utf-8"))

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["status"], "pending_agent_review")
        self.assertEqual(payload["outputs"]["promotion_request"], "workbench_promotion_request.json")
        self.assertEqual(json.loads(timeline_path.read_text(encoding="utf-8")), timeline_data)
        self.assertEqual(json.loads(contract_path.read_text(encoding="utf-8")), contract_data)
        self.assertTrue(packet_path.is_file())
        request_payload = json.loads((self.artifact_root / "workbench_promotion_request.json").read_text(encoding="utf-8"))
        self.assertEqual(request_payload["artifact_role"], "workbench_promotion_request")
        self.assertEqual(request_payload["status"], "pending_agent_review")
        self.assertIn("patched_draft_timeline.json", request_payload["requested_artifacts"])
        self.assertIn("workbench_contract_patch.json", request_payload["requested_artifacts"])

    def test_merged_workbench_patch_writes_only_draft_artifacts(self):
        self.start_test_server()
        base_url = f"http://localhost:{self.port}"

        media = self.artifact_root / "clip.mp4"
        media.write_bytes(b"0123456789" * 100)
        (self.artifact_root / "timeline.json").write_text(json.dumps({
            "plan": [
                {
                    "slot_index": 0,
                    "segment": 1,
                    "source": str(media),
                    "slot_dur": 2.0,
                    "extract_start": 0.0,
                    "extract_dur": 2.0,
                }
            ]
        }), encoding="utf-8")
        (self.artifact_root / "project_material_map.json").write_text(json.dumps({
            "artifact_role": "project_material_map",
            "assets": [
                {
                    "asset_id": "a0",
                    "asset_type": "video",
                    "source": str(media),
                    "duration_sec": 10.0,
                    "scenes": [{"start": 0.0, "end": 2.0, "caption": "original"}],
                }
            ],
        }), encoding="utf-8")
        before_timeline = (self.artifact_root / "timeline.json").read_text(encoding="utf-8")
        before_map = (self.artifact_root / "project_material_map.json").read_text(encoding="utf-8")

        patch = {
            "artifact_role": "timeline_patch",
            "version": 1,
            "base_timeline_ref": "timeline.json",
            "patches": [
                {
                    "op": "set_duration",
                    "slot_index": 0,
                    "after": {"duration_sec": 3.0},
                }
            ],
            "diagnostics": [],
        }
        req = urllib.request.Request(
            f"{base_url}/api/workbench/patch",
            data=json.dumps(patch).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        payload = json.loads(urllib.request.urlopen(req).read().decode("utf-8"))

        self.assertTrue(payload["ok"])
        self.assertEqual(set(payload["written"]), {
            "timeline_patch.json",
            "patched_draft_timeline.json",
            "preview_timeline.json",
        })
        self.assertEqual((self.artifact_root / "timeline.json").read_text(encoding="utf-8"), before_timeline)
        self.assertEqual((self.artifact_root / "project_material_map.json").read_text(encoding="utf-8"), before_map)

    def test_dashboard_server_hosts_merged_workbench_runtime(self):
        self.start_test_server()
        base_url = f"http://localhost:{self.port}"

        (self.artifact_root / "timeline.json").write_text(json.dumps({"plan": []}), encoding="utf-8")

        health = json.loads(urllib.request.urlopen(
            f"{base_url}/api/workbench/health"
        ).read().decode("utf-8"))
        self.assertEqual(health["artifact_role"], "workbench_health")
        self.assertEqual(health["status"], "ok")
        self.assertTrue(health["write_limited"])

        preview = json.loads(urllib.request.urlopen(
            f"{base_url}/api/workbench/preview-timeline"
        ).read().decode("utf-8"))
        self.assertEqual(preview["artifact_role"], "preview_timeline")

    def test_material_map_review_route_uses_clean_non_mock_page(self):
        self.start_test_server()
        base_url = f"http://localhost:{self.port}"

        html = urllib.request.urlopen(f"{base_url}/material-map").read().decode("utf-8")

        self.assertIn("hermes-spa-dashboard", html)
        self.assertNotIn("MODE_MOCKS", html)

    def test_material_map_view_api_normalizes_real_artifacts(self):
        self.start_test_server()
        base_url = f"http://localhost:{self.port}"

        (self.artifact_root / "video_intent.json").write_text(json.dumps({
            "artifact_role": "video_intent",
            "entry_path": "material-first",
            "route": "material_map_lifecycle",
            "video_type": "graduation_recap",
            "audience": "students and families",
            "goal": "make a recap",
        }), encoding="utf-8")
        (self.artifact_root / "reviewed_project_material_map.json").write_text(json.dumps({
            "artifact_role": "project_material_map",
            "assets": [
                {
                    "asset_id": "asset_real_1",
                    "asset_type": "video",
                    "source": "materials/ceremony.mp4",
                    "duration_sec": 8,
                    "scenes": [
                        {
                            "caption": "award ceremony",
                            "thumbnail_path": "thumbs/ceremony.jpg",
                            "usable_range": {"start": 1.0, "end": 6.5},
                            "start_sec": 1.25,
                            "duration_sec": 4.0,
                            "visual_family": "ceremony",
                            "angle_scale": "wide",
                            "action_family": "award",
                            "subject": "students",
                            "satisfies": [{"need_id": "nd_ceremony", "status": "accepted"}],
                        }
                    ],
                },
                {
                    "asset_id": "asset_real_2",
                    "asset_type": "photo",
                    "source": "materials/group.jpg",
                    "poster": "thumbs/group.jpg",
                    "scenes": [
                        {
                            "caption": "group photo fallback thumbnail",
                            "satisfies": [{"need_id": "nd_ceremony", "status": "candidate"}],
                        }
                    ],
                }
            ],
            "needs": [
                {
                    "need_id": "nd_ceremony",
                    "purpose": "show ceremony milestone",
                    "count": 1,
                    "must_have": True,
                    "fallback_options": ["replace_clip"],
                }
            ],
        }), encoding="utf-8")
        (self.artifact_root / "fresh_material_delta.json").write_text(json.dumps({
            "artifact_role": "material_delta",
            "ready_for_build": True,
            "deltas": [
                {
                    "need_id": "nd_ceremony",
                    "outcome": "covered",
                    "route": "none",
                    "reason": "1 accepted meet required 1",
                    "evidence": {"accepted": 1, "candidate": 0, "rejected": 0},
                }
            ],
            "summary": {"covered": 1, "thin": 0, "missing": 0, "excess": 0},
        }), encoding="utf-8")

        payload = json.loads(urllib.request.urlopen(
            f"{base_url}/api/material-map-view?root={urllib.parse.quote(str(self.artifact_root))}"
        ).read().decode("utf-8"))

        self.assertEqual(payload["artifact_role"], "material_map_dashboard_view")
        self.assertEqual(payload["entry_path"], "material-first")
        self.assertEqual(payload["route"], "material_map_lifecycle")
        self.assertEqual(payload["intent"]["video_type"], "graduation_recap")
        self.assertEqual(payload["intent"]["goal"], "make a recap")
        self.assertEqual(payload["intent"]["expected_outputs"], [])
        self.assertTrue(payload["ready_for_build"])
        self.assertEqual(payload["stats"]["assets"], 2)
        self.assertEqual(payload["stats"]["accepted_edges"], 1)
        self.assertEqual(payload["assets"][0]["asset_id"], "asset_real_1")
        self.assertEqual(payload["assets"][0]["scenes"][0]["need_ids"], ["nd_ceremony"])
        self.assertEqual(payload["assets"][0]["scenes"][0]["satisfies"][0]["status"], "accepted")
        self.assertEqual(payload["assets"][0]["scenes"][0]["thumbnail"], "thumbs/ceremony.jpg")
        self.assertIn("/static/thumbs/ceremony.jpg?root=", payload["assets"][0]["scenes"][0]["thumbnail_url"])
        self.assertEqual(payload["assets"][0]["scenes"][0]["usable_range"], {"start": 1.0, "end": 6.5})
        self.assertEqual(payload["assets"][0]["scenes"][0]["start_sec"], 1.25)
        self.assertEqual(payload["assets"][0]["scenes"][0]["duration_sec"], 4.0)
        self.assertEqual(payload["assets"][1]["scenes"][0]["thumbnail"], "thumbs/group.jpg")
        self.assertIn("/static/thumbs/group.jpg?root=", payload["assets"][1]["scenes"][0]["thumbnail_url"])
        self.assertEqual(payload["needs"][0]["outcome"], "covered")
        stages_by_label = {stage["label"]: stage for stage in payload["stages"]}
        self.assertEqual(stages_by_label["Material Ingest"]["status"], "missing")
        self.assertEqual(stages_by_label["Material Map"]["artifact"], "reviewed_project_material_map.json")
        self.assertEqual(stages_by_label["Coverage Delta"]["artifact"], "fresh_material_delta.json")
        self.assertEqual(stages_by_label["Coverage Delta"]["status"], "present")


if __name__ == "__main__":
    unittest.main()
