import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from video_pipeline_core.capability_execution import (
    compare_manifest_chain,
    hash_file,
    initialize_accountable_run,
    load_execution_contract,
    reserve_attempt,
    run_capability_step,
    snapshot_monitored_state,
    validate_accountable_run_evidence,
)
from video_pipeline_core.capability_catalog import load_live_catalog

from tests.test_capability_execution_contract import commit_all, contract_for, git, git_repository, write_companion


class AccountableInitializationTest(unittest.TestCase):
    def test_initialization_publishes_immutable_reference_and_refuses_overwrite(self):
        with execution_repository() as (root, path):
            result = initialize_accountable_run(root, path)

            self.assertTrue(result["ok"], result)
            reference_path = root / ".tmp/example/accountability/contract_reference.json"
            reference = json.loads(reference_path.read_text(encoding="utf-8"))
            self.assertEqual({
                "artifact_role", "version", "run_instance_id", "run_root", "contract_path",
                "contract_sha256", "contract_source_commit", "initialized_at",
            }, set(reference))
            self.assertEqual("accountability_contract_reference", reference["artifact_role"])
            self.assertEqual(1, reference["version"])
            self.assertRegex(reference["run_instance_id"], r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
            self.assertEqual(path, reference["contract_path"])
            self.assertEqual(hash_file(root / path), reference["contract_sha256"])
            self.assertRegex(reference["contract_source_commit"], r"^[0-9a-f]{40}$")
            self.assertEqual(".tmp/example", reference["run_root"])

            second = initialize_accountable_run(root, path)
            self.assertFalse(second["ok"], second)
            self.assertEqual(["accountability_run_already_initialized"], error_codes(second))


class AccountableReservationTest(unittest.TestCase):
    def test_reservation_is_exclusive_and_stale_reservation_is_unknown(self):
        with execution_repository() as (root, path):
            initialize_accountable_run(root, path)
            contract = load_execution_contract(root, path)

            first = reserve_attempt(root, contract, "L1.example")
            self.assertTrue(first["ok"], first)
            self.assertEqual(1, first["attempt"])
            reservation_path = root / first["reservation_path"]
            reservation = json.loads(reservation_path.read_text(encoding="utf-8"))
            self.assertEqual({
                "artifact_role", "version", "run_instance_id", "contract_path", "contract_sha256",
                "step_id", "capability_id", "attempt", "argv_sha256", "process_id", "started_at",
            }, set(reservation))
            self.assertEqual(1, reservation["attempt"])
            self.assertRegex(reservation["argv_sha256"], r"^[0-9a-f]{64}$")

            second = reserve_attempt(root, contract, "L1.example")
            self.assertFalse(second["ok"], second)
            self.assertEqual("unknown", second["status"])
            self.assertEqual(["accountability_stale_reservation"], error_codes(second))


class AccountableManifestTest(unittest.TestCase):
    def test_snapshots_keep_deleted_tombstones_and_exclude_control_subtree(self):
        with execution_repository() as (root, path):
            initialize_accountable_run(root, path)
            input_path = root / ".tmp/example/input.txt"
            input_path.parent.mkdir(parents=True, exist_ok=True)
            input_path.write_text("input\n", encoding="utf-8")
            contract = load_execution_contract(root, path)
            contract["initial_run_root_manifest"] = [{
                "path": ".tmp/example/input.txt",
                "state": "present",
                "sha256": hash_file(input_path),
            }]

            before = snapshot_monitored_state(root, contract, scope="production")
            self.assertEqual([".tmp/example/input.txt"], [item["path"] for item in before["files"]])
            control = root / ".tmp/example/accountability/child-write.json"
            control.parent.mkdir(parents=True, exist_ok=True)
            control.write_text("control\n", encoding="utf-8")
            self.assertNotIn(".tmp/example/accountability/child-write.json", {item["path"] for item in before["files"]})

            input_path.unlink()
            after = snapshot_monitored_state(root, contract, scope="production")
            self.assertEqual({"path": ".tmp/example/input.txt", "state": "deleted", "sha256": None}, after["files"][0])
            errors = compare_manifest_chain(before, after)
            self.assertEqual(["manifest_file_deleted"], error_codes({"errors": errors}))

    def test_exact_directory_owner_zone_is_monitored(self):
        with execution_repository() as (root, path):
            initialize_accountable_run(root, path)
            exact_file = root / "owner-zone/evidence.txt"
            exact_file.parent.mkdir(parents=True, exist_ok=True)
            exact_file.write_text("evidence\n", encoding="utf-8")
            contract = load_execution_contract(root, path)
            contract["allowed_owner_zones"] = [{"path": "owner-zone", "match": "exact"}]

            snapshot = snapshot_monitored_state(root, contract, scope="production")

            self.assertIn("owner-zone/evidence.txt", {item["path"] for item in snapshot["files"]})


class AccountableExecutionTest(unittest.TestCase):
    def test_one_step_execution_writes_frozen_pass_receipt_and_evidence_validator_is_pure(self):
        with execution_repository() as (root, path):
            initialize_accountable_run(root, path)
            contract = load_execution_contract(root, path)
            before = sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())

            result = run_capability_step(root, path, "L1.example")

            self.assertTrue(result["ok"], result)
            self.assertEqual("pass", result["status"])
            receipt_path = root / result["receipt_path"]
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            self.assertEqual({
                "artifact_role", "version", "run_instance_id", "contract_path", "contract_sha256",
                "step_id", "capability_id", "attempt", "reservation_path", "reservation_sha256",
                "command_argv", "started_at", "completed_at", "duration_sec", "exit_code", "status",
                "failure_class", "retryable", "input_hashes", "output_hashes", "changed_paths",
                "pre_manifest_path", "pre_manifest_sha256", "post_manifest_path", "post_manifest_sha256",
                "source_tool", "depends_on_step_ids", "dependency_receipt_hashes",
            }, set(receipt))
            self.assertEqual("pass", receipt["status"])
            self.assertEqual([], receipt["depends_on_step_ids"])
            self.assertEqual({}, receipt["dependency_receipt_hashes"])
            self.assertEqual([sys.executable, "tools/child.py", "--out", ".tmp/example/output.txt"], receipt["command_argv"])
            self.assertRegex(receipt["output_hashes"][".tmp/example/output.txt"], r"^[0-9a-f]{64}$")
            self.assertRegex(receipt["input_hashes"]["inputs/source.txt"], r"^[0-9a-f]{64}$")
            self.assertTrue((root / ".tmp/example/output.txt").is_file())

            evidence = validate_accountable_run_evidence(root, contract, load_live_catalog(root / "skills"))
            self.assertEqual({"ok", "tool_entries", "decision_entries", "final_state", "errors", "warnings"}, set(evidence))
            self.assertTrue(evidence["ok"], evidence)
            self.assertEqual("PASS", evidence["final_state"])
            after = sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())
            self.assertNotEqual(before, after)

    def test_input_hash_is_frozen_before_child_launch(self):
        with execution_repository() as (root, path):
            initialize_accountable_run(root, path)
            (root / "inputs/source.txt").write_text("drifted\n", encoding="utf-8")

            result = run_capability_step(root, path, "L1.example")

            self.assertFalse(result["ok"], result)
            self.assertEqual(["accountability_input_hash_mismatch"], error_codes(result))
            self.assertFalse((root / ".tmp/example/output.txt").exists())

    def test_child_control_write_is_structural_and_not_a_pass(self):
        with execution_repository() as (root, path):
            initialize_accountable_run(root, path)
            child = root / "tools/child.py"
            child.write_text(
                child.read_text(encoding="utf-8") +
                "Path('.tmp/example/accountability/forbidden.json').write_text('forbidden', encoding='utf-8')\n",
                encoding="utf-8",
            )

            result = run_capability_step(root, path, "L1.example")

            self.assertFalse(result["ok"], result)
            self.assertEqual("stopped", result["status"])
            self.assertEqual(["STRUCTURAL_CHILD_CONTROL_WRITE"], [result["failure_class"]])

    def test_declared_control_output_is_allowed_for_a_control_writer_step(self):
        with execution_repository() as (root, path):
            contract_path = root / path
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
            contract["steps"][0]["command_argv"] = [
                "{python}", "tools/child.py", "--out", ".tmp/example/accountability/declared.json",
            ]
            contract["steps"][0]["required_outputs"] = [
                ".tmp/example/accountability/declared.json",
            ]
            contract_path.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
            skill_path = root / "skills/example.md"
            skill = json.loads(skill_path.read_text(encoding="utf-8").split("\n", 1)[1].rsplit("\n", 2)[0])
            skill["canonical_tools"][0]["command"] = "tools/child.py --out .tmp/example/accountability/declared.json"
            skill_path.write_text(
                "<!-- TOOL_CONTRACT_START -->\n" + json.dumps(skill, indent=2)
                + "\n<!-- TOOL_CONTRACT_END -->\n",
                encoding="utf-8",
            )
            commit_all(root, "declare control output fixture")
            initialized = initialize_accountable_run(root, path)
            self.assertTrue(initialized["ok"], initialized)

            result = run_capability_step(root, path, "L1.example")

            self.assertTrue(result["ok"], result)
            self.assertTrue((root / ".tmp/example/accountability/declared.json").is_file())

    def test_process_uses_repo_cwd_and_shell_false(self):
        with execution_repository() as (root, path):
            initialize_accountable_run(root, path)
            original = subprocess.run
            calls = []

            def record(*args, **kwargs):
                calls.append((args, kwargs))
                return original(*args, **kwargs)

            with patch("video_pipeline_core.capability_execution.subprocess.run", side_effect=record):
                result = run_capability_step(root, path, "L1.example")

            self.assertTrue(result["ok"], result)
            child_calls = [item for item in calls if item[0] and isinstance(item[0][0], list) and "tools/child.py" in item[0][0]]
            self.assertEqual(1, len(child_calls))
            self.assertFalse(child_calls[0][1]["shell"])
            self.assertEqual(root, child_calls[0][1]["cwd"])
            self.assertEqual(1.0, child_calls[0][1]["timeout"])

    def test_nonzero_step_cannot_be_retried_without_contract_allowance(self):
        with execution_repository() as (root, path):
            initialize_accountable_run(root, path)
            child = root / "tools/child.py"
            child.write_text("raise SystemExit(3)\n", encoding="utf-8")

            first = run_capability_step(root, path, "L1.example")
            second = run_capability_step(root, path, "L1.example")

            self.assertFalse(first["ok"], first)
            self.assertEqual("fail", first["status"])
            self.assertFalse(second["ok"], second)
            self.assertEqual(["accountability_retry_not_allowed"], error_codes(second))

    def test_child_receipt_records_exact_parent_receipt_path_and_hash(self):
        with two_step_execution_repository() as (root, path):
            initialize_accountable_run(root, path)
            parent = run_capability_step(root, path, "L1.example")
            child = run_capability_step(root, path, "L2.child")

            self.assertTrue(parent["ok"], parent)
            self.assertTrue(child["ok"], child)
            receipt = json.loads((root / child["receipt_path"]).read_text(encoding="utf-8"))
            self.assertEqual(["L1.example"], receipt["depends_on_step_ids"])
            self.assertEqual(
                {"L1.example": {"path": parent["receipt_path"], "sha256": parent["receipt_sha256"]}},
                receipt["dependency_receipt_hashes"],
            )

    def test_missing_or_non_pass_parent_prevents_child_execution(self):
        with two_step_execution_repository() as (root, path):
            initialize_accountable_run(root, path)
            missing = run_capability_step(root, path, "L2.child")
            self.assertFalse(missing["ok"], missing)
            self.assertEqual(["accountability_dependency_missing"], error_codes(missing))

        with two_step_execution_repository() as (root, path):
            initialize_accountable_run(root, path)
            child = root / "tools/child.py"
            child.write_text("raise SystemExit(3)\n", encoding="utf-8")
            parent = run_capability_step(root, path, "L1.example")
            blocked = run_capability_step(root, path, "L2.child")
            self.assertFalse(parent["ok"], parent)
            self.assertFalse(blocked["ok"], blocked)
            self.assertEqual(["accountability_dependency_not_pass"], error_codes(blocked))

    def test_strict_closure_rejects_tampered_parent_receipt_after_child_execution(self):
        from video_pipeline_core.no_skip_execution_trace import write_strict_trace_audit

        with two_step_execution_repository() as (root, path):
            initialize_accountable_run(root, path)
            run_capability_step(root, path, "L1.example")
            child = run_capability_step(root, path, "L2.child")
            parent_path = root / ".tmp/example/accountability/receipts/L1.example/attempt-1.json"
            parent = json.loads(parent_path.read_text(encoding="utf-8"))
            parent["tampered_after_child"] = True
            parent_path.write_text(json.dumps(parent, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            contract = load_execution_contract(root, path)

            result = write_strict_trace_audit(root, path, root / contract["run_root"], root / contract["accountability_root"])

            self.assertFalse(result["ok"], result)
            self.assertIn("accountability_dependency_receipt_hash_mismatch", error_codes(result))
            self.assertTrue((root / child["receipt_path"]).is_file())

    def test_new_strict_run_fails_closed_when_child_dependency_fields_are_missing(self):
        from video_pipeline_core.no_skip_execution_trace import write_strict_trace_audit

        with two_step_execution_repository() as (root, path):
            initialize_accountable_run(root, path)
            run_capability_step(root, path, "L1.example")
            child = run_capability_step(root, path, "L2.child")
            child_path = root / child["receipt_path"]
            child_receipt = json.loads(child_path.read_text(encoding="utf-8"))
            child_receipt.pop("depends_on_step_ids", None)
            child_receipt.pop("dependency_receipt_hashes", None)
            child_path.write_text(json.dumps(child_receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            contract = load_execution_contract(root, path)

            result = write_strict_trace_audit(root, path, root / contract["run_root"], root / contract["accountability_root"])

            self.assertFalse(result["ok"], result)
            self.assertIn("accountability_dependency_receipt_hash_missing", error_codes(result))

    def test_legacy_non_strict_run_remains_accepted_without_dependency_fields(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = resolve_legacy_run(root)
            self.assertFalse(result["strict"])
            self.assertEqual([], result["errors"])


def resolve_legacy_run(root: Path):
    from video_pipeline_core.capability_execution import resolve_strict_contract
    return resolve_strict_contract(root, root / "legacy", None)


def execution_repository():
    context = _ExecutionRepository()
    return context


class _ExecutionRepository:
    def __enter__(self):
        self._tmp = TemporaryDirectory()
        self.root = Path(self._tmp.name)
        git(self.root, "init")
        git(self.root, "config", "user.email", "tests@example.invalid")
        git(self.root, "config", "user.name", "Task Eight Tests")
        git(self.root, "config", "core.autocrlf", "false")
        (self.root / "README.md").write_text("fixture\n", encoding="utf-8")
        (self.root / "tools").mkdir()
        (self.root / "tools/child.py").write_text(
            "from pathlib import Path\n"
            "import argparse\n"
            "parser = argparse.ArgumentParser()\n"
            "parser.add_argument('--out', required=True)\n"
            "args = parser.parse_args()\n"
            "path = Path(args.out)\n"
            "path.parent.mkdir(parents=True, exist_ok=True)\n"
            "path.write_text('child output\\n', encoding='utf-8')\n",
            encoding="utf-8",
        )
        (self.root / "skills").mkdir()
        skill = {
            "version": 1,
            "skill": "example",
            "stage_owner": "stage1",
            "capability_namespace": "cap.example",
            "capability_lookup_owner": "example",
            "triggers": ["run"],
            "forbidden_tools": [],
            "canonical_tools": [{
                "tool": "tools/child.py",
                "command": "tools/child.py --out .tmp/example/output.txt",
                "when": "run",
                "inputs": [],
                "outputs": [".tmp/example/output.txt"],
                "stop_if": [],
                "capability_id": "cap.example.child.v1",
                "execution_class": "deterministic",
                "capability_role": "operation",
                "loops": ["L1"],
                "maturity": "experimental",
            }],
        }
        (self.root / "skills/example.md").write_text(
            "<!-- TOOL_CONTRACT_START -->\n" + json.dumps(skill, indent=2) +
            "\n<!-- TOOL_CONTRACT_END -->\n",
            encoding="utf-8",
        )
        (self.root / "docs/construction-guides/work-orders").mkdir(parents=True)
        work_order = self.root / "docs/work.md"
        work_order.parent.mkdir(parents=True, exist_ok=True)
        work_order.write_text("work order\n", encoding="utf-8")
        input_file = self.root / "inputs/source.txt"
        input_file.parent.mkdir(parents=True, exist_ok=True)
        input_file.write_text("source\n", encoding="utf-8")
        contract = contract_for("example", ".tmp/example", work_order_path="docs/work.md")
        contract["work_order_sha256"] = hashlib.sha256(work_order.read_bytes()).hexdigest()
        contract["steps"][0].update({
            "capability_id": "cap.example.child.v1",
            "command_argv": ["{python}", "tools/child.py", "--out", ".tmp/example/output.txt"],
            "inputs": [{"path": "inputs/source.txt", "sha256": hashlib.sha256(input_file.read_bytes()).hexdigest()}],
            "required_outputs": [".tmp/example/output.txt"],
        })
        self.path = write_companion(self.root, "example", contract)
        commit_all(self.root, "initial task eight execution repository")
        return self.root, self.path

    def __exit__(self, *args):
        self._tmp.cleanup()


def error_codes(result):
    return [item["code"] for item in result.get("errors", [])]


class _TwoStepExecutionRepository:
    def __enter__(self):
        self._context = execution_repository()
        self.root, self.path = self._context.__enter__()
        skill_path = self.root / "skills/example.md"
        skill = json.loads(skill_path.read_text(encoding="utf-8").split("\n", 1)[1].rsplit("\n", 2)[0])
        skill["canonical_tools"].append({
            "tool": "tools/child.py",
            "command": "tools/child.py --out .tmp/example/child-output.txt",
            "when": "run child",
            "inputs": [],
            "outputs": [".tmp/example/child-output.txt"],
            "stop_if": [],
            "capability_id": "cap.example.child-two.v1",
            "execution_class": "deterministic",
            "capability_role": "operation",
            "loops": ["L1"],
            "maturity": "experimental",
        })
        skill_path.write_text(
            "<!-- TOOL_CONTRACT_START -->\n" + json.dumps(skill, indent=2) +
            "\n<!-- TOOL_CONTRACT_END -->\n",
            encoding="utf-8",
        )
        companion = self.root / self.path
        contract = json.loads(companion.read_text(encoding="utf-8"))
        contract["steps"].append({
            "step_id": "L2.child",
            "loop": "L1",
            "capability_id": "cap.example.child-two.v1",
            "depends_on": ["L1.example"],
            "command_argv": ["{python}", "tools/child.py", "--out", ".tmp/example/child-output.txt"],
            "timeout_ms": 1000,
            "inputs": [],
            "required_outputs": [".tmp/example/child-output.txt"],
            "required_verifier_step_ids": [],
            "max_attempts": 1,
            "allowed_retry_failure_classes": [],
        })
        companion.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        commit_all(self.root, "add two-step receipt lineage fixture")
        return self.root, self.path

    def __exit__(self, *args):
        return self._context.__exit__(*args)


def two_step_execution_repository():
    return _TwoStepExecutionRepository()


if __name__ == "__main__":
    unittest.main()
