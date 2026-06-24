"""Effect template dictionary helpers.

The dictionary records reusable, review-derived effect treatments. It is a
small artifact layer above effect intent: upstream stages can name a template,
while Remotion/ffmpeg workers still receive concrete presentation parameters.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


DEFAULT_DICTIONARY_PATH = (
    Path(__file__).resolve().parents[1]
    / "examples"
    / "training_recap_effect_dictionary.json"
)


def _non_empty_str(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def load_effect_template_dictionary(path: str | Path | None = None) -> dict[str, Any]:
    dictionary_path = Path(path) if path is not None else DEFAULT_DICTIONARY_PATH
    with dictionary_path.open(encoding="utf-8-sig") as f:
        payload = json.load(f)
    validate_effect_template_dictionary(payload)
    return payload


def validate_effect_template_dictionary(payload: Mapping[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise ValueError("effect template dictionary must be object")
    if payload.get("artifact_role") != "effect_template_dictionary":
        raise ValueError("artifact_role must be effect_template_dictionary")
    if payload.get("version") != 1:
        raise ValueError("effect_template_dictionary version must be 1")
    templates = payload.get("templates")
    if not isinstance(templates, list) or not templates:
        raise ValueError("effect_template_dictionary.templates must be non-empty list")
    seen: set[str] = set()
    for idx, template in enumerate(templates):
        if not isinstance(template, dict):
            raise ValueError(f"templates[{idx}] must be object")
        template_id = _non_empty_str(template.get("template_id"), f"templates[{idx}].template_id")
        if template_id in seen:
            raise ValueError(f"duplicate template_id: {template_id}")
        seen.add(template_id)
        _non_empty_str(template.get("role"), f"templates[{idx}].role")
        _non_empty_str(template.get("component_family"), f"templates[{idx}].component_family")
        _non_empty_str(template.get("render_backend"), f"templates[{idx}].render_backend")
        if not isinstance(template.get("required_fields"), list):
            raise ValueError(f"templates[{idx}].required_fields must be list")
        presentation = template.get("default_presentation")
        if not isinstance(presentation, dict):
            raise ValueError(f"templates[{idx}].default_presentation must be object")
        for field in ("text_position", "text_scale", "effect_strength", "safe_area"):
            _non_empty_str(presentation.get(field), f"templates[{idx}].default_presentation.{field}")


def templates_by_id(payload: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    validate_effect_template_dictionary(payload)
    return {
        str(template["template_id"]): template
        for template in payload["templates"]
    }


def get_effect_template(template_id: str, *,
                        dictionary: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
    payload = dictionary if dictionary is not None else load_effect_template_dictionary()
    template = templates_by_id(payload).get(_non_empty_str(template_id, "template_id"))
    if template is None:
        raise ValueError(f"unknown effect template_id: {template_id}")
    return template


def template_defaults(template_id: str, *,
                      dictionary: Mapping[str, Any] | None = None) -> dict[str, Any]:
    template = get_effect_template(template_id, dictionary=dictionary)
    return dict(template.get("default_presentation") or {})
