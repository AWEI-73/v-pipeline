from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


class UpstreamRouteAlignmentDocsTest(unittest.TestCase):
    def test_canonical_intake_declares_material_availability_split(self):
        for rel in [
            "docs/START_HERE_VIDEO_PIPELINE.md",
            "docs/canonical-video-pipeline-route.md",
            "docs/video-pipeline-operating-map.md",
            "skills/video-pipeline-route.md",
            "skills/video-workflow.md",
        ]:
            text = read(rel)
            for expected in [
                "material availability",
                "existing-material-first",
                "story-first",
                "hybrid",
                "generation is fallback",
                "teaching",
                "personal video",
            ]:
                self.assertIn(expected, text, rel)

    def test_video_intent_planner_is_canonical_stage_zero_name(self):
        for rel in [
            "docs/START_HERE_VIDEO_PIPELINE.md",
            "docs/canonical-video-pipeline-route.md",
            "docs/video-pipeline-operating-map.md",
            "skills/video-pipeline-route.md",
            "roadmap.md",
        ]:
            text = read(rel)
            self.assertIn("Video Intent Planner", text, rel)

        canonical = read("docs/canonical-video-pipeline-route.md")
        self.assertIn("| 0 | Video Intent Planner", canonical)
        self.assertIn("script-first` is a legacy alias for `story-first`", canonical)
        self.assertIn("material-first` is a legacy alias for `existing-material-first`", canonical)

    def test_existing_material_storybook_route_requires_early_map_not_auto_generation(self):
        start = read("docs/START_HERE_VIDEO_PIPELINE.md")
        for expected in [
            "Material Map quick inventory",
            "story/design skeleton constrained by the map",
            "Do not route to generated storybook only because the style is comic",
        ]:
            self.assertIn(expected, start)

    def test_generated_route_names_initial_map_and_delta_before_provider(self):
        route_skill = read("skills/video-pipeline-route.md")
        for expected in [
            "initial project_material_map.json",
            "initial material_delta.json",
            "ready_for_build=false",
            "provider output mapping is required",
        ]:
            self.assertIn(expected, route_skill)

        producer = read("skills/generated-material-producer.md")
        for expected in [
            "Prefer explicit provider output mapping",
            "newest session fallback is allowed only for local smoke",
            "not for formal route acceptance",
        ]:
            self.assertIn(expected, producer)

        roadmap = read("roadmap.md")
        for expected in [
            "formal route acceptance requires explicit provider output mapping",
            "newest `~/.codex/generated_images` session is allowed only",
            "not for formal route acceptance",
            "final generated-material",
        ]:
            self.assertIn(expected, roadmap)

    def test_material_map_and_generated_skills_define_route_boundaries(self):
        material_map = read("skills/material-map.md")
        for expected in [
            "existing-material-first",
            "story-first",
            "hybrid",
            "story source and constraint",
            "validation and handoff layer",
        ]:
            self.assertIn(expected, material_map)

        generated = read("skills/generated-material-producer.md")
        for expected in [
            "generation is fallback",
            "existing-material-first",
            "teaching",
            "personal video",
            "storybook",
        ]:
            self.assertIn(expected, generated)

    def test_upstream_route_doc_declares_full_story_to_contract_line(self):
        text = read("docs/upstream-story-route.md")
        for expected in [
            "Role / Literary Lens",
            "Blueprint Interview",
            "Story Soul Package",
            "Director Shot Plan",
            "Contract Compile",
            "Material-Ready Handoff",
            "blueprint.md",
            "blueprint.json",
            "story_soul_blueprint.json",
            "director_shot_plan.json",
            "segment_contract.json",
            "material_needs.json",
            "generation_manifest.json",
            "generated material review rubric",
            "initial missing material_delta",
            "3-5 minute children's comic/storybook",
        ]:
            self.assertIn(expected, text)

    def test_start_here_and_operating_map_point_to_upstream_route(self):
        for rel in [
            "docs/START_HERE_VIDEO_PIPELINE.md",
            "docs/video-pipeline-operating-map.md",
            "docs/INDEX.md",
            "roadmap.md",
        ]:
            self.assertIn("docs/upstream-story-route.md", read(rel), rel)

    def test_video_pipeline_route_skill_names_upstream_route(self):
        text = read("skills/video-pipeline-route.md")
        for expected in [
            "docs/upstream-story-route.md",
            "Role / Literary Lens",
            "Blueprint Interview",
            "Story Soul Package",
            "Director Shot Plan",
            "Contract Compile",
            "Material-Ready Handoff",
            "initial material_delta",
            "review_policy.level=deep",
            "Chinese subtitle requirements",
        ]:
            self.assertIn(expected, text)


if __name__ == "__main__":
    unittest.main()
