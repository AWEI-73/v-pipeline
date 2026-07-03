from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


class InteractiveSkillFlowDocsTest(unittest.TestCase):
    def test_video_pipeline_declares_interactive_skill_flow_entry(self):
        text = read("skills/video-pipeline.md")
        for expected in [
            "ISF1 Interactive Skill Flow",
            "流程固化，不是樣板固化",
            "video-workflow",
            "story-soul-blueprint",
            "material-map",
            "generated-material-producer",
            "Workbench",
            "state.json",
        ]:
            self.assertIn(expected, text)

    def test_video_workflow_defines_interactive_artifact_contract(self):
        text = read("skills/video-workflow.md")
        for expected in [
            "ISF1 Interactive Brief Contract",
            "storyboard_panel_locked",
            "project_brief.json",
            "story_world.json",
            "creative_concept.json",
            "screenplay_beats.json",
            "director_shot_plan.json",
            "material_needs.json",
            "停止條件",
            "下一步條件",
        ]:
            self.assertIn(expected, text)

    def test_route_uses_current_next_action_vocabulary(self):
        text = read("skills/archive/route.md")
        for expected in [
            "wait_for_generated_provider",
            "await_visual_review",
            "await_material_visual_review",
            "revise:material(material_delta)",
            "fix_timeline_or_assembly",
        ]:
            self.assertIn(expected, text)
        self.assertNotIn("route 只會回 BUILD", text)
        self.assertNotIn("needs_generated(seg=", text)

    def test_material_first_boundary_acceptance_cli_is_documented(self):
        for rel in [
            "docs/START_HERE_VIDEO_PIPELINE.md",
            "skills/video-pipeline-route.md",
            "docs/route-agent-runner-protocol.md",
        ]:
            text = read(rel)
            self.assertIn("tools/material_first_boundary_acceptance.py", text, rel)
            self.assertIn("material_first_boundary_acceptance_report.json", text, rel)
            self.assertIn("do not substitute `--source-dir`", text, rel)

    def test_roadmap_and_index_point_to_isf1_decision(self):
        roadmap = read("roadmap.md")
        index = read("docs/INDEX.md")
        self.assertIn("ISF1 Interactive Skill Flow", roadmap)
        self.assertIn("2026-06-19-interactive-skill-flow.md", roadmap)
        self.assertIn("2026-06-19-interactive-skill-flow.md", index)


if __name__ == "__main__":
    unittest.main()
