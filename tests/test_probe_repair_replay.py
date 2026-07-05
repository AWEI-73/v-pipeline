import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core.replay_acceptance import build_probe_repair_replay_report


class ProbeRepairReplayTest(unittest.TestCase):
    def test_probe_repair_20260704_report_covers_required_checks(self):
        report = build_probe_repair_replay_report(Path.cwd())

        self.assertEqual(report["artifact_role"], "probe_repair_replay_acceptance")
        self.assertEqual(report["scenario"], "probe-repair-20260704")
        self.assertTrue(report["ok"], report.get("failures"))
        check_ids = {check["id"] for check in report["checks"]}
        self.assertEqual(
            check_ids,
            {
                "storybook_stock_story",
                "material_intake_boundary",
                "delivery_placeholder_stream_guard",
                "dotenv_provider_visibility",
            },
        )
        self.assertGreaterEqual(len(report["artifacts"]), 4)
        self.assertEqual(report["failures"], [])

        story = next(check for check in report["checks"] if check["id"] == "storybook_stock_story")
        self.assertGreater(story["metrics"]["timeline_clip_count"], 0)
        self.assertGreater(story["metrics"]["music_section_count"], 0)
        self.assertIn("video", story["metrics"]["final_streams"])
        self.assertIn("audio", story["metrics"]["final_streams"])

        material = next(check for check in report["checks"] if check["id"] == "material_intake_boundary")
        self.assertTrue(material["metrics"]["missing_folder_needs_context"])
        self.assertTrue(material["metrics"]["bad_mp4_rejected"])
        self.assertEqual(material["metrics"]["target_length_5h_sec"], 18000.0)

    def test_probe_repair_20260704_cli_writes_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "probe_repair_replay_report.json"
            proc = subprocess.run(
                [
                    sys.executable,
                    "video_tools.py",
                    "replay-acceptance",
                    "--scenario",
                    "probe-repair-20260704",
                    "--out",
                    str(out),
                ],
                cwd=Path.cwd(),
                text=True,
                capture_output=True,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["scenario"], "probe-repair-20260704")


if __name__ == "__main__":
    unittest.main()
