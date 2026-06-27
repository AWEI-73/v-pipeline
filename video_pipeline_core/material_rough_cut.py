"""Build an inspectable rough-cut plan from reviewed material-map edges."""
from __future__ import annotations

import json
from pathlib import Path

from .edit_artifacts import build_timeline_build


def _need_refs(segment: dict) -> list[str]:
    refs = []
    material_fit = segment.get("material_fit") or {}
    for value in (segment.get("need_ref"), material_fit.get("need_ref")):
        if isinstance(value, str) and value.strip():
            refs.append(value.strip())
    for value in material_fit.get("need_refs") or []:
        if isinstance(value, str) and value.strip() and value.strip() not in refs:
            refs.append(value.strip())
    return refs


def _requested_duration(segment: dict, default_clip_sec: float) -> float:
    for key in ("requested_duration_sec", "duration_sec", "target_duration_sec"):
        try:
            value = float(segment.get(key) or 0)
        except (TypeError, ValueError):
            value = 0.0
        if value > 0:
            return value
    return float(default_clip_sec)


def _accepted_need_ids(scene: dict) -> set[str]:
    out = set()
    for edge in scene.get("satisfies") or []:
        if not isinstance(edge, dict):
            continue
        if edge.get("status") != "accepted":
            continue
        need_id = edge.get("need_id")
        if isinstance(need_id, str) and need_id.strip():
            out.add(need_id.strip())
    return out


def _accepted_edge(scene: dict, need_id: str) -> dict | None:
    for edge in scene.get("satisfies") or []:
        if not isinstance(edge, dict):
            continue
        if edge.get("status") == "accepted" and edge.get("need_id") == need_id:
            return edge
    return None


def _edge_is_rejected(edge: dict | None) -> bool:
    if not edge:
        return False
    verdict = edge.get("curator_verdict") or edge.get("verdict")
    return verdict in {"reject", "rejected", "duplicate"}


def _scene_duration(scene: dict, fallback: float) -> float:
    try:
        start = float(scene.get("start") or 0.0)
        end = float(scene.get("end") or 0.0)
    except (TypeError, ValueError):
        return fallback
    return max(0.0, end - start) or fallback


def _scene_start(scene: dict) -> float:
    try:
        return float(scene.get("start") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _usable_range(scene: dict, need_id: str) -> tuple[float, float] | None:
    edge = _accepted_edge(scene, need_id)
    if not edge:
        return None
    value = edge.get("usable_range")
    if not isinstance(value, dict):
        return None
    try:
        start = float(value.get("start"))
        end = float(value.get("end"))
    except (TypeError, ValueError):
        return None
    if end <= start:
        return None
    return start, end


def _candidate_scenes(project_map: dict, need_id: str) -> list[dict]:
    candidates = []
    for asset in project_map.get("assets") or []:
        asset_id = asset.get("asset_id")
        source = asset.get("source") or asset.get("path")
        for index, scene in enumerate(asset.get("scenes") or []):
            if need_id not in _accepted_need_ids(scene):
                continue
            edge = _accepted_edge(scene, need_id)
            if _edge_is_rejected(edge):
                continue
            scene_index = scene.get("scene_index")
            if not isinstance(scene_index, int):
                scene_index = index
            usable = _usable_range(scene, need_id)
            if usable:
                available_start = usable[0]
                available_duration = usable[1] - usable[0]
                has_reviewed_usable_range = True
            else:
                available_start = _scene_start(scene)
                available_duration = _scene_duration(scene, 0.0)
                has_reviewed_usable_range = False
            candidates.append({
                "asset_id": asset_id,
                "asset_type": asset.get("asset_type"),
                "source": source,
                "scene": scene,
                "scene_index": scene_index,
                "scene_duration_sec": _scene_duration(scene, 0.0),
                "available_start_sec": available_start,
                "available_range_sec": available_duration,
                "has_reviewed_usable_range": has_reviewed_usable_range,
            })
    return sorted(
        candidates,
        key=lambda item: (
            -float(item["available_range_sec"] or 0.0),
            str(item.get("asset_id") or ""),
            int(item.get("scene_index") or 0),
        ),
    )


def _timeline_from_clips(clips: list[dict]) -> dict:
    render_plan = []
    for index, clip in enumerate(clips):
        render_plan.append({
            "segment": clip["segment"],
            "source": clip["source_path"],
            "extract_start": clip["start_sec"],
            "extract_dur": clip["duration_sec"],
            "slot_index": index,
            "scene_id": clip["scene_id"],
            "asset_id": clip.get("asset_id"),
            "material_map_id": clip.get("asset_id"),
            "need_id": clip.get("need_id"),
            "caption": clip.get("caption"),
            "source_repeat_count": clip.get("source_repeat_count"),
            "reason": clip.get("reason"),
        })
    timeline = build_timeline_build(render_plan)
    timeline["artifact_role"] = "timeline_build"
    timeline["source_artifact"] = "rough_cut_plan"
    return timeline


def build_rough_cut_plan(contract: dict, project_map: dict, *, default_clip_sec: float = 3.0) -> dict:
    clips = []
    gaps = []
    source_counts = {}

    for index, segment in enumerate(contract.get("segments") or []):
        segment_id = segment.get("segment", index + 1)
        refs = _need_refs(segment)
        if not refs:
            gaps.append({
                "segment": segment_id,
                "need_id": None,
                "reason": "segment has no material need refs",
            })
            continue

        requested = _requested_duration(segment, default_clip_sec)
        chosen = None
        chosen_need = None
        for need_id in refs:
            candidates = _candidate_scenes(project_map, need_id)
            if candidates:
                chosen = candidates[0]
                chosen_need = need_id
                break
        if not chosen:
            gaps.append({
                "segment": segment_id,
                "need_id": refs[0],
                "reason": "no accepted scene satisfies the segment need",
            })
            continue

        scene = chosen["scene"]
        source = chosen.get("source")
        available = float(chosen.get("available_range_sec") or _scene_duration(scene, requested))
        is_still_asset = str(chosen.get("asset_type") or "").lower() in {"image", "photo", "still", "jpg", "jpeg", "png"}
        if (
            not chosen.get("has_reviewed_usable_range")
            and is_still_asset
        ):
            available = max(available, float(requested))
        start = chosen.get("available_start_sec")
        if start is None:
            start = _scene_start(scene)
        duration = min(requested, available)
        source_counts[source] = source_counts.get(source, 0) + 1
        clips.append({
            "segment": segment_id,
            "need_id": chosen_need,
            "asset_id": chosen.get("asset_id"),
            "asset_type": chosen.get("asset_type"),
            "source_path": source,
            "scene_id": f"{chosen.get('asset_id')}:{chosen.get('scene_index')}",
            "scene_index": chosen.get("scene_index"),
            "start_sec": round(float(start), 3),
            "duration_sec": round(duration, 3),
            "available_range_sec": round(available, 3),
            "caption": scene.get("caption"),
            "source_repeat_count": source_counts[source],
            "reason": "selected first accepted material-map scene for segment need",
        })
        missing_duration = round(max(0.0, requested - duration), 3)
        if missing_duration > 0 and not is_still_asset:
            gaps.append({
                "segment": segment_id,
                "need_id": chosen_need,
                "asset_id": chosen.get("asset_id"),
                "scene_id": f"{chosen.get('asset_id')}:{chosen.get('scene_index')}",
                "reason": "accepted scene is shorter than requested segment duration",
                "requested_duration_sec": round(float(requested), 3),
                "selected_duration_sec": round(float(duration), 3),
                "missing_duration_sec": missing_duration,
            })

    plan = {
        "artifact_role": "rough_cut_plan",
        "version": 1,
        "ok": not gaps,
        "clip_count": len(clips),
        "gap_count": len(gaps),
        "total_duration_sec": round(sum(float(item["duration_sec"]) for item in clips), 3),
        "source_repetition": source_counts,
        "clips": clips,
        "gaps": gaps,
    }
    plan["timeline_build"] = _timeline_from_clips(clips)
    return plan


def load_json(path):
    with Path(path).open(encoding="utf-8-sig") as handle:
        return json.load(handle)


def write_json(path, payload):
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
