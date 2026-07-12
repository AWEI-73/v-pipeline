from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video_pipeline_core.skill_tool_contract import iter_tool_entries, load_contracts, normalize_tool_ref


MAJOR_SIDE_BRANCHES = {
    "material-map",
    "soundtrack-arranger",
    "subtitle-voiceover",
    "effect-factory",
    "workbench-brownfield",
}

INTERFACE_ARTIFACT_SUFFIXES = (
    "_handoff.json",
    "_acceptance.json",
    "_revision_packet.json",
    "_review_report.json",
    "_request.json",
    "_patch.json",
)

BRANCH_OUTPUT_SUFFIXES = (
    "_handoff.json",
    "_acceptance.json",
    "_report.json",
    "_packet.json",
    "_request.json",
    "_patch.json",
    "report.md",
    "_brief.md",
)

INFRASTRUCTURE_TOOL_MARKERS = (
    "_audit.py",
    "_smoke.py",
    "_map.py",
    "pipeline_home.py",
    "pipeline_interface_discovery.py",
    "pipeline_interface_audit.py",
    "skill_tool_contract_audit.py",
    "api_surface_manifest.py",
    "_server.py",
    "test_tiers.py",
    "orphan_audit.py",
)


def extract_tool_contracts(skills_dir: Path) -> list[dict[str, Any]]:
    contracts, _errors = load_contracts(skills_dir)
    return contracts


def _tool_entries(contract: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in iter_tool_entries(contract):
        if item.get("_section") not in {"canonical_tools", "supporting_tools"}:
            continue
        entry = dict(item)
        entry["skill"] = contract.get("skill")
        entry["stage_owner"] = contract.get("stage_owner")
        entry["tool_bucket"] = item.get("_section")
        if entry.get("tool"):
            out.append(entry)
    return out


def scan_tools_directory(tools_dir: Path) -> dict[str, dict[str, Any]]:
    tools_info = {}
    if not tools_dir.exists():
        return tools_info

    # Patterns for outputs in tool files
    artifact_pattern = re.compile(r"['\"]([a-zA-Z0-9_\-]+\.(?:json|jpg|png|mp4|wav))['\"]")

    for py_file in tools_dir.glob("*.py"):
        try:
            content = py_file.read_text(encoding="utf-8-sig")
            
            # Extract argparse description
            desc = ""
            desc_match = re.search(r"ArgumentParser\((?:description=)?['\"](.*?)['\"]", content)
            if desc_match:
                desc = desc_match.group(1)
            else:
                # Fallback to module docstring
                doc_match = re.search(r"^['\"]{3}(.*?)['\"]{3}", content, re.DOTALL)
                if doc_match:
                    desc = doc_match.group(1).strip().split("\n")[0]

            # Find all output artifact candidates
            found_artifacts = set()
            for art in artifact_pattern.findall(content):
                if art.startswith("_"):
                    continue
                if any(suffix in art for suffix in INTERFACE_ARTIFACT_SUFFIXES):
                    found_artifacts.add(art)

            tools_info[f"tools/{py_file.name}"] = {
                "description": desc,
                "potential_outputs": sorted(list(found_artifacts))
            }
        except Exception:
            pass
    return tools_info


def map_tool_to_branch(tool_path: str, skill_name: str | None) -> str:
    # Heuristics based on skill name or tool name
    combined = f"{skill_name or ''} {tool_path}".lower()
    if "subtitle" in combined or "voiceover" in combined or "voxcpm" in combined:
        return "subtitle-voiceover"
    if "material-map" in combined or "curator" in combined:
        return "material-map"
    if "soundtrack" in combined or "audio-director" in combined:
        return "soundtrack-arranger"
    if "effect-factory" in combined or "video-effect" in combined or "remotion-effect" in combined:
        return "effect-factory"
    if "brownfield" in combined or "workbench" in combined or "dashboard" in combined:
        return "workbench-brownfield"
    if "verify" in combined or "reviewer" in combined or "delivery" in combined:
        return "verify-delivery"
    if "pipeline-route" in combined or "pipeline_home" in combined:
        return "main-pipeline"
    return "main-pipeline"


def _looks_like_interface_output(name: Any) -> bool:
    return isinstance(name, str) and any(name.endswith(suffix) for suffix in INTERFACE_ARTIFACT_SUFFIXES)


def _looks_like_branch_output(name: Any) -> bool:
    return isinstance(name, str) and any(name.endswith(suffix) for suffix in BRANCH_OUTPUT_SUFFIXES)


def _is_infrastructure_tool(tool_path: str) -> bool:
    return any(marker in tool_path for marker in INFRASTRUCTURE_TOOL_MARKERS)


def _interface_direction(tool_path: str, skill_name: str | None, branch: str, outputs: list[str]) -> tuple[str, str, str]:
    combined = f"{tool_path} {skill_name or ''}".lower()
    if "final_product_verify" in combined or "revision_packet" in " ".join(outputs):
        return "verify-delivery", branch if branch in MAJOR_SIDE_BRANCHES else "main-pipeline", "repair_route"
    if branch in MAJOR_SIDE_BRANCHES and any(
        output.endswith(("_handoff.json", "_acceptance.json", "_review_report.json"))
        for output in outputs
    ):
        return branch, "main-pipeline", "branch_handoff"
    if branch in MAJOR_SIDE_BRANCHES:
        return "main-pipeline", branch, "branch_request"
    return "main-pipeline", branch, "branch_request"


def _coverage_gaps(existing_interfaces: list[dict[str, Any]]) -> list[dict[str, Any]]:
    coverage = {
        branch: {"request": False, "handoff": False, "repair": False}
        for branch in MAJOR_SIDE_BRANCHES
    }
    for face in existing_interfaces:
        from_b = face.get("from_branch")
        to_b = face.get("to_branch")
        itype = face.get("interface_type")
        if itype == "branch_request" and from_b == "main-pipeline" and to_b in MAJOR_SIDE_BRANCHES:
            coverage[to_b]["request"] = True
        elif itype == "branch_handoff" and from_b in MAJOR_SIDE_BRANCHES and to_b in {"main-pipeline", "verify-delivery"}:
            coverage[from_b]["handoff"] = True
        elif itype == "repair_route" and from_b == "verify-delivery" and to_b in MAJOR_SIDE_BRANCHES:
            coverage[to_b]["repair"] = True

    gaps: list[dict[str, Any]] = []
    for branch, states in sorted(coverage.items()):
        for kind, present in sorted(states.items()):
            if not present:
                gaps.append({
                    "api_id": f"coverage_gap.{branch}.{kind}",
                    "from_branch": "verify-delivery" if kind == "repair" else ("main-pipeline" if kind == "request" else branch),
                    "to_branch": branch if kind in {"request", "repair"} else "main-pipeline",
                    "interface_type": "repair_route" if kind == "repair" else ("branch_request" if kind == "request" else "branch_handoff"),
                    "purpose": f"Missing {kind} interface coverage for {branch}",
                    "request": {"tool": None, "inputs": []},
                    "response": {"outputs": []},
                    "forbidden_writes": ["final.mp4"],
                    "discovery_reason": "major_side_branch_coverage_gap",
                })
    return gaps


def run_discovery(
    dict_path: Path,
    registry_path: Path,
    skills_dir: Path,
    tools_dir: Path,
    project_root: Path
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    # 1. Read existing dictionary
    existing_interfaces = []
    existing_interface_count = 0
    if dict_path.exists():
        try:
            dict_data = json.loads(dict_path.read_text(encoding="utf-8-sig"))
            if dict_data.get("artifact_role") == "pipeline_api_dictionary":
                existing_interfaces = dict_data.get("interfaces", [])
                existing_interface_count = len(existing_interfaces)
            else:
                errors.append(f"Invalid artifact_role in dictionary: {dict_data.get('artifact_role')}")
        except Exception as exc:
            errors.append(f"Failed to parse dictionary JSON: {exc}")
    else:
        warnings.append(f"Dictionary file not found at: {dict_path}")

    # 2. Read branch registry
    valid_branch_ids = set()
    registry_outputs = set()
    registry_inputs = set()
    if registry_path.exists():
        try:
            reg_data = json.loads(registry_path.read_text(encoding="utf-8-sig"))
            for b in reg_data.get("branches", []):
                bid = b.get("branch_id")
                if bid:
                    valid_branch_ids.add(bid)
                for out in b.get("canonical_outputs", []) + b.get("handoff_outputs", []):
                    registry_outputs.add(out)
                for inp in b.get("required_inputs", []):
                    registry_inputs.add(inp)
        except Exception as exc:
            errors.append(f"Failed to parse branch contract registry: {exc}")
    else:
        warnings.append(f"Branch contract registry not found at: {registry_path}")

    # 3. Read skill contracts
    skill_contracts = extract_tool_contracts(skills_dir)
    discovered_tool_entries: list[dict[str, Any]] = []
    for contract in skill_contracts:
        discovered_tool_entries.extend(_tool_entries(contract))
    discovered_tool_keys = {
        (entry.get("tool"), entry.get("skill"))
        for entry in discovered_tool_entries
        if entry.get("tool")
    }

    # 4. Scan tools directory
    tools_info = scan_tools_directory(tools_dir)

    # Dictionary coverage helpers
    covered_tools = set()
    covered_outputs = set()
    dictionary_inputs = set()
    for face in existing_interfaces:
        req = face.get("request", {})
        if req and req.get("tool"):
            covered_tools.add(req.get("tool"))
        resp = face.get("response", {})
        if resp and resp.get("outputs"):
            for out in resp.get("outputs", []):
                covered_outputs.add(out)
        if req and req.get("inputs"):
            for inp in req.get("inputs", []):
                dictionary_inputs.add(inp)
        trigger = face.get("trigger", {})
        if trigger and trigger.get("artifact"):
            dictionary_inputs.add(trigger.get("artifact"))

    # 5. Build candidate interfaces from skill contracts and tools scanning
    candidate_interfaces = []
    for entry in sorted(discovered_tool_entries, key=lambda item: str(item.get("tool"))):
        tool_path = str(entry.get("tool") or "")
        skill_name = entry.get("skill")
        if not tool_path.startswith("tools/"):
            continue
        if _is_infrastructure_tool(tool_path):
            continue
        t_info = tools_info.get(tool_path, {})
        contract_outputs = [
            output for output in entry.get("outputs", []) or []
            if _looks_like_interface_output(output)
        ]
        scanned_outputs = [
            output for output in t_info.get("potential_outputs", []) or []
            if _looks_like_interface_output(output)
        ]
        potential_outputs = sorted(set(contract_outputs + scanned_outputs))
        if not potential_outputs:
            continue

        mapped_branch = map_tool_to_branch(tool_path, skill_name)
        if mapped_branch not in MAJOR_SIDE_BRANCHES and mapped_branch != "verify-delivery":
            continue
        from_b, to_b, itype = _interface_direction(tool_path, skill_name, mapped_branch, potential_outputs)
        if from_b == to_b:
            continue

        api_id = f"{from_b}.to.{to_b}.{Path(tool_path).stem}"
        candidate_interfaces.append({
            "api_id": api_id,
            "from_branch": from_b,
            "to_branch": to_b,
            "interface_type": itype,
            "purpose": entry.get("when") or t_info.get("description") or f"Auto-discovered interface for {tool_path}",
            "request": {
                "tool": tool_path,
                "inputs": entry.get("inputs", []),
            },
            "response": {
                "outputs": potential_outputs,
            },
            "forbidden_writes": ["final.mp4"],
            "discovery_reason": "tool_contract_interface_outputs",
        })

    # Deduplicate candidate interfaces
    unique_candidates = []
    seen_cand_ids = set()
    for cand in candidate_interfaces:
        if cand["api_id"] not in seen_cand_ids:
            seen_cand_ids.add(cand["api_id"])
            unique_candidates.append(cand)

    # 6. Find missing dictionary candidates
    missing_dictionary_candidates = _coverage_gaps(existing_interfaces)
    for cand in unique_candidates:
        tool_ref = cand["request"]["tool"]
        outputs_ref = cand["response"]["outputs"]
        
        # Covered check
        is_covered = (
            tool_ref in covered_tools
            and any(out in covered_outputs or out in dictionary_inputs for out in outputs_ref)
        ) or any(out in covered_outputs for out in outputs_ref)
        if not is_covered:
            missing_dictionary_candidates.append(cand)

    # 7. Find stale dictionary interfaces
    stale_dictionary_interfaces = []
    for face in existing_interfaces:
        api_id = face.get("api_id")
        from_b = face.get("from_branch")
        to_b = face.get("to_branch")
        req = face.get("request", {})
        tool_ref = req.get("tool") if req else None

        stale_reason = []
        if from_b and from_b not in valid_branch_ids:
            stale_reason.append(f"from_branch '{from_b}' not in registry")
        if to_b and to_b not in valid_branch_ids:
            stale_reason.append(f"to_branch '{to_b}' not in registry")
        
        if tool_ref:
            # Handle split by OR
            parts = [p.strip() for p in str(tool_ref).split(" OR ")]
            for part in parts:
                if part.startswith("tools/") and part.endswith(".py"):
                    full_tool_path = project_root / part
                    if not full_tool_path.is_file():
                        stale_reason.append(f"tool file '{part}' does not exist")
                elif "video_tools.py" in part:
                    vt_path = project_root / "video_tools.py"
                    if not vt_path.is_file():
                        stale_reason.append("video_tools.py does not exist")

        if stale_reason:
            stale_dictionary_interfaces.append({
                "api_id": api_id,
                "reasons": stale_reason
            })

    # 8. Find unmapped branch outputs
    unmapped_branch_outputs = []
    for out in sorted(list(registry_outputs)):
        # Check if it looks like handoff/report/acceptance/revision/request
        if _looks_like_branch_output(out):
            # Check if mentioned in dictionary outputs or inputs
            if out not in covered_outputs and out not in dictionary_inputs:
                unmapped_branch_outputs.append(out)

    report = {
        "artifact_role": "pipeline_interface_discovery_report",
        "ok": not errors,
        "existing_interface_count": existing_interface_count,
        "discovered_tool_count": len(discovered_tool_keys),
        "candidate_interfaces": unique_candidates,
        "missing_dictionary_candidates": missing_dictionary_candidates,
        "stale_dictionary_interfaces": stale_dictionary_interfaces,
        "unmapped_branch_outputs": unmapped_branch_outputs,
        "warnings": warnings,
        "errors": errors
    }

    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Discover and suggest pipeline interface alignment candidates.")
    parser.add_argument("--dictionary", default="docs/interface-contracts/pipeline-api-dictionary.json", help="Path to dictionary JSON")
    parser.add_argument("--registry", default="docs/branch-contract-registry.json", help="Path to branch registry")
    parser.add_argument("--skills-dir", default="skills", help="Skills directory")
    parser.add_argument("--tools-dir", default="tools", help="Tools directory")
    parser.add_argument("--out", help="Write JSON report to file")
    parser.add_argument("--json", action="store_true", help="Write report JSON to stdout")
    args = parser.parse_args(argv)

    project_root = Path(__file__).resolve().parent.parent
    dict_path = Path(args.dictionary)
    registry_path = Path(args.registry)
    skills_path = Path(args.skills_dir)
    tools_path = Path(args.tools_dir)

    report = run_discovery(dict_path, registry_path, skills_path, tools_path, project_root)

    # Output selection
    payload = json.dumps(report, ensure_ascii=False, indent=2)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(payload, encoding="utf-8")

    if args.json:
        print(payload)
    else:
        print("Pipeline Interface Discovery:")
        print(f"  Existing Interfaces: {report['existing_interface_count']}")
        print(f"  Discovered Tools: {report['discovered_tool_count']}")
        print(f"  Candidate Interfaces found: {len(report['candidate_interfaces'])}")
        print(f"  Missing dictionary candidates: {len(report['missing_dictionary_candidates'])}")
        print(f"  Stale dictionary interfaces: {len(report['stale_dictionary_interfaces'])}")
        print(f"  Unmapped branch outputs: {len(report['unmapped_branch_outputs'])}")
        if report["errors"]:
            print("Errors:", file=sys.stderr)
            for err in report["errors"]:
                print(f"  - {err}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
