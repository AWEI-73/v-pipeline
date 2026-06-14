import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from video_pipeline_core import mv_cut
from video_pipeline_core import opening_sequence as op
from video_pipeline_core.vt_core import FFMPEG, FFPROBE


def _shots(n):
    return [{"source": f"/m/s{i}.mp4", "start": float(i), "dur": 10.0} for i in range(n)]


class CompileTest(unittest.TestCase):
    def test_full_recipe_produces_ordered_opening_clips(self):
        recipe = {"title_text": "66期養成班", "context_count": 2}
        result = op.compile_opening_sequence(recipe, _shots(5))
        roles = [c["opening_role"] for c in result["clips"]]
        self.assertEqual(roles, ["hook", "context_montage", "context_montage", "title_reveal"])
        self.assertEqual(result["clips"][0]["still_treatment"], {"mode": "slow_push"})
        title = result["clips"][-1]
        self.assertEqual(title["text"], {"narrative": "66期養成班"})
        self.assertEqual([c["segment"] for c in result["clips"]], [0, 0, 0, 0])
        self.assertIn("sound_punctuation", result["beats_used"])
        self.assertEqual(result["cues"], [{"type": "hit", "anchor": "title_reveal"}])

    def test_no_material_drops_visual_beats_gracefully(self):
        result = op.compile_opening_sequence({"title_text": "T"}, [])
        self.assertEqual(result["clips"], [])
        dropped = {d["beat"]: d["reason"] for d in result["dropped"]}
        self.assertEqual(dropped["hook"], "no_material")
        self.assertEqual(dropped["context_montage"], "no_material")
        self.assertEqual(dropped["title_reveal"], "no_material")

    def test_missing_title_text_drops_title_reveal_only(self):
        result = op.compile_opening_sequence({"context_count": 1}, _shots(3))
        roles = [c["opening_role"] for c in result["clips"]]
        self.assertNotIn("title_reveal", roles)
        self.assertIn({"beat": "title_reveal", "reason": "no_title_text"}, result["dropped"])

    def test_title_reuses_first_shot_when_pool_exhausted(self):
        # 1 shot, hook consumes it; title_reveal should reuse first_shot, not drop
        result = op.compile_opening_sequence(
            {"title_text": "T", "context_count": 0}, _shots(1))
        roles = [c["opening_role"] for c in result["clips"]]
        self.assertEqual(roles, ["hook", "title_reveal"])

    def test_role_hint_selects_hook(self):
        shots = [{"source": "/m/a.mp4", "start": 0, "dur": 5},
                 {"source": "/m/hook.mp4", "start": 0, "dur": 5, "role": "hook"}]
        result = op.compile_opening_sequence({"context_count": 0}, shots)
        self.assertEqual(result["clips"][0]["source"], "/m/hook.mp4")


class HardeningTest(unittest.TestCase):
    def test_video_clip_clamped_to_approved_shot_dur(self):
        # hook design dur 2.5, but the approved video shot is only 1.0s long
        short = [{"source": "/m/s.mp4", "start": 0.0, "dur": 1.0}]
        result = op.compile_opening_sequence({"context_count": 0}, short)
        hook = result["clips"][0]
        self.assertEqual(hook["opening_role"], "hook")
        self.assertEqual(hook["extract_dur"], 1.0)        # clamped, not 2.5

    def test_video_clip_clamped_against_start_offset(self):
        # shot 10s but window starts at 9.0 -> only 1.0s available
        shot = [{"source": "/m/s.mp4", "start": 9.0, "dur": 10.0}]
        hook = op.compile_opening_sequence({"context_count": 0}, shot)["clips"][0]
        self.assertEqual(hook["extract_dur"], 1.0)

    def test_photo_uses_design_duration_not_source_dur(self):
        photo = [{"source": "/m/p.jpg", "start": 0.0, "dur": 0.0, "is_photo": True}]
        hook = op.compile_opening_sequence({"context_count": 0}, photo)["clips"][0]
        self.assertEqual(hook["extract_dur"], 2.5)        # design hook dur, unclamped

    def test_sound_punctuation_dropped_when_title_reveal_absent(self):
        # no title_text -> title_reveal dropped -> the cue has no real anchor
        result = op.compile_opening_sequence({"context_count": 1}, _shots(3))
        self.assertEqual(result["cues"], [])
        self.assertIn({"beat": "sound_punctuation", "reason": "anchor_missing:title_reveal"},
                      result["dropped"])
        self.assertNotIn("sound_punctuation", result["beats_used"])

    def test_sound_punctuation_emitted_only_with_real_title(self):
        result = op.compile_opening_sequence({"title_text": "T", "context_count": 1}, _shots(3))
        self.assertEqual(result["cues"], [{"type": "hit", "anchor": "title_reveal"}])
        self.assertIn("sound_punctuation", result["beats_used"])


class PoolAndPrependTest(unittest.TestCase):
    def test_pool_from_plan_dedups_and_orders(self):
        plan = [{"source": "/m/a.mp4", "extract_start": 1.0, "extract_dur": 3.0},
                {"source": "/m/a.mp4", "extract_start": 5.0, "extract_dur": 3.0},
                {"source": "/m/b.mp4", "extract_start": 0.0, "extract_dur": 2.0}]
        pool = op.opening_pool_from_plan(plan)
        self.assertEqual([s["source"] for s in pool], ["/m/a.mp4", "/m/b.mp4"])

    def test_prepend_reindexes_slot_index(self):
        plan = [{"source": "/m/seg.mp4", "slot_index": 0}]
        opening = [{"source": "/m/hook.mp4"}, {"source": "/m/title.mp4"}]
        combined = op.prepend_opening_to_plan(plan, opening)
        self.assertEqual([c["slot_index"] for c in combined], [0, 1, 2])
        self.assertEqual(combined[0]["source"], "/m/hook.mp4")
        self.assertEqual(combined[-1]["source"], "/m/seg.mp4")


class RunMvIntegrationTest(unittest.TestCase):
    def test_opening_recipe_changes_the_render_plan(self):
        script = {"opening_recipe": {"title_text": "T", "context_count": 1},
                  "segments": [
                      {"segment": 1, "visual_desc": "故事", "weight": 1.0,
                       "pace": "hold", "audio_role": "music"}]}
        clip_list = {"assignments": [{"segment": 1, "picks": [{"path": "/m/story.mp4"}]}]}
        captured = {}

        with patch("video_pipeline_core.mv_cut.detect_beats", lambda _p: (120.0, [0.0, 2.0, 4.0])), \
             patch("video_pipeline_core.mv_cut._windows_from_clip",
                   lambda path, *a, **k: [{"source": path, "extract_start": 0.0,
                                           "extract_dur": 3.0, "keep_audio": False,
                                           "segment": k.get("segment")}]), \
             patch("video_pipeline_core.mv_cut.render_mv_audio",
                   lambda plan, *a, **k: captured.update(plan=plan)), \
             patch("video_pipeline_core.mv_cut.build_mv_state", lambda *a, **k: None):
            result = mv_cut.run_mv(script, "/materials", "/out/final.mp4",
                                   music_path="/m.mp3", clip_list=clip_list, verbose=False)

        plan = result["plan"]
        self.assertEqual(plan[0]["opening_role"], "hook")
        self.assertIn("title_reveal", [c.get("opening_role") for c in plan])
        self.assertEqual([c["slot_index"] for c in plan], list(range(len(plan))))
        self.assertEqual(plan[-1]["source"], "/m/story.mp4")   # story follows opening
        self.assertEqual(result["opening"]["beats_used"][0], "hook")

    def test_no_recipe_leaves_plan_unchanged(self):
        script = {"segments": [{"segment": 1, "visual_desc": "故事", "weight": 1.0,
                                "pace": "hold", "audio_role": "music"}]}
        clip_list = {"assignments": [{"segment": 1, "picks": [{"path": "/m/story.mp4"}]}]}
        with patch("video_pipeline_core.mv_cut.detect_beats", lambda _p: (120.0, [0.0, 2.0])), \
             patch("video_pipeline_core.mv_cut._windows_from_clip",
                   lambda path, *a, **k: [{"source": path, "extract_start": 0.0,
                                           "extract_dur": 3.0, "keep_audio": False,
                                           "segment": k.get("segment")}]), \
             patch("video_pipeline_core.mv_cut.render_mv_audio", lambda *a, **k: None), \
             patch("video_pipeline_core.mv_cut.build_mv_state", lambda *a, **k: None):
            result = mv_cut.run_mv(script, "/materials", "/out/final.mp4",
                                   music_path="/m.mp3", clip_list=clip_list, verbose=False)
        self.assertIsNone(result["opening"])
        self.assertFalse(any(c.get("opening_role") for c in result["plan"]))


class RealRenderTest(unittest.TestCase):
    def test_compiled_opening_clips_render_to_video(self):
        """True-render proof: compiled opening clips (incl. a title overlay)
        actually produce a video segment of the expected duration."""
        d = Path(tempfile.mkdtemp())
        src = d / "src.mp4"
        music = d / "bgm.mp3"
        subprocess.run([FFMPEG, "-y", "-f", "lavfi", "-i",
                        "testsrc=size=320x240:rate=30:duration=6",
                        "-pix_fmt", "yuv420p", str(src)],
                       capture_output=True, check=True)
        subprocess.run([FFMPEG, "-y", "-f", "lavfi", "-i",
                        "sine=frequency=220:duration=8", str(music)],
                       capture_output=True, check=True)
        recipe = {"title_text": "TITLE", "context_count": 1,
                  "shots": [{"source": str(src), "start": 0.0, "dur": 6.0}]}
        opening = op.compile_opening_sequence(recipe, recipe["shots"])
        plan = op.prepend_opening_to_plan([], opening["clips"])
        out = d / "opening.mp4"
        mv_cut.render_mv_audio(plan, str(music), str(out), mat_dir=str(d), burn_text=True)
        self.assertTrue(out.exists())
        dur = float(subprocess.check_output(
            [FFPROBE, "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(out)], text=True).strip())
        # hook 2.5 + title 2.0 = 4.5s (context dropped: only 1 shot, reused)
        self.assertGreater(dur, 3.5)

    def test_short_source_clip_is_clamped_in_true_render(self):
        """Short-material true render: a 1s approved video shot must not produce
        a 2.5s hook clip — the clamp holds through a real ffmpeg render."""
        d = Path(tempfile.mkdtemp())
        src = d / "short.mp4"
        music = d / "bgm.mp3"
        subprocess.run([FFMPEG, "-y", "-f", "lavfi", "-i",
                        "testsrc=size=320x240:rate=30:duration=1",
                        "-pix_fmt", "yuv420p", str(src)], capture_output=True, check=True)
        subprocess.run([FFMPEG, "-y", "-f", "lavfi", "-i",
                        "sine=frequency=220:duration=4", str(music)],
                       capture_output=True, check=True)
        recipe = {"context_count": 0,
                  "shots": [{"source": str(src), "start": 0.0, "dur": 1.0}]}
        opening = op.compile_opening_sequence(recipe, recipe["shots"])
        self.assertEqual(opening["clips"][0]["extract_dur"], 1.0)
        plan = op.prepend_opening_to_plan([], opening["clips"])
        out = d / "short_open.mp4"
        mv_cut.render_mv_audio(plan, str(music), str(out), mat_dir=str(d), burn_text=False)
        self.assertTrue(out.exists())
        dur = float(subprocess.check_output(
            [FFPROBE, "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(out)], text=True).strip())
        self.assertLess(dur, 1.6)          # ~1.0s hook, not 2.5s


if __name__ == "__main__":
    unittest.main()
