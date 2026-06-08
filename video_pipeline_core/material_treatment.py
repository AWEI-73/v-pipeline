"""material_treatment.py — Treatment resolver for the material-treatment grammar.

Given a segment's editing_intent / content_pattern / material_treatment override
and the beat grid, resolve which concrete treatment materializes each segment,
how many materials it needs, and how the four lanes (photo/video, subtitle,
music) co-vary.

All functions are pure (no I/O, no print). Provider/backend neutral.

Spec source: docs/material-treatment-grammar-spec.md
"""
from __future__ import annotations

import math
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_TREATMENTS = frozenset({
    "single_hold",
    "photo_stack_beat",
    "quick_cut_bridge",
    "stepped_sequence",
    "video_primary",
    "collage",
    "real_material_only",
})

VALID_CONTENT_PATTERNS = frozenset({
    "emotional",
    "establishing",
    "enumeration",
    "process",
    "bridge",
    "action",
    "testimony",
    "proof",
    "identity",
})

# content_pattern → default treatment (from spec table)
_PATTERN_DEFAULT_TREATMENT: dict[str, str] = {
    "emotional": "single_hold",
    "establishing": "single_hold",
    "enumeration": "photo_stack_beat",
    "process": "stepped_sequence",
    "bridge": "quick_cut_bridge",
    "action": "video_primary",
    "testimony": "real_material_only",
    "proof": "real_material_only",
    "identity": "real_material_only",
}

# Honesty-guard patterns: MUST resolve to real_material_only regardless.
_HONESTY_GUARD_PATTERNS = frozenset({"testimony", "proof", "identity"})

# section_role → fallback content_pattern (when content_pattern is absent)
_ROLE_FALLBACK_PATTERN: dict[str, str] = {
    "opening": "establishing",
    "closing": "emotional",
}

# Lane co-variation table (from spec §Lane co-variation)
_LANE_TABLE: dict[str, dict] = {
    "single_hold": {
        "photo_video": "1 still slow_push / 1 clip",
        "subtitle": "narrative_card",
        "music": "swell_or_drop",
    },
    "photo_stack_beat": {
        "photo_video": "N stills on beat",
        "subtitle": "per_item_label",
        "music": "fast_on_beat_no_duck",
    },
    "quick_cut_bridge": {
        "photo_video": "2-4 fast stills/clips",
        "subtitle": "none_or_short_label",
        "music": "beat_driven_energetic",
    },
    "stepped_sequence": {
        "photo_video": "ordered clips/stepped stills",
        "subtitle": "optional_step_label",
        "music": "steady_low",
    },
    "video_primary": {
        "photo_video": "clip",
        "subtitle": "light_label",
        "music": "steady_duck_if_diegetic",
    },
    "collage": {
        "photo_video": "N stills composited in one frame",
        "subtitle": "narrative_card",
        "music": "steady_low",
    },
    "real_material_only": {
        "photo_video": "real clip/photo, original audio",
        "subtitle": "name_super_and_asr",
        "music": "duck_under_speech",
    },
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_content_pattern(segment: dict) -> str | None:
    """Extract content_pattern from segment, checking editing_intent first."""
    ei = segment.get("editing_intent") or {}
    return ei.get("content_pattern")


def _get_section_role(segment: dict) -> str | None:
    """Extract section_role / segment_role from various possible locations."""
    core = segment.get("core") or {}
    role = core.get("section_role")
    if role:
        return role
    ei = segment.get("editing_intent") or {}
    return ei.get("segment_role")


def _get_items(segment: dict) -> list:
    """Extract the items list for enumeration/process/collage treatments."""
    mt = segment.get("material_treatment") or {}
    items = mt.get("items")
    if items:
        return items
    # Fallback: try content_items at segment root
    return segment.get("content_items") or []


def _get_steps(segment: dict) -> list:
    """Extract steps list for process/stepped_sequence."""
    mt = segment.get("material_treatment") or {}
    steps = mt.get("steps") or mt.get("items")
    if steps:
        return steps
    return segment.get("steps") or segment.get("content_items") or []


def _get_segment_duration(segment: dict) -> float:
    """Get segment duration in seconds."""
    dur = segment.get("duration_sec")
    if dur is not None:
        return float(dur)
    pacing = segment.get("pacing") or {}
    shots = pacing.get("preferred_shot_sec")
    if shots and len(shots) >= 2:
        return float(shots[1])  # upper bound as fallback
    return 4.0  # sensible default


def _get_bridge_shot_sec(editing_policy: dict | None) -> float:
    """Get bridge_shot_sec from editing_policy or default."""
    if editing_policy:
        bridge = editing_policy.get("bridge_shot_sec")
        if bridge:
            if isinstance(bridge, (list, tuple)) and len(bridge) >= 2:
                return float(bridge[1])  # upper bound
            return float(bridge)
    return 1.0  # spec default upper bound


# ---------------------------------------------------------------------------
# Main resolver
# ---------------------------------------------------------------------------


def resolve_treatment(
    segment: dict,
    beat_count: int,
    editing_policy: dict | None = None,
) -> dict:
    """Resolve the material treatment for a segment.

    Returns a dict with:
        treatment     — one of VALID_TREATMENTS
        n_required    — how many materials the segment needs
        lane_plan     — {photo_video, subtitle, music} from the lane co-variation table
        reason        — human-readable reason for the resolution

    Resolution priority:
      1. segment.material_treatment.treatment (explicit override)
      2. segment.editing_intent.content_pattern → default treatment
      3. segment.core.section_role / editing_intent.segment_role fallback
         (opening → establishing, closing → emotional)

    Honesty guard:
      content_pattern ∈ {testimony, proof, identity} → always real_material_only
      regardless of any override.
    """
    editing_policy = editing_policy or {}

    # --- 1. Determine content_pattern ---
    content_pattern = _get_content_pattern(segment)
    reason_parts: list[str] = []

    # --- 2. Honesty guard: if content_pattern is testimony/proof/identity,
    #        force real_material_only regardless of any override ---
    if content_pattern in _HONESTY_GUARD_PATTERNS:
        treatment = "real_material_only"
        reason_parts.append(
            f"content_pattern={content_pattern} → honesty guard forces real_material_only"
        )
        n_required = 1
        lane_plan = dict(_LANE_TABLE[treatment])
        return {
            "treatment": treatment,
            "n_required": n_required,
            "lane_plan": lane_plan,
            "reason": "; ".join(reason_parts),
        }

    # --- 3. Resolve treatment ---
    # Priority 1: explicit material_treatment override
    mt = segment.get("material_treatment") or {}
    explicit_treatment = mt.get("treatment")

    if explicit_treatment and explicit_treatment in VALID_TREATMENTS:
        treatment = explicit_treatment
        reason_parts.append(f"explicit material_treatment override: {treatment}")
    elif content_pattern and content_pattern in _PATTERN_DEFAULT_TREATMENT:
        # Priority 2: content_pattern → default
        # Check editing_policy overrides for pattern→treatment mapping
        policy_defaults = editing_policy.get("treatment_defaults_by_pattern") or {}
        treatment = policy_defaults.get(content_pattern) or _PATTERN_DEFAULT_TREATMENT[content_pattern]
        reason_parts.append(f"content_pattern={content_pattern} → {treatment}")
    else:
        # Priority 3: section_role fallback
        section_role = _get_section_role(segment)
        fallback_pattern = _ROLE_FALLBACK_PATTERN.get(section_role or "")
        if fallback_pattern:
            treatment = _PATTERN_DEFAULT_TREATMENT[fallback_pattern]
            reason_parts.append(
                f"section_role={section_role} → fallback pattern={fallback_pattern} → {treatment}"
            )
        else:
            # Ultimate fallback: single_hold
            treatment = "single_hold"
            reason_parts.append("no content_pattern or section_role → fallback single_hold")

    # --- 4. Compute n_required ---
    n_required = _compute_n_required(segment, treatment, beat_count, editing_policy)
    reason_parts.append(f"n_required={n_required}")

    # --- 5. Lane plan ---
    lane_plan = dict(_LANE_TABLE.get(treatment, _LANE_TABLE["single_hold"]))

    return {
        "treatment": treatment,
        "n_required": n_required,
        "lane_plan": lane_plan,
        "reason": "; ".join(reason_parts),
    }


def _compute_n_required(
    segment: dict,
    treatment: str,
    beat_count: int,
    editing_policy: dict | None,
) -> int:
    """Derive the number of materials required based on treatment type.

    From the spec "Quantity is derived":
      single_hold         → 1
      video_primary       → 1
      real_material_only  → 1
      photo_stack_beat    → len(items), clamped to beat_count
      quick_cut_bridge    → ceil(segment_sec / bridge_shot_sec), clamped 2..4
      stepped_sequence    → len(steps)
      collage             → len(items), minimum 2
    """
    editing_policy = editing_policy or {}

    if treatment in ("single_hold", "video_primary", "real_material_only"):
        return 1

    if treatment == "photo_stack_beat":
        items = _get_items(segment)
        n = len(items) if items else beat_count
        # Clamp to available beats
        if beat_count > 0:
            n = min(n, beat_count)
        return max(n, 1)

    if treatment == "quick_cut_bridge":
        seg_dur = _get_segment_duration(segment)
        bridge_shot = _get_bridge_shot_sec(editing_policy)
        n = math.ceil(seg_dur / bridge_shot) if bridge_shot > 0 else 2
        # Spec says 2..4 typical
        return max(2, min(n, 4))

    if treatment == "stepped_sequence":
        steps = _get_steps(segment)
        return max(len(steps), 1)

    if treatment == "collage":
        items = _get_items(segment)
        return max(len(items), 2)

    # Fallback
    return 1
