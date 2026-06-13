"""Scene-level material retrieval and source-speech planning."""
from __future__ import annotations

import re


def _terms(value):
    return {
        token for token in re.findall(r"[\w\u4e00-\u9fff]+", str(value or "").lower())
        if len(token) > 1
    }


def _text_score(query, caption):
    query = str(query or "").strip().lower()
    caption = str(caption or "").strip().lower()
    if not query or not caption:
        return 0
    if query in caption or caption in query:
        return 2
    q_terms, c_terms = _terms(query), _terms(caption)
    return 1 if q_terms & c_terms else 0


def _function_score(segment, scene):
    required = set((segment.get("sequence_grammar") or {}).get("required_functions") or [])
    available = set(scene.get("functions") or [])
    if scene.get("function"):
        available.add(scene["function"])
    return 2 if required and required & available else 0


def _pace_score(segment, scene):
    pace = str((segment.get("visual_style") or {}).get("pace") or "").lower()
    duration = float(scene.get("end") or 0) - float(scene.get("start") or 0)
    active = bool(scene.get("motion_peaks"))
    if pace == "fast" and (active or 0 < duration <= 3):
        return 2
    if pace in ("hold", "slow") and duration >= 4:
        return 2
    return 0


def rank_scenes(segment, material_maps, *, ranker=None):
    """Rank evidenced scenes; external rankers may rerank but not admit zero-fit scenes."""
    query = (segment.get("material_fit") or {}).get("visual_desc") or segment.get("visual_desc")
    ranked = []
    for material_map in material_maps or []:
        for index, scene in enumerate(material_map.get("scenes") or []):
            breakdown = {
                "text": _text_score(query, scene.get("caption")),
                "function": _function_score(segment, scene),
                "pace": _pace_score(segment, scene),
            }
            evidence_score = sum(breakdown.values())
            if evidence_score <= 0:
                continue
            external = float(ranker(segment, scene) or 0) if ranker else 0
            ranked.append({
                "asset_id": material_map.get("asset_id"),
                "source": material_map.get("source"),
                "scene_index": index,
                "scene_id": f"{material_map.get('asset_id')}:{index}",
                "start": float(scene.get("start") or 0),
                "end": float(scene.get("end") or 0),
                "caption": scene.get("caption"),
                "score_breakdown": breakdown,
                "ranker_score": external,
                "score": evidence_score + external,
            })
    return sorted(ranked, key=lambda item: (-item["score"], item["scene_id"]))


def plan_ranked_windows(segment, material_maps, *, limit, clip_dur, ranker=None):
    """Convert top-ranked scenes to concrete editor slots."""
    slots = []
    for item in rank_scenes(segment, material_maps, ranker=ranker)[:max(0, int(limit))]:
        available = max(0.0, item["end"] - item["start"])
        take = min(float(clip_dur), available)
        if take <= 0:
            continue
        slots.append({
            "source": item["source"],
            "extract_start": round(item["start"] + max(0, available - take) / 2, 3),
            "extract_dur": round(take, 3),
            "keep_audio": False,
            "segment": segment.get("segment"),
            "scene_id": item["scene_id"],
            "retrieval_score": item["score"],
        })
    return slots


def plan_sound_bite(segment, material_maps):
    """Choose the strongest mapped speech run for a source_speech segment."""
    role = (segment.get("audio") or {}).get("role") or segment.get("audio_role")
    if role != "source_speech":
        return {"status": "not_requested", "segment": segment.get("segment")}
    candidates = []
    for material_map in material_maps or []:
        for run in material_map.get("speech") or []:
            if run.get("kind") != "speech":
                continue
            duration = float(run.get("end") or 0) - float(run.get("start") or 0)
            if duration > 0:
                candidates.append((bool(run.get("text")), duration, material_map, run))
    if not candidates:
        return {"status": "gap", "segment": segment.get("segment"),
                "reason": "source_speech requested but no speech run is mapped"}
    _has_text, duration, material_map, run = max(candidates, key=lambda item: (item[0], item[1]))
    return {
        "status": "ok",
        "segment": segment.get("segment"),
        "source": material_map.get("source"),
        "extract_start": float(run.get("start") or 0),
        "extract_dur": duration,
        "keep_audio": True,
        "audio_role": "source_speech",
        "transcript": run.get("text"),
    }
