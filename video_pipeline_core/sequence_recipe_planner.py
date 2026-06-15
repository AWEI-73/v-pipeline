"""SRP1 — Segment Sequence Recipe Planner.

Automatically plans sequence recipes from approved map-ranked slots of a segment.
"""
from __future__ import annotations

from .vt_core import GAP


def plan_segment_sequence(segment, approved_slots, *, entry=None, policy=None):
    """Auto-plans a sequence recipe from the segment's approved slots.

    segment: dict (the segment configuration from script)
    approved_slots: list of dict (already plan_ranked_windows output)
    entry: dict (optional segment execution meta entry)
    policy: optional custom policy dict

    Returns:
    {
      "status": "planned" | "not_applicable",
      "recipe": {
        "beats": [...],
        "durations": {...},
        "source": "auto_sequence_recipe",
        "reason": "...",
        "punctuate_payoff": bool
      } | None,
      "evidence": {
        "approved_slot_count": int,
        "distinct_visual_families": int,
        "distinct_angle_scales": int
      },
      "reason": "..."
    }
    """
    approved_slots = approved_slots or []
    entry = entry or {}

    distinct_families = sorted(list({sl.get("visual_family") for sl in approved_slots if sl.get("visual_family")}))
    distinct_scales = sorted(list({sl.get("angle_scale") for sl in approved_slots if sl.get("angle_scale")}))

    evidence = {
        "approved_slot_count": len(approved_slots),
        "distinct_visual_families": len(distinct_families),
        "distinct_angle_scales": len(distinct_scales),
    }

    # Rule 1: Segment must not have an existing beat_recipe
    if segment.get("beat_recipe"):
        return {
            "status": "not_applicable",
            "recipe": None,
            "evidence": evidence,
            "reason": "Segment already has a manual beat_recipe"
        }

    # Rule 2: Segment must have at least 2 approved slots
    if len(approved_slots) < 2:
        return {
            "status": "not_applicable",
            "recipe": None,
            "evidence": evidence,
            "reason": f"Insufficient approved slots: {len(approved_slots)} (minimum 2 required)"
        }

    # Rule 3: Exclude source_speech / keep_audio segment
    keep_audio = bool(
        segment.get("hold") or
        segment.get("keep_audio") or
        segment.get("audio_role") in ("duck", "diegetic", "source_speech")
    )
    if keep_audio:
        return {
            "status": "not_applicable",
            "recipe": None,
            "evidence": evidence,
            "reason": "Segment requires keep_audio or source_speech"
        }

    # Rule 4: Exclude stock-only segments
    if segment.get("source") == "stock":
        return {
            "status": "not_applicable",
            "recipe": None,
            "evidence": evidence,
            "reason": "Stock-only segment is excluded from sequence planning"
        }

    # Rule 5: Exclude GAP / fallback-only
    retrieval_path = entry.get("retrieval_path")
    if retrieval_path in ("matched_fallback", "live_fallback", "matched", "live"):
        return {
            "status": "not_applicable",
            "recipe": None,
            "evidence": evidence,
            "reason": f"Fallback segment (path: {retrieval_path}) is excluded"
        }

    if any(sl.get("source") == GAP or not sl.get("source") for sl in approved_slots):
        return {
            "status": "not_applicable",
            "recipe": None,
            "evidence": evidence,
            "reason": "Segment contains GAP slots"
        }

    if entry.get("picked_scores") == [GAP]:
        return {
            "status": "not_applicable",
            "recipe": None,
            "evidence": evidence,
            "reason": "Segment has GAP picks"
        }

    # Rule 6: Exclude segment with explicit hold or non-switchable request
    if segment.get("hold"):
        return {
            "status": "not_applicable",
            "recipe": None,
            "evidence": evidence,
            "reason": "Segment has hold enabled"
        }

    # Determine beats based on the actual number of approved slots
    n_slots = len(approved_slots)
    if n_slots == 2:
        beats = ["context", "payoff"]
    elif n_slots == 3:
        beats = ["context", "primary_action", "payoff"]
    else:
        beats = ["context", "primary_action", "detail_reaction", "payoff"]

    # Map each beat to the duration of the corresponding slot to ensure window integrity
    durations = {}
    for idx, beat in enumerate(beats):
        durations[beat] = float(approved_slots[idx]["extract_dur"])

    recipe = {
        "beats": beats,
        "durations": durations,
        "source": "auto_sequence_recipe",
        "reason": f"Auto-planned {len(beats)}-beat sequence for segment {segment.get('segment')}",
        "punctuate_payoff": "payoff" in beats
    }

    return {
        "status": "planned",
        "recipe": recipe,
        "evidence": evidence,
        "reason": f"Successfully planned sequence recipe with {len(beats)} beats"
    }


def segment_pool_from_plan(plan):
    """Derive a shot pool from already-planned story clips for segment sequence.
    Does NOT de-duplicate by source; preserves all evidence fields."""
    pool = []
    for clip in plan or []:
        source = clip.get("source") or clip.get("source_path")
        if not source:
            continue
        shot = {
            "source": source,
            "start": float(clip.get("extract_start") or clip.get("start_sec") or 0.0),
            "dur": float(clip.get("extract_dur") or clip.get("duration_sec") or 0.0),
        }
        # Copy all other evidence fields so they pass to _beat_clip
        for field in ("is_photo", "scene_id", "retrieval_score", "visual_family", "angle_scale", "kenburns", "caption", "function"):
            if field in clip:
                shot[field] = clip[field]
        # Copy exact window fields to avoid rounding mismatch
        if "extract_start" in clip:
            shot["extract_start"] = clip["extract_start"]
        if "extract_dur" in clip:
            shot["extract_dur"] = clip["extract_dur"]
        pool.append(shot)
    return pool
