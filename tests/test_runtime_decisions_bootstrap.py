"""Runtime bootstrap: blueprint.json + decisions.json -> soul-layer contract.

Verifies _copy_initial_artifacts compiles a density-correct segment_contract.json
via blueprint_to_contract when a decisions.json is present (and that the thin
fallback is used when it is absent).
"""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from video_pipeline_core import runtime_orchestrator as ro


def _blueprint():
    return {
        "artifact_role": "narrative_blueprint", "version": 1,
        "thesis": "a short real thing", "mode_hint": "warm_documentary",
        "beats": [
            {"id": "B1", "role": "setup", "summary": "quiet open"},
            {"id": "B2", "role": "turn", "summary": "the peak"},
        ],
    }


def _decisions():
    return {
        "B1": {"content_pattern": "establishing", "material_hint": "open"},
        "B2": {"content_pattern": "action", "emphasis": "hero", "material_hint": "peak"},
    }


class TestRuntimeDecisionsBootstrap(unittest.TestCase):
    def _setup_project(self, with_decisions):
        tmp = Path(tempfile.mkdtemp())
        inp = tmp / "input"
        inp.mkdir(parents=True)
        (inp / "blueprint.json").write_text(json.dumps(_blueprint()), encoding="utf-8")
        if with_decisions:
            (inp / "decisions.json").write_text(json.dumps(_decisions()), encoding="utf-8")
        run_dir = tmp / "runs" / "t1"
        run_dir.mkdir(parents=True)
        return tmp, run_dir

    def _run(self, project_dir, run_dir):
        args = SimpleNamespace(contract=None)
        try:
            ro._copy_initial_artifacts(project_dir, run_dir, args)
        except SystemExit:
            pass  # readiness gate may exit; we only assert the contract artifact

    def test_decisions_present_uses_soul_compiler(self):
        proj, run_dir = self._setup_project(with_decisions=True)
        self._run(proj, run_dir)
        contract_path = run_dir / "segment_contract.json"
        self.assertTrue(contract_path.exists(), "contract not generated")
        c = json.loads(contract_path.read_text(encoding="utf-8"))
        # soul layer markers: every segment carries content_pattern + sequence_grammar
        for seg in c["segments"]:
            self.assertIn("content_pattern", seg.get("editing_intent", {}))
            self.assertIn("required_functions", seg.get("sequence_grammar", {}))
            self.assertNotIn("editing_grammar", seg.get("core", {}))  # placed at seg level
        # decisions.json copied into the run for lineage
        self.assertTrue((run_dir / "decisions.json").exists())

    def test_no_decisions_falls_back_thin(self):
        proj, run_dir = self._setup_project(with_decisions=False)
        self._run(proj, run_dir)
        c = json.loads((run_dir / "segment_contract.json").read_text(encoding="utf-8"))
        # thin bootstrap path: no content_pattern injected
        self.assertNotIn("content_pattern", c["segments"][0].get("editing_intent", {}))


if __name__ == "__main__":
    unittest.main()
