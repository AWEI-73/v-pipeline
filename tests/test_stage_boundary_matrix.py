from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class StageBoundaryMatrixTest(unittest.TestCase):
    def test_three_route_lines_have_reviewable_boundaries(self):
        text = (ROOT / "docs" / "stage-boundary-matrix.md").read_text(encoding="utf-8")
        for expected in [
            "Main Pipeline",
            "Material Map Branch",
            "Effect Factory Branch",
            "Soundtrack / Audio Branch",
            "Subtitle / Voiceover Branch",
            "allowed outputs",
            "forbidden writes",
            "done gate",
            "stop gate",
            "next handoff",
            "worker mode",
            "maintainer mode",
        ]:
            self.assertIn(expected, text)

    def test_runner_protocol_points_to_stage_boundary_matrix(self):
        text = (ROOT / "docs" / "route-agent-runner-protocol.md").read_text(encoding="utf-8")
        for expected in [
            "docs/stage-boundary-matrix.md",
            "worker mode",
            "maintainer mode",
            "forbidden writes",
        ]:
            self.assertIn(expected, text)

    def test_start_here_points_to_stage_boundary_matrix(self):
        text = (ROOT / "docs" / "START_HERE_VIDEO_PIPELINE.md").read_text(encoding="utf-8")
        self.assertIn("docs/stage-boundary-matrix.md", text)
        self.assertIn("Main Pipeline", text)
        self.assertIn("Material Map branch", text)
        self.assertIn("Effect Factory branch", text)
        self.assertIn("Soundtrack Arranger branch", text)

    def test_decision_tree_covers_main_and_side_branches(self):
        decision_tree = "docs/pipeline-decision-tree.md"
        text = (ROOT / decision_tree).read_text(encoding="utf-8")
        for expected in [
            "Main Pipeline Decision Tree",
            "Stage 0 Decision Order",
            "Branch Insertion Points",
            "Structure-First Decision Path",
            "BUILD Decision Section",
            "Workbench Natural Entry Points",
            "Material Map Branch Decision Tree",
            "Effect Factory Branch Decision Tree",
            "Audio Communication Branch Decision Tree",
            "Workbench / Brownfield Branch Decision Tree",
            "Review / Verify / Delivery Gate Cross-Cutting Decision Tree",
            "input_state",
            "material_scan_decision",
            "soundtrack_contract",
            "subtitle_voiceover_contract",
            "effect_policy",
            "Loop Break Conditions",
            "All BUILD prerequisites are AND conditions",
            "Deferred child contracts count as satisfied only when",
            "Needs-Context Exit Rule",
            "bounded effect means",
            "draft-only",
            "audio and effect branches are child lanes",
            "BUILD details live in",
            "rough cut, draft preview, failed verify, or user patch request",
            "fail closed",
            "forbidden actions",
            "handoff artifacts",
            "return route",
        ]:
            self.assertIn(expected, text)

        for rel in [
            "RUNBOOK.md",
            "docs/START_HERE_VIDEO_PIPELINE.md",
            "skills/video-pipeline-route.md",
            "docs/INDEX.md",
        ]:
            linked = (ROOT / rel).read_text(encoding="utf-8")
            self.assertIn(decision_tree, linked, rel)

    def test_stage_zero_to_ten_alignment_plan_is_linked(self):
        plan = "docs/construction-guides/stage0-10-route-alignment-plan.md"
        for rel in [
            "docs/START_HERE_VIDEO_PIPELINE.md",
            "docs/INDEX.md",
            "RUNBOOK.md",
            "docs/canonical-video-pipeline-route.md",
        ]:
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertIn(plan, text, rel)

    def test_canonical_route_names_child_contract_branches(self):
        text = (ROOT / "docs" / "canonical-video-pipeline-route.md").read_text(encoding="utf-8")
        for expected in [
            "child contracts",
            "material_contract",
            "material_scan_decision",
            "soundtrack_contract",
            "effect_policy",
            "subtitle_voiceover_contract",
            "Soundtrack Arranger branch",
            "Audio Director",
        ]:
            self.assertIn(expected, text)

    def test_route_skills_name_all_stage_zero_child_contracts(self):
        combined = "\n".join(
            (ROOT / rel).read_text(encoding="utf-8")
            for rel in [
                "skills/video-pipeline-route.md",
                "skills/video-intent-planner.md",
            ]
        )
        for expected in [
            "material_contract",
            "soundtrack_contract",
            "effect_policy",
            "subtitle_voiceover_contract",
            "stage0_subtitle_voiceover_intent",
        ]:
            self.assertIn(expected, combined)

    def test_video_intent_planner_names_second_turn_canonical_objects(self):
        text = (ROOT / "skills" / "video-intent-planner.md").read_text(encoding="utf-8")
        for expected in [
            "Second-Turn Canonical Output Rule",
            '"material_scan_decision": {',
            '"default_scope": "all_materials"',
            '"soundtrack_contract": {',
            '"subtitle_voiceover_contract": {',
            'Do not write `"material_scan_decision": "scan_all_materials"`',
            'Do not write `"soundtrack_contract": "defer"`',
            "Exact key names are part of the contract",
            "Do not rename `scan_depth` to `mode`",
            "Do not rename `first_action` value `material_map_quick_inventory` to `material_quick_inventory`",
        ]:
            self.assertIn(expected, text)


if __name__ == "__main__":
    unittest.main()
