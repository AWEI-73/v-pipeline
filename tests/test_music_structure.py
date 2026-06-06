"""music_structure — canonical music timing artifact for V3 P1."""
import json
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core import music_structure as ms


class MusicStructureTest(unittest.TestCase):
    def test_build_music_structure_from_beats(self):
        s = ms.build_music_structure(
            tempo_bpm=120.0,
            beat_times=[0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0],
            source_audio="bgm.mp3",
            every_n_beats=4,
        )
        self.assertEqual(s["music_structure_version"], 1)
        self.assertEqual(s["source_audio"], "bgm.mp3")
        self.assertEqual(s["tempo_bpm"], 120.0)
        self.assertEqual(s["beat_count"], 9)
        self.assertEqual(len(s["sections"]), 2)
        self.assertEqual(s["sections"][0]["cut_density_hint"], "medium")
        self.assertEqual(s["sections"][0]["Start_Time"], "00:00.0")
        self.assertEqual(s["sections"][0]["End_Time"], "00:02.0")

    def test_write_music_structure_uses_detector_and_writes_json(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "music_structure.json"

            def detector(path):
                self.assertEqual(path, "song.mp3")
                return 90.0, [0.0, 0.75, 1.5, 2.25, 3.0]

            result = ms.write_music_structure("song.mp3", out, detector=detector, every_n_beats=2)
            saved = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(result["music_structure"], str(out))
            self.assertEqual(saved["tempo_bpm"], 90.0)
            self.assertEqual(saved["beats"][1], 0.75)
            self.assertEqual(len(saved["sections"]), 2)


if __name__ == "__main__":
    unittest.main()
