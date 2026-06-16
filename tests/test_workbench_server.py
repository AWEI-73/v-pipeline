import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from http.server import HTTPServer
from pathlib import Path

from tools.workbench_server import WorkbenchHandler


def _write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


class WorkbenchServerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.media = self.root / "clip.mp4"
        self.media.write_bytes(b"0123456789" * 100)
        _write_json(self.root / "timeline.json", {
            "plan": [
                {
                    "slot_index": 0,
                    "segment": 1,
                    "source": str(self.media),
                    "slot_dur": 2.0,
                    "extract_start": 0.0,
                    "extract_dur": 2.0,
                }
            ]
        })
        _write_json(self.root / "project_material_map.json", {
            "artifact_role": "project_material_map",
            "version": 1,
            "assets": [
                {
                    "asset_id": "a0",
                    "asset_type": "video",
                    "source": str(self.media),
                    "duration_sec": 10.0,
                }
            ],
        })

        class BoundHandler(WorkbenchHandler):
            artifact_root = self.root
            base_url = "http://127.0.0.1:0"

        self.handler_class = BoundHandler
        self.server = HTTPServer(("127.0.0.1", 0), self.handler_class)
        self.port = self.server.server_port
        self.handler_class.base_url = f"http://127.0.0.1:{self.port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.tmp.cleanup()

    def url(self, path: str) -> str:
        return f"http://127.0.0.1:{self.port}{path}"

    def test_get_preview_timeline_and_workbench_html(self):
        html = urllib.request.urlopen(self.url("/workbench")).read().decode("utf-8")
        self.assertIn("Hermes Native Preview Workbench", html)

        payload = json.loads(urllib.request.urlopen(
            self.url("/api/workbench/preview-timeline")
        ).read().decode("utf-8"))
        self.assertEqual(payload["artifact_role"], "preview_timeline")
        self.assertEqual(len(payload["clips"]), 1)
        self.assertIn("/media?src=", payload["clips"][0]["src_url"])

    def test_media_serves_only_allowlisted_sources_with_range_support(self):
        src = urllib.parse.quote(str(self.media), safe="")
        req = urllib.request.Request(
            self.url(f"/media?src={src}"),
            headers={"Range": "bytes=0-4"},
        )
        resp = urllib.request.urlopen(req)
        self.assertEqual(resp.status, 206)
        self.assertEqual(resp.read(), b"01234")

        outside = urllib.parse.quote(str(self.root / "other.mp4"), safe="")
        with self.assertRaises(urllib.error.HTTPError) as cm:
            urllib.request.urlopen(self.url(f"/media?src={outside}"))
        self.assertEqual(cm.exception.code, 403)

    def test_post_patch_writes_only_workbench_artifacts(self):
        before_timeline = (self.root / "timeline.json").read_text(encoding="utf-8")
        before_map = (self.root / "project_material_map.json").read_text(encoding="utf-8")
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
            self.url("/api/workbench/patch"),
            data=json.dumps(patch).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        result = json.loads(urllib.request.urlopen(req).read().decode("utf-8"))
        self.assertTrue(result["ok"])
        self.assertEqual(set(result["written"]), {
            "timeline_patch.json",
            "patched_draft_timeline.json",
            "preview_timeline.json",
        })
        self.assertEqual((self.root / "timeline.json").read_text(encoding="utf-8"), before_timeline)
        self.assertEqual((self.root / "project_material_map.json").read_text(encoding="utf-8"), before_map)

    def test_invalid_patch_writes_nothing(self):
        patch = {
            "artifact_role": "timeline_patch",
            "version": 1,
            "base_timeline_ref": "timeline.json",
            "patches": [
                {
                    "op": "set_duration",
                    "slot_index": 0,
                    "after": {"duration_sec": -1},
                }
            ],
            "diagnostics": [],
        }
        req = urllib.request.Request(
            self.url("/api/workbench/patch"),
            data=json.dumps(patch).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with self.assertRaises(urllib.error.HTTPError) as cm:
            urllib.request.urlopen(req)
        self.assertEqual(cm.exception.code, 422)
        self.assertFalse((self.root / "timeline_patch.json").exists())
        self.assertFalse((self.root / "patched_draft_timeline.json").exists())


if __name__ == "__main__":
    unittest.main()
