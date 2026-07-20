import tempfile
import unittest
from pathlib import Path

from tools import pipeline_map


class PipelineMapTest(unittest.TestCase):
    def test_active_map_references_existing_files(self):
        data = pipeline_map.build_map()
        refs = set(data["active_docs"] + data["active_skills"] + data["core_tools"])
        for tools in data.get("support_tools", {}).values():
            refs.update(tools)
        for stage in data["stages"]:
            refs.update(stage.get("docs", []))
            refs.update(stage.get("skills", []))
            for tool in stage.get("tools", []):
                refs.add(tool.split(":", 1)[0].split(" ", 1)[0])
        for branch in data["branches"]:
            refs.update(branch.get("docs", []))
            refs.update(branch.get("skills", []))

        missing = sorted(ref for ref in refs if not (pipeline_map.ROOT / ref).is_file())
        self.assertEqual([], missing)

    def test_build_corpus_copies_active_docs_skills_and_tools(self):
        data = pipeline_map.build_map()
        self.assertLessEqual(len(data["active_docs"]), 9)
        self.assertNotIn("roadmap.md", data["active_docs"])
        self.assertIn("HANDOFF_CURRENT.md", data["active_docs"])
        with tempfile.TemporaryDirectory() as tmp:
            corpus = pipeline_map.build_corpus(data, Path(tmp) / "mvp")

            self.assertTrue((corpus / "RUNBOOK.md").is_file())
            self.assertTrue((corpus / "HANDOFF_CURRENT.md").is_file())
            self.assertFalse((corpus / "roadmap.md").exists())
            self.assertFalse((corpus / "docs" / "video-pipeline-operating-map.md").exists())
            self.assertFalse((corpus / "docs" / "pipeline-decision-tree.md").exists())
            self.assertTrue((corpus / "skills" / "video-effect-factory.md").is_file())
            self.assertTrue((corpus / "skills" / "shooting-brief.md").is_file())
            self.assertFalse((corpus / "dashboard" / "workbench_native" / "API_CONTRACT.md").exists())
            self.assertTrue((pipeline_map.ROOT / "dashboard" / "workbench_native" / "API_CONTRACT.md").is_file())
            self.assertTrue((corpus / "tools" / "workbench_frontend_smoke.py").is_file())
            self.assertTrue((corpus / "tools" / "test_tiers.py").is_file())
            self.assertTrue((corpus / "tools" / "workbench_handoff.py").is_file())
            self.assertTrue((corpus / "tools" / "canonical_route_acceptance.py").is_file())

    def test_workbench_stage_exposes_frontend_migration_guards(self):
        data = pipeline_map.build_map()
        workbench = next(stage for stage in data["stages"] if stage["id"] == "stage8")
        tools = " ".join(workbench["tools"])

        self.assertIn("tools/test_tiers.py --tier workbench", tools)
        self.assertIn("tools/workbench_frontend_smoke.py", tools)
        self.assertIn("tools/workbench_browser_layout_smoke.mjs", tools)

    def test_markdown_stage_table_exposes_stage_tools(self):
        data = pipeline_map.build_map()
        with tempfile.TemporaryDirectory() as tmp:
            path = pipeline_map.write_markdown(data, Path(tmp))
            text = path.read_text(encoding="utf-8")

        self.assertIn("| Stage | Skills | Tools | Artifacts | Gate |", text)
        self.assertIn("tools/test_tiers.py --tier workbench", text)
        self.assertIn("tools/workbench_frontend_smoke.py", text)

    def test_stage0_10_map_exposes_current_branches_and_handoffs(self):
        data = pipeline_map.build_map()
        stage_ids = {stage["id"] for stage in data["stages"]}
        branch_ids = {branch["id"] for branch in data["branches"]}
        stage5 = next(stage for stage in data["stages"] if stage["id"] == "stage5")
        stage9 = next(stage for stage in data["stages"] if stage["id"] == "stage9")
        stage10 = next(stage for stage in data["stages"] if stage["id"] == "stage10")

        self.assertIn("stage10", stage_ids)
        self.assertEqual(stage9["name"], "Brownfield / Finishing")
        self.assertEqual(stage10["name"], "Delivery")
        self.assertIn("soundtrack-arranger", branch_ids)
        self.assertIn("subtitle-voiceover", branch_ids)
        self.assertIn("rough_cut_plan.json", stage5["artifacts"])
        self.assertIn("audio_build_handoff.json", stage5["artifacts"])
        self.assertIn("effect_handoff.json", stage5["artifacts"])
        self.assertIn("subtitles.srt", stage5["artifacts"])
        self.assertNotIn("docs/construction-guides/stage0-10-route-alignment-plan.md", data["active_docs"])


if __name__ == "__main__":
    unittest.main()
