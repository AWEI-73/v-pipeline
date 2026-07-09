import unittest
import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


class FactoryImprovementLoopTest(unittest.TestCase):
    def test_rendered_qa_finding_becomes_structured_improvement(self):
        from video_pipeline_core.factory_improvement_loop import build_factory_improvement_backlog

        backlog = build_factory_improvement_backlog(
            findings=[
                {
                    "source": "rendered_product_qa",
                    "rule": "title_effect_evidence_missing",
                    "message": "title/effect lifecycle QA exists but lacks rendered frame evidence",
                    "artifact": "title_effect_lifecycle_qa.json",
                }
            ]
        )

        self.assertEqual(backlog["artifact_role"], "factory_improvement_backlog")
        self.assertEqual(len(backlog["items"]), 1)
        item = backlog["items"][0]
        self.assertEqual(item["owner_branch"], "effect-factory")
        self.assertEqual(item["product_level_impact"], "rendered candidate cannot clear QA/no-skip")
        self.assertEqual(item["proposed_acceptance_hook"], "tools/rendered_product_qa.py")
        self.assertIs(item["golden_path_worthy"], True)

    def test_cli_runs_directly_from_tools_path(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            findings = root / "findings.json"
            out = root / "factory_improvement_backlog.json"
            findings.write_text(
                json.dumps(
                    {
                        "source_tool": "rendered_product_qa",
                        "blocking": [{"rule": "title_effect_evidence_missing"}],
                    }
                ),
                encoding="utf-8",
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    "tools/factory_improvement_loop.py",
                    "--findings",
                    str(findings),
                    "--out",
                    str(out),
                    "--json",
                ],
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue(out.exists())


if __name__ == "__main__":
    unittest.main()
