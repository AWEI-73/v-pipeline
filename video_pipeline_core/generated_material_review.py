"""Review and promote generated material candidates.

Generated assets enter material maps as candidate evidence. This module applies
an explicit reviewer verdict that can promote those candidates to accepted or
rejected. It never auto-accepts generated files.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from .material_needs import VALID_STATUSES, validate_material_needs
from .project_material_map import build_project_material_map


REVIEW_STATUSES = ("accepted", "rejected")
CANONICAL_WAIVER_FIELDS = ("reviewer", "reason", "at")


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _error(errors: list[str]) -> dict:
    return {
        "artifact_role": "generated_material_review_result",
        "version": 1,
        "ok": False,
        "errors": errors,
        "project_material_map": None,
        "summary": {"accepted": 0, "rejected": 0},
    }


def _canonical_quality_waiver(value: Any) -> dict | None:
    if not isinstance(value, Mapping):
        return None
    if not all(_text(value.get(key)) for key in CANONICAL_WAIVER_FIELDS):
        return None
    return {key: _text(value.get(key)) for key in CANONICAL_WAIVER_FIELDS}


def _quality_index(quality_review: Mapping[str, Any] | None) -> dict[str, dict]:
    if not isinstance(quality_review, Mapping):
        return {}
    index = {}
    for item in quality_review.get("items") or []:
        if not isinstance(item, Mapping):
            continue
        for key in ("job_id", "asset_id", "segment"):
            value = _text(item.get(key))
            if value and value not in index:
                index[value] = dict(item)
    return index


def _quality_item_for(edge: Mapping[str, Any], asset_id: str, index: Mapping[str, dict]) -> dict | None:
    lineage = edge.get("lineage") if isinstance(edge.get("lineage"), Mapping) else {}
    for key in ("generated_job_id", "job_id", "generated_asset_id"):
        value = _text(lineage.get(key))
        if value and value in index:
            return index[value]
    if asset_id in index:
        return index[asset_id]
    return None


def _validate_inputs(project_map: Mapping[str, Any], verdict: Mapping[str, Any],
                     material_needs: Mapping[str, Any]) -> tuple[list[str], set[str]]:
    errors: list[str] = []
    needs_result = validate_material_needs(material_needs)
    if not needs_result["ok"]:
        errors.append("material_needs invalid: " + "; ".join(needs_result["errors"]))
    known_need_ids = {need["need_id"] for need in needs_result.get("needs") or []}
    if not isinstance(project_map, Mapping) or project_map.get("artifact_role") != "project_material_map":
        errors.append("project_material_map artifact required")
    if not isinstance(verdict, Mapping):
        errors.append("review verdict must be an object")
        return errors, known_need_ids
    if not _text(verdict.get("reviewer")):
        errors.append("reviewer must be a non-empty string")
    decisions = verdict.get("decisions")
    if not isinstance(decisions, list) or not decisions:
        errors.append("decisions must be a non-empty list")
        return errors, known_need_ids
    for index, decision in enumerate(decisions):
        ref = f"decision {index}"
        if not isinstance(decision, Mapping):
            errors.append(f"{ref} must be an object")
            continue
        for key in ("asset_id", "need_id", "reason"):
            if not _text(decision.get(key)):
                errors.append(f"{ref} {key} must be a non-empty string")
        scene_index = decision.get("scene_index")
        if not isinstance(scene_index, int) or isinstance(scene_index, bool) or scene_index < 0:
            errors.append(f"{ref} scene_index must be a non-negative integer")
        status = decision.get("status")
        if status not in REVIEW_STATUSES:
            errors.append(f"{ref} status must be accepted or rejected, got {status!r}")
        need_id = _text(decision.get("need_id"))
        if need_id and known_need_ids and need_id not in known_need_ids:
            errors.append(f"{ref} references unknown need_id {need_id!r}")
    return errors, known_need_ids


def _scene_source_type(scene: Mapping[str, Any], asset: Mapping[str, Any]) -> str:
    return _text(scene.get("source_type") or asset.get("source_type"))


def _find_edge(scene: Mapping[str, Any], need_id: str) -> dict | None:
    for edge in scene.get("satisfies") or []:
        if isinstance(edge, dict) and edge.get("need_id") == need_id:
            return edge
    return None


def apply_generated_material_review(
    project_map: Mapping[str, Any],
    verdict: Mapping[str, Any],
    material_needs: Mapping[str, Any],
    *,
    quality_review: Mapping[str, Any] | None = None,
) -> dict:
    errors, _known = _validate_inputs(project_map, verdict, material_needs)
    if errors:
        return _error(errors)

    reviewed = deepcopy(project_map)
    assets = reviewed.get("assets") or []
    asset_index = {
        asset.get("asset_id"): asset
        for asset in assets
        if isinstance(asset, dict) and _text(asset.get("asset_id"))
    }
    counts = {"accepted": 0, "rejected": 0}
    reviewer = _text(verdict.get("reviewer"))
    at = _text(verdict.get("at"))
    quality_by_id = _quality_index(quality_review)

    for decision in verdict.get("decisions") or []:
        asset_id = _text(decision.get("asset_id"))
        scene_index = decision.get("scene_index")
        need_id = _text(decision.get("need_id"))
        status = decision.get("status")
        reason = _text(decision.get("reason"))
        asset = asset_index.get(asset_id)
        if not asset:
            errors.append(f"unknown review target asset_id={asset_id!r}")
            continue
        scenes = asset.get("scenes") or []
        if not isinstance(scene_index, int) or scene_index >= len(scenes):
            errors.append(f"unknown review target asset_id={asset_id!r} scene_index={scene_index!r}")
            continue
        scene = scenes[scene_index]
        edge = _find_edge(scene, need_id)
        if not edge:
            errors.append(
                f"unknown review target asset_id={asset_id!r} scene_index={scene_index!r} need_id={need_id!r}")
            continue
        if edge.get("status") != "candidate":
            errors.append(f"not generated candidate: current status is {edge.get('status')!r}")
            continue
        source_type = _scene_source_type(scene, asset)
        lineage = edge.get("lineage") if isinstance(edge.get("lineage"), dict) else {}
        generated_lineage = bool(lineage.get("generated_job_id") or lineage.get("generated_panel_index"))
        if source_type and source_type != "generated":
            errors.append("not generated candidate: review target is not generated material")
            continue
        if not source_type and not generated_lineage:
            errors.append("not generated candidate: review target is not generated material")
            continue
        if status not in VALID_STATUSES:
            errors.append(f"invalid status {status!r}")
            continue
        quality_item = _quality_item_for(edge, asset_id, quality_by_id)
        quality_failed = bool(quality_item and quality_item.get("pass") is False)
        quality_waiver = _canonical_quality_waiver(decision.get("quality_waiver"))
        if status == "accepted" and quality_failed and not quality_waiver:
            score = quality_item.get("score")
            errors.append(
                f"quality review failed for asset_id={asset_id!r} need_id={need_id!r}"
                + (f" score={score!r}" if score is not None else "")
            )
            continue
        edge["status"] = status
        edge["lineage"] = dict(lineage)
        edge["lineage"].update({
            "reviewer": reviewer,
            "reason": reason,
            "previous_status": "candidate",
        })
        if quality_item:
            edge["lineage"]["quality_review"] = {
                "pass": quality_item.get("pass"),
                "score": quality_item.get("score"),
                "findings": list(quality_item.get("findings") or []),
            }
        if quality_waiver:
            edge["lineage"]["quality_waiver"] = quality_waiver
        if at:
            edge["lineage"]["at"] = at
        counts[status] += 1

    if errors:
        return _error(errors)
    try:
        rebuilt = build_project_material_map(reviewed["assets"], needs=material_needs)
    except ValueError as exc:
        return _error([str(exc)])
    return {
        "artifact_role": "generated_material_review_result",
        "version": 1,
        "ok": True,
        "errors": [],
        "project_material_map": rebuilt,
        "summary": counts,
    }
