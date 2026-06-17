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


if __name__ == "__main__":
    unittest.main()
