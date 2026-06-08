"""shot_slots.py — Node 9 shot slots expander.

Expands segment grammar contracts into concrete shot slots.
All functions are pure (no I/O, no print).
"""
from __future__ import annotations

from typing import Any


def expand_shot_slots(segment: dict, n_required: int | None = None) -> list[dict]:
    """Expand required and optional segment functions into concrete shot slots.

    Args:
        segment: Dictionary representing a segment contract with sequence_grammar.
        n_required: Optional target shot slot count derived from treatment.

    Returns:
        list of dict: Each slot dict has keys:
            slot, function, reason, preferred_media, target_duration_sec,
            candidate_requirements.
    """
    seg_id = segment.get("segment")
    if seg_id is None:
        seg_id = 1

    grammar = segment.get("sequence_grammar") or {}
    required_funcs = grammar.get("required_functions") or ["establish", "action", "detail", "result"]
    optional_funcs = grammar.get("optional_functions") or []

    # Build the list of functions
    funcs = list(required_funcs)

    if n_required is not None and n_required > len(funcs):
        # 1. Fill with optional functions first
        for opt_func in optional_funcs:
            if len(funcs) >= n_required:
                break
            funcs.append(opt_func)

        # 2. Fill the rest with "detail" functions
        while len(funcs) < n_required:
            funcs.append("detail")

    # Determine shot duration
    seg_duration = segment.get("duration_sec")
    if seg_duration is not None:
        default_dur = float(seg_duration) / max(len(funcs), 1)
    else:
        pacing = segment.get("pacing") or {}
        pref = pacing.get("preferred_shot_sec")
        if pref:
            if isinstance(pref, (list, tuple)) and len(pref) >= 2:
                default_dur = float(sum(pref)) / len(pref)
            else:
                default_dur = float(pref)
        else:
            default_dur = 5.0

    # Determine preferred media
    still_policy = segment.get("still_image_policy") or {}
    still_allowed = still_policy.get("allowed", True)
    pref_media = ["video"]
    if still_allowed:
        pref_media.append("photo")

    slots: list[dict] = []
    for i, func in enumerate(funcs):
        slots.append({
            "slot": f"{seg_id}.{i + 1}",
            "function": func,
            "reason": f"segment {seg_id} function {func}",
            "preferred_media": pref_media,
            "target_duration_sec": round(default_dur, 2),
            "candidate_requirements": {
                "min_candidates": 1,
                "avoid_same_source_as_previous": True,
            },
        })

    return slots
