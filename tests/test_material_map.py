import tempfile
import time
import unittest
from pathlib import Path

from video_pipeline_core import material_map


def _slow_material_map_builder(entry):
    time.sleep(1.0)
    return {
        "artifact_role": "material_map",
        "version": 1,
        "asset_id": entry["id"],
        "asset_type": entry.get("type") or "video",
        "source": entry.get("path"),
        "duration_sec": entry.get("duration_sec") or 0,
        "scenes": [],
        "speech": [],
    }


def _fast_material_map_builder(entry):
    return {
        "artifact_role": "material_map",
        "version": 1,
        "asset_id": entry["id"],
        "asset_type": entry.get("type") or "photo",
        "source": entry.get("path"),
        "duration_sec": entry.get("duration_sec") or 0,
        "scenes": [],
        "speech": [],
    }


class MaterialMapTest(unittest.TestCase):
    def test_video_map_combines_scene_motion_and_speech_evidence(self):
        entry = {
            "id": "clip-a",
            "type": "video",
            "path": "clip-a.mp4",
            "metadata": {"duration_sec": 10},
        }

        result = material_map.build_asset_map(
            entry,
            shot_detector=lambda _path: [(0, 4), (4, 10)],
            motion_detector=lambda _path: [1.5, 7.0],
            speech_detector=lambda _path, _duration: [
                {"start": 2.0, "end": 3.0, "kind": "speech"},
            ],
        )

        self.assertEqual(result["asset_id"], "clip-a")
        self.assertEqual(len(result["scenes"]), 2)
        self.assertEqual(result["scenes"][0]["midpoint"], 2.0)
        self.assertEqual(result["scenes"][0]["motion_peaks"], [1.5])
        self.assertEqual(result["scenes"][1]["motion_peaks"], [7.0])
        self.assertEqual(result["speech"][0]["kind"], "speech")

    def test_photo_map_has_one_useful_scene(self):
        result = material_map.build_asset_map({"id": "photo-a", "type": "photo", "path": "a.jpg"})
        self.assertEqual(len(result["scenes"]), 1)
        self.assertEqual(result["scenes"][0]["kind"], "still")

    def test_fast_video_map_uses_duration_without_expensive_detectors(self):
        entry = {
            "id": "clip-fast",
            "type": "video",
            "path": "clip-fast.mp4",
            "metadata": {"duration_sec": 42},
        }

        result = material_map.build_fast_asset_map(entry)

        self.assertEqual(result["asset_id"], "clip-fast")
        self.assertEqual(result["map_mode"], "fast")
        self.assertEqual(result["duration_sec"], 42.0)
        self.assertEqual(result["scenes"], [{
            "start": 0.0,
            "end": 42.0,
            "midpoint": 21.0,
            "kind": "video",
            "motion_peaks": [],
            "map_mode": "fast",
        }])
        self.assertEqual(result["speech"], [])

    def test_parse_silencedetect_inverts_silence_to_speech(self):
        stderr = "silence_start: 2.0\nsilence_end: 4.0 | silence_duration: 2.0\n"
        runs = material_map.parse_silencedetect_runs(stderr, 6.0)
        self.assertEqual(
            runs,
            [
                {"start": 0.0, "end": 2.0, "kind": "speech"},
                {"start": 2.0, "end": 4.0, "kind": "silence"},
                {"start": 4.0, "end": 6.0, "kind": "speech"},
            ],
        )

    def test_scene_review_can_caption_and_mark_bridge(self):
        asset_map = {
            "asset_id": "clip-a",
            "scenes": [{"start": 0, "end": 2}, {"start": 2, "end": 4}],
        }
        result = material_map.apply_scene_review_verdict(asset_map, {
            "scenes": [
                {"scene_index": 0, "caption": "Students enter the workshop", "bridge": True},
                {"scene_index": 1, "caption": "Close-up of hands"},
            ],
        })
        self.assertEqual(result["scenes"][0]["caption"], "Students enter the workshop")
        self.assertTrue(result["scenes"][0]["bridge"])

    def test_scene_review_preserves_shallow_visual_diversity_labels(self):
        asset_map = {
            "asset_id": "clip-a",
            "asset_type": "video",
            "scenes": [{"start": 0, "end": 2}],
        }
        result = material_map.apply_scene_review_verdict(asset_map, {
            "scenes": [{
                "scene_index": 0,
                "visual_family": "outdoor_muster_wide",
                "angle_scale": "wide",
                "action_family": "standing_muster",
                "subject": "students",
            }],
        })
        scene = result["scenes"][0]
        self.assertEqual(scene["visual_family"], "outdoor_muster_wide")
        self.assertEqual(scene["angle_scale"], "wide")
        self.assertEqual(scene["action_family"], "standing_muster")
        self.assertEqual(scene["subject"], "students")
        self.assertNotIn("media_type", scene)

    def test_opt_in_transcript_detector_only_transcribes_speech_runs(self):
        entry = {
            "id": "clip-a",
            "type": "video",
            "path": "clip-a.mp4",
            "metadata": {"duration_sec": 4},
        }
        result = material_map.build_asset_map(
            entry,
            shot_detector=lambda _path: [(0, 4)],
            motion_detector=lambda _path: [],
            speech_detector=lambda _path, _duration: [
                {"start": 0, "end": 2, "kind": "speech"},
                {"start": 2, "end": 4, "kind": "silence"},
            ],
            transcript_detector=lambda _path, run: f"spoken {run['start']}-{run['end']}",
        )
        self.assertEqual(result["speech"][0]["text"], "spoken 0-2")
        self.assertNotIn("text", result["speech"][1])

    def test_write_material_maps_respects_limit_for_operator_first_pass(self):
        root = Path(tempfile.mkdtemp())
        db = {"files": [
            {"id": "a", "type": "photo", "path": str(root / "a.jpg")},
            {"id": "b", "type": "photo", "path": str(root / "b.jpg")},
            {"id": "c", "type": "photo", "path": str(root / "c.jpg")},
        ]}

        maps = material_map.write_material_maps(db, root / "maps", limit=2)

        self.assertEqual([item["asset_id"] for item in maps], ["a", "b"])
        self.assertTrue((root / "maps" / "a.map.json").exists())
        self.assertTrue((root / "maps" / "b.map.json").exists())
        self.assertFalse((root / "maps" / "c.map.json").exists())
        self.assertIn("material_map", db["files"][0])
        self.assertIn("material_map", db["files"][1])
        self.assertNotIn("material_map", db["files"][2])

    def test_write_material_maps_can_restrict_to_wall_selected_assets(self):
        root = Path(tempfile.mkdtemp())
        db = {"files": [
            {"id": "a", "type": "photo", "path": str(root / "a.jpg"),
             "selected_for_material_map": False},
            {"id": "b", "type": "photo", "path": str(root / "b.jpg"),
             "selected_for_material_map": True},
            {"id": "c", "type": "photo", "path": str(root / "c.jpg"),
             "selected_for_material_map": True},
        ]}

        maps = material_map.write_material_maps(db, root / "maps", selected_only=True)

        self.assertEqual([item["asset_id"] for item in maps], ["b", "c"])
        self.assertFalse((root / "maps" / "a.map.json").exists())
        self.assertTrue((root / "maps" / "b.map.json").exists())
        self.assertTrue((root / "maps" / "c.map.json").exists())

    def test_write_material_maps_fast_mode_maps_videos_without_timeout_skip(self):
        root = Path(tempfile.mkdtemp())
        db = {"files": [
            {
                "id": "v",
                "type": "video",
                "path": str(root / "v.mp4"),
                "metadata": {"duration_sec": 30},
                "selected_for_material_map": True,
            },
        ]}

        maps = material_map.write_material_maps(
            db,
            root / "maps",
            selected_only=True,
            asset_timeout_sec=0.01,
            fast=True,
        )

        self.assertEqual([item["asset_id"] for item in maps], ["v"])
        self.assertEqual(maps[0]["map_mode"], "fast")
        self.assertEqual(db["files"][0]["material_map_status"], "mapped")
        self.assertTrue((root / "maps" / "v.map.json").exists())

    def test_write_material_maps_skips_asset_timeout_and_keeps_previous_maps(self):
        root = Path(tempfile.mkdtemp())
        db = {"files": [
            {"id": "a", "type": "photo", "path": str(root / "a.jpg"),
             "selected_for_material_map": True},
            {"id": "b", "type": "video", "path": str(root / "b.mp4"),
             "selected_for_material_map": True},
        ]}

        maps = material_map.write_material_maps(
            db,
            root / "maps",
            selected_only=True,
            asset_timeout_sec=0.05,
            map_builder=lambda entry: (
                _fast_material_map_builder(entry)
                if entry["id"] == "a"
                else _slow_material_map_builder(entry)
            ),
        )

        self.assertEqual([item["asset_id"] for item in maps], ["a"])
        self.assertTrue((root / "maps" / "a.map.json").exists())
        self.assertFalse((root / "maps" / "b.map.json").exists())
        self.assertIn("material_map", db["files"][0])
        self.assertNotIn("material_map", db["files"][1])
        self.assertEqual(db["files"][1]["material_map_status"], "skipped")
        self.assertEqual(db["files"][1]["material_map_error"]["reason"], "timeout")

    def test_write_material_maps_writes_update_db_incrementally_after_success(self):
        root = Path(tempfile.mkdtemp())
        update_db = root / "materials_db.partial.json"
        db = {"files": [
            {"id": "a", "type": "photo", "path": str(root / "a.jpg"),
             "selected_for_material_map": True},
            {"id": "b", "type": "video", "path": str(root / "b.mp4"),
             "selected_for_material_map": True},
        ]}

        material_map.write_material_maps(
            db,
            root / "maps",
            selected_only=True,
            asset_timeout_sec=0.05,
            update_db_path=update_db,
            map_builder=lambda entry: (
                _fast_material_map_builder(entry)
                if entry["id"] == "a"
                else _slow_material_map_builder(entry)
            ),
        )

        self.assertTrue(update_db.exists())
        written = material_map.json.loads(update_db.read_text(encoding="utf-8"))
        self.assertIn("material_map", written["files"][0])
        self.assertEqual(written["files"][1]["material_map_status"], "skipped")

    def test_write_material_maps_records_absolute_map_paths_for_handoff(self):
        root = Path(tempfile.mkdtemp())
        update_db = root / "materials_db.mapped.json"
        db = {"files": [
            {"id": "a", "type": "photo", "path": str(root / "a.jpg")},
        ]}

        old_cwd = Path.cwd()
        try:
            material_map.os.chdir(root)
            material_map.write_material_maps(
                db,
                Path("relative_maps"),
                update_db_path=update_db,
            )
        finally:
            material_map.os.chdir(old_cwd)

        written = material_map.json.loads(update_db.read_text(encoding="utf-8"))
        path = Path(written["files"][0]["material_map"])
        self.assertTrue(path.is_absolute())
        self.assertTrue(path.exists())


if __name__ == "__main__":
    unittest.main()
