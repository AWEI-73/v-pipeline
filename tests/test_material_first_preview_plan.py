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

    def test_extends_unique_candidates_before_repeating_assets(self):
        from video_pipeline_core.material_first_preview_plan import build_preview_plan

        matrix = {
            "artifact_role": "material_understanding_matrix",
            "version": 1,
            "assets": [
                {
                    "asset_id": f"asset_{index}",
                    "source_path": f"C:/media/asset_{index}.mp4",
                    "media_type": "video",
                    "duration_sec": 8.0,
                    "role_hints": [["opening", "training", "closing"][index % 3]],
                    "visual_evidence": {"caption_hint": f"asset {index}"},
                }
                for index in range(8)
            ],
        }
        draft = {
            "artifact_role": "material_wall_review_verdict",
            "version": 1,
            "primary_selection": {
                "opening": "asset_0",
                "training": "asset_1",
                "closing": "asset_2",
            },
            "alternate_candidates": [
                {"asset_id": f"asset_{index}", "for_role": ["opening", "training", "closing"][index % 3]}
                for index in range(3, 8)
            ],
        }

        plan = build_preview_plan(
            matrix,
            draft,
            target_duration_sec=72,
            min_duration_sec=60,
            max_duration_sec=90,
            clip_duration_sec=6,
        )

        asset_ids = [clip["asset_id"] for clip in plan["clips"]]
        self.assertTrue(plan["ok"], plan)
        self.assertGreaterEqual(plan["total_duration_sec"], 60)
        self.assertEqual(len(asset_ids), len(set(asset_ids)))
        self.assertTrue(any(clip["duration_sec"] > 6 for clip in plan["clips"]))

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

    def test_writes_json_safe_windows_paths_with_chinese_and_numeric_folder(self):
        from video_pipeline_core.material_first_preview_plan import build_preview_plan

        matrix = {
            "artifact_role": "material_understanding_matrix",
            "version": 1,
            "assets": [
                {
                    "asset_id": "closing_a",
                    "source_path": r"C:\素材\運動會\66期配四班隊呼.mp4",
                    "media_type": "video",
                    "duration_sec": 20.0,
                    "role_hints": ["closing"],
                    "visual_evidence": {"caption_hint": "closing"},
                }
            ],
        }
        draft = {
            "artifact_role": "material_wall_review_verdict",
            "version": 1,
            "primary_selection": {"closing": "closing_a"},
        }

        plan = build_preview_plan(
            matrix,
            draft,
            target_duration_sec=8,
            min_duration_sec=1,
            max_duration_sec=10,
            clip_duration_sec=8,
            roles=["closing"],
        )
        encoded = json.dumps(plan, ensure_ascii=False)
        parsed = json.loads(encoded)

        self.assertEqual(
            parsed["clips"][0]["source_path"],
            "C:/素材/運動會/66期配四班隊呼.mp4",
        )


if __name__ == "__main__":
    unittest.main()
