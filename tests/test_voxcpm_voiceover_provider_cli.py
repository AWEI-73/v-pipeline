import json
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL = REPO_ROOT / "tools" / "voxcpm_voiceover_provider.py"


class VoxcpmVoiceoverProviderCliTests(unittest.TestCase):
    def _script(self, root: Path) -> Path:
        path = root / "script.json"
        path.write_text(
            json.dumps([{"segment": 1, "title": "opening", "text": "Narration test."}]),
            encoding="utf-8",
        )
        return path

    def _fake_repo(self, root: Path) -> Path:
        repo = root / "VoxCPM-main"
        cli = repo / "src" / "voxcpm" / "cli.py"
        cli.parent.mkdir(parents=True)
        cli.write_text("print('fake voxcpm cli')\n", encoding="utf-8")
        return repo

    def test_plan_only_uses_local_repo_and_writes_artifacts(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out = root / "out"
            result = subprocess.run(
                [
                    sys.executable,
                    str(TOOL),
                    str(self._script(root)),
                    "--out-dir",
                    str(out),
                    "--voxcpm-repo",
                    str(self._fake_repo(root)),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["selected_provider"], "voxcpm")
            self.assertEqual(payload["provider_entry_type"], "local_repo")
            self.assertFalse(payload["voiceover_ready"])
            self.assertTrue((out / "voiceover_provider_plan.json").exists())
            self.assertTrue((out / "subtitle_voiceover_build_handoff.json").exists())
            self.assertTrue((out / "narration_manifest.json").exists())

    def test_missing_repo_fails_closed_without_fallback(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            result = subprocess.run(
                [
                    sys.executable,
                    str(TOOL),
                    str(self._script(root)),
                    "--out-dir",
                    str(root / "out"),
                    "--voxcpm-repo",
                    str(root / "missing-repo"),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            self.assertEqual(result.returncode, 1, result.stderr + result.stdout)
            payload = json.loads(result.stdout)
            self.assertFalse(payload["ok"])
            self.assertEqual(payload["selected_provider"], "voxcpm")
            self.assertFalse(payload["provider_available"])


if __name__ == "__main__":
    unittest.main()
