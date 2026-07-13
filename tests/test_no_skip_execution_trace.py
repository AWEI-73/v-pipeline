import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from video_pipeline_core.no_skip_execution_trace import (
    audit_run_gate_authenticity,
    evaluate_no_skip_contract,
    write_strict_trace_audit,
)
from tests.test_capability_execution_receipts import execution_repository
from tests.test_capability_execution_contract import commit_all
from video_pipeline_core.capability_execution import initialize_accountable_run, load_execution_contract, run_capability_step


def _write_json(root: Path, name: str, payload: dict) -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


class NoSkipExecutionTraceTest(unittest.TestCase):
    def test_strict_cli_returns_zero_for_ok_waiting_owner_result(self):
        import tools.no_skip_execution_trace as no_skip_cli

        with patch.object(
            no_skip_cli,
            "write_strict_trace_audit",
            return_value={"ok": True, "final_state": "WAITING_OWNER_ACCOUNTABILITY_FIXTURE"},
        ), patch.object(
            no_skip_cli.sys,
            "argv",
            [
                "no_skip_execution_trace.py",
                "--contract", "contract.json",
                "--run", "run",
                "--out-dir", "out",
            ],
        ):
            self.assertEqual(0, no_skip_cli.main())

    def test_strict_closure_derives_v2_trace_and_decision_without_legacy_fallback(self):
        with execution_repository() as (root, path):
            initialize_accountable_run(root, path)
            run_capability_step(root, path, "L1.example")
            contract = load_execution_contract(root, path)
            out_dir = root / contract["accountability_root"]

            result = write_strict_trace_audit(root, path, root / contract["run_root"], out_dir)

            self.assertTrue(result["ok"], result)
            self.assertEqual("PASS", result["final_state"])
            trace = json.loads((out_dir / "pipeline_execution_trace.json").read_text(encoding="utf-8"))
            self.assertEqual(2, trace["version"])
            self.assertIn("tool_entries", trace)
            self.assertIn("decision_entries", trace)
            self.assertFalse((root / contract["run_root"] / "pipeline_execution_trace.json").exists())

    def test_strict_agent_sidecar_binds_receipt_and_missing_owner_waits(self):
        with execution_repository() as (root, path):
            _add_decision_requirements(root, path)
            initialize_accountable_run(root, path)
            run = run_capability_step(root, path, "L1.example")
            contract = load_execution_contract(root, path)
            reference = json.loads((root / contract["accountability_root"] / "contract_reference.json").read_text(encoding="utf-8"))
            receipt_path = root / run["receipt_path"]
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            dependency = {
                "step_id": "L1.example",
                "path": run["receipt_path"],
                "sha256": run["receipt_sha256"],
                "completed_at": receipt["completed_at"],
            }
            _write_json(root, "".join([contract["accountability_root"], "/attestations/fixture.review.json"]), {
                "artifact_role": "agent_attestation",
                "version": 1,
                "run_instance_id": reference["run_instance_id"],
                "execution_contract_path": path,
                "execution_contract_sha256": reference["contract_sha256"],
                "requirement_id": "fixture.review",
                "step_id": "L1.example",
                "capability_id": "cap.example.child.v1",
                "actor_type": "agent",
                "agent_run_id": "test-agent-run",
                "reviewed_evidence": [{"path": ".tmp/example/output.txt", "sha256": hash_file(root / ".tmp/example/output.txt"), "locator": "test"}],
                "dependency_receipts": [dependency],
                "judgment": "bounded test evidence is present",
                "blind_spots": ["synthetic child only"],
                "proposed_findings": [],
                "attested_at": "2999-01-01T00:00:00+00:00",
            })

            result = write_strict_trace_audit(root, path, root / contract["run_root"], root / contract["accountability_root"])

            self.assertTrue(result["ok"], result)
            self.assertEqual("WAITING_OWNER_ACCOUNTABILITY_FIXTURE", result["final_state"])
            self.assertNotIn("receipt_path", result["decision_entries"][0])

    def test_strict_stale_agent_sidecar_is_blocking(self):
        with execution_repository() as (root, path):
            _add_decision_requirements(root, path)
            initialize_accountable_run(root, path)
            run = run_capability_step(root, path, "L1.example")
            contract = load_execution_contract(root, path)
            _write_json(root, contract["accountability_root"] + "/attestations/fixture.review.json", {
                "artifact_role": "agent_attestation",
                "version": 1,
                "run_instance_id": "00000000-0000-4000-8000-000000000000",
                "execution_contract_path": path,
                "execution_contract_sha256": "0" * 64,
                "requirement_id": "fixture.review",
                "step_id": "L1.example",
                "capability_id": "cap.example.child.v1",
                "actor_type": "agent",
                "agent_run_id": "stale",
                "reviewed_evidence": [{"path": ".tmp/example/output.txt", "sha256": hash_file(root / ".tmp/example/output.txt"), "locator": "test"}],
                "dependency_receipts": [{"step_id": "L1.example", "path": run["receipt_path"], "sha256": run["receipt_sha256"], "completed_at": "2999-01-01T00:00:00+00:00"}],
                "judgment": "stale",
                "blind_spots": ["stale"],
                "proposed_findings": [],
                "attested_at": "2999-01-01T00:00:00+00:00",
            })

            result = write_strict_trace_audit(root, path, root / contract["run_root"], root / contract["accountability_root"])

            self.assertFalse(result["ok"], result)
            self.assertIn("stale_agent_decision_sidecar", {item["code"] for item in result["errors"]})

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


def hash_file(path: Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _add_decision_requirements(root: Path, path: str) -> None:
    companion = root / path
    payload = json.loads(companion.read_text(encoding="utf-8"))
    payload["decision_requirements"] = [
        {
            "requirement_id": "fixture.review",
            "actor_class": "agent",
            "depends_on_step_ids": ["L1.example"],
            "evidence_path": payload["accountability_root"] + "/attestations/fixture.review.json",
            "missing_state": "UNKNOWN_AGENT_EVIDENCE",
        },
        {
            "requirement_id": "owner.final",
            "actor_class": "owner",
            "depends_on_step_ids": ["L1.example"],
            "evidence_path": payload["accountability_root"] + "/verdicts/owner.final.json",
            "missing_state": "WAITING_OWNER_ACCOUNTABILITY_FIXTURE",
        },
    ]
    companion.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    commit_all(root, "add strict decision requirements")
