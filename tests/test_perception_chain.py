import json
import subprocess
import tempfile
import unittest
from pathlib import Path


def _ffmpeg_available():
    try:
        from video_pipeline_core.platform_tools import resolve_ffmpeg
        resolve_ffmpeg()
        return True
    except Exception:
        return False


@unittest.skipUnless(_ffmpeg_available(), "ffmpeg not available")
class PerceptionChainSmokeTest(unittest.TestCase):
    def setUp(self):
        from video_pipeline_core.platform_tools import resolve_ffmpeg

        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.video = self.root / "fixture.mp4"
        subprocess.run(
            [
                resolve_ffmpeg(),
                "-y",
                "-f",
                "lavfi",
                "-i",
                "testsrc=duration=4:size=320x240:rate=12",
                "-pix_fmt",
                "yuv420p",
                str(self.video),
            ],
            capture_output=True,
            check=True,
        )
        self.shots = [
            {"shot_id": "shot_001", "start_sec": 0.0, "end_sec": 2.0},
            {"shot_id": "shot_002", "start_sec": 2.0, "end_sec": 4.0},
        ]
        self.shots_path = self.root / "shots.json"
        self.shots_path.write_text(json.dumps(self.shots), encoding="utf-8")
        self.anchors = {
            "beat_times": [0.75, 2.75],
            "energy_peaks": [1.5],
            "speech_starts": [2.2],
        }

    def tearDown(self):
        self.tmp.cleanup()

    def test_planner_writes_contract_with_baseline_and_audio_reasons(self):
        from video_pipeline_core.sampling_planner import write_sampling_plan

        out = self.root / "sampling_plan.json"
        plan = write_sampling_plan(self.video, self.shots, out, audio_anchors=self.anchors)

        self.assertTrue(out.exists())
        saved = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(saved, plan)
        self.assertEqual(plan["artifact_role"], "sampling_plan")
        self.assertEqual(plan["source_video"], str(self.video))
        self.assertTrue(plan["samples"])
        reasons = {sample["reason"] for sample in plan["samples"]}
        self.assertIn("baseline", reasons)
        self.assertIn("audio_beat", reasons)
        self.assertIn("energy_event", reasons)
        self.assertIn("speech_start", reasons)
        self.assertEqual({sample["shot_id"] for sample in plan["samples"]}, {"shot_001", "shot_002"})
        for sample in plan["samples"]:
            self.assertIn("timestamp_sec", sample)
            self.assertGreaterEqual(sample["timestamp_sec"], 0.0)
            self.assertLessEqual(sample["timestamp_sec"], 4.0)

    def test_sampling_coverage_report_fails_closed_and_cli_writes_json(self):
        import video_tools
        from video_pipeline_core.sampling_planner import write_sampling_plan
        from video_pipeline_core.sampling_coverage import verify_sampling_coverage

        plan_path = self.root / "sampling_plan.json"
        plan = write_sampling_plan(self.video, self.shots, plan_path, audio_anchors=self.anchors)
        report = verify_sampling_coverage(plan, self.shots, self.anchors, max_gap_sec=1.25)
        self.assertEqual(report["artifact_role"], "sampling_coverage_report")
        self.assertTrue(report["pass"])
        self.assertFalse(report["gaps"])
        self.assertTrue(all(check["pass"] for check in report["checks"]))

        failing = verify_sampling_coverage({}, self.shots, self.anchors)
        self.assertFalse(failing["pass"])
        self.assertIn("missing_sampling_plan", {check["check"] for check in failing["checks"]})

        out = self.root / "sampling_coverage_report.json"
        args = type("Args", (), {
            "sampling_plan": str(plan_path),
            "shots": str(self.shots_path),
            "anchors": None,
            "out": str(out),
            "tolerance_sec": 0.35,
            "max_gap_sec": 1.25,
        })()
        video_tools.cmd_sampling_coverage(args)
        saved = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(saved["artifact_role"], "sampling_coverage_report")
        self.assertEqual(saved["sampling_plan_path"], str(plan_path))

    def test_chain_writes_sampling_coverage_and_montage_wall_artifacts(self):
        from video_pipeline_core.montage_wall import write_montage_wall
        from video_pipeline_core.sampling_coverage import write_sampling_coverage_report
        from video_pipeline_core.sampling_planner import write_sampling_plan

        plan_path = self.root / "sampling_plan.json"
        coverage_path = self.root / "sampling_coverage_report.json"
        wall_path = self.root / "wall.png"
        sidecar_path = self.root / "montage_wall.json"

        write_sampling_plan(self.video, self.shots, plan_path, audio_anchors=self.anchors)
        write_sampling_coverage_report(
            plan_path,
            self.shots_path,
            coverage_path,
            audio_anchors=self.anchors,
            max_gap_sec=1.25,
        )
        wall = write_montage_wall(
            self.video,
            plan_path,
            coverage_path,
            wall_path,
            sidecar_path,
            profile="material_wall",
        )

        for path in (plan_path, coverage_path, wall_path, sidecar_path):
            self.assertTrue(path.exists(), path)
            self.assertGreater(path.stat().st_size, 0)
        self.assertEqual(wall["artifact_role"], "montage_wall")
        self.assertEqual(wall["profile"], "material_wall")
        self.assertEqual(wall["coverage_report_path"], str(coverage_path))
        self.assertEqual(wall["sampling_plan_path"], str(plan_path))
        self.assertEqual(wall["wall_image_path"], str(wall_path))
        self.assertTrue(wall["cells"])
        self.assertTrue(all(cell["shot_id"] and "timestamp_sec" in cell for cell in wall["cells"]))
        saved = json.loads(sidecar_path.read_text(encoding="utf-8"))
        self.assertEqual(saved, wall)
        self.assertFalse(wall["limitations"])


if __name__ == "__main__":
    unittest.main()
