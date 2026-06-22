from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


class MaterialMapRelationDocsTest(unittest.TestCase):
    def test_lifecycle_doc_declares_isf1_relationships(self):
        text = read("docs/material-map-lifecycle.md")
        for expected in [
            "ISF1 Relationship",
            "story-soul-blueprint",
            "generated-material-producer",
            "storyboard_panel_locked",
            "Workbench",
            "draft",
            "candidate",
            "official BUILD handoff",
        ]:
            self.assertIn(expected, text)

    def test_skill_declares_material_map_handoff_boundaries(self):
        text = read("skills/material-map.md")
        for expected in [
            "ISF1 Material-Map Handoff",
            "story-soul-blueprint",
            "generated-material-producer",
            "candidate satisfies",
            "storyboard_panel_locked",
            "Workbench",
            "must not overwrite canonical",
        ]:
            self.assertIn(expected, text)

    def test_decision_log_records_material_map_relation_review(self):
        text = read("docs/archive/decisions/2026-06-19-material-map-relation-review.md")
        for expected in [
            "Material-map relation review",
            "No new runtime layer",
            "Generated assets return as candidates",
            "Workbench drafts are not material truth",
        ]:
            self.assertIn(expected, text)


if __name__ == "__main__":
    unittest.main()
