import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core import punctuation as pn
from video_pipeline_core.vt_core import FFMPEG, FFPROBE

ASSET_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "sfx")


def _clip(role_key, role, dur, **extra):
    c = {"extract_dur": dur, role_key: role}
    c.update(extra)
    return c


class ResolveTest(unittest.TestCase):
    def test_anchor_resolves_to_timeline_start(self):
        # opening hook (2.5) then title_reveal (2.0) at t=2.5
        plan = [_clip("opening_role", "hook", 2.5, segment=0),
                _clip("opening_role", "title_reveal", 2.0, segment=0)]
        cues = [{"type": "hit", "anchor": "title_reveal", "segment": 0}]
        res = pn.resolve_punctuation_cues(plan, cues, asset_dir=ASSET_DIR)
        self.assertEqual(len(res["cues"]), 1)
        self.assertEqual(res["cues"][0]["start_sec"], 2.5)
        self.assertTrue(res["cues"][0]["asset"].endswith("hit_1.wav"))

    def test_unknown_anchor_is_dropped(self):
        plan = [_clip("opening_role", "hook", 2.5, segment=0)]
        cues = [{"type": "hit", "anchor": "title_reveal", "segment": 0}]
        res = pn.resolve_punctuation_cues(plan, cues, asset_dir=ASSET_DIR)
        self.assertEqual(res["cues"], [])
        self.assertEqual(res["dropped"][0]["reason"], "anchor_missing:title_reveal")

    def test_beat_payoff_anchor_scoped_to_segment(self):
        plan = [_clip("beat_role", "payoff", 2.0, segment=1),
                _clip("beat_role", "payoff", 2.0, segment=2)]
        cues = [{"type": "hit", "anchor": "payoff", "segment": 2}]
        res = pn.resolve_punctuation_cues(plan, cues, asset_dir=ASSET_DIR)
        self.assertEqual(res["cues"][0]["start_sec"], 2.0)   # second payoff, after first 2.0s

    def test_no_cues_yields_empty_plan(self):
        res = pn.resolve_punctuation_cues([], [], asset_dir=ASSET_DIR)
        self.assertEqual(res["cues"], [])


class RealMixTest(unittest.TestCase):
    def test_punctuation_mixes_real_audio_at_anchor_time(self):
        """Real audio-mix proof: a resolved hit raises audio energy at its
        timeline anchor versus the silent baseline there."""
        self.assertTrue(os.path.exists(os.path.join(ASSET_DIR, "hit_1.wav")),
                        "CC0 sfx asset must exist")
        d = Path(tempfile.mkdtemp())
        base = d / "base.wav"
        out = d / "mixed.wav"
        # near-silent base so the hit is unambiguous
        subprocess.run([FFMPEG, "-y", "-f", "lavfi", "-i",
                        "anullsrc=r=48000:cl=stereo", "-t", "5", str(base)],
                       capture_output=True, check=True)
        plan = [_clip("opening_role", "hook", 3.0, segment=0),
                _clip("opening_role", "title_reveal", 2.0, segment=0)]
        cues = [{"type": "hit", "anchor": "title_reveal", "segment": 0}]
        resolved = pn.resolve_punctuation_cues(plan, cues, asset_dir=ASSET_DIR)
        self.assertEqual(resolved["cues"][0]["start_sec"], 3.0)
        pn.mix_punctuation_audio(str(base), resolved, str(out))
        self.assertTrue(out.exists())

        def vol(path, ss, t):
            r = subprocess.run([FFMPEG, "-ss", str(ss), "-t", str(t), "-i", path,
                                "-af", "volumedetect", "-f", "null", "-"],
                               capture_output=True, text=True)
            for line in r.stderr.splitlines():
                if "mean_volume" in line:
                    return float(line.split("mean_volume:")[1].split("dB")[0])
            return -91.0
        at_hit = vol(str(out), 3.0, 0.4)     # the hit lands at 3.0s
        silent = vol(str(out), 0.5, 0.4)     # baseline (no cue here)
        self.assertGreater(at_hit, silent + 3.0)   # hit clearly louder than baseline


if __name__ == "__main__":
    unittest.main()
