import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core.platform_tools import resolve_ffmpeg


class MaterialFirstHappyPathTest(unittest.TestCase):
    def _write_video(self, path: Path, color: str):
        path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                resolve_ffmpeg(),
                "-y",
                "-hide_banner",
                "-f",
                "lavfi",
                "-i",
                f"color=c={color}:s=160x90:d=9",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                str(path),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def _source_dir(self, root: Path) -> Path:
        source = root / "source"
        self._write_video(source / "opening drone" / "MAX_0169.mp4", "red")
        self._write_video(source / "training pole" / "IMG_8346.mp4", "blue")
        self._write_video(source / "closing group" / "group_call.mp4", "green")
        self._write_video(source / "training safety" / "IMG_8515.mp4", "yellow")
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
            matrix = json.loads(
                (run_dir / "material_understanding" / "material_understanding_matrix.json").read_text(encoding="utf-8-sig")
            )
            keyframes = [
                Path(item["image_path"])
                for asset in matrix["assets"]
                for item in asset["visual_evidence"]["keyframes"]
                if item.get("image_path")
            ]
            self.assertTrue(keyframes)
            self.assertTrue(all(path.is_file() for path in keyframes))
            self.assertTrue(all(run_dir in path.parents for path in keyframes))

    def test_wrapper_carries_video_intent_stage0_contracts_into_acceptance(self):
        from tools.pipeline_home import summarize_run

        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self._source_dir(root)
            run_dir = root / "run"
            intent = root / "video_intent.json"
            intent.write_text(json.dumps({
                "artifact_role": "video_intent",
                "entry_path": "material-first",
                "soundtrack_contract": {
                    "music_role": "mixed",
                    "handoff_to": "soundtrack-arranger",
                },
                "effect_policy": {
                    "activation": "defer_to_brownfield_or_segment_review",
                    "handoff_to": "effect-factory",
                },
                "subtitle_voiceover_contract": {
                    "subtitle_required": True,
                    "voiceover_required": False,
                    "handoff_to": "subtitle-director",
                },
            }), encoding="utf-8")

            proc = subprocess.run(
                [
                    sys.executable,
                    "tools/material_first_happy_path.py",
                    "--out",
                    str(run_dir),
                    "--source-dir",
                    str(source),
                    "--video-intent",
                    str(intent),
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
            report = json.loads((run_dir / "material_first_boundary_acceptance_report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["stage0_contracts"]["soundtrack"]["handoff_to"], "soundtrack-arranger")
            self.assertEqual(report["stage0_contracts"]["effect"]["handoff_to"], "effect-factory")
            self.assertTrue(report["stage0_contracts"]["subtitle_voiceover"]["subtitle_required"])
            summary = summarize_run(run_dir)
            self.assertEqual(summary["cursor"], "soundtrack_arranger")
            self.assertEqual(summary["next"], "soundtrack-arrange")

    def test_wrapper_preserves_video_intent_when_it_starts_inside_output_folder(self):
        from tools.pipeline_home import summarize_run

        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self._source_dir(root)
            run_dir = root / "run"
            run_dir.mkdir()
            intent = run_dir / "video_intent.json"
            intent.write_text(json.dumps({
                "artifact_role": "video_intent",
                "entry_path": "material-first",
                "soundtrack_contract": {
                    "music_role": "mixed",
                    "handoff_to": "soundtrack-arranger",
                },
            }), encoding="utf-8")

            proc = subprocess.run(
                [
                    sys.executable,
                    "tools/material_first_happy_path.py",
                    "--out",
                    str(run_dir),
                    "--source-dir",
                    str(source),
                    "--video-intent",
                    str(intent),
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
            self.assertTrue((run_dir / "video_intent.json").is_file())
            report = json.loads((run_dir / "material_first_boundary_acceptance_report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["stage0_contracts"]["soundtrack"]["handoff_to"], "soundtrack-arranger")
            summary = summarize_run(run_dir)
            self.assertEqual(summary["next"], "soundtrack-arrange")


if __name__ == "__main__":
    unittest.main()
