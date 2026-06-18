import json
import tempfile
import unittest
from pathlib import Path

from tools.generated_material_flow_acceptance import run_acceptance_cases


class GeneratedMaterialFlowAcceptanceTest(unittest.TestCase):
    def test_two_comic_cases_run_from_needs_to_candidate_maps(self):
        with tempfile.TemporaryDirectory() as td:
            report = run_acceptance_cases(Path(td))

            self.assertTrue(report["ok"], report.get("errors"))
            self.assertEqual(len(report["cases"]), 2)
            for case in report["cases"]:
                self.assertEqual(case["initial_delta"]["summary"]["missing"], 2)
                self.assertGreaterEqual(case["generated"]["summary"]["image_count"], 4)
                self.assertEqual(case["after_generation_delta"]["summary"]["missing"], 0)
                self.assertEqual(case["after_generation_delta"]["summary"]["thin"], 2)
                self.assertEqual(case["after_review_delta"]["summary"]["covered"], 2)
                self.assertGreaterEqual(case["director_score"], 80)
                self.assertTrue(Path(case["refs"]["contact_sheet"]).exists())
            self.assertTrue((Path(td) / "FLOW_REVIEW.md").exists())


if __name__ == "__main__":
    unittest.main()
