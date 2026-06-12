import unittest
from unittest.mock import patch

from video_pipeline_core import mv_cut


class CreativeExceptionRuntimeTest(unittest.TestCase):
    def test_mv_render_plan_preserves_segment_creative_exception(self):
        exception = {
            "rule_bent": "hold_discipline",
            "reason": "Hold for the reveal.",
            "risk": "The shot may feel slow.",
            "requires_review": True,
        }
        script = {"segments": [{
            "segment": 1,
            "visual_desc": "reveal",
            "weight": 1.0,
            "pace": "hold",
            "audio_role": "music",
            "creative_exception": exception,
        }]}
        clip_list = {"assignments": [{"segment": 1, "picks": [{"path": "/m/a.mp4"}]}]}

        with patch("video_pipeline_core.mv_cut.detect_beats", lambda _p: (120.0, [0.0, 2.0])), \
             patch("video_pipeline_core.mv_cut._windows_from_clip", lambda path, *a, **k: [{
                 "source": path,
                 "extract_start": 1.0,
                 "extract_dur": 2.0,
                 "keep_audio": False,
                 "segment": k.get("segment"),
             }]), \
             patch("video_pipeline_core.mv_cut.render_mv_audio", lambda *a, **k: None), \
             patch("video_pipeline_core.mv_cut.build_mv_state", lambda *a, **k: None):
            result = mv_cut.run_mv(
                script,
                "/materials",
                "/out/final.mp4",
                music_path="/music.mp3",
                clip_list=clip_list,
                verbose=False,
            )

        self.assertEqual(result["plan"][0]["creative_exception"], exception)


if __name__ == "__main__":
    unittest.main()
