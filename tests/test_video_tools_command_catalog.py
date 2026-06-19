import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace

import video_tools


class VideoToolsCommandCatalogTest(unittest.TestCase):
    def test_command_manifest_classifies_all_dispatch_commands(self):
        manifest = video_tools.build_video_tools_command_manifest()

        self.assertEqual(manifest["artifact_role"], "video_tools_command_manifest")
        self.assertEqual(manifest["version"], 1)
        self.assertEqual(manifest["unclassified_commands"], [])
        self.assertEqual(
            sorted(manifest["commands"].keys()),
            sorted(video_tools.VIDEO_TOOLS_DISPATCH.keys()),
        )
        self.assertGreater(manifest["command_count"], 60)

        expected_groups = {
            "workspace",
            "contract",
            "material",
            "build",
            "verify",
            "frontend",
            "acceptance",
            "legacy_media",
            "provider_optional",
        }
        self.assertTrue(expected_groups.issubset(set(manifest["groups"])))
        self.assertEqual(manifest["commands"]["project-init"]["group"], "workspace")
        self.assertEqual(manifest["commands"]["contract-run"]["group"], "contract")
        self.assertEqual(manifest["commands"]["material-map-lifecycle"]["group"], "material")
        self.assertEqual(manifest["commands"]["verify-evidence"]["group"], "verify")
        self.assertEqual(manifest["commands"]["dashboard"]["group"], "frontend")
        self.assertEqual(manifest["commands"]["replay-acceptance"]["group"], "acceptance")

    def test_commands_manifest_cli_prints_or_writes_json(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "commands.json"
            video_tools.cmd_commands_manifest(SimpleNamespace(out=str(out)))
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(payload["artifact_role"], "video_tools_command_manifest")
            self.assertIn("contract-run", payload["commands"])

        buf = StringIO()
        with redirect_stdout(buf):
            video_tools.cmd_commands_manifest(SimpleNamespace(out=None))
        payload = json.loads(buf.getvalue())
        self.assertIn("commands-manifest", payload["commands"])

    def test_workflow_manifest_references_registered_commands(self):
        manifest = video_tools.build_video_tools_workflow_manifest()
        commands = set(video_tools.VIDEO_TOOLS_DISPATCH)

        self.assertEqual(manifest["artifact_role"], "video_tools_workflow_manifest")
        self.assertEqual(manifest["version"], 1)
        self.assertIn("canonical_build", manifest["workflows"])
        self.assertIn("workbench_review_rerender", manifest["workflows"])

        for workflow in manifest["workflows"].values():
            self.assertIsInstance(workflow["steps"], list)
            self.assertGreater(len(workflow["steps"]), 0)
            for step in workflow["steps"]:
                self.assertIn(step["command"], commands)
                for dep in step.get("requires", []):
                    self.assertTrue(dep)

        wb_steps = manifest["workflows"]["workbench_review_rerender"]["steps"]
        self.assertEqual([s["command"] for s in wb_steps], [
            "workbench-handoff-validate",
            "workbench-draft-rerender",
        ])
        self.assertEqual(wb_steps[1]["requires"], ["workbench-handoff-validate:ok"])

    def test_brownfield_edit_route_is_explicit_workflow(self):
        manifest = video_tools.build_video_tools_workflow_manifest()
        workflow = manifest["workflows"].get("brownfield_edit_route")
        self.assertIsNotNone(workflow)
        self.assertIn("local patch", workflow["description"])
        steps = workflow["steps"]
        self.assertEqual([s["command"] for s in steps], [
            "workbench-handoff-validate",
            "workbench-draft-rerender",
            "effect-revision-request",
            "effect-revision-draft",
            "remotion-prompt-pack",
            "remotion-worker-outputs",
            "effect-revision-apply",
        ])
        self.assertEqual(
            steps[4]["requires"],
            ["effect-revision-request:adapter_route"],
        )
        self.assertEqual(
            steps[5]["requires"],
            ["remotion-prompt-pack:ok"],
        )
        self.assertIn("second contract-run", steps[-1]["purpose"])
        self.assertIn("story evidence material", workflow["description"])

    def test_workflow_manifest_cli_prints_or_writes_json(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "workflows.json"
            video_tools.cmd_workflow_manifest(SimpleNamespace(out=str(out)))
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(payload["artifact_role"], "video_tools_workflow_manifest")
            self.assertIn("material_map_lifecycle", payload["workflows"])

        buf = StringIO()
        with redirect_stdout(buf):
            video_tools.cmd_workflow_manifest(SimpleNamespace(out=None))
        payload = json.loads(buf.getvalue())
        self.assertIn("workbench_review_rerender", payload["workflows"])


if __name__ == "__main__":
    unittest.main()
