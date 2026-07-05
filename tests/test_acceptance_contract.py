import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace

import video_tools
from video_pipeline_core import acceptance_contract


class AcceptanceContractTest(unittest.TestCase):
    def test_contract_declares_required_acceptance_commands(self):
        payload = acceptance_contract.build_acceptance_contract(
            video_tools.VIDEO_TOOLS_DISPATCH.keys()
        )

        self.assertEqual(payload["artifact_role"], "acceptance_command_contract")
        self.assertEqual(payload["version"], 1)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["missing_dispatch_commands"], [])
        self.assertEqual(payload["invalid_command_refs"], [])

        commands = {entry["id"]: entry for entry in payload["commands"]}
        for command_id in [
            "full-unittest",
            "e2e-smoke-stock-story",
            "e2e-smoke-single-long-highlight",
            "registry-audit",
            "interface-audit",
            "asset-path-audit-strict",
            "test-tier-dev",
            "test-tier-work-order-acceptance",
            "test-tier-full",
        ]:
            self.assertIn(command_id, commands)
            self.assertIsInstance(commands[command_id]["argv"], list)
            self.assertTrue(commands[command_id]["purpose"])
            self.assertIn("owner_category", commands[command_id])
            self.assertIn("needs_run_dir", commands[command_id])
            self.assertEqual(
                commands[command_id]["expected_exit_behavior"],
                "0=pass; nonzero=fail",
            )

        self.assertTrue(commands["asset-path-audit-strict"]["needs_run_dir"])
        self.assertFalse(commands["interface-audit"]["needs_run_dir"])

    def test_contract_fails_closed_for_unknown_video_tools_refs(self):
        payload = acceptance_contract.build_acceptance_contract(
            video_tools.VIDEO_TOOLS_DISPATCH.keys(),
            extra_commands=[
                {
                    "id": "bad-ref",
                    "argv": ["python", "video_tools.py", "missing-command"],
                    "purpose": "prove missing command refs fail closed",
                    "intended_use": "test fixture",
                    "needs_run_dir": False,
                    "fixture_argument": None,
                    "expected_exit_behavior": "0=pass; nonzero=fail",
                    "owner_category": "audit",
                }
            ],
        )

        self.assertFalse(payload["ok"])
        self.assertEqual(payload["missing_dispatch_commands"], ["missing-command"])
        self.assertEqual(payload["invalid_command_refs"][0]["id"], "bad-ref")

    def test_contract_fails_closed_for_unknown_test_tier_refs(self):
        payload = acceptance_contract.build_acceptance_contract(
            video_tools.VIDEO_TOOLS_DISPATCH.keys(),
            extra_commands=[
                {
                    "id": "bad-tier",
                    "argv": ["python", "video_tools.py", "test-tiers", "--tier", "missing-tier"],
                    "purpose": "prove missing test tier refs fail closed",
                    "intended_use": "test fixture",
                    "needs_run_dir": False,
                    "fixture_argument": None,
                    "expected_exit_behavior": "0=pass; nonzero=fail",
                    "owner_category": "tier",
                }
            ],
        )

        self.assertFalse(payload["ok"])
        self.assertEqual(payload["missing_test_tiers"], ["missing-tier"])
        self.assertEqual(payload["invalid_command_refs"][0]["id"], "bad-tier")

    def test_acceptance_contract_cli_prints_or_writes_json(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "acceptance_contract.json"
            video_tools.cmd_acceptance_contract(SimpleNamespace(out=str(out)))
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(payload["artifact_role"], "acceptance_command_contract")
            self.assertTrue(payload["ok"])
            self.assertIn("commands", payload)

        buf = StringIO()
        with redirect_stdout(buf):
            video_tools.cmd_acceptance_contract(SimpleNamespace(out=None))
        payload = json.loads(buf.getvalue())
        ids = {entry["id"] for entry in payload["commands"]}
        self.assertIn("test-tier-work-order-acceptance", ids)


if __name__ == "__main__":
    unittest.main()
