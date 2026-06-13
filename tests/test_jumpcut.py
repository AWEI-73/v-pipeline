import unittest

from video_pipeline_core.jumpcut import (
    apply_jumpcut,
    apply_jumpcut_verdict,
    build_jumpcut_plan,
)


class JumpcutTest(unittest.TestCase):
    def test_plan_keeps_speech_and_marks_long_silence_for_removal(self):
        material_map = {"asset_id": "talk", "source": "talk.mp4", "speech": [
            {"start": 0, "end": 3, "kind": "speech", "text": "hello"},
            {"start": 3, "end": 5, "kind": "silence"},
            {"start": 5, "end": 8, "kind": "speech", "text": "finish"},
        ]}
        plan = build_jumpcut_plan(material_map, min_remove_silence_sec=1)
        self.assertEqual(plan["segments"][1]["action"], "remove")
        self.assertTrue(plan["requires_review"])

    def test_short_silence_is_kept(self):
        material_map = {"asset_id": "talk", "speech": [
            {"start": 0, "end": 0.3, "kind": "silence"},
        ]}
        plan = build_jumpcut_plan(material_map, min_remove_silence_sec=1)
        self.assertEqual(plan["segments"][0]["action"], "keep")

    def test_apply_verdict_accepts_or_patches_actions(self):
        plan = {"asset_id": "talk", "segments": [
            {"index": 0, "start": 0, "end": 2, "action": "keep"},
            {"index": 1, "start": 2, "end": 4, "action": "remove"},
        ]}
        result = apply_jumpcut_verdict(plan, {
            "decision": "accept",
            "patches": [{"index": 1, "action": "keep"}],
        })
        self.assertTrue(result["approved"])
        self.assertEqual(result["segments"][1]["action"], "keep")
        self.assertEqual(result["review_lineage"]["decision"], "accept")

    def test_apply_requires_approved_plan_and_records_lineage(self):
        calls = []
        plan = {
            "asset_id": "talk",
            "source": "talk.mp4",
            "approved": True,
            "review_lineage": {"decision": "accept", "reviewer": "agent"},
            "segments": [
                {"start": 0, "end": 2, "action": "keep"},
                {"start": 2, "end": 4, "action": "remove"},
                {"start": 4, "end": 6, "action": "keep"},
            ],
        }
        result = apply_jumpcut(
            plan,
            "processed/talk.mp4",
            runner=lambda command: calls.append(command),
        )
        self.assertEqual(len(calls), 1)
        self.assertEqual(result["lineage"]["source"], "talk.mp4")
        self.assertEqual(result["lineage"]["kept_ranges"], [[0.0, 2.0], [4.0, 6.0]])

    def test_apply_rejects_unapproved_plan(self):
        with self.assertRaises(ValueError):
            apply_jumpcut({"approved": False, "segments": []}, "out.mp4", runner=lambda _c: None)


if __name__ == "__main__":
    unittest.main()
