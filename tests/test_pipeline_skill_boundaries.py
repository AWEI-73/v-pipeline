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

    def test_fresh_agent_entry_authority_and_bounded_routes_are_unambiguous(self):
        claude = read("CLAUDE.md")
        start_here = read("docs/START_HERE_VIDEO_PIPELINE.md")
        skill_index = read("skills/INDEX.md")
        runtime_driver = read("skills/video-pipeline.md")
        route = read("skills/video-pipeline-route.md")
        runbook = read("RUNBOOK.md")

        for text in [claude, start_here, skill_index, runtime_driver]:
            self.assertIn("skills/video-pipeline-route.md", text)

        for expected in ["RUNBOOK.md", "HANDOFF_CURRENT.md"]:
            self.assertIn(expected, claude)
        self.assertNotIn("then enter through\n`skills/video-pipeline.md`", claude)

        self.assertNotIn(
            "Every video production request enters through `skills/video-pipeline.md`",
            start_here,
        )
        self.assertIn("compatibility runtime driver", runtime_driver)
        self.assertIn("not the operator entry", runtime_driver)
        self.assertNotIn("唯一入口", runtime_driver)
        self.assertIn("compatibility runtime driver", skill_index)

        for expected in [
            "Stage 0 -> Material-first",
            "entry_path=material-first",
            "review this video",
            "Editorial Reviewer",
        ]:
            self.assertIn(expected, route)

        for pattern in [
            r"Existing candidate/draft repair enters\s+Workbench / Brownfield first",
            r"`runtime\.py rerun` is reserved for an active\s+canonical run",
        ]:
            self.assertRegex(route, re.compile(pattern))

        self.assertRegex(
            runbook,
            re.compile(
                r"Existing candidate/draft subtitle or volume\s+repair enters "
                r"Workbench/Brownfield first"
            ),
        )

    def test_compatibility_docs_do_not_compete_with_current_operator_routes(self):
        runbook = read("RUNBOOK.md")
        docs_index = read("docs/INDEX.md")
        system_design = read("docs/SYSTEM-DESIGN.md")
        material_replay = read("docs/runbooks/material-first-happy-path.md")
        boundary = read("skills/pipeline-boundary.md")
        audio = read("skills/audio-director.md")

        for text in [runbook, material_replay]:
            self.assertIn("validation-only golden fixture", text)
            self.assertIn("not a user-job entry", text)
        self.assertNotIn("## Official Replay Command", material_replay)

        for expected in [
            "Existing candidate/draft bounded patch",
            "locked and dirty layers",
        ]:
            self.assertIn(expected, boundary)
        self.assertRegex(
            boundary,
            re.compile(r"does\s+not require a new Stage 0 package"),
        )

        for expected in [
            "Compatibility command: mix-audio (legacy)",
            "tools/audio_mix_plan_execute.py",
            "Do not split and concatenate media",
        ]:
            self.assertIn(expected, audio)
        self.assertRegex(
            audio,
            re.compile(r"not the canonical\s+speech-aware repair route"),
        )

        self.assertNotIn("canonical operator entrypoint", docs_index)
        self.assertIn("optional concept orientation", docs_index)
        self.assertIn("video-pipeline-route", system_design)
        self.assertIn("compatibility runtime driver", system_design)
        self.assertNotIn("唯一強制入口", system_design)
        self.assertNotRegex(system_design, re.compile(r"runtime\.py.*唯一入口"))

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

    def test_stage_spine_and_editing_loops_have_distinct_authority(self):
        runbook = read("RUNBOOK.md")
        skill = read("skills/editing-loop-director.md")
        spec = read("docs/construction-guides/2026-07-10-editing-loop-product-spec.md")

        for text in (runbook, skill, spec):
            self.assertIn("Stage owns lifecycle", text)
            self.assertIn("Loop owns editing method", text)
            self.assertIn("Stage 6", text)
            self.assertIn("canonical render", text)

        for expected in [
            "S3 → L0",
            "S5 → L1 / L2 / L3 / L4",
            "S7 / S8 → L5",
            "S9 → finding-targeted L0–L4",
            "COMPILED / NOT_RENDERED",
            "L1 does not own canonical render",
        ]:
            self.assertIn(expected, skill)

    def test_longform_greenfield_requires_story_and_director_contract_before_l1(self):
        skill = read("skills/editing-loop-director.md")
        for expected in [
            "greenfield whole-video or long-form",
            "video_intent.json",
            "story_soul_blueprint.json",
            "director_shot_plan.json",
            "segment_contract.json",
            "material-first L0 exception",
            "must return to S1 / S2 before L1",
            "brownfield entry",
        ]:
            self.assertIn(expected, skill)

    def test_editing_loop_consumer_declares_every_domain_it_routes(self):
        consumers, parse_errors = load_capability_consumers(ROOT / "skills")
        self.assertEqual([], parse_errors)
        consumer = next(item for item in consumers if item["consumer"] == "editing-loop-director")
        for namespace in [
            "cap.audio-director.*",
            "cap.brownfield-edit.*",
            "cap.generated-material-producer.*",
            "cap.material-map.*",
            "cap.soundtrack-arranger.*",
            "cap.subtitle-director.*",
            "cap.video-effect-factory.*",
            "cap.verify.*",
        ]:
            self.assertIn(namespace, consumer["active_namespaces"])

    def test_authority_surfaces_publish_exact_entry_markers(self):
        expected_markers = {
            "AGENTS.md": ["<!-- OPERATIONAL_ENTRY_POINTER: RUNBOOK.md -->"],
            "RUNBOOK.md": [
                "<!-- OPERATIONAL_ENTRY: RUNBOOK -->",
                "<!-- CURRENT_HANDOFF_POINTER: HANDOFF_CURRENT.md -->",
            ],
            "HANDOFF_CURRENT.md": ["<!-- DOCUMENT_ROLE: CURRENT_HANDOFF -->"],
        }

        for rel, markers in expected_markers.items():
            text = read(rel)
            for marker in markers:
                self.assertIn(marker, text, rel)

    def test_runbook_is_the_only_operational_entry_surface(self):
        runbook = read("RUNBOOK.md")
        self.assertEqual(1, runbook.count("<!-- OPERATIONAL_ENTRY: RUNBOOK -->"))

        for rel in [
            "AGENTS.md",
            "HANDOFF_CURRENT.md",
            "docs/START_HERE_VIDEO_PIPELINE.md",
            "docs/INDEX.md",
        ]:
            self.assertNotIn("<!-- OPERATIONAL_ENTRY: RUNBOOK -->", read(rel), rel)

    def test_runbook_stays_free_of_active_state_machine_keys_and_tokens(self):
        runbook = read("RUNBOOK.md")
        self.assertNotIn("active_work_order", runbook)
        self.assertNotIn("authoritative_state_artifact", runbook)
        self.assertNotIn("ACTIVE_WORK_ORDER", runbook)
        self.assertNotRegex(
            runbook,
            re.compile(r"\b(?:WAITING|STOPPED|ACTIVE)(?:_[A-Z0-9]+)+\b"),
        )

    def test_bounded_agent_freedom_stays_inside_existing_route_contract(self):
        expected = [
            "Fuzzy/new whole-video work still enters Stage 0 and canonical BUILD.",
            "existing\nreviewed candidate with explicit locked and dirty layers",
            "orchestrating agent may select existing\nregistered capabilities",
            "Only dirty layers rerun",
            "returns to Verify and Owner verdict",
            "No direct whole-video hand\nstitching, protected-truth mutation, or delivery promotion is allowed.",
        ]

        for rel in ["RUNBOOK.md", "skills/video-pipeline.md"]:
            text = read(rel)
            for marker in expected:
                self.assertIn(marker, text, rel)


if __name__ == "__main__":
    unittest.main()
