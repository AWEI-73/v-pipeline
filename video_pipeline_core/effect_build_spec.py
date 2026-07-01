"""Validated control surface for bounded Remotion effect components."""

from __future__ import annotations

import math
from typing import Any, Mapping

from .effect_layer_manifest import generic_layer_types


SUPPORTED_COMPONENTS: dict[str, set[str]] = {
    "MemoryPhotoWall": {
        "duration_sec",
        "story_function",
        "pacing",
        "density",
        "reveal_mode",
        "camera_motion",
        "caption_mode",
    },
    "StoryToMVTransition": {
        "duration_sec",
        "section_from",
        "section_to",
        "pacing_shift",
        "impact_moment_sec",
        "thumbnail_acceleration",
        "motion_grammar",
        "phase_labels",
    },
    "GenericRemotionEffect": {
        "duration_sec",
        "canvas",
        "layers",
        "timing",
        "review_required",
    },
}


SUPPORTED_GENERIC_LAYER_TYPES = generic_layer_types()


def _component(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("effect_build_spec.component must be a non-empty string")
    component = value.strip()
    if component not in SUPPORTED_COMPONENTS:
        raise ValueError(f"unsupported effect_build_spec component: {component}")
    return component


def _positive_number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a positive finite number")
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise ValueError(f"{field} must be a positive finite number")
    return number


def _string_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{field} must be a non-empty string list")
    cleaned = []
    for idx, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{field}[{idx}] must be a non-empty string")
        cleaned.append(item.strip())
    return cleaned


def _generic_layers(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise ValueError("layers must be a non-empty layer list")
    normalized: list[dict[str, Any]] = []
    for idx, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise ValueError(f"layers[{idx}] must be an object")
        layer_id = item.get("id")
        layer_type = item.get("type")
        if not isinstance(layer_id, str) or not layer_id.strip():
            raise ValueError(f"layers[{idx}].id must be a non-empty string")
        if not isinstance(layer_type, str) or not layer_type.strip():
            raise ValueError(f"layers[{idx}].type must be a non-empty string")
        clean_type = layer_type.strip()
        if clean_type not in SUPPORTED_GENERIC_LAYER_TYPES:
            raise ValueError(f"unsupported generic effect layer type: {clean_type}")
        params = item.get("params", {})
        if not isinstance(params, Mapping):
            raise ValueError(f"layers[{idx}].params must be an object")
        normalized.append({
            "id": layer_id.strip(),
            "type": clean_type,
            "params": dict(params),
        })
    return normalized


def _generic_canvas(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("canvas must be an object")
    width = _positive_number(value.get("width"), "canvas.width")
    height = _positive_number(value.get("height"), "canvas.height")
    fps = _positive_number(value.get("fps"), "canvas.fps")
    return {"width": int(width), "height": int(height), "fps": int(fps)}


def validate_effect_build_spec(spec: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and return a normalized Remotion effect build spec.

    The validator is intentionally small. It does not decide aesthetics; it only
    prevents unsupported component names or incomplete control surfaces from
    entering the Remotion worker route.
    """
    if not isinstance(spec, Mapping):
        raise ValueError("effect_build_spec must be an object")
    component = _component(spec.get("component"))
    missing = [field for field in sorted(SUPPORTED_COMPONENTS[component]) if field not in spec]
    if missing:
        raise ValueError(f"{component} missing required field: {missing[0]}")

    normalized = dict(spec)
    normalized["component"] = component
    normalized["duration_sec"] = _positive_number(spec.get("duration_sec"), "duration_sec")
    if component == "StoryToMVTransition":
        normalized["impact_moment_sec"] = _positive_number(spec.get("impact_moment_sec"), "impact_moment_sec")
        normalized["motion_grammar"] = _string_list(spec.get("motion_grammar"), "motion_grammar")
        normalized["phase_labels"] = _string_list(spec.get("phase_labels"), "phase_labels")
        if len(normalized["phase_labels"]) < 2:
            raise ValueError("phase_labels must include source and target labels")
    if component == "GenericRemotionEffect":
        normalized["canvas"] = _generic_canvas(spec.get("canvas"))
        normalized["layers"] = _generic_layers(spec.get("layers"))
        if not isinstance(spec.get("timing"), Mapping):
            raise ValueError("timing must be an object")
        normalized["timing"] = dict(spec.get("timing") or {})
        normalized["review_required"] = bool(spec.get("review_required"))
    return normalized


def effect_build_spec_component_from_params(params: Mapping[str, Any] | None) -> str | None:
    if not isinstance(params, Mapping):
        return None
    spec = params.get("effect_build_spec")
    if spec is None:
        return None
    return validate_effect_build_spec(spec)["component"]
