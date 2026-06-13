import unittest

from video_pipeline_core.edit_point_planner import (
    derive_motion_phases,
    plan_edit_window,
    plan_render_edit_points,
)


class EditPointPlannerTest(unittest.TestCase):
    def test_keep_audio_uses_full_intersecting_speech_run(self):
        result = plan_edit_window(
            start=3,
            duration=2,
            keep_audio=True,
            speech_runs=[{"start": 2, "end": 7, "kind": "speech"}],
            scene_cuts=[4],
            motion_peaks=[4.5],
        )
        self.assertEqual(result["start"], 2)
        self.assertEqual(result["end"], 7)
        self.assertEqual(result["reason"], "speech_boundary")

    def test_non_speech_prefers_scene_cut_then_motion(self):
        result = plan_edit_window(
            start=3,
            duration=2,
            keep_audio=False,
            speech_runs=[],
            scene_cuts=[4],
            motion_peaks=[3.5],
        )
        self.assertEqual(result["start"], 4)
        self.assertEqual(result["reason"], "scene_boundary")

    def test_action_window_uses_rise_and_settle(self):
        phases = derive_motion_phases(
            {"start": 0, "end": 10, "motion_peaks": [5]},
            rise_lead_sec=1.5,
            settle_tail_sec=2,
        )
        self.assertEqual(phases, [{"rise": 3.5, "peak": 5.0, "settle": 7.0}])

    def test_bridge_scene_is_not_used_for_action_phase(self):
        phases = derive_motion_phases(
            {"start": 0, "end": 10, "motion_peaks": [5], "bridge": True},
        )
        self.assertEqual(phases, [])

    def test_render_plan_uses_speech_boundary_for_keep_audio(self):
        plan = [{"source": "talk.mp4", "extract_start": 3, "extract_dur": 2, "keep_audio": True}]
        maps = [{"asset_id": "talk", "source": "talk.mp4", "speech": [
            {"start": 2, "end": 7, "kind": "speech"},
        ], "scenes": []}]
        result = plan_render_edit_points(plan, maps)
        self.assertEqual(result[0]["extract_start"], 2)
        self.assertEqual(result[0]["extract_dur"], 5)
        self.assertEqual(result[0]["adjustment_reason"], "speech_boundary")

    def test_action_scene_uses_rise_to_settle(self):
        plan = [{"source": "action.mp4", "scene_id": "action:0", "extract_start": 0,
                 "extract_dur": 8, "beat_alignment": "action"}]
        maps = [{"asset_id": "action", "source": "action.mp4", "scenes": [
            {"start": 0, "end": 10, "motion_peaks": [5]},
        ]}]
        result = plan_render_edit_points(plan, maps, rise_lead_sec=1, settle_tail_sec=2)
        self.assertEqual(result[0]["extract_start"], 4)
        self.assertEqual(result[0]["extract_dur"], 3)
        self.assertEqual(result[0]["adjustment_reason"], "motion_phase")


if __name__ == "__main__":
    unittest.main()
