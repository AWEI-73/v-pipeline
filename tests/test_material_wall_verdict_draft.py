import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class MaterialWallVerdictDraftTest(unittest.TestCase):
    def _matrix(self):
        def asset(asset_id, roles, risks=None):
            return {
                "asset_id": asset_id,
                "source_path": f"C:/media/{asset_id}.mp4",
                "media_type": "video",
                "duration_sec": 8.0,
                "role_hints": roles,
                "risk_flags": risks or [],
                "visual_evidence": {
                    "caption_hint": f"caption for {asset_id}",
                    "keyframes": [{"timestamp_sec": 2.0, "image_path": f"C:/frames/{asset_id}.jpg"}],
                },
                "audio_evidence": {"rough_audio_type": "unknown_until_soundtrack_probe_or_asr"},
            }

        return {
            "artifact_role": "material_understanding_matrix",
            "version": 1,
            "assets": [
                asset("open_a", ["opening"]),
                asset("open_b", ["opening"]),
                asset("train_a", ["training"]),
                asset("train_b", ["training"]),
                asset("close_a", ["closing"]),
                asset("close_b", ["closing"], risks=["possible_duplicate_name"]),
            ],
        }

    def test_draft_selects_one_primary_per_role_and_keeps_alternates_out_of_formal_keep(self):
        from video_pipeline_core.material_wall_verdict_draft import build_wall_verdict_draft

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "material_wall_review_verdict.draft.json"

            payload = build_wall_verdict_draft(
                self._matrix(),
                out_path=out,
                required_roles=["opening", "training", "closing"],
            )

            self.assertEqual(payload["artifact_role"], "material_wall_review_verdict")
            formal = {item["asset_id"]: item for item in payload["assets"]}
            self.assertEqual(formal["open_a"]["coarse_status"], "keep")
            self.assertEqual(formal["train_a"]["coarse_status"], "keep")
            self.assertEqual(formal["close_a"]["coarse_status"], "keep")
            self.assertEqual(formal["open_b"]["coarse_status"], "reject")
            self.assertEqual(formal["train_b"]["coarse_status"], "reject")
            self.assertEqual(formal["close_b"]["coarse_status"], "duplicate")
            self.assertNotIn("open_b", [item["asset_id"] for item in payload["assets"] if item["coarse_status"] in {"keep", "maybe"}])
            alternates = {item["asset_id"]: item for item in payload["alternate_candidates"]}
            self.assertEqual(alternates["open_b"]["for_role"], "opening")
            self.assertEqual(alternates["train_b"]["for_role"], "training")
            self.assertEqual(alternates["close_b"]["for_role"], "closing")
            self.assertTrue(out.exists())

    def test_cli_writes_draft(self):
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            matrix = root / "material_understanding_matrix.json"
            matrix.write_text(json.dumps(self._matrix()), encoding="utf-8")
            out = root / "material_wall_review_verdict.draft.json"

            proc = subprocess.run(
                [
                    sys.executable,
                    "tools/material_wall_verdict_draft.py",
                    "--matrix",
                    str(matrix),
                    "--out",
                    str(out),
                    "--roles",
                    "opening,training,closing",
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
            self.assertTrue(out.exists())

    def test_training_primary_prefers_practical_action_over_briefing_when_both_match_role(self):
        from video_pipeline_core.material_wall_verdict_draft import build_wall_verdict_draft

        matrix = {
            "artifact_role": "material_understanding_matrix",
            "version": 1,
            "assets": [
                {
                    "asset_id": "briefing",
                    "source_path": "C:/media/briefing.mp4",
                    "media_type": "video",
                    "duration_sec": 8.0,
                    "folder_tags": ["工安早會"],
                    "role_hints": ["training"],
                    "risk_flags": [],
                    "visual_evidence": {"caption_hint": "folder/file hint: 工安早會 / briefing"},
                },
                {
                    "asset_id": "practice",
                    "source_path": "C:/media/practice.mp4",
                    "media_type": "video",
                    "duration_sec": 8.0,
                    "folder_tags": ["換桿"],
                    "role_hints": ["training"],
                    "risk_flags": [],
                    "visual_evidence": {"caption_hint": "folder/file hint: 換桿 / practical operation"},
                },
            ],
        }

        payload = build_wall_verdict_draft(matrix, required_roles=["training"])

        self.assertEqual(payload["primary_selection"]["training"], "practice")
        formal = {item["asset_id"]: item for item in payload["assets"]}
        self.assertEqual(formal["practice"]["coarse_status"], "keep")
        self.assertEqual(formal["briefing"]["coarse_status"], "reject")


if __name__ == "__main__":
    unittest.main()
