"""BR2 — Beat-to-Sequence Recipes.

Compile a story beat into an OPTIONAL multi-shot sequence and actually replace
that segment's render-plan slots, so it changes the timeline (not just a
declaration). It is a selectable BUILD recipe, NOT a universal action-spine gate.

    context -> primary_action -> detail_reaction -> payoff

Reuses BR1's approved-window contract (`shot.dur` = window length, invalid-dur
video dropped) via opening_sequence helpers, so all video windows obey the same
{start, dur} rule. Graceful fallback: a beat with no material is dropped and
recorded. An optional payoff punctuation cue is emitted only when the payoff
clip actually exists (consumed by BR3).
"""
from __future__ import annotations

from .opening_sequence import _effective_dur, _usable_shot


DEFAULT_BEATS = ("context", "primary_action", "detail_reaction", "payoff")
DEFAULT_BEAT_DURATIONS = {"context": 1.5, "primary_action": 2.5,
                          "detail_reaction": 1.5, "payoff": 2.0}


def _beat_clip(shot, design_dur, *, beat_role, segment, treatment=None):
    # Check if exact original window is stored in shot
    if "extract_start" in shot and "extract_dur" in shot:
        start = shot["extract_start"]
        dur = shot["extract_dur"]
    else:
        start = round(float(shot.get("start", 0.0)), 3)
        dur = round(_effective_dur(shot, design_dur), 3)

    clip = {
        "source": shot["source"],
        "extract_start": start,
        "extract_dur": dur,
        "slot_dur": dur,
        "keep_audio": False,
        "segment": segment,
        "beat_role": beat_role,
    }
    # Preserve approved-slot lineage / evidence fields:
    for field in ("scene_id", "need_id", "retrieval_score", "visual_family",
                  "angle_scale", "is_photo", "kenburns", "caption", "function"):
        if field in shot:
            clip[field] = shot[field]
    if treatment:
        clip["still_treatment"] = treatment
    return clip


def compile_beat_sequence(recipe, available_shots, *, segment):
    """Compile an approved beat recipe into render-plan clips for one segment.

    recipe: {beats?, durations?, shots?, punctuate_payoff?}
    Returns {segment, clips, cues, beats_used, dropped}. Deterministic."""
    recipe = recipe or {}
    beats = list(recipe.get("beats") or DEFAULT_BEATS)
    durs = {**DEFAULT_BEAT_DURATIONS, **(recipe.get("durations") or {})}

    clips, cues, used, dropped = [], [], [], []
    pool = []
    for shot in (available_shots or []):
        if not shot.get("source"):
            continue
        if _usable_shot(shot):                 # BR1 window contract
            pool.append(dict(shot))
        else:
            dropped.append({"reason": "invalid_video_dur", "source": shot.get("source")})

    def take(role_hint=None):
        for i, shot in enumerate(pool):
            if role_hint is None or shot.get("role") == role_hint:
                return pool.pop(i)
        return None

    for beat in beats:
        if beat not in DEFAULT_BEAT_DURATIONS:
            dropped.append({"beat": beat, "reason": "unknown_beat"})
            continue
        shot = take(beat) or take()
        if shot:
            treatment = {"mode": "slow_push"} if beat in ("context", "payoff") else None
            clips.append(_beat_clip(shot, durs[beat], beat_role=beat,
                                    segment=segment, treatment=treatment))
            used.append(beat)
        else:
            dropped.append({"beat": beat, "reason": "no_material"})

    # optional payoff punctuation — only if the payoff clip was actually produced
    if recipe.get("punctuate_payoff"):
        if "payoff" in {clip["beat_role"] for clip in clips}:
            cues.append({"type": "hit", "anchor": "payoff", "segment": segment})
            used.append("sound_punctuation")
        else:
            dropped.append({"beat": "sound_punctuation", "reason": "anchor_missing:payoff"})

    return {
        "artifact_role": "beat_sequence",
        "version": 1,
        "segment": segment,
        "clips": clips,
        "cues": cues,
        "beats_used": used,
        "dropped": dropped,
    }
