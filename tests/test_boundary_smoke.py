import json
import tempfile
import unittest
from pathlib import Path

from tools.boundary_smoke import run_boundary


def _write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def _segment(num, need_id):
    return {
        "segment": num,
        "core": {
            "section_role": "montage",
            "story_purpose": f"show training moment {num}",
            "timeline_source": "beat",
        },
        "material_fit": {
            "visual_desc": "cohort opening shot",
            "reason": "matches the requested opening need",
            "need_refs": [need_id],
        },
        "audio": {"role": "music", "reason": "recap montage pacing"},
        "visual_style": {"layout": "montage", "pace": "medium", "reason": "stable recap"},
        "text_layer": "none",
    }


class BoundarySmokeTest(unittest.TestCase):
    def test_stage1_story_blueprint_preserves_user_seed(self):
        with tempfile.TemporaryDirectory() as tmp:
            stage_dir = Path(tmp) / "stage1_story_blueprint"
            input_dir = stage_dir / "input"
            _write(input_dir / "boundary_config.json", {
                "stage": "stage1_story_blueprint",
                "expected": {
                    "ok": True,
                    "must_include_text": ["two lost siblings", "tiny lantern", "moon bridge"],
                    "must_not_include_text": ["courier", "postcard"],
                },
            })
            _write(input_dir / "project_brief.json", {
                "project_type": "generated storybook fairy tale",
                "audience": "children and parents",
                "goal": (
                    "Tell a warm, safe short fairy tale where a tiny lantern helps "
                    "two lost siblings find the moon bridge home."
                ),
                "known_material_categories": [],
                "desired_style": "Japanese cute picture-book illustration",
                "seed_device": "tiny lantern and moon bridge",
                "story_seed": {
                    "protagonists": ["two lost siblings", "a tiny kind lantern"],
                    "setting": "safe moonlit forest path",
                    "moral": "small kindness can become a path",
                },
                "facts": {
                    "protagonist": "two lost siblings and a tiny kind lantern",
                    "place": "safe moonlit forest path",
                },
                "required_inclusions": ["tiny lantern", "two siblings", "moon bridge"],
            })

            report = run_boundary(stage_dir)

            self.assertTrue(report["pass"], report)
            self.assertEqual(report["gate_source"], "story_soul_blueprint")
            self.assertEqual(report["gate_status"], "done")
            self.assertTrue((stage_dir / "actual" / "blueprint" / "screenplay_beats.json").exists())

    def test_stage3_review_apply_uses_lifecycle_verdict_for_build_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            stage_dir = Path(tmp) / "stage3_review_apply"
            input_dir = stage_dir / "input"
            need_id = "nd_opening"
            _write(input_dir / "boundary_config.json", {
                "stage": "stage3_review_apply",
                "expected": {"stage": "build_ready", "can_build": True},
            })
            _write(input_dir / "material_needs.json", {
                "artifact_role": "material_needs",
                "version": 1,
                "project": "boundary",
                "needs": [{
                    "need_id": need_id,
                    "category": "scene",
                    "type": "opening",
                    "purpose": "establish the cohort",
                    "count": 1,
                    "fallback_tier": 1,
                    "must_have": True,
                }],
            })
            _write(input_dir / "maps" / "clip-a.map.json", {
                "artifact_role": "material_map",
                "version": 1,
                "asset_id": "clip-a",
                "asset_type": "video",
                "source": "clip-a.mp4",
                "duration_sec": 12.0,
                "scenes": [{"start": 0, "end": 4, "caption": "class opening"}],
            })
            _write(input_dir / "materials_db.json", {
                "files": [{"id": "clip-a", "path": "clip-a.mp4", "material_map": "maps/clip-a.map.json"}],
            })
            _write(input_dir / "material_map_review_verdict.json", {
                "artifact_role": "material_map_review_verdict",
                "version": 1,
                "reviewer": "agent:director",
                "decisions": [{
                    "asset_id": "clip-a",
                    "scene_index": 0,
                    "need_id": need_id,
                    "status": "accepted",
                    "visual_evidence": ["visible trainees establish the cohort"],
                }],
            })
            _write(input_dir / "segment_contract.json", {
                "material_needs_ref": "material_needs.json",
                "segments": [_segment(1, need_id), _segment(2, need_id)],
            })

            report = run_boundary(stage_dir)

            self.assertTrue(report["pass"], report)
            self.assertEqual(report["gate_source"], "material_map_lifecycle")
            self.assertEqual(report["gate_status"], "build_ready")
            lifecycle = json.loads(
                (stage_dir / "actual" / "material_map_lifecycle.json").read_text(encoding="utf-8")
            )
            self.assertTrue(lifecycle["can_build"])
            self.assertEqual(lifecycle["next_action"], "build")


if __name__ == "__main__":
    unittest.main()
