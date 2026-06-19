import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _job(target_file="rendered.mov", preview_file="preview.mp4"):
    return {
        "job_id": "rm_fx4e_opening_glow",
        "source_effect_id": "fx_opening_glow",
        "component_family": "light_leak_overlay",
        "prompt": "warm opening glow",
        "props": {
            "intent": "add a warm cinematic glow to the opening",
            "visual_language": ["warm glow", "soft sweep"],
            "intensity": "medium",
            "duration_sec": 1.2,
        },
        "timing": {"start_sec": 0.0, "duration_sec": 1.2},
        "output": {
            "type": "overlay_video",
            "alpha": True,
            "target_file": target_file,
            "preview_file": preview_file,
        },
    }


class RemotionWorkerBridgeTest(unittest.TestCase):
    def test_write_entry_only_creates_remotion_entry_and_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            job_path = root / "job.json"
            preview = root / "preview.mp4"
            rendered = root / "rendered.mov"
            project = root / "remotion_project"
            job_path.write_text(json.dumps(_job(str(rendered), str(preview))), encoding="utf-8")

            proc = subprocess.run([
                "node",
                "tools/remotion_worker_bridge.mjs",
                "--job-json", str(job_path),
                "--preview-file", str(preview),
                "--rendered-asset", str(rendered),
                "--project-root", str(project),
                "--write-entry-only",
            ], cwd=ROOT, capture_output=True, text=True)

            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["status"], "entry_written")
            entry = Path(payload["entry"])
            self.assertTrue(entry.is_file())
            text = entry.read_text(encoding="utf-8")
            self.assertIn("HermesEffectOverlay", text)
            self.assertIn("registerRoot", text)
            self.assertIn("warm opening glow", text)
            self.assertEqual(payload["rendered_asset"], str(rendered))
            self.assertEqual(payload["preview_file"], str(preview))
            self.assertIn("--codec=prores", " ".join(payload["render_command"]))

    def test_bridge_refuses_canonical_outputs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            job_path = root / "job.json"
            preview = root / "preview.mp4"
            job_path.write_text(json.dumps(_job("final.mp4", str(preview))), encoding="utf-8")

            proc = subprocess.run([
                "node",
                "tools/remotion_worker_bridge.mjs",
                "--job-json", str(job_path),
                "--preview-file", str(preview),
                "--rendered-asset", str(root / "final.mp4"),
                "--project-root", str(root / "project"),
                "--write-entry-only",
            ], cwd=ROOT, capture_output=True, text=True)

            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("protected canonical", proc.stderr)

    def test_bridge_requires_positive_duration(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bad = _job()
            bad["timing"]["duration_sec"] = 0
            job_path = root / "job.json"
            job_path.write_text(json.dumps(bad), encoding="utf-8")

            proc = subprocess.run([
                "node",
                "tools/remotion_worker_bridge.mjs",
                "--job-json", str(job_path),
                "--preview-file", str(root / "preview.mp4"),
                "--rendered-asset", str(root / "rendered.mov"),
                "--project-root", str(root / "project"),
                "--write-entry-only",
            ], cwd=ROOT, capture_output=True, text=True)

            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("duration_sec", proc.stderr)

    def test_bridge_accepts_utf8_sig_job_json(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            job_path = root / "job.json"
            preview = root / "preview.mp4"
            rendered = root / "rendered.mov"
            job_path.write_text("\ufeff" + json.dumps(_job(str(rendered), str(preview))), encoding="utf-8")

            proc = subprocess.run([
                "node",
                "tools/remotion_worker_bridge.mjs",
                "--job-json", str(job_path),
                "--preview-file", str(preview),
                "--rendered-asset", str(rendered),
                "--project-root", str(root / "project"),
                "--write-entry-only",
            ], cwd=ROOT, capture_output=True, text=True)

            self.assertEqual(proc.returncode, 0, proc.stderr)


if __name__ == "__main__":
    unittest.main()
