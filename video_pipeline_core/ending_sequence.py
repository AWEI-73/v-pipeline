"""BR4 - Ending / Payoff Sequence Builder.

Compile an approved ending recipe into real render-plan clips so a video can
close on a callback, payoff, and closing title instead of merely stopping when
the story material runs out. This is BUILD behavior, not a VERIFY score.
"""
from __future__ import annotations

from .opening_sequence import _effective_dur, _usable_shot


DEFAULT_BEATS = ("callback", "payoff", "closing_title")
DEFAULT_BEAT_DURATIONS = {"callback": 2.0, "payoff": 2.5, "closing_title": 2.5}


def _ending_clip(shot, design_dur, *, role, segment, text=None, treatment=None):
    dur = round(_effective_dur(shot, design_dur), 3)
    clip = {
        "source": shot["source"],
        "extract_start": round(float(shot.get("start", 0.0)), 3),
        "extract_dur": dur,
        "slot_dur": dur,
        "keep_audio": False,
        "is_photo": bool(shot.get("is_photo", False)),
        "segment": segment,
        "ending_role": role,
    }
    if text:
        clip["text"] = text
    if treatment:
        clip["still_treatment"] = treatment
    return clip


def compile_ending_sequence(recipe, available_shots, *, segment):
    """Compile an approved ending recipe using only approved shot windows."""
    recipe = recipe or {}
    beats = list(recipe.get("beats") or DEFAULT_BEATS)
    durations = {**DEFAULT_BEAT_DURATIONS, **(recipe.get("durations") or {})}
    closing_text = recipe.get("closing_text")
    clips, cues, used, dropped = [], [], [], []

    pool = []
    for shot in available_shots or []:
        if not shot.get("source"):
            continue
        if _usable_shot(shot):
            pool.append(dict(shot))
        else:
            dropped.append({"reason": "invalid_video_dur", "source": shot.get("source")})
    first_shot = dict(pool[0]) if pool else None

    def take(role_hint=None):
        for index, shot in enumerate(pool):
            if role_hint is None or shot.get("role") == role_hint:
                return pool.pop(index)
        return None

    for beat in beats:
        if beat == "callback":
            shot = take("callback") or take()
            if shot:
                clips.append(_ending_clip(
                    shot, durations["callback"], role="callback", segment=segment,
                    treatment={"mode": "slow_push"}))
                used.append("callback")
            else:
                dropped.append({"beat": "callback", "reason": "no_material"})
        elif beat == "payoff":
            shot = take("payoff") or take()
            if shot:
                clips.append(_ending_clip(
                    shot, durations["payoff"], role="payoff", segment=segment,
                    treatment={"mode": "slow_push"}))
                used.append("payoff")
            else:
                dropped.append({"beat": "payoff", "reason": "no_material"})
        elif beat == "closing_title":
            if not closing_text:
                dropped.append({"beat": "closing_title", "reason": "no_closing_text"})
                continue
            shot = take("closing_title") or take() or first_shot
            if shot:
                clips.append(_ending_clip(
                    shot, durations["closing_title"], role="closing_title",
                    segment=segment, text={"narrative": closing_text},
                    treatment={"mode": "slow_push"}))
                used.append("closing_title")
            else:
                dropped.append({"beat": "closing_title", "reason": "no_material"})
        else:
            dropped.append({"beat": beat, "reason": "unknown_beat"})

    if recipe.get("punctuate_payoff"):
        if "payoff" in {clip["ending_role"] for clip in clips}:
            cues.append({"type": "hit", "anchor": "payoff", "segment": segment})
        else:
            dropped.append({"beat": "sound_punctuation",
                            "reason": "anchor_missing:payoff"})

    return {
        "artifact_role": "ending_sequence",
        "version": 1,
        "segment": segment,
        "clips": clips,
        "cues": cues,
        "beats_used": used,
        "dropped": dropped,
        "closing_text": closing_text,
    }


def ending_pool_from_plan(plan, *, max_shots=6):
    """Derive an ending pool from the story tail, preferring recent sources."""
    pool, seen = [], set()
    for clip in reversed(list(plan or [])):
        source = clip.get("source") or clip.get("source_path")
        if not source or source in seen:
            continue
        seen.add(source)
        pool.append({
            "source": source,
            "start": float(clip.get("extract_start") or clip.get("start_sec") or 0.0),
            "dur": float(clip.get("extract_dur") or clip.get("duration_sec") or 0.0),
            "is_photo": bool(clip.get("is_photo", False)),
        })
        if len(pool) >= int(max_shots):
            break
    return pool


def append_ending_to_plan(plan, ending_clips):
    """Append ending clips and reindex the full render plan."""
    combined = list(plan or []) + list(ending_clips or [])
    for index, clip in enumerate(combined):
        clip["slot_index"] = index
    return combined
