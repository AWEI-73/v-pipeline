import json
import hashlib
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core.route_orchestrator import accept_task_result, write_next_task
from video_pipeline_core.video_intent_planner import plan_video_intent


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class RouteOrchestratorTaskPacketTest(unittest.TestCase):
    def test_emit_next_task_snapshots_must_not_touch_and_clears_allowed_outputs(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            protected = root / "final.mp4"
            protected.write_bytes(b"KEEP")
            stale = root / "project_brief.json"
            stale.write_text("stale", encoding="utf-8")

            packet = write_next_task(root, root / "task.json", now_epoch=1000.0)

            self.assertEqual(packet["artifact_role"], "route_subagent_task")
            self.assertEqual(packet["stage"], "Video Intent Planner")
            self.assertIn(str(root / "video_intent.json"), packet["allowed_outputs"])
            self.assertFalse(stale.exists())
            snapshot = packet["snapshot"]["must_not_touch"][str(protected)]
            self.assertTrue(snapshot["exists"])
            self.assertEqual(snapshot["sha256"], hashlib.sha256(b"KEEP").hexdigest())

    def test_accept_done_advances_when_outputs_fresh_and_protected_unchanged(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "final.mp4").write_bytes(b"KEEP")
            task = write_next_task(root, root / "task.json", now_epoch=1000.0)
            output = root / "project_brief.json"
            output.write_text('{"ok": true}', encoding="utf-8")
            os.utime(output, (1001.0, 1001.0))
            result = {
                "artifact_role": "route_subagent_result",
                "task_id": task["task_id"],
                "status": "done",
                "outputs": [str(output)],
                "summary": "brief generated",
            }
            result_path = root / "result.json"
            result_path.write_text(json.dumps(result), encoding="utf-8")

            verdict = accept_task_result(root / "task.json", result_path, state_out=root / "state.json")

            self.assertTrue(verdict["ok"], verdict)
            state = _read_json(root / "state.json")
            self.assertEqual(state["status"], "ready")
            self.assertEqual(state["current_stage"], 1)
            self.assertEqual(state["history"][-1]["accepted_status"], "done")

    def test_stage_zero_accepts_real_video_intent_artifact(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            task = write_next_task(root, root / "task.json", now_epoch=1000.0)
            output = root / "video_intent.json"
            output.write_text(
                json.dumps(
                    plan_video_intent(
                        {
                            "request": "teaching video with existing screen recordings",
                            "video_type": "teaching",
                            "audience": "new students",
                            "goal": "teach clearly",
                            "target_length": "5 minutes",
                            "material_availability": "existing",
                        }
                    ),
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            os.utime(output, (1001.0, 1001.0))
            result_path = root / "result.json"
            result_path.write_text(
                json.dumps(
                    {
                        "artifact_role": "route_subagent_result",
                        "task_id": task["task_id"],
                        "status": "done",
                        "outputs": [str(output)],
                        "summary": "video intent generated",
                    }
                ),
                encoding="utf-8",
            )

            verdict = accept_task_result(root / "task.json", result_path, state_out=root / "state.json")

            self.assertTrue(verdict["ok"], verdict)
            state = _read_json(root / "state.json")
            self.assertEqual(state["current_stage"], 1)
            self.assertEqual(state["history"][-1]["outputs"], [str(output)])

    def test_accept_rejects_modified_must_not_touch(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            protected = root / "final.mp4"
            protected.write_bytes(b"KEEP")
            task = write_next_task(root, root / "task.json", now_epoch=1000.0)
            protected.write_bytes(b"CHANGED")
            output = root / "project_brief.json"
            output.write_text("{}", encoding="utf-8")
            os.utime(output, (1001.0, 1001.0))
            result_path = root / "result.json"
            result_path.write_text(
                json.dumps(
                    {
                        "artifact_role": "route_subagent_result",
                        "task_id": task["task_id"],
                        "status": "done",
                        "outputs": [str(output)],
                    }
                ),
                encoding="utf-8",
            )

            verdict = accept_task_result(root / "task.json", result_path, state_out=root / "state.json")

            self.assertFalse(verdict["ok"])
            self.assertIn("must_not_touch changed", verdict["errors"][0])
            self.assertFalse((root / "state.json").exists())

    def test_accept_rejects_stale_allowed_output(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            task = write_next_task(root, root / "task.json", now_epoch=1000.0)
            output = root / "project_brief.json"
            output.write_text("{}", encoding="utf-8")
            os.utime(output, (999.0, 999.0))
            result_path = root / "result.json"
            result_path.write_text(
                json.dumps(
                    {
                        "artifact_role": "route_subagent_result",
                        "task_id": task["task_id"],
                        "status": "done",
                        "outputs": [str(output)],
                    }
                ),
                encoding="utf-8",
            )

            verdict = accept_task_result(root / "task.json", result_path, state_out=root / "state.json")

            self.assertFalse(verdict["ok"])
            self.assertIn("stale output", verdict["errors"][0])

    def test_accept_rejects_unexpected_output_claim(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            task = write_next_task(root, root / "task.json", now_epoch=1000.0)
            output = root / "unexpected.json"
            output.write_text("{}", encoding="utf-8")
            os.utime(output, (1001.0, 1001.0))
            result_path = root / "result.json"
            result_path.write_text(
                json.dumps(
                    {
                        "artifact_role": "route_subagent_result",
                        "task_id": task["task_id"],
                        "status": "done",
                        "outputs": [str(output)],
                    }
                ),
                encoding="utf-8",
            )

            verdict = accept_task_result(root / "task.json", result_path, state_out=root / "state.json")

            self.assertFalse(verdict["ok"])
            self.assertIn("output outside allowed_outputs", verdict["errors"][0])

    def test_non_happy_status_transitions_are_explicit(self):
        for status, expected_state in [
            ("blocked", "blocked"),
            ("needs_context", "needs_context"),
            ("failed", "failed"),
        ]:
            with self.subTest(status=status), tempfile.TemporaryDirectory() as td:
                root = Path(td)
                task = write_next_task(root, root / "task.json", now_epoch=1000.0)
                result_path = root / "result.json"
                result_path.write_text(
                    json.dumps(
                        {
                            "artifact_role": "route_subagent_result",
                            "task_id": task["task_id"],
                            "status": status,
                            "outputs": [],
                            "next_action": "operator_review",
                        }
                    ),
                    encoding="utf-8",
                )

                verdict = accept_task_result(root / "task.json", result_path, state_out=root / "state.json")

                self.assertTrue(verdict["ok"], verdict)
                state = _read_json(root / "state.json")
                self.assertEqual(state["status"], expected_state)
                self.assertEqual(state["current_stage"], 0)
                self.assertEqual(state["next_action"], "operator_review")


class RouteOrchestratorCliTest(unittest.TestCase):
    def test_cli_next_and_accept_round_trip(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            task = root / "task.json"
            result = root / "result.json"
            state = root / "state.json"
            subprocess.run(
                [
                    sys.executable,
                    "video_tools.py",
                    "route-task-next",
                    str(root),
                    "--out",
                    str(task),
                    "--now-epoch",
                    "1000",
                ],
                check=True,
                cwd=Path(__file__).resolve().parents[1],
                stdout=subprocess.DEVNULL,
            )
            packet = _read_json(task)
            output = root / "project_brief.json"
            output.write_text("{}", encoding="utf-8")
            os.utime(output, (1001.0, 1001.0))
            result.write_text(
                json.dumps(
                    {
                        "artifact_role": "route_subagent_result",
                        "task_id": packet["task_id"],
                        "status": "done",
                        "outputs": [str(output)],
                    }
                ),
                encoding="utf-8",
            )

            subprocess.run(
                [
                    sys.executable,
                    "video_tools.py",
                    "route-task-accept",
                    "--task",
                    str(task),
                    "--result",
                    str(result),
                    "--state-out",
                    str(state),
                ],
                check=True,
                cwd=Path(__file__).resolve().parents[1],
                stdout=subprocess.DEVNULL,
            )

            self.assertEqual(_read_json(state)["current_stage"], 1)


if __name__ == "__main__":
    unittest.main()
