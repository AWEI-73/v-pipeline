"""VD1 - prove shallow visual-label coverage before VD2 soft ranking.

This module is evidence-only. It reads a project material map and reports label
coverage and missing scene references. It never ranks, selects, or mutates
material.
"""
from __future__ import annotations

import json
from pathlib import Path


VD0_AXES = ("visual_family", "angle_scale", "action_family", "subject")
VD2_REQUIRED_AXES = ("visual_family", "angle_scale")


def _is_labeled(scene, axis):
    value = scene.get(axis)
    return isinstance(value, str) and bool(value.strip())


def _ratio_threshold(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number from 0 to 1")
    value = float(value)
    if value < 0 or value > 1:
        raise ValueError(f"{name} must be a number from 0 to 1")
    return value


def _scene_labels_by_ref(project_map):
    labels = {}
    for asset in project_map.get("assets") or []:
        asset_id = asset.get("asset_id")
        for scene_index, scene in enumerate(asset.get("scenes") or []):
            labels[(asset_id, scene_index)] = scene
    return labels


def _consistency_report(project_map, reviews, *, min_scenes, min_ratio):
    baseline = _scene_labels_by_ref(project_map)
    comparable_scenes = set()
    agreeing_labels = 0
    comparable_labels = 0
    per_axis = {}

    for axis in VD2_REQUIRED_AXES:
        axis_agreeing = 0
        axis_comparable = 0
        for review in reviews:
            if not isinstance(review, dict) or review.get("artifact_role") != "project_material_map":
                raise ValueError("consistency reviews must be project_material_map artifacts")
            for ref, review_scene in _scene_labels_by_ref(review).items():
                baseline_scene = baseline.get(ref)
                if not baseline_scene:
                    continue
                if _is_labeled(baseline_scene, axis) and _is_labeled(review_scene, axis):
                    comparable_scenes.add(ref)
                    axis_comparable += 1
                    axis_agreeing += int(
                        baseline_scene[axis].strip() == review_scene[axis].strip())
        comparable_labels += axis_comparable
        agreeing_labels += axis_agreeing
        per_axis[axis] = {
            "comparable_label_count": axis_comparable,
            "agreement_ratio": round(axis_agreeing / axis_comparable, 4)
            if axis_comparable else 0,
        }

    agreement_ratio = round(agreeing_labels / comparable_labels, 4) if comparable_labels else 0
    return {
        "review_count": len(reviews),
        "comparable_scene_count": len(comparable_scenes),
        "comparable_label_count": comparable_labels,
        "agreement_ratio": agreement_ratio,
        "min_consistency_scenes": min_scenes,
        "min_consistency_ratio": min_ratio,
        "per_axis": per_axis,
    }


def build_visual_diversity_coverage(
        project_map, *, min_visual_family_coverage=0.7,
        min_angle_scale_coverage=0.6, consistency_reviews=None,
        min_consistency_ratio=0.7, min_consistency_scenes=10):
    if not isinstance(project_map, dict) or project_map.get("artifact_role") != "project_material_map":
        raise ValueError("VD1 requires a project_material_map artifact")
    required_thresholds = {
        "visual_family": _ratio_threshold(
            min_visual_family_coverage, "min_visual_family_coverage"),
        "angle_scale": _ratio_threshold(
            min_angle_scale_coverage, "min_angle_scale_coverage"),
    }
    consistency_threshold = _ratio_threshold(
        min_consistency_ratio, "min_consistency_ratio")
    if (isinstance(min_consistency_scenes, bool)
            or not isinstance(min_consistency_scenes, int)
            or min_consistency_scenes < 1):
        raise ValueError("min_consistency_scenes must be a positive integer")
    reviews = list(consistency_reviews or [])

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

    consistency = _consistency_report(
        project_map, reviews, min_scenes=min_consistency_scenes,
        min_ratio=consistency_threshold)
    blocking = []
    if scene_count == 0:
        blocking.append("no_scenes")
    for axis, threshold in required_thresholds.items():
        if axes[axis]["coverage_ratio"] < threshold:
            blocking.append(f"{axis}_coverage_below_threshold")
    if not reviews:
        blocking.append("consistency_evidence_missing")
    else:
        for axis in VD2_REQUIRED_AXES:
            axis_consistency = consistency["per_axis"][axis]
            if axis_consistency["comparable_label_count"] < min_consistency_scenes:
                blocking.append(f"{axis}_consistency_sample_below_threshold")
            elif axis_consistency["agreement_ratio"] < consistency_threshold:
                blocking.append(f"{axis}_consistency_ratio_below_threshold")
    ready = not blocking
    ratio = lambda count: round(count / scene_count, 4) if scene_count else 0
    return {
        "artifact_role": "visual_diversity_coverage",
        "version": 2,
        "ready_for_vd2": ready,
        "decision": {
            "reason": "ready" if ready else blocking[0],
            "blocking_reasons": blocking,
            "required_axis_coverage": required_thresholds,
        },
        "metrics": {
            "scene_count": scene_count,
            "any_vd0_labeled_scene_ratio": ratio(any_labeled),
            "fully_labeled_scene_ratio": ratio(fully_labeled),
        },
        "axes": axes,
        "consistency": consistency,
    }


def write_visual_diversity_coverage(project_map_path, out_path, *,
                                     min_visual_family_coverage=0.7,
                                     min_angle_scale_coverage=0.6,
                                     consistency_review_paths=None,
                                     min_consistency_ratio=0.7,
                                     min_consistency_scenes=10):
    with open(project_map_path, encoding="utf-8") as handle:
        project_map = json.load(handle)
    reviews = []
    for review_path in consistency_review_paths or []:
        with open(review_path, encoding="utf-8") as handle:
            reviews.append(json.load(handle))
    report = build_visual_diversity_coverage(
        project_map,
        min_visual_family_coverage=min_visual_family_coverage,
        min_angle_scale_coverage=min_angle_scale_coverage,
        consistency_reviews=reviews,
        min_consistency_ratio=min_consistency_ratio,
        min_consistency_scenes=min_consistency_scenes)
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
