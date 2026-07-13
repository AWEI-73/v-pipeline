from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video_pipeline_core.skill_tool_contract import (
    REQUIRED_TOOL_FIELDS,
    audit_repository_contracts,
    iter_tool_entries,
    load_capability_consumers,
    load_contracts,
    normalize_tool_ref,
    projected_command_ref,
    suggest_capability_id,
    validate_contract_schema,
    validate_retirement_delta,
)


def _normalize_tool_name(value: str) -> str:
    return normalize_tool_ref(value)


def _tool_entries(contract: dict[str, Any]) -> list[dict[str, Any]]:
    return iter_tool_entries(contract)


def validate_contracts(contracts: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    seen_skills: set[str] = set()
    canonical_owners: dict[str, str] = {}

    for contract in contracts:
        source = contract.get("_source", "<unknown>")
        skill = str(contract.get("skill") or "").strip()
        if not skill:
            errors.append(f"{source}: contract missing skill")
            continue
        if skill in seen_skills:
            errors.append(f"{source}: duplicate contract for skill {skill}")
        seen_skills.add(skill)

        for field in ("version", "skill", "stage_owner", "triggers", "canonical_tools", "forbidden_tools"):
            if field not in contract:
                errors.append(f"{source}: {skill} missing {field}")

        if not contract.get("triggers"):
            errors.append(f"{source}: {skill} has no triggers")
        if not contract.get("canonical_tools"):
            errors.append(f"{source}: {skill} has no canonical_tools")

        for entry in _tool_entries(contract):
            tool = entry.get("tool")
            section = entry.get("_section")
            if not tool:
                errors.append(f"{source}: {skill} {section} entry missing tool")
                continue
            for field in REQUIRED_TOOL_FIELDS:
                if field not in entry:
                    errors.append(f"{source}: {skill} tool {tool} missing {field}")
            if section == "canonical_tools":
                normalized = _normalize_tool_name(str(tool))
                previous = canonical_owners.get(normalized)
                if previous and not entry.get("shared"):
                    errors.append(
                        f"{source}: canonical tool {normalized} owned by both {previous} and {skill}; "
                        "mark shared=true or make it supporting/internal"
                    )
                canonical_owners.setdefault(normalized, skill)
    return errors


def discover_python_tools(tools_dir: Path) -> list[str]:
    if not tools_dir.exists():
        return []
    return sorted(
        str(path.relative_to(tools_dir.parent)).replace("\\", "/")
        for path in tools_dir.glob("*.py")
        if path.name != "__init__.py"
    )


def discover_command_sets(skills_dir: Path) -> tuple[set[str], set[str]]:
    """Use the live CLI/catalog surface, with deterministic fixture overrides."""
    context = load_audit_context(skills_dir)
    from video_tools import VIDEO_TOOLS_DISPATCH, build_video_tools_command_manifest

    dispatch = {f"video_tools.py {name}" for name in VIDEO_TOOLS_DISPATCH}
    manifest = build_video_tools_command_manifest()
    catalog = {f"video_tools.py {name}" for name in (manifest.get("commands") or {})}
    if "dispatch_commands" in context:
        dispatch = {normalize_tool_ref(value) for value in context.get("dispatch_commands") or []}
    if "catalog_commands" in context:
        catalog = {normalize_tool_ref(value) for value in context.get("catalog_commands") or []}
    return dispatch, catalog


def load_audit_context(skills_dir: Path) -> dict[str, Any]:
    context_path = skills_dir.parent / "audit_context.json"
    if not context_path.exists():
        return {}
    return json.loads(context_path.read_text(encoding="utf-8"))


def analyze(skills_dir: Path, tools_dir: Path) -> dict[str, Any]:
    contracts, parse_errors = load_contracts(skills_dir)
    capability_consumers, consumer_parse_errors = load_capability_consumers(skills_dir)
    python_tools = discover_python_tools(tools_dir)
    dispatch_commands, catalog_commands = discover_command_sets(skills_dir)
    audit_context = load_audit_context(skills_dir)
    capability_errors = [*parse_errors, *consumer_parse_errors]
    capability_errors.extend(validate_contract_schema(contracts))

    ownership: dict[str, list[str]] = {}
    for contract in contracts:
        skill = str(contract.get("skill") or "")
        for entry in _tool_entries(contract):
            tool = _normalize_tool_name(str(entry.get("tool") or ""))
            if tool.endswith(".py") and tool.startswith("tools/"):
                ownership.setdefault(tool, []).append(skill)

    unowned = [tool for tool in python_tools if tool not in ownership]
    duplicate_canonical: dict[str, list[str]] = {}
    canonical_seen: dict[str, list[str]] = {}
    for contract in contracts:
        skill = str(contract.get("skill") or "")
        for entry in contract.get("canonical_tools", []) or []:
            if isinstance(entry, dict):
                tool = _normalize_tool_name(str(entry.get("tool") or ""))
                if tool:
                    canonical_seen.setdefault(tool, []).append(skill)
    duplicate_canonical = {
        tool: owners for tool, owners in canonical_seen.items() if len(set(owners)) > 1
    }
    capability_id_proposals = []
    for contract in contracts:
        for entry in contract.get("canonical_tools", []) or []:
            if not isinstance(entry, dict) or entry.get("capability_id"):
                continue
            tool = _normalize_tool_name(str(entry.get("tool") or ""))
            capability_id_proposals.append({
                "source": contract.get("_source"),
                "skill": contract.get("skill"),
                "tool": tool,
                "proposed_capability_id": suggest_capability_id(str(contract.get("skill") or ""), tool),
            })
    capability_id_proposals.sort(key=lambda item: (str(item.get("skill") or ""), str(item.get("tool") or "")))

    retirement_delta_errors = validate_retirement_delta(
        {str(value) for value in audit_context.get("retirement_pre_ids", [])},
        {str(value) for value in audit_context.get("retirement_post_ids", [])},
        [item for item in audit_context.get("retirement_rows", []) if isinstance(item, dict)],
    )

    if unowned:
        capability_errors.extend(
            {
                "code": "unowned_python_tool",
                "source": str(tools_dir).replace("\\", "/"),
                "skill": None,
                "capability_id": None,
                "tool": tool,
                "message": "python tool is not owned by any Skill contract",
            }
            for tool in unowned
        )
    if duplicate_canonical:
        for tool, owners in duplicate_canonical.items():
            capability_errors.append({
                "code": "duplicate_canonical_owner",
                "source": str(skills_dir).replace("\\", "/"),
                "skill": ",".join(sorted(set(owners))),
                "capability_id": None,
                "tool": tool,
                "message": f"canonical tool has multiple owners: {', '.join(sorted(set(owners)))}",
            })
    repository_errors = audit_repository_contracts(
        contracts,
        python_tools=python_tools,
        dispatch_commands=dispatch_commands,
        catalog_commands=catalog_commands,
        capability_consumers=capability_consumers,
    )
    # The shared repository audit includes pure schema errors; retain one
    # deterministic list for the report rather than duplicating them.
    capability_errors = sorted(
        {json.dumps(item, ensure_ascii=False, sort_keys=True): item for item in [*capability_errors, *repository_errors]}.values(),
        key=lambda item: (
            str(item.get("code") or ""),
            str(item.get("source") or ""),
            str(item.get("skill") or ""),
            str(item.get("tool") or ""),
            str(item.get("capability_id") or ""),
        ),
    )
    errors = [str(item.get("message") or item) for item in capability_errors]
    errors.extend(str(item.get("message") or item) for item in retirement_delta_errors)

    return {
        "artifact_role": "skill_tool_contract_audit_report",
        "version": 1,
        "ok": not capability_errors and not retirement_delta_errors,
        "skills_dir": str(skills_dir).replace("\\", "/"),
        "tools_dir": str(tools_dir).replace("\\", "/"),
        "contract_count": len(contracts),
        "python_tool_count": len(python_tools),
        "owned_python_tool_count": len(python_tools) - len(unowned),
        "unowned_python_tools": unowned,
        "duplicate_canonical_tools": duplicate_canonical,
        "capability_id_proposals": capability_id_proposals,
        "capability_consumer_count": len(capability_consumers),
        "capability_consumers": [
            {
                "consumer": item.get("consumer"),
                "source": item.get("_source"),
                "active_capability_ids": sorted(str(value) for value in item.get("active_capability_ids") or []),
                "active_namespaces": sorted(str(value) for value in item.get("active_namespaces") or []),
            }
            for item in capability_consumers
        ],
        "contracts": [
            {
                "skill": contract.get("skill"),
                "stage_owner": contract.get("stage_owner"),
                "source": contract.get("_source"),
                "canonical_tools": [
                    _normalize_tool_name(str(item.get("tool")))
                    for item in contract.get("canonical_tools", []) or []
                    if isinstance(item, dict)
                ],
                "canonical_commands": [
                    projected_command_ref(item)
                    for item in contract.get("canonical_tools", []) or []
                    if isinstance(item, dict)
                ],
            }
            for contract in contracts
        ],
        "tool_ownership": {tool: sorted(set(owners)) for tool, owners in sorted(ownership.items())},
        "errors": errors,
        "capability_errors": capability_errors,
        "retirement_delta_errors": retirement_delta_errors,
        "duplicate_capability_ids": [item for item in capability_errors if item.get("code") == "duplicate_capability_id"],
        "broken_tool_references": [item for item in capability_errors if item.get("code") == "missing_tool_reference"],
        "broken_command_references": [item for item in capability_errors if item.get("code", "").startswith("command_")],
        "broken_domain_lookups": [item for item in capability_errors if item.get("code") == "broken_domain_lookup"],
        "broken_director_references": [item for item in capability_errors if item.get("code") == "broken_director_reference"],
        "active_legacy_references": [item for item in capability_errors if item.get("code") == "active_legacy_reference"],
        "noncanonical_public_references": [item for item in capability_errors if item.get("code") == "noncanonical_public_reference"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit Hermes skill-to-tool contracts.")
    parser.add_argument("--skills-dir", default="skills")
    parser.add_argument("--tools-dir", default="tools")
    parser.add_argument("--json", action="store_true", help="write report JSON to stdout")
    parser.add_argument("--out", help="write report JSON to this path")
    args = parser.parse_args(argv)

    report = analyze(Path(args.skills_dir), Path(args.tools_dir))
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(payload + "\n", encoding="utf-8")
    if args.json or not args.out:
        print(payload)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
