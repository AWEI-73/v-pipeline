"""Remotion effect capability manifest.

The template dictionary records reusable effect treatments. This manifest adds
operational status: whether each template has a concrete worker renderer and
which reference review/evidence currently supports it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .effect_template_dictionary import (
    load_effect_template_dictionary,
    validate_effect_template_dictionary,
)


SUPPORTED_TEMPLATE_IDS = {
    "training_opening_title",
    "module_label_white_blue",
    "speaker_subtitle_yellow_bar",
    "soft_light_transition",
    "highlight_warm_glow",
    "blurred_side_fill",
    "profile_memory_card",
    "film_strip_transition_card",
    "clean_white_quote_card",
    "memory_photo_wall",
}


def _load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8-sig") as f:
        payload = json.load(f)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _reference_review_summary(reference_review_path: str | Path | None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if reference_review_path is None:
        return [], {}
    path = Path(reference_review_path)
    review = _load_json(path)
    evidence = dict(review.get("verify_evidence") or {})
    black = evidence.get("black_frame_audit")
    if isinstance(black, dict) and black.get("pass") is False:
        black.setdefault("next_action", "formalize_or_fix_black_transition_plates")
    return [{
        "artifact": str(path),
        "artifact_role": review.get("artifact_role"),
        "source_reference": review.get("source_reference"),
        "review_verdict": review.get("review_verdict"),
    }], evidence


def build_remotion_template_manifest(
    dictionary: Mapping[str, Any] | None = None,
    *,
    reference_review_path: str | Path | None = None,
    supported_template_ids: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Build a machine-readable support matrix for Remotion effect templates."""
    payload = dictionary if dictionary is not None else load_effect_template_dictionary()
    validate_effect_template_dictionary(payload)
    supported = set(supported_template_ids or SUPPORTED_TEMPLATE_IDS)
    reference_reviews, verify_evidence = _reference_review_summary(reference_review_path)

    templates: list[dict[str, Any]] = []
    for template in payload["templates"]:
        template_id = str(template["template_id"])
        has_support = template_id in supported
        templates.append({
            "template_id": template_id,
            "label": template.get("label"),
            "role": template.get("role"),
            "component_family": template.get("component_family"),
            "render_backend": template.get("render_backend"),
            "concrete_worker_support": has_support,
            "status": "verified" if has_support else "planned",
            "required_fields": list(template.get("required_fields") or []),
            "default_presentation": dict(template.get("default_presentation") or {}),
            "notes": template.get("notes"),
        })

    return {
        "artifact_role": "remotion_effect_capability_manifest",
        "version": 1,
        "source_dictionary": payload.get("dictionary_id"),
        "template_ids": [template["template_id"] for template in templates],
        "summary": {
            "template_count": len(templates),
            "concrete_worker_supported_count": sum(
                1 for template in templates if template["concrete_worker_support"]
            ),
            "verified_count": sum(1 for template in templates if template["status"] == "verified"),
        },
        "reference_reviews": reference_reviews,
        "verify_evidence": verify_evidence,
        "templates": templates,
    }


def write_remotion_template_manifest(
    out_path: str | Path,
    *,
    dictionary_path: str | Path | None = None,
    reference_review_path: str | Path | None = None,
) -> dict[str, Any]:
    dictionary = load_effect_template_dictionary(dictionary_path)
    manifest = build_remotion_template_manifest(
        dictionary,
        reference_review_path=reference_review_path,
    )
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest
