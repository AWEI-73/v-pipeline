import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from video_pipeline_core import beat_sequence as bs
from video_pipeline_core import mv_cut
from video_pipeline_core.vt_core import FFMPEG, FFPROBE


def _shots(n, dur=10.0):
    return [{"source": f"/m/s{i}.mp4", "start": 0.0, "dur": dur} for i in range(n)]


class CompileTest(unittest.TestCase):
    def test_full_beat_recipe_produces_ordered_sequence(self):
        seq = bs.compile_beat_sequence({}, _shots(4), segment=3)
        roles = [c["beat_role"] for c in seq["clips"]]
        self.assertEqual(roles, ["context", "primary_action", "detail_reaction", "payoff"])
        self.assertTrue(all(c["segment"] == 3 for c in seq["clips"]))
        self.assertEqual(seq["clips"][1]["extract_dur"], 2.5)   # primary_action design

    def test_window_contract_clamps_video(self):
        seq = bs.compile_beat_sequence({"beats": ["primary_action"]},
                                       [{"source": "/m/a.mp4", "start": 5.0, "dur": 1.0}],
                                       segment=1)
        self.assertEqual(seq["clips"][0]["extract_dur"], 1.0)   # min(2.5, dur 1.0)

    def test_invalid_dur_video_dropped(self):
        seq = bs.compile_beat_sequence({"beats": ["primary_action"]},
                                       [{"source": "/m/a.mp4", "start": 0.0}], segment=1)
        self.assertEqual(seq["clips"], [])
        self.assertIn({"reason": "invalid_video_dur", "source": "/m/a.mp4"}, seq["dropped"])

    def test_missing_material_drops_beat(self):
        seq = bs.compile_beat_sequence({"beats": ["context", "payoff"]},
                                       _shots(1), segment=2)
        roles = [c["beat_role"] for c in seq["clips"]]
        self.assertEqual(roles, ["context"])
        self.assertIn({"beat": "payoff", "reason": "no_material"}, seq["dropped"])

    def test_payoff_cue_only_when_payoff_present(self):
        with_payoff = bs.compile_beat_sequence(
            {"beats": ["payoff"], "punctuate_payoff": True}, _shots(1), segment=4)
        self.assertEqual(with_payoff["cues"], [{"type": "hit", "anchor": "payoff", "segment": 4}])
        no_payoff = bs.compile_beat_sequence(
            {"beats": ["payoff"], "punctuate_payoff": True}, [], segment=5)
        self.assertEqual(no_payoff["cues"], [])
        self.assertIn({"beat": "sound_punctuation", "reason": "anchor_missing:payoff"},
                      no_payoff["dropped"])


class RunMvIntegrationTest(unittest.TestCase):
    def _run(self, script, clip_list, captured):
        with patch("video_pipeline_core.mv_cut.detect_beats", lambda _p: (120.0, [0.0, 2.0, 4.0])), \
             patch("video_pipeline_core.mv_cut._windows_from_clip",
                   lambda path, *a, **k: [{"source": path, "extract_start": 0.0,
                                           "extract_dur": 6.0, "keep_audio": False,
                                           "segment": k.get("segment")}]), \
             patch("video_pipeline_core.mv_cut.render_mv_audio",
                   lambda plan, *a, **k: captured.update(plan=plan)), \
             patch("video_pipeline_core.mv_cut.build_mv_state", lambda *a, **k: None):
            return mv_cut.run_mv(script, "/materials", "/out/final.mp4",
                                 music_path="/m.mp3", clip_list=clip_list, verbose=False)

    def test_beat_recipe_replaces_segment_slots(self):
        script = {"segments": [
            {"segment": 1, "visual_desc": "課程", "weight": 1.0, "pace": "hold",
             "audio_role": "music",
             "beat_recipe": {"beats": ["context", "primary_action"],
                             "shots": [{"source": "/m/x.mp4", "start": 0.0, "dur": 8.0},
                                       {"source": "/m/y.mp4", "start": 0.0, "dur": 8.0}]}}]}
        clip_list = {"assignments": [{"segment": 1, "picks": [{"path": "/m/x.mp4"}]}]}
        captured = {}
        result = self._run(script, clip_list, captured)
        roles = [c.get("beat_role") for c in result["plan"]]
        self.assertEqual(roles, ["context", "primary_action"])
        self.assertEqual([c["slot_index"] for c in result["plan"]], [0, 1])

    def test_no_beat_recipe_leaves_segment_unchanged(self):
        script = {"segments": [
            {"segment": 1, "visual_desc": "課程", "weight": 1.0, "pace": "hold",
             "audio_role": "music"}]}
        clip_list = {"assignments": [{"segment": 1, "picks": [{"path": "/m/x.mp4"}]}]}
        captured = {}
        result = self._run(script, clip_list, captured)
        self.assertFalse(any(c.get("beat_role") for c in result["plan"]))

    def test_beat_recipe_preserves_keep_audio_and_audio_role(self):
        # a duck (keep_audio) segment must not lose its audio semantic on replace
        script = {"segments": [
            {"segment": 1, "visual_desc": "致詞", "weight": 1.0, "pace": "hold",
             "audio_role": "duck",
             "beat_recipe": {"beats": ["context", "primary_action"],
                             "shots": [{"source": "/m/x.mp4", "start": 0.0, "dur": 8.0},
                                       {"source": "/m/y.mp4", "start": 0.0, "dur": 8.0}]}}]}
        clip_list = {"assignments": [{"segment": 1, "picks": [{"path": "/m/x.mp4"}]}]}
        result = self._run(script, clip_list, {})
        beat_clips = [c for c in result["plan"] if c.get("beat_role")]
        self.assertTrue(beat_clips)
        self.assertTrue(all(c["keep_audio"] for c in beat_clips))
        self.assertTrue(all(c.get("audio_role") == "duck" for c in beat_clips))

    def test_beat_recipe_preserves_text_layer(self):
        script = {"segments": [
            {"segment": 1, "visual_desc": "課程", "weight": 1.0, "pace": "hold",
             "audio_role": "music", "subtitle": "字幕內容", "narrative": "旁白內容",
             "beat_recipe": {"beats": ["context"],
                             "shots": [{"source": "/m/x.mp4", "start": 0.0, "dur": 8.0}]}}]}
        clip_list = {"assignments": [{"segment": 1, "picks": [{"path": "/m/x.mp4"}]}]}
        result = self._run(script, clip_list, {})
        beat_clip = [c for c in result["plan"] if c.get("beat_role")][0]
        self.assertEqual(beat_clip["text"]["subtitle"], "字幕內容")
        self.assertEqual(beat_clip["text"]["narrative"], "旁白內容")


class RealRenderTest(unittest.TestCase):
    def test_compiled_beat_sequence_renders_to_video(self):
        """Sequence true-render proof: a compiled beat sequence renders to a
        video of the expected (clamped) duration."""
        d = Path(tempfile.mkdtemp())
        src = d / "src.mp4"
        music = d / "bgm.mp3"
        subprocess.run([FFMPEG, "-y", "-f", "lavfi", "-i",
                        "testsrc=size=320x240:rate=30:duration=8",
                        "-pix_fmt", "yuv420p", str(src)], capture_output=True, check=True)
        subprocess.run([FFMPEG, "-y", "-f", "lavfi", "-i",
                        "sine=frequency=220:duration=10", str(music)],
                       capture_output=True, check=True)
        recipe = {"beats": ["context", "primary_action"],
                  "shots": [{"source": str(src), "start": 0.0, "dur": 8.0}]}
        seq = bs.compile_beat_sequence(recipe, recipe["shots"], segment=1)
        plan = seq["clips"]
        for i, c in enumerate(plan):
            c["slot_index"] = i
        # only 1 shot -> context takes it, primary_action drops (no_material)
        self.assertEqual([c["beat_role"] for c in plan], ["context"])
        out = d / "beat.mp4"
        mv_cut.render_mv_audio(plan, str(music), str(out), mat_dir=str(d), burn_text=False)
        self.assertTrue(out.exists())
        dur = float(subprocess.check_output(
            [FFPROBE, "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(out)], text=True).strip())
        self.assertGreater(dur, 1.0)        # context design 1.5s


if __name__ == "__main__":
    unittest.main()
