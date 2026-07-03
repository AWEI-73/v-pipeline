import tempfile
import unittest
import json
import types
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from video_pipeline_core import curator


class MaterialVisualReviewTest(unittest.TestCase):
    def test_build_request_uses_montage_for_video_and_photo_as_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            calls = []

            def fake_grid(video, out, **kwargs):
                calls.append((video, str(out)))
                return {"grid_path": str(out), "samples": [{"timestamp_sec": 1.0}]}

            request = curator.build_material_review_request(
                {"files": [
                    {"id": "f1", "type": "video", "path": "clip.mp4"},
                    {"id": "f2", "type": "photo", "path": "photo.jpg", "display_path": "display.jpg"},
                ]},
                tmp,
                _gridfn=fake_grid,
            )

        self.assertEqual(calls[0][0], "clip.mp4")
        self.assertIn("material_review", request["assets"][0]["montage"])
        self.assertEqual(request["assets"][1]["montage"], "display.jpg")
        self.assertEqual(request["next_action"], "await_material_visual_review")

    def test_apply_verdict_updates_caption_and_agent_lineage(self):
        db = {"files": [{"id": "f1", "type": "video", "path": "clip.mp4"}]}
        result = curator.apply_material_review_verdict(db, {
            "assets": [{"id": "f1", "caption": "A team meets around a table", "notes": "usable"}]
        })

        self.assertEqual(result["files"][0]["vlm_caption"], "A team meets around a table")
        self.assertEqual(result["files"][0]["caption_source"], "agent_visual_review")
        self.assertEqual(result["files"][0]["caption_notes"], "usable")

    def test_caption_meta_agent_review_awaits_then_resumes_from_verdict(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db_path = root / "materials_db.json"
            review_dir = root / "review"
            db_path.write_text(json.dumps({"files": [
                {"id": "f1", "type": "photo", "path": "photo.jpg"},
            ]}), encoding="utf-8")
            args = types.SimpleNamespace(
                db=str(db_path),
                model=None,
                limit=None,
                visual_review_dir=str(review_dir),
            )

            with patch(
                "video_pipeline_core.curator.build_material_review_request",
                return_value={
                    "artifact_role": "material_visual_review_request",
                    "next_action": "await_material_visual_review",
                    "assets": [{"id": "f1", "montage": "photo.jpg"}],
                    "verdict_template": {"assets": [{"id": "f1", "caption": None, "notes": None}]},
                },
            ):
                output = StringIO()
                with redirect_stdout(output):
                    curator.cmd_caption_meta(args)

            status = json.loads(output.getvalue())
            self.assertEqual(status["next_action"], "await_material_visual_review")
            self.assertTrue((review_dir / "material_visual_review_request.json").exists())

            (review_dir / "material_visual_review_verdict.json").write_text(json.dumps({
                "assets": [{"id": "f1", "caption": "Students practice cable repair", "notes": "clear"}],
            }), encoding="utf-8-sig")
            output = StringIO()
            with redirect_stdout(output):
                curator.cmd_caption_meta(args)

            status = json.loads(output.getvalue())
            result = json.loads(db_path.read_text(encoding="utf-8"))
            self.assertEqual(status["status"], "ok")
            self.assertEqual(status["captioned"], 1)
            self.assertEqual(result["files"][0]["caption_source"], "agent_visual_review")

    def test_apply_verdict_rejects_missing_pending_asset(self):
        db = {"files": [
            {"id": "f1", "type": "video", "path": "one.mp4"},
            {"id": "f2", "type": "video", "path": "two.mp4"},
        ]}

        with self.assertRaisesRegex(ValueError, "missing pending asset"):
            curator.apply_material_review_verdict(db, {
                "assets": [{"id": "f1", "caption": "First clip"}],
            })

    def test_ingest_meta_includes_files_at_source_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            video = root / "root-clip.mp4"
            video.write_bytes(b"fixture")
            db_path = root / "materials_db.json"
            args = types.SimpleNamespace(src=str(root), out=str(db_path), work_dir=str(root / "work"))

            with patch("video_pipeline_core.curator._video_info", return_value={
                "resolution": "1920x1080", "duration_sec": 10.0,
            }), patch("video_pipeline_core.curator._extract_keyframes", return_value=[]):
                curator.cmd_ingest_meta(args)

            db = json.loads(db_path.read_text(encoding="utf-8"))
            self.assertEqual(db["total"], 1)
            self.assertEqual(db["files"][0]["path"], "root-clip.mp4")

    def test_caption_meta_agent_review_finishes_when_nothing_is_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db_path = root / "materials_db.json"
            db_path.write_text(json.dumps({"files": [
                {"id": "f1", "vlm_caption": "Already captioned"},
            ]}), encoding="utf-8")
            args = types.SimpleNamespace(
                db=str(db_path), model=None, limit=None, visual_review_dir=str(root / "review"),
            )

            output = StringIO()
            with redirect_stdout(output):
                curator.cmd_caption_meta(args)

            status = json.loads(output.getvalue())
            self.assertEqual(status["status"], "ok")
            self.assertEqual(status["captioned"], 0)
            self.assertNotIn("next_action", status)

    def test_caption_meta_defaults_to_agent_review_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db_path = root / "materials_db.json"
            photo = root / "photo.jpg"
            photo.write_bytes(b"fixture")
            db_path.write_text(json.dumps({"files": [
                {"id": "f1", "type": "photo", "path": str(photo)},
            ]}), encoding="utf-8")
            args = types.SimpleNamespace(
                db=str(db_path),
                model=None,
                limit=None,
                visual_review_dir=None,
                local_vlm=False,
            )

            output = StringIO()
            with redirect_stdout(output):
                curator.cmd_caption_meta(args)

            status = json.loads(output.getvalue())
            self.assertEqual(status["next_action"], "await_material_visual_review")
            self.assertTrue((root / "material_visual_review" / "material_visual_review_request.json").exists())


if __name__ == "__main__":
    unittest.main()
