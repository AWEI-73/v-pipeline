"""Guards: the graduation product-route harness is driven by ROUTE_STAGES and
composes only registered branches.

ROUTE_STAGES (video_pipeline_core/graduation_product_route_runner.py) is the
declarative source of the route's stage sequence + per-stage owner branch,
owner tool, gate artifact, and kind. These guards fail if the table names an
owner that is not a real branch in docs/branch-contract-registry.json, if an
owner tool is missing, if a stage does not declare a verify-or-review kind, or
if the executor ever runs stages in an order that diverges from the table.

(A full registry-driven harness that derives the order from a JSON manifest is
a further step; this table + these guards remove the hardcoded, drift-prone
stage list in the meantime.)
"""
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from video_pipeline_core.graduation_product_route_runner import (
    ROUTE_STAGES,
    REVIEW_KINDS,
    VERIFY_KINDS,
    GraduationProductRouteRunner,
)

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs" / "branch-contract-registry.json"


def _result(exit_code=0, payload=None):
    return {"exit_code": exit_code, "stdout": json.dumps(payload or {}), "stderr": ""}


class FakeCommandRunner:
    def __init__(self, responses):
        self.responses = list(responses)

    def __call__(self, command, cwd=None):
        return self.responses.pop(0)


class GraduationRouteRegistryConsistencyTest(unittest.TestCase):
    def _branch_ids(self) -> set[str]:
        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        return {branch["branch_id"] for branch in registry["branches"]}

    def test_stage_owners_are_registered_branches(self):
        owners = {stage["owner"] for stage in ROUTE_STAGES}
        unregistered = sorted(owners - self._branch_ids())
        self.assertEqual(unregistered, [], f"stage owners missing from registry: {unregistered}")

    def test_stage_owner_tools_exist(self):
        for stage in ROUTE_STAGES:
            tool = stage.get("owner_tool")
            if tool:
                self.assertTrue((ROOT / tool).exists(), f"{stage['stage_id']} owner tool missing: {tool}")

    def test_every_stage_declares_verify_or_review(self):
        allowed = VERIFY_KINDS | REVIEW_KINDS
        for stage in ROUTE_STAGES:
            self.assertIn(
                stage["kind"],
                allowed,
                f"{stage['stage_id']} kind {stage['kind']!r} is neither a verify nor a review",
            )

    def test_executed_order_matches_route_stages(self):
        with TemporaryDirectory() as tmp:
            run = Path(tmp) / "run"
            out = Path(tmp) / "out"
            run.mkdir()
            (run / "final.mp4").write_bytes(b"fake")
            (run / "product_route_review_decision.json").write_text(
                json.dumps({"decision": "approved", "reviewer": "human", "approve_all_reviewed": True}),
                encoding="utf-8",
            )
            (run / "production_readiness_gate.json").write_text(
                json.dumps({"ready_for_production": True}), encoding="utf-8"
            )
            (run / "visual_selection_gate.json").write_text(json.dumps({"pass": True}), encoding="utf-8")
            (run / "pipeline_execution_trace.json").write_text(
                json.dumps({"entries": [{
                    "artifact": "visual_selection_gate.json",
                    "classification": "pipeline_tool_generated",
                    "source_tool": "tools/visual_selection_gate.py",
                }]}),
                encoding="utf-8",
            )
            (run / "shot_level_material_proof_plan.json").write_text(
                json.dumps({"shots": [{"shot_id": "s1", "proof_role": "primary"}]}), encoding="utf-8"
            )
            (run / "effect_handoff.json").write_text(json.dumps({"status": "accepted"}), encoding="utf-8")
            (run / "render_handoff.json").write_text(
                json.dumps({"music_subtitle_profile": {"status": "ready"}}), encoding="utf-8"
            )
            runner = GraduationProductRouteRunner(
                repo_root=Path.cwd(),
                command_runner=FakeCommandRunner([
                    _result(payload={"status": "READY", "cursor": "render_rehearsal"}),
                    _result(payload={"pass": True}),
                    _result(exit_code=0, payload={"pass": True}),
                ]),
            )

            result = runner.run(run=run, source_root=run, out_dir=out, mode="render-rehearsal")

            self.assertTrue(result["pass"], result)
            trace = json.loads((out / "pipeline_execution_trace.json").read_text(encoding="utf-8"))
            executed = [entry["stage_id"] for entry in trace["entries"]]
            self.assertEqual(executed, [stage["stage_id"] for stage in ROUTE_STAGES])


if __name__ == "__main__":
    unittest.main()
