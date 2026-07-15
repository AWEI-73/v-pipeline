"""Scene-level material retrieval and source-speech planning."""
from __future__ import annotations

import re

NON_MAIN_TIMELINE_ASSET_TYPES = {"effect_overlay", "motion_asset", "sfx"}


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


def _filename_prior_score(query, material_map, scene):
    """Score filename/folder hints weakly, without admitting a scene alone."""
    prior = scene.get("filename_prior") or material_map.get("filename_prior") or {}
    if isinstance(prior, dict):
        prior = prior.get("text") or ""
    return _text_score(query, prior)


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


def _soul_score(segment, scene):
    """Soft story-intent score, only meaningful after base evidence admits a scene."""
    core = segment.get("core") or {}
    material_fit = segment.get("material_fit") or {}
    director_intent = segment.get("director_intent") or {}
    values = [
        core.get("emotional_movement"),
        core.get("conflict_or_turn"),
        core.get("intended_viewer_feeling"),
        core.get("sensory_anchor"),
        core.get("narrative_device"),
    ]
    values.extend(material_fit.get("material_prompt_requirements") or [])
    values.extend(director_intent.get("material_prompt_requirements") or [])
    if isinstance(director_intent, dict):
        values.extend(
            director_intent.get(key)
            for key in ("composition", "camera_movement", "lighting", "emotion")
        )
    wanted = set()
    for value in values:
        wanted.update(_terms(value))
    if not wanted:
        return 0
    seen = set()
    for key in ("caption", "visual_family", "angle_scale", "action_family", "subject"):
        seen.update(_terms(scene.get(key)))
    overlap = wanted & seen
    if not overlap:
        return 0
    return min(2, len(overlap))


def _expected_need_ids(segment):
    material_fit = segment.get("material_fit") or {}
    values = []
    for value in (segment.get("need_ref"), material_fit.get("need_ref")):
        if isinstance(value, str) and value.strip():
            values.append(value.strip())
    for value in material_fit.get("need_refs") or []:
        if isinstance(value, str) and value.strip():
            values.append(value.strip())
    return {str(value) for value in values}


def _allowed_material_map_ids(segment):
    values = []
    for value in segment.get("material_map_ids") or segment.get("asset_ids") or []:
        if isinstance(value, str) and value.strip():
            values.append(value.strip())
    return {str(value) for value in values}


def _scene_need_id(material_map, scene):
    for status in ("accepted", "candidate"):
        for edge in scene.get("satisfies") or []:
            if edge.get("status") == status and edge.get("need_id"):
                return edge["need_id"]
    return scene.get("need_id") or material_map.get("need_id")


def _need_score(segment, material_map, scene):
    expected = _expected_need_ids(segment)
    actual = _scene_need_id(material_map, scene)
    return 4 if expected and actual and str(actual) in expected else 0


def _evidence_quality_score(scene):
    """Score reviewed evidence quality without admitting a scene by itself."""
    score = 0.0
    if scene.get("direct_story_evidence") is True:
        score += 4.0
    if str(scene.get("assigned_story_function") or scene.get("story_function") or "").strip():
        score += 2.0

    review = scene.get("review") or {}
    if review.get("visual_evidence") or scene.get("visual_evidence") or scene.get("evidence_refs"):
        score += 1.0

    confidence = review.get("confidence", scene.get("confidence"))
    try:
        confidence = max(0.0, min(1.0, float(confidence)))
    except (TypeError, ValueError):
        confidence = 0.0
    score += 2.0 * confidence

    if str(scene.get("support_subtype") or "").strip().lower() in {
        "support_only", "unresolved", "unresolved_cutaway",
    }:
        score -= 0.5
    return round(score, 3)


def rank_scenes(segment, material_maps, *, ranker=None, soul_ranking=True):
    """Rank evidenced scenes; external rankers may rerank but not admit zero-fit scenes."""
    query = (segment.get("material_fit") or {}).get("visual_desc") or segment.get("visual_desc")
    allowed_asset_ids = _allowed_material_map_ids(segment)
    expected_need_ids = _expected_need_ids(segment)
    ranked = []
    for material_map in material_maps or []:
        if material_map.get("asset_type") in NON_MAIN_TIMELINE_ASSET_TYPES:
            continue
        asset_id = str(material_map.get("asset_id") or "")
        if allowed_asset_ids and asset_id not in allowed_asset_ids:
            continue
        for index, scene in enumerate(material_map.get("scenes") or []):
            actual_need_id = _scene_need_id(material_map, scene)
            if expected_need_ids and actual_need_id and str(actual_need_id) not in expected_need_ids:
                continue
            breakdown = {
                "need": _need_score(segment, material_map, scene),
                "text": _text_score(query, scene.get("caption")),
                "name_prior": _filename_prior_score(query, material_map, scene),
                "function": _function_score(segment, scene),
                "pace": _pace_score(segment, scene),
                "evidence_quality": _evidence_quality_score(scene),
            }
            base_score = sum(
                value for key, value in breakdown.items()
                if key not in {"name_prior", "evidence_quality"}
            )
            if base_score <= 0:
                continue
            if query and breakdown["text"] <= 0 and breakdown["need"] <= 0:
                continue
            breakdown["soul"] = _soul_score(segment, scene) if soul_ranking else 0
            evidence_score = sum(breakdown.values())
            external = float(ranker(segment, scene) or 0) if ranker else 0
            ranked.append({
                "asset_id": material_map.get("asset_id"),
                "source": material_map.get("source"),
                "source_hash": material_map.get("source_hash"),
                "filename_prior": material_map.get("filename_prior"),
                "scene_index": index,
                "scene_id": f"{material_map.get('asset_id')}:{index}",
                "start": float(scene.get("start") or 0),
                "end": float(scene.get("end") or 0),
                "caption": scene.get("caption"),
                "need_id": actual_need_id,
                "score_breakdown": breakdown,
                "ranker_score": external,
                "score": evidence_score + external,
                "visual_family": scene.get("visual_family"),
                "angle_scale": scene.get("angle_scale"),
                "asset_type": material_map.get("asset_type"),
                "function": scene.get("function"),
                "story_function": scene.get("story_function"),
                "protected_speech_anchor": bool(
                    scene.get("protected_speech_anchor")
                    or scene.get("story_function") == "protected_speech_anchor"
                    or scene.get("function") == "talking_head"
                    or scene.get("visual_family") == "talking_head"
                    or scene.get("audio_role") == "source_speech"
                ),
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


def _is_protected_speech_anchor(item):
    return bool(
        item.get("protected_speech_anchor")
        or item.get("story_function") == "protected_speech_anchor"
        or item.get("function") == "talking_head"
        or item.get("visual_family") == "talking_head"
        or item.get("audio_role") == "source_speech"
    )


def _source_counts(history):
    counts = {}
    for prev in history or []:
        if not isinstance(prev, dict) or _is_protected_speech_anchor(prev):
            continue
        source = prev.get("source") if isinstance(prev, dict) else None
        if source:
            counts[source] = counts.get(source, 0) + 1
    return counts


def select_diverse_ranked_scenes(ranked, material_maps, limit, history=None,
                                 diversity=True, max_source_repeats=None,
                                 require_unique_visual_family=False):
    """Select scenes from ranked list with diversity preference within same score
    tiers. `diversity=False` (VD2 off / acceptance baseline) skips the same-tier
    family/scale reorder and the cross-segment history, taking the strict
    correctness order (`-score`, then `scene_id`) — a minimal, backward-compatible
    control; the default `True` is the existing behavior."""
    candidates = []
    for item in ranked:
        source = item.get("source")
        if not isinstance(source, str) or not source.strip():
            continue
        is_photo = item.get("asset_type") == "photo"
        if not is_photo:
            available = max(0.0, item["end"] - item["start"])
            if available <= 0:
                continue
        candidates.append(item)

    if not diversity:
        out = []
        for c in candidates[:max(0, int(limit))]:
            c_copy = dict(c)
            c_copy["diversity_selection_reason"] = "diversity_disabled"
            out.append(c_copy)
        return out

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
    source_counts = _source_counts(history)
    try:
        source_cap = int(max_source_repeats) if max_source_repeats is not None else None
    except (TypeError, ValueError):
        source_cap = None
    if source_cap is not None and source_cap <= 0:
        source_cap = None

    if history:
        for prev in history:
            vf = prev.get("visual_family")
            if vf and not _is_protected_speech_anchor(prev):
                used_families.add(vf)
            scale = prev.get("angle_scale")
            if scale:
                last_scale = scale

    for tier in tiers:
        if len(selected) >= limit:
            break
        while tier and len(selected) < limit:
            scored_candidates = []
            under_source_cap = [
                c for c in tier
                if _is_protected_speech_anchor(c)
                or source_cap is None
                or source_counts.get(c.get("source"), 0) < source_cap
            ]
            fallback_reason = None
            if source_cap is not None and not under_source_cap:
                fallback_reason = "eligible_supply_exhausted"
            tier_pool = under_source_cap or tier
            if require_unique_visual_family:
                unique_family_pool = [
                    c for c in tier_pool
                    if not c.get("visual_family")
                    or c.get("visual_family") not in used_families
                ]
                if unique_family_pool:
                    tier_pool = unique_family_pool
                else:
                    fallback_reason = "eligible_supply_exhausted"
            for c in tier:
                if c not in tier_pool:
                    continue
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
            if vf and not _is_protected_speech_anchor(best_candidate):
                used_families.add(vf)
            scale = best_candidate.get("angle_scale")
            if scale:
                last_scale = scale

            c_copy = dict(best_candidate)
            c_copy["diversity_selection_reason"] = best_reason
            source = best_candidate.get("source")
            c_copy["source_repeat_count"] = source_counts.get(source, 0) if source else 0
            if fallback_reason and (source_cap is not None or require_unique_visual_family):
                c_copy["diversity_fallback_reason"] = fallback_reason
            selected.append(c_copy)
            if source and not _is_protected_speech_anchor(best_candidate):
                source_counts[source] = source_counts.get(source, 0) + 1
            tier.remove(best_candidate)

    return selected


def _range_number(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    import math
    return number if math.isfinite(number) else None


def _iter_avoid_ranges(scene):
    for key in ("avoid_ranges", "bad_ranges"):
        for item in scene.get(key) or []:
            if isinstance(item, dict):
                start = _range_number(item.get("start"))
                end = _range_number(item.get("end"))
                reason = str(item.get("reason") or key)
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                start = _range_number(item[0])
                end = _range_number(item[1])
                reason = key
            else:
                continue
            if start is None or end is None or end <= start:
                continue
            yield start, end, reason


def _window_quality_reason(scene, start, dur):
    """Return a deterministic skip reason for known bad source ranges.

    Material maps may annotate black frames, blank cards, or transition cuts as
    `avoid_ranges`/`bad_ranges` in source seconds. BUILD must consume that
    evidence when choosing the concrete extraction window, while keeping the
    expensive detection step outside the hot render path.
    """
    end = start + dur
    for bad_start, bad_end, reason in _iter_avoid_ranges(scene):
        if start < bad_end and end > bad_start:
            return reason or "avoid_range"
    return "ok"


def plan_ranked_windows(segment, material_maps, *, limit, clip_dur, ranker=None,
                        history=None, diversity=True, soul_ranking=True,
                        max_source_repeats=None,
                        require_unique_visual_family=False):
    """Convert top-ranked scenes to concrete editor slots. `diversity=False`
    disables the VD2 same-tier diversity reorder (correctness order only)."""
    from .action_progression import classify_function
    limit = max(0, int(limit))

    ranked = rank_scenes(segment, material_maps, ranker=ranker, soul_ranking=soul_ranking)
    # Select enough candidates for window-quality filtering to backfill from
    # lower-ranked usable scenes instead of letting a bad top window consume the
    # caller's limit.
    selected = select_diverse_ranked_scenes(ranked, material_maps, len(ranked),
                                            history=history, diversity=diversity,
                                            max_source_repeats=max_source_repeats,
                                            require_unique_visual_family=require_unique_visual_family)

    slots = []
    fallback_slots = []
    for item in selected:
        if len(slots) >= limit:
            break
        source = item.get("source")
        is_photo = item.get("asset_type") == "photo"
        if is_photo:
            try:
                take = float(clip_dur)
            except (ValueError, TypeError):
                continue
            import math
            if not math.isfinite(take) or take <= 0:
                continue
            start = 0.0
            available = take
        else:
            available = max(0.0, item["end"] - item["start"])
            take = min(float(clip_dur), available)

            start = item["start"] + max(0.0, available - take) / 2
            start = min(max(start, item["start"]), item["end"] - take)
        scene = _scene_by_id(material_maps, item["scene_id"]) or {}
        if not is_photo:
            quality_reason = _window_quality_reason(scene, start, take)
        else:
            quality_reason = "ok"
        function = scene.get("function") or classify_function(
            item.get("caption"),
            motion_peaks=scene.get("motion_peaks"),
            duration_sec=available,
        )
        slot = {
            "source": source,
            "extract_start": round(start, 3),
            "extract_dur": round(take, 3),
            "keep_audio": False,
            "segment": segment.get("segment"),
            "scene_id": item["scene_id"],
            "caption": item.get("caption"),
            "function": function,
            "retrieval_score": item["score"],
            "score_breakdown": item.get("score_breakdown"),
            "need_id": item.get("need_id"),
            "visual_family": item.get("visual_family"),
            "angle_scale": item.get("angle_scale"),
            "diversity_selection_reason": item.get("diversity_selection_reason", "default"),
            "source_repeat_count": item.get("source_repeat_count", 0),
            "window_quality_reason": quality_reason,
        }
        if item.get("diversity_fallback_reason"):
            slot["diversity_fallback_reason"] = item["diversity_fallback_reason"]
        if item.get("protected_speech_anchor"):
            slot["protected_speech_anchor"] = True
        if is_photo:
            slot["is_photo"] = True
            slot["kenburns"] = True
        if quality_reason != "ok":
            slot["window_quality_fallback"] = True
            fallback_slots.append(slot)
            continue
        slots.append(slot)
    for slot in fallback_slots:
        if len(slots) >= limit:
            break
        slots.append(slot)
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
