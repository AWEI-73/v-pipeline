import json
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core.skill_tool_contract import (
    iter_tool_entries,
    load_contracts,
    normalize_tool_ref,
    parse_json_marker_blocks,
    suggest_capability_id,
    validate_contract_schema,
)


def _contract(skill, *, capability_id="cap.fixture.tool.v1", source="tools/example.py"):
    return {
        "version": 1,
        "skill": skill,
        "stage_owner": "fixture_stage",
        "capability_namespace": "cap.fixture.*",
        "capability_lookup_owner": "fixture-owner",
        "triggers": ["fixture"],
        "forbidden_tools": [],
        "canonical_tools": [{
            "capability_id": capability_id,
            "tool": source,
            "loops": ["L3"],
            "maturity": "bounded",
            "certified_scope": "fixture scope",
            "when": "run fixture",
            "inputs": ["in.json"],
            "outputs": ["out.json"],
            "stop_if": ["bad"],
        }],
        "supporting_tools": [{
            "tool": "tools/support.py",
            "when": "support fixture",
            "inputs": [],
            "outputs": [],
            "stop_if": [],
        }],
        "internal_tools": [{
            "tool": "tools/internal.py",
            "when": "internal fixture",
            "inputs": [],
            "outputs": [],
            "stop_if": [],
        }],
        "diagnostic_tools": [{
            "tool": "tools/diagnostic.py",
            "when": "diagnose fixture",
            "inputs": [],
            "outputs": [],
            "stop_if": [],
        }],
    }


class SkillToolContractParserTest(unittest.TestCase):
    def test_consumers_delegate_marker_loading_to_shared_parser(self):
        root = Path(__file__).resolve().parents[1]
        for name in ("skill_tool_contract_audit.py", "pipeline_interface_discovery.py"):
            text = (root / "tools" / name).read_text(encoding="utf-8")
            self.assertIn("from video_pipeline_core.skill_tool_contract", text)
            self.assertNotIn("TOOL_CONTRACT_START -->", text)
            self.assertNotIn("contract_json =", text)

    def test_parse_marker_blocks_stamps_source_and_reports_malformed_json(self):
        text = """前言 中文\n<!-- TOOL_CONTRACT_START -->\n{"skill":"ok"}\n<!-- TOOL_CONTRACT_END -->\n<!-- TOOL_CONTRACT_START -->\n{bad\n<!-- TOOL_CONTRACT_END -->\n"""
        blocks, errors = parse_json_marker_blocks(
            Path("fixture.md"), text, start="TOOL_CONTRACT_START", end="TOOL_CONTRACT_END"
        )
        self.assertEqual(["ok"], [item["skill"] for item in blocks])
        self.assertEqual("fixture.md", blocks[0]["_source"])
        self.assertEqual(1, len(errors))

    def test_load_contracts_is_sorted_and_preserves_duplicate_blocks_for_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = json.dumps(_contract("zeta"), ensure_ascii=False)
            marker = f"<!-- TOOL_CONTRACT_START -->\n{payload}\n<!-- TOOL_CONTRACT_END -->\n"
            (root / "z.md").write_text(marker, encoding="utf-8")
            (root / "a.md").write_text(marker + marker, encoding="utf-8")
            contracts, errors = load_contracts(root)
            self.assertEqual([], errors)
            self.assertEqual(["a.md", "a.md", "z.md"], [Path(x["_source"]).name for x in contracts])

    def test_iter_entries_copies_sections_and_owner_metadata(self):
        contract = _contract("fixture")
        contract["_source"] = "skills/fixture.md"
        entries = iter_tool_entries(contract)
        self.assertEqual(["canonical_tools", "supporting_tools", "internal_tools", "diagnostic_tools"], [x["_section"] for x in entries])
        self.assertEqual({"fixture", "fixture_stage", "skills/fixture.md"}, {entries[0][key] for key in ("_skill", "_stage_owner", "_source")})
        entries[0]["tool"] = "changed"
        self.assertEqual("tools/example.py", contract["canonical_tools"][0]["tool"])

    def test_normalize_tool_ref_and_capability_proposal_are_deterministic(self):
        self.assertEqual("tools/example.py", normalize_tool_ref("python .\\tools\\example.py"))
        self.assertEqual("cap.audio-director.audio-mix-plan-execute.v1", suggest_capability_id("audio-director", "tools/audio_mix_plan_execute.py"))

    def test_schema_errors_are_structured_and_sorted(self):
        bad = _contract("fixture", capability_id="bad")
        bad["canonical_tools"][0].pop("loops")
        bad["canonical_tools"][0]["maturity"] = "unknown"
        errors = validate_contract_schema([bad])
        self.assertEqual(["invalid_capability_id", "invalid_maturity", "missing_loops"], [e["code"] for e in errors])
        self.assertTrue(all(set(e) == {"code", "source", "skill", "capability_id", "tool", "message"} for e in errors))


if __name__ == "__main__":
    unittest.main()
