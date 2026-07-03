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
        self.assertEqual(manifest["commands"]["video-intent-plan"]["group"], "workspace")
        self.assertEqual(manifest["commands"]["contract-run"]["group"], "contract")
        self.assertEqual(manifest["commands"]["material-map-lifecycle"]["group"], "material")
        self.assertEqual(manifest["commands"]["source-section-map"]["group"], "material")
        self.assertEqual(manifest["commands"]["source-motion-profile"]["group"], "material")
        self.assertEqual(manifest["commands"]["source-dialogue-script"]["group"], "material")
        self.assertEqual(manifest["commands"]["ingest-assets"]["group"], "material")
        self.assertEqual(manifest["commands"]["gc-assets"]["group"], "material")
        self.assertEqual(manifest["commands"]["asset-path-audit"]["group"], "verify")
        self.assertEqual(manifest["commands"]["verify-evidence"]["group"], "verify")
        self.assertEqual(manifest["commands"]["dashboard"]["group"], "frontend")
        self.assertEqual(manifest["commands"]["replay-acceptance"]["group"], "acceptance")
        self.assertEqual(manifest["commands"]["video-intent-acceptance"]["group"], "acceptance")

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
        self.assertIn("video_intent_planner", manifest["workflows"])
        self.assertIn("video_intent_acceptance", manifest["workflows"])
        self.assertIn("workbench_review_rerender", manifest["workflows"])
        self.assertIn("source_understanding", manifest["workflows"])

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

        vip_steps = manifest["workflows"]["video_intent_planner"]["steps"]
        self.assertEqual([s["command"] for s in vip_steps], ["video-intent-plan"])
        self.assertIn("video_intent.json", manifest["workflows"]["video_intent_planner"]["description"])

        via_steps = manifest["workflows"]["video_intent_acceptance"]["steps"]
        self.assertEqual([s["command"] for s in via_steps], ["video-intent-acceptance"])
        self.assertEqual(via_steps[0]["requires"], ["video-intent-plan:implemented"])

        source_steps = manifest["workflows"]["source_understanding"]["steps"]
        self.assertEqual([s["command"] for s in source_steps], [
            "source-section-map",
            "source-motion-profile",
            "source-material-matrix",
            "source-dialogue-script",
            "source-highlight-plan",
        ])
        self.assertEqual(source_steps[1]["requires"], ["source-section-map:ok"])
        self.assertIn("one long source", manifest["workflows"]["source_understanding"]["description"])

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
            "effect-collage-refs",
            "remotion-prompt-pack",
            "remotion-worker-outputs",
            "effect-render-verification",
            "effect-design-review",
            "remotion-composite-draft",
            "effect-revision-apply",
        ])
        self.assertEqual(
            steps[5]["requires"],
            ["effect-revision-request:adapter_route"],
        )
        self.assertEqual(
            steps[6]["requires"],
            ["remotion-prompt-pack:ok"],
        )
        by_command = {step["command"]: step for step in steps}
        self.assertEqual(
            by_command["effect-render-verification"]["requires"],
            ["remotion-worker-outputs:accepted_review"],
        )
        self.assertEqual(
            by_command["effect-design-review"]["requires"],
            ["effect-design-concept:selected", "remotion-worker-outputs:rendered_or_preview_probe"],
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
