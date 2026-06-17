import json
import tempfile
import unittest
from pathlib import Path

from tools.workbench_proxy import PROXY_DIRNAME, build_proxies


def _write(root: Path, name: str, payload) -> None:
    (root / name).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _make_root(tmp: str) -> Path:
    root = Path(tmp)
    vid = root / "clip.mov"
    img = root / "still.png"
    vid.write_bytes(b"video")
    img.write_bytes(b"image")
    _write(root, "timeline.json", {"plan": [
        {"slot_index": 0, "source": str(vid), "slot_dur": 1.2, "extract_start": 13.4, "extract_dur": 1.2},
        {"slot_index": 1, "source": str(img), "slot_dur": 2.0},
    ]})
    _write(root, "project_material_map.json", {
        "artifact_role": "project_material_map", "version": 1,
        "assets": [
            {"asset_id": "v", "asset_type": "video", "source": str(vid), "duration_sec": 30.0},
            {"asset_id": "i", "asset_type": "image", "source": str(img), "duration_sec": 0.0},
        ],
        "needs": [],
    })
    return root


class FakeProxyRunner:
    def __init__(self):
        self.calls = []

    def __call__(self, source, start_sec, duration_sec, out_path):
        self.calls.append({"source": source, "start": start_sec, "duration": duration_sec, "out": out_path})
        Path(out_path).write_bytes(b"proxy")
        return True


BASE = "http://localhost:8770"


class WorkbenchProxyTest(unittest.TestCase):
    def test_video_proxy_is_trimmed_to_clip_window_and_starts_at_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            runner = FakeProxyRunner()
            m = build_proxies(str(root), BASE, runner=runner)
            self.assertEqual(m["artifact_role"], "workbench_proxies")
            self.assertIn("0", m["proxies"])
            self.assertNotIn("1", m["proxies"])  # images do not need video proxies
            self.assertIn(PROXY_DIRNAME, m["proxies"]["0"]["src_url"])
            self.assertEqual(m["proxies"]["0"]["source_start_sec"], 0.0)
            self.assertEqual(m["proxies"]["0"]["source_duration_sec"], 1.2)
            self.assertAlmostEqual(runner.calls[0]["start"], 13.4)
            self.assertAlmostEqual(runner.calls[0]["duration"], 1.2)

    def test_proxies_are_cached(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            runner = FakeProxyRunner()
            build_proxies(str(root), BASE, runner=runner)
            build_proxies(str(root), BASE, runner=runner)
            self.assertEqual(len(runner.calls), 1)

    def test_failed_proxy_omitted_not_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            m = build_proxies(str(root), BASE, runner=lambda s, st, d, o: False)
            self.assertEqual(m["proxies"], {})

    def test_canonical_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            before = (root / "timeline.json").read_text(encoding="utf-8")
            build_proxies(str(root), BASE, runner=FakeProxyRunner())
            self.assertEqual((root / "timeline.json").read_text(encoding="utf-8"), before)


if __name__ == "__main__":
    unittest.main()
