import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from tools.material_first_stage2_3_smoke import run_stage2_3_smoke


def _jpg(path, color):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (80, 45), color=color).save(path, "JPEG")


def _write_verdict(path):
    path.write_text(json.dumps({
        "artifact_role": "material_wall_review_verdict",
        "version": 1,
        "reviewer": "test:director",
        "assets": [
            {
                "asset_id": "real_0001",
                "coarse_status": "keep",
                "visual_role": ["opening"],
                "quality": "good",
                "usable_ranges": [{"start": 1.5, "end": 3.5}],
                "visual_evidence": ["opening has usable motion after first second"],
            },
            {
                "asset_id": "real_0002",
                "coarse_status": "keep",
                "visual_role": ["training"],
                "quality": "good",
                "usable_ranges": [{"start": 2.0, "end": 3.8}],
                "visual_evidence": ["training action is centered"],
            },
            {
                "asset_id": "real_0003",
                "coarse_status": "keep",
                "visual_role": ["closing"],
                "quality": "good",
                "visual_evidence": ["closing group moment"],
            },
            {
                "asset_id": "real_0004",
                "coarse_status": "duplicate",
                "visual_role": ["opening"],
                "quality": "duplicate",
                "duplicate_of": "real_0001",
                "why_not_selected": "same opening moment as real_0001",
            },
            {
                "asset_id": "real_0005",
                "coarse_status": "reject",
                "visual_role": [],
                "quality": "bad",
                "why_not_selected": "off-topic still",
            },
        ],
    }), encoding="utf-8")


def _source_folder(root):
    source = root / "source"
    _jpg(source / "opening" / "opening_a.jpg", "red")
    _jpg(source / "training" / "training.jpg", "green")
    _jpg(source / "closing" / "closing.jpg", "blue")
    _jpg(source / "opening" / "opening_dup.jpg", "orange")
    _jpg(source / "unused" / "reject.jpg", "black")
    return source


class MaterialFirstStage23SmokeTest(unittest.TestCase):
    def test_smoke_report_proves_wall_verdict_changes_mapping_and_rough_cut(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = _source_folder(root)
            verdict = root / "material_wall_review_verdict.json"
            _write_verdict(verdict)
            run_dir = root / "run"

            result = run_stage2_3_smoke(run_dir, source_dir=source, wall_verdict=verdict, max_assets=5)

            self.assertTrue(result["ok"], result)
            report_path = run_dir / "stage2_3_smoke_report.json"
            self.assertTrue(report_path.exists())
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["artifact_role"], "stage2_3_smoke_report")
            self.assertEqual(report["stage"], "stage2_3_material_wall_to_review_apply")
            self.assertEqual(report["selected_asset_ids"], ["real_0001", "real_0002", "real_0003"])
            self.assertEqual(report["duplicate_asset_ids"], ["real_0004"])
            self.assertEqual(report["rejected_asset_ids"], ["real_0005"])
            self.assertEqual(report["rough_cut_asset_ids"], ["real_0001", "real_0002", "real_0003"])
            self.assertEqual(report["rough_cut_starts"]["real_0001"], 1.5)
            self.assertEqual(report["rough_cut_starts"]["real_0002"], 2.0)
            self.assertEqual(report["pipeline_home"]["cursor"], "stage5_final_review")

    def test_cli_outputs_json_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = _source_folder(root)
            verdict = root / "material_wall_review_verdict.json"
            _write_verdict(verdict)
            run_dir = root / "run"

            completed = subprocess.run(
                [
                    sys.executable,
                    "tools/material_first_stage2_3_smoke.py",
                    "--out",
                    str(run_dir),
                    "--source-dir",
                    str(source),
                    "--wall-verdict",
                    str(verdict),
                    "--max-assets",
                    "5",
                    "--json",
                ],
                cwd=Path(__file__).resolve().parents[1],
                text=True,
                capture_output=True,
                check=True,
            )

            result = json.loads(completed.stdout)
            self.assertTrue(result["ok"], result)
            self.assertEqual(result["report"]["duplicate_asset_ids"], ["real_0004"])


if __name__ == "__main__":
    unittest.main()
