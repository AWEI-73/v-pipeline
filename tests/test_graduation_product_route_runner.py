import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from video_pipeline_core.graduation_product_route_runner import (
    GraduationProductRouteRunner,
)


class FakeCommandRunner:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, command, cwd=None):
        self.calls.append(command)
        if not self.responses:
            raise AssertionError(f"unexpected command: {command}")
        return self.responses.pop(0)


def _result(exit_code=0, payload=None):
    stdout = json.dumps(payload or {}, ensure_ascii=False)
    return {"exit_code": exit_code, "stdout": stdout, "stderr": ""}


class GraduationProductRouteRunnerTest(unittest.TestCase):
    def test_stops_when_pipeline_home_returns_waiting(self):
        with TemporaryDirectory() as tmp:
            run = Path(tmp) / "run"
            out = Path(tmp) / "out"
            run.mkdir()
            runner = GraduationProductRouteRunner(
                repo_root=Path.cwd(),
                command_runner=FakeCommandRunner([
                    _result(payload={"status": "WAITING", "cursor": "human_story_review"}),
                ]),
            )

            result = runner.run(run=run, source_root=run, out_dir=out, mode="no-render")

            self.assertFalse(result["pass"])
            self.assertEqual(result["stop_gate"], "pipeline_home")
            self.assertEqual(result["stop_reason"], "WAITING")
            self.assertTrue((out / "pipeline_execution_trace.json").exists())
            self.assertTrue((out / "graduation_product_route_harness_result.json").exists())

    def test_no_render_stops_on_missing_product_route_review(self):
        with TemporaryDirectory() as tmp:
            run = Path(tmp) / "run"
            out = Path(tmp) / "out"
            run.mkdir()
            runner = GraduationProductRouteRunner(
                repo_root=Path.cwd(),
                command_runner=FakeCommandRunner([
                    _result(payload={"status": "READY", "cursor": "product_route"}),
                ]),
            )

            result = runner.run(run=run, source_root=run, out_dir=out, mode="no-render")

            self.assertFalse(result["pass"])
            self.assertEqual(result["stop_gate"], "product_route_review_decision")
            self.assertIn("missing", result["stop_reason"])

    def test_render_rehearsal_runs_rendered_qa_before_no_skip(self):
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
                json.dumps({"ready_for_production": True}),
                encoding="utf-8",
            )
            (run / "visual_selection_gate.json").write_text(
                json.dumps({"pass": True}),
                encoding="utf-8",
            )
            (run / "pipeline_execution_trace.json").write_text(
                json.dumps({
                    "entries": [{
                        "artifact": "visual_selection_gate.json",
                        "classification": "pipeline_tool_generated",
                        "source_tool": "tools/visual_selection_gate.py",
                    }]
                }),
                encoding="utf-8",
            )
            (run / "shot_level_material_proof_plan.json").write_text(
                json.dumps({"shots": [{"shot_id": "s1", "proof_role": "primary"}]}),
                encoding="utf-8",
            )
            (run / "effect_handoff.json").write_text(
                json.dumps({"status": "accepted"}),
                encoding="utf-8",
            )
            (run / "render_handoff.json").write_text(
                json.dumps({"music_subtitle_profile": {"status": "ready"}}),
                encoding="utf-8",
            )
            runner = GraduationProductRouteRunner(
                repo_root=Path.cwd(),
                command_runner=FakeCommandRunner([
                    _result(payload={"status": "READY", "cursor": "render_rehearsal"}),
                    _result(payload={"pass": False, "blocking": [{"rule": "ffprobe_failed"}]}),
                ]),
            )

            result = runner.run(run=run, source_root=run, out_dir=out, mode="render-rehearsal")

            self.assertFalse(result["pass"])
            self.assertEqual(result["stop_gate"], "rendered_product_qa")
            trace = json.loads((out / "pipeline_execution_trace.json").read_text(encoding="utf-8"))
            stages = [entry["stage_id"] for entry in trace["entries"]]
            self.assertIn("rendered_product_qa", stages)
            self.assertNotIn("no_skip_execution_trace", stages)

    def test_copied_visual_gate_blocks_before_render(self):
        with TemporaryDirectory() as tmp:
            run = Path(tmp) / "run"
            out = Path(tmp) / "out"
            run.mkdir()
            (run / "product_route_review_decision.json").write_text(
                json.dumps({"decision": "approved", "reviewer": "human", "approve_all_reviewed": True}),
                encoding="utf-8",
            )
            (run / "production_readiness_gate.json").write_text(
                json.dumps({"ready_for_production": True}),
                encoding="utf-8",
            )
            (run / "visual_selection_gate.json").write_text(
                json.dumps({"pass": True}),
                encoding="utf-8",
            )
            (run / "shot_level_material_proof_plan.json").write_text(
                json.dumps({"shots": [{"shot_id": "s1", "proof_role": "primary"}]}),
                encoding="utf-8",
            )
            (run / "pipeline_execution_trace.json").write_text(
                json.dumps({
                    "entries": [{
                        "artifact": "visual_selection_gate.json",
                        "classification": "copied_from_prior",
                    }]
                }),
                encoding="utf-8",
            )
            runner = GraduationProductRouteRunner(
                repo_root=Path.cwd(),
                command_runner=FakeCommandRunner([
                    _result(payload={"status": "READY", "cursor": "render_rehearsal"}),
                ]),
            )

            result = runner.run(run=run, source_root=run, out_dir=out, mode="render-rehearsal")

            self.assertFalse(result["pass"])
            self.assertEqual(result["stop_gate"], "visual_selection_gate")
            self.assertIn("copied", result["stop_reason"])


if __name__ == "__main__":
    unittest.main()
