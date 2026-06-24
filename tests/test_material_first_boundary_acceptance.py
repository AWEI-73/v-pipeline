import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from tools.material_first_boundary_acceptance import run_material_first_boundary_acceptance


def _jpg(path, color):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (80, 45), color=color).save(path, "JPEG")


def _source_folder(root):
    source = root / "source"
    _jpg(source / "opening" / "opening.jpg", "red")
    _jpg(source / "training" / "training.jpg", "green")
    _jpg(source / "closing" / "closing.jpg", "blue")
    _jpg(source / "opening" / "duplicate.jpg", "orange")
    _jpg(source / "unused" / "reject.jpg", "black")
    return source


def _write_verdict(path, *, missing_training=False):
    assets = [
        {
            "asset_id": "real_0001",
            "coarse_status": "keep",
            "visual_role": ["opening"],
            "quality": "good",
            "usable_ranges": [{"start": 1.0, "end": 3.0}],
            "visual_evidence": ["opening shot"],
        },
        {
            "asset_id": "real_0002",
            "coarse_status": "reject" if missing_training else "keep",
            "visual_role": [] if missing_training else ["training"],
            "quality": "bad" if missing_training else "good",
            "usable_ranges": [] if missing_training else [{"start": 1.5, "end": 3.5}],
            "visual_evidence": ["training shot"],
            "why_not_selected": "not training" if missing_training else None,
        },
        {
            "asset_id": "real_0003",
            "coarse_status": "keep",
            "visual_role": ["closing"],
            "quality": "good",
            "visual_evidence": ["closing shot"],
        },
        {
            "asset_id": "real_0004",
            "coarse_status": "duplicate",
            "visual_role": ["opening"],
            "quality": "duplicate",
            "duplicate_of": "real_0001",
            "why_not_selected": "same opening moment",
        },
        {
            "asset_id": "real_0005",
            "coarse_status": "reject",
            "visual_role": [],
            "quality": "bad",
            "why_not_selected": "off-topic",
        },
    ]
    path.write_text(json.dumps({
        "artifact_role": "material_wall_review_verdict",
        "version": 1,
        "reviewer": "test:director",
        "assets": assets,
    }), encoding="utf-8")


class MaterialFirstBoundaryAcceptanceTest(unittest.TestCase):
    def test_acceptance_runs_stage2_3_stage4_stage5_and_writes_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = _source_folder(root)
            verdict = root / "material_wall_review_verdict.json"
            _write_verdict(verdict)
            run_dir = root / "run"

            result = run_material_first_boundary_acceptance(
                run_dir,
                source_dir=source,
                wall_verdict=verdict,
                max_assets=5,
            )

            self.assertTrue(result["ok"], result)
            report = json.loads((run_dir / "material_first_boundary_acceptance_report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["artifact_role"], "material_first_boundary_acceptance_report")
            self.assertEqual(report["next_action"], "ready_for_render_or_human_review")
            self.assertEqual(
                [stage["stage"] for stage in report["stages"]],
                ["stage2_3_material_wall_to_review_apply", "stage4_build", "stage5_final_review"],
            )
            self.assertTrue(all(stage["ok"] for stage in report["stages"]))
            self.assertEqual(report["stage_reports"]["stage4_build"], "stage4_build_smoke_report.json")
            self.assertEqual(report["stage_reports"]["stage5_final_review"], "stage5_final_review_smoke_report.json")

    def test_acceptance_stops_when_stage2_3_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = _source_folder(root)
            verdict = root / "material_wall_review_verdict.json"
            _write_verdict(verdict, missing_training=True)
            run_dir = root / "run"

            result = run_material_first_boundary_acceptance(
                run_dir,
                source_dir=source,
                wall_verdict=verdict,
                max_assets=5,
            )

            self.assertFalse(result["ok"], result)
            report = result["report"]
            self.assertEqual(report["failed_stage"], "stage2_3_material_wall_to_review_apply")
            self.assertEqual(report["next_action"], "repair:stage2_3_material_wall_to_review_apply")
            self.assertEqual(len(report["stages"]), 1)
            self.assertFalse((run_dir / "stage4_build_smoke_report.json").exists())

    def test_acceptance_preserves_in_run_wall_verdict_when_out_is_recreated(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = _source_folder(root)
            run_dir = root / "run"
            run_dir.mkdir()
            verdict = run_dir / "material_wall_review_verdict.json"
            _write_verdict(verdict)

            result = run_material_first_boundary_acceptance(
                run_dir,
                source_dir=source,
                wall_verdict=verdict,
                max_assets=5,
            )

            self.assertTrue(result["ok"], result)
            self.assertTrue(verdict.exists())
            restored = json.loads(verdict.read_text(encoding="utf-8"))
            self.assertEqual(restored["artifact_role"], "material_wall_review_verdict")
            self.assertTrue((run_dir / "material_first_boundary_acceptance_report.json").exists())

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
                    "tools/material_first_boundary_acceptance.py",
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
            self.assertEqual(result["report"]["next_action"], "ready_for_render_or_human_review")

    def test_cli_accepts_wall_verdict_inside_out_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = _source_folder(root)
            run_dir = root / "run"
            run_dir.mkdir()
            verdict = run_dir / "material_wall_review_verdict.json"
            _write_verdict(verdict)

            completed = subprocess.run(
                [
                    sys.executable,
                    "tools/material_first_boundary_acceptance.py",
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
            self.assertTrue(verdict.exists())
            self.assertTrue((run_dir / "material_first_boundary_acceptance_report.json").exists())


if __name__ == "__main__":
    unittest.main()
