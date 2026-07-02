"""Effect Factory design concept planning and review.

This module sits between fuzzy effect intent and backend worker contracts. It
turns vague language into a reviewable design brief, multiple concept options,
a scored selection, downstream prompt parameters, and a post-render design
review surface.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Mapping


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _lower_text(value: Any) -> str:
    return _clean_text(value).lower()


def _copy_json(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False))


def _write_json(path: str | Path, payload: Mapping[str, Any]) -> str:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def _tokens_for_request(request: str) -> set[str]:
    text = _lower_text(request)
    tokens = set()
    if any(token in text for token in ("溫度", "有温度", "warm", "human", "情感", "感人")):
        tokens.add("warmth")
    if any(token in text for token in ("回憶", "记忆", "memory", "recap", "回顧", "回顾")):
        tokens.add("memory")
    if any(token in text for token in ("慢慢", "slow", "湧", "涌", "浮現", "浮现")):
        tokens.add("slow_reveal")
    if any(token in text for token in ("不要太花", "克制", "restrained", "不要太炫", "not flashy")):
        tokens.add("restrained")
    if any(token in text for token in ("不要像簡報", "不要像简报", "presentation", "簡報", "简报", "slide")):
        tokens.add("avoid_presentation")
    if any(token in text for token in ("訓練", "训练", "training", "class", "team", "團隊", "团队")):
        tokens.add("training_context")
    if not tokens:
        tokens.update({"warmth", "memory", "restrained"})
    return tokens


def build_effect_design_brief(
    *,
    request: str,
    effect_role: str = "opening_title",
    duration_sec: float = 4.0,
    material_context: str = "reviewed_or_local_material_refs",
) -> dict[str, Any]:
    """Build a reviewable design brief from fuzzy effect language."""
    if not _clean_text(request):
        raise ValueError("request must be a non-empty string")
    duration = float(duration_sec)
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("duration_sec must be a positive finite number")
    tokens = _tokens_for_request(request)
    emotional_core = []
    if "warmth" in tokens:
        emotional_core.append("warmth")
    if "memory" in tokens:
        emotional_core.append("memory")
    if "restrained" in tokens:
        emotional_core.append("restraint")
    if "slow_reveal" in tokens:
        emotional_core.append("slow_emergence")
    if not emotional_core:
        emotional_core = ["clarity", "controlled_emotion"]

    negative_direction = [
        "avoid_presentation_deck",
        "avoid_generic_template",
        "avoid_excessive_flash",
        "avoid_covering_faces_or_proof_material",
    ]
    if "restrained" in tokens:
        negative_direction.append("avoid_party_energy")

    return {
        "artifact_role": "effect_design_brief",
        "version": 1,
        "source_request": request,
        "effect_role": effect_role,
        "duration_sec": duration,
        "material_context": material_context,
        "emotional_core": emotional_core,
        "visual_metaphors": [
            "memory_surfaces_over_time",
            "reviewed_moments_gather_into_context",
            "warm_light_as_emotional_thread",
        ],
        "audience_feeling_goal": [
            "this_is_a_real_recap",
            "quiet_curiosity_to_keep_watching",
            "human_warmth_without_sentimentality",
        ],
        "negative_direction": negative_direction,
        "copy_direction": {
            "title": "short_specific_human_title",
            "subtitle": "one_plain_emotional_line",
            "avoid_copy": [
                "Reviewed material memory wall",
                "Opening",
                "Untitled",
                "TITLE",
            ],
        },
        "design_questions": [
            "Which real material refs carry the most human warmth?",
            "Can the concept read in 4-6 seconds without explanatory text?",
            "Does the title feel authored rather than route-generated?",
        ],
    }


def _concept(
    concept_id: str,
    name: str,
    *,
    visual_primitives: list[str],
    motion_primitives: list[str],
    typography: Mapping[str, Any],
    material_usage: Mapping[str, Any],
    prompt_parameters: Mapping[str, Any],
    fits: list[str],
    risks: list[str],
    base_score: int,
) -> dict[str, Any]:
    return {
        "concept_id": concept_id,
        "name": name,
        "visual_primitives": visual_primitives,
        "motion_primitives": motion_primitives,
        "typography_direction": dict(typography),
        "material_usage_rule": dict(material_usage),
        "prompt_parameters": _copy_json(prompt_parameters),
        "why_it_fits": fits,
        "risks": risks,
        "score": base_score,
        "review_rubric": [
            "emotional_fit",
            "presentation_avoidance",
            "copy_specificity",
            "material_presence",
            "pacing_fit",
        ],
    }


def build_effect_concept_options(design_brief: Mapping[str, Any]) -> dict[str, Any]:
    """Build multiple design concepts from a design brief."""
    if design_brief.get("artifact_role") != "effect_design_brief":
        raise ValueError("design_brief must have artifact_role effect_design_brief")
    emotional = set(design_brief.get("emotional_core") or [])
    negative = set(design_brief.get("negative_direction") or [])
    duration = float(design_brief.get("duration_sec") or 4.0)
    memory_score = 2 if "memory" in emotional else 0
    slow_score = 1 if "slow_emergence" in emotional else 0
    avoid_deck_score = 1 if "avoid_presentation_deck" in negative else 0

    concepts = [
        _concept(
            "quiet_memory_wall",
            "Quiet Memory Wall",
            visual_primitives=[
                "deep_neutral_background",
                "reviewed_photo_wall",
                "restrained_warm_glow",
                "human_scale_title",
                "low_density_layout",
            ],
            motion_primitives=[
                "one_by_one_image_reveal",
                "slow_push_in",
                "gentle_depth_parallax",
                "title_settle_after_memory_context",
            ],
            typography={
                "position": "bottom_left",
                "scale": "large_but_quiet",
                "weight": "bold_readable",
                "subtitle": "small_plain_line",
                "avoid_copy": design_brief.get("copy_direction", {}).get("avoid_copy", []),
            },
            material_usage={
                "source": "reviewed_material_refs",
                "priority": "people_group_and_classroom_moments",
                "max_refs": 6,
                "preserve_faces": True,
                "do_not_claim_material_truth": True,
            },
            prompt_parameters={
                "template_id": "memory_photo_wall",
                "presentation": {
                    "background_style": "memory_photo_wall",
                    "text_position": "bottom_left",
                    "text_scale": "large",
                    "effect_strength": "subtle",
                    "safe_area": "title_safe",
                    "accent_color": "#ffd36a",
                    "text_color": "#ffffff",
                    "theme": "warm_training_recap",
                },
                "effect_build_spec": {
                    "component": "MemoryPhotoWall",
                    "duration_sec": duration,
                    "story_function": "warm_human_training_recap_opening",
                    "pacing": "slow",
                    "density": "low",
                    "reveal_mode": "one_by_one",
                    "reveal_interval_sec": 0.9,
                    "hold_after_full_wall_sec": 0.8,
                    "camera_motion": "slow_push_in",
                    "caption_mode": "minimal",
                    "accent_light": "soft_warm",
                },
            },
            fits=[
                "directly carries memory and warmth",
                "uses reviewed material rather than decorative graphics",
                "low-density layout avoids presentation-slide feeling",
            ],
            risks=[
                "can look sparse if material refs are weak",
                "title copy must be authored or it will feel internal",
            ],
            base_score=5 + memory_score + slow_score + avoid_deck_score,
        ),
        _concept(
            "film_table_recall",
            "Film Table Recall",
            visual_primitives=[
                "dark_table_surface",
                "scattered_prints",
                "soft_edge_shadow",
                "warm_practical_light",
            ],
            motion_primitives=[
                "camera_slide_across_prints",
                "small_photo_lift",
                "soft_focus_to_title",
            ],
            typography={
                "position": "lower_center",
                "scale": "medium",
                "weight": "editorial_serif_or_plain_bold",
                "subtitle": "caption_like_memory_line",
                "avoid_copy": design_brief.get("copy_direction", {}).get("avoid_copy", []),
            },
            material_usage={
                "source": "reviewed_stills_as_prints",
                "priority": "faces_hands_shared_room",
                "max_refs": 5,
                "preserve_faces": True,
                "do_not_claim_material_truth": True,
            },
            prompt_parameters={
                "template_id": None,
                "presentation": {
                    "background_style": "photo_table",
                    "text_position": "bottom_center",
                    "text_scale": "medium",
                    "effect_strength": "subtle",
                    "safe_area": "title_safe",
                    "accent_color": "#f0c16a",
                    "text_color": "#fff8dc",
                    "theme": "warm_archive_table",
                },
                "effect_build_spec": {
                    "component": "MemoryPhotoWall",
                    "duration_sec": duration,
                    "story_function": "memory_table_recall_opening",
                    "pacing": "slow",
                    "density": "balanced",
                    "reveal_mode": "cascade",
                    "reveal_interval_sec": 0.75,
                    "hold_after_full_wall_sec": 0.6,
                    "camera_motion": "slow_lateral_slide",
                    "caption_mode": "none",
                    "accent_light": "soft_warm",
                },
            },
            fits=[
                "stronger authored metaphor than a normal wall",
                "naturally avoids corporate deck composition",
            ],
            risks=[
                "requires renderer support for table layout or it may collapse to wall",
                "can feel staged if source stills are low quality",
            ],
            base_score=4 + memory_score + avoid_deck_score,
        ),
        _concept(
            "warm_archive_opening",
            "Warm Archive Opening",
            visual_primitives=[
                "archive_card_edges",
                "date_or_course_trace",
                "warm_scan_light",
                "documentary_neutral_background",
            ],
            motion_primitives=[
                "archive_card_reveal",
                "slow_scan_light",
                "title_resolve_from_metadata",
            ],
            typography={
                "position": "top_left",
                "scale": "medium",
                "weight": "documentary_label",
                "subtitle": "short_context_line",
                "avoid_copy": design_brief.get("copy_direction", {}).get("avoid_copy", []),
            },
            material_usage={
                "source": "reviewed_material_refs_plus_course_context",
                "priority": "representative_moments_not_logos",
                "max_refs": 4,
                "preserve_faces": True,
                "do_not_claim_material_truth": True,
            },
            prompt_parameters={
                "template_id": None,
                "presentation": {
                    "background_style": "warm_archive",
                    "text_position": "top_left",
                    "text_scale": "medium",
                    "effect_strength": "subtle",
                    "safe_area": "title_safe",
                    "accent_color": "#e6b45f",
                    "text_color": "#fff8dc",
                    "theme": "documentary_warm_archive",
                },
                "effect_build_spec": {
                    "component": "MemoryPhotoWall",
                    "duration_sec": duration,
                    "story_function": "warm_archive_recap_opening",
                    "pacing": "slow",
                    "density": "low",
                    "reveal_mode": "one_by_one",
                    "reveal_interval_sec": 1.0,
                    "hold_after_full_wall_sec": 0.7,
                    "camera_motion": "slow_push_in",
                    "caption_mode": "minimal",
                    "accent_light": "scan_warm",
                },
            },
            fits=[
                "adds documentary context without becoming a slide",
                "works when material needs a little structure",
            ],
            risks=[
                "metadata labels can look administrative",
                "less emotionally direct than memory wall",
            ],
            base_score=4 + slow_score + avoid_deck_score,
        ),
    ]
    return {
        "artifact_role": "effect_concept_options",
        "version": 1,
        "source_brief_role": "effect_design_brief",
        "concepts": concepts,
        "selection_policy": {
            "prefer": [
                "strong_material_presence",
                "clear_emotional_metaphor",
                "renderer_supported_controls",
                "low_presentation_risk",
            ],
            "avoid": list(negative),
        },
    }


def select_effect_concept(
    design_brief: Mapping[str, Any],
    concept_options: Mapping[str, Any],
    *,
    preferred_concept_id: str | None = None,
) -> dict[str, Any]:
    """Select the highest-scoring concept and keep the reasoning visible."""
    if design_brief.get("artifact_role") != "effect_design_brief":
        raise ValueError("design_brief must have artifact_role effect_design_brief")
    if concept_options.get("artifact_role") != "effect_concept_options":
        raise ValueError("concept_options must have artifact_role effect_concept_options")
    concepts = [
        item for item in concept_options.get("concepts") or []
        if isinstance(item, Mapping)
    ]
    if not concepts:
        raise ValueError("concept_options.concepts must not be empty")
    by_id = {str(item.get("concept_id")): item for item in concepts}
    if preferred_concept_id:
        selected = by_id.get(preferred_concept_id)
        if selected is None:
            raise ValueError(f"preferred_concept_id not found: {preferred_concept_id}")
    else:
        selected = sorted(
            concepts,
            key=lambda item: (int(item.get("score") or 0), str(item.get("concept_id") or "")),
            reverse=True,
        )[0]
    risks = list(selected.get("risks") or [])
    return {
        "artifact_role": "effect_concept_selection",
        "version": 1,
        "decision": "selected",
        "selected_concept_id": selected["concept_id"],
        "selected_concept": _copy_json(selected),
        "score": int(selected.get("score") or 0),
        "reason": (
            "Selected because it best balances emotional warmth, reviewed material "
            "presence, restrained motion, and low presentation-deck risk."
        ),
        "risk_register": [
            {"risk": risk, "mitigation": _risk_mitigation(risk)}
            for risk in risks
        ],
        "downstream_requirements": [
            "copy must be authored and not route-internal",
            "effect_build_spec controls must reach remotion_prompt_pack",
            "render review must check presentation feel, material presence, and duration drift",
        ],
    }


def _risk_mitigation(risk: str) -> str:
    text = risk.lower()
    if "copy" in text or "title" in text:
        return "run effect_design_review and revise display_text/subtitle_text before delivery"
    if "material" in text or "refs" in text:
        return "prefer reviewed material refs and label placeholders explicitly"
    if "renderer" in text:
        return "fall back only with explicit degraded review note"
    return "review against selected concept rubric before handoff"


def build_effect_design_concept_chain(
    *,
    request: str,
    effect_role: str = "opening_title",
    duration_sec: float = 4.0,
    material_context: str = "reviewed_or_local_material_refs",
    preferred_concept_id: str | None = None,
) -> dict[str, Any]:
    brief = build_effect_design_brief(
        request=request,
        effect_role=effect_role,
        duration_sec=duration_sec,
        material_context=material_context,
    )
    options = build_effect_concept_options(brief)
    selection = select_effect_concept(
        brief,
        options,
        preferred_concept_id=preferred_concept_id,
    )
    return {
        "design_brief": brief,
        "concept_options": options,
        "concept_selection": selection,
    }


def write_effect_design_concept_chain(
    out_dir: str | Path,
    *,
    request: str,
    effect_role: str = "opening_title",
    duration_sec: float = 4.0,
    material_context: str = "reviewed_or_local_material_refs",
    preferred_concept_id: str | None = None,
) -> dict[str, Any]:
    out_dir = Path(out_dir)
    chain = build_effect_design_concept_chain(
        request=request,
        effect_role=effect_role,
        duration_sec=duration_sec,
        material_context=material_context,
        preferred_concept_id=preferred_concept_id,
    )
    artifacts = {
        "effect_design_brief": _write_json(out_dir / "effect_design_brief.json", chain["design_brief"]),
        "effect_concept_options": _write_json(out_dir / "effect_concept_options.json", chain["concept_options"]),
        "effect_concept_selection": _write_json(out_dir / "effect_concept_selection.json", chain["concept_selection"]),
    }
    return {**chain, "artifacts": artifacts}


def apply_effect_concept_to_effect(
    effect: Mapping[str, Any],
    concept_selection: Mapping[str, Any],
) -> dict[str, Any]:
    """Merge selected design concept controls into an effect intent item."""
    if concept_selection.get("artifact_role") != "effect_concept_selection":
        raise ValueError("concept_selection must have artifact_role effect_concept_selection")
    selected = concept_selection.get("selected_concept")
    if not isinstance(selected, Mapping):
        raise ValueError("concept_selection.selected_concept must be object")
    prompt = selected.get("prompt_parameters")
    if not isinstance(prompt, Mapping):
        raise ValueError("selected_concept.prompt_parameters must be object")
    enriched = _copy_json(effect)
    params = dict(enriched.get("prompt_parameters") or {})
    design_concept = {
        "concept_id": selected.get("concept_id"),
        "name": selected.get("name"),
        "typography_direction": selected.get("typography_direction") or {},
        "material_usage_rule": selected.get("material_usage_rule") or {},
        "review_rubric": selected.get("review_rubric") or [],
        "selection_reason": concept_selection.get("reason"),
        "recommended_prompt_parameters": _copy_json(prompt),
    }
    params["design_concept"] = design_concept
    params["negative_rules"] = _merge_lists(
        params.get("negative_rules"),
        [
            "avoid_presentation_deck",
            "avoid_generic_template",
            "avoid_route_internal_copy",
            "preserve_material_faces",
        ],
    )
    if isinstance(prompt.get("effect_build_spec"), Mapping):
        existing_spec = dict(params.get("effect_build_spec") or {})
        existing_component = existing_spec.get("component")
        concept_component = prompt["effect_build_spec"].get("component")
        if not existing_component or existing_component == concept_component:
            params["effect_build_spec"] = {
                **existing_spec,
                **_copy_json(prompt["effect_build_spec"]),
            }
            if isinstance(existing_spec.get("material_refs"), list) and existing_spec["material_refs"]:
                params["effect_build_spec"]["material_refs"] = existing_spec["material_refs"]
        else:
            params["design_build_spec_guidance"] = _copy_json(prompt["effect_build_spec"])
    for key, value in prompt.items():
        if key in {"effect_build_spec", "presentation"}:
            continue
        params[key] = _copy_json(value)
    enriched["prompt_parameters"] = params
    current_spec = params.get("effect_build_spec") if isinstance(params.get("effect_build_spec"), Mapping) else None
    current_component = current_spec.get("component") if isinstance(current_spec, Mapping) else None
    concept_spec = prompt.get("effect_build_spec") if isinstance(prompt.get("effect_build_spec"), Mapping) else None
    concept_component = concept_spec.get("component") if isinstance(concept_spec, Mapping) else None
    if (
        prompt.get("template_id") is not None
        and (not current_component or current_component == concept_component)
    ):
        enriched["template_id"] = prompt.get("template_id")
    elif "template_id" not in enriched:
        enriched["template_id"] = None
    presentation = dict(enriched.get("presentation") or {})
    if isinstance(prompt.get("presentation"), Mapping):
        presentation.update(_copy_json(prompt["presentation"]))
    enriched["presentation"] = presentation
    visual_language = _merge_lists(
        enriched.get("visual_language"),
        list(selected.get("visual_primitives") or []) + [str(selected.get("concept_id") or "")],
    )
    enriched["visual_language"] = visual_language
    motion = _merge_lists(params.get("motion_grammar"), selected.get("motion_primitives") or [])
    params["motion_grammar"] = motion
    return enriched


def _merge_lists(*values: Any) -> list[Any]:
    merged = []
    seen = set()
    for value in values:
        if value is None:
            continue
        items = value if isinstance(value, list) else [value]
        for item in items:
            key = json.dumps(item, ensure_ascii=False, sort_keys=True) if isinstance(item, (dict, list)) else str(item)
            if not key or key in seen:
                continue
            seen.add(key)
            merged.append(item)
    return merged


def build_effect_design_review(
    concept_selection: Mapping[str, Any],
    render_report: Mapping[str, Any],
) -> dict[str, Any]:
    """Review a rendered effect against the selected design concept."""
    if concept_selection.get("artifact_role") != "effect_concept_selection":
        raise ValueError("concept_selection must have artifact_role effect_concept_selection")
    selected = concept_selection.get("selected_concept") or {}
    if not isinstance(selected, Mapping):
        selected = {}
    rubric = list(selected.get("review_rubric") or [
        "emotional_fit",
        "presentation_avoidance",
        "copy_specificity",
        "material_presence",
        "pacing_fit",
    ])
    blocking = []
    warnings = []
    requested = render_report.get("requested_duration_sec")
    duration = render_report.get("duration_sec")
    try:
        requested_f = float(requested)
        duration_f = float(duration)
    except (TypeError, ValueError):
        requested_f = duration_f = None
    if requested_f and duration_f and abs(duration_f - requested_f) > 0.35:
        blocking.append({
            "issue_id": "duration_padding_or_drift",
            "reason": f"render duration {duration_f:.2f}s differs from requested {requested_f:.2f}s",
            "fix": "trim composition metadata or adjust effect duration before handoff",
        })
    copy_avoid = _avoid_copy_values(selected)
    visible_copy = " ".join([
        _clean_text(render_report.get("display_text")),
        _clean_text(render_report.get("subtitle_text")),
    ]).lower()
    if any(value and value.lower() in visible_copy for value in copy_avoid):
        blocking.append({
            "issue_id": "default_or_internal_copy",
            "reason": "visible title/subtitle uses route-internal or placeholder wording",
            "fix": "revise display_text/subtitle_text from the design brief copy direction",
        })
    if render_report.get("uses_real_material_refs") is False:
        warnings.append({
            "issue_id": "placeholder_material",
            "reason": "render uses placeholders instead of reviewed material refs",
            "fix": "label as probe or replace with reviewed material refs",
        })
    if render_report.get("playable_preview") is not True:
        blocking.append({
            "issue_id": "missing_playable_preview",
            "reason": "design review requires a playable preview or extracted contact sheet",
            "fix": "render a playable preview before design acceptance",
        })
    if not render_report.get("contact_sheet"):
        warnings.append({
            "issue_id": "missing_contact_sheet",
            "reason": "contact sheet is absent, making visual review harder",
            "fix": "extract representative frames from the preview",
        })

    checks = []
    for item in rubric:
        if item == "copy_specificity" and any(issue["issue_id"] == "default_or_internal_copy" for issue in blocking):
            status = "revise"
        elif item == "pacing_fit" and any(issue["issue_id"] == "duration_padding_or_drift" for issue in blocking):
            status = "revise"
        elif item == "material_presence" and render_report.get("uses_real_material_refs") is False:
            status = "warn"
        else:
            status = "pass"
        checks.append({"check": item, "status": status})
    status = "fail" if any(issue["issue_id"] == "missing_playable_preview" for issue in blocking) else (
        "revise" if blocking else "pass"
    )
    return {
        "artifact_role": "effect_design_review",
        "version": 1,
        "status": status,
        "selected_concept_id": concept_selection.get("selected_concept_id"),
        "checks": checks,
        "blocking_issues": blocking,
        "warnings": warnings,
        "evidence_refs": [
            ref for ref in [
                render_report.get("preview_file"),
                render_report.get("contact_sheet"),
            ] if ref
        ],
        "next_action": "handoff" if status == "pass" else "revise_contract_or_render",
    }


def _avoid_copy_values(selected: Mapping[str, Any]) -> list[str]:
    title_direction = selected.get("title_direction")
    if not isinstance(title_direction, Mapping):
        title_direction = selected.get("typography_direction")
    if not isinstance(title_direction, Mapping):
        return ["reviewed material memory wall", "opening", "untitled", "title"]
    return [
        _clean_text(item)
        for item in title_direction.get("avoid_copy") or []
        if _clean_text(item)
    ]


def write_effect_design_review(
    selection_path: str | Path,
    render_report_path: str | Path,
    out_path: str | Path,
) -> dict[str, Any]:
    selection = json.loads(Path(selection_path).read_text(encoding="utf-8-sig"))
    render_report = json.loads(Path(render_report_path).read_text(encoding="utf-8-sig"))
    review = build_effect_design_review(selection, render_report)
    _write_json(out_path, review)
    return review
