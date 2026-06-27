import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace

import video_tools
from tools.test_tiers import _default_runner, build_test_tier_manifest, run_test_tier


class TestTierRunnerTest(unittest.TestCase):
    def test_manifest_declares_expected_tiers_with_commands(self):
        manifest = build_test_tier_manifest()

        self.assertEqual(manifest["artifact_role"], "test_tier_manifest")
        self.assertEqual(manifest["version"], 1)
        for tier in ["backend-smoke", "workbench", "material-map", "render-e2e", "full"]:
            self.assertIn(tier, manifest["tiers"])
            self.assertGreater(len(manifest["tiers"][tier]["commands"]), 0)
            self.assertIn("optional_checks", manifest["tiers"][tier])
            for command in manifest["tiers"][tier]["commands"]:
                self.assertIsInstance(command, list)
                self.assertGreater(len(command), 0)

        workbench_optional = manifest["tiers"]["workbench"]["optional_checks"]
        workbench_commands = [" ".join(command) for command in manifest["tiers"]["workbench"]["commands"]]
        self.assertTrue(any("dashboard_spa_render_smoke.mjs" in command for command in workbench_commands))
        self.assertTrue(any("dashboard_i18n_smoke.mjs" in command for command in workbench_commands))
        self.assertIn("SPA-shell boundary", manifest["tiers"]["workbench"]["description"])
        self.assertEqual(workbench_optional[0]["name"], "workbench-browser-layout")
        self.assertIn("workbench_browser_layout_smoke.mjs", " ".join(workbench_optional[0]["command"]))
        self.assertIn("workbench_browser_layout_smoke.mjs", " ".join(workbench_optional[0]["merged_spa_command"]))
        self.assertIn("http://localhost:8765/workbench", workbench_optional[0]["merged_spa_command"])
        self.assertIn("SPA iframe shell", workbench_optional[0]["description"])
        self.assertEqual(workbench_optional[1]["name"], "workbench-frontend-fixture")
        self.assertIn("--init-fixture", workbench_optional[1]["command"])
        self.assertIn("--exercise-replace", workbench_optional[1]["replace_command"])
        self.assertIn("--force-init-fixture", workbench_optional[1]["description"])

    def test_dry_run_returns_commands_without_executing(self):
        calls = []

        result = run_test_tier("workbench", dry_run=True, runner=lambda cmd: calls.append(cmd))

        self.assertTrue(result["ok"])
        self.assertTrue(result["dry_run"])
        self.assertEqual(result["command_count"], len(result["commands"]))
        self.assertGreater(len(result["optional_checks"]), 0)
        self.assertEqual(result["optional_checks"][0]["name"], "workbench-browser-layout")
        self.assertIn("merged_spa_command", result["optional_checks"][0])
        self.assertEqual(result["optional_checks"][1]["name"], "workbench-frontend-fixture")
        self.assertIn("replace_command", result["optional_checks"][1])
        self.assertEqual(calls, [])

    def test_run_executes_commands_and_stops_on_failure(self):
        calls = []

        def fake_runner(cmd):
            calls.append(cmd)
            return 7 if len(calls) == 2 else 0

        result = run_test_tier("backend-smoke", dry_run=False, runner=fake_runner)

        self.assertFalse(result["ok"])
        self.assertEqual(result["failed_command_index"], 1)
        self.assertEqual(result["exit_code"], 7)
        self.assertEqual(len(calls), 2)

    def test_default_runner_uses_repo_local_temp_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            probe = Path(tmp) / "probe_env.py"
            out = Path(tmp) / "env.json"
            probe.write_text(
                "import json, os, sys\n"
                "payload = {'TMP': os.environ.get('TMP'), 'TEMP': os.environ.get('TEMP')}\n"
                "open(sys.argv[1], 'w', encoding='utf-8').write(json.dumps(payload))\n",
                encoding="utf-8",
            )

            code = _default_runner(["python", str(probe), str(out)])
            payload = json.loads(out.read_text(encoding="utf-8"))

        expected = str(Path.cwd() / ".tmp" / "test-temp")
        self.assertEqual(code, 0)
        self.assertEqual(payload["TMP"], expected)
        self.assertEqual(payload["TEMP"], expected)
        self.assertTrue(Path(expected).is_dir())

    def test_unknown_tier_fails_closed(self):
        with self.assertRaises(ValueError):
            run_test_tier("unknown", dry_run=True)

    def test_video_tools_test_tiers_cli_writes_manifest_or_dry_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "tiers.json"
            with redirect_stdout(StringIO()):
                video_tools.cmd_test_tiers(SimpleNamespace(tier=None, dry_run=True, out=str(out)))
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(payload["artifact_role"], "test_tier_manifest")

        buf = StringIO()
        with redirect_stdout(buf):
            video_tools.cmd_test_tiers(SimpleNamespace(tier="backend-smoke", dry_run=True, out=None))
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["tier"], "backend-smoke")
        self.assertTrue(payload["dry_run"])


if __name__ == "__main__":
    unittest.main()
