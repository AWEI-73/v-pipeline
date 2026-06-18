import tempfile
import unittest
from pathlib import Path

from tools.story_to_generated_material_e2e import run_story_to_generated_material_e2e


class StoryToGeneratedMaterialE2ETest(unittest.TestCase):
    def test_story_soul_blueprint_flows_to_generated_accepted_material(self):
        with tempfile.TemporaryDirectory() as td:
            report = run_story_to_generated_material_e2e(Path(td))

            self.assertTrue(report["ok"], report.get("errors"))
            self.assertEqual(report["case_id"], "postcard_city_sky")
            self.assertTrue(report["story_blueprint"]["ok"])
            self.assertGreaterEqual(report["story_blueprint"]["beat_count"], 5)
            self.assertGreaterEqual(report["story_blueprint"]["minimum_material_count"], 18)
            self.assertEqual(report["initial_delta"]["summary"]["missing"],
                             report["story_blueprint"]["need_count"])
            self.assertEqual(report["after_generation_delta"]["summary"]["missing"], 0)
            self.assertGreaterEqual(report["after_generation_delta"]["summary"]["thin"], 1)
            self.assertEqual(report["after_review_delta"]["summary"]["covered"],
                             report["story_blueprint"]["need_count"])
            self.assertGreaterEqual(report["director_score"], 85)
            self.assertTrue(Path(report["refs"]["contact_sheet"]).exists())
            self.assertTrue(Path(report["refs"]["review_report"]).exists())


if __name__ == "__main__":
    unittest.main()
