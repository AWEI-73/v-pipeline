"""Capability gate for Effect Factory worker handoff.

This module is intentionally deterministic. It does not decide aesthetics; it
decides whether a requested effect has enough supported layer/API surface to be
sent to the bounded Remotion worker.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .effect_build_spec import SUPPORTED_GENERIC_LAYER_TYPES, validate_effect_build_spec


UNSUPPORTED_CUES = {
    "3d character",
    "realistic 3d",
    "rotoscope",
    "physics simulation",
    "fluid simulation",
    "full cg",
    "dragon character",
    "face swap",
    "body tracking",
}

MATERIAL_GENERATION_CUES = {
    "generate a new",
    "new scene",
    "story scene",
    "two children",
    "character walking",
    "forest scene",
    "no source footage",
}

EDITING_CUES = {
    "trim",
    "cut shorter",
    "remove silence",
    "subtitle only",
    "audio mix",
}

SUPPORTED_CUE_TO_LAYERS = {
    "lightning": ["electric_arcs", "particle_overlay", "light_overlay", "camera_motion", "text"],
    "electric": ["electric_arcs", "particle_overlay", "light_overlay", "radial_current", "text"],
    "current": ["radial_current", "light_overlay", "image_layout", "text"],
    "energy ring": ["radial_current", "light_overlay", "image_layout", "text"],
    "outer ring": ["radial_current", "light_overlay", "image_layout", "text"],
    "crack": ["crack_lines", "particle_overlay", "camera_motion", "film_grain", "text"],
    "earthquake": ["crack_lines", "particle_overlay", "camera_motion", "film_grain", "text"],
    "terminal": ["glyph_stream", "light_overlay", "text"],
    "data stream": ["glyph_stream", "light_overlay", "text"],
    "ink": ["mask_reveal", "texture_overlay", "text"],
    "prism": ["refraction", "chromatic_split", "mask_wipe", "text"],
    "glass": ["refraction", "chromatic_split", "mask_wipe", "text"],
    "photo wall": ["image_layout", "camera_motion", "light_overlay", "text"],
}


def _text(payload: Mapping[str, Any]) -> str:
    parts = [
        payload.get("request"),
        payload.get("effect_role"),
        payload.get("style_family"),
        payload.get("story_function"),
    ]
    return " ".join(str(part).lower() for part in parts if part)


def _layers_from_build_spec(payload: Mapping[str, Any]) -> tuple[list[str], list[str]]:
    spec = payload.get("effect_build_spec")
    if not isinstance(spec, Mapping):
        return [], []
    try:
        normalized = validate_effect_build_spec(spec)
    except ValueError as exc:
        return [], [str(exc)]
    if normalized["component"] != "GenericRemotionEffect":
        return [], []
    layer_types = [str(layer["type"]) for layer in normalized.get("layers") or []]
    return layer_types, []


def _has_positive_duration(payload: Mapping[str, Any]) -> bool:
    duration = payload.get("duration_sec")
    if isinstance(duration, (int, float)) and not isinstance(duration, bool) and duration > 0:
        return True
    spec = payload.get("effect_build_spec")
    if isinstance(spec, Mapping):
        spec_duration = spec.get("duration_sec")
        return isinstance(spec_duration, (int, float)) and not isinstance(spec_duration, bool) and spec_duration > 0
    return False


def _handoff_missing_inputs(payload: Mapping[str, Any]) -> list[str]:
    missing: list[str] = []
    if not isinstance(payload.get("effect_role"), str) or not str(payload.get("effect_role")).strip():
        missing.append("effect_role")
    if not _has_positive_duration(payload):
        missing.append("duration_sec")
    spec = payload.get("effect_build_spec")
    if isinstance(spec, Mapping) and spec.get("review_required") is not True:
        missing.append("effect_build_spec.review_required=true")
    return missing


def _layers_from_cues(text: str) -> list[str]:
    layers: list[str] = []
    for cue, cue_layers in SUPPORTED_CUE_TO_LAYERS.items():
        if cue in text:
            for layer in cue_layers:
                if layer not in layers:
                    layers.append(layer)
    return layers


def review_effect_capability(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return a review artifact for an Effect Factory request."""
    if not isinstance(payload, Mapping):
        raise ValueError("effect capability payload must be an object")
    text = _text(payload)
    requested_layers, errors = _layers_from_build_spec(payload)
    inferred_layers = requested_layers or _layers_from_cues(text)

    decision = "probe_required"
    reason = "request needs a bounded preview before production handoff"
    build_allowed = False
    probe_allowed = True
    reroute_to = None
    next_action = "create_bounded_probe_preview"

    if any(cue in text for cue in MATERIAL_GENERATION_CUES):
        decision = "reroute_material"
        reason = "request asks for new story/material content, not a bounded overlay effect"
        probe_allowed = False
        reroute_to = "generated_material_provider"
        next_action = "route_to_generated_material_or_story_branch"
    elif any(cue in text for cue in EDITING_CUES):
        decision = "reroute_editing"
        reason = "request is an editing/audio/subtitle operation, not an Effect Factory build"
        probe_allowed = False
        reroute_to = "workbench_or_build_worker"
        next_action = "route_to_workbench_or_build_worker"
    elif any(cue in text for cue in UNSUPPORTED_CUES):
        decision = "unsupported"
        reason = "request requires capabilities outside the bounded Remotion worker surface"
        probe_allowed = False
        next_action = "revise_effect_request_or_choose_supported_layers"
    elif errors:
        decision = "unsupported"
        reason = "; ".join(errors)
        probe_allowed = False
        next_action = "revise_effect_build_spec"
    elif requested_layers:
        decision = "supported"
        reason = "all requested GenericRemotionEffect layers are supported"
        missing_for_handoff = _handoff_missing_inputs(payload)
        build_allowed = not missing_for_handoff
        probe_allowed = True
        next_action = "handoff_to_remotion_effect_worker" if build_allowed else "complete_effect_handoff_context"
    elif inferred_layers:
        missing_for_handoff = ["confirmed effect_build_spec.layers"]
        decision = "partial"
        reason = "semantic cues map to supported layers, but reviewer confirmation is still required"
        next_action = "confirm_or_adjust_effect_build_spec"
    else:
        missing_for_handoff = ["confirmed effect_build_spec.layers"]

    return {
        "artifact_role": "effect_capability_review",
        "version": 1,
        "request": payload.get("request", ""),
        "effect_role": payload.get("effect_role", ""),
        "decision": decision,
        "status": "pass" if decision == "supported" else "needs_action",
        "reason": reason,
        "build_allowed": build_allowed,
        "production_handoff_allowed": build_allowed,
        "probe_allowed": probe_allowed,
        "reroute_to": reroute_to,
        "supported_layer_types": sorted(SUPPORTED_GENERIC_LAYER_TYPES),
        "requested_layer_types": requested_layers,
        "suggested_layer_types": inferred_layers,
        "backend_policy": {
            "worker": "remotion-effect-worker",
            "runtime": "remotion",
            "fallback": "do_not_silent_fallback_to_template",
        },
        "required_inputs": [
            "effect_role",
            "duration_sec",
            "story_function_or_request",
            "effect_build_spec.layers for worker handoff",
            "review evidence before dictionary promotion",
        ],
        "missing_inputs": missing_for_handoff if "missing_for_handoff" in locals() else [],
        "next_action": next_action,
    }


def write_effect_capability_review(payload: Mapping[str, Any], out_path: str | Path) -> dict[str, Any]:
    review = review_effect_capability(payload)
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(review, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return review
