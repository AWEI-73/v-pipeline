import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core.story_soul_blueprint import build_story_soul_blueprint


def _training_brief():
    return {
        "project_type": "graduation_training_film",
        "audience": "trainees, instructors, family, internal leadership",
        "duration_sec": 300,
        "facts": {
            "cohort": "66th training class",
            "time_span": "one intensive training period",
            "place": "training center",
        },
        "known_material_categories": [
            "morning assembly",
            "course montage",
            "director encouragement",
            "daily life",
            "blood donation",
            "leaving the center",
        ],
        "required_inclusions": ["director encouragement", "training completion"],
        "seed_device": "0.66% of life spent in training center",
    }


def _comic_brief():
    return {
        "project_type": "generated_comic_story",
        "audience": "short-form viewers",
        "duration_sec": 60,
        "facts": {
            "protagonist": "teen courier",
            "place": "sunset rooftops",
        },
        "known_material_categories": [],
        "desired_style": "clean manga watercolor",
        "seed_device": "one forgotten postcard crosses the city sky",
    }


class StorySoulBlueprintTest(unittest.TestCase):
    def test_training_blueprint_has_narrative_device_not_course_list(self):
        result = build_story_soul_blueprint(_training_brief())

        self.assertTrue(result["ok"], result.get("errors"))
        concept = result["creative_concept"]
        self.assertIn("0.66", concept["core_metaphor"])
        self.assertIn("report", concept["narrative_device"].lower())
        self.assertTrue(concept["why_this_is_not_a_course_list"])
        beats = result["screenplay_beats"]["beats"]
        self.assertGreaterEqual(len(beats), 8)
        self.assertLessEqual(len(beats), 12)
        for beat in beats:
            self.assertTrue(beat["existence_test"])
            self.assertGreaterEqual(beat["minimum_material_count"], 2)
            self.assertTrue(beat["fallback_if_missing"])
        needs = result["material_needs"]["needs"]
        self.assertGreaterEqual(len(needs), len(beats))
        self.assertTrue(any("generated" in " ".join(n.get("fallback_options") or [])
                            for n in needs))

    def test_generated_comic_blueprint_estimations_fit_duration(self):
        result = build_story_soul_blueprint(_comic_brief())

        self.assertTrue(result["ok"], result.get("errors"))
        self.assertEqual(result["story_world"]["project_type"], "generated_comic_story")
        beats = result["screenplay_beats"]["beats"]
        total_min = sum(beat["minimum_material_count"] for beat in beats)
        self.assertGreaterEqual(total_min, 18)
        shot_plan = result["director_shot_plan"]["shots"]
        self.assertTrue(all(shot["media_preference"] == "generated_image"
                            for shot in shot_plan))
        self.assertTrue(all(shot["prompt"] for shot in shot_plan))

    def test_screenplay_beats_have_turn_sensory_and_viewer_feeling(self):
        result = build_story_soul_blueprint(_training_brief())

        self.assertTrue(result["ok"], result.get("errors"))
        for beat in result["screenplay_beats"]["beats"]:
            self.assertTrue(beat.get("conflict_or_turn"), beat["beat_id"])
            self.assertTrue(beat.get("sensory_anchor"), beat["beat_id"])
            self.assertTrue(beat.get("intended_viewer_feeling"), beat["beat_id"])

    def test_director_shot_plan_has_dense_director_intent(self):
        result = build_story_soul_blueprint(_comic_brief())

        self.assertTrue(result["ok"], result.get("errors"))
        for shot in result["director_shot_plan"]["shots"]:
            intent = shot.get("director_intent")
            self.assertIsInstance(intent, dict, shot["beat_id"])
            for key in (
                "composition",
                "camera_motion",
                "edit_role",
                "audio_subtitle_intent",
                "material_prompt_requirements",
            ):
                self.assertTrue(intent.get(key), f"{shot['beat_id']} missing {key}")
            self.assertIn("clean manga watercolor", shot["prompt"])
            self.assertIn(shot["visual_family"], shot["prompt"])

    def test_generic_brief_without_story_subject_fails_closed(self):
        result = build_story_soul_blueprint({"project_type": "video"})

        self.assertFalse(result["ok"])
        self.assertIn("story subject", "; ".join(result["errors"]))

    def test_cli_writes_all_artifacts(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            brief = d / "brief.json"
            out_dir = d / "out"
            brief.write_text(json.dumps(_comic_brief()), encoding="utf-8")

            proc = subprocess.run(
                [
                    sys.executable,
                    "video_tools.py",
                    "story-soul-blueprint",
                    str(brief),
                    "--out-dir",
                    str(out_dir),
                ],
                cwd=root,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            for name in (
                "story_world.json",
                "creative_concept.json",
                "screenplay_beats.json",
                "director_shot_plan.json",
                "material_needs.json",
                "generation_manifest.json",
                "review_checklist.md",
            ):
                self.assertTrue((out_dir / name).exists(), name)

    def test_cli_accepts_utf8_bom_json_from_windows_tools(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            brief = d / "brief.json"
            out_dir = d / "out"
            brief.write_text(json.dumps(_comic_brief()), encoding="utf-8-sig")

            proc = subprocess.run(
                [
                    sys.executable,
                    "video_tools.py",
                    "story-soul-blueprint",
                    str(brief),
                    "--out-dir",
                    str(out_dir),
                ],
                cwd=root,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
