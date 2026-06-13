import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import video_tools


class JumpcutCliTest(unittest.TestCase):
    def test_jumpcut_review_applies_agent_verdict(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = Path(tmp) / "plan.json"
            verdict = Path(tmp) / "verdict.json"
            out = Path(tmp) / "approved.json"
            plan.write_text(json.dumps({
                "segments": [{"index": 0, "start": 0, "end": 2, "action": "remove"}],
            }), encoding="utf-8")
            verdict.write_text(json.dumps({
                "decision": "accept", "patches": [{"index": 0, "action": "keep"}],
            }), encoding="utf-8")
            video_tools.cmd_jumpcut_review(SimpleNamespace(
                plan=str(plan), verdict=str(verdict), out=str(out),
            ))
            saved = json.loads(out.read_text(encoding="utf-8"))
            self.assertTrue(saved["approved"])
            self.assertEqual(saved["segments"][0]["action"], "keep")

    def test_jumpcut_plan_command_writes_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            material_map = Path(tmp) / "a.map.json"
            out = Path(tmp) / "jumpcut_plan.json"
            material_map.write_text(json.dumps({
                "asset_id": "a", "source": "a.mp4",
                "speech": [{"start": 0, "end": 2, "kind": "silence"}],
            }), encoding="utf-8")
            video_tools.cmd_jumpcut_plan(SimpleNamespace(
                material_map=str(material_map), out=str(out), min_silence=1,
            ))
            self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["artifact_role"],
                             "jumpcut_plan")

    def test_jumpcut_apply_writes_lineage(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan_path = Path(tmp) / "plan.json"
            out = Path(tmp) / "processed.mp4"
            lineage = Path(tmp) / "lineage.json"
            plan_path.write_text(json.dumps({
                "approved": True, "source": "a.mp4",
                "segments": [{"start": 0, "end": 2, "action": "keep"}],
            }), encoding="utf-8")
            with patch("video_pipeline_core.jumpcut.subprocess.run"):
                video_tools.cmd_jumpcut_apply(SimpleNamespace(
                    plan=str(plan_path), out=str(out), lineage=str(lineage),
                ))
            self.assertEqual(json.loads(lineage.read_text(encoding="utf-8"))["operation"],
                             "jumpcut_apply")


if __name__ == "__main__":
    unittest.main()
