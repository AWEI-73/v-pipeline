import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.video_intent_acceptance import run_video_intent_acceptance


class VideoIntentAcceptanceTest(unittest.TestCase):
    def test_acceptance_harness_covers_vip0_route_cases(self):
        report = run_video_intent_acceptance()

        self.assertEqual(report["artifact_role"], "video_intent_acceptance")
        self.assertTrue(report["ok"], report.get("errors"))
        self.assertEqual(report["case_count"], 5)
        by_id = {case["id"]: case for case in report["cases"]}
        self.assertEqual(by_id["teaching_existing"]["actual"]["entry_path"], "material-first")
        self.assertEqual(by_id["teaching_existing"]["actual"]["legacy_route"], "existing-material-first")
        self.assertEqual(by_id["children_story_no_material"]["actual"]["entry_path"], "structure-first")
        self.assertEqual(by_id["children_story_no_material"]["actual"]["legacy_route"], "story-first")
        self.assertTrue(by_id["children_story_no_material"]["actual"]["needs_generated_material_fallback"])
        self.assertEqual(by_id["graduation_partial"]["actual"]["entry_path"], "material-first")
        self.assertEqual(by_id["graduation_partial"]["actual"]["legacy_route"], "hybrid")
        self.assertEqual(by_id["vague_request"]["actual"]["entry_path"], "needs-context")
        self.assertGreaterEqual(len(by_id["vague_request"]["actual"]["required_followup_questions"]), 4)
        self.assertEqual(by_id["vague_graduation_direct_cut_request"]["actual"]["video_type"], "graduation-event")
        self.assertEqual(by_id["vague_graduation_direct_cut_request"]["actual"]["entry_path"], "needs-context")
        self.assertEqual(by_id["vague_graduation_direct_cut_request"]["actual"]["handoff_to"], "ask_followup")
        self.assertGreaterEqual(
            len(by_id["vague_graduation_direct_cut_request"]["actual"]["required_followup_questions"]),
            4,
        )
        self.assertIn("stage_0_entry_lock", report["boundaries"])
        self.assertIn("no_direct_cut_from_fuzzy_request", report["boundaries"])

    def test_cli_writes_acceptance_report(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "video_intent_acceptance.json"
            subprocess.run(
                [
                    sys.executable,
                    "video_tools.py",
                    "video-intent-acceptance",
                    "--out",
                    str(out),
                ],
                check=True,
                cwd=Path(__file__).resolve().parents[1],
                stdout=subprocess.DEVNULL,
            )

            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertTrue(payload["ok"], payload)
            self.assertEqual(payload["artifact_role"], "video_intent_acceptance")


if __name__ == "__main__":
    unittest.main()
