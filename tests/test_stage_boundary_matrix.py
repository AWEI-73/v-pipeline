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


if __name__ == "__main__":
    unittest.main()
