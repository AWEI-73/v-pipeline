import unittest

from video_pipeline_core.source_section_map import build_source_section_map


class SourceSectionMapTests(unittest.TestCase):
    def test_audio_change_near_shot_boundary_becomes_section_boundary(self):
        energy_curve = []
        for index in range(75):
            start = index * 4.0
            energy = 0.18
            if 48 <= index <= 51:
                energy = 0.72
            elif index > 51:
                energy = 0.35
            energy_curve.append({
                "start_sec": start,
                "end_sec": start + 4.0,
                "relative_energy": energy,
            })
        shots = [
            (0.0, 42.0),
            (42.0, 101.0),
            (101.0, 196.0),
            (196.0, 207.0),
            (207.0, 261.0),
            (261.0, 300.0),
        ]

        result = build_source_section_map(
            duration_sec=300.0,
            energy_curve=energy_curve,
            shots=shots,
            target_section_sec=80.0,
            min_section_sec=20.0,
        )

        boundaries = result["boundaries"]
        self.assertTrue(any(196.0 <= b["time_sec"] <= 207.0 for b in boundaries))
        boundary = next(b for b in boundaries if 196.0 <= b["time_sec"] <= 207.0)
        self.assertIn("audio_energy_change", boundary["reasons"])
        self.assertIn("visual_shot_boundary", boundary["reasons"])
        self.assertGreater(len(result["sections"]), 4)


if __name__ == "__main__":
    unittest.main()
