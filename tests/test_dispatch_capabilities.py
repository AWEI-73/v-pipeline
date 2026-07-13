import copy
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace

from video_pipeline_core.skill_tool_contract import load_contracts
from video_pipeline_core.capability_catalog import build_catalog, load_live_catalog, query_catalog
import video_tools


def _contract(
    tool="tools/audio_mix_plan_execute.py",
    capability_id="cap.audio-director.audio-mix-plan-execute.v1",
    when="execute speech ducking",
    execution_class="deterministic",
    capability_role="operation",
):
    return {
        "_source": "skills/audio-director.md",
        "version": 1,
        "skill": "audio-director",
        "stage_owner": "audio_director_mix_execution",
        "capability_namespace": "cap.audio-director.*",
        "capability_lookup_owner": "audio-director",
        "triggers": ["audio"],
        "forbidden_tools": [],
        "canonical_tools": [{
            "capability_id": capability_id,
            "tool": tool,
            "execution_class": execution_class,
            "capability_role": capability_role,
            "loops": ["L3"],
            "maturity": "bounded",
            "certified_scope": "Canon 67 39s speech-aware preview mix",
            "when": when,
            "inputs": ["audio_mix_plan.json", "audio_handoff_acceptance.json"],
            "outputs": ["final_audio.wav", "audio_mix_report.json"],
            "stop_if": ["acceptance is not ok"],
        }],
    }


class DispatchCapabilitiesTest(unittest.TestCase):
    def test_build_and_query_exact_id_owner_loop_and_and_query(self):
        catalog = build_catalog([_contract()])
        self.assertTrue(catalog["ok"], catalog)
        exact = query_catalog(catalog, selector="id", value="cap.audio-director.audio-mix-plan-execute.v1")
        self.assertTrue(exact["ok"])
        self.assertEqual(1, exact["count"])
        self.assertEqual(1, len(exact["results"]))
        self.assertEqual("bounded", exact["results"][0]["maturity"])
        self.assertEqual(1, query_catalog(catalog, selector="owner", value="audio-director")["count"])
        self.assertEqual(1, query_catalog(catalog, selector="loop", value="L3")["count"])
        self.assertEqual(1, query_catalog(catalog, selector="query", value="speech ducking")["count"])

    def test_no_match_and_invalid_catalog_envelopes(self):
        catalog = build_catalog([_contract()])
        no_match = query_catalog(catalog, selector="query", value="definitely absent")
        self.assertFalse(no_match["ok"])
        self.assertEqual("no_match", no_match["error"]["code"])
        invalid = build_catalog([_contract()], validation_errors=[{"code": "missing_capability_id"}])
        self.assertFalse(invalid["ok"])
        invalid_result = query_catalog(invalid, selector="id", value="anything")
        self.assertEqual("invalid_catalog", invalid_result["error"]["code"])

    def test_cards_are_deterministic_and_load_live_catalog_is_not_cached(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = root / "audio.md"
            payload = _contract()
            marker = lambda value: "<!-- TOOL_CONTRACT_START -->\n" + json.dumps(value) + "\n<!-- TOOL_CONTRACT_END -->\n"
            skill.write_text(marker(payload), encoding="utf-8")
            first = load_live_catalog(root)
            payload["canonical_tools"][0]["when"] = "changed query phrase"
            skill.write_text(marker(payload), encoding="utf-8")
            second = load_live_catalog(root)
            self.assertNotEqual(first["cards"], second["cards"])
            self.assertEqual(first["cards"], sorted(first["cards"], key=lambda item: item["capability_id"]))

    def test_live_speech_ducking_query_resolves_audio_capability(self):
        root = Path(__file__).resolve().parents[1]
        catalog = load_live_catalog(root / "skills")
        result = query_catalog(catalog, selector="query", value="speech ducking")
        self.assertTrue(result["ok"], result)
        self.assertIn(
            "cap.audio-director.audio-mix-plan-execute.v1",
            [item["capability_id"] for item in result["results"]],
        )

    def test_cli_no_match_with_json_output_returns_one(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "missing.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    "video_tools.py",
                    "dispatch-capabilities",
                    "--id",
                    "cap.no-such-owner.no-such-capability.v1",
                    "--out",
                    str(out),
                ],
                cwd=root,
                text=True,
                capture_output=True,
            )
            self.assertEqual(1, completed.returncode, completed.stdout + completed.stderr)
            self.assertEqual("no_match", json.loads(out.read_text(encoding="utf-8"))["error"]["code"])

    def test_query_requires_count_to_equal_results(self):
        catalog = build_catalog([_contract()])
        for selector, value in (("id", "cap.audio-director.audio-mix-plan-execute.v1"), ("owner", "audio-director"), ("loop", "L3")):
            result = query_catalog(catalog, selector=selector, value=value)
            self.assertEqual(result["count"], len(result["results"]))

    def test_cli_seam_writes_exact_json_and_human_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skills = root / "skills"
            skills.mkdir()
            tools = root / "tools"
            tools.mkdir()
            (tools / "audio_mix_plan_execute.py").write_text("# fixture", encoding="utf-8")
            payload = _contract()
            skills.joinpath("audio-director.md").write_text(
                "<!-- TOOL_CONTRACT_START -->\n" + json.dumps(payload) + "\n<!-- TOOL_CONTRACT_END -->\n",
                encoding="utf-8",
            )
            out = root / "result.json"
            args = SimpleNamespace(id=None, owner=None, loop=None, query=None, json=True, out=str(out))
            args.id = "cap.audio-director.audio-mix-plan-execute.v1"
            stdout = StringIO()
            with redirect_stdout(stdout):
                code = video_tools.run_dispatch_capabilities_query(
                    args,
                    skills_dir=skills,
                    tools_dir=tools,
                    dispatch_commands=set(),
                    catalog_commands=set(),
                )
            self.assertEqual(0, code)
            self.assertEqual(json.loads(stdout.getvalue()), json.loads(out.read_text(encoding="utf-8")))
            human = SimpleNamespace(id=None, owner="audio-director", loop=None, query=None, json=False, out=None)
            stdout = StringIO()
            with redirect_stdout(stdout):
                self.assertEqual(0, video_tools.run_dispatch_capabilities_query(human, skills_dir=skills, tools_dir=tools, dispatch_commands=set(), catalog_commands=set()))
            self.assertIn("cap.audio-director.audio-mix-plan-execute.v1 [bounded]", stdout.getvalue())

    def test_cli_no_match_human_mode_is_stderr_only_and_selector_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skills = root / "skills"
            skills.mkdir()
            tools = root / "tools"
            tools.mkdir()
            (tools / "audio_mix_plan_execute.py").write_text("# fixture", encoding="utf-8")
            skills.joinpath("audio-director.md").write_text(
                "<!-- TOOL_CONTRACT_START -->\n" + json.dumps(_contract()) + "\n<!-- TOOL_CONTRACT_END -->\n",
                encoding="utf-8",
            )
            args = SimpleNamespace(id=None, owner=None, loop=None, query="absent", json=False, out=None)
            stdout, stderr = StringIO(), StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                code = video_tools.run_dispatch_capabilities_query(args, skills_dir=skills, tools_dir=tools, dispatch_commands=set(), catalog_commands=set())
            self.assertEqual(1, code)
            self.assertEqual("", stdout.getvalue())
            self.assertEqual("capability query: no matches\n", stderr.getvalue())


class CapabilityCatalogAccountabilityUnitTest(unittest.TestCase):
    def test_live_card_projects_normalized_command_and_accountability_fields(self):
        source_entry = {
            "capability_id": "cap.voiceover.voiceover-provider-plan.v1",
            "tool": "python .\\video_tools.py voiceover-provider-plan",
            "execution_class": "deterministic",
            "capability_role": "operation",
            "loops": ["L2"],
            "maturity": "bounded",
            "certified_scope": "synthetic provider planning fixture",
            "when": "plan provider selection",
            "inputs": ["voiceover_request.json"],
            "outputs": ["voiceover_provider_plan.json"],
            "stop_if": ["request is invalid"],
        }
        contract = {
            "_source": "skills/voiceover-provider.md",
            "version": 1,
            "skill": "voiceover-provider",
            "stage_owner": "voiceover_provider_plan",
            "capability_namespace": "cap.voiceover.*",
            "capability_lookup_owner": "voiceover-provider",
            "triggers": ["voiceover"],
            "forbidden_tools": [],
            "canonical_tools": [source_entry],
        }

        catalog = build_catalog([contract])
        self.assertTrue(catalog["ok"], catalog)
        card = catalog["cards"][0]
        self.assertEqual(card["command"], "video_tools.py voiceover-provider-plan")
        self.assertEqual(card["execution_class"], "deterministic")
        self.assertEqual(card["capability_role"], "operation")
        self.assertNotIn("command", source_entry)

    def test_query_results_expose_projected_accountability_fields(self):
        catalog = build_catalog([
            _contract(
                tool="python .\\video_tools.py voiceover-provider-plan",
                capability_id="cap.voiceover.voiceover-provider-plan.v1",
                when="plan provider selection",
                execution_class="deterministic",
                capability_role="operation",
            )
        ])
        result = query_catalog(
            catalog,
            selector="id",
            value="cap.voiceover.voiceover-provider-plan.v1",
        )
        self.assertTrue(result["ok"], result)
        card = result["results"][0]
        self.assertEqual(card["command"], "video_tools.py voiceover-provider-plan")
        self.assertEqual(card["execution_class"], "deterministic")
        self.assertEqual(card["capability_role"], "operation")


if __name__ == "__main__":
    unittest.main()
