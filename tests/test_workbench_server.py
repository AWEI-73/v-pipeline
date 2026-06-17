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
        self.media_b = self.root / "clip_b.mp4"
        self.media_b.write_bytes(b"abcdefghij" * 100)
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
                    "scenes": [{"start": 0.0, "end": 2.0, "caption": "original"}],
                },
                {
                    "asset_id": "b0",
                    "asset_type": "video",
                    "source": str(self.media_b),
                    "duration_sec": 10.0,
                    "scenes": [{"start": 3.0, "end": 6.0, "caption": "replacement"}],
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
        asset = next(a for a in payload["material_assets"] if a["asset_id"] == "b0")
        self.assertEqual(asset["scenes"][0]["start_sec"], 3.0)
        self.assertEqual(asset["scenes"][0]["end_sec"], 6.0)

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

    def test_media_serves_material_browser_assets_not_yet_on_timeline(self):
        src = urllib.parse.quote(str(self.media_b), safe="")
        req = urllib.request.Request(
            self.url(f"/media?src={src}"),
            headers={"Range": "bytes=0-3"},
        )
        resp = urllib.request.urlopen(req)
        self.assertEqual(resp.status, 206)
        self.assertEqual(resp.read(), b"abcd")

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

    def test_malformed_patch_json_returns_structured_error_and_writes_nothing(self):
        req = urllib.request.Request(
            self.url("/api/workbench/patch"),
            data=b"{not-json",
            headers={"Content-Type": "application/json"},
        )
        with self.assertRaises(urllib.error.HTTPError) as cm:
            urllib.request.urlopen(req)
        self.assertEqual(cm.exception.code, 400)
        payload = json.loads(cm.exception.read().decode("utf-8"))
        self.assertIn("error", payload)
        self.assertFalse((self.root / "timeline_patch.json").exists())
        self.assertFalse((self.root / "patched_draft_timeline.json").exists())

    def test_post_replace_clip_patch_writes_draft_not_canonical(self):
        before_timeline = (self.root / "timeline.json").read_text(encoding="utf-8")
        patch = {
            "artifact_role": "timeline_patch",
            "version": 1,
            "base_timeline_ref": "timeline.json",
            "patches": [
                {
                    "op": "replace_clip",
                    "slot_index": 0,
                    "after": {"asset_id": "b0", "scene_index": 0},
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
        draft = json.loads((self.root / "patched_draft_timeline.json").read_text(encoding="utf-8"))
        clip = draft["plan"][0]
        self.assertEqual(clip["scene_id"], "b0:0")
        self.assertEqual(clip["extract_start"], 3.0)
        self.assertEqual(clip["extract_dur"], 3.0)
        self.assertEqual(clip["caption"], "replacement")
        self.assertEqual((self.root / "timeline.json").read_text(encoding="utf-8"), before_timeline)

    def test_sync_contract_writes_only_draft_artifacts(self):
        before_timeline = (self.root / "timeline.json").read_text(encoding="utf-8")
        before_map = (self.root / "project_material_map.json").read_text(encoding="utf-8")
        patch = {
            "artifact_role": "timeline_patch", "version": 1,
            "base_timeline_ref": "timeline.json",
            "patches": [{"op": "set_duration", "slot_index": 0, "after": {"duration_sec": 3.0}}],
            "diagnostics": [],
        }
        req = urllib.request.Request(
            self.url("/api/workbench/sync-contract"),
            data=json.dumps({"patch": patch}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        result = json.loads(urllib.request.urlopen(req).read().decode("utf-8"))
        self.assertTrue(result["ok"])
        self.assertEqual(set(result["written"]),
                         {"workbench_contract_patch.json", "patched_draft_timeline.json"})
        # canonical untouched
        self.assertEqual((self.root / "timeline.json").read_text(encoding="utf-8"), before_timeline)
        self.assertEqual((self.root / "project_material_map.json").read_text(encoding="utf-8"), before_map)
        self.assertFalse((self.root / "segment_contract.json").exists())

    def test_invalid_sync_contract_writes_nothing(self):
        # source window beyond asset bounds -> fail-closed
        patch = {
            "artifact_role": "timeline_patch", "version": 1,
            "base_timeline_ref": "timeline.json",
            "patches": [{"op": "set_source_window", "slot_index": 0,
                         "after": {"source_start_sec": 9.0, "source_duration_sec": 5.0}}],
            "diagnostics": [],
        }
        req = urllib.request.Request(
            self.url("/api/workbench/sync-contract"),
            data=json.dumps({"patch": patch}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with self.assertRaises(urllib.error.HTTPError) as cm:
            urllib.request.urlopen(req)
        self.assertEqual(cm.exception.code, 422)
        self.assertFalse((self.root / "workbench_contract_patch.json").exists())
        self.assertFalse((self.root / "patched_draft_timeline.json").exists())

    def test_stage_media_css_uses_fixed_monitor_box(self):
        css = (Path(__file__).resolve().parent.parent / "dashboard" /
               "workbench_native" / "workbench.css").read_text(encoding="utf-8")
        start = css.index(".wb-monitor img,\n.wb-monitor video")
        block = css[start:css.index("}", start)]
        lines = {line.strip() for line in block.splitlines()}
        self.assertIn("width: 100%;", lines)
        self.assertIn("height: 100%;", lines)
        self.assertIn("object-fit: contain;", block)

    # ------------------------------------------------------------------ #
    # NPE4 editorial runtime tracks (save-all + boundaries)
    # ------------------------------------------------------------------ #
    def _post(self, path, payload):
        req = urllib.request.Request(
            self.url(path), data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"})
        return req

    def _hash(self, name):
        import hashlib
        p = self.root / name
        return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None

    def _valid_save_all(self):
        return {
            "timeline_patch": {"artifact_role": "timeline_patch", "version": 1,
                               "base_timeline_ref": "timeline.json", "diagnostics": [],
                               "patches": [{"op": "set_duration", "slot_index": 0, "after": {"duration_sec": 3.0}}]},
            "audio_cue_patch": {"artifact_role": "audio_cue_patch", "version": 1, "diagnostics": [],
                                "patches": [{"op": "add_cue", "cue_id": "c1",
                                             "after": {"time_sec": 1.0, "cue_type": "impact", "strength": 3}}]},
            "effect_patch": {"artifact_role": "effect_patch", "version": 1, "diagnostics": [],
                             "patches": [{"op": "add_effect", "effect_id": "e1", "after": {
                                 "preset": "flash", "target_slot_index": 0,
                                 "start_sec": 0.0, "duration_sec": 0.5, "intensity": 3}}]},
        }

    def test_M_save_all_writes_only_allowed_artifacts(self):
        result = json.loads(urllib.request.urlopen(
            self._post("/api/workbench/save-all", self._valid_save_all())).read().decode("utf-8"))
        self.assertTrue(result["ok"])
        self.assertEqual(set(result["written"]), {
            "timeline_patch.json", "patched_draft_timeline.json",
            "audio_cue_patch.json", "effect_patch.json", "workbench_handoff.json"})
        self.assertEqual(result["summary"]["audio_cues"], 1)
        self.assertEqual(result["summary"]["effect_intents"], 1)
        handoff = json.loads((self.root / "workbench_handoff.json").read_text(encoding="utf-8"))
        self.assertRegex(handoff["artifact_details"]["timeline_patch"]["sha256"], r"^[0-9a-f]{64}$")

    def test_N_save_all_invalid_layer_writes_nothing(self):
        payload = self._valid_save_all()
        payload["effect_patch"]["patches"][0]["after"]["preset"] = "not_a_preset"  # invalid
        with self.assertRaises(urllib.error.HTTPError) as cm:
            urllib.request.urlopen(self._post("/api/workbench/save-all", payload))
        self.assertEqual(cm.exception.code, 422)
        for n in ("timeline_patch.json", "patched_draft_timeline.json",
                  "audio_cue_patch.json", "effect_patch.json", "workbench_handoff.json"):
            self.assertFalse((self.root / n).exists(), n)

    def test_P_canonical_unchanged_by_hash_after_save_all(self):
        before = {n: self._hash(n) for n in ("timeline.json", "project_material_map.json")}
        urllib.request.urlopen(self._post("/api/workbench/save-all", self._valid_save_all()))
        after = {n: self._hash(n) for n in ("timeline.json", "project_material_map.json")}
        self.assertEqual(before, after)

    def test_Q_static_path_traversal_blocked(self):
        # the /workbench/<rel> static route must reject traversal
        with self.assertRaises(urllib.error.HTTPError) as cm:
            urllib.request.urlopen(self.url("/workbench/..%2Ftimeline.json"))
        self.assertIn(cm.exception.code, (403, 404))

    def test_thumbnails_endpoint_returns_manifest_no_canonical_write(self):
        import hashlib
        before = hashlib.sha256((self.root / "timeline.json").read_bytes()).hexdigest()
        # dummy clip.mp4 makes ffmpeg fail; endpoint must still return 200 + dict
        m = json.loads(urllib.request.urlopen(
            self.url("/api/workbench/thumbnails")).read().decode("utf-8"))
        self.assertEqual(m["artifact_role"], "workbench_thumbnails")
        self.assertIsInstance(m["thumbnails"], dict)
        self.assertEqual(hashlib.sha256((self.root / "timeline.json").read_bytes()).hexdigest(), before)

    def test_media_allowlist_is_cached(self):
        from tools import workbench_server as ws
        key = __import__("os").path.normcase(str(self.root.resolve()))
        ws._ALLOW_CACHE.pop(key, None)
        first = ws._media_allowlist(self.root, self.handler_class.base_url)
        self.assertIn(key, ws._ALLOW_CACHE)
        second = ws._media_allowlist(self.root, self.handler_class.base_url)
        self.assertIs(first, second)  # same cached object, not rebuilt

    def test_proxies_endpoint_returns_manifest_no_canonical_write(self):
        import hashlib
        before = hashlib.sha256((self.root / "timeline.json").read_bytes()).hexdigest()
        # dummy clip.mp4 makes ffmpeg fail; endpoint must still return 200 + dict
        m = json.loads(urllib.request.urlopen(
            self.url("/api/workbench/proxies")).read().decode("utf-8"))
        self.assertEqual(m["artifact_role"], "workbench_proxies")
        self.assertIsInstance(m["proxies"], dict)
        self.assertEqual(hashlib.sha256((self.root / "timeline.json").read_bytes()).hexdigest(), before)

    def test_media_allows_proxy_cache_but_not_outside(self):
        proxy_dir = self.root / "workbench_proxy"
        proxy_dir.mkdir()
        proxy = proxy_dir / "slot-0-test.mp4"
        proxy.write_bytes(b"proxy-video")
        src = urllib.parse.quote(str(proxy), safe="")
        resp = urllib.request.urlopen(self.url(f"/media?src={src}"))
        self.assertEqual(resp.status, 200)
        self.assertEqual(resp.read(), b"proxy-video")

        outside = self.root / "not_proxy.mp4"
        outside.write_bytes(b"nope")
        outside_src = urllib.parse.quote(str(outside), safe="")
        with self.assertRaises(urllib.error.HTTPError) as cm:
            urllib.request.urlopen(self.url(f"/media?src={outside_src}"))
        self.assertEqual(cm.exception.code, 403)

    def test_export_endpoint_passes_effects_flag_to_exporter(self):
        from tools import workbench_server as ws
        calls = []
        old_export = ws.wx.export

        def fake_export(artifact_root, out="workbench_export.mp4", patch=None, **kwargs):
            calls.append({"root": artifact_root, "out": out, "patch": patch, "kwargs": kwargs})
            return {"ok": True, "out": str(self.root / out), "rendered_clips": 1}

        ws.wx.export = fake_export
        try:
            result = json.loads(urllib.request.urlopen(self._post(
                "/api/workbench/export",
                {"patch": None, "effects": True},
            )).read().decode("utf-8"))
        finally:
            ws.wx.export = old_export
        self.assertTrue(result["ok"])
        self.assertEqual(len(calls), 1)
        self.assertIs(calls[0]["kwargs"].get("render_effects"), True)

    def test_export_endpoint_passes_inline_effect_patch_to_exporter(self):
        from tools import workbench_server as ws
        calls = []
        old_export = ws.wx.export
        inline_effect = {
            "artifact_role": "effect_patch",
            "version": 1,
            "diagnostics": [],
            "patches": [{"op": "add_effect", "effect_id": "inline-fx", "after": {
                "preset": "flash", "target_slot_index": 0,
                "start_sec": 0.0, "duration_sec": 0.5, "intensity": 3}}],
        }

        def fake_export(artifact_root, out="workbench_export.mp4", patch=None, **kwargs):
            calls.append({"root": artifact_root, "out": out, "patch": patch, "kwargs": kwargs})
            return {"ok": True, "out": str(self.root / out), "rendered_clips": 1}

        ws.wx.export = fake_export
        try:
            result = json.loads(urllib.request.urlopen(self._post(
                "/api/workbench/export",
                {"patch": None, "effects": True, "effect_patch": inline_effect},
            )).read().decode("utf-8"))
        finally:
            ws.wx.export = old_export
        self.assertTrue(result["ok"])
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["kwargs"].get("effect_patch"), inline_effect)

    def test_subtitle_endpoint_requires_srt_and_writes_only_patch(self):
        (self.root / "review_subtitles.srt").write_text(
            "1\n00:00:00,000 --> 00:00:02,000\nHi\n", encoding="utf-8")
        before_srt = (self.root / "review_subtitles.srt").read_text(encoding="utf-8")
        patch = {"artifact_role": "subtitle_patch", "version": 1, "diagnostics": [],
                 "patches": [{"op": "set_subtitle_text", "subtitle_id": "sub-1", "after": {"text": "Yo"}}]}
        result = json.loads(urllib.request.urlopen(
            self._post("/api/workbench/subtitle-patch", {"patch": patch})).read().decode("utf-8"))
        self.assertEqual(result["written"], ["subtitle_patch.json"])
        # original srt untouched
        self.assertEqual((self.root / "review_subtitles.srt").read_text(encoding="utf-8"), before_srt)


if __name__ == "__main__":
    unittest.main()
