import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core.replay_acceptance import build_probe_repair_replay_report


class ProbeRepairReplayTest(unittest.TestCase):
    def test_probe_repair_20260704_report_runs_from_clean_temp_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            clean_root = Path(tmp)
            self.assertFalse((clean_root / ".tmp" / "r3_acceptance_probe").exists())
            self.assertFalse((clean_root / "runs" / "storybook-stock-story").exists())

            report = build_probe_repair_replay_report(clean_root)

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
        artifact_text = "\n".join(report["artifacts"])
        self.assertNotIn(".tmp/r3_acceptance_probe", artifact_text)
        self.assertNotIn("runs/storybook-stock-story", artifact_text)

        story = next(check for check in report["checks"] if check["id"] == "storybook_stock_story")
        self.assertGreater(story["metrics"]["timeline_clip_count"], 0)
        self.assertGreater(story["metrics"]["music_section_count"], 0)
        self.assertIn("video", story["metrics"]["final_streams"])
        self.assertIn("audio", story["metrics"]["final_streams"])

        material = next(check for check in report["checks"] if check["id"] == "material_intake_boundary")
        self.assertTrue(material["metrics"]["missing_folder_needs_context"])
        self.assertTrue(material["metrics"]["bad_mp4_rejected"])
        self.assertEqual(material["metrics"]["target_length_5h_sec"], 18000.0)

    def test_probe_repair_delivery_placeholder_check_is_behavior_based(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = build_probe_repair_replay_report(Path(tmp))

        delivery = next(check for check in report["checks"] if check["id"] == "delivery_placeholder_stream_guard")
        self.assertTrue(delivery["ok"], delivery)
        self.assertTrue(delivery["metrics"]["placeholder_final_rejected"])
        self.assertTrue(delivery["metrics"]["finding_mentions_stream_or_playable_media"])
        self.assertIn("media_probe_failed", delivery["metrics"]["blocking_rules"])
        metric_names = set(delivery["metrics"])
        self.assertNotIn("guard_message_present", metric_names)
        self.assertNotIn("placeholder_regression_test_present", metric_names)

    def test_probe_repair_dotenv_provider_visibility_is_behavior_based(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = build_probe_repair_replay_report(Path(tmp))

        dotenv = next(check for check in report["checks"] if check["id"] == "dotenv_provider_visibility")
        self.assertTrue(dotenv["ok"], dotenv)
        self.assertTrue(dotenv["metrics"]["env_loader_reads_dotenv"])
        self.assertTrue(dotenv["metrics"]["preflight_provider_visibility_uses_loaded_env"])
        self.assertTrue(dotenv["metrics"]["stock_provider_env_lookup_uses_loaded_value"])
        self.assertTrue(dotenv["metrics"]["soundtrack_provider_env_lookup_uses_loaded_value"])
        metric_names = set(dotenv["metrics"])
        self.assertNotIn("video_tools_applies_dotenv", metric_names)
        self.assertNotIn("preflight_uses_env_loader", metric_names)

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
