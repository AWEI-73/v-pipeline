import json
import tempfile
import types
import unittest
from pathlib import Path

from PIL import Image

from video_tools import cmd_material_wall_build, cmd_material_wall_review_apply
from video_pipeline_core import material_wall


def _jpg(path, color):
    Image.new("RGB", (80, 45), color=color).save(path, "JPEG")


class MaterialWallTest(unittest.TestCase):
    def test_video_frame_budget_scales_by_duration(self):
        self.assertEqual(material_wall.video_frame_budget(10), 3)
        self.assertEqual(material_wall.video_frame_budget(45), 6)
        self.assertEqual(material_wall.video_frame_budget(180), 9)
        self.assertEqual(material_wall.video_frame_budget(600), 12)

    def test_builds_photo_wall_and_video_strip_batches(self):
        root = Path(tempfile.mkdtemp())
        p1 = root / "p1.jpg"
        p2 = root / "p2.jpg"
        kfs = []
        _jpg(p1, "red")
        _jpg(p2, "blue")
        for i in range(6):
            frame = root / f"kf{i}.jpg"
            _jpg(frame, "green")
            kfs.append({"timestamp_sec": i * 5.0, "image_path": str(frame)})
        db_path = root / "materials_db.json"
        db_path.write_text(json.dumps({
            "files": [
                {"id": "photo-1", "type": "photo", "path": str(p1)},
                {"id": "photo-2", "type": "photo", "path": str(p2)},
                {
                    "id": "video-1",
                    "type": "video",
                    "path": str(root / "video.mp4"),
                    "metadata": {"duration_sec": 45.0},
                    "keyframes": kfs,
                },
            ]
        }), encoding="utf-8")
        out = root / "material_wall_request.json"

        cmd_material_wall_build(types.SimpleNamespace(
            db=str(db_path),
            out_dir=str(root / "wall"),
            out=str(out),
            photo_batch_size=60,
            video_batch_size=8,
        ))

        request = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(request["artifact_role"], "material_wall_request")
        self.assertEqual(request["next_action"], "await_material_wall_review")
        self.assertEqual([b["type"] for b in request["batches"]], ["photo_wall", "video_wall"])
        self.assertTrue(Path(request["batches"][0]["wall_image"]).exists())
        self.assertTrue(Path(request["batches"][1]["wall_image"]).exists())
        video_asset = request["batches"][1]["assets"][0]
        self.assertEqual(video_asset["asset_id"], "video-1")
        self.assertEqual(len(video_asset["frames"]), 6)

    def test_build_respects_limit_for_operator_first_pass(self):
        root = Path(tempfile.mkdtemp())
        paths = []
        for i, color in enumerate(("red", "blue", "green"), 1):
            path = root / f"p{i}.jpg"
            _jpg(path, color)
            paths.append(path)
        db_path = root / "materials_db.json"
        db_path.write_text(json.dumps({
            "files": [
                {"id": f"photo-{i}", "type": "photo", "path": str(path)}
                for i, path in enumerate(paths, 1)
            ]
        }), encoding="utf-8")
        out = root / "material_wall_request.json"

        cmd_material_wall_build(types.SimpleNamespace(
            db=str(db_path),
            out_dir=str(root / "wall"),
            out=str(out),
            photo_batch_size=60,
            video_batch_size=8,
            limit=2,
        ))

        request = json.loads(out.read_text(encoding="utf-8"))
        asset_ids = [
            asset["asset_id"]
            for batch in request["batches"]
            for asset in batch["assets"]
        ]
        self.assertEqual(asset_ids, ["photo-1", "photo-2"])

    def test_slice_db_from_wall_request_keeps_only_wall_assets_in_order(self):
        root = Path(tempfile.mkdtemp())
        db_path = root / "materials_db.json"
        db_path.write_text(json.dumps({
            "files": [
                {"id": "a", "type": "photo"},
                {"id": "b", "type": "video"},
                {"id": "c", "type": "photo"},
            ],
            "source_root": "demo",
        }), encoding="utf-8")
        request_path = root / "material_wall_request.json"
        request_path.write_text(json.dumps({
            "artifact_role": "material_wall_request",
            "batches": [
                {"assets": [{"asset_id": "b"}, {"asset_id": "a"}]},
            ],
        }), encoding="utf-8")
        out = root / "materials_db.bounded.json"

        result = material_wall.slice_material_db_from_wall_request_file(
            db_path, request_path, out)

        sliced = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(result["asset_count"], 2)
        self.assertEqual([item["id"] for item in sliced["files"]], ["a", "b"])
        self.assertEqual(sliced["source_root"], "demo")

    def test_build_supplements_video_frames_when_ingest_has_too_few(self):
        root = Path(tempfile.mkdtemp())
        frame = root / "kf0.jpg"
        _jpg(frame, "green")
        extra = []
        for i in range(6):
            path = root / f"extra{i}.jpg"
            _jpg(path, "yellow")
            extra.append({"timestamp_sec": i * 10.0, "image_path": str(path)})

        request = material_wall.build_material_wall_request(
            {"files": [{
                "id": "video-1",
                "type": "video",
                "path": str(root / "video.mp4"),
                "metadata": {"duration_sec": 45.0},
                "keyframes": [{"timestamp_sec": 1.0, "image_path": str(frame)}],
            }]},
            root / "wall",
            _frame_extractor=lambda entry, out_dir, budget: extra,
        )

        self.assertEqual(len(request["batches"][0]["assets"][0]["frames"]), 6)

    def test_build_exposes_folder_siblings_for_candidate_comparison(self):
        root = Path(tempfile.mkdtemp())
        a = root / "leader" / "a.jpg"
        b = root / "leader" / "b.jpg"
        a.parent.mkdir()
        _jpg(a, "red")
        _jpg(b, "blue")

        request = material_wall.build_material_wall_request(
            {"files": [
                {"id": "a", "type": "photo", "path": str(a), "tags_from_path": ["leader"]},
                {"id": "b", "type": "photo", "path": str(b), "tags_from_path": ["leader"]},
            ]},
            root / "wall",
        )

        assets = request["batches"][0]["assets"]
        self.assertEqual(assets[0]["folder_group"], "leader")
        self.assertEqual(assets[0]["sibling_asset_ids"], ["b"])
        self.assertEqual(request["candidate_groups"]["leader"], ["a", "b"])

    def test_apply_review_marks_keep_maybe_as_selected(self):
        root = Path(tempfile.mkdtemp())
        db_path = root / "materials_db.json"
        db_path.write_text(json.dumps({
            "files": [
                {"id": "a", "type": "photo", "path": "a.jpg"},
                {"id": "b", "type": "video", "path": "b.mp4"},
            ]
        }), encoding="utf-8")
        verdict_path = root / "material_wall_review_verdict.json"
        verdict_path.write_text(json.dumps({
            "artifact_role": "material_wall_review_verdict",
            "reviewer": "agent:director",
            "assets": [
                {
                    "asset_id": "a",
                    "coarse_status": "keep",
                    "visual_role": ["opening"],
                    "quality": "good",
                    "visual_evidence": ["clear entrance shot"],
                },
                {
                    "asset_id": "b",
                    "coarse_status": "reject",
                    "visual_role": [],
                    "quality": "weak",
                    "why_not_selected": "too shaky for the story need",
                },
            ],
        }), encoding="utf-8")
        out = root / "materials_db.reviewed.json"

        cmd_material_wall_review_apply(types.SimpleNamespace(
            db=str(db_path),
            verdict=str(verdict_path),
            out=str(out),
        ))

        reviewed = json.loads(out.read_text(encoding="utf-8"))
        by_id = {item["id"]: item for item in reviewed["files"]}
        self.assertTrue(by_id["a"]["selected_for_material_map"])
        self.assertFalse(by_id["b"]["selected_for_material_map"])
        self.assertEqual(by_id["a"]["material_wall_review"]["coarse_status"], "keep")
        self.assertEqual(by_id["a"]["material_wall_review"]["visual_evidence"], ["clear entrance shot"])
        self.assertEqual(by_id["b"]["material_wall_review"]["why_not_selected"],
                         "too shaky for the story need")

    def test_apply_review_rejects_unknown_asset(self):
        root = Path(tempfile.mkdtemp())
        db_path = root / "materials_db.json"
        db_path.write_text(json.dumps({"files": [{"id": "a", "type": "photo"}]}), encoding="utf-8")
        verdict_path = root / "verdict.json"
        verdict_path.write_text(json.dumps({
            "assets": [{"asset_id": "missing", "coarse_status": "keep"}],
        }), encoding="utf-8")

        with self.assertRaises(ValueError):
            cmd_material_wall_review_apply(types.SimpleNamespace(
                db=str(db_path),
                verdict=str(verdict_path),
                out=str(root / "out.json"),
            ))

    def test_apply_review_requires_every_visual_asset_to_be_reviewed(self):
        root = Path(tempfile.mkdtemp())
        db_path = root / "materials_db.json"
        db_path.write_text(json.dumps({
            "files": [
                {"id": "a", "type": "photo", "path": str(root / "a.jpg")},
                {"id": "b", "type": "photo", "path": str(root / "b.jpg")},
            ]
        }), encoding="utf-8")
        verdict_path = root / "verdict.json"
        verdict_path.write_text(json.dumps({
            "assets": [{
                "asset_id": "a",
                "coarse_status": "keep",
                "visual_evidence": ["clear opening"],
            }],
        }), encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "missing material wall decision"):
            cmd_material_wall_review_apply(types.SimpleNamespace(
                db=str(db_path),
                verdict=str(verdict_path),
                out=str(root / "out.json"),
            ))

    def test_apply_review_requires_visual_evidence_for_keep_or_maybe(self):
        root = Path(tempfile.mkdtemp())
        db_path = root / "materials_db.json"
        db_path.write_text(json.dumps({"files": [{"id": "a", "type": "photo", "path": "a.jpg"}]}),
                           encoding="utf-8")
        verdict_path = root / "verdict.json"
        verdict_path.write_text(json.dumps({
            "assets": [{"asset_id": "a", "coarse_status": "keep", "notes": "folder says opening"}],
        }), encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "visual_evidence"):
            cmd_material_wall_review_apply(types.SimpleNamespace(
                db=str(db_path),
                verdict=str(verdict_path),
                out=str(root / "out.json"),
            ))

    def test_apply_review_requires_reject_reason_and_duplicate_target(self):
        root = Path(tempfile.mkdtemp())
        db_path = root / "materials_db.json"
        db_path.write_text(json.dumps({
            "files": [
                {"id": "a", "type": "photo", "path": "a.jpg"},
                {"id": "b", "type": "photo", "path": "b.jpg"},
            ]
        }), encoding="utf-8")
        verdict_path = root / "verdict.json"
        verdict_path.write_text(json.dumps({
            "assets": [
                {"asset_id": "a", "coarse_status": "reject"},
                {"asset_id": "b", "coarse_status": "duplicate", "why_not_selected": "same scene"},
            ],
        }), encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "why_not_selected|duplicate_of"):
            cmd_material_wall_review_apply(types.SimpleNamespace(
                db=str(db_path),
                verdict=str(verdict_path),
                out=str(root / "out.json"),
            ))


if __name__ == "__main__":
    unittest.main()
