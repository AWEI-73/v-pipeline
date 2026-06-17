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

from tools.dashboard_server import detect_profile, DashboardHandler


class DashboardServerTest(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for artifacts
        self.test_dir = tempfile.mkdtemp()
        self.artifact_root = Path(self.test_dir)
        
        # Create a temporary directory for dashboard UI
        self.dashboard_dir_temp = tempfile.mkdtemp()
        self.dashboard_dir = Path(self.dashboard_dir_temp)
        
        # Create dummy HTML/CSS/JS files
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

    def test_static_routes_and_security(self):
        self.start_test_server()
        base_url = f"http://localhost:{self.port}"

        # Try fetching dashboard pages
        html_resp = urllib.request.urlopen(f"{base_url}/").read()
        self.assertEqual(html_resp, b"<html>Dashboard HTML</html>")

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
