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
                json.dumps({"artifact_role": "render_handoff", "owner": "main-pipeline", "ok": True}),
                encoding="utf-8",
            )
            (run / "audio_subtitle_review_handoff.json").write_text(
                json.dumps({"status": "ready"}), encoding="utf-8"
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


    def _reach_visual_gate(self, run):
        (run / "product_route_review_decision.json").write_text(
            json.dumps({"decision": "approved", "reviewer": "human", "approve_all_reviewed": True}),
            encoding="utf-8",
        )
        (run / "production_readiness_gate.json").write_text(
            json.dumps({"ready_for_production": True}), encoding="utf-8"
        )
        (run / "visual_selection_gate.json").write_text(json.dumps({"pass": True}), encoding="utf-8")
        (run / "shot_level_material_proof_plan.json").write_text(
            json.dumps({"shots": [{"shot_id": "s1", "proof_role": "primary"}]}), encoding="utf-8"
        )
        (run / "pipeline_execution_trace.json").write_text(
            json.dumps({"entries": [{
                "artifact": "visual_selection_gate.json",
                "classification": "pipeline_tool_generated",
                "source_tool": "tools/visual_selection_gate.py",
            }]}),
            encoding="utf-8",
        )

    def _write_signed_visual_review(self, run):
        from video_pipeline_core.reviewer_registry import sign_review

        signature = sign_review("visual_selection_reviewer", passed=True, findings=[])
        (run / "visual_selection_review.json").write_text(
            json.dumps({"artifact_role": "visual_selection_review", "review_signature": signature}),
            encoding="utf-8",
        )

    def test_unsigned_visual_review_blocks_with_sign_reminder(self):
        with TemporaryDirectory() as tmp:
            run = Path(tmp) / "run"
            out = Path(tmp) / "out"
            run.mkdir()
            self._reach_visual_gate(run)
            (run / "visual_selection_review.json").write_text(
                json.dumps({"artifact_role": "visual_selection_review", "selections": []}),
                encoding="utf-8",
            )
            runner = GraduationProductRouteRunner(
                repo_root=Path.cwd(),
                command_runner=FakeCommandRunner([_result(payload={"status": "READY"})]),
            )

            result = runner.run(run=run, source_root=run, out_dir=out, mode="no-render")

            self.assertFalse(result["pass"])
            self.assertEqual(result["stop_gate"], "visual_selection_gate")
            self.assertEqual(result["next_action"], "sign_review")

    def test_signed_visual_review_passes_signature_gate(self):
        with TemporaryDirectory() as tmp:
            run = Path(tmp) / "run"
            out = Path(tmp) / "out"
            run.mkdir()
            self._reach_visual_gate(run)
            self._write_signed_visual_review(run)
            runner = GraduationProductRouteRunner(
                repo_root=Path.cwd(),
                command_runner=FakeCommandRunner([_result(payload={"status": "READY"})]),
            )

            result = runner.run(run=run, source_root=run, out_dir=out, mode="no-render")

            # signature accepted -> route proceeds past visual gate to the next
            # missing gate (effect_handoff), not blocked on signature
            self.assertEqual(result["stop_gate"], "effect_handoff")

    def test_unsigned_effect_review_blocks_with_sign_reminder(self):
        with TemporaryDirectory() as tmp:
            run = Path(tmp) / "run"
            out = Path(tmp) / "out"
            run.mkdir()
            self._reach_visual_gate(run)
            self._write_signed_visual_review(run)
            (run / "effect_handoff.json").write_text(
                json.dumps({"status": "accepted"}),
                encoding="utf-8",
            )
            (run / "effect_review.json").write_text(
                json.dumps({"artifact_role": "effect_review", "status": "pass"}),
                encoding="utf-8",
            )
            runner = GraduationProductRouteRunner(
                repo_root=Path.cwd(),
                command_runner=FakeCommandRunner([_result(payload={"status": "READY"})]),
            )

            result = runner.run(run=run, source_root=run, out_dir=out, mode="no-render")

            self.assertFalse(result["pass"])
            self.assertEqual(result["stop_gate"], "effect_handoff")
            self.assertEqual(result["next_action"], "sign_review")

    def test_signed_effect_review_passes_signature_gate(self):
        from video_pipeline_core.reviewer_registry import sign_review

        with TemporaryDirectory() as tmp:
            run = Path(tmp) / "run"
            out = Path(tmp) / "out"
            run.mkdir()
            self._reach_visual_gate(run)
            self._write_signed_visual_review(run)
            (run / "effect_handoff.json").write_text(
                json.dumps({"status": "accepted"}),
                encoding="utf-8",
            )
            signature = sign_review("effect_director", passed=True, findings=[])
            (run / "effect_review.json").write_text(
                json.dumps({"artifact_role": "effect_review", "status": "pass", "review_signature": signature}),
                encoding="utf-8",
            )
            runner = GraduationProductRouteRunner(
                repo_root=Path.cwd(),
                command_runner=FakeCommandRunner([_result(payload={"status": "READY"})]),
            )

            result = runner.run(run=run, source_root=run, out_dir=out, mode="no-render")

            self.assertFalse(result["pass"])
            self.assertEqual(result["stop_gate"], "music_subtitle_profile")

    def test_music_subtitle_stage_does_not_consume_main_render_handoff(self):
        with TemporaryDirectory() as tmp:
            run = Path(tmp) / "run"
            out = Path(tmp) / "out"
            run.mkdir()
            self._reach_visual_gate(run)
            self._write_signed_visual_review(run)
            (run / "effect_handoff.json").write_text(json.dumps({"status": "accepted"}), encoding="utf-8")
            from video_pipeline_core.reviewer_registry import sign_review

            signature = sign_review("effect_director", passed=True, findings=[])
            (run / "effect_review.json").write_text(
                json.dumps({"artifact_role": "effect_review", "status": "pass", "review_signature": signature}),
                encoding="utf-8",
            )
            (run / "render_handoff.json").write_text(
                json.dumps({"artifact_role": "render_handoff", "owner": "main-pipeline", "ok": True, "status": "ready"}),
                encoding="utf-8",
            )
            runner = GraduationProductRouteRunner(
                repo_root=Path.cwd(),
                command_runner=FakeCommandRunner([_result(payload={"status": "READY"})]),
            )

            result = runner.run(run=run, source_root=run, out_dir=out, mode="no-render")

            self.assertFalse(result["pass"])
            self.assertEqual(result["stop_gate"], "music_subtitle_profile")

    def test_compose_render_handoff_requires_ok_main_pipeline_ownership(self):
        with TemporaryDirectory() as tmp:
            run = Path(tmp) / "run"
            out = Path(tmp) / "out"
            run.mkdir()
            self._reach_visual_gate(run)
            self._write_signed_visual_review(run)
            (run / "effect_handoff.json").write_text(json.dumps({"status": "accepted"}), encoding="utf-8")
            from video_pipeline_core.reviewer_registry import sign_review

            signature = sign_review("effect_director", passed=True, findings=[])
            (run / "effect_review.json").write_text(
                json.dumps({"artifact_role": "effect_review", "status": "pass", "review_signature": signature}),
                encoding="utf-8",
            )
            (run / "audio_subtitle_review_handoff.json").write_text(
                json.dumps({"status": "ready"}), encoding="utf-8"
            )
            (run / "render_handoff.json").write_text(
                json.dumps({"artifact_role": "render_handoff", "status": "ready"}), encoding="utf-8"
            )
            runner = GraduationProductRouteRunner(
                repo_root=Path.cwd(),
                command_runner=FakeCommandRunner([_result(payload={"status": "READY"})]),
            )

            result = runner.run(run=run, source_root=run, out_dir=out, mode="no-render")

            self.assertFalse(result["pass"])
            self.assertEqual(result["stop_gate"], "compose_render_handoff")
            self.assertIn("ok", result["stop_reason"])


if __name__ == "__main__":
    unittest.main()
