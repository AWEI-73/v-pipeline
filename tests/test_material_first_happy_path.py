import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class MaterialFirstHappyPathTest(unittest.TestCase):
    def _source_dir(self, root: Path) -> Path:
        source = root / "source"
        (source / "66期學長空拍影片").mkdir(parents=True)
        (source / "工安早會").mkdir(parents=True)
        (source / "換桿").mkdir(parents=True)
        (source / "運動會").mkdir(parents=True)
        (source / "66期學長空拍影片" / "MAX_0169.MP4").write_bytes(b"fake")
        (source / "工安早會" / "IMG_8515.MOV").write_bytes(b"fake")
        (source / "換桿" / "IMG_8346.MOV").write_bytes(b"fake")
        (source / "運動會" / "66期配四班隊呼.mp4").write_bytes(b"fake")
        return source

    def test_wrapper_creates_matrix_draft_and_acceptance_report_without_render(self):
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self._source_dir(root)
            run_dir = root / "run"

            proc = subprocess.run(
                [
                    sys.executable,
                    "tools/material_first_happy_path.py",
                    "--out",
                    str(run_dir),
                    "--source-dir",
                    str(source),
                    "--max-assets",
                    "12",
                    "--frame-budget",
                    "1",
                    "--json",
                ],
                cwd=repo,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            result = json.loads(proc.stdout)
            self.assertTrue(result["ok"])
            self.assertEqual(result["next_action"], "ready_for_render_or_human_review")
            self.assertTrue((run_dir / "materials_db.source_candidates.json").is_file())
            self.assertTrue((run_dir / "material_understanding" / "material_understanding_matrix.json").is_file())
            self.assertTrue((run_dir / "material_wall_review_verdict.draft.json").is_file())
            self.assertTrue((run_dir / "preview_rough_cut_plan.json").is_file())
            self.assertTrue((run_dir / "material_first_boundary_acceptance_report.json").is_file())
            self.assertFalse((run_dir / "final.mp4").exists())

            verdict = json.loads((run_dir / "material_wall_review_verdict.draft.json").read_text(encoding="utf-8-sig"))
            self.assertEqual(verdict["primary_selection"]["training"], "real_0002")
            preview = json.loads((run_dir / "preview_rough_cut_plan.json").read_text(encoding="utf-8-sig"))
            self.assertEqual(preview["decision_scope"], "preview_proposal_not_canonical_timeline")
            self.assertGreaterEqual(preview["total_duration_sec"], 60)


if __name__ == "__main__":
    unittest.main()
