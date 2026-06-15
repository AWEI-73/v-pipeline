"""SRP2 — Opening / Hook Auto Planner.

Derive a SHALLOW, deterministic opening recipe from the already-approved story
plan slots, then hand it to the existing BR1 `compile_opening_sequence`. This is
a BUILD capability (it changes the timeline + true render), not a VERIFY audit,
and not story understanding or aesthetic direction. It only re-orders a handful
of approved story shots into a hook → context_montage → title_reveal → story_entry
opening that is PREPENDED to the story plan; the original story timeline is never
modified.

Safety principles (inherited from SRP1):
  * use only approved story-plan slots (no re-retrieval, no material map dipping)
  * never invent source / scene_id / window / evidence
  * correctness (retrieval_score) is never overridden by diversity preferences
  * preserve evidence / lineage on the selected shots
  * a manual `script["opening_recipe"]` always wins (auto planner yields
    not_applicable so the caller keeps the manual path)
  * the original script / slots are never mutated

The result is a runtime-ephemeral plan: it builds NO second canonical schema and
NO second opening compiler. The selected shots ride in `recipe["shots"]`, which
the existing `compile_opening_sequence` already consumes.
"""
from __future__ import annotations

from .vt_core import GAP

# Title text may ONLY come from an explicit, human-authored script/contract
# field. The planner never fabricates copy.
_TITLE_FIELDS = ("opening_title", "title")

# Audio roles whose original sound is load-bearing — never reused as silent
# opening b-roll (a hook must never steal a source-speech / diegetic key shot).
_PROTECTED_AUDIO_ROLES = ("source_speech", "diegetic", "duck")


def _is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _is_qualified(slot):
    """A story slot is an eligible opening candidate only if it is an APPROVED,
    re-usable, renderable shot. This deterministically excludes GAP / missing
    source, fallback-only slots (no scene_id evidence), source_speech / keep_audio
    key shots, explicit holds, and illegal windows."""
    src = slot.get("source")
    if not src or src == GAP:
        return False
    # approved map-ranked evidence: a real scene_id. Fallback-only / live shots
    # without scene_id evidence are not eligible (req. 四.5 / H).
    if not slot.get("scene_id"):
        return False
    if slot.get("keep_audio"):
        return False
    if slot.get("audio_role") in _PROTECTED_AUDIO_ROLES:
        return False
    if slot.get("hold") or slot.get("hold_reason"):
        return False
    # window integrity
    if bool(slot.get("is_photo", False)):
        return True                      # photo: design-duration shot, 0-window ok
    dur = slot.get("extract_dur")
    start = slot.get("extract_start", 0.0)
    if not _is_number(dur) or dur <= 0:
        return False
    if not _is_number(start) or start < 0:
        return False
    return True


def _correctness(slot):
    score = slot.get("retrieval_score")
    return float(score) if _is_number(score) else 0.0


def _rank_key(slot):
    """Deterministic, CORRECTNESS-FIRST ranking. retrieval_score dominates so a
    high-score candidate can never be displaced by a low-score one for a
    family/scale preference (req. G). The remaining keys are soft, same-tier
    tie-breakers only: video over photo, evidence-richer first, then scene_id as
    the final deterministic tie-break."""
    is_photo = bool(slot.get("is_photo", False))
    has_family_scale = bool(slot.get("visual_family") or slot.get("angle_scale"))
    return (
        -_correctness(slot),                 # 1) correctness tier (higher first)
        0 if not is_photo else 1,            # 2) video over photo (same tier)
        0 if has_family_scale else 1,        # 3) evidence-richer first (same tier)
        str(slot.get("scene_id") or ""),     # 4) deterministic final tie-break
    )


def _shot_from_slot(slot):
    """Build a BR1 opening-pool shot from an approved slot. `start`/`dur` are the
    approved window (start position + window length); only evidence fields that
    actually exist on the slot are copied (no invented defaults)."""
    shot = {
        "source": slot["source"],
        "start": float(slot.get("extract_start") or 0.0),
        "dur": float(slot.get("extract_dur") or 0.0),
    }
    for field in ("is_photo", "kenburns", "scene_id", "retrieval_score",
                  "visual_family", "angle_scale", "caption", "function"):
        if field in slot:
            shot[field] = slot[field]
    return shot


def _title_text(script):
    for field in _TITLE_FIELDS:
        val = script.get(field)
        if isinstance(val, str) and val.strip():
            return val.strip(), field
    return None, None


def plan_opening_recipe(script, approved_story_plan, *, policy=None):
    """Plan a deterministic opening recipe from approved story-plan slots.

    script: the (already deep-copied by run_mv) script dict — read only.
    approved_story_plan: the frozen story render-plan slots — read only.
    policy: optional dict (reserved; deterministic defaults used today).

    Returns:
    {
      "status": "planned" | "not_applicable",
      "recipe": { beats, title_text, context_count, shots, source, reason } | None,
      "selected_scene_ids": [...],
      "evidence": {...},
      "reason": "...",
    }
    """
    script = script or {}
    approved_story_plan = approved_story_plan or []

    # Rule 1: a manual opening_recipe always wins — auto planner stands down.
    if script.get("opening_recipe"):
        return {
            "status": "not_applicable",
            "recipe": None,
            "selected_scene_ids": [],
            "evidence": {"approved_slot_count": len(approved_story_plan)},
            "reason": "Manual opening_recipe present; auto planner stands down",
        }

    candidates = [sl for sl in approved_story_plan if _is_qualified(sl)]
    ranked = sorted(candidates, key=_rank_key)

    title_text, title_field = _title_text(script)
    distinct_families = sorted({c.get("visual_family") for c in ranked
                                if c.get("visual_family")})
    evidence = {
        "approved_slot_count": len(approved_story_plan),
        "qualified_candidate_count": len(ranked),
        "distinct_visual_families": len(distinct_families),
        "title_source": title_field,
    }

    n = len(ranked)

    # Rule 2: need at least 2 qualified candidates to form a worthwhile opening
    # (a single shot would just duplicate the story's first frame — req. B).
    if n < 2:
        return {
            "status": "not_applicable",
            "recipe": None,
            "selected_scene_ids": [],
            "evidence": evidence,
            "reason": f"Insufficient qualified opening candidates: {n} (minimum 2)",
        }

    # Determine the shallow opening shape from the qualified candidate count.
    # story_entry is a marker beat (no clip): the real story follows the opening.
    if n == 2:
        beats = ["hook", "story_entry"]
        context_count = 0
        take = 1                          # hook only
    elif n == 3:
        beats = ["hook", "context_montage", "story_entry"]
        context_count = 1
        take = 2                          # hook + 1 context
    else:                                 # n >= 4
        if title_text:
            beats = ["hook", "context_montage", "title_reveal", "story_entry"]
            context_count = 1
            take = 3                      # hook + 1 context + title base (distinct)
        else:
            beats = ["hook", "context_montage", "story_entry"]
            context_count = 2
            take = 3                      # hook + 2 context

    selected = ranked[:take]
    shots = [_shot_from_slot(sl) for sl in selected]
    selected_scene_ids = [sl.get("scene_id") for sl in selected]

    reason = (f"Auto-planned {len([b for b in beats if b != 'story_entry'])}-beat "
              f"opening from {n} approved candidate(s)"
              + (" with title_reveal" if "title_reveal" in beats else ""))

    recipe = {
        "beats": beats,
        "title_text": title_text,
        "context_count": context_count,
        "shots": shots,
        "source": "auto_opening_recipe",
        "reason": reason,
    }

    return {
        "status": "planned",
        "recipe": recipe,
        "selected_scene_ids": selected_scene_ids,
        "evidence": evidence,
        "reason": reason,
    }
