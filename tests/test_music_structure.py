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

    def test_write_music_structure_fails_closed_when_probe_yields_no_sections(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "music_structure.json"

            result = ms.write_music_structure(
                "bgm.mp3",
                out,
                detector=lambda _path: (117.454, [0.07]),
                duration_detector=lambda _path: 60.0,
                every_n_beats=4,
            )
            saved = json.loads(out.read_text(encoding="utf-8"))

        self.assertFalse(result["ok"])
        self.assertEqual(result["stage"], "music_structure")
        self.assertEqual(result["next_action"], "repair_or_rerun_soundtrack_probe")
        self.assertEqual(saved["sections"], [])
        self.assertEqual(saved["status"], "blocked")
        self.assertEqual(saved["errors"][0]["rule"], "music_structure_empty_sections")

    def test_write_music_structure_uses_full_track_section_for_short_fixture_audio(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "music_structure.json"

            result = ms.write_music_structure(
                "short-fixture.wav",
                out,
                detector=lambda _path: (0.0, [0.07]),
                duration_detector=lambda _path: 5.0,
                every_n_beats=4,
            )
            saved = json.loads(out.read_text(encoding="utf-8"))

        self.assertTrue(result["ok"])
        self.assertEqual(len(saved["sections"]), 1)
        self.assertEqual(saved["sections"][0]["source"], "short_audio_fallback")
        self.assertEqual(saved["sections"][0]["end_sec"], 5.0)

    def test_section_energy_detector_populates_existing_sections(self):
        structure = ms.build_music_structure(
            tempo_bpm=120,
            beat_times=[0, 1, 2, 3, 4],
            every_n_beats=2,
        )
        calls = []

        def detector(path, start, duration):
            calls.append((path, start, duration))
            return {-0.0: -28.0, 2.0: -12.0}[start]

        result = ms.annotate_section_energy(structure, "song.mp3", detector=detector)

        self.assertEqual([section["energy_score"] for section in result["sections"]],
                         [-28.0, -12.0])
        self.assertEqual(calls, [("song.mp3", 0.0, 2.0), ("song.mp3", 2.0, 2.0)])


if __name__ == "__main__":
    unittest.main()
