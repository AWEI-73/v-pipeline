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

    def test_current_entry_and_index_keep_interactive_flow_discoverable(self):
        roadmap = read("roadmap.md")
        index = read("docs/INDEX.md")
        self.assertIn("Story / structure clarification", roadmap)
        self.assertIn("RUNBOOK.md", roadmap)
        self.assertIn("2026-06-19-interactive-skill-flow.md", index)

    def test_start_here_is_orientation_only_not_an_operational_entry(self):
        text = read("docs/START_HERE_VIDEO_PIPELINE.md")
        self.assertIn("<!-- DOCUMENT_ROLE: ORIENTATION -->", text)
        self.assertNotIn("<!-- OPERATIONAL_ENTRY: RUNBOOK -->", text)
        self.assertNotIn("active_work_order", text)
        self.assertNotIn("authoritative_state_artifact", text)
        self.assertIn("Current E2E review hardening source:", text)
        self.assertIn(
            "docs/construction-guides/agent-orchestration/2026-06-22-integrated-e2e-review-action-plan.md",
            text,
        )
        self.assertIn("construction review, not a replacement for the canonical route docs.", text)

    def test_docs_index_is_map_only_and_historical_links_stay_non_authoritative(self):
        text = read("docs/INDEX.md")
        self.assertIn("<!-- DOCUMENT_ROLE: MAP -->", text)
        self.assertNotIn("<!-- OPERATIONAL_ENTRY: RUNBOOK -->", text)
        self.assertNotIn("active_work_order", text)
        self.assertNotIn("authoritative_state_artifact", text)
        self.assertIn("Current Editing Loop continuation", text)
        self.assertIn(
            "docs/construction-guides/work-orders/2026-07-11-editing-loop-anchor-health-integrated-longform-campaign.md",
            text,
        )
        self.assertIn("stop at the declared owner gate.", text)

    def test_editorial_ambiguity_loop_grills_one_decision_without_adding_a_route(self):
        text = read("skills/editorial-ambiguity-loop.md")
        for expected in [
            "Interactive grilling discipline",
            "Ask decisions; inspect facts",
            "ask exactly one question",
            '"question_id"',
            '"branch_id"',
            '"fills"',
            '"environment_facts"',
            '"recommended_answer"',
            "interaction_log.md",
            "worker_information_projection",
            "content_taxonomy.training_units[]",
            "Small-model emission preflight",
            "canonical field-path array",
            "每個選項都有 `answer` 與 `tradeoff`",
            "不能由 repo、素材、ASR、牆面或既有 verdict 直接查得",
            "不得在 `remaining_unknowns` 被重新打開",
            "hard constraints、可替換文字與 worker discretion 明確分開",
        ]:
            self.assertIn(expected, text)
        self.assertIn("不得建立新的 router、gate", text)
        self.assertIn("Stage 5/6", text)


if __name__ == "__main__":
    unittest.main()
