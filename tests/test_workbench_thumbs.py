import json
import tempfile
import unittest
from pathlib import Path

from tools.workbench_thumbs import THUMBS_DIRNAME, build_thumbnails


def _write(root: Path, name: str, payload) -> None:
    (root / name).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _make_root(tmp: str) -> Path:
    root = Path(tmp)
    vid = root / "clip.mp4"
    img = root / "still.png"
    vid.write_bytes(b"\x00")
    img.write_bytes(b"\x00")
    _write(root, "timeline.json", {"plan": [
        {"slot_index": 0, "source": str(vid), "slot_dur": 3.0, "extract_start": 1.2, "extract_dur": 3.0},
        {"slot_index": 1, "source": str(img), "slot_dur": 2.0},
    ]})
    _write(root, "project_material_map.json", {
        "artifact_role": "project_material_map", "version": 1,
        "assets": [
            {"asset_id": "a0", "asset_type": "video", "source": str(vid), "duration_sec": 30.0},
            {"asset_id": "a1", "asset_type": "image", "source": str(img), "duration_sec": 0.0},
        ], "needs": []})
    return root


class FakeRunner:
    def __init__(self):
        self.calls = []

    def __call__(self, source, start_sec, out_path):
        self.calls.append({"source": source, "start": start_sec, "out": out_path})
        Path(out_path).write_bytes(b"\xff\xd8\xff")  # pretend ffmpeg wrote a JPEG
        return True


BASE = "http://localhost:8770"


class ThumbnailsTest(unittest.TestCase):
    def test_video_thumb_built_image_passthrough(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            runner = FakeRunner()
            m = build_thumbnails(str(root), BASE, runner=runner)
            self.assertEqual(m["artifact_role"], "workbench_thumbnails")
            # video slot 0 -> a /media url under workbench_thumbs
            self.assertIn("0", m["thumbnails"])
            self.assertIn("/media?src=", m["thumbnails"]["0"])
            self.assertIn(THUMBS_DIRNAME, m["thumbnails"]["0"])
            # image slot 1 -> its own src_url (no ffmpeg)
            self.assertIn("1", m["thumbnails"])
            self.assertNotIn(THUMBS_DIRNAME, m["thumbnails"]["1"])
            # ffmpeg runner called once (the single video clip)
            self.assertEqual(len(runner.calls), 1)
            self.assertAlmostEqual(runner.calls[0]["start"], 1.2)
            self.assertTrue((root / THUMBS_DIRNAME / "slot-0.jpg").exists())

    def test_thumbnails_are_cached(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            runner = FakeRunner()
            build_thumbnails(str(root), BASE, runner=runner)
            build_thumbnails(str(root), BASE, runner=runner)  # second call uses cache
            self.assertEqual(len(runner.calls), 1)

    def test_failed_extraction_is_omitted_not_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            m = build_thumbnails(str(root), BASE, runner=lambda s, t, o: False)
            self.assertNotIn("0", m["thumbnails"])  # video omitted
            self.assertIn("1", m["thumbnails"])      # image still passes through

    def test_canonical_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            before = (root / "timeline.json").read_text(encoding="utf-8")
            build_thumbnails(str(root), BASE, runner=FakeRunner())
            self.assertEqual((root / "timeline.json").read_text(encoding="utf-8"), before)


if __name__ == "__main__":
    unittest.main()
