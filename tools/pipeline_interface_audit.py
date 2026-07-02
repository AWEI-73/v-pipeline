from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


MAJOR_SIDE_BRANCHES = {
    "material-map",
    "soundtrack-arranger",
    "subtitle-voiceover",
    "effect-factory",
    "workbench-brownfield",
}

ALLOWED_INTERFACE_TYPES = {"branch_request", "branch_handoff", "repair_route"}

MANIFEST_HANDOFF_OUTPUTS = {
    "audio_director_handoff.json",
    "effect_handoff.json",
    "remotion_effect_handoff.json",
    "material_delta.json",
    "material_map_lifecycle.json",
    "subtitle_voiceover_build_handoff.json",
    "subtitle_voiceover_handoff_acceptance.json",
    "workbench_handoff.json",
}

GLOBAL_NEXT_ACTIONS = {
    "ask_user_or_blocked",
    "material_understanding_or_scope_review",
    "material_wall_verdict_draft",
    "material_review_required_or_blocked",
    "audio_director_mix_or_build",
    "visual_technique_plan",
    "return_to_build_or_verify",
}


def _valid_next_actions(branches: list[dict[str, Any]]) -> set[str]:
    actions = set(GLOBAL_NEXT_ACTIONS)
    for branch in branches:
        for action in branch.get("next_actions", []) or []:
            if isinstance(action, str) and action:
                actions.add(action)
    return actions


def _validate_next_action(api_id: str, field: str, action: Any, valid_actions: set[str], errors: list[str]) -> None:
    if not action:
        errors.append(f"Interface '{api_id}': response.{field} is required")
        return
    if not isinstance(action, str):
        errors.append(f"Interface '{api_id}': response.{field} must be a string")
        return
    if action.endswith(".json"):
        errors.append(
            f"Interface '{api_id}': response.{field} must be an action id, not artifact filename '{action}'"
        )
        return
    if action not in valid_actions:
        errors.append(
            f"Interface '{api_id}': response.{field} '{action}' is not declared in branch next_actions or global actions"
        )


def _has_manifest_registrable_handoff_output(outputs: Any) -> bool:
    if not isinstance(outputs, list):
        return False
    for output in outputs:
        if not isinstance(output, str):
            continue
        if output in MANIFEST_HANDOFF_OUTPUTS or output.endswith("_handoff.json") or output.endswith("_build_handoff.json"):
            return True
    return False


def audit_dictionary(dict_path: Path, registry_path: Path, project_root: Path) -> tuple[list[str], list[str], int]:
    errors: list[str] = []
    warnings: list[str] = []
    interface_count = 0

    if not dict_path.exists():
        errors.append(f"Dictionary file not found at: {dict_path}")
        return errors, warnings, 0

    if not registry_path.exists():
        errors.append(f"Branch registry file not found at: {registry_path}")
        return errors, warnings, 0

    # 1. Parse dictionary JSON
    try:
        dict_data = json.loads(dict_path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"Failed to parse dictionary JSON: {exc}")
        return errors, warnings, 0

    # 2. Check artifact_role
    if dict_data.get("artifact_role") != "pipeline_api_dictionary":
        errors.append(f"Invalid artifact_role: expected 'pipeline_api_dictionary', got '{dict_data.get('artifact_role')}'")
    if dict_data.get("version") != 1:
        errors.append(f"Invalid version: expected 1, got '{dict_data.get('version')}'")

    # Load branch registry for branch ID validation
    try:
        registry_data = json.loads(registry_path.read_text(encoding="utf-8"))
        branches = registry_data.get("branches", [])
        valid_branch_ids = {b.get("branch_id") for b in branches if isinstance(b, dict)}
        valid_next_actions = _valid_next_actions(branches)
    except Exception as exc:
        errors.append(f"Failed to parse branch contract registry: {exc}")
        return errors, warnings, 0

    interfaces = dict_data.get("interfaces", [])
    if not isinstance(interfaces, list):
        errors.append("Field 'interfaces' must be a list")
        return errors, warnings, 0

    interface_count = len(interfaces)
    seen_ids: set[str] = set()

    has_request: dict[str, bool] = {b: False for b in MAJOR_SIDE_BRANCHES}
    has_handoff: dict[str, bool] = {b: False for b in MAJOR_SIDE_BRANCHES}
    has_repair: dict[str, bool] = {b: False for b in MAJOR_SIDE_BRANCHES}

    for idx, face in enumerate(interfaces):
        if not isinstance(face, dict):
            errors.append(f"Interface index {idx} is not a dictionary")
            continue

        api_id = face.get("api_id")
        from_b = face.get("from_branch")
        to_b = face.get("to_branch")
        itype = face.get("interface_type")
        trigger = face.get("trigger")
        forbidden = face.get("forbidden_writes")

        # 3. Check necessary fields
        if not api_id:
            errors.append(f"Interface index {idx}: missing api_id")
            api_id = f"index_{idx}"
        
        # Check duplicate api_id (Rule 9)
        if api_id in seen_ids:
            errors.append(f"Duplicate api_id found: '{api_id}'")
        seen_ids.add(api_id)

        if not from_b:
            errors.append(f"Interface '{api_id}': missing from_branch")
        if not to_b:
            errors.append(f"Interface '{api_id}': missing to_branch")
        if not itype:
            errors.append(f"Interface '{api_id}': missing interface_type")
        elif itype not in ALLOWED_INTERFACE_TYPES:
            errors.append(f"Interface '{api_id}': unsupported interface_type '{itype}'")
        if not trigger:
            errors.append(f"Interface '{api_id}': missing trigger")
        elif not isinstance(trigger, dict) or not trigger.get("artifact") or not trigger.get("condition"):
            errors.append(f"Interface '{api_id}': trigger must include artifact and condition")
        if forbidden is None:
            errors.append(f"Interface '{api_id}': missing forbidden_writes")

        if "request" not in face and "response" not in face:
            errors.append(f"Interface '{api_id}': must have at least one of 'request' or 'response'")
        response_obj = face.get("response")
        if not isinstance(response_obj, dict):
            errors.append(f"Interface '{api_id}': missing response object")
        else:
            outputs = response_obj.get("outputs")
            if not isinstance(outputs, list) or not outputs:
                errors.append(f"Interface '{api_id}': response.outputs must be a non-empty list")
            elif itype == "branch_handoff" and not _has_manifest_registrable_handoff_output(outputs):
                errors.append(
                    f"Interface '{api_id}': branch_handoff response.outputs must include at least one manifest-registrable handoff artifact"
                )
            _validate_next_action(
                api_id,
                "success_next_action",
                response_obj.get("success_next_action"),
                valid_next_actions,
                errors,
            )
            _validate_next_action(
                api_id,
                "failure_next_action",
                response_obj.get("failure_next_action"),
                valid_next_actions,
                errors,
            )

        # 4. branch_id registry check
        if from_b and from_b not in valid_branch_ids:
            errors.append(f"Interface '{api_id}': from_branch '{from_b}' is not in registry")
        if to_b and to_b not in valid_branch_ids:
            errors.append(f"Interface '{api_id}': to_branch '{to_b}' is not in registry")

        # Track side branch interface coverage
        if from_b == "main-pipeline" and to_b in MAJOR_SIDE_BRANCHES:
            has_request[to_b] = True
        if from_b in MAJOR_SIDE_BRANCHES and to_b in ("main-pipeline", "verify-delivery"):
            has_handoff[from_b] = True
        if from_b == "verify-delivery" and to_b in MAJOR_SIDE_BRANCHES:
            has_repair[to_b] = True

        # 5. forbidden_writes contains final.mp4 for branch request/handoff/repair
        if itype in ("branch_request", "branch_handoff", "repair_route"):
            if not isinstance(forbidden, list) or "final.mp4" not in forbidden:
                errors.append(f"Interface '{api_id}': forbidden_writes must contain 'final.mp4'")

        # 6. Side branch returning to main must forbid writing final.mp4
        if to_b == "main-pipeline" and from_b != "main-pipeline":
            if not isinstance(forbidden, list) or "final.mp4" not in forbidden:
                errors.append(f"Interface '{api_id}': returning to main-pipeline must forbid writing 'final.mp4'")

        # 7. request.tool validation
        request_obj = face.get("request")
        if not isinstance(request_obj, dict):
            errors.append(f"Interface '{api_id}': missing request object")
        else:
            inputs = request_obj.get("inputs")
            required_fields = request_obj.get("required_fields")
            if not isinstance(inputs, list) or not inputs:
                errors.append(f"Interface '{api_id}': request.inputs must be a non-empty list")
            if not isinstance(required_fields, list) or not required_fields:
                errors.append(f"Interface '{api_id}': request.required_fields must be a non-empty list")
            tool = request_obj.get("tool")
            if not tool:
                errors.append(f"Interface '{api_id}': request.tool is required")
            else:
                # Can be split by OR
                parts = [p.strip() for p in str(tool).split(" OR ")]
                for part in parts:
                    if part.startswith("tools/") and part.endswith(".py"):
                        tool_path = project_root / part
                        if not tool_path.is_file():
                            errors.append(f"Interface '{api_id}': referenced tool '{part}' does not exist")
                    elif "video_tools.py" in part:
                        # video_tools.py should exist in project root
                        vt_path = project_root / "video_tools.py"
                        if not vt_path.is_file():
                            errors.append(f"Interface '{api_id}': referenced video_tools.py does not exist")
                    elif part.startswith("python "):
                        # general command line trigger, e.g. python video_tools.py
                        pass
                    else:
                        warnings.append(f"Interface '{api_id}': tool '{part}' uses unrecognized naming convention")

    # 8. Check major side branch coverage
    for b in MAJOR_SIDE_BRANCHES:
        if not has_request[b]:
            errors.append(f"Missing interface coverage: no request route from main-pipeline to '{b}'")
        if not has_handoff[b]:
            errors.append(f"Missing interface coverage: no handoff/return route from '{b}' to main-pipeline/verify-delivery")
        if not has_repair[b]:
            errors.append(f"Missing interface coverage: no repair route from verify-delivery to '{b}'")

    return errors, warnings, interface_count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit Hermes pipeline interface contracts.")
    parser.add_argument("--dictionary", default="docs/interface-contracts/pipeline-api-dictionary.json", help="Path to dictionary JSON")
    parser.add_argument("--registry", default="docs/branch-contract-registry.json", help="Path to branch registry")
    parser.add_argument("--json", action="store_true", help="Write report JSON to stdout")
    args = parser.parse_args(argv)

    project_root = Path(__file__).resolve().parent.parent
    dict_path = Path(args.dictionary)
    registry_path = Path(args.registry)

    errors, warnings, count = audit_dictionary(dict_path, registry_path, project_root)
    ok = not errors

    report = {
        "artifact_role": "pipeline_interface_audit_report",
        "ok": ok,
        "interface_count": count,
        "errors": errors,
        "warnings": warnings
    }

    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if args.json:
        print(payload)
    else:
        if ok:
            print(f"Pipeline Interface Audit: OK ({count} interfaces audited)")
            if warnings:
                print("Warnings:")
                for w in warnings:
                    print(f"  - {w}")
        else:
            print("Pipeline Interface Audit: FAILED", file=sys.stderr)
            for err in errors:
                print(f"  - {err}", file=sys.stderr)
            if warnings:
                print("Warnings:", file=sys.stderr)
                for w in warnings:
                    print(f"  - {w}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
