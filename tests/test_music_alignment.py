import subprocess
import tempfile
import types
import unittest
from pathlib import Path

from video_pipeline_core.music_structure import plan_music_alignment
from video_pipeline_core.vt_audio import _bgm_loop_chain, cmd_mix_audio
from video_pipeline_core.vt_core import FFMPEG, FFPROBE


class MusicAlignmentPlanTest(unittest.TestCase):
    def test_climax_aligns_to_highest_energy_from_nearest_structure_point(self):
        script = [
            {"segment": 1, "title": "opening"},
            {"segment": 2, "title": "develop"},
            {"segment": 3, "title": "climax"},
        ]
        timing = {
            "segments": [
                {"segment": 1, "start_sec": 0.0, "duration_sec": 4.0},
                {"segment": 2, "start_sec": 4.0, "duration_sec": 5.0},
                {"segment": 3, "start_sec": 9.0, "duration_sec": 4.0},
            ]
        }
        structure = {
            "sections": [
                {"index": 1, "start_sec": 0.0, "energy_score": 0.2},
                {"index": 2, "start_sec": 4.0, "energy_score": 0.4},
                {"index": 3, "start_sec": 12.0, "energy_score": 0.9},
                {"index": 4, "start_sec": 16.0, "energy_score": 0.5},
            ]
        }

        plan = plan_music_alignment(script, timing, structure)

        self.assertEqual(plan["bgm_offset_sec"], 4.0)
        self.assertEqual(plan["climax_segment"], 3)
        self.assertEqual(plan["energy_section_index"], 3)
        self.assertEqual(plan["alignment_error_sec"], 1.0)

    def test_missing_climax_or_energy_keeps_zero_offset(self):
        script = [{"segment": 1, "title": "opening"}]
        timing = {"segments": [{"segment": 1, "start_sec": 0.0, "duration_sec": 3.0}]}
        structure = {"sections": [{"index": 1, "start_sec": 0.0, "energy_score": None}]}

        plan = plan_music_alignment(script, timing, structure)

        self.assertEqual(plan["bgm_offset_sec"], 0.0)
        self.assertEqual(plan["reason"], "no_climax_or_energy_section")


class BgmOffsetChainTest(unittest.TestCase):
    def test_missing_bgm_duration_keeps_legacy_single_input(self):
        self.assertEqual(_bgm_loop_chain(voice_dur=12.0, bgm_dur=None, bgm_offset=3.0),
                         ("", "1:a"))

    def test_offset_trims_each_bgm_copy_before_looping(self):
        chain, src = _bgm_loop_chain(voice_dur=12.0, bgm_dur=10.0, bgm_offset=4.0)

        self.assertIn("atrim=start=4.000", chain)
        self.assertEqual(chain.count("atrim=start=4.000"), 3)
        self.assertEqual(chain.count("acrossfade"), 2)
        self.assertEqual(src, "bgmlp2")

    def test_offset_mix_renders_to_voice_duration(self):
        with tempfile.TemporaryDirectory() as directory:
            voice = Path(directory) / "voice.wav"
            bgm = Path(directory) / "bgm.wav"
            out = Path(directory) / "mixed.wav"
            for path, duration, frequency in ((voice, 4, 440), (bgm, 10, 330)):
                subprocess.run([
                    FFMPEG, "-y", "-f", "lavfi", "-i",
                    f"sine=frequency={frequency}:duration={duration}",
                    "-af", "aformat=channel_layouts=stereo", str(path),
                ], capture_output=True, check=True)
            cmd_mix_audio(types.SimpleNamespace(
                voice=str(voice),
                bgm=str(bgm),
                out=str(out),
                bgm_vol=0.2,
                bgm_offset=3.0,
                duck=True,
            ))
            probe = subprocess.run([
                FFPROBE, "-v", "error", "-show_entries", "format=duration",
                "-of", "csv=p=0", str(out),
            ], capture_output=True, text=True, check=True)
            self.assertAlmostEqual(float(probe.stdout.strip()), 4.0, delta=0.3)


if __name__ == "__main__":
    unittest.main()
