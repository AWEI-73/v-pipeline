import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.pipeline_home import summarize_run


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "write_story_human_review_decision.py"


def _write_json(root: Path, name: str, payload: dict):
    path = root / name
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _make_run(root: Path):
    (root / "final.mp4").write_bytes(b"fake final")
    _write_json(root, "delivery_gate.json", {
        "artifact_role": "delivery_gate",
        "version": 1,
        "pass": True,
        "blocking": [],
        "warnings": [{
            "rule": "story_human_review_required",
            "message": "Story map contains agent-filled decisions that still need human review.",
        }],
        "next_action": None,
    })
    _write_json(root, "story_contract.json", {
        "artifact_role": "story_contract",
        "required_story_beats": [
            {"beat_id": "establish_gathering"},
            {"beat_id": "training_process_detail"},
        ],
    })
    _write_json(root, "story_to_material_map.json", {
        "artifact_role": "story_to_material_map",
        "items": [
            {"beat_id": "establish_gathering", "evidence_type": "agent_inferred", "needs_human_confirmation": True},
            {"beat_id": "training_process_detail", "evidence_type": "agent_inferred", "needs_human_confirmation": True},
        ],
    })


def _run_tool(*args: str, cwd: Path | None = None):
    return subprocess.run(
        [sys.executable, str(TOOL), *args],
        cwd=cwd or ROOT,
        text=True,
        capture_output=True,
    )


class StoryHumanReviewDecisionWriterTest(unittest.TestCase):
    def test_approved_all_beats_writes_artifact_and_pipeline_home_is_done(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_run(root)

            proc = _run_tool("--run", str(root), "--decision", "approved", "--reviewer", "human", "--approve-all", "--json")

            self.assertEqual(proc.returncode, 0, proc.stderr)
            decision = json.loads((root / "story_human_review_decision.json").read_text(encoding="utf-8"))
            self.assertEqual(decision["artifact_role"], "story_human_review_decision")
            self.assertEqual(decision["decision"], "approved")
            self.assertEqual(decision["reviewer"], "human")
            self.assertEqual(set(decision["approved_beat_ids"]), {"establish_gathering", "training_process_detail"})
            summary = summarize_run(root)
            self.assertEqual(summary["mode"], "done")
            self.assertEqual(summary["cursor"], "complete")

    def test_partial_approval_fails_and_does_not_write_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_run(root)

            proc = _run_tool(
                "--run", str(root),
                "--decision", "approved",
                "--reviewer", "human",
                "--approved-beat-id", "establish_gathering",
                "--json",
            )

            self.assertNotEqual(proc.returncode, 0)
            self.assertFalse((root / "story_human_review_decision.json").exists())

    def test_non_human_reviewer_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_run(root)

            proc = _run_tool("--run", str(root), "--decision", "approved", "--reviewer", "agent", "--approve-all", "--json")

            self.assertNotEqual(proc.returncode, 0)
            self.assertFalse((root / "story_human_review_decision.json").exists())

    def test_out_name_must_stay_run_local(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "run"
            root.mkdir()
            _make_run(root)
            outside = Path(tmp) / "outside.json"

            proc = _run_tool(
                "--run", str(root),
                "--decision", "approved",
                "--reviewer", "human",
                "--approve-all",
                "--out-name", str(outside),
                "--json",
            )

            self.assertNotEqual(proc.returncode, 0)
            self.assertFalse(outside.exists())
            self.assertFalse((root / "story_human_review_decision.json").exists())

    def test_revision_requested_requires_note_then_routes_to_repair(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_run(root)

            missing_note = _run_tool("--run", str(root), "--decision", "revision_requested", "--reviewer", "human", "--json")
            self.assertNotEqual(missing_note.returncode, 0)
            self.assertFalse((root / "story_human_review_decision.json").exists())

            proc = _run_tool(
                "--run", str(root),
                "--decision", "revision_requested",
                "--reviewer", "human",
                "--note", "Replace inferred training-process beat with reviewed material.",
                "--json",
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            decision = json.loads((root / "story_human_review_decision.json").read_text(encoding="utf-8"))
            self.assertEqual(decision["decision"], "revision_requested")
            self.assertEqual(decision["revision_notes"], ["Replace inferred training-process beat with reviewed material."])
            summary = summarize_run(root)
            self.assertEqual(summary["mode"], "repair")
            self.assertEqual(summary["cursor"], "human_story_review")
            self.assertEqual(summary["next"], "revise_story_material_mapping")

    def test_rejected_requires_note_or_rejected_beat_then_routes_to_repair(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_run(root)

            missing_evidence = _run_tool("--run", str(root), "--decision", "rejected", "--reviewer", "human", "--json")
            self.assertNotEqual(missing_evidence.returncode, 0)
            self.assertFalse((root / "story_human_review_decision.json").exists())

            proc = _run_tool(
                "--run", str(root),
                "--decision", "rejected",
                "--reviewer", "human",
                "--rejected-beat-id", "training_process_detail",
                "--note", "Human reviewer rejected the inferred training sequence.",
                "--json",
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            decision = json.loads((root / "story_human_review_decision.json").read_text(encoding="utf-8"))
            self.assertEqual(decision["decision"], "rejected")
            self.assertEqual(decision["rejected_beat_ids"], ["training_process_detail"])
            summary = summarize_run(root)
            self.assertEqual(summary["mode"], "repair")
            self.assertEqual(summary["cursor"], "human_story_review")
            self.assertEqual(summary["next"], "repair_rejected_story_material_mapping")

    def test_utf8_json_contains_no_replacement_character(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_run(root)
            note = "\u9700\u8981\u4eba\u5de5\u78ba\u8a8d\u8a13\u7df4\u6bb5\u843d"

            proc = _run_tool(
                "--run", str(root),
                "--decision", "revision_requested",
                "--reviewer", "human",
                "--note", note,
                "--json",
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            text = (root / "story_human_review_decision.json").read_text(encoding="utf-8")
            self.assertNotIn("\ufffd", text)
            self.assertNotIn("?" * 4, text)
            self.assertIn(note, text)


if __name__ == "__main__":
    unittest.main()
