"""Real BGM source — music-fetch (yt-dlp audio) + pipeline bgm resolution plan.

Pixabay has no public music API, so yt-dlp audio extraction is the working source
(matches the actual workflow); jamendo is a documented provider seam. These tests
cover the pure command/plan builders — no network.
"""
import os
import tempfile
import types
import unittest
from unittest.mock import patch

import video_tools as vt
import video_pipeline as vp
from video_pipeline_core import vt_audio


class CmdMusicFetchInvokeTest(unittest.TestCase):
    """實際呼叫 cmd_music_fetch(mock yt-dlp/ffprobe)——抓「拆模組漏 import」這類
    pure-builder 測不到的執行期 NameError(如 vt_audio 漏 from pathlib import Path)。"""

    def test_cmd_music_fetch_yt_runs_without_nameerror(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "m.mp3")
            args = types.SimpleNamespace(source="yt", query="lofi calm", max_dur=240, out=out)

            def fake_run(cmd):
                self.assertIn("--ffmpeg-location", cmd)   # Path(FFMPEG).parent 那段有跑到
                with open(out, "wb") as f:
                    f.write(b"x")                         # 模擬 yt-dlp 產出 mp3
                return types.SimpleNamespace(returncode=0, stderr="")

            with patch("video_pipeline_core.vt_audio.run", fake_run), \
                 patch("video_pipeline_core.vt_audio._audio_duration", lambda p: 200.0):
                vt_audio.cmd_music_fetch(args)            # 不可 NameError(Path)
            self.assertTrue(os.path.exists(out))


class MusicYtdlpCmdTest(unittest.TestCase):
    def test_cmd_searches_n_hits_and_extracts_mp3(self):
        cmd = vt._music_ytdlp_cmd("lofi calm piano", "/tmp/bgm_track", "/opt/ff")
        # ytsearchN (not 1) so one bad/filtered top hit doesn't leave us empty
        self.assertIn("ytsearch5:lofi calm piano", cmd)
        self.assertIn("-x", cmd)
        self.assertEqual(cmd[cmd.index("--audio-format") + 1], "mp3")
        self.assertIn("/tmp/bgm_track.%(ext)s", cmd)
        self.assertEqual(cmd[cmd.index("--ffmpeg-location") + 1], "/opt/ff")
        # stop after the first duration-suitable match
        self.assertEqual(cmd[cmd.index("--max-downloads") + 1], "1")

    def test_default_duration_window_floor_and_ceiling(self):
        cmd = vt._music_ytdlp_cmd("epic", "/tmp/x", "/opt/ff")
        flt = cmd[cmd.index("--match-filter") + 1]
        self.assertEqual(flt, "duration > 30 & duration < 600")   # 預設 30s–10min

    def test_max_dur_sets_ceiling(self):
        cmd = vt._music_ytdlp_cmd("epic", "/tmp/x", "/opt/ff", max_dur=180)
        flt = cmd[cmd.index("--match-filter") + 1]
        self.assertEqual(flt, "duration > 30 & duration < 180")


class BgmPlanTest(unittest.TestCase):
    def test_dict_routes_to_fetch(self):
        kind, payload = vp._bgm_plan({"query": "lofi", "source": "yt"})
        self.assertEqual(kind, "fetch")
        self.assertEqual(payload["query"], "lofi")

    def test_string_routes_to_local(self):
        kind, payload = vp._bgm_plan("calm")
        self.assertEqual(kind, "local")
        self.assertEqual(payload, "calm")

    def test_falsy_routes_to_none(self):
        self.assertEqual(vp._bgm_plan(None), ("none", None))
        self.assertEqual(vp._bgm_plan(""), ("none", None))


if __name__ == "__main__":
    unittest.main()
