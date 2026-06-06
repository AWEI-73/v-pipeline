import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import video_tools


class DashboardStateTest(unittest.TestCase):
    def test_cmd_state_preserves_existing_route_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            (workdir / "state.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "next_action": "review",
                        "segments": [
                            {
                                "segment": 1,
                                "title": "Needs Review",
                                "status": "needs_review",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (workdir / "script.json").write_text("[]", encoding="utf-8")

            args = SimpleNamespace(workdir=str(workdir), project="Demo", out=None)
            video_tools.cmd_state(args)

            state = json.loads((workdir / "state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["next_action"], "review")
            self.assertEqual(state["segments"][0]["status"], "needs_review")
            self.assertIn("dashboard", state)
            self.assertIn("nodes", state["dashboard"])

    def test_cmd_dashboard_and_story_map_embed_normalized_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            (workdir / "state.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "next_action": "await_material",
                        "segments": [
                            {
                                "segment": 1,
                                "title": "Need Material",
                                "status": "blocked",
                                "block_reason": "missing",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            dashboard_out = workdir / "dashboard_view.html"
            story_out = workdir / "story_map_view.html"
            video_tools.cmd_dashboard(SimpleNamespace(workdir=str(workdir), out=str(dashboard_out)))
            video_tools.cmd_story_map(SimpleNamespace(workdir=str(workdir), out=str(story_out)))

            dashboard_html = dashboard_out.read_text(encoding="utf-8")
            story_html = story_out.read_text(encoding="utf-8")
            self.assertIn('"run":', dashboard_html)
            self.assertIn('"nodes":', dashboard_html)
            self.assertIn('"run":', story_html)
            self.assertIn('"nodes":', story_html)


if __name__ == "__main__":
    unittest.main()
