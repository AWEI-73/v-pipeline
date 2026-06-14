import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from video_pipeline_core import ending_sequence as es
from video_pipeline_core import mv_cut
from video_pipeline_core.vt_core import FFMPEG, FFPROBE


def _shots(n, dur=10.0):
    return [{"source": f"/m/s{i}.mp4", "start": 0.0, "dur": dur} for i in range(n)]


class CompileTest(unittest.TestCase):
    def test_full_recipe_produces_narrative_closure(self):
        result = es.compile_ending_sequence(
            {"closing_text": "We are ready", "punctuate_payoff": True},
            _shots(3), segment=4)
        self.assertEqual([c["ending_role"] for c in result["clips"]],
                         ["callback", "payoff", "closing_title"])
        self.assertEqual(result["clips"][-1]["text"], {"narrative": "We are ready"})
        self.assertEqual(result["cues"], [{"type": "hit", "anchor": "payoff", "segment": 4}])

    def test_invalid_video_window_is_dropped(self):
        result = es.compile_ending_sequence(
            {"beats": ["payoff"]}, [{"source": "/m/a.mp4"}], segment=2)
        self.assertEqual(result["clips"], [])
        self.assertIn({"reason": "invalid_video_dur", "source": "/m/a.mp4"},
                      result["dropped"])

    def test_missing_closing_text_drops_only_title(self):
        result = es.compile_ending_sequence({}, _shots(2), segment=3)
        self.assertEqual([c["ending_role"] for c in result["clips"]],
                         ["callback", "payoff"])
        self.assertIn({"beat": "closing_title", "reason": "no_closing_text"},
                      result["dropped"])

    def test_payoff_cue_requires_real_payoff(self):
        result = es.compile_ending_sequence(
            {"beats": ["payoff"], "punctuate_payoff": True}, [], segment=2)
        self.assertEqual(result["cues"], [])
        self.assertIn({"beat": "sound_punctuation",
                       "reason": "anchor_missing:payoff"}, result["dropped"])


class PoolAndAppendTest(unittest.TestCase):
    def test_ending_pool_prefers_story_tail_and_dedups(self):
        plan = [{"source": "/m/a.mp4", "extract_start": 0, "extract_dur": 2},
                {"source": "/m/b.mp4", "extract_start": 1, "extract_dur": 3},
                {"source": "/m/a.mp4", "extract_start": 5, "extract_dur": 2}]
        pool = es.ending_pool_from_plan(plan)
        self.assertEqual([s["source"] for s in pool], ["/m/a.mp4", "/m/b.mp4"])
        self.assertEqual(pool[0]["start"], 5.0)

    def test_append_reindexes_entire_plan(self):
        plan = [{"source": "/m/story.mp4", "slot_index": 8}]
        ending = [{"source": "/m/end.mp4"}]
        combined = es.append_ending_to_plan(plan, ending)
        self.assertEqual([c["slot_index"] for c in combined], [0, 1])
        self.assertEqual(combined[-1]["source"], "/m/end.mp4")


class RunMvIntegrationTest(unittest.TestCase):
    def _run(self, script):
        clip_list = {"assignments": [
            {"segment": 1, "picks": [{"path": "/m/story.mp4"}]}]}
        with patch("video_pipeline_core.mv_cut.detect_beats",
                   lambda _p: (120.0, [0.0, 2.0, 4.0])), \
             patch("video_pipeline_core.mv_cut._windows_from_clip",
                   lambda path, *a, **k: [{"source": path, "extract_start": 0.0,
                                           "extract_dur": 6.0, "keep_audio": False,
                                           "segment": k.get("segment")}]), \
             patch("video_pipeline_core.mv_cut.render_mv_audio", lambda *a, **k: None), \
             patch("video_pipeline_core.mv_cut.build_mv_state", lambda *a, **k: None):
            return mv_cut.run_mv(script, "/materials", "/out/final.mp4",
                                 music_path="/m.mp3", clip_list=clip_list, verbose=False)

    def test_ending_recipe_appends_to_render_plan(self):
        script = {"ending_recipe": {"closing_text": "END", "beats": ["payoff", "closing_title"]},
                  "segments": [{"segment": 1, "visual_desc": "story", "weight": 1.0,
                                "pace": "hold", "audio_role": "music"}]}
        result = self._run(script)
        self.assertEqual(result["plan"][0]["source"], "/m/story.mp4")
        self.assertEqual([c.get("ending_role") for c in result["plan"][1:]],
                         ["payoff", "closing_title"])
        self.assertEqual(result["ending"]["beats_used"], ["payoff", "closing_title"])

    def test_no_recipe_leaves_plan_unchanged(self):
        script = {"segments": [{"segment": 1, "visual_desc": "story", "weight": 1.0,
                                "pace": "hold", "audio_role": "music"}]}
        result = self._run(script)
        self.assertIsNone(result["ending"])
        self.assertFalse(any(c.get("ending_role") for c in result["plan"]))

    def test_opening_story_and_ending_keep_narrative_order(self):
        script = {
            "opening_recipe": {"beats": ["hook"], "shots": _shots(1)},
            "ending_recipe": {"beats": ["payoff"], "shots": _shots(1)},
            "segments": [{"segment": 1, "visual_desc": "story", "weight": 1.0,
                          "pace": "hold", "audio_role": "music"}],
        }
        result = self._run(script)
        self.assertEqual(result["plan"][0]["opening_role"], "hook")
        self.assertEqual(result["plan"][1]["source"], "/m/story.mp4")
        self.assertEqual(result["plan"][2]["ending_role"], "payoff")
        self.assertEqual([c["slot_index"] for c in result["plan"]], [0, 1, 2])


class RealRenderTest(unittest.TestCase):
    def test_compiled_ending_renders_to_video(self):
        d = Path(tempfile.mkdtemp())
        src = d / "src.mp4"
        music = d / "bgm.mp3"
        subprocess.run([FFMPEG, "-y", "-f", "lavfi", "-i",
                        "testsrc=size=320x240:rate=30:duration=7",
                        "-pix_fmt", "yuv420p", str(src)], capture_output=True, check=True)
        subprocess.run([FFMPEG, "-y", "-f", "lavfi", "-i",
                        "sine=frequency=220:duration=8", str(music)],
                       capture_output=True, check=True)
        result = es.compile_ending_sequence(
            {"beats": ["payoff", "closing_title"], "closing_text": "END"},
            [{"source": str(src), "start": 0.0, "dur": 7.0}], segment=2)
        plan = es.append_ending_to_plan([], result["clips"])
        out = d / "ending.mp4"
        mv_cut.render_mv_audio(plan, str(music), str(out), mat_dir=str(d), burn_text=True)
        self.assertTrue(out.exists())
        dur = float(subprocess.check_output(
            [FFPROBE, "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(out)], text=True).strip())
        self.assertGreater(dur, 4.0)


if __name__ == "__main__":
    unittest.main()
