from pathlib import Path
import re
import unittest
from video_pipeline_core.skill_tool_contract import (
    audit_repository_contracts,
    iter_tool_entries,
    load_capability_consumers,
    load_contracts,
)


ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


class PipelineSkillBoundariesTest(unittest.TestCase):
    def test_shared_pipeline_boundary_charter_exists(self):
        text = read("skills/pipeline-boundary.md")
        for expected in [
            "Stage 0 entry lock",
            "Do not direct-cut from a fuzzy request",
            "required_followup_questions",
            "contract-run",
            "final.mp4",
            "handoff_packet",
            "fail closed",
        ]:
            self.assertIn(expected, text)

    def test_start_here_points_to_shared_boundary(self):
        text = read("docs/START_HERE_VIDEO_PIPELINE.md")
        for expected in [
            "skills/pipeline-boundary.md",
            "Stage 0 entry lock",
            "Do not direct-cut from a fuzzy request",
            "video_intent.json.required_followup_questions",
        ]:
            self.assertIn(expected, text)

    def test_pipeline_skills_reference_shared_boundary(self):
        for rel in [
            "skills/video-pipeline-route.md",
            "skills/video-intent-planner.md",
            "skills/video-pipeline.md",
            "skills/video-workflow.md",
            "skills/material-map.md",
            "skills/generated-material-producer.md",
            "skills/brownfield-edit.md",
            "skills/video-effect-factory.md",
            "skills/remotion-effect-worker.md",
            "skills/effects-director.md",
            "skills/soundtrack-arranger.md",
        ]:
            text = read(rel)
            self.assertIn("skills/pipeline-boundary.md", text, rel)
            self.assertIn("Stage 0 entry lock", text, rel)
            self.assertIn("direct-cut", text, rel)
            self.assertRegex(text, re.compile(r"fuzzy\s+request"), rel)

    def test_video_pipeline_route_skill_has_semantic_trigger_router(self):
        text = read("skills/video-pipeline-route.md")
        for expected in [
            "Semantic Trigger Router",
            "help me cut",
            "I have footage",
            "opening / transition / effect",
            "edit this draft",
            "export final video",
            "route_judgment is not a Stage 0 artifact",
            "pipeline_home.py must not remain unknown",
            "material-first owns the route before story structure",
            "story structure must be derived from material-map facts",
            "Material Delta is the next gate, not a forbidden action",
            "RUNBOOK.md",
            "pipeline_home.py",
            "docs/stage-boundary-matrix.md",
        ]:
            self.assertIn(expected, text)

    def test_soundtrack_arranger_branch_is_documented(self):
        skill = read("skills/soundtrack-arranger.md")
        route = read("docs/soundtrack-arranger-route.md")
        runbook = read("RUNBOOK.md")
        start_here = read("docs/START_HERE_VIDEO_PIPELINE.md")
        audio = read("skills/audio-director.md")

        for expected in [
            "soundtrack_plan.json",
            "music_source_candidates.json",
            "sound_license_manifest.json",
            "audio_director_handoff.json",
            "Jamendo",
            "Pixabay",
            "optional API layer",
            "reference_only",
            "HERMES_ALLOW_UNLICENSED_MUSIC=false",
        ]:
            self.assertIn(expected, skill)
            self.assertIn(expected, route)

        for text in [runbook, start_here, audio]:
            self.assertIn("soundtrack-arranger", text)
            self.assertIn("soundtrack_plan.json", text)
            self.assertIn("sound_license_manifest.json", text)

    def test_runbook_has_operator_semantic_entry_router(self):
        text = read("RUNBOOK.md")
        for expected in [
            "Single Operator Entry",
            "Task-to-Document Router",
            "Decision tree",
            "Stage/tool map",
            "Skill/tool ownership",
            "Semantic Entry Router",
            "Entry Precedence",
            "Stage 0 package",
            "target_length",
            "User says",
            "Entry skill",
            "First safe action",
            "Stop condition",
            "Resume existing run",
            "Whole-video requests win over side-branch keywords",
            "Side-branch keywords are child intents",
            "Subtitle or volume repair is not Soundtrack Arranger",
            "music/song/BGM intent",
            "whole-video subtitle intent",
            "subtitle repair",
            "help me cut a video",
            "I already have footage",
            "I need an opening effect",
            "export the final video",
            "route_judgment.json is not enough",
            "pipeline_home.py returns unknown",
            "material-first remains the route",
            "story skeleton follows material facts",
            "Material Delta is a gate",
        ]:
            self.assertIn(expected, text)

    def test_docs_index_declares_runbook_single_entry(self):
        text = read("docs/INDEX.md")
        for expected in [
            "Document Map",
            "Single operator entry",
            "RUNBOOK.md",
            "Concept orientation",
            "Decision tree",
            "Stage/tool map",
            "Skill/tool ownership",
            "Construction guides",
            "Historical archive",
        ]:
            self.assertIn(expected, text)
        self.assertNotIn("Start here (entry points, in order)", text)

    def test_stage_tool_simplification_has_precedence_rules(self):
        text = read("docs/stage-tool-simplification.md")
        for expected in [
            "Entry Precedence",
            "Stage 0 package",
            "target_length",
            "whole-video request",
            "resume existing run",
            "draft patch",
            "soundtrack intent",
            "audio repair",
            "subtitle repair",
            "generated candidate fallback",
        ]:
            self.assertIn(expected, text)

    def test_stage0_minimum_package_is_aligned(self):
        for rel in [
            "RUNBOOK.md",
            "skills/pipeline-boundary.md",
            "skills/video-intent-planner.md",
            "skills/video-pipeline-route.md",
            "docs/stage-tool-simplification.md",
        ]:
            text = read(rel)
            for expected in [
                "Stage 0 package",
                "project_brief.json",
                "interaction_log.md",
                "video_intent.json",
                "target_length",
                "required_followup_questions",
            ]:
                self.assertIn(expected, text, rel)

    def test_stage0_tables_show_full_three_file_package(self):
        runbook = read("RUNBOOK.md")
        route = read("skills/video-pipeline-route.md")
        stage_tools = read("docs/stage-tool-simplification.md")

        for label, text in [
            ("RUNBOOK.md", runbook),
            ("skills/video-pipeline-route.md", route),
            ("docs/stage-tool-simplification.md", stage_tools),
        ]:
            self.assertRegex(
                text,
                re.compile(
                    r"project_brief\.json.*interaction_log\.md.*video_intent\.json"
                    r"|project_brief\.json.*video_intent\.json.*interaction_log\.md",
                    re.DOTALL,
                ),
                label,
            )

    def test_routing_skill_frontmatter_is_readable(self):
        for rel in [
            "skills/material-map.md",
            "skills/dashboard.md",
            "skills/spec-contract.md",
            "skills/verify.md",
            "skills/video-pipeline-route.md",
            "skills/video-intent-planner.md",
            "skills/soundtrack-arranger.md",
            "skills/audio-director.md",
            "skills/subtitle-director.md",
            "skills/video-effect-factory.md",
            "skills/brownfield-edit.md",
        ]:
            text = read(rel)
            self.assertTrue(text.startswith("---\n"), rel)
            frontmatter = text.split("---", 2)[1]
            self.assertNotRegex(frontmatter, re.compile(r"[\ue000-\uf8ff]"), rel)
            self.assertRegex(frontmatter, re.compile(r"^name:\s+[-a-z0-9]+$", re.MULTILINE), rel)
            self.assertRegex(frontmatter, re.compile(r"^description:\s+\S", re.MULTILINE), rel)

    def test_editing_loop_director_is_one_capability_consumer_not_a_tool_owner(self):
        text = read("skills/editing-loop-director.md")
        self.assertEqual(1, text.count("<!-- CAPABILITY_CONSUMER_START -->"))
        self.assertEqual(1, text.count("<!-- CAPABILITY_CONSUMER_END -->"))
        consumers, parse_errors = load_capability_consumers(ROOT / "skills")
        self.assertEqual([], parse_errors)
        self.assertEqual(1, len(consumers))
        consumer = consumers[0]
        self.assertEqual("editing-loop-director", consumer["consumer"])
        self.assertFalse(any(key in consumer for key in ("canonical_tools", "supporting_tools", "internal_tools", "diagnostic_tools")))
        contracts, contract_errors = load_contracts(ROOT / "skills")
        self.assertEqual([], contract_errors)
        python_tools = {
            str(path.relative_to(ROOT)).replace("\\", "/")
            for path in (ROOT / "tools").glob("*.py")
            if path.name != "__init__.py"
        }
        errors = audit_repository_contracts(
            contracts,
            python_tools=python_tools,
            capability_consumers=consumers,
        )
        self.assertEqual([], errors)
        canonical = {
            entry.get("capability_id"): entry
            for contract in contracts
            for entry in iter_tool_entries(contract)
            if entry.get("_section") == "canonical_tools"
        }
        self.assertTrue(consumer["active_capability_ids"])
        self.assertTrue(set(consumer["active_capability_ids"]).issubset(canonical))
        self.assertTrue(all(canonical[item]["maturity"] != "legacy" for item in consumer["active_capability_ids"]))
        self.assertFalse(consumer["human_creative_approval"])
        self.assertFalse(consumer["final_delivery_claimed"])


if __name__ == "__main__":
    unittest.main()
