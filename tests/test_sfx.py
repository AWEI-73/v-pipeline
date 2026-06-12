import json
import audioop
import subprocess
import tempfile
import types
import unittest
import wave
from pathlib import Path

from video_pipeline_core import sfx
from video_pipeline_core.vt_audio import cmd_mix_sfx
from video_pipeline_core.vt_core import FFMPEG, FFPROBE


class SfxPlanTest(unittest.TestCase):
    def test_section_changes_get_whoosh_and_title_cards_get_hit(self):
        script = [
            {"segment": 1, "title": "opening"},
            {"segment": 2, "title": "develop"},
            {"segment": 3, "title": "develop", "effects": {"title_card": {"text": "Work"}}},
            {"segment": 4, "title": "closing"},
        ]
        timing = {"segments": [
            {"segment": 1, "start_sec": 0.0},
            {"segment": 2, "start_sec": 9.0},
            {"segment": 3, "start_sec": 18.0},
            {"segment": 4, "start_sec": 27.0},
        ]}

        plan = sfx.plan_sfx_cues(script, timing, "assets/sfx")

        self.assertEqual(
            [(x["type"], x["segment"], x["start_sec"]) for x in plan["cues"]],
            [("whoosh", 2, 9.0), ("hit", 3, 18.0), ("whoosh", 4, 27.0)],
        )
        self.assertTrue(all(x["volume"] == 0.15 for x in plan["cues"]))

    def test_repeated_cue_types_rotate_assets_deterministically(self):
        script = [
            {"segment": 1, "title": "a"},
            {"segment": 2, "title": "b"},
            {"segment": 3, "title": "c"},
        ]
        timing = {"segments": [
            {"segment": 1, "start_sec": 0.0},
            {"segment": 2, "start_sec": 2.0},
            {"segment": 3, "start_sec": 4.0},
        ]}

        plan = sfx.plan_sfx_cues(script, timing, "assets/sfx")

        self.assertTrue(plan["cues"][0]["asset"].endswith("whoosh_1.wav"))
        self.assertTrue(plan["cues"][1]["asset"].endswith("whoosh_2.wav"))


class SfxFilterTest(unittest.TestCase):
    def test_filter_delays_and_mixes_each_cue_with_base_audio(self):
        cues = [
            {"start_sec": 1.25, "volume": 0.15},
            {"start_sec": 3.5, "volume": 0.1},
        ]

        graph, label = sfx.build_sfx_filter(cues)

        self.assertIn("adelay=1250|1250", graph)
        self.assertIn("adelay=3500|3500", graph)
        self.assertIn("amerge=inputs=3", graph)
        self.assertIn("pan=stereo|c0=c0+c2+c4|c1=c1+c3+c5", graph)
        self.assertNotIn("alimiter", graph)
        self.assertEqual(label, "sfxmixed")


class SfxRenderTest(unittest.TestCase):
    def test_real_mix_keeps_base_duration(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            base = root / "base.wav"
            cue = root / "cue.wav"
            plan = root / "sfx_plan.json"
            out = root / "mixed.wav"
            subprocess.run([FFMPEG, "-y", "-f", "lavfi", "-i",
                            "sine=frequency=220:duration=3", str(base)],
                           capture_output=True, check=True)
            subprocess.run([FFMPEG, "-y", "-f", "lavfi", "-i",
                            "sine=frequency=880:duration=0.2",
                            "-af", "aformat=channel_layouts=stereo",
                            "-ar", "48000", str(cue)],
                           capture_output=True, check=True)
            plan.write_text(json.dumps({"cues": [{
                "type": "hit", "asset": str(cue), "start_sec": 1.0, "volume": 0.15,
            }]}), encoding="utf-8")

            cmd_mix_sfx(types.SimpleNamespace(base=str(base), plan=str(plan), out=str(out)))

            duration = float(subprocess.check_output([
                FFPROBE, "-v", "error", "-show_entries", "format=duration",
                "-of", "csv=p=0", str(out),
            ], text=True).strip())
            self.assertAlmostEqual(duration, 3.0, delta=0.1)
            with wave.open(str(base), "rb") as src:
                base_rms = audioop.rms(src.readframes(src.getframerate() // 2), src.getsampwidth())
            with wave.open(str(out), "rb") as src:
                mixed_rms = audioop.rms(src.readframes(src.getframerate() // 2), src.getsampwidth())
            self.assertAlmostEqual(mixed_rms / base_rms, 1.0, delta=0.08)


if __name__ == "__main__":
    unittest.main()
