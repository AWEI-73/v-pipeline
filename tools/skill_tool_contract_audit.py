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
    iter_tool_entries,
    load_contracts,
    normalize_tool_ref,
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


def analyze(skills_dir: Path, tools_dir: Path) -> dict[str, Any]:
    contracts, parse_errors = load_contracts(skills_dir)
    errors = [str(item.get("message") or item) for item in parse_errors]
    errors.extend(validate_contracts(contracts))

    python_tools = discover_python_tools(tools_dir)
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

    if unowned:
        errors.append(f"unowned python tools: {', '.join(unowned)}")
    if duplicate_canonical:
        for tool, owners in duplicate_canonical.items():
            errors.append(f"duplicate canonical owners for {tool}: {', '.join(sorted(set(owners)))}")

    return {
        "artifact_role": "skill_tool_contract_audit_report",
        "version": 1,
        "ok": not errors,
        "skills_dir": str(skills_dir).replace("\\", "/"),
        "tools_dir": str(tools_dir).replace("\\", "/"),
        "contract_count": len(contracts),
        "python_tool_count": len(python_tools),
        "owned_python_tool_count": len(python_tools) - len(unowned),
        "unowned_python_tools": unowned,
        "duplicate_canonical_tools": duplicate_canonical,
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
            }
            for contract in contracts
        ],
        "tool_ownership": {tool: sorted(set(owners)) for tool, owners in sorted(ownership.items())},
        "errors": errors,
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
