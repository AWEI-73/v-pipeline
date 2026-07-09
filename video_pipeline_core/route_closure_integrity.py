"""Machine checks for product-route closure facts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from video_pipeline_core.graduation_product_route_runner import (
    REVIEW_KINDS,
    ROUTE_STAGES,
    VERIFY_KINDS,
)
from video_pipeline_core.next_action_vocabulary import NEXT_ACTION_VOCABULARY
from video_pipeline_core.reviewer_registry import build_reviewer_registry


def _as_set(values: Iterable[Any]) -> set[str]:
    return {str(value) for value in values if value}


def _branch_artifacts(branches: list[Mapping[str, Any]]) -> set[str]:
    artifacts: set[str] = set()
    for branch in branches:
        for key in ("canonical_outputs", "handoff_outputs"):
            artifacts.update(_as_set(branch.get(key, [])))
    return artifacts


def _reviewer_output_artifacts(reviewer_roles: set[str] | None = None) -> set[str]:
    registry = build_reviewer_registry()
    outputs = {
        str(item.get("output_artifact"))
        for item in registry.get("reviewers", [])
        if item.get("output_artifact")
        and (reviewer_roles is None or item.get("reviewer_role") in reviewer_roles)
    }
    return outputs


def _review_artifacts(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value if item]
    return []


def validate_route_closure(
    *,
    route_stages: list[Mapping[str, Any]],
    branch_registry: Mapping[str, Any],
    next_actions: set[str],
    reviewer_roles: set[str] | None,
) -> dict[str, Any]:
    branches = [b for b in branch_registry.get("branches", []) if isinstance(b, Mapping)]
    branch_ids = {str(branch.get("branch_id")) for branch in branches if branch.get("branch_id")}
    registry_artifacts = _branch_artifacts(branches)
    reviewer_artifacts = _reviewer_output_artifacts(reviewer_roles)
    valid_kinds = set(VERIFY_KINDS) | set(REVIEW_KINDS)
    errors: list[str] = []
    stage_summaries: list[dict[str, Any]] = []

    for stage in route_stages:
        stage_id = str(stage.get("stage_id") or "")
        owner = str(stage.get("owner") or "")
        kind = str(stage.get("kind") or "")
        artifact = stage.get("artifact")
        review_artifacts = _review_artifacts(stage.get("review_artifact"))

        if not owner:
            errors.append(f"missing_owner:{stage_id}")
        elif owner not in branch_ids:
            errors.append(f"unknown_owner:{stage_id}:{owner}")

        if not kind:
            errors.append(f"missing_kind:{stage_id}")
        elif kind not in valid_kinds:
            errors.append(f"invalid_kind:{stage_id}:{kind}")

        if kind == "signed_review" and not review_artifacts:
            errors.append(f"missing_review_artifact:{stage_id}")

        for review_artifact in review_artifacts:
            if review_artifact not in registry_artifacts and review_artifact not in reviewer_artifacts:
                errors.append(f"unregistered_review_artifact:{stage_id}:{review_artifact}")

        if isinstance(artifact, str) and artifact and artifact not in registry_artifacts:
            errors.append(f"stage_artifact_not_registered:{stage_id}:{artifact}")

        for action in _as_set(stage.get("next_actions", [])):
            if action not in next_actions:
                errors.append(f"invalid_next_action:{stage_id}:{action}")

        stage_summaries.append(
            {
                "stage_id": stage_id,
                "owner": owner,
                "kind": kind,
                "artifact": artifact,
                "review_artifacts": review_artifacts,
            }
        )

    return {
        "artifact_role": "route_closure_integrity_report",
        "version": 1,
        "ok": not errors,
        "errors": sorted(errors),
        "route_stages": stage_summaries,
        "registered_branch_count": len(branch_ids),
        "registered_artifact_count": len(registry_artifacts),
    }


def validate_current_route_closure(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root)
    registry = json.loads((root / "docs" / "branch-contract-registry.json").read_text(encoding="utf-8"))
    reviewer_roles = {
        str(item.get("reviewer_role"))
        for item in build_reviewer_registry().get("reviewers", [])
        if item.get("reviewer_role")
    }
    return validate_route_closure(
        route_stages=ROUTE_STAGES,
        branch_registry=registry,
        next_actions=set(NEXT_ACTION_VOCABULARY),
        reviewer_roles=reviewer_roles,
    )


def write_route_closure_integrity_report(repo_root: str | Path, out: str | Path) -> dict[str, Any]:
    report = validate_current_route_closure(repo_root)
    path = Path(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report
