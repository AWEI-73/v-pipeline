import json
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from video_pipeline_core.capability_execution import (
    discover_execution_companions,
    resolve_strict_contract,
    validate_execution_contract,
)
from video_pipeline_core.capability_catalog import load_live_catalog
from video_pipeline_core.no_skip_execution_trace import evaluate_no_skip_contract, write_strict_trace_audit


class ContractActivationTest(unittest.TestCase):
    def test_tracked_unique_companion_activates_strict_with_public_shape(self):
        with git_repository() as root:
            path, contract = commit_companion(root, "example", run_root=".tmp/example")

            result = resolve_strict_contract(root, root / ".tmp/example", path)

            self.assertEqual({
                "ok", "strict", "contract_path", "contract_sha256", "contract_source_commit",
                "run_root", "accountability_root", "contract", "errors",
            }, set(result))
            self.assertTrue(result["ok"], result)
            self.assertTrue(result["strict"])
            self.assertEqual(path, result["contract_path"])
            self.assertEqual(contract, result["contract"])
            self.assertRegex(result["contract_sha256"], r"^[0-9a-f]{64}$")
            self.assertRegex(result["contract_source_commit"], r"^[0-9a-f]{40}$")
            self.assertEqual(".tmp/example", result["run_root"])
            self.assertEqual(".tmp/example/accountability", result["accountability_root"])
            self.assertEqual([], result["errors"])

    def test_no_companion_preserves_legacy_behavior(self):
        with git_repository() as root:
            result = resolve_strict_contract(root, root / ".tmp/legacy", None)

            self.assertEqual({"ok": True, "strict": False, "contract_path": None, "contract_sha256": None,
                              "contract_source_commit": None, "run_root": ".tmp/legacy",
                              "accountability_root": ".tmp/legacy/accountability", "contract": {}, "errors": []}, result)

    def test_untracked_or_dirty_explicit_companion_is_rejected(self):
        with git_repository() as root:
            path = write_companion(root, "untracked", contract_for("untracked", ".tmp/untracked"))
            result = resolve_strict_contract(root, root / ".tmp/untracked", path)
            self.assertEqual(["contract_not_tracked"], error_codes(result))

            commit_all(root, "track companion")
            absolute = root / path
            absolute.write_text(json.dumps(contract_for("untracked", ".tmp/untracked", extra={"dirty": True})), encoding="utf-8")
            result = resolve_strict_contract(root, root / ".tmp/untracked", path)
            self.assertEqual(["contract_worktree_drift"], error_codes(result))

    def test_malformed_or_unsupported_invoked_companion_is_rejected(self):
        with git_repository() as root:
            path = write_raw_companion(root, "malformed", b"{not valid json}\n")
            commit_all(root, "malformed companion")
            self.assertEqual(["contract_json_invalid"], error_codes(resolve_strict_contract(root, root / ".tmp/malformed", path)))

        with git_repository() as root:
            path, _ = commit_companion(root, "unsupported", run_root=".tmp/unsupported", version=2)
            self.assertEqual(["contract_version_unsupported"], error_codes(resolve_strict_contract(root, root / ".tmp/unsupported", path)))

    def test_duplicate_work_order_identity_and_path_are_rejected(self):
        with git_repository() as root:
            first, _ = commit_companion(root, "first", work_order_id="same-id", work_order_path="docs/work.md", run_root=".tmp/first")
            write_companion(root, "second", contract_for("same-id", ".tmp/second", work_order_path="docs/other.md"))
            write_companion(root, "third", contract_for("other-id", ".tmp/third", work_order_path="docs/work.md"))
            commit_all(root, "duplicate companions")

            result = resolve_strict_contract(root, root / ".tmp/first", first)

            self.assertEqual(["contract_duplicate_work_order_id", "contract_duplicate_work_order_path"], error_codes(result))

    def test_case_variant_work_order_paths_are_duplicate_on_windows(self):
        with git_repository() as root:
            work_order = root / "docs/Work.md"
            work_order.parent.mkdir(parents=True, exist_ok=True)
            work_order.write_text("real work order\n", encoding="utf-8")
            first, _ = commit_companion(root, "first", work_order_path="docs/Work.md", run_root=".tmp/first")
            write_companion(root, "second", contract_for("second", ".tmp/second", work_order_path="docs/work.md"))
            commit_all(root, "case variant companions")

            result = resolve_strict_contract(root, root / ".tmp/first", first)

            self.assertEqual(["contract_duplicate_work_order_path"], error_codes(result))

    def test_conflicting_versions_in_one_identity_group_are_rejected(self):
        with git_repository() as root:
            first, _ = commit_companion(root, "first", work_order_id="same-id", run_root=".tmp/first", version=1)
            write_companion(root, "second", contract_for("same-id", ".tmp/second", work_order_path="docs/other.md", version=2))
            commit_all(root, "conflicting versions")

            result = resolve_strict_contract(root, root / ".tmp/first", first)

            self.assertEqual(["contract_duplicate_work_order_id", "contract_version_unsupported"], error_codes(result))

    def test_matching_run_root_activates_strict_without_cli_contract(self):
        with git_repository() as root:
            path, _ = commit_companion(root, "matched", run_root=".tmp/matched")

            result = resolve_strict_contract(root, root / ".tmp/matched", None)

            self.assertTrue(result["strict"], result)
            self.assertEqual(path, result["contract_path"])

    def test_run_root_conflict_and_strict_control_without_reference_fail_closed(self):
        with git_repository() as root:
            path, _ = commit_companion(root, "declared", run_root=".tmp/declared")
            result = resolve_strict_contract(root, root / ".tmp/other", path)
            self.assertEqual(["contract_run_root_conflict"], error_codes(result))

            control = root / ".tmp/uncontracted/accountability/receipts"
            control.mkdir(parents=True)
            (control / "attempt-1.json").write_text("{}", encoding="utf-8")
            result = resolve_strict_contract(root, root / ".tmp/uncontracted", None)
            self.assertEqual(["strict_contract_reference_missing"], error_codes(result))

    def test_strict_control_root_without_companion_requires_cli_contract(self):
        with git_repository() as root:
            (root / ".tmp/controlled/accountability").mkdir(parents=True)

            result = resolve_strict_contract(root, root / ".tmp/controlled", None)

            self.assertEqual(["strict_contract_argument_missing"], error_codes(result))

    def test_discovery_is_tracked_only_and_sorted(self):
        with git_repository() as root:
            first, _ = commit_companion(root, "z", run_root=".tmp/z")
            second = write_companion(root, "a", contract_for("a", ".tmp/a"))
            commit_all(root, "two companions")
            write_companion(root, "untracked", contract_for("untracked", ".tmp/untracked"))

            companions = discover_execution_companions(root)

            self.assertEqual(sorted([first, second]), [item["path"] for item in companions])


class ExecutionContractSchemaTest(unittest.TestCase):
    def test_registered_direct_tool_binds_argv_prefix_and_rejects_another_tool(self):
        contract = contract_for("direct-prefix", ".tmp/direct-prefix")
        contract["steps"][0]["command_argv"] = [
            "{python}", "tools/audio_mix_plan_execute.py", "--plan", "fixture.json"
        ]
        catalog = {"ok": True, "cards": [{
            "capability_id": "cap.example.operation.v1",
            "tool": "tools/audio_mix_plan_execute.py",
            "command": "tools/audio_mix_plan_execute.py",
            "execution_class": "deterministic",
            "capability_role": "operation",
        }]}

        self.assertEqual([], validate_execution_contract(Path.cwd(), contract, catalog))

        contract["steps"][0]["command_argv"][1] = "tools/material_rough_cut.py"
        errors = validate_execution_contract(Path.cwd(), contract, catalog)
        self.assertIn("contract_command_argv_mismatch", error_codes({"errors": errors}))

    def test_registered_video_tools_command_binds_subcommand_and_allows_frozen_tail(self):
        contract = contract_for("video-tools-prefix", ".tmp/video-tools-prefix")
        contract["steps"][0]["command_argv"] = [
            "{python}", "video_tools.py", "material-rough-cut", "--fixture", "value"
        ]
        catalog = {"ok": True, "cards": [{
            "capability_id": "cap.example.operation.v1",
            "tool": "video_tools.py material-rough-cut",
            "command": "video_tools.py material-rough-cut",
            "execution_class": "deterministic",
            "capability_role": "operation",
        }]}

        self.assertEqual([], validate_execution_contract(Path.cwd(), contract, catalog))

        contract["steps"][0]["command_argv"][2] = "audio-mix-plan-execute"
        errors = validate_execution_contract(Path.cwd(), contract, catalog)
        self.assertIn("contract_command_argv_mismatch", error_codes({"errors": errors}))

    def test_valid_contract_is_accepted_without_route_selection(self):
        contract = contract_for("valid", ".tmp/valid")
        catalog = {"ok": True, "cards": [{
            "capability_id": "cap.example.operation.v1",
            "command": "tools/example.py --run .tmp/valid",
            "execution_class": "deterministic",
            "capability_role": "operation",
        }]}

        self.assertEqual([], validate_execution_contract(Path.cwd(), contract, catalog))

    def test_schema_errors_are_sorted_and_reject_worker_selectable_argv(self):
        contract = contract_for("invalid", ".tmp/invalid")
        contract["steps"][0]["command_argv"] = ["{python}", "tools/example.py", "{route}"]
        contract["steps"].append({"step_id": "L1.example", "capability_id": "cap.missing.v1"})

        errors = validate_execution_contract(Path.cwd(), contract, {"ok": True, "cards": []})

        self.assertEqual(errors, sorted(errors, key=lambda item: (item["code"], item["path"], item["message"])))
        self.assertIn("contract_command_argv_invalid", error_codes({"errors": errors}))
        self.assertIn("contract_step_id_duplicate", error_codes({"errors": errors}))

    def test_step_inputs_require_object_canonical_path_and_sha256(self):
        contract = contract_for("invalid-inputs", ".tmp/invalid-inputs")
        contract["steps"][0]["inputs"] = [
            "not-an-object",
            {"path": "evidence/source.json"},
            {"path": "../escape.json", "sha256": "a" * 64},
            {"path": "evidence\\source.json", "sha256": "a" * 64},
            {"path": "/absolute.json", "sha256": "a" * 64},
            {"path": "evidence/source.json", "sha256": "A" * 64},
        ]

        errors = validate_execution_contract(Path.cwd(), contract, {
            "ok": True,
            "cards": [{
                "capability_id": "cap.example.operation.v1",
                "command": "tools/example.py --run .tmp/invalid-inputs",
                "execution_class": "deterministic",
                "capability_role": "operation",
            }],
        })

        self.assertEqual(errors, sorted(errors, key=lambda item: (item["code"], item["path"], item["message"])))
        self.assertEqual(
            [
                ("contract_path_invalid", "steps/0/inputs/2/path"),
                ("contract_path_invalid", "steps/0/inputs/3/path"),
                ("contract_path_invalid", "steps/0/inputs/4/path"),
                ("contract_step_input_invalid", "steps/0/inputs/0"),
                ("contract_step_input_invalid", "steps/0/inputs/1/sha256"),
                ("contract_step_input_invalid", "steps/0/inputs/5/sha256"),
            ],
            [(item["code"], item["path"]) for item in errors],
        )


class AccountabilityForwardFixtureTest(unittest.TestCase):
    def test_fixture_and_companion_schema(self):
        root = Path(__file__).resolve().parents[1]
        fixture_root = root / "tests/fixtures/accountability_forward_v1"
        manifest = json.loads((fixture_root / "fixture_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual("accountability_forward_fixture_manifest", manifest["artifact_role"])
        self.assertEqual(1, manifest["version"])
        for item in manifest["files"]:
            path = fixture_root / item["path"]
            self.assertTrue(path.is_file(), item["path"])
            self.assertEqual(item["sha256"], hash_bytes(path.read_bytes()), item["path"])
        self.assertNotIn("PLACEHOLDER", json.dumps(manifest))

        companion_path = root / "docs/construction-guides/work-orders/2026-07-13-single-entry-forward-accountability-acceptance.execution.json"
        contract = json.loads(companion_path.read_text(encoding="utf-8"))
        self.assertNotIn("PLACEHOLDER", json.dumps(contract))
        self.assertEqual("single-entry-forward-accountability-long-task", contract["work_order_id"])
        self.assertEqual(hash_bytes((root / contract["work_order_path"]).read_bytes()), contract["work_order_sha256"])
        self.assertEqual({"fixture.material-rough-cut", "fixture.audio-mix-plan-execute"}, {item["step_id"] for item in contract["steps"]})
        self.assertEqual({"fixture.technical-review", "owner.final"}, {item["requirement_id"] for item in contract["decision_requirements"]})
        self.assertFalse(contract["human_creative_approval"])
        self.assertFalse(contract["final_delivery_claimed"])
        self.assertEqual([], validate_execution_contract(root, contract, load_live_catalog(root / "skills")))
        for relative, expected in {item["path"]: item["sha256"] for item in contract["protected_paths"]}.items():
            path = root / relative
            self.assertTrue(path.is_file(), relative)
            self.assertEqual(expected, hash_bytes(path.read_bytes()), relative)


class AccountabilityNegativeFixtureTests(unittest.TestCase):
    def test_missing_required_step(self):
        from tests.test_capability_execution_receipts import execution_repository
        from video_pipeline_core.capability_execution import initialize_accountable_run, load_execution_contract, run_capability_step, validate_accountable_run_evidence

        with execution_repository() as (root, path):
            initialize_accountable_run(root, path)
            run = run_capability_step(root, path, "L1.example")
            contract = load_execution_contract(root, path)
            (root / run["receipt_path"]).unlink()
            result = validate_accountable_run_evidence(root, contract, load_live_catalog(root / "skills"))
            expected = json.loads((Path(__file__).resolve().parents[1] / "tests/fixtures/accountability_forward_v1/negative/missing-step/mutation.json").read_text(encoding="utf-8"))["expected_code"]

            self.assertIn(expected, error_codes(result))

    def test_self_authored_gate(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "visual_selection_gate.json").write_text(json.dumps({"artifact_role": "visual_selection_gate", "pass": True}), encoding="utf-8")
            (root / "pipeline_execution_trace.json").write_text(json.dumps({"entries": [{"artifact": "visual_selection_gate.json", "classification": "run_local_worker_generated"}]}), encoding="utf-8")
            result = evaluate_no_skip_contract(root)
            expected = json.loads((Path(__file__).resolve().parents[1] / "tests/fixtures/accountability_forward_v1/negative/self-authored-gate/mutation.json").read_text(encoding="utf-8"))["expected_code"]

            self.assertIn(expected, {item["rule"] for item in result["blocking"]})

    def test_stale_agent_sidecar(self):
        from tests.test_capability_execution_receipts import execution_repository
        from tests.test_no_skip_execution_trace import _add_decision_requirements
        from video_pipeline_core.capability_execution import initialize_accountable_run, load_execution_contract, run_capability_step

        with execution_repository() as (root, path):
            _add_decision_requirements(root, path)
            initialize_accountable_run(root, path)
            run = run_capability_step(root, path, "L1.example")
            contract = load_execution_contract(root, path)
            write_agent_sidecar(root, path, contract, run, stale=True)
            result = write_strict_trace_audit(root, path, root / contract["run_root"], root / contract["accountability_root"])
            expected = json.loads((Path(__file__).resolve().parents[1] / "tests/fixtures/accountability_forward_v1/negative/stale-agent-sidecar/mutation.json").read_text(encoding="utf-8"))["expected_code"]

            self.assertIn(expected, error_codes(result))

    def test_copied_owner_sidecar(self):
        from tests.test_capability_execution_receipts import execution_repository
        from tests.test_no_skip_execution_trace import _add_decision_requirements
        from video_pipeline_core.capability_execution import initialize_accountable_run, load_execution_contract, run_capability_step

        with execution_repository() as (root, path):
            _add_decision_requirements(root, path)
            initialize_accountable_run(root, path)
            run = run_capability_step(root, path, "L1.example")
            contract = load_execution_contract(root, path)
            write_agent_sidecar(root, path, contract, run)
            write_owner_sidecar(root, path, contract, run, copied=True)
            result = write_strict_trace_audit(root, path, root / contract["run_root"], root / contract["accountability_root"])
            expected = json.loads((Path(__file__).resolve().parents[1] / "tests/fixtures/accountability_forward_v1/negative/copied-owner-sidecar/mutation.json").read_text(encoding="utf-8"))["expected_code"]

            self.assertIn(expected, error_codes(result))


def git_repository():
    return _GitRepository()


class _GitRepository:
    def __enter__(self):
        self._tmp = TemporaryDirectory()
        self.root = Path(self._tmp.name)
        git(self.root, "init")
        git(self.root, "config", "user.email", "tests@example.invalid")
        git(self.root, "config", "user.name", "Task Seven Tests")
        git(self.root, "config", "core.autocrlf", "false")
        (self.root / "README.md").write_text("fixture\n", encoding="utf-8")
        commit_all(self.root, "initial")
        return self.root

    def __exit__(self, *args):
        self._tmp.cleanup()


def git(root, *args):
    return subprocess.run(["git", *args], cwd=root, check=True, text=True, capture_output=True)


def commit_all(root, message):
    git(root, "add", ".")
    git(root, "commit", "-m", message)


def write_companion(root, name, contract):
    path = f"docs/construction-guides/work-orders/{name}.execution.json"
    absolute = root / path
    absolute.parent.mkdir(parents=True, exist_ok=True)
    absolute.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def write_raw_companion(root, name, content):
    path = f"docs/construction-guides/work-orders/{name}.execution.json"
    absolute = root / path
    absolute.parent.mkdir(parents=True, exist_ok=True)
    absolute.write_bytes(content)
    return path


def commit_companion(root, name, **kwargs):
    work_order_id = kwargs.pop("work_order_id", name)
    path = write_companion(root, name, contract_for(work_order_id, kwargs.pop("run_root"), **kwargs))
    commit_all(root, f"add {name} companion")
    return path, json.loads((root / path).read_text(encoding="utf-8"))


def contract_for(work_order_id, run_root, *, work_order_path=None, version=1, extra=None):
    contract = {
        "artifact_role": "work_order_execution_contract",
        "version": 1,
        "accountability_contract_version": version,
        "work_order_id": work_order_id,
        "work_order_path": work_order_path or f"docs/construction-guides/work-orders/{work_order_id}.md",
        "work_order_sha256": "a" * 64,
        "run_root": run_root,
        "accountability_root": f"{run_root}/accountability",
        "initial_run_root_manifest": [],
        "initial_owner_zone_manifest": [],
        "steps": [{
            "step_id": "L1.example",
            "loop": "L1",
            "capability_id": "cap.example.operation.v1",
            "depends_on": [],
            "command_argv": ["{python}", "tools/example.py", "--run", run_root],
            "timeout_ms": 1000,
            "inputs": [],
            "required_outputs": [f"{run_root}/output.json"],
            "required_verifier_step_ids": [],
            "max_attempts": 1,
            "allowed_retry_failure_classes": [],
        }],
        "decision_requirements": [],
        "allowed_owner_zones": [{"path": run_root, "match": "directory_prefix"}],
        "forbidden_paths": [],
        "protected_paths": [],
        "human_creative_approval": False,
        "final_delivery_claimed": False,
    }
    contract.update(extra or {})
    return contract


def error_codes(result):
    return [item["code"] for item in result["errors"]]


def hash_bytes(value):
    import hashlib
    return hashlib.sha256(value).hexdigest()


def write_agent_sidecar(root, path, contract, run, *, stale=False):
    reference = json.loads((root / contract["accountability_root"] / "contract_reference.json").read_text(encoding="utf-8"))
    receipt = json.loads((root / run["receipt_path"]).read_text(encoding="utf-8"))
    payload = {
        "artifact_role": "agent_attestation",
        "version": 1,
        "run_instance_id": "00000000-0000-4000-8000-000000000000" if stale else reference["run_instance_id"],
        "execution_contract_path": path,
        "execution_contract_sha256": "0" * 64 if stale else reference["contract_sha256"],
        "requirement_id": "fixture.review",
        "step_id": "L1.example",
        "capability_id": "cap.example.child.v1",
        "actor_type": "agent",
        "agent_run_id": "test-agent",
        "reviewed_evidence": [{"path": ".tmp/example/output.txt", "sha256": hash_bytes((root / ".tmp/example/output.txt").read_bytes()), "locator": "test"}],
        "dependency_receipts": [{"step_id": "L1.example", "path": run["receipt_path"], "sha256": run["receipt_sha256"], "completed_at": receipt["completed_at"]}],
        "judgment": "bounded test evidence",
        "blind_spots": ["synthetic fixture"],
        "proposed_findings": [],
        "attested_at": "2999-01-01T00:00:00+00:00",
    }
    target = root / contract["accountability_root"] / "attestations/fixture.review.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_owner_sidecar(root, path, contract, run, *, copied=False):
    reference = json.loads((root / contract["accountability_root"] / "contract_reference.json").read_text(encoding="utf-8"))
    receipt = json.loads((root / run["receipt_path"]).read_text(encoding="utf-8"))
    payload = {
        "artifact_role": "owner_decision",
        "version": 1,
        "run_instance_id": "00000000-0000-4000-8000-000000000000" if copied else reference["run_instance_id"],
        "execution_contract_path": path,
        "execution_contract_sha256": "0" * 64 if copied else reference["contract_sha256"],
        "requirement_id": "owner.final",
        "dependency_receipts": [{"step_id": "L1.example", "path": run["receipt_path"], "sha256": run["receipt_sha256"], "completed_at": receipt["completed_at"]}],
        "scope": "fixture accountability",
        "decision": "approve",
        "evidence_refs": [{"path": ".tmp/example/output.txt", "sha256": hash_bytes((root / ".tmp/example/output.txt").read_bytes()), "locator": "test"}],
        "verbatim_owner_text": "fixture owner text",
        "decided_at": "2999-01-01T00:00:00+00:00",
    }
    target = root / contract["accountability_root"] / "verdicts/owner.final.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
