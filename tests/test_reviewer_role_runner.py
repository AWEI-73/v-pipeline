import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core import reviewer_registry
from video_pipeline_core.reviewer_role_runner import review_artifacts


ROOT = Path(__file__).resolve().parents[1]


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _story_case(root: Path, *, duration_sec: int, panel_count: int, beat_count: int = 6) -> dict:
    beats = []
    needs = []
    assets = []
    for idx in range(beat_count):
        need_id = f"nd_{idx + 1:02d}"
        beats.append(
            {
                "beat_id": f"beat_{idx + 1:02d}",
                "title": f"Beat {idx + 1}",
                "conflict_or_turn": "turn",
                "intended_viewer_feeling": "curiosity",
                "visual_intent": "clear story action",
            }
        )
        needs.append({"need_id": need_id, "count": 1, "must_have": True})
    for idx in range(panel_count):
        need_id = needs[min(idx, len(needs) - 1)]["need_id"]
        assets.append(
            {
                "asset_id": f"panel_{idx + 1:02d}",
                "asset_type": "generated_image",
                "scenes": [
                    {
                        "scene_index": 0,
                        "satisfies": [{"need_id": need_id, "status": "accepted"}],
                    }
                ],
            }
        )
    brief = {
        "video_type": "storybook",
        "duration_sec": duration_sec,
        "target_length": f"{duration_sec} seconds",
        "audience": "children",
        "tone": "warm story",
    }
    screenplay = {"artifact_role": "screenplay_beats", "version": 1, "beats": beats}
    material_needs = {"artifact_role": "material_needs", "version": 1, "needs": needs}
    project_map = {"artifact_role": "project_material_map", "version": 1, "assets": assets}
    _write_json(root / "project_brief.json", brief)
    _write_json(root / "screenplay_beats.json", screenplay)
    _write_json(root / "material_needs.json", material_needs)
    _write_json(root / "reviewed_project_material_map.json", project_map)
    return {
        "project_brief": root / "project_brief.json",
        "screenplay_beats": root / "screenplay_beats.json",
        "material_needs": root / "material_needs.json",
        "project_material_map": root / "reviewed_project_material_map.json",
    }


class ReviewerRoleRunnerTest(unittest.TestCase):
    def test_story_director_revises_when_story_visual_density_is_too_sparse(self):
        with tempfile.TemporaryDirectory() as td:
            paths = _story_case(Path(td), duration_sec=90, panel_count=6)

            review = review_artifacts("story_director", paths)

        self.assertEqual(review["artifact_role"], "artifact_review")
        self.assertEqual(review["reviewer_role"], "story_director")
        self.assertEqual(review["decision"], "revise")
        self.assertEqual(review["gate_strength"], "revise")
        self.assertEqual(review["next_action"], "revise_shot_plan")
        finding_codes = {item["code"] for item in review["findings"]}
        self.assertIn("visual_rhythm_too_sparse", finding_codes)
        self.assertGreater(review["metrics"]["avg_hold_per_visual_sec"], 10)
        self.assertTrue(reviewer_registry.validate_review_artifact(review)["ok"])

    def test_story_director_passes_dense_storyboard_without_story_specific_rules(self):
        with tempfile.TemporaryDirectory() as td:
            paths = _story_case(Path(td), duration_sec=90, panel_count=14)

            review = review_artifacts("story_director", paths)

        self.assertEqual(review["decision"], "pass")
        self.assertEqual(review["gate_strength"], "revise")
        self.assertEqual(review["findings"], [])
        self.assertLess(review["metrics"]["avg_hold_per_visual_sec"], 8)
        self.assertTrue(reviewer_registry.validate_review_artifact(review)["ok"])

    def test_cli_writes_role_review_json(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            paths = _story_case(root, duration_sec=90, panel_count=6)
            out = root / "story_director_review.json"

            proc = subprocess.run(
                [
                    sys.executable,
                    "video_tools.py",
                    "reviewer-role-review",
                    "--role",
                    "story_director",
                    "--project-brief",
                    str(paths["project_brief"]),
                    "--screenplay-beats",
                    str(paths["screenplay_beats"]),
                    "--material-needs",
                    str(paths["material_needs"]),
                    "--project-map",
                    str(paths["project_material_map"]),
                    "--out",
                    str(out),
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(payload["reviewer_role"], "story_director")
            self.assertEqual(payload["decision"], "revise")

    def test_material_producer_blocks_when_delta_is_not_ready(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            paths = _story_case(root, duration_sec=90, panel_count=6)
            delta = {
                "artifact_role": "material_delta",
                "version": 1,
                "ready_for_build": False,
                "summary": {"covered": 5, "thin": 0, "missing": 1, "excess": 0},
                "missing": [{"need_id": "nd_missing"}],
            }
            delta_path = root / "material_delta.json"
            _write_json(delta_path, delta)

            review = review_artifacts("material_producer", {
                **paths,
                "material_delta": delta_path,
            })

        self.assertEqual(review["artifact_role"], "artifact_review")
        self.assertEqual(review["reviewer_role"], "material_producer")
        self.assertEqual(review["decision"], "block")
        self.assertEqual(review["gate_strength"], "hard_gate")
        self.assertEqual(review["next_action"], "await_material")
        self.assertEqual(review["findings"][0]["code"], "material_delta_not_ready")
        self.assertTrue(reviewer_registry.validate_review_artifact(review)["ok"])

    def test_material_producer_passes_when_delta_is_ready(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            paths = _story_case(root, duration_sec=90, panel_count=6)
            delta_path = root / "material_delta.json"
            _write_json(delta_path, {
                "artifact_role": "material_delta",
                "version": 1,
                "ready_for_build": True,
                "summary": {"covered": 6, "thin": 0, "missing": 0, "excess": 0},
            })

            review = review_artifacts("material_producer", {
                **paths,
                "material_delta": delta_path,
            })

        self.assertEqual(review["decision"], "pass")
        self.assertEqual(review["findings"], [])

    def test_material_producer_blocks_missing_even_when_delta_allows_fallback_build(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            paths = _story_case(root, duration_sec=90, panel_count=6)
            delta_path = root / "material_delta.json"
            _write_json(delta_path, {
                "artifact_role": "material_delta",
                "version": 1,
                "ready_for_build": True,
                "summary": {"covered": 5, "thin": 0, "missing": 1, "excess": 0},
                "missing": [{"need_id": "nd_missing", "fallback_options": ["generated_image"]}],
            })

            review = review_artifacts("material_producer", {
                **paths,
                "material_delta": delta_path,
            })

        self.assertEqual(review["decision"], "block")
        self.assertEqual(review["next_action"], "await_material")
        self.assertEqual(review["findings"][0]["code"], "material_delta_not_ready")


if __name__ == "__main__":
    unittest.main()
