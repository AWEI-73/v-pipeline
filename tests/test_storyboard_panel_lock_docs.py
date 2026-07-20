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

    def test_archived_decision_records_auto_fill_vs_panel_locked_boundary(self):
        text = (ROOT / "docs" / "archive" / "decisions" / "2026-06-19-storyboard-panel-lock.md").read_text(encoding="utf-8")
        self.assertIn("Storyboard Panel-Lock", text)
        self.assertIn("one panel per story beat", text)
        self.assertIn("auto-fill accepted shots is allowed", text)


if __name__ == "__main__":
    unittest.main()
