from pathlib import Path
import shutil
import tempfile
import unittest

from tools.canonical_route_acceptance import run_check


ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


class CanonicalRouteDocsTest(unittest.TestCase):
    def test_route_doc_declares_stage_order_and_boundaries(self):
        text = read("docs/canonical-video-pipeline-route.md")
        expected = [
            "Video Intent Planner",
            "Story Soul",
            "Director Shot Plan",
            "Material Truth",
            "Coverage / Decision Gate",
            "BUILD Planning",
            "Official Render",
            "Verify",
            "Workbench Draft Review",
            "Brownfield Edit / Finishing",
            "Delivery",
        ]
        positions = [text.index(f"| {stage} |") for stage in expected]
        self.assertEqual(positions, sorted(positions))
        for boundary in [
            "Generated assets are material candidates, not truth",
            "Workbench is draft authority only",
            "Effects are neutral until backend route is chosen",
            "Templates extend the route, not the route itself",
            "Do not mass-rename code yet",
        ]:
            self.assertIn(boundary, text)

    def test_operator_skill_points_to_route_and_tools(self):
        text = read("skills/video-pipeline-route.md")
        for expected in [
            "docs/canonical-video-pipeline-route.md",
            "input state",
            "entry_path",
            "material-first",
            "structure-first",
            "existing material",
            "generated material",
            "hybrid is not a primary Stage 0 entry path",
            "generation is fallback",
            "teaching",
            "personal video",
            "draft review / brownfield edit",
            "generated-image-provider-packet",
            "generated-material-import",
            "generated-material-review",
            "material-delta",
            "contract-run",
            "storyboard_panel_locked=true",
            "Resume Existing Run",
            "Minimal CLI Skeletons",
            "workbench_contract_patch.json",
        ]:
            self.assertIn(expected, text)

    def test_roadmap_and_index_link_canonical_route(self):
        for rel in ["roadmap.md", "docs/INDEX.md"]:
            self.assertIn("docs/canonical-video-pipeline-route.md", read(rel))

    def test_entry_docs_link_end_to_end_line(self):
        for rel in ["docs/START_HERE_VIDEO_PIPELINE.md", "docs/INDEX.md", "roadmap.md"]:
            self.assertIn("docs/video-pipeline-end-to-end-line.md", read(rel))

    def test_stage_zero_artifact_ownership_is_explicit(self):
        combined = "\n".join(
            read(rel)
            for rel in [
                "docs/START_HERE_VIDEO_PIPELINE.md",
                "docs/canonical-video-pipeline-route.md",
                "docs/video-pipeline-operating-map.md",
                "skills/video-pipeline-route.md",
            ]
        )
        for expected in [
            "project_brief.json",
            "brief.json",
            "video_intent.json",
            "route_decision.json",
            "canonical Stage 0",
            "input_state",
            "entry_path",
            "material-first",
            "structure-first",
            "hybrid is not a primary Stage 0 entry path",
            "legacy/compat",
            "video-intent-acceptance",
        ]:
            self.assertIn(expected, combined)

    def test_end_to_end_line_strings_whole_pipeline(self):
        text = read("docs/video-pipeline-end-to-end-line.md")
        expected = [
            "Video Intent Planner",
            "Story / Structure Planner",
            "Director Shot Plan",
            "Material Truth",
            "Coverage / Decision Gate",
            "BUILD Planning",
            "Official Render",
            "Verify / Reviewer Layer",
            "Workbench Draft Review",
            "Brownfield Edit / Finishing",
            "Delivery",
        ]
        positions = [text.index(stage) for stage in expected]
        self.assertEqual(positions, sorted(positions))
        for expected_term in [
            "material-first",
            "structure-first",
            "needs-context",
            "hybrid is not a primary Stage 0 entry path",
            "generated-image-provider-packet",
            "explicit provider output mapping",
            "Workbench is a review and draft-edit surface",
            "Do not render from stale material_delta",
        ]:
            self.assertIn(expected_term, text)


class CanonicalRouteAcceptanceHarnessTest(unittest.TestCase):
    def test_acceptance_harness_passes_repo(self):
        result = run_check(ROOT)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["summary"]["stage_count"], 11)
        self.assertGreaterEqual(result["summary"]["tool_count"], 10)
        self.assertGreaterEqual(result["summary"]["artifact_count"], 20)

    def test_acceptance_harness_fails_when_route_doc_missing(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            for rel in [
                "docs/START_HERE_VIDEO_PIPELINE.md",
                "docs/canonical-video-pipeline-route.md",
                "docs/video-pipeline-operating-map.md",
                "docs/artifact-reviewer-map.md",
                "skills/video-pipeline-route.md",
                "skills/story-soul-blueprint.md",
                "skills/material-map.md",
                "skills/material-generation-fallback.md",
                "skills/generated-material-producer.md",
                "skills/brownfield-edit.md",
                "skills/verify.md",
                "roadmap.md",
                "docs/INDEX.md",
                "video_tools.py",
            ]:
                src = ROOT / rel
                dst = tmp / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dst)
            (tmp / "docs/canonical-video-pipeline-route.md").unlink()
            result = run_check(tmp)
            self.assertFalse(result["ok"])
            self.assertIn("missing required file", result["errors"][0])

    def test_acceptance_harness_fails_when_start_here_missing(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            for rel in [
                "docs/START_HERE_VIDEO_PIPELINE.md",
                "docs/canonical-video-pipeline-route.md",
                "docs/video-pipeline-operating-map.md",
                "docs/artifact-reviewer-map.md",
                "skills/video-pipeline-route.md",
                "skills/story-soul-blueprint.md",
                "skills/material-map.md",
                "skills/material-generation-fallback.md",
                "skills/generated-material-producer.md",
                "skills/brownfield-edit.md",
                "skills/verify.md",
                "roadmap.md",
                "docs/INDEX.md",
                "video_tools.py",
            ]:
                src = ROOT / rel
                dst = tmp / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dst)
            (tmp / "docs/START_HERE_VIDEO_PIPELINE.md").unlink()
            result = run_check(tmp)
            self.assertFalse(result["ok"])
            self.assertTrue(
                any("docs\\START_HERE_VIDEO_PIPELINE.md" in e or "docs/START_HERE_VIDEO_PIPELINE.md" in e
                    for e in result["errors"]),
                result,
            )


if __name__ == "__main__":
    unittest.main()
