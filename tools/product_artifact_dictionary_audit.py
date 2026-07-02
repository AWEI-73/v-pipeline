from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REQUIRED_ARTIFACTS = {
    "source_media_review.json",
    "material_matrix.json",
    "edit_decision_plan.json",
    "audio_decision_plan.json",
    "effect_decision_plan.json",
    "subtitle_voiceover_decision_plan.json",
    "build_handoff.json",
    "final_review_bundle.json",
}

REQUIRED_FIELDS = {
    "artifact_name",
    "owner_branch",
    "purpose",
    "semantic_inputs",
    "functional_parameters",
    "downstream_consumers",
    "review_focus",
    "canonical_write_policy",
}


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object: {path}")
    return data


def _validate_list_field(api_id: str, field: str, value: Any, errors: list[str]) -> None:
    if not isinstance(value, list) or not value:
        errors.append(f"Artifact '{api_id}': {field} must be a non-empty list")


def audit_product_dictionary(dict_path: str | Path) -> tuple[list[str], list[str], int]:
    path = Path(dict_path)
    errors: list[str] = []
    warnings: list[str] = []
    if not path.is_file():
        return [f"Product artifact dictionary not found: {path}"], warnings, 0

    try:
        data = _load_json(path)
    except Exception as exc:
        return [f"Failed to parse product artifact dictionary: {exc}"], warnings, 0

    if data.get("artifact_role") != "pipeline_product_artifact_dictionary":
        errors.append(
            "Invalid artifact_role: expected 'pipeline_product_artifact_dictionary', "
            f"got '{data.get('artifact_role')}'"
        )
    if data.get("version") != 1:
        errors.append(f"Invalid version: expected 1, got '{data.get('version')}'")

    artifacts = data.get("artifacts")
    if not isinstance(artifacts, list):
        errors.append("Field 'artifacts' must be a list")
        return errors, warnings, 0

    seen: set[str] = set()
    for idx, artifact in enumerate(artifacts):
        if not isinstance(artifact, dict):
            errors.append(f"Artifact index {idx} is not a dictionary")
            continue
        name = artifact.get("artifact_name") or f"index_{idx}"
        if name in seen:
            errors.append(f"Duplicate artifact_name found: '{name}'")
        seen.add(str(name))

        for field in REQUIRED_FIELDS:
            if field not in artifact:
                errors.append(f"Artifact '{name}': missing {field}")

        for field in (
            "semantic_inputs",
            "functional_parameters",
            "downstream_consumers",
            "review_focus",
        ):
            _validate_list_field(str(name), field, artifact.get(field), errors)

        policy = artifact.get("canonical_write_policy")
        if policy not in {"read_only", "draft_only", "handoff_only", "canonical_candidate"}:
            errors.append(
                f"Artifact '{name}': canonical_write_policy must be one of "
                "read_only, draft_only, handoff_only, canonical_candidate"
            )

    missing = sorted(REQUIRED_ARTIFACTS - {str(item.get("artifact_name")) for item in artifacts if isinstance(item, dict)})
    for name in missing:
        errors.append(f"Missing required product artifact: {name}")

    return errors, warnings, len(artifacts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit Hermes product artifact dictionary.")
    parser.add_argument(
        "--dictionary",
        default="docs/interface-contracts/pipeline-product-artifact-dictionary.json",
        help="Path to product artifact dictionary JSON.",
    )
    parser.add_argument("--json", action="store_true", help="Write JSON report to stdout.")
    args = parser.parse_args(argv)

    errors, warnings, count = audit_product_dictionary(args.dictionary)
    report = {
        "artifact_role": "pipeline_product_artifact_dictionary_audit_report",
        "ok": not errors,
        "artifact_count": count,
        "errors": errors,
        "warnings": warnings,
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif errors:
        print("Product Artifact Dictionary Audit: FAILED", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    else:
        print(f"Product Artifact Dictionary Audit: OK ({count} artifacts audited)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
