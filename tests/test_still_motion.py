import unittest


class StillMotionCoreTest(unittest.TestCase):
    def test_shared_motion_core_exposes_the_frozen_treatments(self):
        from video_pipeline_core.still_motion import STILL_TREATMENT_MODES

        self.assertEqual(
            STILL_TREATMENT_MODES,
            ("slow_push", "pan_right", "detail_push", "pan_left"),
        )

    def test_shared_motion_core_preserves_tuned_mv_filter_policy(self):
        from video_pipeline_core.mv_cut import _photo_vf
        from video_pipeline_core.still_motion import build_still_motion_filter

        for mode in ("slow_push", "pan_right", "detail_push", "pan_left"):
            with self.subTest(mode=mode):
                self.assertEqual(
                    build_still_motion_filter(
                        2.0,
                        treatment={"mode": mode},
                        width=1920,
                        height=1080,
                        fps=30,
                    ),
                    _photo_vf(2.0, kenburns=True, treatment={"mode": mode}),
                )
                self.assertNotIn("zoompan", build_still_motion_filter(2.0, treatment={"mode": mode}))


if __name__ == "__main__":
    unittest.main()
