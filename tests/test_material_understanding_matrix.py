import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


def _jpg(path: Path, color: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (96, 54), color=color).save(path, "JPEG")


class MaterialUnderstandingMatrixTest(unittest.TestCase):
    def test_builds_matrix_without_claiming_material_truth(self):
        from video_pipeline_core.material_understanding_matrix import build_material_understanding_matrix

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            video = root / "training" / "pole_training.mp4"
            photo = root / "closing" / "group_photo.jpg"
            export = root / "export" / "final_master.mp4"
            video.parent.mkdir(parents=True)
            export.parent.mkdir(parents=True)
            video.write_bytes(b"fake video")
            export.write_bytes(b"fake export")
            _jpg(photo, "blue")
            db = {
                "artifact_role": "materials_db",
                "files": [
                    {
                        "id": "a001",
                        "path": str(video),
                        "type": "video",
                        "metadata": {"duration_sec": 30},
                        "tags_from_path": ["training"],
                        "vlm_caption": "folder/file hint: training / pole_training",
                    },
                    {
                        "id": "a002",
                        "path": str(photo),
                        "type": "photo",
                        "tags_from_path": ["closing"],
                        "vlm_caption": "folder/file hint: closing / group_photo",
                    },
                    {
                        "id": "a003",
                        "path": str(export),
                        "type": "video",
                        "metadata": {"duration_sec": 180},
                        "tags_from_path": ["export"],
                        "vlm_caption": "folder/file hint: export / final_master",
                    },
                ],
            }

            def fake_frame_extractor(source, timestamp_sec, out_path):
                _jpg(Path(out_path), "red")
                return str(out_path)

            matrix = build_material_understanding_matrix(
                db,
                out_dir=root / "out",
                max_assets=10,
                frame_budget=2,
                frame_extractor=fake_frame_extractor,
            )

            self.assertEqual(matrix["artifact_role"], "material_understanding_matrix")
            self.assertEqual(matrix["asset_count"], 3)
            by_id = {asset["asset_id"]: asset for asset in matrix["assets"]}
            self.assertEqual(len(by_id["a001"]["visual_evidence"]["keyframes"]), 2)
            self.assertEqual(by_id["a002"]["visual_evidence"]["photo"], str(photo))
            self.assertIn("looks_like_finished_export", by_id["a003"]["risk_flags"])
            self.assertIn("training", by_id["a001"]["role_hints"])
            self.assertIn("closing", by_id["a002"]["role_hints"])
            for asset in matrix["assets"]:
                self.assertNotIn("selected_for_material_map", asset)
                self.assertNotIn("need_id", asset)
                self.assertEqual(asset["next_review_action"], "review_material_wall_decision")
            self.assertTrue((root / "out" / "material_understanding_matrix.json").exists())

    def test_cli_writes_matrix(self):
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            photo = root / "opening" / "photo.jpg"
            _jpg(photo, "green")
            db = root / "materials_db.json"
            db.write_text(json.dumps({
                "artifact_role": "materials_db",
                "files": [{
                    "id": "p001",
                    "path": str(photo),
                    "type": "photo",
                    "tags_from_path": ["opening"],
                }],
            }), encoding="utf-8")
            out = root / "out"

            proc = subprocess.run(
                [
                    sys.executable,
                    "tools/material_understanding_matrix.py",
                    "--materials-db",
                    str(db),
                    "--out-dir",
                    str(out),
                    "--json",
                ],
                cwd=repo,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertTrue(payload["ok"])
            self.assertTrue((out / "material_understanding_matrix.json").exists())


if __name__ == "__main__":
    unittest.main()
