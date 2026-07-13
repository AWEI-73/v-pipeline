"""Committed, fail-closed activation rules for accountable capability runs.

This module deliberately validates frozen contracts and their repository paths;
it does not select a route or execute a capability.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_COMPANION_GLOB = "docs/construction-guides/work-orders/*.execution.json"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_DRIVE_RE = re.compile(r"^[A-Za-z]:")
_CONTROL_NAMES = {"contract_reference.json", "receipts", "reservations", "attestations", "verdicts"}
_REFERENCE_NAME = "contract_reference.json"
_ATTEMPT_RE = re.compile(r"^attempt-(\d+)\.json$")


class ExecutionContractError(ValueError):
    """A committed execution companion could not be loaded safely."""

    def __init__(self, errors: list[dict[str, str]]):
        self.errors = _sorted_errors(errors)
        super().__init__(self.errors[0]["message"] if self.errors else "execution contract error")


def canonical_json_bytes(payload: dict, *, self_hash_field: str | None = None) -> bytes:
    """Serialize a JSON object in the contract's deterministic hash form."""
    if not isinstance(payload, dict):
        raise TypeError("canonical JSON payload must be an object")
    value = dict(payload)
    if self_hash_field is not None:
        value.pop(self_hash_field, None)
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def hash_file(path: Path) -> str:
    """Return the SHA-256 of a file's exact bytes."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def initialize_accountable_run(repo_root: Path, contract_path: Path) -> dict:
    """Create the one immutable contract reference for a strict run."""
    root = Path(repo_root).resolve()
    try:
        requested = _coerce_repo_path(root, contract_path)
    except ValueError as exc:
        return _failure("contract_not_tracked", str(contract_path), str(exc))
    record = next((item for item in discover_execution_companions(root) if item["path"] == requested), None)
    if record is None:
        return _failure("contract_not_tracked", requested, "contract companion is not tracked in HEAD")
    if record["errors"]:
        return {"ok": False, "errors": record["errors"]}
    contract = dict(record["contract"])
    run = contract.get("run_root")
    if not isinstance(run, str):
        return _failure("contract_field_invalid", "run_root", "contract run_root is invalid")
    activation = resolve_strict_contract(root, root / run, requested)
    if not activation["ok"]:
        return {"ok": False, "errors": activation["errors"]}
    catalog = _load_catalog(root)
    if catalog is not None:
        contract_errors = validate_execution_contract(root, contract, catalog)
        if contract_errors:
            return {"ok": False, "errors": contract_errors}
    errors = _validate_initialization_files(root, contract)
    accountability = root / contract["accountability_root"]
    reference_path = accountability / _REFERENCE_NAME
    if reference_path.is_file():
        return _failure("accountability_run_already_initialized", _relative_path(root, reference_path), "contract reference already exists")
    if accountability.exists() and any(accountability.rglob("*")):
        errors.append(_error("accountability_control_root_not_empty", contract["accountability_root"], "accountability control root must be empty before initialization"))
    run_instance_id = str(uuid.uuid4())
    initial_snapshot = _snapshot_monitored_state(root, contract, scope="production", run_instance_id=run_instance_id)
    expected_entries = [*(contract.get("initial_run_root_manifest") or []), *(contract.get("initial_owner_zone_manifest") or [])]
    expected = _manifest_from_entries(expected_entries, run_instance_id=run_instance_id, scope="production")
    errors.extend(compare_manifest_chain(expected, initial_snapshot))
    if errors:
        return {"ok": False, "errors": _sorted_errors(errors)}
    reference = {
        "artifact_role": "accountability_contract_reference",
        "version": 1,
        "run_instance_id": run_instance_id,
        "run_root": contract["run_root"],
        "contract_path": requested,
        "contract_sha256": record["contract_sha256"],
        "contract_source_commit": record["source_commit"],
        "initialized_at": _now_rfc3339(),
    }
    try:
        _write_json_exclusive(reference_path, reference)
    except FileExistsError:
        return _failure("accountability_run_already_initialized", _relative_path(root, reference_path), "contract reference already exists")
    return {
        "ok": True,
        "reference_path": _relative_path(root, reference_path),
        "reference": reference,
        "errors": [],
    }


def reserve_attempt(repo_root: Path, contract: dict, step_id: str) -> dict:
    """Atomically reserve the next explicit attempt before child launch."""
    root = Path(repo_root).resolve()
    context, context_errors = _execution_context(root, contract)
    if context is None:
        return {"ok": False, "errors": context_errors}
    step = _find_step(contract, step_id)
    if step is None:
        return _failure("contract_step_not_found", step_id, "step_id is not present in the committed contract")
    control = root / contract["accountability_root"]
    reservations = control / "reservations" / step_id
    receipts = control / "receipts" / step_id
    reservation_numbers = _attempt_numbers(reservations)
    receipt_numbers = _attempt_numbers(receipts)
    numbers = sorted(reservation_numbers | receipt_numbers)
    if numbers and numbers != list(range(1, max(numbers) + 1)):
        return _failure("accountability_attempt_sequence_invalid", step_id, "attempt numbers must be consecutive")
    for number in numbers:
        if number in reservation_numbers and number not in receipt_numbers:
            return {
                "ok": False,
                "status": "unknown",
                "failure_class": "STALE_RESERVATION",
                "retryable": False,
                "errors": [_error("accountability_stale_reservation", f"{step_id}/attempt-{number}", "reservation has no matching receipt")],
            }
        if number in receipt_numbers and number not in reservation_numbers:
            return _failure("accountability_attempt_sequence_invalid", step_id, "receipt has no matching reservation")
    attempt = (max(numbers) + 1) if numbers else 1
    if numbers:
        previous = _read_json(receipts / f"attempt-{attempt - 1}.json")
        previous_status = previous.get("status")
        if previous_status == "pass":
            return {
                "ok": False,
                "status": "stopped",
                "failure_class": "PASS_TERMINAL",
                "retryable": False,
                "errors": [_error("accountability_attempt_terminal", step_id, "a PASS receipt is terminal")],
            }
        if not bool(previous.get("retryable")) or previous.get("failure_class") not in set(step.get("allowed_retry_failure_classes") or []):
            return {
                "ok": False,
                "status": "stopped",
                "failure_class": str(previous.get("failure_class") or "NOT_RETRYABLE"),
                "retryable": False,
                "errors": [_error("accountability_retry_not_allowed", step_id, "previous failure is not explicitly retryable by the contract")],
            }
    max_attempts = int(step.get("max_attempts") or 0)
    if attempt > max_attempts:
        return _failure("accountability_attempt_limit", step_id, "attempt count exceeds contract max_attempts")
    argv = _resolved_argv(step)
    reservation = {
        "artifact_role": "accountability_attempt_reservation",
        "version": 1,
        "run_instance_id": context["reference"]["run_instance_id"],
        "contract_path": context["reference"]["contract_path"],
        "contract_sha256": context["reference"]["contract_sha256"],
        "step_id": step_id,
        "capability_id": step.get("capability_id"),
        "attempt": attempt,
        "argv_sha256": _hash_json_value(argv),
        "process_id": os.getpid(),
        "started_at": _now_rfc3339(),
    }
    reservation_path = reservations / f"attempt-{attempt}.json"
    try:
        _write_json_exclusive(reservation_path, reservation)
    except FileExistsError:
        return _failure("accountability_concurrent_attempt", _relative_path(root, reservation_path), "attempt reservation already exists")
    return {
        "ok": True,
        "status": "reserved",
        "attempt": attempt,
        "reservation_path": _relative_path(root, reservation_path),
        "reservation_sha256": hash_file(reservation_path),
        "reservation": reservation,
        "errors": [],
    }


def snapshot_monitored_state(repo_root: Path, contract: dict, *, scope: str) -> dict:
    """Capture a deterministic production or accountability-control manifest."""
    root = Path(repo_root).resolve()
    context, errors = _execution_context(root, contract, allow_missing_reference=True)
    if context is None and errors:
        raise ExecutionContractError(errors)
    run_instance_id = context["reference"]["run_instance_id"] if context else str(contract.get("_run_instance_id") or "")
    return _snapshot_monitored_state(root, contract, scope=scope, run_instance_id=run_instance_id)


def compare_manifest_chain(expected: dict, actual: dict) -> list[dict]:
    """Return deterministic differences between two state manifests."""
    errors: list[dict[str, str]] = []
    for field in ("artifact_role", "version", "run_instance_id", "scope"):
        if expected.get(field) != actual.get(field):
            errors.append(_error("manifest_metadata_mismatch", field, f"manifest {field} differs"))
    expected_files = {item.get("path"): item for item in expected.get("files") or [] if isinstance(item, dict)}
    actual_files = {item.get("path"): item for item in actual.get("files") or [] if isinstance(item, dict)}
    for path in sorted(set(expected_files) | set(actual_files)):
        before = expected_files.get(path)
        after = actual_files.get(path)
        if before is None:
            errors.append(_error("manifest_file_added", str(path), "file was added after the expected manifest"))
        elif after is None or after.get("state") == "deleted":
            errors.append(_error("manifest_file_deleted", str(path), "file is absent from the actual manifest"))
        elif before.get("sha256") != after.get("sha256"):
            errors.append(_error("manifest_file_changed", str(path), "file hash differs from the expected manifest"))
    return _sorted_errors(errors)


def run_capability_step(repo_root: Path, contract_path: Path, step_id: str) -> dict:
    """Execute exactly one committed capability step and write one receipt."""
    root = Path(repo_root).resolve()
    try:
        normalized = _coerce_repo_path(root, contract_path)
        contract = dict(load_execution_contract(root, normalized))
    except (ValueError, ExecutionContractError) as exc:
        errors = exc.errors if isinstance(exc, ExecutionContractError) else [_error("contract_not_tracked", str(contract_path), str(exc))]
        return {"ok": False, "errors": _sorted_errors(errors)}
    contract["_contract_path"] = normalized
    activation = resolve_strict_contract(root, root / contract["run_root"], normalized)
    if not activation["ok"]:
        return {"ok": False, "errors": activation["errors"]}
    catalog = _load_catalog(root)
    if catalog is None or not catalog.get("ok"):
        return _failure("contract_catalog_invalid", "skills", "live capability catalog is unavailable or invalid")
    contract_errors = validate_execution_contract(root, contract, catalog)
    if contract_errors:
        return {"ok": False, "errors": contract_errors}
    step = _find_step(contract, step_id)
    if step is None:
        return _failure("contract_step_not_found", step_id, "step_id is not present in the committed contract")
    dependency_errors = _validate_dependency_receipts(root, contract, step)
    if dependency_errors:
        return {"ok": False, "errors": dependency_errors}
    input_hashes, input_errors = _hash_inputs(root, step)
    if input_errors:
        return {"ok": False, "errors": input_errors}
    pre_manifest = _snapshot_monitored_state(root, contract, scope="production", run_instance_id=None)
    reservation = reserve_attempt(root, contract, step_id)
    if not reservation["ok"]:
        return reservation
    attempt = reservation["attempt"]
    child_before = _snapshot_monitored_state(root, contract, scope="child_control", run_instance_id=None)
    started = time.monotonic()
    started_at = _now_rfc3339()
    exit_code: int | None = None
    failure_class: str | None = None
    status = "pass"
    try:
        completed = subprocess.run(
            _resolved_argv(step),
            cwd=root,
            shell=False,
            timeout=int(step["timeout_ms"]) / 1000,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        exit_code = completed.returncode
        if exit_code != 0:
            status = "fail"
            failure_class = "LOCAL_PROCESS_NONZERO"
    except subprocess.TimeoutExpired:
        status = "unknown"
        failure_class = "LOCAL_TIMEOUT"
    child_after = _snapshot_monitored_state(root, contract, scope="child_control", run_instance_id=None)
    child_errors = compare_manifest_chain(child_before, child_after)
    if child_errors:
        status = "stopped"
        failure_class = "STRUCTURAL_CHILD_CONTROL_WRITE"
    post_manifest = _snapshot_monitored_state(root, contract, scope="production", run_instance_id=None)
    output_hashes, output_errors = _hash_outputs(root, step)
    if output_errors and status == "pass":
        status = "fail"
        failure_class = "LOCAL_OUTPUT_MISSING"
    changed_paths = _changed_manifest_paths(pre_manifest, post_manifest)
    undeclared = _undeclared_changes(root, contract, step, changed_paths)
    if undeclared:
        status = "stopped"
        failure_class = "STRUCTURAL_UNDECLARED_OUTPUT"
    retryable = status in {"fail", "unknown"} and failure_class in set(step.get("allowed_retry_failure_classes") or [])
    pre_path = root / contract["accountability_root"] / "manifests" / step_id / f"attempt-{attempt}-pre.json"
    post_path = root / contract["accountability_root"] / "manifests" / step_id / f"attempt-{attempt}-post.json"
    _write_json_exclusive(pre_path, pre_manifest)
    _write_json_exclusive(post_path, post_manifest)
    reservation_path = root / reservation["reservation_path"]
    receipt = {
        "artifact_role": "accountability_step_receipt",
        "version": 1,
        "run_instance_id": reservation["reservation"]["run_instance_id"],
        "contract_path": reservation["reservation"]["contract_path"],
        "contract_sha256": reservation["reservation"]["contract_sha256"],
        "step_id": step_id,
        "capability_id": step.get("capability_id"),
        "attempt": attempt,
        "reservation_path": reservation["reservation_path"],
        "reservation_sha256": hash_file(reservation_path),
        "command_argv": _resolved_argv(step),
        "started_at": started_at,
        "completed_at": _now_rfc3339(),
        "duration_sec": round(time.monotonic() - started, 6),
        "exit_code": exit_code,
        "status": status,
        "failure_class": failure_class,
        "retryable": retryable,
        "input_hashes": input_hashes,
        "output_hashes": output_hashes,
        "changed_paths": changed_paths,
        "pre_manifest_path": _relative_path(root, pre_path),
        "pre_manifest_sha256": hash_file(pre_path),
        "post_manifest_path": _relative_path(root, post_path),
        "post_manifest_sha256": hash_file(post_path),
        "source_tool": "video_tools.py capability-run",
    }
    receipt_path = root / contract["accountability_root"] / "receipts" / step_id / f"attempt-{attempt}.json"
    try:
        _write_json_exclusive(receipt_path, receipt)
    except FileExistsError:
        return _failure("accountability_concurrent_attempt", _relative_path(root, receipt_path), "receipt already exists")
    return {
        "ok": status == "pass",
        "status": status,
        "receipt_path": _relative_path(root, receipt_path),
        "receipt_sha256": hash_file(receipt_path),
        "failure_class": failure_class,
        "retryable": retryable,
        "changed_paths": changed_paths,
        "errors": output_errors if status == "fail" and output_errors else (child_errors if child_errors else ([_error(failure_class, step_id, "capability step did not pass")] if status != "pass" else [])),
    }


def validate_accountable_run_evidence(repo_root: Path, contract: dict, catalog: dict) -> dict:
    """Read strict evidence and return the closure-facing six-key result."""
    root = Path(repo_root).resolve()
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    context, context_errors = _execution_context(root, contract)
    if context is None:
        return {"ok": False, "tool_entries": [], "decision_entries": [], "final_state": "UNKNOWN_ACCOUNTABILITY", "errors": context_errors, "warnings": []}
    contract_errors = validate_execution_contract(root, contract, catalog)
    if contract_errors:
        return {"ok": False, "tool_entries": [], "decision_entries": [], "final_state": "UNKNOWN_ACCOUNTABILITY", "errors": contract_errors, "warnings": []}
    tool_entries: list[dict[str, Any]] = []
    for step in contract.get("steps") or []:
        if not isinstance(step, dict):
            continue
        step_id = step.get("step_id")
        receipt_dir = root / contract["accountability_root"] / "receipts" / str(step_id)
        numbers = _attempt_numbers(receipt_dir)
        if not numbers:
            errors.append(_error("missing_required_step", str(step_id), "required step has no receipt"))
            continue
        receipt_path = receipt_dir / f"attempt-{max(numbers)}.json"
        receipt = _read_json(receipt_path)
        if receipt.get("status") != "pass":
            errors.append(_error("required_step_not_pass", str(step_id), "latest required step receipt is not PASS"))
        tool_entries.append({
            "step_id": step_id,
            "receipt_path": _relative_path(root, receipt_path),
            "receipt_sha256": hash_file(receipt_path),
        })
    decision_entries: list[dict[str, Any]] = []
    owner_waiting: str | None = None
    for decision in contract.get("decision_requirements") or []:
        if not isinstance(decision, dict):
            continue
        path = str(decision.get("evidence_path") or "")
        evidence = root / path if path else root
        exists = evidence.is_file()
        status = "present" if exists else "missing"
        entry = {
            "requirement_id": decision.get("requirement_id"),
            "actor_class": decision.get("actor_class"),
            "status": status,
        }
        if exists:
            entry["evidence_path"] = path
            entry["evidence_sha256"] = hash_file(evidence)
        elif decision.get("actor_class") == "agent":
            errors.append(_error("missing_agent_evidence", path, "agent decision evidence is missing"))
        elif owner_waiting is None:
            owner_waiting = str(decision.get("missing_state") or "WAITING_OWNER_ACCOUNTABILITY")
        decision_entries.append(entry)
    if errors:
        final_state = "UNKNOWN_ACCOUNTABILITY"
    elif owner_waiting:
        final_state = owner_waiting
    else:
        final_state = "PASS"
    return {
        "ok": not errors,
        "tool_entries": sorted(tool_entries, key=lambda item: str(item.get("step_id") or "")),
        "decision_entries": sorted(decision_entries, key=lambda item: str(item.get("requirement_id") or "")),
        "final_state": final_state,
        "errors": _sorted_errors(errors),
        "warnings": sorted(warnings, key=lambda item: (str(item.get("code") or ""), str(item.get("path") or ""))),
    }


def _load_catalog(root: Path) -> dict | None:
    skills = root / "skills"
    if not skills.is_dir():
        return None
    from .capability_catalog import load_live_catalog

    return load_live_catalog(skills)


def _validate_initialization_files(root: Path, contract: dict) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    work_order = contract.get("work_order_path")
    expected = contract.get("work_order_sha256")
    if isinstance(work_order, str) and isinstance(expected, str):
        path = root / work_order
        if not path.is_file():
            errors.append(_error("contract_work_order_missing", work_order, "declared work order is missing"))
        elif hash_file(path) != expected:
            errors.append(_error("contract_work_order_hash_mismatch", work_order, "declared work order hash does not match"))
    for item in contract.get("protected_paths") or []:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            continue
        path = root / item["path"]
        if not path.is_file() or hash_file(path) != item.get("sha256"):
            errors.append(_error("contract_protected_hash_mismatch", item["path"], "protected path is missing or drifted"))
    return errors


def _execution_context(root: Path, contract: dict, *, allow_missing_reference: bool = False) -> tuple[dict | None, list[dict[str, str]]]:
    run = contract.get("run_root")
    if not isinstance(run, str):
        return None, [_error("contract_field_invalid", "run_root", "contract run_root is invalid")]
    candidate = contract.get("_contract_path") or contract.get("contract_path")
    if candidate is None:
        activation = resolve_strict_contract(root, root / run, None)
        if not activation.get("strict"):
            return None, activation.get("errors") or [_error("strict_contract_argument_missing", run, "no committed contract matches run root")]
        candidate = activation.get("contract_path")
    try:
        normalized = _coerce_repo_path(root, candidate)
    except ValueError as exc:
        return None, [_error("contract_not_tracked", str(candidate), str(exc))]
    record = next((item for item in discover_execution_companions(root) if item["path"] == normalized), None)
    if record is None:
        return None, [_error("contract_not_tracked", normalized, "contract companion is not tracked in HEAD")]
    if record["errors"]:
        return None, record["errors"]
    accountability = contract.get("accountability_root")
    if not isinstance(accountability, str):
        return None, [_error("contract_field_invalid", "accountability_root", "contract accountability_root is invalid")]
    reference_path = root / accountability / _REFERENCE_NAME
    if not reference_path.is_file():
        if allow_missing_reference:
            return None, []
        return None, [_error("accountability_reference_missing", _relative_path(root, reference_path), "accountability contract reference is missing")]
    try:
        reference = json.loads(reference_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None, [_error("accountability_reference_invalid", _relative_path(root, reference_path), "accountability contract reference is not valid JSON")]
    expected = {
        "contract_path": normalized,
        "contract_sha256": record["contract_sha256"],
        "contract_source_commit": record["source_commit"],
        "run_root": contract.get("run_root"),
    }
    errors = []
    for key, value in expected.items():
        if reference.get(key) != value:
            errors.append(_error("accountability_reference_mismatch", key, f"reference {key} does not match committed contract"))
    if errors:
        return None, errors
    return {"reference": reference, "reference_path": reference_path, "contract_path": normalized}, []


def _find_step(contract: dict, step_id: str) -> dict | None:
    matches = [item for item in contract.get("steps") or [] if isinstance(item, dict) and item.get("step_id") == step_id]
    return matches[0] if len(matches) == 1 else None


def _attempt_numbers(directory: Path) -> set[int]:
    if not directory.is_dir():
        return set()
    numbers: set[int] = set()
    for path in directory.iterdir():
        match = _ATTEMPT_RE.fullmatch(path.name)
        if match:
            numbers.add(int(match.group(1)))
    return numbers


def _resolved_argv(step: dict) -> list[str]:
    return [sys.executable if value == "{python}" else str(value) for value in step.get("command_argv") or []]


def _hash_json_value(value: Any) -> str:
    encoded = (json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _write_json_exclusive(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = canonical_json_bytes(payload)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    descriptor = os.open(path, flags, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            try:
                os.fsync(handle.fileno())
            except OSError:
                pass
    except BaseException:
        try:
            os.close(descriptor)
        except OSError:
            pass
        raise


def _read_json(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _now_rfc3339() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _relative_path(root: Path, path: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(root).as_posix()
    except ValueError:
        return path.as_posix().replace("\\", "/")


def _snapshot_monitored_state(root: Path, contract: dict, *, scope: str, run_instance_id: str | None) -> dict:
    if scope not in {"production", "child_control"}:
        raise ValueError("scope must be production or child_control")
    if run_instance_id is None:
        reference = root / str(contract.get("accountability_root") or "") / _REFERENCE_NAME
        run_instance_id = _read_json(reference).get("run_instance_id", "")
    files: dict[str, dict[str, Any]] = {}
    if scope == "child_control":
        base = root / str(contract.get("accountability_root") or "")
        if base.is_dir():
            for candidate in sorted(base.rglob("*"), key=lambda item: item.as_posix()):
                if candidate.is_file() and not candidate.is_symlink() and _is_within(root, candidate.resolve(strict=False)):
                    relative = _relative_path(root, candidate)
                    files[relative] = {"path": relative, "state": "present", "sha256": hash_file(candidate)}
    else:
        monitored: set[Path] = set()
        run_root = root / str(contract.get("run_root") or "")
        monitored.update(_files_under(run_root, root, exclude=root / str(contract.get("accountability_root") or "")))
        for rule in contract.get("allowed_owner_zones") or []:
            if not isinstance(rule, dict) or not isinstance(rule.get("path"), str):
                continue
            zone = root / rule["path"]
            if rule.get("match") == "exact":
                if zone.is_file() and not zone.is_symlink():
                    monitored.add(zone)
                elif zone.is_dir():
                    monitored.update(_files_under(zone, root, exclude=root / str(contract.get("accountability_root") or "")))
            else:
                monitored.update(_files_under(zone, root, exclude=root / str(contract.get("accountability_root") or "")))
        expected_entries = [*(contract.get("initial_run_root_manifest") or []), *(contract.get("initial_owner_zone_manifest") or [])]
        for item in expected_entries:
            if isinstance(item, dict) and isinstance(item.get("path"), str):
                monitored.add(root / item["path"])
        control_prefix = root / str(contract.get("accountability_root") or "")
        for candidate in sorted(monitored, key=lambda item: item.as_posix()):
            if _is_within(control_prefix, candidate.resolve(strict=False)):
                continue
            relative = _relative_path(root, candidate)
            if candidate.is_file() and not candidate.is_symlink():
                files[relative] = {"path": relative, "state": "present", "sha256": hash_file(candidate)}
            elif not candidate.exists():
                files[relative] = {"path": relative, "state": "deleted", "sha256": None}
    return {
        "artifact_role": "accountability_state_manifest",
        "version": 1,
        "run_instance_id": run_instance_id or "",
        "scope": scope,
        "captured_at": _now_rfc3339(),
        "files": [files[key] for key in sorted(files)],
    }


def _files_under(base: Path, root: Path, *, exclude: Path) -> set[Path]:
    if not base.is_dir():
        return set()
    result: set[Path] = set()
    for candidate in base.rglob("*"):
        if candidate.is_file() and not candidate.is_symlink() and _is_within(root, candidate.resolve(strict=False)) and not _is_within(exclude, candidate.resolve(strict=False)):
            result.add(candidate)
    return result


def _manifest_from_entries(entries: list, *, run_instance_id: str, scope: str) -> dict:
    files: dict[str, dict[str, Any]] = {}
    for item in entries:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            continue
        state = "deleted" if item.get("state") == "deleted" else "present"
        files[item["path"]] = {"path": item["path"], "state": state, "sha256": item.get("sha256") if state == "present" else None}
    return {
        "artifact_role": "accountability_state_manifest",
        "version": 1,
        "run_instance_id": run_instance_id,
        "scope": scope,
        "captured_at": "",
        "files": [files[key] for key in sorted(files)],
    }


def _validate_dependency_receipts(root: Path, contract: dict, step: dict) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    for dependency in step.get("depends_on") or []:
        dependency_step = _find_step(contract, dependency)
        if dependency_step is None:
            errors.append(_error("contract_step_reference_invalid", str(dependency), "dependency step is not in the contract"))
            continue
        receipt_dir = root / contract["accountability_root"] / "receipts" / str(dependency)
        numbers = _attempt_numbers(receipt_dir)
        if not numbers:
            errors.append(_error("accountability_dependency_missing", str(dependency), "dependency has no receipt"))
            continue
        receipt = _read_json(receipt_dir / f"attempt-{max(numbers)}.json")
        if receipt.get("status") != "pass":
            errors.append(_error("accountability_dependency_not_pass", str(dependency), "dependency receipt is not PASS"))
    return _sorted_errors(errors)


def _hash_inputs(root: Path, step: dict) -> tuple[dict[str, str], list[dict[str, str]]]:
    hashes: dict[str, str] = {}
    errors: list[dict[str, str]] = []
    for item in step.get("inputs") or []:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            continue
        path = root / item["path"]
        if not path.is_file():
            errors.append(_error("accountability_input_missing", item["path"], "declared input is missing"))
            continue
        digest = hash_file(path)
        hashes[item["path"]] = digest
        if digest != item.get("sha256"):
            errors.append(_error("accountability_input_hash_mismatch", item["path"], "declared input hash does not match"))
    return hashes, _sorted_errors(errors)


def _hash_outputs(root: Path, step: dict) -> tuple[dict[str, str], list[dict[str, str]]]:
    hashes: dict[str, str] = {}
    errors: list[dict[str, str]] = []
    for raw_path in step.get("required_outputs") or []:
        if not isinstance(raw_path, str):
            continue
        path = root / raw_path
        if not path.is_file():
            errors.append(_error("required_output_missing", raw_path, "required output is missing"))
            continue
        hashes[raw_path] = hash_file(path)
    return hashes, _sorted_errors(errors)


def _changed_manifest_paths(before: dict, after: dict) -> list[str]:
    before_map = {item.get("path"): item for item in before.get("files") or [] if isinstance(item, dict)}
    after_map = {item.get("path"): item for item in after.get("files") or [] if isinstance(item, dict)}
    changed = []
    for path in sorted(set(before_map) | set(after_map)):
        if before_map.get(path) != after_map.get(path):
            changed.append(str(path))
    return changed


def _undeclared_changes(root: Path, contract: dict, step: dict, changed_paths: list[str]) -> list[str]:
    declared = set()
    for raw_path in step.get("required_outputs") or []:
        if isinstance(raw_path, str):
            declared.add(raw_path)
    forbidden = {item.get("path") for item in contract.get("forbidden_paths") or [] if isinstance(item, dict)}
    return [path for path in changed_paths if path in forbidden or path not in declared]


def _failure(code: str, path: str, message: str) -> dict:
    return {"ok": False, "errors": [_error(code, path, message)]}


def normalize_repo_path(repo_root: Path, raw: str) -> str:
    """Return a portable repo-relative POSIX path or raise ``ValueError``."""
    root = Path(repo_root).resolve()
    if not isinstance(raw, str) or not raw or "\\" in raw or raw.startswith(("/", "//")) or _DRIVE_RE.match(raw):
        raise ValueError("path must be a non-empty portable repo-relative POSIX path")
    parts = raw.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError("path contains an empty or traversal component")

    current = root
    for part in parts:
        # Windows filesystems are case-insensitive. Reject a spelling that
        # would collide there even when these tests run on a POSIX filesystem.
        if current.exists():
            collisions = [item.name for item in current.iterdir() if item.name.casefold() == part.casefold()]
            if collisions and part not in collisions:
                raise ValueError("path case does not match the repository spelling")
        current = current / part

    resolved = current.resolve(strict=False)
    if not _is_within(root, resolved):
        raise ValueError("path escapes the repository root")
    return "/".join(parts)


def path_matches_rule(repo_root: Path, changed_path: str, rule: dict[str, Any]) -> bool:
    """Match one exact or directory-prefix ownership rule without globs."""
    path = normalize_repo_path(repo_root, changed_path)
    if not isinstance(rule, dict):
        raise ValueError("path rule must be an object")
    rule_path = normalize_repo_path(repo_root, rule.get("path"))
    match = rule.get("match")
    if match == "exact":
        return path == rule_path
    if match == "directory_prefix":
        return path.startswith(rule_path + "/")
    raise ValueError("path rule match must be exact or directory_prefix")


def discover_execution_companions(repo_root: Path) -> list[dict]:
    """Return every tracked companion, with committed bytes and load errors."""
    root = Path(repo_root).resolve()
    listed = _git(root, ["ls-files", _COMPANION_GLOB])
    if listed.returncode:
        return []
    paths = sorted(line for line in listed.stdout.decode("utf-8").splitlines() if line)
    return [_discover_companion(root, path) for path in paths]


def load_execution_contract(repo_root: Path, contract_path: str | Path) -> dict:
    """Load one tracked, committed, clean execution companion."""
    root = Path(repo_root).resolve()
    path = _coerce_repo_path(root, contract_path)
    if not _is_companion_path(path):
        raise ExecutionContractError([_error("contract_not_tracked", path, "contract path is not a tracked execution companion")])
    records = {item["path"]: item for item in discover_execution_companions(root)}
    record = records.get(path)
    if record is None:
        raise ExecutionContractError([_error("contract_not_tracked", path, "contract companion is not tracked in HEAD")])
    if record["errors"]:
        raise ExecutionContractError(record["errors"])
    return record["contract"]


def resolve_strict_contract(repo_root: Path, run_root: Path, contract_path: str | Path | None) -> dict:
    """Resolve strict activation solely from committed companions and run state."""
    root = Path(repo_root).resolve()
    run = _coerce_repo_path(root, run_root)
    base = {
        "ok": True,
        "strict": False,
        "contract_path": None,
        "contract_sha256": None,
        "contract_source_commit": None,
        "run_root": run,
        "accountability_root": f"{run}/accountability",
        "contract": {},
        "errors": [],
    }
    records = discover_execution_companions(root)
    selected: dict | None = None
    errors: list[dict[str, str]] = []

    if contract_path is not None:
        try:
            requested = _coerce_repo_path(root, contract_path)
        except ValueError:
            requested = str(contract_path).replace("\\", "/")
        selected = next((record for record in records if record["path"] == requested), None)
        if selected is None:
            errors.append(_error("contract_not_tracked", requested, "contract companion is not tracked in HEAD"))
        else:
            errors.extend(selected["errors"])
    else:
        matches = [record for record in records if record.get("contract", {}).get("run_root") == run]
        if len(matches) == 1:
            selected = matches[0]
            errors.extend(selected["errors"])
        elif len(matches) > 1:
            for record in matches:
                errors.append(_error("contract_run_root_conflict", record["path"], "more than one companion names this run root"))
        else:
            control = root / run / "accountability"
            if _has_control_artifact(control):
                errors.append(_error("strict_contract_reference_missing", f"{run}/accountability", "strict control artifacts require a committed contract reference"))
            elif control.exists():
                errors.append(_error("strict_contract_argument_missing", f"{run}/accountability", "strict control root requires an explicit committed contract"))
            else:
                return base

    if selected is not None:
        base.update({
            "contract_path": selected["path"],
            "contract_sha256": selected.get("contract_sha256"),
            "contract_source_commit": selected.get("source_commit"),
            "contract": selected.get("contract") or {},
        })
        contract = selected.get("contract") or {}
        if isinstance(contract.get("run_root"), str) and contract["run_root"] != run:
            errors.append(_error("contract_run_root_conflict", selected["path"], "contract run_root does not match the requested run root"))
        _append_duplicate_errors(root, records, selected, errors)

    base["errors"] = _sorted_errors(errors)
    base["ok"] = not base["errors"]
    base["strict"] = selected is not None
    return base


def validate_execution_contract(repo_root: Path, contract: dict, catalog: dict) -> list[dict]:
    """Validate frozen contract structure against the live read-only catalog."""
    root = Path(repo_root).resolve()
    errors: list[dict[str, str]] = []
    if not isinstance(contract, dict):
        return [_error("contract_json_invalid", "", "execution contract must be a JSON object")]

    _require_equal(contract, "artifact_role", "work_order_execution_contract", errors)
    _require_equal(contract, "version", 1, errors)
    _require_equal(contract, "accountability_contract_version", 1, errors, code="contract_version_unsupported")
    for key in ("work_order_id", "work_order_path", "work_order_sha256", "run_root", "accountability_root"):
        if not isinstance(contract.get(key), str) or not contract[key]:
            errors.append(_error("contract_field_invalid", key, f"{key} must be a non-empty string"))
    if isinstance(contract.get("work_order_sha256"), str) and not _SHA256_RE.fullmatch(contract["work_order_sha256"]):
        errors.append(_error("contract_hash_invalid", "work_order_sha256", "work_order_sha256 must be 64 lowercase hexadecimal characters"))

    normalized: dict[str, str] = {}
    for key in ("work_order_path", "run_root", "accountability_root"):
        if isinstance(contract.get(key), str):
            try:
                normalized[key] = normalize_repo_path(root, contract[key])
            except ValueError as exc:
                errors.append(_error("contract_path_invalid", key, str(exc)))
    if normalized.get("run_root") and normalized.get("accountability_root") != f"{normalized['run_root']}/accountability":
        errors.append(_error("contract_accountability_root_invalid", "accountability_root", "accountability_root must be run_root/accountability"))

    for key in ("initial_run_root_manifest", "initial_owner_zone_manifest", "allowed_owner_zones", "forbidden_paths", "protected_paths", "decision_requirements"):
        if not isinstance(contract.get(key), list):
            errors.append(_error("contract_field_invalid", key, f"{key} must be a list"))
    _validate_manifest(root, contract.get("initial_run_root_manifest"), "initial_run_root_manifest", errors)
    _validate_manifest(root, contract.get("initial_owner_zone_manifest"), "initial_owner_zone_manifest", errors)
    _validate_rules(root, contract.get("allowed_owner_zones"), "allowed_owner_zones", errors)
    _validate_rules(root, contract.get("forbidden_paths"), "forbidden_paths", errors)
    _validate_protected_paths(root, contract.get("protected_paths"), errors)

    cards = {item.get("capability_id"): item for item in (catalog.get("cards") or []) if isinstance(item, dict)} if isinstance(catalog, dict) and catalog.get("ok") else {}
    steps = contract.get("steps")
    if not isinstance(steps, list) or not steps:
        errors.append(_error("contract_field_invalid", "steps", "steps must be a non-empty list"))
        steps = []
    step_ids: set[str] = set()
    for index, step in enumerate(steps):
        location = f"steps/{index}"
        if not isinstance(step, dict):
            errors.append(_error("contract_step_invalid", location, "step must be an object"))
            continue
        step_id = step.get("step_id")
        if not isinstance(step_id, str) or not step_id:
            errors.append(_error("contract_step_invalid", location + "/step_id", "step_id must be a non-empty string"))
        elif step_id in step_ids:
            errors.append(_error("contract_step_id_duplicate", location + "/step_id", "step_id must be unique"))
        else:
            step_ids.add(step_id)
        capability_id = step.get("capability_id")
        card = cards.get(capability_id)
        if card is None:
            errors.append(_error("contract_capability_unregistered", location + "/capability_id", "step capability_id is not registered in the live catalog"))
        _validate_step(root, step, location, card, errors)

    _validate_step_references(steps, step_ids, errors)
    _validate_decisions(root, contract.get("decision_requirements"), step_ids, cards, steps, errors)
    return _sorted_errors(errors)


def _discover_companion(root: Path, path: str) -> dict:
    errors: list[dict[str, str]] = []
    try:
        normalized = normalize_repo_path(root, path)
    except ValueError as exc:
        normalized = path.replace("\\", "/")
        errors.append(_error("contract_not_tracked", normalized, str(exc)))
    revision = _git(root, ["rev-list", "-1", "HEAD", "--", normalized])
    commit = revision.stdout.decode("utf-8").strip() if revision.returncode == 0 else ""
    committed = b""
    if not commit:
        errors.append(_error("contract_not_tracked", normalized, "contract companion is not committed in HEAD"))
    else:
        shown = _git(root, ["show", f"{commit}:{normalized}"])
        committed = shown.stdout if shown.returncode == 0 else b""
        indexed = _git(root, ["show", f":{normalized}"])
        worktree = root / normalized
        working = worktree.read_bytes() if worktree.is_file() else None
        if indexed.returncode or indexed.stdout != committed or working != committed:
            errors.append(_error("contract_worktree_drift", normalized, "working tree and index bytes must match the committed companion"))

    contract: dict = {}
    if committed:
        try:
            loaded = json.loads(committed.decode("utf-8"))
            if not isinstance(loaded, dict):
                raise ValueError("contract is not an object")
            contract = loaded
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
            errors.append(_error("contract_json_invalid", normalized, "committed companion is not a JSON object"))
        else:
            if contract.get("accountability_contract_version") != 1:
                errors.append(_error("contract_version_unsupported", normalized, "accountability_contract_version must be 1"))
    return {
        "path": normalized,
        "source_commit": commit or None,
        "contract_sha256": hashlib.sha256(committed).hexdigest() if committed else None,
        "contract": contract,
        "errors": _sorted_errors(errors),
    }


def _append_duplicate_errors(root: Path, records: list[dict], selected: dict, errors: list[dict[str, str]]) -> None:
    contract = selected.get("contract") or {}
    for field, code in (("work_order_id", "contract_duplicate_work_order_id"), ("work_order_path", "contract_duplicate_work_order_path")):
        value = contract.get(field)
        if not isinstance(value, str):
            continue
        if field == "work_order_path":
            value = _lexical_path_identity(value)
            if value is None:
                continue
        group = []
        for record in records:
            other = record.get("contract") or {}
            other_value = other.get(field)
            if field == "work_order_path" and isinstance(other_value, str):
                other_value = _lexical_path_identity(other_value)
                if other_value is None:
                    continue
            if other_value == value:
                group.append(record)
        if len(group) > 1:
            errors.append(_error(code, selected["path"], f"{field} is shared by multiple committed companions"))
            versions = {item.get("contract", {}).get("accountability_contract_version") for item in group}
            if versions != {1}:
                errors.append(_error("contract_version_unsupported", selected["path"], "duplicate companion group contains an unsupported version"))


def _lexical_path_identity(raw: str) -> str | None:
    """Return a filesystem-independent identity for a portable POSIX path."""
    if not isinstance(raw, str) or not raw or "\\" in raw or raw.startswith(("/", "//")) or _DRIVE_RE.match(raw):
        return None
    parts = raw.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        return None
    return "/".join(parts).casefold()


def _validate_manifest(root: Path, manifest: Any, location: str, errors: list[dict[str, str]]) -> None:
    if not isinstance(manifest, list):
        return
    for index, item in enumerate(manifest):
        path = f"{location}/{index}"
        if not isinstance(item, dict):
            errors.append(_error("contract_manifest_invalid", path, "manifest item must be an object"))
            continue
        _validate_declared_path(root, item.get("path"), path + "/path", errors)
        deleted = item.get("state") == "deleted"
        digest = item.get("sha256")
        if deleted:
            if digest is not None:
                errors.append(_error("contract_manifest_invalid", path + "/sha256", "deleted tombstones must use sha256 null"))
        elif not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
            errors.append(_error("contract_manifest_invalid", path + "/sha256", "live manifest entries require a SHA-256"))


def _validate_rules(root: Path, rules: Any, location: str, errors: list[dict[str, str]]) -> None:
    if not isinstance(rules, list):
        return
    for index, rule in enumerate(rules):
        path = f"{location}/{index}"
        if not isinstance(rule, dict):
            errors.append(_error("contract_path_rule_invalid", path, "path rule must be an object"))
            continue
        _validate_declared_path(root, rule.get("path"), path + "/path", errors)
        if rule.get("match") not in {"exact", "directory_prefix"}:
            errors.append(_error("contract_path_rule_invalid", path + "/match", "match must be exact or directory_prefix"))


def _validate_protected_paths(root: Path, paths: Any, errors: list[dict[str, str]]) -> None:
    if not isinstance(paths, list):
        return
    for index, item in enumerate(paths):
        location = f"protected_paths/{index}"
        if not isinstance(item, dict):
            errors.append(_error("contract_protected_path_invalid", location, "protected path must be an object"))
            continue
        _validate_declared_path(root, item.get("path"), location + "/path", errors)
        if not isinstance(item.get("sha256"), str) or not _SHA256_RE.fullmatch(item["sha256"]):
            errors.append(_error("contract_protected_path_invalid", location + "/sha256", "protected path requires a SHA-256"))


def _validate_step(root: Path, step: dict, location: str, card: dict | None, errors: list[dict[str, str]]) -> None:
    argv = step.get("command_argv")
    if not isinstance(argv, list) or not argv or not all(isinstance(item, str) and item for item in argv):
        errors.append(_error("contract_command_argv_invalid", location + "/command_argv", "command_argv must be a non-empty argv list"))
    else:
        for index, item in enumerate(argv):
            if "{" in item or "}" in item:
                if not (index == 0 and item == "{python}"):
                    errors.append(_error("contract_command_argv_invalid", location + f"/command_argv/{index}", "only argv[0] may equal {python}"))
        if card is not None:
            registered_command = card.get("command")
            if not isinstance(registered_command, str) or not registered_command.strip():
                errors.append(_error(
                    "contract_registered_command_missing",
                    location + "/command_argv",
                    "registered capability command must be non-empty",
                ))
            else:
                try:
                    expected = [sys.executable, *shlex.split(registered_command)]
                except ValueError:
                    errors.append(_error(
                        "contract_registered_command_invalid",
                        location + "/command_argv",
                        "registered capability command must be a valid argv prefix",
                    ))
                else:
                    actual = [sys.executable if item == "{python}" else item for item in argv]
                    if actual[:len(expected)] != expected:
                        errors.append(_error(
                            "contract_command_argv_mismatch",
                            location + "/command_argv",
                            "command_argv must start with the registered capability command",
                        ))
    for field in ("timeout_ms", "max_attempts"):
        if not isinstance(step.get(field), int) or isinstance(step.get(field), bool) or step[field] <= 0:
            errors.append(_error("contract_step_invalid", location + f"/{field}", f"{field} must be a positive integer"))
    for field in ("depends_on", "inputs", "required_outputs", "required_verifier_step_ids", "allowed_retry_failure_classes"):
        if not isinstance(step.get(field), list):
            errors.append(_error("contract_step_invalid", location + f"/{field}", f"{field} must be a list"))
    for index, output in enumerate(step.get("required_outputs") or []):
        _validate_declared_path(root, output, location + f"/required_outputs/{index}", errors)
    inputs = step.get("inputs")
    if isinstance(inputs, list):
        for index, item in enumerate(inputs):
            _validate_step_input(root, item, location + f"/inputs/{index}", errors)
    for index, retry_class in enumerate(step.get("allowed_retry_failure_classes") or []):
        if not isinstance(retry_class, str) or not retry_class.startswith("LOCAL_"):
            errors.append(_error("contract_retry_invalid", location + f"/allowed_retry_failure_classes/{index}", "only LOCAL_* failure classes are retryable"))


def _validate_step_input(root: Path, item: Any, location: str, errors: list[dict[str, str]]) -> None:
    if not isinstance(item, dict):
        errors.append(_error("contract_step_input_invalid", location, "input must be an object"))
        return
    _validate_declared_path(root, item.get("path"), location + "/path", errors)
    digest = item.get("sha256")
    if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
        errors.append(_error("contract_step_input_invalid", location + "/sha256", "input sha256 must be 64 lowercase hexadecimal characters"))


def _validate_step_references(steps: list, step_ids: set[str], errors: list[dict[str, str]]) -> None:
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            continue
        for field in ("depends_on", "required_verifier_step_ids"):
            for ref in step.get(field) or []:
                if ref not in step_ids:
                    errors.append(_error("contract_step_reference_invalid", f"steps/{index}/{field}", "step reference must name a contract step_id"))


def _validate_decisions(root: Path, decisions: Any, step_ids: set[str], cards: dict, steps: list, errors: list[dict[str, str]]) -> None:
    if not isinstance(decisions, list):
        return
    ids: set[str] = set()
    evidence: set[str] = set()
    agent_dependencies: dict[str, int] = {}
    for index, item in enumerate(decisions):
        location = f"decision_requirements/{index}"
        if not isinstance(item, dict):
            errors.append(_error("contract_decision_invalid", location, "decision requirement must be an object"))
            continue
        requirement_id = item.get("requirement_id")
        if not isinstance(requirement_id, str) or not requirement_id or requirement_id in ids:
            errors.append(_error("contract_decision_invalid", location + "/requirement_id", "requirement_id must be unique and non-empty"))
        else:
            ids.add(requirement_id)
        actor = item.get("actor_class")
        if actor not in {"agent", "owner"}:
            errors.append(_error("contract_decision_invalid", location + "/actor_class", "actor_class must be agent or owner"))
        deps = item.get("depends_on_step_ids")
        if not isinstance(deps, list) or not deps or any(dep not in step_ids for dep in deps):
            errors.append(_error("contract_decision_invalid", location + "/depends_on_step_ids", "dependencies must name contract step IDs"))
        if actor == "agent" and isinstance(deps, list):
            for dep in deps:
                agent_dependencies[dep] = agent_dependencies.get(dep, 0) + 1
        evidence_path = item.get("evidence_path")
        if isinstance(evidence_path, str):
            _validate_declared_path(root, evidence_path, location + "/evidence_path", errors)
            if evidence_path in evidence:
                errors.append(_error("contract_decision_invalid", location + "/evidence_path", "evidence_path must be unique"))
            evidence.add(evidence_path)
        else:
            errors.append(_error("contract_decision_invalid", location + "/evidence_path", "evidence_path must be a path"))
        missing = item.get("missing_state")
        if actor == "agent" and missing != "UNKNOWN_AGENT_EVIDENCE":
            errors.append(_error("contract_decision_invalid", location + "/missing_state", "agent requirements use UNKNOWN_AGENT_EVIDENCE"))
        if actor == "owner" and (not isinstance(missing, str) or not missing.startswith("WAITING_OWNER_")):
            errors.append(_error("contract_decision_invalid", location + "/missing_state", "owner requirements use WAITING_OWNER_*"))
    for step in steps:
        if isinstance(step, dict) and cards.get(step.get("capability_id"), {}).get("execution_class") == "hybrid":
            step_id = step.get("step_id")
            if agent_dependencies.get(step_id) != 1:
                errors.append(_error("contract_hybrid_decision_invalid", f"steps/{step_id}", "hybrid steps require exactly one agent decision requirement"))


def _validate_declared_path(root: Path, value: Any, location: str, errors: list[dict[str, str]]) -> None:
    try:
        normalize_repo_path(root, value)
    except ValueError as exc:
        errors.append(_error("contract_path_invalid", location, str(exc)))


def _require_equal(contract: dict, key: str, expected: Any, errors: list[dict[str, str]], *, code: str = "contract_field_invalid") -> None:
    if contract.get(key) != expected:
        errors.append(_error(code, key, f"{key} must equal {expected!r}"))


def _coerce_repo_path(root: Path, raw: str | Path) -> str:
    path = Path(raw)
    if path.is_absolute():
        try:
            raw = path.resolve(strict=False).relative_to(root).as_posix()
        except ValueError as exc:
            raise ValueError("path escapes the repository root") from exc
    return normalize_repo_path(root, str(raw).replace("\\", "/"))


def _has_control_artifact(control: Path) -> bool:
    if not control.exists():
        return False
    for item in control.iterdir():
        if item.name in _CONTROL_NAMES:
            if item.name == "contract_reference.json":
                continue
            return True
    return False


def _is_companion_path(path: str) -> bool:
    return path.startswith("docs/construction-guides/work-orders/") and path.endswith(".execution.json")


def _is_within(root: Path, candidate: Path) -> bool:
    root_text = os.path.normcase(str(root))
    candidate_text = os.path.normcase(str(candidate))
    try:
        return os.path.commonpath([root_text, candidate_text]) == root_text
    except ValueError:
        return False


def _git(root: Path, args: list[str]) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["git", "-C", str(root), *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)


def _error(code: str, path: str, message: str) -> dict[str, str]:
    return {"code": code, "path": path, "message": message}


def _sorted_errors(errors: list[dict[str, str]]) -> list[dict[str, str]]:
    unique = {(item["code"], item["path"], item["message"]): item for item in errors}
    return [unique[key] for key in sorted(unique)]
