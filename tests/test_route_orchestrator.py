import json
import hashlib
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import video_pipeline_core.route_orchestrator as route_orchestrator
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
            self.assertEqual(packet["mode"], "worker")
            self.assertIn(str(root / "video_intent.json"), packet["allowed_outputs"])
            self.assertIn("docs", packet["forbidden_writes"])
            self.assertIn("skills", packet["forbidden_writes"])
            self.assertIn("video_pipeline_core", packet["forbidden_writes"])
            self.assertFalse(stale.exists())
            snapshot = packet["snapshot"]["must_not_touch"][str(protected)]
            self.assertTrue(snapshot["exists"])
            self.assertEqual(snapshot["sha256"], hashlib.sha256(b"KEEP").hexdigest())

    def test_stage_zero_done_rejects_project_brief_without_video_intent(self):
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

            self.assertFalse(verdict["ok"])
            self.assertTrue(any("video_intent.json" in err for err in verdict["errors"]))
            self.assertFalse((root / "state.json").exists())

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
                            "tone": "clear instructional",
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

    def test_stage_zero_done_rejects_video_intent_with_followup_questions(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            task = write_next_task(root, root / "task.json", now_epoch=1000.0)
            output = root / "video_intent.json"
            output.write_text(
                json.dumps(plan_video_intent({"request": "請幫我剪一部結訓典禮影片"}), ensure_ascii=False),
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
                        "summary": "video intent generated but still needs context",
                    }
                ),
                encoding="utf-8",
            )

            verdict = accept_task_result(root / "task.json", result_path, state_out=root / "state.json")

            self.assertFalse(verdict["ok"])
            self.assertTrue(any("required_followup_questions" in err for err in verdict["errors"]))
            self.assertFalse((root / "state.json").exists())

    def test_stage_zero_needs_context_accepts_followup_video_intent_without_advancing(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            task = write_next_task(root, root / "task.json", now_epoch=1000.0)
            output = root / "video_intent.json"
            output.write_text(
                json.dumps(plan_video_intent({"request": "請幫我剪一部結訓典禮影片"}), ensure_ascii=False),
                encoding="utf-8",
            )
            os.utime(output, (1001.0, 1001.0))
            result_path = root / "result.json"
            result_path.write_text(
                json.dumps(
                    {
                        "artifact_role": "route_subagent_result",
                        "task_id": task["task_id"],
                        "status": "needs_context",
                        "outputs": [str(output)],
                        "next_action": "ask_followup",
                    }
                ),
                encoding="utf-8",
            )

            verdict = accept_task_result(root / "task.json", result_path, state_out=root / "state.json")

            self.assertTrue(verdict["ok"], verdict)
            state = _read_json(root / "state.json")
            self.assertEqual(state["status"], "needs_context")
            self.assertEqual(state["current_stage"], 0)
            self.assertEqual(state["next_action"], "ask_followup")

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

    def test_accept_rejects_repo_doc_change_by_bounded_worker(self):
        with tempfile.TemporaryDirectory() as repo_td, tempfile.TemporaryDirectory() as run_td:
            repo_root = Path(repo_td)
            (repo_root / "docs").mkdir()
            (repo_root / ".gitignore").write_text("*.tmp\n", encoding="utf-8")
            (repo_root / "docs" / "keep.md").write_text("tracked\n", encoding="utf-8")
            subprocess.run(["git", "init"], cwd=repo_root, check=True, stdout=subprocess.DEVNULL)
            subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo_root, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=repo_root, check=True)
            subprocess.run(["git", "add", "."], cwd=repo_root, check=True)
            subprocess.run(["git", "commit", "-m", "fixture"], cwd=repo_root, check=True, stdout=subprocess.DEVNULL)
            original_repo_root = route_orchestrator.REPO_ROOT
            route_orchestrator.REPO_ROOT = repo_root
            repo_doc = repo_root / "docs" / "_route_orchestrator_forbidden_probe.tmp"
            try:
                root = Path(run_td)
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
                                "tone": "clear instructional",
                            }
                        ),
                        ensure_ascii=False,
                    ),
                    encoding="utf-8",
                )
                os.utime(output, (1001.0, 1001.0))
                repo_doc.write_text("worker should not write docs\n", encoding="utf-8")
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
                self.assertTrue(any("repository guard changed" in err for err in verdict["errors"]))
                self.assertFalse((root / "state.json").exists())
            finally:
                route_orchestrator.REPO_ROOT = original_repo_root

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

            completed = subprocess.run(
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
                cwd=Path(__file__).resolve().parents[1],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            self.assertNotEqual(completed.returncode, 0)
            self.assertFalse(state.exists())


if __name__ == "__main__":
    unittest.main()
