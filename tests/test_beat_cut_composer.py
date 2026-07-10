import importlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _composer_module():
    path = ROOT / "video_pipeline_core" / "beat_cut_composer.py"
    return importlib.import_module("video_pipeline_core.beat_cut_composer") if path.is_file() else None


def _accepted_assets(count):
    return [
        {
            "asset_id": f"accepted_{index:02d}",
            "source_relative_path": f"accepted/asset_{index:02d}.mp4",
            "accepted": True,
            "media_duration_sec": 4.0,
        }
        for index in range(count)
    ]


class BeatCutComposerTest(unittest.TestCase):
    def test_composes_fifteen_distinct_assets_on_real_beat_anchors(self):
        composer = _composer_module()
        self.assertIsNotNone(composer, "canonical beat-cut composer module is required")

        result = composer.compose_beat_cut_montage(
            _accepted_assets(15),
            beat_grid=[18.0 + (0.5 * index) for index in range(53)],
            window_start=18.0,
            window_end=44.0,
            fps=30,
            min_distinct_assets=15,
        )

        clips = result["clips"]
        self.assertGreaterEqual(len({clip["asset_id"] for clip in clips}), 15)
        self.assertEqual(clips[0]["timeline_in_sec"], 18.0)
        self.assertEqual(clips[-1]["timeline_out_sec"], 44.0)
        self.assertTrue(all(clip["source_lineage"]["accepted"] for clip in clips))
        report = composer.verify_beat_cut_alignment(
            {"clips": clips},
            [18.0 + (0.5 * index) for index in range(53)],
            window_start=18.0,
            window_end=44.0,
            fps=30,
        )
        self.assertTrue(report["pass"], report)
        self.assertEqual(report["within_one_frame_ratio"], 1.0)

    def test_rejects_insufficient_distinct_or_misaligned_montage(self):
        composer = _composer_module()
        self.assertIsNotNone(composer, "canonical beat-cut composer module is required")

        with self.assertRaises(ValueError):
            composer.compose_beat_cut_montage(
                _accepted_assets(14),
                beat_grid=[18.0 + (0.5 * index) for index in range(53)],
                window_start=18.0,
                window_end=44.0,
                fps=30,
                min_distinct_assets=15,
            )
        report = composer.verify_beat_cut_alignment(
            {"clips": [
                {"section": "montage", "timeline_in_sec": 18.0, "timeline_out_sec": 19.123},
                {"section": "montage", "timeline_in_sec": 19.123, "timeline_out_sec": 44.0},
            ]},
            [18.0, 19.0, 20.0, 44.0],
            window_start=18.0,
            window_end=44.0,
            fps=30,
        )
        self.assertFalse(report["pass"])
        self.assertLess(report["within_one_frame_ratio"], 1.0)

    def test_verifier_cli_writes_a_failing_alignment_report_without_repairing_timeline(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            timeline = root / "timeline_build.json"
            beats = root / "soundtrack_probe_report.json"
            out = root / "beat_cut_alignment_report.json"
            timeline.write_text(json.dumps({"clips": [
                {"section": "montage", "timeline_in_sec": 18.0, "timeline_out_sec": 19.123},
                {"section": "montage", "timeline_in_sec": 19.123, "timeline_out_sec": 44.0},
            ]}), encoding="utf-8")
            beats.write_text(json.dumps({"features": {"beat_times": [18.0, 19.0, 20.0, 44.0]}}), encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    "tools/verify_beat_cut_alignment.py",
                    "--timeline", str(timeline),
                    "--beats", str(beats),
                    "--window-start", "18",
                    "--window-end", "44",
                    "--fps", "30",
                    "--out", str(out),
                    "--json",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertNotEqual(completed.returncode, 0)
            self.assertTrue(out.is_file())
            report = json.loads(out.read_text(encoding="utf-8"))
            self.assertFalse(report["pass"])
