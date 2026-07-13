import json
import copy
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core.skill_tool_contract import (
    audit_repository_contracts,
    iter_tool_entries,
    load_capability_consumers,
    load_contracts,
    normalize_tool_ref,
    parse_json_marker_blocks,
    suggest_capability_id,
    validate_contract_schema,
)


def _contract(
    skill,
    *,
    capability_id="cap.fixture.tool.v1",
    source="tools/example.py",
    execution_class="deterministic",
    capability_role="operation",
):
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
            "execution_class": execution_class,
            "capability_role": capability_role,
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

    def test_load_capability_consumers_is_sorted_and_preserves_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            marker = "<!-- CAPABILITY_CONSUMER_START -->\n" + json.dumps({
                "consumer": "director",
                "active_capability_ids": ["cap.fixture.tool.v1"],
                "active_namespaces": ["cap.fixture.*"],
            }) + "\n<!-- CAPABILITY_CONSUMER_END -->\n"
            (root / "z.md").write_text(marker, encoding="utf-8")
            (root / "a.md").write_text(marker, encoding="utf-8")
            consumers, errors = load_capability_consumers(root)
            self.assertEqual([], errors)
            self.assertEqual(["a.md", "z.md"], [Path(x["_source"]).name for x in consumers])
            self.assertEqual("director", consumers[0]["consumer"])

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

    def test_all_22_named_negative_fixtures_return_expected_codes(self):
        manifest = json.loads(
            (Path(__file__).parent / "fixtures" / "capability_contract_audit" / "negative_fixtures.json").read_text(encoding="utf-8")
        )
        self.assertEqual(22, len(manifest["fixtures"]))
        base_tools = {"tools/example.py", "tools/support.py", "tools/internal.py", "tools/diagnostic.py"}
        for fixture in manifest["fixtures"]:
            name = fixture["name"]
            contracts = [_contract("fixture")]
            tools = set(base_tools)
            dispatch = {"video_tools.py known"}
            catalog = {"video_tools.py known"}
            consumers = []
            if name == "unowned_python_tool":
                tools = tools | {"tools/unowned.py"}
            elif name == "canonical_missing_capability_id":
                contracts[0]["canonical_tools"][0].pop("capability_id")
            elif name == "invalid_capability_id":
                contracts[0]["canonical_tools"][0]["capability_id"] = "bad"
            elif name == "duplicate_capability_id":
                contracts.append(_contract("other"))
            elif name == "missing_loops":
                contracts[0]["canonical_tools"][0].pop("loops")
            elif name == "invalid_loops":
                contracts[0]["canonical_tools"][0]["loops"] = ["L9"]
            elif name == "missing_maturity":
                contracts[0]["canonical_tools"][0].pop("maturity")
            elif name == "invalid_maturity":
                contracts[0]["canonical_tools"][0]["maturity"] = "unknown"
            elif name == "empty_loops_without_stage_owner":
                contracts[0]["stage_owner"] = ""
                contracts[0]["canonical_tools"][0]["loops"] = []
            elif name == "bounded_missing_certified_scope":
                contracts[0]["canonical_tools"][0].pop("certified_scope")
            elif name == "certified_missing_certified_scope":
                contracts[0]["canonical_tools"][0]["maturity"] = "certified"
                contracts[0]["canonical_tools"][0].pop("certified_scope")
            elif name == "capability_missing_tool":
                contracts[0]["canonical_tools"][0]["tool"] = "tools/missing.py"
            elif name == "duplicate_canonical_owner":
                contracts.append(_contract("other", capability_id="cap.fixture.other.v1"))
            elif name in {"command_missing_both", "command_dispatch_only", "command_catalog_only"}:
                contracts[0]["canonical_tools"][0]["command"] = "video_tools.py absent"
                if name == "command_dispatch_only":
                    dispatch.add("video_tools.py absent")
                elif name == "command_catalog_only":
                    catalog.add("video_tools.py absent")
            elif name == "broken_domain_lookup":
                contracts[0]["capability_namespace"] = "cap.unknown.*"
            elif name == "broken_director_reference":
                consumers.append({"source": "skills/director.md", "consumer": "director", "active_capability_ids": ["cap.unknown.missing.v1"]})
            elif name == "active_legacy_reference":
                contracts[0]["canonical_tools"][0]["maturity"] = "legacy"
                consumers.append({"source": "skills/director.md", "consumer": "director", "active_capability_ids": ["cap.fixture.tool.v1"]})
            elif name in {"supporting_promoted_as_public", "internal_promoted_as_public", "diagnostic_promoted_as_public"}:
                section = name.removesuffix("_promoted_as_public") + "_tools"
                contracts[0][section][0]["capability_id"] = f"cap.fixture.{name}.v1"
                consumers.append({"source": "skills/director.md", "consumer": "director", "active_capability_ids": [f"cap.fixture.{name}.v1"]})
            errors = audit_repository_contracts(
                copy.deepcopy(contracts),
                python_tools=tools,
                dispatch_commands=dispatch,
                catalog_commands=catalog,
                capability_consumers=consumers,
            )
            codes = {item["code"] for item in errors}
            self.assertTrue(set(fixture["expected_codes"]) <= codes, (name, codes))

    def test_explicitly_shared_owner_is_valid(self):
        first = _contract("first")
        second = _contract("second")
        first["canonical_tools"][0]["shared"] = True
        second["canonical_tools"][0]["shared"] = True
        errors = audit_repository_contracts(
            [first, second],
            python_tools={"tools/example.py", "tools/support.py", "tools/internal.py", "tools/diagnostic.py"},
        )
        self.assertEqual([], errors)


class CapabilityAccountabilitySchemaUnitTest(unittest.TestCase):
    def _contract(self, **overrides):
        return _contract("fixture", **overrides)

    def _contract_without_accountability_fields(self):
        contract = self._contract()
        contract["canonical_tools"][0].pop("execution_class")
        contract["canonical_tools"][0].pop("capability_role")
        return contract

    def test_canonical_card_requires_execution_class_and_role(self):
        errors = validate_contract_schema([self._contract_without_accountability_fields()])
        self.assertEqual(
            {e["code"] for e in errors},
            {"missing_execution_class", "missing_capability_role"},
        )

    def test_invalid_execution_class_and_role_values_are_rejected(self):
        errors = validate_contract_schema([
            self._contract(execution_class="manual", capability_role="orchestrator")
        ])
        self.assertEqual(
            {e["code"] for e in errors},
            {"invalid_execution_class", "invalid_capability_role"},
        )

    def test_hybrid_adapter_is_rejected(self):
        errors = validate_contract_schema([
            self._contract(execution_class="hybrid", capability_role="adapter")
        ])
        self.assertIn("invalid_execution_class_role", {e["code"] for e in errors})

    def test_allowed_execution_class_role_matrix_is_accepted(self):
        valid_pairs = [
            ("deterministic", "operation"),
            ("hybrid", "operation"),
            ("deterministic", "review"),
            ("hybrid", "review"),
            ("deterministic", "gate"),
            ("hybrid", "gate"),
            ("deterministic", "adapter"),
        ]
        for execution_class, capability_role in valid_pairs:
            with self.subTest(
                execution_class=execution_class,
                capability_role=capability_role,
            ):
                self.assertEqual(
                    [],
                    validate_contract_schema([
                        self._contract(
                            execution_class=execution_class,
                            capability_role=capability_role,
                        )
                    ]),
                )


if __name__ == "__main__":
    unittest.main()
