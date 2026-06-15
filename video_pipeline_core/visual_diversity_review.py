"""Apply an Agent-authored VD0 shallow-label review to a project material map."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path


LABEL_AXES = ("visual_family", "angle_scale", "action_family", "subject")
ANGLE_SCALES = ("wide", "medium", "close")


def _nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def _scene_lookup(project_map, errors=None):
    errors = errors if errors is not None else []
    lookup = {}
    assets = project_map.get("assets")
    if not isinstance(assets, list):
        errors.append("project_map.assets must be a list")
        return lookup
    asset_ids = set()
    for asset_index, asset in enumerate(assets):
        ref = f"project_map.assets[{asset_index}]"
        if not isinstance(asset, dict):
            errors.append(f"{ref} must be an object")
            continue
        asset_id = asset.get("asset_id")
        if not _nonempty(asset_id):
            errors.append(f"{ref}.asset_id must be a non-empty string")
            continue
        if asset_id in asset_ids:
            errors.append(f"duplicate project-map asset_id {asset_id!r}")
            continue
        asset_ids.add(asset_id)
        scenes = asset.get("scenes")
        if not isinstance(scenes, list):
            errors.append(f"{ref}.scenes must be a list")
            continue
        for scene_index, scene in enumerate(scenes):
            if not isinstance(scene, dict):
                errors.append(f"{ref}.scenes[{scene_index}] must be an object")
                continue
            lookup[(asset_id, scene_index)] = scene
    return lookup


def apply_visual_diversity_review(project_map, review):
    """Return a reviewed project-map copy or fail closed with validation errors."""
    errors = []
    if not isinstance(project_map, dict) or project_map.get("artifact_role") != "project_material_map":
        errors.append("project_map must be a project_material_map artifact")
    if not isinstance(review, dict) or review.get("artifact_role") != "visual_diversity_review":
        errors.append("review must be a visual_diversity_review artifact")
        review = {}
    reviewer = review.get("reviewer")
    at = review.get("at")
    if not _nonempty(reviewer):
        errors.append("reviewer must be a non-empty string")
    if not _nonempty(at):
        errors.append("at must be a non-empty string supplied by the reviewer")
    items = review.get("scenes")
    if not isinstance(items, list):
        errors.append("review.scenes must be a list")
        items = []

    lookup = _scene_lookup(project_map, errors) if not errors else {}
    seen = set()
    validated = []
    for index, item in enumerate(items):
        ref = f"review.scenes[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{ref} must be an object")
            continue
        asset_id = item.get("asset_id")
        scene_index = item.get("scene_index")
        asset_id_valid = _nonempty(asset_id)
        scene_index_valid = (
            not isinstance(scene_index, bool)
            and isinstance(scene_index, int)
            and scene_index >= 0
        )
        if not asset_id_valid:
            errors.append(f"{ref}.asset_id must be a non-empty string")
        if not scene_index_valid:
            errors.append(f"{ref}.scene_index must be a non-negative integer")
        key = (asset_id, scene_index) if asset_id_valid and scene_index_valid else None
        if key is not None:
            if key in seen:
                errors.append(f"duplicate review scene reference {key!r}")
            seen.add(key)
            if key not in lookup:
                errors.append(f"unknown review scene reference {key!r}")
            elif "visual_diversity_lineage" in lookup[key] and not isinstance(
                    lookup[key]["visual_diversity_lineage"], list):
                errors.append(f"{ref} existing visual_diversity_lineage must be a list")

        labels = {}
        for axis in LABEL_AXES:
            if axis not in item:
                continue
            value = item.get(axis)
            if not _nonempty(value):
                errors.append(f"{ref}.{axis} must be a non-empty string")
                continue
            value = value.strip()
            if axis == "angle_scale" and value not in ANGLE_SCALES:
                errors.append(f"{ref}.angle_scale must be one of {ANGLE_SCALES}")
                continue
            labels[axis] = value
        if not labels:
            errors.append(f"{ref} must provide at least one shallow label")
        if key is not None:
            validated.append((key, labels))

    if errors:
        return {"ok": False, "errors": errors, "applied_scene_count": 0, "project_map": None}

    result = copy.deepcopy(project_map)
    output_lookup = _scene_lookup(result)
    for key, labels in validated:
        scene = output_lookup[key]
        scene.update(labels)
        lineage = scene.setdefault("visual_diversity_lineage", [])
        lineage.append({
            "reviewer": reviewer.strip(),
            "at": at.strip(),
            "axes": sorted(labels),
        })
    return {
        "ok": True,
        "errors": [],
        "applied_scene_count": len(validated),
        "project_map": result,
    }


def write_visual_diversity_review(project_map_path, review_path, out_path):
    """Apply a review and replace the output only after validation succeeds."""
    with open(project_map_path, encoding="utf-8-sig") as handle:
        project_map = json.load(handle)
    with open(review_path, encoding="utf-8-sig") as handle:
        review = json.load(handle)
    result = apply_visual_diversity_review(project_map, review)
    if not result["ok"]:
        raise ValueError("visual diversity review invalid: " + "; ".join(result["errors"]))

    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(str(path) + ".vd-review.tmp")
    try:
        temp.write_text(
            json.dumps(result["project_map"], ensure_ascii=False, indent=2),
            encoding="utf-8")
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()
    return result
