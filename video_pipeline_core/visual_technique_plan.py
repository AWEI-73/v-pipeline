"""Semantic-to-technique planner for bounded Remotion effects.

This is the upstream translation layer: natural style language becomes
visual primitives, motion primitives, render strategies, and controls. It does
not render, inspect material maps, or write final delivery artifacts.
"""

from __future__ import annotations

from typing import Any, Mapping


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _text(*values: Any) -> str:
    return " ".join(_clean(value).casefold() for value in values if _clean(value))


def _has_any(text: str, tokens: tuple[str, ...]) -> bool:
    return any(token.casefold() in text for token in tokens)


def _duration_sec(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        return number if number > 0 else None
    text = (
        _clean(value)
        .casefold()
        .replace("seconds", "")
        .replace("second", "")
        .replace("secs", "")
        .replace("sec", "")
        .replace("秒", "")
        .strip()
    )
    try:
        number = float(text)
    except ValueError:
        return None
    return number if number > 0 else None


def _detect_style_family(text: str) -> str | None:
    sakura = _has_any(text, ("櫻花", "樱花", "sakura", "cherry blossom", "petal", "petals"))
    japanese = _has_any(text, ("日式", "日系", "日本", "japanese", "anime", "和風", "和风"))
    if sakura and japanese:
        return "japanese_sakura"
    if sakura:
        return "sakura_poetic"
    if _has_any(text, ("熱血", "热血", "激動", "激动", "mv", "energetic", "impact", "beat", "flash")):
        return "energetic_mv"
    if _has_any(text, ("溫馨", "温馨", "warm", "nostalgic", "回憶", "回忆")):
        return "warm_documentary"
    if _has_any(text, ("寫實", "写实", "documentary", "realistic", "紀錄", "记录")):
        return "documentary_realistic"
    return None


def _questions(request: str, effect_role: str, style_family: str | None) -> list[str]:
    questions: list[str] = []
    if not style_family:
        questions.append("What visual style should drive the technique plan?")
    if not effect_role:
        questions.append("What effect role is this for: opening_title, transition, lower_third, montage_hit, or outro?")
    if not request:
        questions.append("What should the audience feel or notice first?")
    return questions


def _sakura_plan(duration: float | None, *, style_family: str) -> dict[str, Any]:
    controls: dict[str, Any] = {
        "petal_count": 140,
        "wind_strength": 0.35,
        "fall_speed": 0.28,
        "depth_layers": 4,
        "color_mood": "soft_pink_warm_white",
        "loopable": True,
    }
    if duration is not None:
        controls["duration_sec"] = duration
    return {
        "style_family": style_family,
        "render_strategy": [
            "remotion_react_particles",
            "remotion_canvas_particles",
            "remotion_three_particles",
        ],
        "visual_primitives": ["sakura", "petals", "soft_bloom", "negative_space_title"],
        "motion_primitives": ["drift", "fall", "parallax", "slow_reveal"],
        "controls": controls,
    }


def _energetic_mv_plan(duration: float | None) -> dict[str, Any]:
    controls: dict[str, Any] = {
        "type_scale": "large",
        "cut_intensity": 0.85,
        "flash_frequency": "beat_synced",
        "bar_thickness": "medium",
        "impact_frame_count": 3,
    }
    if duration is not None:
        controls["duration_sec"] = duration
    return {
        "style_family": "energetic_mv",
        "render_strategy": ["remotion_text_layers", "remotion_shape_layers", "remotion_timeline_cuts"],
        "visual_primitives": ["kinetic_typography", "flash_bars", "contrast_blocks", "speed_lines"],
        "motion_primitives": ["impact_cuts", "beat_pulse", "snap_zoom", "strobe_reveal"],
        "controls": controls,
    }


def _warm_documentary_plan(duration: float | None) -> dict[str, Any]:
    controls: dict[str, Any] = {
        "grain_amount": 0.18,
        "light_leak_strength": 0.28,
        "camera_motion": "gentle_drift",
        "color_mood": "warm_muted",
    }
    if duration is not None:
        controls["duration_sec"] = duration
    return {
        "style_family": "warm_documentary",
        "render_strategy": ["remotion_layers", "remotion_light_overlay"],
        "visual_primitives": ["soft_light", "film_grain", "warm_vignette"],
        "motion_primitives": ["gentle_drift", "slow_fade", "soft_push"],
        "controls": controls,
    }


def _documentary_plan(duration: float | None) -> dict[str, Any]:
    controls: dict[str, Any] = {
        "camera_motion": "static_or_slow_pan",
        "contrast": "natural",
        "texture": "minimal",
        "color_mood": "neutral",
    }
    if duration is not None:
        controls["duration_sec"] = duration
    return {
        "style_family": "documentary_realistic",
        "render_strategy": ["remotion_clean_text_layers", "ffmpeg_safe_overlay"],
        "visual_primitives": ["clean_title", "subtle_rule_line", "natural_grade"],
        "motion_primitives": ["hold", "slow_fade", "minimal_slide"],
        "controls": controls,
    }


def plan_visual_technique(brief: Mapping[str, Any]) -> dict[str, Any]:
    """Translate fuzzy semantic style into technique-level controls."""
    if not isinstance(brief, Mapping):
        raise ValueError("visual technique brief must be an object")

    request = _clean(brief.get("request") or brief.get("semantic_request") or brief.get("style_request"))
    effect_role = _clean(brief.get("effect_role"))
    material_state = brief.get("material_state")
    duration = _duration_sec(brief.get("duration_sec") or brief.get("duration"))
    search_text = _text(request, brief.get("style"), brief.get("tone"), effect_role)
    style_family = _detect_style_family(search_text)
    followup_questions = _questions(request, effect_role, style_family)

    if followup_questions:
        return {
            "artifact_role": "visual_technique_plan",
            "version": 1,
            "style_family": style_family or "needs_clarification",
            "effect_role": effect_role or None,
            "material_state": material_state,
            "render_strategy": [],
            "visual_primitives": [],
            "motion_primitives": [],
            "controls": {"duration_sec": duration} if duration is not None else {},
            "followup_questions": followup_questions,
            "handoff_to": "ask_followup",
        }

    if style_family in {"japanese_sakura", "sakura_poetic"}:
        technique = _sakura_plan(duration, style_family=style_family)
    elif style_family == "energetic_mv":
        technique = _energetic_mv_plan(duration)
    elif style_family == "warm_documentary":
        technique = _warm_documentary_plan(duration)
    elif style_family == "documentary_realistic":
        technique = _documentary_plan(duration)
    else:
        technique = {
            "style_family": "needs_clarification",
            "render_strategy": [],
            "visual_primitives": [],
            "motion_primitives": [],
            "controls": {"duration_sec": duration} if duration is not None else {},
        }

    return {
        "artifact_role": "visual_technique_plan",
        "version": 1,
        "effect_role": effect_role,
        "material_state": material_state,
        "followup_questions": [],
        "handoff_to": "remotion_prompt_parameters",
        **technique,
    }


def technique_to_effect(
    technique_plan: Mapping[str, Any],
    *,
    effect_id: str = "fx_visual_technique_01",
    display_text: str = "Opening",
    subtitle_text: str | None = None,
) -> dict[str, Any]:
    """Create a minimal effect intent item carrying the technique plan downstream."""
    if technique_plan.get("artifact_role") != "visual_technique_plan":
        raise ValueError("technique_plan must have artifact_role visual_technique_plan")
    if technique_plan.get("handoff_to") == "ask_followup":
        raise ValueError("technique_plan requires followup before effect conversion")

    effect_role = str(technique_plan.get("effect_role") or "opening_title")
    role = {
        "opening_title": "title_card",
        "transition": "chapter_transition",
        "lower_third": "lower_third",
        "montage_hit": "overlay",
        "outro": "title_card",
    }.get(effect_role, "title_card")
    style_family = str(technique_plan.get("style_family") or "")
    duration = float((technique_plan.get("controls") or {}).get("duration_sec") or 5.0)

    template_id = None
    if role == "title_card":
        template_id = "training_opening_title"
    elif role == "chapter_transition":
        template_id = "film_strip_transition_card"

    return {
        "effect_id": effect_id,
        "role": role,
        "template_id": template_id,
        "intent": f"{style_family} {effect_role}".strip(),
        "intensity": "medium",
        "target": {"beat_id": f"beat_{effect_id}", "segment_id": effect_id},
        "visual_language": list(technique_plan.get("visual_primitives") or []),
        "required_for_story": True,
        "must_preserve_proof": False,
        "allowed_backends": ["remotion_preview", "remotion_render"],
        "fallback": "ask for supported visual technique",
        "duration_sec": duration,
        "display_text": display_text,
        "subtitle_text": subtitle_text or "",
        "prompt_parameters": {
            "visual_technique_plan": dict(technique_plan),
            "motion_grammar": list(technique_plan.get("motion_primitives") or []),
        },
    }
