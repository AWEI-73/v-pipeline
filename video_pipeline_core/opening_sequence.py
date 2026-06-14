"""BR1 — Opening / Hook Sequence Builder.

Compile an APPROVED opening recipe into a designed opening sequence that is
prepended to the render plan, so it changes both the timeline and the true
render (this is a BUILD capability, not a VERIFY audit). Recipe beats:

    hook -> context_montage -> sound_punctuation -> title_reveal -> story_entry

Deterministic compiler with graceful fallback: a beat with no usable material
is dropped and recorded (never invented). `sound_punctuation` is emitted as a
cue only — wiring it into audio is BR3's scope, not BR1's.
"""
from __future__ import annotations


DEFAULT_BEATS = ("hook", "context_montage", "sound_punctuation",
                 "title_reveal", "story_entry")
DEFAULT_BEAT_DURATIONS = {"hook": 2.5, "context": 1.2, "title": 2.0}
DEFAULT_CONTEXT_COUNT = 3


def _shot_clip(shot, dur, *, role, text=None, treatment=None):
    clip = {
        "source": shot["source"],
        "extract_start": round(float(shot.get("start", 0.0)), 3),
        "extract_dur": round(float(dur), 3),
        "slot_dur": round(float(dur), 3),
        "keep_audio": False,
        "is_photo": bool(shot.get("is_photo", False)),
        "segment": 0,                 # opening precedes story segment 1
        "opening_role": role,
    }
    if text:
        clip["text"] = text
    if treatment:
        clip["still_treatment"] = treatment
    return clip


def compile_opening_sequence(recipe, available_shots, *, durations=None):
    """Compile an approved opening recipe into prependable render-plan clips.

    recipe: {beats?, title_text?, context_count?, durations?}
    available_shots: pool [{source, start, dur, role?, is_photo?}] (approved).
    Returns {clips, cues, beats_used, dropped, title_text}. Deterministic."""
    recipe = recipe or {}
    beats = list(recipe.get("beats") or DEFAULT_BEATS)
    durs = {**DEFAULT_BEAT_DURATIONS, **(recipe.get("durations") or {}),
            **(durations or {})}
    title_text = recipe.get("title_text")
    pool = [dict(s) for s in (available_shots or []) if s.get("source")]
    first_shot = dict(pool[0]) if pool else None

    clips, cues, used, dropped = [], [], [], []

    def take(role_hint=None):
        for i, shot in enumerate(pool):
            if role_hint is None or shot.get("role") == role_hint:
                return pool.pop(i)
        return None

    for beat in beats:
        if beat == "hook":
            shot = take("hook") or take()
            if shot:
                clips.append(_shot_clip(shot, durs["hook"], role="hook",
                                        treatment={"mode": "slow_push"}))
                used.append("hook")
            else:
                dropped.append({"beat": "hook", "reason": "no_material"})
        elif beat == "context_montage":
            count = int(recipe.get("context_count", DEFAULT_CONTEXT_COUNT))
            picked = 0
            for _ in range(max(0, count)):
                shot = take("context") or take()
                if not shot:
                    break
                clips.append(_shot_clip(shot, durs["context"], role="context_montage"))
                picked += 1
            if picked:
                used.append("context_montage")
            else:
                dropped.append({"beat": "context_montage", "reason": "no_material"})
        elif beat == "sound_punctuation":
            cues.append({"type": "hit", "anchor": "title_reveal"})  # BR3 wires audio
            used.append("sound_punctuation")
        elif beat == "title_reveal":
            if not title_text:
                dropped.append({"beat": "title_reveal", "reason": "no_title_text"})
                continue
            base = take("title") or take() or first_shot
            if base:
                # full-screen centered title card (darkened bg + big text) — the
                # text layer is the dict shape mv_cut._drawtext_chain consumes.
                clips.append(_shot_clip(base, durs["title"], role="title_reveal",
                                        text={"narrative": title_text},
                                        treatment={"mode": "slow_push"}))
                used.append("title_reveal")
            else:
                dropped.append({"beat": "title_reveal", "reason": "no_material"})
        elif beat == "story_entry":
            used.append("story_entry")    # marker: story segments follow opening
        else:
            dropped.append({"beat": beat, "reason": "unknown_beat"})

    return {
        "artifact_role": "opening_sequence",
        "version": 1,
        "clips": clips,
        "cues": cues,
        "beats_used": used,
        "dropped": dropped,
        "title_text": title_text,
    }


def opening_pool_from_plan(plan, *, max_shots=6):
    """Derive an opening shot pool from already-planned story clips (reuse real
    approved material). Deterministic: plan order, unique sources."""
    pool, seen = [], set()
    for clip in plan or []:
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


def prepend_opening_to_plan(plan, opening_clips):
    """Prepend opening clips and reassign slot_index across the whole plan so
    render file naming stays collision-free."""
    combined = list(opening_clips or []) + list(plan or [])
    for index, clip in enumerate(combined):
        clip["slot_index"] = index
    return combined
