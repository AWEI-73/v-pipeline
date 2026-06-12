"""BGM loop seam: crossfaded copies instead of aloop hard joins (city-day lesson:
a 122.9s epic track hard-looped into a 297s film restarts mid-climax twice)."""
import json
import os
import subprocess
import tempfile
import types
import unittest
from pathlib import Path

from video_pipeline_core.vt_audio import _bgm_loop_chain, cmd_mix_audio
from video_pipeline_core.vt_core import FFMPEG


def _sine(path, dur, freq=440):
    subprocess.run([FFMPEG, "-y", "-f", "lavfi", "-i",
                    f"sine=frequency={freq}:duration={dur}",
                    "-ac", "2", "-ar", "48000", str(path)],
                   capture_output=True, check=True)


def _dur(path):
    out = subprocess.run([FFMPEG.replace("ffmpeg", "ffprobe"), "-v", "error",
                          "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True)
    return float(out.stdout.strip())


class BgmLoopChainTest(unittest.TestCase):
    def test_no_loop_when_bgm_long_enough(self):
        chain, src = _bgm_loop_chain(voice_dur=30.0, bgm_dur=120.0)
        self.assertEqual((chain, src), ("", "1:a"))

    def test_crossfade_chain_when_bgm_short(self):
        chain, src = _bgm_loop_chain(voice_dur=297.6, bgm_dur=122.9)
        self.assertIn("acrossfade", chain)
        self.assertEqual(src, "bgmlp2")          # 3 copies → 2 crossfades
        self.assertEqual(chain.count("acrossfade"), 2)

    def test_copies_are_capped(self):
        chain, _ = _bgm_loop_chain(voice_dur=10000.0, bgm_dur=10.0)
        self.assertLessEqual(chain.count("acrossfade") + 1, 12)


class MixAudioRenderTest(unittest.TestCase):
    """Real ffmpeg render: output duration must equal the voice (ground truth)."""

    def _mix(self, voice_dur, bgm_dur, duck=False):
        with tempfile.TemporaryDirectory() as d:
            voice = Path(d) / "voice.wav"
            bgm = Path(d) / "bgm.wav"
            out = Path(d) / "mixed.wav"
            _sine(voice, voice_dur, 440)
            _sine(bgm, bgm_dur, 330)
            args = types.SimpleNamespace(voice=str(voice), bgm=str(bgm),
                                         out=str(out), bgm_vol=0.2, duck=duck)
            cmd_mix_audio(args)
            return _dur(out)

    def test_looped_bgm_mix_matches_voice_duration(self):
        self.assertAlmostEqual(self._mix(voice_dur=12.0, bgm_dur=5.0), 12.0, delta=0.3)

    def test_long_bgm_trimmed_to_voice(self):
        self.assertAlmostEqual(self._mix(voice_dur=4.0, bgm_dur=10.0), 4.0, delta=0.3)

    def test_duck_path_with_loop(self):
        self.assertAlmostEqual(self._mix(voice_dur=12.0, bgm_dur=5.0, duck=True),
                               12.0, delta=0.3)


if __name__ == "__main__":
    unittest.main()
