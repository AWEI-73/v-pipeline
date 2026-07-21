import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "distribution" / "agent-skill" / "video-pipeline"


class AgentOnlySkillBundleTests(unittest.TestCase):
    def test_bundle_contains_only_installable_skill_surfaces(self):
        paths = sorted(path.relative_to(SKILL_ROOT).as_posix() for path in SKILL_ROOT.rglob("*"))
        self.assertEqual(paths, ["SKILL.md", "agents", "agents/openai.yaml"])

    def test_skill_is_thin_and_routes_without_runtime_copies(self):
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertLess(len(skill.splitlines()), 250)
        self.assertIn("name: video-pipeline", skill)
        self.assertIn("producing, editing, reviewing, or repairing video", skill)
        for marker in [
            "current directory first",
            "VIDEO_PIPELINE_HOME",
            "fail closed",
            "read `RUNBOOK.md` as the only first read",
            "HANDOFF_CURRENT.md` second",
            "repo-local skill or tool on demand",
            "Fuzzy/new whole-video work still enters Stage 0 and canonical BUILD.",
            "Only dirty layers rerun",
            "returns to Verify and Owner verdict",
            "No direct whole-video hand",
        ]:
            self.assertIn(marker, skill)

        self.assertNotRegex(skill, re.compile(r"(?i)C:\\\\Users\\\\|/Users/|/home/"))
        for forbidden in [
            "distribution/agent-skill/video-pipeline/video_pipeline_core",
            "distribution/agent-skill/video-pipeline/tools/",
            "route registry copy",
            "project state copy",
        ]:
            self.assertNotIn(forbidden, skill)

    def test_openai_metadata_is_present_and_points_to_this_skill(self):
        metadata = (SKILL_ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertIn('display_name: "Video Pipeline Runtime"', metadata)
        self.assertIn('$video-pipeline', metadata)
        self.assertNotIn("C:\\Users\\user", metadata)


if __name__ == "__main__":
    unittest.main()
