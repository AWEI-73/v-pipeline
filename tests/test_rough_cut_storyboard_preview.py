import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class RoughCutStoryboardPreviewTest(unittest.TestCase):
    def test_cli_builds_preview_from_matrix_keyframes_without_video_sources(self):
        from PIL import Image

        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            frames = root / "frames"
            frames.mkdir()
            frame_a = frames / "a.jpg"
            frame_b = frames / "b.jpg"
            Image.new("RGB", (160, 90), (220, 40, 40)).save(frame_a)
            Image.new("RGB", (160, 90), (40, 80, 220)).save(frame_b)

            matrix = {
                "artifact_role": "material_understanding_matrix",
                "assets": [
                    {
                        "asset_id": "real_0001",
                        "visual_evidence": {
                            "keyframes": [{"image_path": str(frame_a)}],
                        },
                    },
                    {
                        "asset_id": "real_0002",
                        "visual_evidence": {
                            "keyframes": [{"image_path": str(frame_b)}],
                        },
                    },
                ],
            }
            plan = {
                "artifact_role": "material_first_preview_rough_cut_plan",
                "clips": [
                    {"asset_id": "real_0001", "duration_sec": 6.0, "segment": 1, "role": "opening"},
                    {"asset_id": "real_0002", "duration_sec": 6.0, "segment": 2, "role": "training"},
                ],
            }
            matrix_path = root / "matrix.json"
            plan_path = root / "rough_cut_plan.json"
            matrix_path.write_text(json.dumps(matrix), encoding="utf-8")
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            out = root / "storyboard_preview.mp4"
            report = root / "storyboard_preview_report.json"

            proc = subprocess.run(
                [
                    sys.executable,
                    "tools/rough_cut_storyboard_preview.py",
                    "--matrix",
                    str(matrix_path),
                    "--rough-cut-plan",
                    str(plan_path),
                    "--out",
                    str(out),
                    "--report",
                    str(report),
                    "--seconds-per-clip",
                    "0.5",
                    "--width",
                    "320",
                    "--height",
                    "180",
                    "--json",
                ],
                cwd=repo,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(payload["artifact_role"], "rough_cut_storyboard_preview_report")
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["clip_count"], 2)
            self.assertEqual(payload["source_mode"], "matrix_keyframes")
            self.assertTrue(out.is_file())


if __name__ == "__main__":
    unittest.main()
