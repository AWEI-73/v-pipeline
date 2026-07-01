import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.pipeline_home import summarize_run


class StoryFirstProviderHappyPathTest(unittest.TestCase):
    def test_story_first_wrapper_stops_at_real_provider_packet_without_test_renderer(self):
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "story"

            proc = subprocess.run(
                [
                    sys.executable,
                    "tools/story_first_provider_happy_path.py",
                    "--out",
                    str(run_dir),
                    "--title",
                    "Moonlit Forest Rabbit",
                    "--style",
                    "Japanese cute picture book style",
                    "--target-duration",
                    "60",
                    "--json",
                ],
                cwd=repo,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            result = json.loads(proc.stdout)
            self.assertTrue(result["ok"], result)
            self.assertEqual(result["next_action"], "call_image_generation_agent")
            self.assertTrue((run_dir / "video_intent.json").is_file())
            self.assertTrue((run_dir / "story_blueprint" / "material_needs.json").is_file())
            self.assertTrue((run_dir / "material_generation_fallback.json").is_file())
            self.assertTrue((run_dir / "provider_packet" / "generated_provider_packet.json").is_file())
            self.assertTrue((
                run_dir / "provider_packet" / "image_agent_handoff" / "image_agent_prompt_handoff.json"
            ).is_file())
            self.assertFalse((run_dir / "generated_material_production.json").exists())
            self.assertFalse((run_dir / "final.mp4").exists())

            packet = json.loads(
                (run_dir / "provider_packet" / "generated_provider_packet.json").read_text(encoding="utf-8-sig")
            )
            self.assertEqual(packet["artifact_role"], "generated_image_provider_packet")
            self.assertTrue(packet["test_renderer_forbidden_for_final_art"])
            self.assertGreater(len(packet["items"]), 0)
            self.assertIn("Japanese cute picture book style", json.dumps(packet, ensure_ascii=False))

            summary = summarize_run(run_dir)
            self.assertEqual(summary["mode"], "waiting")
            self.assertEqual(summary["cursor"], "generated_image_agent")
            self.assertEqual(summary["next"], "call_image_generation_agent")


if __name__ == "__main__":
    unittest.main()
