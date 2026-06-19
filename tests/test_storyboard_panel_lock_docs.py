import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class StoryboardPanelLockDocsTest(unittest.TestCase):
    def test_generated_material_skill_documents_panel_lock_boundary(self):
        text = (ROOT / "skills" / "generated-material-producer.md").read_text(encoding="utf-8")
        self.assertIn("storyboard_panel_locked=true", text)
        self.assertIn("do not auto-fill", text)
        self.assertIn("extend the panel", text)

    def test_story_soul_doc_propagates_panel_lock_to_upstream_planning(self):
        text = (ROOT / "docs" / "story-soul-blueprint-skills.md").read_text(encoding="utf-8")
        self.assertIn("Panel-lock rule", text)
        self.assertIn("storyboard_panel_locked=true", text)
        self.assertIn("generate/request more panels", text)

    def test_roadmap_records_auto_fill_vs_panel_locked_decision(self):
        text = (ROOT / "roadmap.md").read_text(encoding="utf-8")
        self.assertIn("GMP2.6 Storyboard Panel-Locked Rendering Boundary", text)
        self.assertIn("Normal auto-fill remains correct", text)
        self.assertIn("one generated panel owns one narration/story beat", text)


if __name__ == "__main__":
    unittest.main()
