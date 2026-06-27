"""Semantic-to-technique planner for bounded Remotion effects.

This upstream translation layer converts natural style language into visual
primitives, motion primitives, render strategies, and controls. It does not
render, inspect material maps, or write final delivery artifacts.
"""

from __future__ import annotations

import json
from pathlib import Path
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
    if _has_any(text, ("lower third", "lower-third", "name title", "speaker label", "下標", "姓名職稱", "職稱")):
        return "clean_lower_third_label"
    if _has_any(text, ("photo wall", "memory wall", "照片牆", "照片墙", "一張一張", "一张一张", "collage")):
        return "memory_photo_wall_warm"
    if _has_any(text, ("page turn", "book flip", "flip book", "翻頁", "翻页")):
        return "page_turn_transition"
    if _has_any(text, ("title card", "particles", "particle title", "金色粒子", "金色顆粒", "獎項", "頒獎")):
        return "golden_particle_title_card"
    if _has_any(text, ("time cracks", "time fracture", "temporal shatter", "玻璃裂", "時間像玻璃", "時間裂", "倒轉", "倒退")):
        return "time_fracture_reverse"
    if _has_any(text, ("sprout", "seedling", "organic growth", "growth timelapse", "發芽", "成長", "幼苗")):
        return "organic_growth_timelapse"
    if _has_any(text, ("portal", "open sesame", "secret world", "door reveal", "芝麻開門", "秘密世界")):
        return "portal_reveal_opening"
    if _has_any(text, ("water reflection", "mirror reveal", "reflection rises", "水面倒影", "自我反思")):
        return "water_reflection_self_reveal"
    if _has_any(text, ("heartbeat", "pulse freeze", "心跳", "定格")):
        return "heartbeat_pulse_freeze"
    if _has_any(text, ("lightning", "electric", "thunder", "arc strike", "electric_lightning_energy")):
        return "electric_lightning_energy"
    if _has_any(text, ("earthquake", "crack", "cracked", "impact crack", "earthquake_crack_impact")):
        return "earthquake_crack_impact"
    if _has_any(text, ("mother's day", "mothers day", "heart", "hearts", "gratitude", "mothers_day_heart_stage")):
        return "mothers_day_heart_stage"
    sakura = _has_any(text, ("櫻花", "樱花", "sakura", "cherry blossom", "petal", "petals"))
    japanese = _has_any(text, ("日式", "日系", "日本", "japanese", "anime", "和風", "和风"))
    if sakura and japanese:
        return "japanese_sakura"
    if sakura:
        return "sakura_poetic"
    legacy_fire = _has_any(text, ("薪火", "精神", "傳承", "传承", "下一個階段", "下一个阶段", "結尾", "结尾", "closing", "legacy"))
    warm_fire = _has_any(text, ("火光", "火星", "餘溫", "余温", "ember", "embers", "afterglow", "warm fire"))
    group_photo = _has_any(text, ("合照", "group photo", "class photo"))
    if (legacy_fire and warm_fire) or (legacy_fire and group_photo):
        return "warm_legacy_fire"
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
        questions.append("What effect role is this for: opening_title, transition, lower_third, montage_hit, closing_title, or outro?")
    if not request:
        questions.append("What should the audience feel or notice first?")
    return questions


def _candidate_review_questions(style_family: str, effect_role: str) -> list[str]:
    role_questions = {
        "memory_photo_wall_warm": [
            "Which photos or material-map refs should enter the wall, and how many should be visible?",
            "Should the reveal feel chronological, emotional, or grouped by people/event?",
            "Are there faces, privacy, or crop-safe areas that must be protected?",
        ],
        "clean_lower_third_label": [
            "What exact name/title text should appear?",
            "Should the label sit lower-left, lower-right, or follow the speaker framing?",
            "How long should the lower third stay on screen?",
        ],
        "time_fracture_reverse": [
            "What are the before/after shots or states around this transition?",
            "Should the time reversal feel subtle, mysterious, or high-impact?",
            "Should cracks appear over the whole frame or only around the subject/text?",
        ],
        "page_turn_transition": [
            "What shot or chapter does the page turn reveal?",
            "Should the direction feel like a book page, notebook, or formal document?",
        ],
        "golden_particle_title_card": [
            "What title text and subtitle should the ceremony card display?",
            "Should particles feel restrained, celebratory, or award-like?",
        ],
    }
    questions = list(role_questions.get(style_family, []))
    if not questions:
        questions = [
            "Which candidate option should be used: restrained, balanced, or expressive?",
            "Should any visual primitive, motion primitive, or control be removed before worker handoff?",
            "Should this candidate be accepted for a short worker preview?",
        ]
    if effect_role == "transition" and not any("before" in q.lower() or "after" in q.lower() for q in questions):
        questions.append("What are the source and target shots for this transition?")
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


def _candidate_parameter_plan(style_family: str, duration: float | None) -> dict[str, Any]:
    """Return visible candidate controls without hard-locking a template.

    These are sample parameter surfaces for review. They should help the agent
    translate fuzzy style words into Remotion-capable language, but the route
    must still show them to the user/reviewer before treating them as hardened.
    """

    library: dict[str, dict[str, Any]] = {
        "electric_lightning_energy": {
            "story_function": "high_impact_opening",
            "tone": "powerful_sharp_controlled",
            "render_strategy": ["remotion_svg_arcs", "remotion_glow_layers", "remotion_text_layers"],
            "visual_primitives": [
                "branching_lightning_arcs",
                "electric_blue_glow",
                "dark_storm_gradient",
                "brief_white_flash",
                "chromatic_edge",
            ],
            "motion_primitives": [
                "arc_strike",
                "micro_jitter",
                "flash_reveal",
                "snap_scale",
                "afterglow_decay",
            ],
            "controls": {
                "strike_count": 4,
                "flash_intensity": "high",
                "jitter_strength": "medium",
                "arc_branching": "high",
                "title_reveal_frame": 54,
                "strobe_safety": "no_full_white_hold",
            },
            "negative_rules": [
                "no horror tone",
                "no unreadable strobe",
                "no long full-white frames",
            ],
        },
        "earthquake_crack_impact": {
            "story_function": "challenge_or_disruption_opening",
            "tone": "dramatic_grounded_serious",
            "render_strategy": ["remotion_svg_cracks", "remotion_particle_dust", "remotion_camera_shake"],
            "visual_primitives": [
                "surface_crack_lines",
                "dust_burst",
                "dark_concrete_texture",
                "impact_shadow",
                "warm_sparks_low",
            ],
            "motion_primitives": [
                "impact_shake",
                "crack_expand",
                "dust_rise",
                "title_settle",
                "low_frequency_pulse",
            ],
            "controls": {
                "crack_count": 5,
                "shake_strength": "medium",
                "shake_decay": "fast",
                "dust_density": "low",
                "texture_contrast": "medium",
                "injury_risk_visuals": "none",
            },
            "negative_rules": [
                "no injury implication",
                "no collapsing building",
                "no gore",
                "no comedy wobble",
            ],
        },
        "mothers_day_heart_stage": {
            "story_function": "gratitude_family_warmth_opening",
            "tone": "warm_gentle_grateful",
            "render_strategy": ["remotion_bokeh_particles", "remotion_ribbon_shapes", "remotion_text_layers"],
            "visual_primitives": [
                "soft_heart_bokeh",
                "pink_gold_gradient",
                "ribbon_curve",
                "flower_petal_drift",
                "warm_light_orbs",
            ],
            "motion_primitives": [
                "heart_float",
                "petal_drift",
                "soft_scale_in",
                "ribbon_sweep",
                "gentle_breathing_glow",
            ],
            "controls": {
                "heart_count": 16,
                "petal_count": 24,
                "glow_strength": "medium",
                "background_density": "clean",
                "color_mood": "pink_gold_soft",
                "title_readability": "high",
            },
            "negative_rules": [
                "no sticker overload",
                "no harsh red",
                "no wedding-only mood",
                "no title clutter",
            ],
        },
        "memory_photo_wall_warm": {
            "story_function": "memory_transition_or_emotional_recap",
            "tone": "warm_slow_human",
            "render_strategy": ["remotion_photo_layers", "remotion_grid_layout", "remotion_soft_light_overlay"],
            "visual_primitives": [
                "photo_grid",
                "soft_memory_plate",
                "warm_vignette",
                "caption_space",
                "subtle_paper_shadow",
            ],
            "motion_primitives": [
                "one_by_one_reveal",
                "slow_push_in",
                "gentle_crossfade",
                "staggered_scale",
                "memory_hold",
            ],
            "controls": {
                "photo_count": "ask_user_or_material_map",
                "reveal_mode": "one_by_one",
                "pacing": "slow",
                "hold_per_photo_sec": 1.2,
                "background_density": "clean",
                "crop_policy": "preserve_faces",
            },
            "negative_rules": [
                "do not crop faces aggressively",
                "no fast slideshow",
                "no cluttered collage",
            ],
        },
        "clean_lower_third_label": {
            "story_function": "speaker_identification",
            "tone": "clean_documentary",
            "render_strategy": ["remotion_text_layers", "remotion_shape_layers"],
            "visual_primitives": [
                "name_title_plate",
                "thin_rule_line",
                "soft_background_chip",
                "high_readability_text",
            ],
            "motion_primitives": [
                "slide_in",
                "short_fade",
                "hold",
                "slide_out",
            ],
            "controls": {
                "safe_area": "lower_left_or_lower_right",
                "duration_sec": 5,
                "font_weight": "medium",
                "background_opacity": 0.72,
                "max_lines": 2,
            },
            "negative_rules": [
                "no decorative overload",
                "do not cover speaker face",
                "no tiny unreadable text",
            ],
        },
        "page_turn_transition": {
            "story_function": "chapter_transition",
            "tone": "storybook_or_documentary_chapter",
            "render_strategy": ["remotion_layer_mask", "remotion_page_warp"],
            "visual_primitives": ["page_edge", "paper_shadow", "next_scene_reveal"],
            "motion_primitives": ["page_curl", "wipe_reveal", "soft_settle"],
            "controls": {
                "turn_direction": "right_to_left",
                "duration_sec": 1.2,
                "paper_texture": "subtle",
                "shadow_strength": "low",
            },
            "negative_rules": ["no cartoon bounce unless requested", "no unreadable mid-turn text"],
        },
        "golden_particle_title_card": {
            "story_function": "ceremony_title_or_award_emphasis",
            "tone": "ceremonial_warm",
            "render_strategy": ["remotion_particle_overlay", "remotion_text_layers"],
            "visual_primitives": ["gold_particles", "soft_spotlight", "title_plate"],
            "motion_primitives": ["particle_drift", "title_fade_in", "subtle_glow_pulse"],
            "controls": {
                "particle_density": "medium",
                "glow_strength": "soft",
                "title_safe_area": "center",
                "duration_sec": 4,
            },
            "negative_rules": ["no luxury-ad excess", "no title clutter"],
        },
        "time_fracture_reverse": {
            "story_function": "time_shift_or_memory_turning_point",
            "tone": "cinematic_mysterious_controlled",
            "render_strategy": ["remotion_svg_cracks", "remotion_reverse_timing_layers", "remotion_glass_shards"],
            "visual_primitives": [
                "glass_crack",
                "time_shard",
                "frozen_frame_plate",
                "reverse_echo",
            ],
            "motion_primitives": [
                "crack_spread",
                "reverse_motion",
                "shard_reassemble",
                "snap_back",
            ],
            "controls": {
                "crack_timing": "midpoint",
                "reverse_window_sec": 1.5,
                "shard_count": 12,
                "impact_strength": "medium",
                "before_after_refs": "ask_user_or_timeline",
            },
            "negative_rules": [
                "no horror glass injury",
                "no full-screen unreadable chaos",
                "preserve transition target clarity",
            ],
        },
        "organic_growth_timelapse": {
            "story_function": "growth_or_maturation_metaphor",
            "tone": "hopeful_natural",
            "render_strategy": ["remotion_shape_growth", "remotion_particle_overlay"],
            "visual_primitives": ["sprout", "leaf_unfurl", "morning_light"],
            "motion_primitives": ["grow", "unfurl", "slow_reveal"],
            "controls": {"growth_pacing": "slow_to_medium", "duration_sec": 6},
            "negative_rules": ["no childish cartoon unless requested"],
        },
        "portal_reveal_opening": {
            "story_function": "hidden_world_reveal",
            "tone": "wonder_impact",
            "render_strategy": ["remotion_mask_reveal", "remotion_light_bloom"],
            "visual_primitives": ["threshold_frame", "door_iris", "reveal_bloom"],
            "motion_primitives": ["open", "expand", "shock_bloom"],
            "controls": {"reveal_target": "ask_user", "duration_sec": 4},
            "negative_rules": ["no horror portal unless requested"],
        },
        "water_reflection_self_reveal": {
            "story_function": "self_reflection_reveal",
            "tone": "quiet_introspective",
            "render_strategy": ["remotion_displacement_ripple", "remotion_reflection_layer"],
            "visual_primitives": ["water_reflection", "ripple", "mirror_surface"],
            "motion_primitives": ["ripple_reveal", "reflection_rise", "soft_fade"],
            "controls": {"ripple_strength": "low", "duration_sec": 5},
            "negative_rules": ["no horror mirror reveal"],
        },
        "heartbeat_pulse_freeze": {
            "story_function": "emphasis_or_emotional_hit",
            "tone": "tense_then_still",
            "render_strategy": ["remotion_scale_pulse", "remotion_freeze_frame"],
            "visual_primitives": ["pulse_vignette", "freeze_plate", "subtle_waveform"],
            "motion_primitives": ["heartbeat_pulse", "shake_decay", "freeze"],
            "controls": {"bpm": "ask_audio_or_user", "pulse_amplitude": "medium", "freeze_frame_target": "ask_user"},
            "negative_rules": ["avoid medical alarm style unless requested"],
        },
    }
    base = dict(library[style_family])
    controls = dict(base["controls"])
    if duration is not None:
        controls["duration_sec"] = duration
    base["controls"] = controls
    base["style_family"] = style_family
    base["parameter_status"] = "candidate_parameters"
    base["requires_human_review"] = True
    base["template_policy"] = "templates_are_carriers_not_creative_locks"
    base["review_prompts"] = [
        "Does this style family match the intended emotion?",
        "Which controls should be softened, intensified, slowed, or removed?",
        "Should this remain a candidate or be hardened after visual evidence?",
    ]
    base["candidate_options"] = [
        {
            "option_id": "restrained",
            "label": "restrained",
            "effect_on_controls": {
                "intensity": "lower",
                "density": "lower",
                "pacing": "slower",
            },
        },
        {
            "option_id": "balanced",
            "label": "balanced",
            "effect_on_controls": {
                "intensity": "medium",
                "density": "medium",
                "pacing": "medium",
            },
        },
        {
            "option_id": "expressive",
            "label": "expressive",
            "effect_on_controls": {
                "intensity": "higher",
                "density": "higher",
                "pacing": "faster",
            },
        },
    ]
    return base


def _warm_legacy_fire_plan(duration: float | None) -> dict[str, Any]:
    controls: dict[str, Any] = {
        "danger_level": "none",
        "fire_realism": "symbolic",
        "ember_density": "low",
        "particle_density": "low",
        "glow_strength": "soft",
        "flicker_speed": "very_slow",
        "pacing": "very_slow",
        "contrast": "soft_dark_warm",
        "color_mood": "warm_amber_gold",
        "text_reveal_speed": "slow",
        "ending_hold_sec": 2,
        "photo_blur": "none_or_very_low",
        "photo_dim_strength": "medium",
        "subtitle_readability": "high",
        "title_safe_area": "center_lower_third",
    }
    if duration is not None:
        controls["duration_sec"] = duration
    return {
        "style_family": "warm_legacy_fire",
        "story_function": "closing_emotional_legacy",
        "placement": "ending",
        "tone": "moving_warm",
        "message_intent": "carry_training_spirit_to_next_stage",
        "display_text": "走向下一個階段",
        "subtitle_text": "把這段日子的精神，帶到更遠的地方",
        "render_strategy": ["remotion_photo_plate", "remotion_particle_overlay", "remotion_text_layers"],
        "material_use": {
            "background_source": "group_photo",
            "background_treatment": "soft_dimmed_memory_plate",
            "background_opacity": "low_to_medium",
            "background_motion": "very_slow_push_in",
            "preserve_people_visibility": True,
        },
        "visual_primitives": [
            "soft_ember_particles",
            "afterglow_warm_light",
            "gentle_vignette",
            "memory_light_leak",
            "quiet_title_reveal",
            "dimmed_group_photo_background",
        ],
        "motion_primitives": [
            "slow_rise",
            "gentle_drift",
            "breathing_flicker",
            "long_fade_in",
            "long_fade_out",
            "very_slow_push_in",
        ],
        "controls": controls,
        "negative_rules": [
            "no aggressive flames",
            "no explosion",
            "no disaster feeling",
            "no horror",
            "no harsh red fire",
            "no heavy smoke",
            "no fast wipe",
            "no impact cut",
            "no slogan-like text",
            "do not obscure faces in group photo",
        ],
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
    search_text = _text(request, brief.get("style"), brief.get("tone"), effect_role, material_state)
    style_family = _detect_style_family(search_text)
    confirmed_style = bool(
        brief.get("confirmed_style_family")
        or brief.get("accept_candidate_parameters")
        or brief.get("user_confirmed")
    )
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

    if style_family in {
        "electric_lightning_energy",
        "earthquake_crack_impact",
        "mothers_day_heart_stage",
        "memory_photo_wall_warm",
        "clean_lower_third_label",
        "page_turn_transition",
        "golden_particle_title_card",
        "time_fracture_reverse",
        "organic_growth_timelapse",
        "portal_reveal_opening",
        "water_reflection_self_reveal",
        "heartbeat_pulse_freeze",
    }:
        technique = _candidate_parameter_plan(style_family, duration)
    elif style_family in {"japanese_sakura", "sakura_poetic"}:
        technique = _sakura_plan(duration, style_family=style_family)
    elif style_family == "warm_legacy_fire":
        technique = _warm_legacy_fire_plan(duration)
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

    if confirmed_style and technique.get("parameter_status") == "candidate_parameters":
        options = [
            item for item in technique.get("candidate_options") or []
            if isinstance(item, Mapping)
        ]
        selected = next(
            (item for item in options if item.get("option_id") == "balanced"),
            options[0] if options else None,
        )
        technique["parameter_status"] = "reviewed_candidate_parameters"
        technique["selected_candidate_option"] = selected
        technique["review_decision"] = {
            "decision": "accept",
            "reviewer": "cli_confirmed",
            "selected_option": selected.get("option_id") if selected else None,
            "reason": "Confirmed by operator flag; parameters remain visible for downstream review.",
            "control_overrides": {},
        }

    return {
        "artifact_role": "visual_technique_plan",
        "version": 1,
        "effect_role": effect_role,
        "material_state": material_state,
        "followup_questions": (
            []
            if confirmed_style or technique.get("parameter_status") != "candidate_parameters"
            else _candidate_review_questions(str(technique.get("style_family") or style_family), effect_role)
        ),
        "handoff_to": (
            "remotion_prompt_parameters"
            if confirmed_style or technique.get("parameter_status") != "candidate_parameters"
            else "review_candidate_parameters"
        ),
        **technique,
    }


def technique_to_effect(
    technique_plan: Mapping[str, Any],
    *,
    effect_id: str = "fx_visual_technique_01",
    display_text: str | None = "Opening",
    subtitle_text: str | None = None,
) -> dict[str, Any]:
    """Create a minimal effect intent item carrying the technique plan downstream."""
    if technique_plan.get("artifact_role") != "visual_technique_plan":
        raise ValueError("technique_plan must have artifact_role visual_technique_plan")
    if technique_plan.get("handoff_to") in {"ask_followup", "review_candidate_parameters"}:
        raise ValueError("technique_plan requires followup before effect conversion")

    effect_role = str(technique_plan.get("effect_role") or "opening_title")
    role = {
        "opening_title": "title_card",
        "closing_title": "title_card",
        "transition": "chapter_transition",
        "lower_third": "lower_third",
        "montage_hit": "overlay",
        "outro": "title_card",
    }.get(effect_role, "title_card")
    style_family = str(technique_plan.get("style_family") or "")
    duration = float((technique_plan.get("controls") or {}).get("duration_sec") or 5.0)

    template_id = None
    if role == "title_card":
        template_id = "training_closing_title" if effect_role == "closing_title" else "training_opening_title"
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
        "display_text": display_text or str(technique_plan.get("display_text") or "Opening"),
        "subtitle_text": subtitle_text if subtitle_text is not None else str(technique_plan.get("subtitle_text") or ""),
        "prompt_parameters": {
            "visual_technique_plan": dict(technique_plan),
            "motion_grammar": list(technique_plan.get("motion_primitives") or []),
            "parameter_status": technique_plan.get("parameter_status") or "reviewable_parameters",
            "requires_human_review": bool(technique_plan.get("requires_human_review", True)),
            "template_policy": technique_plan.get("template_policy") or "templates_are_carriers_not_creative_locks",
        },
    }


def apply_visual_technique_review(
    technique_plan: Mapping[str, Any],
    review: Mapping[str, Any],
) -> dict[str, Any]:
    """Apply a user/reviewer decision to a candidate visual technique plan.

    The review promotes candidate parameters into a confirmed handoff artifact
    without running a backend. It keeps the selected option and overrides visible
    so downstream reviewers can audit what changed.
    """

    if technique_plan.get("artifact_role") != "visual_technique_plan":
        raise ValueError("technique_plan must have artifact_role visual_technique_plan")
    if not isinstance(review, Mapping):
        raise ValueError("visual technique review must be an object")
    if review.get("artifact_role") not in {None, "visual_technique_review"}:
        raise ValueError("review artifact_role must be visual_technique_review")
    decision = str(review.get("decision") or "").strip().lower()
    if decision not in {"accept", "revise"}:
        raise ValueError("visual technique review decision must be accept or revise")
    option_id = str(review.get("selected_option") or review.get("option_id") or "").strip()
    options = {
        str(item.get("option_id") or ""): item
        for item in technique_plan.get("candidate_options") or []
        if isinstance(item, Mapping)
    }
    if option_id and option_id not in options:
        raise ValueError(f"selected_option is not in candidate_options: {option_id}")

    confirmed = json.loads(json.dumps(technique_plan, ensure_ascii=False))
    controls = dict(confirmed.get("controls") or {})
    overrides = review.get("control_overrides") or {}
    if not isinstance(overrides, Mapping):
        raise ValueError("control_overrides must be an object when present")
    controls.update(json.loads(json.dumps(overrides, ensure_ascii=False)))
    confirmed["controls"] = controls

    for field, remove_field in (
        ("visual_primitives", "remove_visual_primitives"),
        ("motion_primitives", "remove_motion_primitives"),
        ("negative_rules", "remove_negative_rules"),
    ):
        current = [str(item) for item in confirmed.get(field) or []]
        removals = {str(item) for item in review.get(remove_field) or []}
        confirmed[field] = [item for item in current if item not in removals]

    for field, add_field in (
        ("visual_primitives", "add_visual_primitives"),
        ("motion_primitives", "add_motion_primitives"),
        ("negative_rules", "add_negative_rules"),
    ):
        current = list(confirmed.get(field) or [])
        for item in review.get(add_field) or []:
            value = str(item)
            if value and value not in current:
                current.append(value)
        confirmed[field] = current

    confirmed["handoff_to"] = "remotion_prompt_parameters"
    confirmed["followup_questions"] = []
    confirmed["parameter_status"] = (
        "reviewed_candidate_parameters" if decision == "accept" else "revised_candidate_parameters"
    )
    confirmed["requires_human_review"] = True
    confirmed["review_decision"] = {
        "decision": decision,
        "reviewer": str(review.get("reviewer") or "unknown"),
        "selected_option": option_id or None,
        "reason": str(review.get("reason") or "").strip(),
        "control_overrides": dict(overrides),
    }
    if option_id:
        confirmed["selected_candidate_option"] = options[option_id]
    return confirmed


def apply_visual_technique_review_file(
    plan_path: str | Path,
    review_path: str | Path,
    out_path: str | Path,
) -> dict[str, Any]:
    with Path(plan_path).open(encoding="utf-8-sig") as f:
        plan = json.load(f)
    with Path(review_path).open(encoding="utf-8-sig") as f:
        review = json.load(f)
    result = apply_visual_technique_review(plan, review)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result
