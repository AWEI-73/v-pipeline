"""One pure loader/normalizer for Skill TOOL_CONTRACT metadata."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable


REQUIRED_TOOL_FIELDS = ("tool", "when", "inputs", "outputs", "stop_if")
CONTRACT_BUCKETS = ("canonical_tools", "supporting_tools", "internal_tools", "diagnostic_tools")
KNOWN_LOOPS = {f"L{index}" for index in range(6)}
MATURITIES = {"experimental", "bounded", "certified", "legacy"}
CAPABILITY_ID_RE = re.compile(r"^cap\.[a-z0-9][a-z0-9-]*\.[a-z0-9][a-z0-9-]*\.v[1-9][0-9]*$")


def _source_text(path: Path) -> str:
    return str(path).replace("\\", "/")


def _marker_pattern(value: str) -> str:
    value = str(value).strip()
    if value.startswith("<!--"):
        return re.escape(value)
    return rf"<!--\s*{re.escape(value)}\s*-->"


def _error(code: str, contract: dict[str, Any] | None = None, entry: dict[str, Any] | None = None, message: str = "") -> dict[str, Any]:
    contract = contract or {}
    entry = entry or {}
    return {
        "code": code,
        "source": contract.get("_source"),
        "skill": contract.get("skill"),
        "capability_id": entry.get("capability_id"),
        "tool": entry.get("tool"),
        "message": message,
    }


def parse_json_marker_blocks(path: Path | str, text: str, *, start: str, end: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Parse all JSON blocks between a generic marker pair."""
    path = Path(path)
    blocks: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    pattern = re.compile(rf"{_marker_pattern(start)}(.*?){_marker_pattern(end)}", re.DOTALL)
    for index, match in enumerate(pattern.finditer(text), start=1):
        raw = match.group(1).strip()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            errors.append({
                "code": "malformed_json",
                "source": _source_text(path),
                "skill": None,
                "capability_id": None,
                "tool": None,
                "message": f"marker block {index} is not valid JSON: {exc}",
            })
            continue
        if not isinstance(payload, dict):
            errors.append({
                "code": "marker_not_object",
                "source": _source_text(path),
                "skill": None,
                "capability_id": None,
                "tool": None,
                "message": f"marker block {index} must contain a JSON object",
            })
            continue
        payload = dict(payload)
        payload["_source"] = _source_text(path)
        payload["_marker_index"] = index
        blocks.append(payload)
    return blocks, errors


def load_contracts(skills_dir: Path | str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    skills_dir = Path(skills_dir)
    contracts: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for path in sorted(skills_dir.glob("*.md"), key=lambda item: item.as_posix()):
        try:
            text = path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError) as exc:
            errors.append({
                "code": "skill_read_error",
                "source": _source_text(path),
                "skill": None,
                "capability_id": None,
                "tool": None,
                "message": str(exc),
            })
            continue
        parsed, parse_errors = parse_json_marker_blocks(path, text, start="TOOL_CONTRACT_START", end="TOOL_CONTRACT_END")
        contracts.extend(parsed)
        errors.extend(parse_errors)
    return contracts, sorted(errors, key=_error_sort_key)


def load_capability_consumers(skills_dir: Path | str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Load director/consumer declarations without creating a second registry."""
    skills_dir = Path(skills_dir)
    consumers: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for path in sorted(skills_dir.glob("*.md"), key=lambda item: item.as_posix()):
        try:
            text = path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError) as exc:
            errors.append({
                "code": "skill_read_error",
                "source": _source_text(path),
                "skill": None,
                "capability_id": None,
                "tool": None,
                "message": str(exc),
            })
            continue
        parsed, parse_errors = parse_json_marker_blocks(
            path,
            text,
            start="CAPABILITY_CONSUMER_START",
            end="CAPABILITY_CONSUMER_END",
        )
        consumers.extend(parsed)
        errors.extend(parse_errors)
    return consumers, sorted(errors, key=_error_sort_key)


def iter_tool_entries(contract: dict[str, Any]) -> list[dict[str, Any]]:
    """Return copied entries with enough provenance for audits and catalogs."""
    entries: list[dict[str, Any]] = []
    for section in CONTRACT_BUCKETS:
        raw_entries = contract.get(section) or []
        if not isinstance(raw_entries, list):
            continue
        for item in raw_entries:
            if isinstance(item, str):
                item = {"tool": item}
            if not isinstance(item, dict):
                continue
            entry = deepcopy(item)
            entry.update({
                "_section": section,
                "_skill": contract.get("skill"),
                "_stage_owner": contract.get("stage_owner"),
                "_source": contract.get("_source"),
            })
            entries.append(entry)
    return entries


def normalize_tool_ref(value: Any) -> str:
    value = str(value or "").strip().replace("\\", "/")
    if value.startswith("python "):
        value = value[7:].strip()
    if value.startswith("./"):
        value = value[2:]
    return value


def suggest_capability_id(owner: str, tool_ref: str) -> str:
    owner_token = re.sub(r"[^a-z0-9-]+", "-", str(owner).strip().lower()).strip("-") or "owner"
    normalized = normalize_tool_ref(tool_ref)
    action = Path(normalized).stem.lower() if normalized else "action"
    action = re.sub(r"[^a-z0-9-]+", "-", action.replace("_", "-")).strip("-") or "action"
    return f"cap.{owner_token}.{action}.v1"


def _error_sort_key(item: dict[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        str(item.get("code") or ""),
        str(item.get("source") or ""),
        str(item.get("skill") or ""),
        str(item.get("tool") or ""),
        str(item.get("capability_id") or ""),
    )


def validate_contract_schema(contracts: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Validate fields and formats only; no filesystem or repository lookup."""
    errors: list[dict[str, Any]] = []
    seen_ids: dict[str, dict[str, Any]] = {}
    for contract in contracts:
        source = contract.get("_source")
        skill = str(contract.get("skill") or "").strip()
        if not skill:
            errors.append(_error("missing_skill", contract, message="contract is missing skill"))
        for field in ("version", "stage_owner", "triggers", "forbidden_tools"):
            if field not in contract:
                errors.append(_error(f"missing_{field}", contract, message=f"contract is missing {field}"))
        if not isinstance(contract.get("triggers"), list) or not contract.get("triggers"):
            errors.append(_error("invalid_triggers", contract, message="triggers must be a non-empty list"))
        if "canonical_tools" not in contract:
            errors.append(_error("missing_canonical_tools", contract, message="contract is missing canonical_tools"))
        if not isinstance(contract.get("canonical_tools"), list) or not contract.get("canonical_tools"):
            errors.append(_error("invalid_canonical_tools", contract, message="canonical_tools must be a non-empty list"))
        if not str(contract.get("stage_owner") or "").strip():
            errors.append(_error("missing_stage_owner", contract, message="contract stage_owner must be non-empty"))
        if not str(contract.get("capability_namespace") or "").strip():
            errors.append(_error("missing_capability_namespace", contract, message="contract capability_namespace must be non-empty"))
        if not str(contract.get("capability_lookup_owner") or "").strip():
            errors.append(_error("missing_capability_lookup_owner", contract, message="contract capability_lookup_owner must be non-empty"))

        for entry in iter_tool_entries(contract):
            tool = entry.get("tool")
            section = entry.get("_section")
            if not tool:
                errors.append(_error("missing_tool", contract, entry, f"{section} entry is missing tool"))
                continue
            for field in REQUIRED_TOOL_FIELDS:
                if field not in entry:
                    errors.append(_error(f"missing_{field}", contract, entry, f"tool is missing {field}"))
            if section != "canonical_tools":
                continue
            capability_id = entry.get("capability_id")
            if not capability_id:
                errors.append(_error("missing_capability_id", contract, entry, "canonical tool is missing capability_id"))
            elif not isinstance(capability_id, str) or not CAPABILITY_ID_RE.fullmatch(capability_id):
                errors.append(_error("invalid_capability_id", contract, entry, "capability_id must match cap.<owner>.<action>.v<major>"))
            elif capability_id in seen_ids and not (entry.get("shared") is True and seen_ids[capability_id].get("shared") is True):
                errors.append(_error("duplicate_capability_id", contract, entry, "capability_id is duplicated"))
            else:
                seen_ids[capability_id] = entry
            loops = entry.get("loops")
            if "loops" not in entry:
                errors.append(_error("missing_loops", contract, entry, "canonical tool is missing loops"))
            elif not isinstance(loops, list):
                errors.append(_error("invalid_loops", contract, entry, "loops must be a list"))
            elif any(loop not in KNOWN_LOOPS for loop in loops):
                errors.append(_error("invalid_loops", contract, entry, "loops contains an unknown loop"))
            elif not loops and not str(contract.get("stage_owner") or "").strip():
                errors.append(_error("missing_loop_or_stage", contract, entry, "empty loops requires a non-empty parent stage_owner"))
            maturity = entry.get("maturity")
            if maturity is None:
                errors.append(_error("missing_maturity", contract, entry, "canonical tool is missing maturity"))
            elif maturity not in MATURITIES:
                errors.append(_error("invalid_maturity", contract, entry, "maturity must be experimental|bounded|certified|legacy"))
            if maturity in {"bounded", "certified"} and not str(entry.get("certified_scope") or "").strip():
                errors.append(_error("missing_certified_scope", contract, entry, "bounded/certified capability requires certified_scope"))
    return sorted(errors, key=_error_sort_key)


def audit_repository_contracts(
    contracts: Iterable[dict[str, Any]],
    *,
    python_tools: Iterable[str] = (),
    dispatch_commands: Iterable[str] = (),
    catalog_commands: Iterable[str] = (),
    capability_consumers: Iterable[dict[str, Any]] = (),
) -> list[dict[str, Any]]:
    """Repository-dependent checks layered on top of pure schema validation."""
    contracts = list(contracts)
    errors = validate_contract_schema(contracts)
    python_tools = {normalize_tool_ref(x) for x in python_tools}
    dispatch_commands = {normalize_tool_ref(x) for x in dispatch_commands}
    catalog_commands = {normalize_tool_ref(x) for x in catalog_commands}
    ownership: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = {}
    canonical_ids: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    all_capability_refs: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    for contract in contracts:
        for entry in iter_tool_entries(contract):
            tool = normalize_tool_ref(entry.get("tool"))
            if tool.startswith("tools/"):
                ownership.setdefault(tool, []).append((contract, entry))
            # Domain Skills may own the root ``video_tools.py`` command
            # surface by command name; only tools/ Python files participate in
            # the filesystem ownership check here.
            if entry.get("_section") == "canonical_tools" and tool.startswith("tools/") and tool not in python_tools:
                errors.append(_error("missing_tool_reference", contract, entry, "canonical tool does not exist in tools directory"))
            capability_id = entry.get("capability_id")
            if capability_id:
                all_capability_refs[str(capability_id)] = (contract, entry)
                if entry.get("_section") == "canonical_tools":
                    canonical_ids[str(capability_id)] = (contract, entry)
            command = normalize_tool_ref(entry.get("command"))
            if command and command not in dispatch_commands:
                errors.append(_error("command_not_dispatched", contract, entry, "command is not present in dispatch command set"))
            if command and command not in catalog_commands:
                errors.append(_error("command_not_cataloged", contract, entry, "command is not present in catalog command set"))
    for tool in sorted(python_tools - set(ownership)):
        errors.append(_error("unowned_python_tool", {"_source": "tools", "skill": None}, {"tool": tool}, "python tool is not owned by any Skill contract"))
    for tool, owners in ownership.items():
        canonical = [(c, e) for c, e in owners if e.get("_section") == "canonical_tools"]
        if len(canonical) > 1 and not all(e.get("shared") is True for _, e in canonical):
            first_contract, first_entry = canonical[0]
            errors.append(_error("duplicate_canonical_owner", first_contract, first_entry, "canonical tool has multiple owners without shared=true"))
    for contract in contracts:
        namespace = str(contract.get("capability_namespace") or "").strip()
        if namespace:
            prefix = namespace[:-1] if namespace.endswith("*") else namespace
            if not any(capability_id.startswith(prefix) for capability_id in canonical_ids):
                errors.append(_error("broken_domain_lookup", contract, message="capability_namespace has no matching canonical capability"))
    for consumer in capability_consumers:
        if not isinstance(consumer, dict):
            continue
        source = {"_source": consumer.get("source", "<consumer>"), "skill": consumer.get("consumer")}
        if any(key in consumer for key in ("canonical_tools", "supporting_tools", "internal_tools", "diagnostic_tools")):
            errors.append(_error("broken_director_reference", source, message="capability consumer cannot contain tool ownership fields"))
        for capability_id in consumer.get("active_capability_ids") or []:
            ref = all_capability_refs.get(str(capability_id))
            if ref is None:
                errors.append(_error("broken_director_reference", source, {"capability_id": capability_id}, "consumer references an unknown capability ID"))
                continue
            contract, entry = ref
            if entry.get("_section") != "canonical_tools":
                errors.append(_error("noncanonical_public_reference", contract, entry, "consumer references a non-canonical tool"))
            if entry.get("maturity") == "legacy":
                errors.append(_error("active_legacy_reference", contract, entry, "consumer references a legacy capability"))
        for namespace in consumer.get("active_namespaces") or []:
            prefix = str(namespace)[:-1] if str(namespace).endswith("*") else str(namespace)
            if not any(capability_id.startswith(prefix) for capability_id in canonical_ids):
                errors.append(_error("broken_director_reference", source, message="consumer references an unknown capability namespace"))
    return sorted(errors, key=_error_sort_key)
