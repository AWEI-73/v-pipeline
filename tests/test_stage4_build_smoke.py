import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.stage4_build_smoke import run_stage4_build_smoke


def _write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _clip(segment, asset_id, source_path, start_sec=1.0, duration_sec=4.0):
    return {
        "segment": segment,
        "need_id": f"nd_{segment}",
        "asset_id": asset_id,
        "asset_type": "video",
        "source_path": source_path,
        "scene_id": f"{asset_id}:0",
        "scene_index": 0,
        "start_sec": start_sec,
        "duration_sec": duration_sec,
        "available_range_sec": 8.0,
        "source_repeat_count": 1,
    }


def _timeline_clip(rough_clip, *, source_path=None, start_sec=None, duration_sec=None):
    start = rough_clip["start_sec"] if start_sec is None else start_sec
    duration = rough_clip["duration_sec"] if duration_sec is None else duration_sec
    return {
        "segment": rough_clip["segment"],
        "source_path": rough_clip["source_path"] if source_path is None else source_path,
        "start_sec": start,
        "end_sec": start + duration,
        "duration_sec": duration,
        "scene_id": rough_clip["scene_id"],
    }


def _write_build_ready_run(root, *, rough_overrides=None, timeline_overrides=None, handoff=None):
    clips = [
        _clip(1, "real_0001", "opening.mp4"),
        _clip(2, "real_0002", "training.mp4", start_sec=2.0),
        _clip(3, "real_0003", "closing.mp4"),
    ]
    rough = {
        "artifact_role": "rough_cut_plan",
        "version": 1,
        "ok": True,
        "clip_count": 3,
        "gap_count": 0,
        "total_duration_sec": 12.0,
        "clips": clips,
        "gaps": [],
    }
    if rough_overrides:
        rough.update(rough_overrides)
    timeline = {
        "artifact_role": "timeline_build",
        "source_artifact": "rough_cut_plan",
        "clips": [_timeline_clip(clip) for clip in clips],
    }
    if timeline_overrides:
        timeline.update(timeline_overrides)
    _write(root / "rough_cut_plan.json", rough)
    _write(root / "timeline_build.json", timeline)
    _write(root / "editor_review.json", {
        "artifact_role": "editor_review",
        "decision": "human_review",
    })
    _write(root / "material_wall_handoff_report.json", handoff or {
        "artifact_role": "material_wall_handoff_report",
        "selected_asset_ids": ["real_0001", "real_0002", "real_0003"],
        "rejected_asset_ids": [],
        "duplicate_asset_ids": [],
        "ready_for_mapping": True,
    })


def _write_product_handoff(root, *, deferred_items=None, cut_overrides=None):
    cuts = [
        {
            "id": "cut_001",
            "segment": 1,
            "source": "opening.mp4",
            "in_seconds": 1.0,
            "out_seconds": 5.0,
            "target_duration_sec": 4.0,
            "scene_id": "real_0001:0",
        },
        {
            "id": "cut_002",
            "segment": 2,
            "source": "training.mp4",
            "in_seconds": 2.0,
            "out_seconds": 6.0,
            "target_duration_sec": 4.0,
            "scene_id": "real_0002:0",
        },
        {
            "id": "cut_003",
            "segment": 3,
            "source": "closing.mp4",
            "in_seconds": 1.0,
            "out_seconds": 5.0,
            "target_duration_sec": 4.0,
            "scene_id": "real_0003:0",
        },
    ]
    if cut_overrides:
        cuts[1].update(cut_overrides)
    deferred = deferred_items or []
    _write(root / "edit_decision_plan.json", {
        "artifact_role": "edit_decision_plan",
        "version": 1,
        "cuts": cuts,
        "audio": {"music": {"asset_id": "audio/theme.mp3"}},
        "effects": [],
        "subtitles": {"enabled": False},
    })
    _write(root / "build_handoff.json", {
        "artifact_role": "build_handoff",
        "version": 1,
        "ready_for_build": not deferred,
        "accepted_handoffs": {
            "material": "rough_cut_plan.json",
            "audio": "audio_director_handoff.json",
        },
        "deferred_items": deferred,
        "product_artifacts": {
            "edit_decision_plan": "edit_decision_plan.json",
        },
    })


class Stage4BuildSmokeTest(unittest.TestCase):
    def test_build_ready_timeline_passes_and_writes_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            _write_build_ready_run(run_dir)

            result = run_stage4_build_smoke(run_dir)

            self.assertTrue(result["ok"], result)
            report = json.loads((run_dir / "stage4_build_smoke_report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["artifact_role"], "stage4_build_smoke_report")
            self.assertEqual(report["clip_count"], 3)
            self.assertEqual(report["timeline_clip_count"], 3)
            self.assertEqual(report["issues"], [])
            self.assertEqual(report["asset_ids"], ["real_0001", "real_0002", "real_0003"])

    def test_rough_cut_gap_fails_stage4(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            _write_build_ready_run(run_dir, rough_overrides={
                "ok": False,
                "gap_count": 1,
                "gaps": [{"segment": 2, "need_id": "nd_training", "reason": "missing"}],
            })

            result = run_stage4_build_smoke(run_dir)

            self.assertFalse(result["ok"], result)
            self.assertIn("rough_cut_gap", [issue["rule"] for issue in result["report"]["issues"]])

    def test_timeline_mismatch_fails_stage4(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            clips = [
                _clip(1, "real_0001", "opening.mp4"),
                _clip(2, "real_0002", "training.mp4", start_sec=2.0),
                _clip(3, "real_0003", "closing.mp4"),
            ]
            _write_build_ready_run(run_dir, timeline_overrides={
                "clips": [
                    _timeline_clip(clips[0]),
                    _timeline_clip(clips[1], source_path="wrong.mp4"),
                    _timeline_clip(clips[2]),
                ],
            })

            result = run_stage4_build_smoke(run_dir)

            self.assertFalse(result["ok"], result)
            self.assertIn("timeline_mismatch", [issue["rule"] for issue in result["report"]["issues"]])

    def test_rejected_or_duplicate_asset_fails_stage4(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            _write_build_ready_run(run_dir, handoff={
                "artifact_role": "material_wall_handoff_report",
                "selected_asset_ids": ["real_0001"],
                "rejected_asset_ids": ["real_0002"],
                "duplicate_asset_ids": ["real_0003"],
                "ready_for_mapping": True,
            })

            result = run_stage4_build_smoke(run_dir)

            self.assertFalse(result["ok"], result)
            rules = [issue["rule"] for issue in result["report"]["issues"]]
            self.assertIn("invalid_material_asset", rules)

    def test_cli_outputs_json_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            _write_build_ready_run(run_dir)

            completed = subprocess.run(
                [
                    sys.executable,
                    "tools/stage4_build_smoke.py",
                    "--run",
                    str(run_dir),
                    "--json",
                ],
                cwd=Path(__file__).resolve().parents[1],
                text=True,
                capture_output=True,
                check=True,
            )

            result = json.loads(completed.stdout)
            self.assertTrue(result["ok"], result)
            self.assertEqual(result["report"]["timeline_clip_count"], 3)

    def test_product_handoff_passes_when_cuts_match_timeline(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            _write_build_ready_run(run_dir)
            _write_product_handoff(run_dir)

            result = run_stage4_build_smoke(run_dir)

            self.assertTrue(result["ok"], result)
            self.assertEqual(result["report"]["product_handoff_status"], "pass")
            self.assertEqual(result["report"]["edit_decision_cut_count"], 3)
            self.assertIn("build_handoff.json", result["report"]["read"])
            self.assertIn("edit_decision_plan.json", result["report"]["read"])

    def test_product_handoff_deferred_items_fail_stage4(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            _write_build_ready_run(run_dir)
            _write_product_handoff(run_dir, deferred_items=[
                {
                    "owner": "effect-factory",
                    "reason": "effect_handoff.json is absent",
                    "return_point": "compile_edit_decision_plan",
                }
            ])

            result = run_stage4_build_smoke(run_dir)

            self.assertFalse(result["ok"], result)
            self.assertIn("build_handoff_deferred", [issue["rule"] for issue in result["report"]["issues"]])

    def test_edit_decision_mismatch_fails_stage4(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            _write_build_ready_run(run_dir)
            _write_product_handoff(run_dir, cut_overrides={"source": "wrong.mp4"})

            result = run_stage4_build_smoke(run_dir)

            self.assertFalse(result["ok"], result)
            self.assertIn("edit_decision_mismatch", [issue["rule"] for issue in result["report"]["issues"]])


if __name__ == "__main__":
    unittest.main()
