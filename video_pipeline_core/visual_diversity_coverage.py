"""VD1 - prove shallow visual-label coverage before VD2 soft ranking.

This module is evidence-only. It reads a project material map and reports label
coverage and missing scene references. It never ranks, selects, or mutates
material.
"""
from __future__ import annotations

import json
from pathlib import Path


VD0_AXES = ("visual_family", "angle_scale", "action_family", "subject")


def _is_labeled(scene, axis):
    value = scene.get(axis)
    return isinstance(value, str) and bool(value.strip())


def build_visual_diversity_coverage(project_map, *, min_visual_family_coverage=0.7):
    if not isinstance(project_map, dict) or project_map.get("artifact_role") != "project_material_map":
        raise ValueError("VD1 requires a project_material_map artifact")
    if isinstance(min_visual_family_coverage, bool) or not isinstance(
            min_visual_family_coverage, (int, float)):
        raise ValueError("min_visual_family_coverage must be a number from 0 to 1")
    threshold = float(min_visual_family_coverage)
    if threshold < 0 or threshold > 1:
        raise ValueError("min_visual_family_coverage must be a number from 0 to 1")

    scene_refs = []
    for asset in project_map.get("assets") or []:
        asset_id = asset.get("asset_id")
        for scene_index, scene in enumerate(asset.get("scenes") or []):
            scene_refs.append(({"asset_id": asset_id, "scene_index": scene_index}, scene))

    scene_count = len(scene_refs)
    axes = {}
    fully_labeled = 0
    any_labeled = 0
    for axis in VD0_AXES:
        missing = [ref for ref, scene in scene_refs if not _is_labeled(scene, axis)]
        labeled_count = scene_count - len(missing)
        axes[axis] = {
            "labeled_count": labeled_count,
            "missing_count": len(missing),
            "coverage_ratio": round(labeled_count / scene_count, 4) if scene_count else 0,
            "missing": missing,
        }
    for _, scene in scene_refs:
        labels = [_is_labeled(scene, axis) for axis in VD0_AXES]
        fully_labeled += int(all(labels))
        any_labeled += int(any(labels))

    family_ratio = axes["visual_family"]["coverage_ratio"]
    ready = scene_count > 0 and family_ratio >= threshold
    reason = (
        "ready"
        if ready
        else "no_scenes"
        if scene_count == 0
        else "visual_family_coverage_below_threshold"
    )
    ratio = lambda count: round(count / scene_count, 4) if scene_count else 0
    return {
        "artifact_role": "visual_diversity_coverage",
        "version": 1,
        "ready_for_vd2": ready,
        "decision": {
            "reason": reason,
            "min_visual_family_coverage": threshold,
            "actual_visual_family_coverage": family_ratio,
        },
        "metrics": {
            "scene_count": scene_count,
            "any_vd0_labeled_scene_ratio": ratio(any_labeled),
            "fully_labeled_scene_ratio": ratio(fully_labeled),
        },
        "axes": axes,
    }


def write_visual_diversity_coverage(project_map_path, out_path, *,
                                     min_visual_family_coverage=0.7):
    with open(project_map_path, encoding="utf-8") as handle:
        project_map = json.load(handle)
    report = build_visual_diversity_coverage(
        project_map, min_visual_family_coverage=min_visual_family_coverage)
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
