import unittest

import video_pipeline as vp


class NarrativeJlCutPlanTest(unittest.TestCase):
    def test_alternates_visual_boundary_around_audio_seam(self):
        timing = {
            "segments": [
                {"segment": 1, "duration_sec": 3.0},
                {"segment": 2, "duration_sec": 4.0},
                {"segment": 3, "duration_sec": 5.0},
                {"segment": 4, "duration_sec": 6.0},
            ]
        }

        plan = vp.plan_narrative_jl_cuts(timing, style="narrative")

        self.assertEqual([x["type"] for x in plan], ["j_cut", "l_cut", "j_cut"])
        self.assertEqual([x["shift_sec"] for x in plan], [0.5, -0.5, 0.5])
        self.assertEqual([x["audio_seam_sec"] for x in plan], [3.0, 7.0, 12.0])
        self.assertEqual([x["visual_cut_sec"] for x in plan], [3.5, 6.5, 12.5])

    def test_clamps_shift_to_protect_short_neighboring_segments(self):
        timing = {
            "segments": [
                {"segment": 1, "duration_sec": 0.6},
                {"segment": 2, "duration_sec": 0.7},
                {"segment": 3, "duration_sec": 2.0},
            ]
        }

        plan = vp.plan_narrative_jl_cuts(timing, style="narrative")

        self.assertEqual(plan[0]["shift_sec"], 0.3)
        self.assertEqual(plan[1]["shift_sec"], 0.3)

    def test_non_narrative_style_keeps_boundaries_aligned(self):
        timing = {"segments": [{"segment": 1, "duration_sec": 3.0},
                               {"segment": 2, "duration_sec": 4.0}]}

        self.assertEqual(vp.plan_narrative_jl_cuts(timing, style="mv"), [])

    def test_final_boundary_is_j_cut_so_visual_can_be_trimmed_to_voice(self):
        timing = {"segments": [{"segment": 1, "duration_sec": 3.0},
                               {"segment": 2, "duration_sec": 4.0},
                               {"segment": 3, "duration_sec": 5.0}]}

        plan = vp.plan_narrative_jl_cuts(timing, style="narrative")

        self.assertEqual([x["type"] for x in plan], ["j_cut", "j_cut"])

    def test_render_tail_covers_delayed_cut_and_transition(self):
        cuts = [{"shift_sec": 0.5}, {"shift_sec": -0.5}, {"shift_sec": 0.5}]

        self.assertEqual(vp.jl_cut_render_tail(cuts, [0.12, 0.2, 0.12]), 1.12)


class NarrativeJlCutFilterTest(unittest.TestCase):
    def test_filter_chain_consumes_planned_visual_cut_offsets(self):
        fc, label = vp.build_filter_chain(
            [3.0, 4.0, 5.0],
            0.12,
            boundary_offsets=[3.5, 6.5],
        )

        self.assertIn("offset=3.500", fc)
        self.assertIn("offset=6.500", fc)
        self.assertEqual(label, "v2")

    def test_filter_chain_trims_shifted_final_boundary_to_voice_duration(self):
        fc, label = vp.build_filter_chain(
            [3.0, 4.0],
            0.12,
            boundary_offsets=[3.5],
            total_duration=7.0,
        )

        self.assertIn("[v1]trim=duration=7.000,setpts=PTS-STARTPTS[vfinal]", fc)
        self.assertEqual(label, "vfinal")


if __name__ == "__main__":
    unittest.main()
