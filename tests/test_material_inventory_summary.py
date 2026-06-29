import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core.material_inventory_summary import build_material_inventory_summary


def _write(path, payload=b"x"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return path


class MaterialInventorySummaryTest(unittest.TestCase):
    def test_builds_quick_inventory_summary_from_scan_decision(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            _write(source / "opening" / "a.jpg")
            _write(source / "training" / "b.mp4")
            _write(source / "training" / "c.mov")
            _write(source / "audio" / "song.mp3")
            decision = {
                "artifact_role": "stage0_material_scan_decision",
                "needed": True,
                "default_scope": "all_materials",
                "scan_depth": "quick_inventory_first",
            }

            summary = build_material_inventory_summary(source, material_scan_decision=decision)

            self.assertEqual(summary["artifact_role"], "material_inventory_summary")
            self.assertEqual(summary["scan_depth"], "quick_inventory_first")
            self.assertEqual(summary["scope"]["mode"], "all_materials")
            self.assertEqual(summary["counts"]["total_files"], 4)
            self.assertEqual(summary["counts"]["images"], 1)
            self.assertEqual(summary["counts"]["videos"], 2)
            self.assertEqual(summary["counts"]["audio"], 1)
            folders = {item["folder"]: item for item in summary["folder_summary"]}
            self.assertEqual(folders["training"]["video_count"], 2)
            self.assertIn("review_material_inventory_summary", summary["recommended_next_actions"])
            self.assertTrue(summary["suggested_followup_questions"])

    def test_user_specified_scope_limits_inventory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            _write(source / "selected" / "a.jpg")
            _write(source / "ignored" / "b.mp4")
            decision = {
                "artifact_role": "stage0_material_scan_decision",
                "needed": True,
                "default_scope": "user_specified",
                "user_scope": "selected",
                "scan_depth": "quick_inventory_first",
            }

            summary = build_material_inventory_summary(source, material_scan_decision=decision)

            self.assertEqual(summary["scope"]["mode"], "user_specified")
            self.assertEqual(summary["scope"]["resolved_roots"], [str((source / "selected").resolve())])
            self.assertEqual(summary["counts"]["total_files"], 1)
            self.assertEqual(summary["counts"]["images"], 1)

    def test_cli_writes_summary_json(self):
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            _write(source / "a.jpg")
            intent = root / "video_intent.json"
            intent.write_text(json.dumps({
                "artifact_role": "video_intent",
                "material_scan_decision": {
                    "needed": True,
                    "default_scope": "all_materials",
                    "scan_depth": "quick_inventory_first",
                },
            }), encoding="utf-8")
            out = root / "material_inventory_summary.json"

            proc = subprocess.run(
                [
                    sys.executable,
                    "tools/material_quick_inventory.py",
                    "--source-dir",
                    str(source),
                    "--video-intent",
                    str(intent),
                    "--out",
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
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(payload["artifact_role"], "material_inventory_summary")
            self.assertEqual(payload["counts"]["total_files"], 1)


if __name__ == "__main__":
    unittest.main()
