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
    detect_profile,
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
        (self.dashboard_dir / "index.html").write_text("<html>Control Index</html>", encoding="utf-8")
        (self.dashboard_dir / "index.css").write_text("/* INDEX CSS */", encoding="utf-8")
        (self.dashboard_dir / "index.js").write_text("// INDEX JS", encoding="utf-8")
        (self.dashboard_dir / "dashboard_v1.html").write_text("<html>Dashboard HTML</html>", encoding="utf-8")
        (self.dashboard_dir / "dashboard_v1.css").write_text("/* CSS */", encoding="utf-8")
        (self.dashboard_dir / "dashboard_v1.js").write_text("// JS", encoding="utf-8")

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

    def test_dashboard_html_has_workbench_entrypoint(self):
        html = (Path(__file__).resolve().parent.parent / "dashboard" /
                "dashboard_v1.html").read_text(encoding="utf-8")
        self.assertIn('id="btn-open-workbench"', html)
        self.assertIn("Workbench", html)

    def test_control_index_declares_dashboard_and_workbench_surfaces(self):
        root = Path(__file__).resolve().parent.parent / "dashboard"
        html = (root / "index.html").read_text(encoding="utf-8")
        js = (root / "index.js").read_text(encoding="utf-8")

        self.assertIn('id="surface-dashboard"', html)
        self.assertIn('id="surface-workbench"', html)
        self.assertIn('id="btn-open-dashboard"', html)
        self.assertIn('id="btn-open-workbench"', html)
        self.assertIn('id="workbench-health"', html)
        self.assertIn('data-field="run-layout"', html)
        self.assertIn("/api/control/status", js)
        self.assertIn("/api/control/workbench-health", js)
        self.assertIn("data.run_layout", js)
        self.assertIn("workbench.draft_summary.agent_ready", js)

    def test_static_routes_and_security(self):
        self.start_test_server()
        base_url = f"http://localhost:{self.port}"

        # Try fetching control shell and dashboard pages
        html_resp = urllib.request.urlopen(f"{base_url}/").read()
        self.assertEqual(html_resp, b"<html>Control Index</html>")

        dash_resp = urllib.request.urlopen(f"{base_url}/dashboard").read()
        self.assertEqual(dash_resp, b"<html>Dashboard HTML</html>")

        index_css_resp = urllib.request.urlopen(f"{base_url}/index.css").read()
        self.assertEqual(index_css_resp, b"/* INDEX CSS */")

        index_js_resp = urllib.request.urlopen(f"{base_url}/index.js").read()
        self.assertEqual(index_js_resp, b"// INDEX JS")

        css_resp = urllib.request.urlopen(f"{base_url}/dashboard_v1.css").read()
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
        self.assertEqual(data["workbench"]["mode"], "external_server")
        self.assertIn("tools/workbench_server.py", data["workbench"]["command"])
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
                {"slot_index": 1, "duration_sec": 3.5},
            ]),
            encoding="utf-8",
        )
        (self.artifact_root / "final.mp4").write_bytes(b"fake")
        (self.artifact_root / "workbench_handoff.json").write_text(
            json.dumps({"artifact_role": "workbench_handoff"}),
            encoding="utf-8",
        )
        (self.artifact_root / "workbench_review_report.json").write_text(
            json.dumps({"artifact_role": "workbench_review_report"}),
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
        self.assertEqual(data["workbench"]["url"], "http://localhost:8770/workbench")
        self.assertEqual(data["workbench"]["health_url"], "http://localhost:8770/api/workbench/health")
        self.assertEqual(data["workbench"]["mode"], "write_limited_draft_editor")
        self.assertIn("tools/workbench_server.py", data["workbench"]["command"])
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

        (self.artifact_root / "workbench_handoff.json").write_text(
            json.dumps({"artifact_role": "workbench_handoff"}),
            encoding="utf-8",
        )
        (self.artifact_root / "workbench_review_report.json").write_text(
            json.dumps({"artifact_role": "workbench_review_report"}),
            encoding="utf-8",
        )
        api_resp = urllib.request.urlopen(f"{base_url}/api/control/status").read()
        data = json.loads(api_resp.decode("utf-8"))
        self.assertEqual(data["recommended_next_action"], "review_workbench_drafts")

    def test_control_workbench_health_proxy_is_structured_when_unreachable(self):
        self.start_test_server()
        base_url = f"http://localhost:{self.port}"

        api_resp = urllib.request.urlopen(f"{base_url}/api/control/workbench-health").read()
        data = json.loads(api_resp.decode("utf-8"))

        self.assertEqual(data["url"], "http://localhost:8770/api/workbench/health")
        self.assertIn("ok", data)
        self.assertIn("status", data)
        if not data["ok"]:
            self.assertIn(data["status"], ["unreachable", "invalid_response"])

    def test_workbench_draft_artifact_status_is_read_only_and_hashes_present_files(self):
        self.start_test_server()
        base_url = f"http://localhost:{self.port}"

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
        self.assertTrue(drafts["timeline_patch"]["exists"])
        self.assertTrue(drafts["workbench_contract_patch"]["exists"])
        self.assertFalse(drafts["patched_draft_timeline"]["exists"])
        self.assertEqual(drafts["timeline_patch"]["path"], "timeline_patch.json")
        self.assertEqual(drafts["workbench_contract_patch"]["path"], "workbench_contract_patch.json")
        self.assertGreater(drafts["timeline_patch"]["size_bytes"], 0)
        self.assertRegex(drafts["timeline_patch"]["sha256"], r"^[0-9a-f]{64}$")

        summary = data["workbench"]["draft_summary"]
        self.assertEqual(summary["present_count"], 2)
        self.assertEqual(summary["timeline_edits"], 1)
        self.assertEqual(summary["contract_edits"], 1)
        self.assertFalse(summary["has_handoff"])
        self.assertFalse(summary["has_review_report"])
        self.assertFalse(summary["agent_ready"])

        self.assertFalse((self.artifact_root / "final.mp4").exists())

    def test_workbench_agent_ready_requires_handoff_and_review_report(self):
        self.start_test_server()
        base_url = f"http://localhost:{self.port}"

        (self.artifact_root / "timeline_patch.json").write_text(
            json.dumps({"patches": [{"op": "replace_clip"}]}),
            encoding="utf-8",
        )
        (self.artifact_root / "workbench_handoff.json").write_text(
            json.dumps({"artifact_role": "workbench_handoff"}),
            encoding="utf-8",
        )
        api_resp = urllib.request.urlopen(f"{base_url}/api/artifacts").read()
        data = json.loads(api_resp.decode("utf-8"))
        summary = data["workbench"]["draft_summary"]
        self.assertTrue(summary["has_handoff"])
        self.assertFalse(summary["has_review_report"])
        self.assertFalse(summary["agent_ready"])

        (self.artifact_root / "workbench_review_report.json").write_text(
            json.dumps({"artifact_role": "workbench_review_report"}),
            encoding="utf-8",
        )
        api_resp = urllib.request.urlopen(f"{base_url}/api/artifacts").read()
        data = json.loads(api_resp.decode("utf-8"))
        summary = data["workbench"]["draft_summary"]
        self.assertTrue(summary["has_handoff"])
        self.assertTrue(summary["has_review_report"])
        self.assertTrue(summary["agent_ready"])

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


if __name__ == "__main__":
    unittest.main()
