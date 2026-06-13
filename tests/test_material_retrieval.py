import unittest

from video_pipeline_core.material_retrieval import plan_sound_bite, rank_scenes


class MaterialRetrievalTest(unittest.TestCase):
    def test_rank_scenes_prefers_caption_function_and_pace_fit(self):
        segment = {
            "segment": 4,
            "material_fit": {"visual_desc": "students pull electrical cable"},
            "sequence_grammar": {"required_functions": ["action"]},
            "visual_style": {"pace": "fast"},
        }
        maps = [{
            "asset_id": "clip-a",
            "source": "a.mp4",
            "scenes": [
                {"start": 0, "end": 2, "caption": "students pull electrical cable",
                 "functions": ["action"], "motion_peaks": [1]},
                {"start": 2, "end": 8, "caption": "empty classroom",
                 "functions": ["establish"], "motion_peaks": []},
            ],
        }]

        ranked = rank_scenes(segment, maps)

        self.assertEqual(len(ranked), 1)
        self.assertEqual(ranked[0]["scene_index"], 0)
        self.assertGreater(ranked[0]["score"], 0)
        self.assertEqual(ranked[0]["score_breakdown"]["text"], 2)

    def test_optional_ranker_reranks_but_cannot_admit_zero_evidence_scene(self):
        segment = {"material_fit": {"visual_desc": "cable training"}}
        maps = [{"asset_id": "a", "source": "a.mp4", "scenes": [
            {"start": 0, "end": 2, "caption": "cable training"},
            {"start": 2, "end": 4, "caption": "unrelated sunset"},
        ]}]
        ranked = rank_scenes(segment, maps, ranker=lambda _segment, _scene: 100)
        self.assertEqual([item["scene_index"] for item in ranked], [0])

    def test_source_speech_selects_transcribed_speech_run(self):
        segment = {"segment": 7, "audio": {"role": "source_speech"}}
        maps = [{"asset_id": "speech-a", "source": "speech.mp4", "speech": [
            {"start": 0, "end": 2, "kind": "silence"},
            {"start": 2, "end": 7, "kind": "speech", "text": "We finished together"},
        ]}]
        result = plan_sound_bite(segment, maps)
        self.assertEqual(result["source"], "speech.mp4")
        self.assertEqual(result["extract_start"], 2)
        self.assertEqual(result["extract_dur"], 5)
        self.assertTrue(result["keep_audio"])

    def test_flat_runtime_audio_role_requests_source_speech(self):
        segment = {"segment": 7, "audio_role": "source_speech"}
        maps = [{"source": "speech.mp4", "speech": [
            {"start": 1, "end": 3, "kind": "speech", "text": "Ready"},
        ]}]
        self.assertEqual(plan_sound_bite(segment, maps)["status"], "ok")

    def test_source_speech_without_speech_is_gap(self):
        result = plan_sound_bite({"segment": 7, "audio": {"role": "source_speech"}}, [])
        self.assertEqual(result["status"], "gap")


if __name__ == "__main__":
    unittest.main()
