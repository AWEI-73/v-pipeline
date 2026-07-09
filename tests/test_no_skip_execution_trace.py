import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from video_pipeline_core.no_skip_execution_trace import (
    audit_run_gate_authenticity,
    evaluate_no_skip_contract,
)


def _write_json(root: Path, name: str, payload: dict) -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


class NoSkipExecutionTraceTest(unittest.TestCase):
    def test_self_authored_visual_gate_blocks_preview_verification(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "final_copyedit_rehearsal.mp4").write_bytes(b"fake")
            _write_json(root, "visual_selection_gate.json", {
                "artifact_role": "visual_selection_gate",
                "pass": True,
            })
            _write_json(root, "pipeline_execution_trace.json", {
                "artifact_role": "pipeline_execution_trace",
                "entries": [{
                    "artifact": "visual_selection_gate.json",
                    "classification": "run_local_worker_generated",
                    "source_tool": "run-local-script",
                }],
            })

            result = evaluate_no_skip_contract(root)

            self.assertFalse(result["pass"])
            rules = {item["rule"] for item in result["blocking"]}
            self.assertIn("self_authored_gate_artifact", rules)

    def test_timing_only_title_qa_without_rendered_evidence_blocks(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "final_copyedit_rehearsal.mp4").write_bytes(b"fake")
            _write_json(root, "pipeline_execution_trace.json", {
                "artifact_role": "pipeline_execution_trace",
                "entries": [{
                    "artifact": "title_effect_lifecycle_qa.json",
                    "classification": "pipeline_tool_generated",
                    "source_tool": "tools/title_effect_lifecycle_qa.py",
                    "command": "tool",
                    "inputs": ["title_effect_lifecycle_plan.json"],
                }],
            })
            _write_json(root, "title_effect_lifecycle_qa.json", {
                "artifact_role": "title_effect_lifecycle_qa",
                "pass": True,
                "items": [{"start_sec": 0, "end_sec": 5}],
            })

            result = evaluate_no_skip_contract(root)

            self.assertFalse(result["pass"])
            rules = {item["rule"] for item in result["blocking"]}
            self.assertIn("rendered_product_qa_missing", rules)
            self.assertIn("title_effect_qa_lacks_rendered_frame_evidence", rules)

    def test_missing_pipeline_execution_trace_blocks_existing_rehearsal(self):
        fixture = Path(".tmp/copyedit_rehearsal_title_overlay_repair_20260708-181934/run")
        if not fixture.exists():
            self.skipTest("copyedit rehearsal fixture not present")

        result = evaluate_no_skip_contract(fixture)

        self.assertFalse(result["pass"])
        self.assertIn("pipeline_execution_trace.json", {
            item.get("artifact") for item in result["blocking"]
        })

    def test_pipeline_tool_generated_gates_with_rendered_qa_pass(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "final_copyedit_rehearsal.mp4").write_bytes(b"fake")
            _write_json(root, "pipeline_execution_trace.json", {
                "artifact_role": "pipeline_execution_trace",
                "entries": [
                    {
                        "artifact": "visual_selection_gate.json",
                        "classification": "pipeline_tool_generated",
                        "source_tool": "tools/visual_selection_gate.py",
                        "command": "tools/visual_selection_gate.py --run run --out-dir run",
                        "inputs": ["visual_selection_review.json"],
                        "outputs": ["visual_selection_gate.json"],
                    },
                    {
                        "artifact": "title_effect_lifecycle_qa.json",
                        "classification": "pipeline_tool_generated",
                        "source_tool": "tools/title_effect_lifecycle_qa.py",
                        "command": "tools/title_effect_lifecycle_qa.py --run run",
                        "inputs": ["title_effect_lifecycle_plan.json", "rendered_product_qa.json"],
                        "outputs": ["title_effect_lifecycle_qa.json"],
                    },
                    {
                        "artifact": "rendered_product_qa.json",
                        "classification": "pipeline_tool_generated",
                        "source_tool": "tools/rendered_product_qa.py",
                        "command": "tools/rendered_product_qa.py --run run",
                        "inputs": ["final_copyedit_rehearsal.mp4", "contact_sheet.jpg"],
                        "outputs": ["rendered_product_qa.json"],
                    },
                ],
            })
            _write_json(root, "visual_selection_gate.json", {
                "artifact_role": "visual_selection_gate",
                "pass": True,
                "generated_by": "tools/visual_selection_gate.py",
            })
            _write_json(root, "title_effect_lifecycle_qa.json", {
                "artifact_role": "title_effect_lifecycle_qa",
                "pass": True,
                "generated_by": "tools/title_effect_lifecycle_qa.py",
                "rendered_frame_evidence": ["contact_sheet.jpg"],
            })
            _write_json(root, "rendered_product_qa.json", {
                "artifact_role": "rendered_product_qa",
                "pass": True,
                "source_tool": "tools/rendered_product_qa.py",
                "frame_evidence": ["contact_sheet.jpg"],
                "contact_sheet": "contact_sheet.jpg",
            })

            result = evaluate_no_skip_contract(root)

            self.assertTrue(result["pass"])
            self.assertEqual(result["blocking"], [])

    def test_gate_authenticity_audit_classifies_unknown_artifact(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_json(root, "visual_selection_gate.json", {
                "artifact_role": "visual_selection_gate",
                "pass": True,
            })

            audit = audit_run_gate_authenticity(root)

            self.assertEqual(audit["artifacts"][0]["classification"], "unknown")


if __name__ == "__main__":
    unittest.main()
