import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VIDEO_TOOLS = ROOT / "video_tools.py"
REGISTRY = ROOT / "docs" / "branch-contract-registry.json"
DECISION_TREE = ROOT / "docs" / "pipeline-decision-tree.md"


class RegistryAuditCliTest(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(VIDEO_TOOLS), "registry-audit", *args],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def test_real_registry_passes(self):
        proc = self.run_cli("--json")
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        report = json.loads(proc.stdout)
        self.assertTrue(report["ok"])
        self.assertEqual(report["finding_count"], 0)

    def test_fake_branch_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_registry = Path(tmpdir) / "branch-contract-registry.json"
            data = json.loads(REGISTRY.read_text(encoding="utf-8-sig"))
            data["branches"].append({
                "branch_id": "fake-unmapped-branch",
                "name": "Fake Unmapped Branch",
                "stages": [
                    {
                        "stage": "fake-stage",
                        "skill": "skills/video-pipeline.md",
                        "artifacts_in": [],
                        "artifacts_out": [],
                        "gate": "fake impossible gate",
                        "next_actions_on_pass": [],
                        "next_actions_on_fail": [],
                    }
                ],
            })
            tmp_registry.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

            proc = self.run_cli(
                "--registry", str(tmp_registry),
                "--decision-tree", str(DECISION_TREE),
                "--json",
            )
            self.assertEqual(proc.returncode, 1)
            report = json.loads(proc.stdout)
            self.assertFalse(report["ok"])
            self.assertIn("missing_branch_label: fake-unmapped-branch", report["findings"])


if __name__ == "__main__":
    unittest.main()
