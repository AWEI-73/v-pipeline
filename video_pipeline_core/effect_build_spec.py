"""Validated control surface for bounded Remotion effect components."""

from __future__ import annotations

import math
from typing import Any, Mapping


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
}


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
    return normalized


def effect_build_spec_component_from_params(params: Mapping[str, Any] | None) -> str | None:
    if not isinstance(params, Mapping):
        return None
    spec = params.get("effect_build_spec")
    if spec is None:
        return None
    return validate_effect_build_spec(spec)["component"]
