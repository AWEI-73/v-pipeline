import unittest

from video_pipeline_core.material_map import (
    apply_scene_review_verdict,
    build_asset_map,
    parse_silencedetect_runs,
)


class MaterialMapTest(unittest.TestCase):
    def test_video_map_combines_scene_motion_and_speech_evidence(self):
        entry = {
            "id": "clip-a",
            "type": "video",
            "path": "clip-a.mp4",
            "metadata": {"duration_sec": 10},
        }

        result = build_asset_map(
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
        result = build_asset_map({"id": "photo-a", "type": "photo", "path": "a.jpg"})
        self.assertEqual(len(result["scenes"]), 1)
        self.assertEqual(result["scenes"][0]["kind"], "still")

    def test_parse_silencedetect_inverts_silence_to_speech(self):
        stderr = "silence_start: 2.0\nsilence_end: 4.0 | silence_duration: 2.0\n"
        runs = parse_silencedetect_runs(stderr, 6.0)
        self.assertEqual(
            runs,
            [
                {"start": 0.0, "end": 2.0, "kind": "speech"},
                {"start": 2.0, "end": 4.0, "kind": "silence"},
                {"start": 4.0, "end": 6.0, "kind": "speech"},
            ],
        )

    def test_scene_review_can_caption_and_mark_bridge(self):
        material_map = {
            "asset_id": "clip-a",
            "scenes": [{"start": 0, "end": 2}, {"start": 2, "end": 4}],
        }
        result = apply_scene_review_verdict(material_map, {
            "scenes": [
                {"scene_index": 0, "caption": "Students enter the workshop", "bridge": True},
                {"scene_index": 1, "caption": "Close-up of hands"},
            ],
        })
        self.assertEqual(result["scenes"][0]["caption"], "Students enter the workshop")
        self.assertTrue(result["scenes"][0]["bridge"])

    def test_opt_in_transcript_detector_only_transcribes_speech_runs(self):
        entry = {
            "id": "clip-a",
            "type": "video",
            "path": "clip-a.mp4",
            "metadata": {"duration_sec": 4},
        }
        result = build_asset_map(
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


if __name__ == "__main__":
    unittest.main()
