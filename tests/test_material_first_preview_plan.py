import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class MaterialFirstPreviewPlanTest(unittest.TestCase):
    def _matrix(self):
        assets = []
        roles = [
            ("open_a", ["opening"]),
            ("train_a", ["training"]),
            ("close_a", ["closing"]),
            ("open_b", ["opening"]),
            ("train_b", ["training"]),
            ("close_b", ["closing"]),
        ]
        for asset_id, role_hints in roles:
            assets.append({
                "asset_id": asset_id,
                "source_path": f"C:/media/{asset_id}.mp4",
                "media_type": "video",
                "duration_sec": 20.0,
                "role_hints": role_hints,
                "visual_evidence": {"caption_hint": f"{asset_id} caption"},
                "risk_flags": [],
            })
        return {"artifact_role": "material_understanding_matrix", "version": 1, "assets": assets}

    def _draft(self):
        return {
            "artifact_role": "material_wall_review_verdict",
            "version": 1,
            "primary_selection": {
                "opening": "open_a",
                "training": "train_a",
                "closing": "close_a",
            },
            "alternate_candidates": [
                {"asset_id": "open_b", "for_role": "opening", "reason": "alternate"},
                {"asset_id": "train_b", "for_role": "training", "reason": "alternate"},
                {"asset_id": "close_b", "for_role": "closing", "reason": "alternate"},
            ],
        }

    def test_builds_reviewable_preview_between_target_bounds_without_canonical_claim(self):
        from video_pipeline_core.material_first_preview_plan import build_preview_plan

        plan = build_preview_plan(
            self._matrix(),
            self._draft(),
            target_duration_sec=66,
            min_duration_sec=60,
            max_duration_sec=90,
            clip_duration_sec=6,
        )

        self.assertEqual(plan["artifact_role"], "material_first_preview_rough_cut_plan")
        self.assertTrue(plan["ok"], plan)
        self.assertGreaterEqual(plan["total_duration_sec"], 60)
        self.assertLessEqual(plan["total_duration_sec"], 90)
        self.assertEqual(plan["decision_scope"], "preview_proposal_not_canonical_timeline")
        self.assertEqual(plan["review_required"], "material_wall_or_workbench_review_before_render")
        statuses = {clip["asset_id"]: clip["selection_status"] for clip in plan["clips"]}
        self.assertEqual(statuses["open_a"], "primary")
        self.assertEqual(statuses["open_b"], "alternate")
        self.assertTrue(all(clip["source_path"] for clip in plan["clips"]))

    def test_cli_writes_preview_plan(self):
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            matrix = root / "matrix.json"
            draft = root / "draft.json"
            out = root / "preview_rough_cut_plan.json"
            matrix.write_text(json.dumps(self._matrix()), encoding="utf-8")
            draft.write_text(json.dumps(self._draft()), encoding="utf-8")

            proc = subprocess.run(
                [
                    sys.executable,
                    "tools/material_first_preview_plan.py",
                    "--matrix",
                    str(matrix),
                    "--wall-verdict-draft",
                    str(draft),
                    "--out",
                    str(out),
                    "--target-duration",
                    "66",
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
            self.assertTrue(out.exists())


if __name__ == "__main__":
    unittest.main()
