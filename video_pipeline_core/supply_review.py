"""Estimate honest segment duration from actual material supply."""
from __future__ import annotations

import math
import os


def _target_shot_sec(segment):
    explicit = segment.get("target_shot_sec")
    if explicit:
        return float(explicit)
    preferred = (segment.get("pacing") or {}).get("preferred_shot_sec")
    if isinstance(preferred, (list, tuple)) and preferred:
        return sum(float(value) for value in preferred) / len(preferred)
    return 3.0


def _requested_duration(segment):
    return float(segment.get("requested_duration_sec") or segment.get("duration_sec") or 0)


def _map_ids(segment):
    return set(segment.get("material_map_ids") or segment.get("asset_ids") or [])


def _useful_shots(material_map):
    scene_count = len(material_map.get("scenes") or [])
    if material_map.get("asset_type") == "video":
        return min(2, scene_count)
    return min(1, scene_count)


def fallback_maps_from_coverage(coverage_map):
    """Conservative fallback: an unscanned positive pick provides one window."""
    maps = {}
    for assignment in (coverage_map or {}).get("assignments") or []:
        for pick in assignment.get("picks") or []:
            if float(pick.get("score", 1) or 0) <= 0:
                continue
            source = str(pick.get("path") or "")
            if not source or source.lower() in maps:
                continue
            extension = os.path.splitext(source)[1].lower()
            asset_type = "photo" if extension in (".jpg", ".jpeg", ".png", ".heic", ".heif") else "video"
            maps[source.lower()] = {
                "asset_id": source,
                "asset_type": asset_type,
                "source": source,
                "map_quality": "coverage_fallback",
                "scenes": [{"start": 0.0, "end": 0.0, "kind": "unscanned"}],
            }
    return list(maps.values())


def _function_coverage(segment, selected_maps):
    required = list((segment.get("sequence_grammar") or {}).get("required_functions") or [])
    available = set()
    for material_map in selected_maps:
        for scene in material_map.get("scenes") or []:
            available.update(scene.get("functions") or [])
            if scene.get("function"):
                available.add(scene["function"])
    return {
        "required": required,
        "covered": [value for value in required if value in available],
        "missing": [value for value in required if value not in available],
    }


def review_supply(contract, material_maps, *, coverage_map=None, target_duration_sec=None):
    """Return per-segment supply estimates without inventing missing material."""
    indexed = {item.get("asset_id"): item for item in material_maps or []}
    by_source = {str(item.get("source") or "").lower(): item for item in material_maps or []}
    assignments = {
        item.get("segment"): item for item in (coverage_map or {}).get("assignments") or []
    }
    segments = (contract or {}).get("segments") or []
    weight_sum = sum(float(item.get("weight") or 1) for item in segments) or 1
    reviewed = []
    for index, segment in enumerate(segments):
        sid = segment.get("segment", index + 1)
        ids = _map_ids(segment)
        if ids:
            selected = [indexed[value] for value in ids if value in indexed]
        else:
            assignment = assignments.get(sid) or {}
            selected = [
                by_source[str(pick.get("path") or "").lower()]
                for pick in assignment.get("picks") or []
                if float(pick.get("score", 1) or 0) > 0
                and str(pick.get("path") or "").lower() in by_source
            ]
        target = _target_shot_sec(segment)
        requested = _requested_duration(segment)
        if not requested and target_duration_sec:
            requested = float(target_duration_sec) * float(segment.get("weight") or 1) / weight_sum
        estimated = sum(_useful_shots(item) for item in selected)
        maximum = round(estimated * target, 3)
        required = math.ceil(requested / target) if target > 0 else 0
        if estimated == 0:
            feasibility, action = "gap", "await_material"
        elif estimated < required:
            feasibility, action = "thin", "shorten_or_merge"
        else:
            feasibility, action = "ok", "ok"
        reviewed.append({
            "segment": sid,
            "requested_duration_sec": requested,
            "target_shot_sec": target,
            "required_effective_shots": required,
            "estimated_effective_shots": estimated,
            "unique_sources": len(selected),
            "function_coverage": _function_coverage(segment, selected),
            "max_honest_duration_sec": maximum,
            "feasibility": feasibility,
            "action": action,
        })
    return {
        "artifact_role": "supply_review",
        "version": 1,
        "segments": reviewed,
        "ready_for_script": all(item["feasibility"] == "ok" for item in reviewed),
    }
