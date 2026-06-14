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

    def test_ending_payoff_anchor_resolves(self):
        plan = [_clip("beat_role", "context", 2.0, segment=1),
                _clip("ending_role", "payoff", 2.0, segment=2)]
        cues = [{"type": "hit", "anchor": "payoff", "segment": 2}]
        res = pn.resolve_punctuation_cues(plan, cues, asset_dir=ASSET_DIR)
        self.assertEqual(res["cues"][0]["start_sec"], 2.0)

    def test_no_cues_yields_empty_plan(self):
        res = pn.resolve_punctuation_cues([], [], asset_dir=ASSET_DIR)
        self.assertEqual(res["cues"], [])

    def test_xfade_overlap_shifts_anchor_time_earlier(self):
        # group A 3.0s, then title_reveal group crossfading in over 0.5s ->
        # title starts at 3.0 - 0.5 = 2.5, not 3.0.
        plan = [_clip("opening_role", "hook", 3.0, segment=0),
                _clip("opening_role", "title_reveal", 2.0, segment=1,
                      transition="xfade", transition_duration=0.5)]
        cues = [{"type": "hit", "anchor": "title_reveal", "segment": 1}]
        res = pn.resolve_punctuation_cues(plan, cues, asset_dir=ASSET_DIR)
        self.assertEqual(res["cues"][0]["start_sec"], 2.5)

    def test_cut_transition_does_not_shift_time(self):
        plan = [_clip("opening_role", "hook", 3.0, segment=0),
                _clip("opening_role", "title_reveal", 2.0, segment=0,
                      transition="cut", transition_duration=0.5)]
        res = pn.resolve_punctuation_cues(
            plan, [{"type": "hit", "anchor": "title_reveal", "segment": 0}], asset_dir=ASSET_DIR)
        self.assertEqual(res["cues"][0]["start_sec"], 3.0)

    def test_oversized_xfade_is_clamped_to_incoming_group_duration(self):
        plan = [_clip("beat_role", "context", 3.0, segment=1),
                _clip("beat_role", "payoff", 0.2, segment=2,
                      transition="xfade", transition_duration=0.5)]
        res = pn.resolve_punctuation_cues(
            plan, [{"type": "hit", "anchor": "payoff", "segment": 2}], asset_dir=ASSET_DIR)
        self.assertEqual(res["cues"][0]["start_sec"], 2.8)

    def test_transition_applies_between_segment_groups_not_within_group(self):
        plan = [_clip("beat_role", "context", 1.0, segment=1),
                _clip("beat_role", "primary_action", 1.0, segment=1,
                      transition="xfade", transition_duration=0.5),
                _clip("beat_role", "payoff", 1.0, segment=2,
                      transition="xfade", transition_duration=0.5)]
        cues = [{"type": "hit", "anchor": "primary_action", "segment": 1},
                {"type": "hit", "anchor": "payoff", "segment": 2}]
        res = pn.resolve_punctuation_cues(plan, cues, asset_dir=ASSET_DIR)
        self.assertEqual([cue["start_sec"] for cue in res["cues"]], [1.0, 1.5])

    def test_oversized_xfade_never_produces_negative_start(self):
        plan = [_clip("beat_role", "context", 0.1, segment=1),
                _clip("beat_role", "payoff", 0.2, segment=2,
                      transition="xfade", transition_duration=5.0)]
        res = pn.resolve_punctuation_cues(
            plan, [{"type": "hit", "anchor": "payoff", "segment": 2}], asset_dir=ASSET_DIR)
        self.assertEqual(res["cues"][0]["start_sec"], 0.0)


class RemuxFailureTest(unittest.TestCase):
    def test_remux_failure_raises_and_reports_no_mix(self):
        plan = [_clip("opening_role", "title_reveal", 2.0, segment=0)]
        cues = [{"type": "hit", "anchor": "title_reveal", "segment": 0}]
        # usable assets exist, but the video input does not -> ffmpeg fails
        with self.assertRaises(pn.PunctuationMixError):
            pn.apply_punctuation_to_video("/no/such/video.mp4", plan, cues, asset_dir=ASSET_DIR)

    def test_missing_assets_is_no_cues_not_failure(self):
        plan = [_clip("opening_role", "title_reveal", 2.0, segment=0)]
        cues = [{"type": "hit", "anchor": "title_reveal", "segment": 0}]
        res = pn.apply_punctuation_to_video("/no/such/video.mp4", plan, cues,
                                            asset_dir="/no/such/sfx_dir")
        self.assertEqual(res["status"], "no_cues")
        self.assertEqual(res["cues_mixed"], 0)

    def test_successful_mix_reports_ok_with_count(self):
        d = Path(tempfile.mkdtemp())
        vid = d / "v.mp4"
        subprocess.run([FFMPEG, "-y", "-f", "lavfi", "-i",
                        "testsrc=size=160x120:rate=30:duration=5",
                        "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
                        "-t", "5", "-c:v", "libx264", "-c:a", "aac",
                        "-pix_fmt", "yuv420p", str(vid)], capture_output=True, check=True)
        plan = [_clip("opening_role", "hook", 3.0, segment=0),
                _clip("opening_role", "title_reveal", 2.0, segment=0)]
        cues = [{"type": "hit", "anchor": "title_reveal", "segment": 0}]
        res = pn.apply_punctuation_to_video(str(vid), plan, cues, asset_dir=ASSET_DIR)
        self.assertEqual(res["status"], "ok")
        self.assertEqual(res["cues_mixed"], 1)
        self.assertTrue(vid.exists())


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
