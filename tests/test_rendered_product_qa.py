import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from video_pipeline_core.rendered_product_qa import build_rendered_product_qa


class RenderedProductQATest(unittest.TestCase):
    def test_missing_rendered_candidate_blocks(self):
        with TemporaryDirectory() as tmp:
            result = build_rendered_product_qa(tmp, tmp)

        self.assertFalse(result["pass"])
        self.assertIn("missing_rendered_candidate", {item["rule"] for item in result["blocking"]})

    def test_candidate_requires_probe_and_frame_evidence(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "final.mp4").write_bytes(b"not a real video")

            result = build_rendered_product_qa(root, root)

            self.assertFalse(result["pass"])
            rules = {item["rule"] for item in result["blocking"]}
            self.assertIn("ffprobe_failed", rules)
            self.assertIn("missing_frame_evidence", rules)
            self.assertEqual(result["source_tool"], "tools/rendered_product_qa.py")

    def test_probe_and_frame_evidence_pass(self):
        def fake_probe(_path):
            return {
                "ok": True,
                "duration_sec": 42.0,
                "streams": [
                    {"codec_type": "video", "codec_name": "h264"},
                    {"codec_type": "audio", "codec_name": "aac"},
                ],
                "raw": {"format": {"duration": "42.0"}},
            }

        def fake_sampler(_video, out_dir):
            frame = Path(out_dir) / "rendered_product_qa_frames" / "frame_000.jpg"
            frame.parent.mkdir(parents=True, exist_ok=True)
            frame.write_bytes(b"jpg")
            sheet = Path(out_dir) / "rendered_product_qa_contact_sheet.jpg"
            sheet.write_bytes(b"jpg")
            return {"ok": True, "frames": [frame], "contact_sheet": sheet}

        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "final.mp4").write_bytes(b"fake video")

            result = build_rendered_product_qa(
                root,
                root,
                probe_func=fake_probe,
                sampler_func=fake_sampler,
            )

            self.assertTrue(result["pass"])
            self.assertEqual(result["blocking"], [])
            self.assertTrue(result["contact_sheet"].endswith("rendered_product_qa_contact_sheet.jpg"))

    def test_write_json_artifact(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = build_rendered_product_qa(root, root)
            out = root / "rendered_product_qa.json"
            out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

            loaded = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(loaded["artifact_role"], "rendered_product_qa")


if __name__ == "__main__":
    unittest.main()
