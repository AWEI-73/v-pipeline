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
from pathlib import Path
from typing import Any


_COMPANION_GLOB = "docs/construction-guides/work-orders/*.execution.json"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_DRIVE_RE = re.compile(r"^[A-Za-z]:")
_CONTROL_NAMES = {"contract_reference.json", "receipts", "reservations", "attestations", "verdicts"}


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
        if card and isinstance(card.get("command"), str):
            expected = [sys.executable, *shlex.split(card["command"])]
            actual = [sys.executable if item == "{python}" else item for item in argv]
            if actual != expected:
                errors.append(_error("contract_command_argv_mismatch", location + "/command_argv", "command_argv must match the registered capability command"))
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
