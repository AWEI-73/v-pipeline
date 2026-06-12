"""Resolve segment pacing from the channel currently carrying the story."""
from __future__ import annotations


_MODE_FALLBACKS = {
    "warm_documentary": [4.0, 8.0],
    "story_documentary": [3.0, 8.0],
    "training_recap": [2.5, 6.0],
    "rhythmic_mv": [1.5, 4.0],
    "promo": [1.5, 4.0],
}


def resolve_attention_budget(
    segment: dict,
    *,
    mode: str = "warm_documentary",
    is_still: bool | None = None,
    has_motion: bool | None = None,
) -> dict:
    """Return the attention owner and healthy per-shot duration band."""
    execution = segment.get("execution_plan") or {}
    narration = execution.get("narration") or {}
    music = execution.get("music") or {}
    narration_mode = narration.get("mode") or "none"
    treatment = segment.get("treatment")

    if narration_mode not in ("none", "captions_only", "no_speech"):
        return {
            "owner": "narration",
            "shot_sec": [3.0, 8.0],
            "reason": "speech carries the story, so the visual may hold",
        }

    if treatment == "photo_stack_beat":
        return {
            "owner": "visual",
            "shot_sec": [0.5, 1.0],
            "reason": "photo stack communicates through rapid visual accumulation",
        }

    declared_no_motion = segment.get("still_motion") == "none"
    if is_still is None:
        is_still = treatment == "single_hold"
    if has_motion is None:
        has_motion = not declared_no_motion
    if is_still and not has_motion:
        return {
            "owner": "visual",
            "shot_sec": [1.0, 2.0],
            "reason": "untreated still has no other channel to sustain attention",
        }

    if str(music.get("intensity") or "").lower() in ("high", "peak", "energetic"):
        return {
            "owner": "music",
            "shot_sec": [0.8, 2.0],
            "reason": "high-energy music carries momentum and requires fast cutting",
        }

    if str(music.get("intensity") or "").lower() not in ("", "none", "low"):
        return {
            "owner": "music",
            "shot_sec": [1.5, 4.0],
            "reason": "music-only segment requires visual progression to carry the story",
        }

    return {
        "owner": "shared",
        "shot_sec": list(_MODE_FALLBACKS.get(mode) or _MODE_FALLBACKS["warm_documentary"]),
        "reason": "no dominant channel declared; use the mode pacing band",
    }
