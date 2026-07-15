"""Fail-closed evidence gate for picture-plan material selection.

This module does not choose a story or create a second material catalog.  It
replays the existing scene ranker against the canonical project material map
and records how each picture-plan clip relates to the ranked candidates.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .project_material_map import expand_project_material_map
from .material_retrieval import rank_scenes


_OVERRIDE_MODES = {"agent_override", "owner_directed_override"}
_RANKED_MODES = {"ranked", "ranked_candidate", "retrieval_ranked"}


def _sha256(path: str | Path | None) -> str | None:
    if not path:
        return None
    value = Path(path)
    if not value.is_file():
        return None
    digest = hashlib.sha256()
    with value.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_ref(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, Mapping):
        for key in ("ref", "path", "file"):
            if isinstance(value.get(key), str) and value[key].strip():
                return value[key].strip()
    return None


def _clip_scene_id(clip: Mapping[str, Any]) -> str | None:
    value = clip.get("scene_id")
    if isinstance(value, str) and value.strip():
        return value.strip()
    asset_id = clip.get("asset_id")
    scene_index = clip.get("scene_index")
    if isinstance(asset_id, str) and isinstance(scene_index, int):
        return f"{asset_id}:{scene_index}"
    return None


def _source_hash_for_map(material_map: Mapping[str, Any]) -> str | None:
    value = material_map.get("source_hash") or material_map.get("sha256")
    return str(value).strip().lower() if value else None


def _candidate_view(item: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "scene_id": item.get("scene_id"),
        "asset_id": item.get("asset_id"),
        "scene_index": item.get("scene_index"),
        "score": item.get("score"),
        "score_breakdown": item.get("score_breakdown") or {},
        "source": item.get("source"),
        "caption": item.get("caption"),
        "visual_family": item.get("visual_family"),
        "angle_scale": item.get("angle_scale"),
    }


def _selected_candidate(clip: Mapping[str, Any], ranked: list[dict[str, Any]]) -> dict[str, Any] | None:
    scene_id = _clip_scene_id(clip)
    if scene_id:
        for item in ranked:
            if item.get("scene_id") == scene_id:
                return item
    asset_id = clip.get("asset_id")
    if not isinstance(asset_id, str):
        return None
    matches = [item for item in ranked if item.get("asset_id") == asset_id]
    source_hash = str(clip.get("source_sha256") or clip.get("source_hash") or "").lower()
    if source_hash:
        matches = [item for item in matches if str(item.get("source_hash") or "").lower() == source_hash]
    if not matches:
        return None
    try:
        start = float(clip.get("start_sec") or 0.0)
    except (TypeError, ValueError):
        start = 0.0
    bounded = [item for item in matches if item.get("start", 0) <= start <= item.get("end", 0)]
    return (bounded or matches)[0]


def _clip_source_hash(clip: Mapping[str, Any]) -> str | None:
    value = clip.get("source_sha256") or clip.get("source_hash")
    return str(value).strip().lower() if value else None


def build_retrieval_ranking_report(
    *,
    picture_plan: Mapping[str, Any],
    segment_contract: Mapping[str, Any],
    project_map: Mapping[str, Any],
    project_map_path: str | Path | None = None,
    picture_plan_path: str | Path | None = None,
    report_path: str | Path | None = None,
    top_k: int = 10,
    allow_declared_hash_placeholder: bool = False,
) -> dict[str, Any]:
    """Build a report and fail closed when the plan bypasses retrieval evidence.

    A selected clip may be inside the top ``top_k`` ranked candidates, or it may
    be an explicit agent/owner override carrying both a reason and evidence.
    Filename/folder hints influence the existing ranker only as weak prior
    evidence; they never satisfy this gate by themselves.
    """
    errors: list[str] = []
    retrieval_evidence = picture_plan.get("retrieval_evidence")
    if not isinstance(retrieval_evidence, Mapping):
        errors.append("missing_retrieval_evidence")
        retrieval_evidence = {}
    if not _json_ref(retrieval_evidence.get("project_material_map_ref")):
        errors.append("missing_project_material_map_ref")
    if not _json_ref(retrieval_evidence.get("ranking_report_ref")):
        errors.append("missing_ranking_report_ref")

    try:
        maps = expand_project_material_map(project_map) or []
    except ValueError as exc:
        errors.append(f"invalid_project_material_map:{exc}")
        maps = []
    segments = {
        item.get("segment"): item
        for item in (segment_contract.get("segments") or [])
        if isinstance(item, Mapping) and item.get("segment")
    }
    clips = [item for item in (picture_plan.get("clips") or [])
             if isinstance(item, Mapping) and item.get("track", "video") == "video"]
    segment_reports: dict[str, dict[str, Any]] = {}
    selection_modes: dict[str, int] = {}
    effective_top_k = max(1, int(top_k or 1))

    for clip_index, clip in enumerate(clips):
        segment_id = clip.get("segment")
        segment = segments.get(segment_id)
        if segment is None:
            errors.append(f"clip_{clip_index}_missing_segment:{segment_id}")
            continue
        ranked = rank_scenes(segment, maps)
        selected = _selected_candidate(clip, ranked)
        entry = segment_reports.setdefault(str(segment_id), {
            "segment": segment_id,
            "candidates": [_candidate_view(item) for item in ranked[:effective_top_k]],
            "selections": [],
        })
        if selected is None:
            errors.append(f"clip_{clip_index}_not_in_ranked_candidates:{clip.get('clip_id')}")
            continue
        rank_position = next(
            (index + 1 for index, item in enumerate(ranked)
             if item.get("scene_id") == selected.get("scene_id")),
            None,
        )
        mode = str(clip.get("selection_mode") or "ranked_candidate")
        selection_modes[mode] = selection_modes.get(mode, 0) + 1
        reason = clip.get("selection_reason") or clip.get("override_reason")
        evidence = clip.get("selection_evidence") or clip.get("override_evidence")
        if mode in _OVERRIDE_MODES:
            if not (isinstance(reason, str) and reason.strip()
                    and isinstance(evidence, list)
                    and any(isinstance(item, str) and item.strip() for item in evidence)):
                errors.append(f"agent_override_requires_reason_and_evidence:{clip.get('clip_id')}")
        elif mode not in _RANKED_MODES:
            errors.append(f"unknown_selection_mode:{mode}")
        elif rank_position is None or rank_position > effective_top_k:
            errors.append(f"clip_{clip_index}_outside_top_k_requires_override:{clip.get('clip_id')}")

        map_hash = next(
            (_source_hash_for_map(item) for item in maps
             if item.get("asset_id") == selected.get("asset_id")),
            None,
        )
        clip_hash = _clip_source_hash(clip)
        if map_hash and clip_hash and map_hash != clip_hash:
            errors.append(f"clip_{clip_index}_source_hash_mismatch:{clip.get('clip_id')}")
        entry["selections"].append({
            "clip_id": clip.get("clip_id"),
            "scene_id": selected.get("scene_id"),
            "rank_position": rank_position,
            "selection_mode": mode,
            "selection_reason": reason,
            "source_hash_match": not (map_hash and clip_hash) or map_hash == clip_hash,
        })

    if project_map_path and retrieval_evidence.get("project_material_map_sha256"):
        actual = _sha256(project_map_path)
        declared = str(retrieval_evidence["project_material_map_sha256"]).lower()
        if actual and actual != declared and not (allow_declared_hash_placeholder and declared == "placeholder"):
            errors.append("project_material_map_hash_mismatch")

    report = {
        "artifact_role": "picture_plan_retrieval_ranking_report",
        "version": 1,
        "ok": not errors,
        "errors": errors,
        "top_k": effective_top_k,
        "picture_plan_ref": str(picture_plan_path) if picture_plan_path else None,
        "picture_plan_sha256": _sha256(picture_plan_path),
        "project_material_map_ref": str(project_map_path) if project_map_path else None,
        "project_material_map_sha256": _sha256(project_map_path),
        "segments": list(segment_reports.values()),
        "summary": {
            "video_clip_count": len(clips),
            "segment_count": len(segment_reports),
            "selection_mode_counts": selection_modes,
            "override_count": sum(selection_modes.get(mode, 0) for mode in _OVERRIDE_MODES),
        },
    }
    if report_path:
        out = Path(report_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report

