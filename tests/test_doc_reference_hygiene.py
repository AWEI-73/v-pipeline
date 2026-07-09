import unittest
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


class DocReferenceHygieneTest(unittest.TestCase):
    def test_unreferenced_canonical_root_doc_is_reported(self):
        from video_pipeline_core.doc_reference_hygiene import evaluate_doc_reference_hygiene

        result = evaluate_doc_reference_hygiene(
            repo_root=Path.cwd(),
            root_docs=["docs/new-canonical-route-fact.md"],
            reference_texts=["docs/INDEX.md mentions something else"],
            exemptions=[],
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["orphan_canonical_docs"], ["docs/new-canonical-route-fact.md"])

    def test_current_root_docs_are_classified(self):
        from video_pipeline_core.doc_reference_hygiene import evaluate_current_doc_reference_hygiene

        result = evaluate_current_doc_reference_hygiene(Path.cwd())

        self.assertTrue(result["ok"], result)
        self.assertGreater(result["classified_count"], 0)
        self.assertIn("docs/INDEX.md", result["referenced_docs"])

    def test_cli_runs_directly_from_tools_path(self):
        with TemporaryDirectory() as tmp:
            out = Path(tmp) / "doc_reference_hygiene.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    "tools/doc_reference_hygiene.py",
                    "--repo-root",
                    ".",
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
