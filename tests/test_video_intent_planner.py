import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core.video_intent_planner import plan_video_intent


class VideoIntentPlannerTest(unittest.TestCase):
    def test_existing_material_enters_material_first_for_ambiguity_reduction(self):
        intent = plan_video_intent(
            {
                "request": "teaching video with existing class and screen-recording material",
                "video_type": "teaching",
                "audience": "new students",
                "goal": "teach clearly",
                "target_length": "5 minutes",
                "material_availability": "existing",
                "material_quality": "enough usable screen recordings",
                "tone": "clear instructional",
            }
        )

        self.assertEqual(intent["artifact_role"], "video_intent")
        self.assertEqual(intent["stage"], "Video Intent Planner")
        self.assertEqual(intent["video_type"], "teaching")
        self.assertEqual(intent["input_state"], "material_available")
        self.assertEqual(intent["entry_path"], "material-first")
        self.assertEqual(intent["route"], "material-first")
        self.assertEqual(intent["legacy_route"], "existing-material-first")
        self.assertEqual(intent["handoff_to"], "material_map_lifecycle")
        self.assertEqual(intent["gap_strategy"], "pending_material_delta")
        self.assertEqual(intent["handoff_packet"]["owner"], "material_map_lifecycle")
        self.assertEqual(intent["handoff_packet"]["first_action"], "material_map_quick_inventory")
        self.assertIn("project_material_map.json", intent["handoff_packet"]["expected_outputs"])
        self.assertIn("material_delta.json", intent["handoff_packet"]["expected_outputs"])
        self.assertIn("teaching-structure-planner", intent["later_planner"])
        self.assertEqual(intent["required_followup_questions"], [])

    def test_zero_material_with_text_or_story_enters_structure_first(self):
        intent = plan_video_intent(
            {
                "request": "children storybook video with no images but a story idea",
                "video_type": "storybook",
                "audience": "children",
                "goal": "tell a gentle bedtime story",
                "target_length": "3 minutes",
                "material_availability": "none",
                "text_availability": "brief",
                "generation_allowed": True,
                "tone": "warm story-driven",
            }
        )

        self.assertEqual(intent["input_state"], "text_available")
        self.assertEqual(intent["entry_path"], "structure-first")
        self.assertEqual(intent["route"], "structure-first")
        self.assertEqual(intent["legacy_route"], "story-first")
        self.assertEqual(intent["handoff_to"], "upstream_structure_route")
        self.assertEqual(intent["handoff_packet"]["owner"], "upstream_structure_route")
        self.assertEqual(intent["handoff_packet"]["first_action"], "story_soul_blueprint")
        self.assertTrue(intent["needs_generated_material_fallback"])
        self.assertIn("generated material fallback", " ".join(intent["next_steps"]))

    def test_partial_material_still_enters_material_first_not_stage_zero_hybrid(self):
        intent = plan_video_intent(
            {
                "request": "graduation event recap with partial material",
                "video_type": "graduation-event",
                "audience": "classmates and instructors",
                "goal": "commemorate the training journey",
                "target_length": "4 minutes",
                "material_availability": "partial",
                "material_quality": "some gaps",
                "tone": "energetic and warm",
            }
        )

        self.assertEqual(intent["input_state"], "material_available")
        self.assertEqual(intent["entry_path"], "material-first")
        self.assertEqual(intent["route"], "material-first")
        self.assertEqual(intent["legacy_route"], "hybrid")
        self.assertEqual(intent["handoff_to"], "material_map_lifecycle")
        self.assertEqual(intent["gap_strategy"], "pending_material_delta")
        self.assertTrue(intent["needs_material_map_first"])
        self.assertIn("event-recap-planner", intent["later_planner"])

    def test_idea_only_without_type_or_audience_needs_context(self):
        intent = plan_video_intent({"request": "make me a video"})

        self.assertEqual(intent["input_state"], "unknown")
        self.assertEqual(intent["entry_path"], "needs-context")
        self.assertIsNone(intent["legacy_route"])
        self.assertEqual(intent["handoff_to"], "ask_followup")
        self.assertEqual(intent["handoff_packet"]["owner"], "Video Intent Planner")
        self.assertEqual(intent["handoff_packet"]["first_action"], "ask_followup_questions")
        self.assertGreaterEqual(len(intent["required_followup_questions"]), 4)
        question_text = " ".join(intent["required_followup_questions"]).lower()
        self.assertIn("material", question_text)
        self.assertIn("audience", question_text)


class VideoIntentPlannerCliTest(unittest.TestCase):
    def test_cli_writes_video_intent_json(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            brief = root / "brief.json"
            out = root / "video_intent.json"
            brief.write_text(
                json.dumps(
                    {
                        "request": "teaching video with existing material",
                        "video_type": "teaching",
                        "audience": "beginners",
                        "goal": "teach the workflow",
                        "target_length": "6 minutes",
                        "material_availability": "existing",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            subprocess.run(
                [
                    sys.executable,
                    "video_tools.py",
                    "video-intent-plan",
                    str(brief),
                    "--out",
                    str(out),
                ],
                check=True,
                cwd=Path(__file__).resolve().parents[1],
                stdout=subprocess.DEVNULL,
            )

            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(payload["artifact_role"], "video_intent")
            self.assertEqual(payload["entry_path"], "material-first")


if __name__ == "__main__":
    unittest.main()
