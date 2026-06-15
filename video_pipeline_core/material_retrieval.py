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
                "visual_family": scene.get("visual_family"),
                "angle_scale": scene.get("angle_scale"),
                "asset_type": material_map.get("asset_type"),
            })
    return sorted(ranked, key=lambda item: (-item["score"], item["scene_id"]))


def _scene_by_id(material_maps, scene_id):
    asset_id, _, raw = str(scene_id).rpartition(":")
    for material_map in material_maps or []:
        if str(material_map.get("asset_id")) == asset_id:
            try:
                return (material_map.get("scenes") or [])[int(raw)]
            except (ValueError, IndexError):
                return None
    return None


def select_diverse_ranked_scenes(ranked, material_maps, limit, history=None):
    """Select scenes from ranked list with diversity preference within same score tiers."""
    candidates = []
    for item in ranked:
        source = item.get("source")
        if not isinstance(source, str) or not source.strip():
            continue
        available = max(0.0, item["end"] - item["start"])
        if available <= 0:
            continue
        candidates.append(item)

    tiers = []
    if candidates:
        current_score = candidates[0]["score"]
        current_tier = []
        for c in candidates:
            if c["score"] == current_score:
                current_tier.append(c)
            else:
                tiers.append(current_tier)
                current_score = c["score"]
                current_tier = [c]
        if current_tier:
            tiers.append(current_tier)

    selected = []
    used_families = set()
    last_scale = None

    if history:
        for prev in history:
            vf = prev.get("visual_family")
            if vf:
                used_families.add(vf)
            scale = prev.get("angle_scale")
            if scale:
                last_scale = scale

    for tier in tiers:
        if len(selected) >= limit:
            break
        while tier and len(selected) < limit:
            scored_candidates = []
            for c in tier:
                vf = c.get("visual_family")
                if vf:
                    family_priority = 1 if vf not in used_families else -1
                else:
                    family_priority = 0

                scale = c.get("angle_scale")
                if scale:
                    angle_scale_priority = -1 if (last_scale is not None and scale == last_scale) else 1
                else:
                    angle_scale_priority = 0

                asset_type = c.get("asset_type")
                asset_type_priority = 1 if asset_type == "video" else 0

                reason = f"tier_score={c['score']:.1f}, family_pref={family_priority}, scale_pref={angle_scale_priority}, type_pref={asset_type_priority}"
                scored_candidates.append((
                    -family_priority,
                    -angle_scale_priority,
                    -asset_type_priority,
                    c["scene_id"],
                    c,
                    reason
                ))

            scored_candidates.sort(key=lambda x: (x[0], x[1], x[2], x[3]))
            best_tuple = scored_candidates[0]
            best_candidate = best_tuple[4]
            best_reason = best_tuple[5]

            vf = best_candidate.get("visual_family")
            if vf:
                used_families.add(vf)
            scale = best_candidate.get("angle_scale")
            if scale:
                last_scale = scale

            c_copy = dict(best_candidate)
            c_copy["diversity_selection_reason"] = best_reason
            selected.append(c_copy)
            tier.remove(best_candidate)

    return selected


def plan_ranked_windows(segment, material_maps, *, limit, clip_dur, ranker=None, history=None):
    """Convert top-ranked scenes to concrete editor slots."""
    from .action_progression import classify_function
    limit = max(0, int(limit))

    ranked = rank_scenes(segment, material_maps, ranker=ranker)
    selected = select_diverse_ranked_scenes(ranked, material_maps, limit, history=history)

    slots = []
    for item in selected:
        source = item.get("source")
        available = max(0.0, item["end"] - item["start"])
        take = min(float(clip_dur), available)

        start = item["start"] + max(0.0, available - take) / 2
        start = min(max(start, item["start"]), item["end"] - take)
        scene = _scene_by_id(material_maps, item["scene_id"]) or {}
        function = scene.get("function") or classify_function(
            item.get("caption"),
            motion_peaks=scene.get("motion_peaks"),
            duration_sec=available,
        )
        slots.append({
            "source": source,
            "extract_start": round(start, 3),
            "extract_dur": round(take, 3),
            "keep_audio": False,
            "segment": segment.get("segment"),
            "scene_id": item["scene_id"],
            "caption": item.get("caption"),
            "function": function,
            "retrieval_score": item["score"],
            "visual_family": item.get("visual_family"),
            "angle_scale": item.get("angle_scale"),
            "diversity_selection_reason": item.get("diversity_selection_reason", "default"),
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
