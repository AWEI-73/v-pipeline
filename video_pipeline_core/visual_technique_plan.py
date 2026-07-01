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
    if _has_any(text, ("ink spread", "ink bloom", "ink wash", "sumi ink", "rice paper reveal")):
        return "ink_spread_reveal"
    if _has_any(text, ("prism glass", "glass refraction", "prismatic", "crystalline split", "spectral split")):
        return "prism_glass_refraction"
    if _has_any(text, ("黑客", "駭客", "資料流", "數據流", "終端機", "terminal", "data stream", "matrix reveal")):
        return "terminal_data_reveal"
    if _has_any(text, ("膠片燒灼", "膠卷燒", "film burn", "burn-through", "light leak burn", "燒灼轉場")):
        return "vintage_film_burn_transition"
    if _has_any(text, (
        "故事轉mv",
        "故事轉 mv",
        "故事轉到",
        "故事到mv",
        "故事到 mv",
        "轉到後半段 mv",
        "story to mv",
        "story-to-mv",
    )):
        return "story_to_mv_transition"
    if _has_any(text, ("閃電", "雷電", "電光", "動感閃電", "雷擊", "電弧")):
        return "electric_lightning_energy"
    if _has_any(text, ("地震", "裂動", "震裂", "衝擊裂", "地面裂痕")):
        return "earthquake_crack_impact"
    if _has_any(text, ("母親節", "愛心", "心形", "感謝媽媽", "溫柔感謝")):
        return "mothers_day_heart_stage"
    japanese_clear = _has_any(text, ("日式", "日本風", "和風", "日系"))
    cute_storybook_clear = _has_any(text, ("可愛", "紙本", "繪本", "故事書", "柔和", "手繪"))
    if japanese_clear and cute_storybook_clear:
        return "japanese_soft_storybook"
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
        "japanese_soft_storybook": [
            "Should the Japanese storybook look lean cute, ceremonial, nostalgic, or dreamy?",
            "Should paper texture, ink lines, character plates, or soft particles be most visible?",
            "What title text, scene image, or material ref should the opening reveal?",
        ],
        "story_to_mv_transition": [
            "What is the exact story section before the transition and the MV/montage section after it?",
            "Where should the impact moment land inside the transition?",
            "Should the acceleration feel subtle, balanced, or aggressive?",
        ],
        "terminal_data_reveal": [
            "Should the data stream feel clean corporate-tech, cyber-thriller, or investigative?",
            "What exact title text should the terminal stream assemble?",
            "Should glyphs be mostly readable code, abstract symbols, or mixed bilingual characters?",
        ],
        "vintage_film_burn_transition": [
            "Should the burn start from the left edge, right edge, center, or random film gate edge?",
            "What are the source memory shot and target truth shot?",
            "Should the burn feel subtle archival, dramatic reveal, or damaged-footage unstable?",
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
        "japanese_soft_storybook": {
            "story_function": "soft_story_opening_or_transition",
            "tone": "gentle_cute_storybook",
            "render_strategy": [
                "remotion_layered_paper",
                "remotion_text_layers",
                "remotion_soft_particle_overlay",
            ],
            "visual_primitives": [
                "storybook_paper_texture",
                "soft_character_plate",
                "rounded_ink_lines",
                "pastel_wash_background",
                "quiet_title_space",
            ],
            "motion_primitives": [
                "gentle_parallax",
                "soft_scale_in",
                "slow_page_breath",
                "delayed_title_fade",
            ],
            "controls": {
                "palette": "soft_pastel_warm",
                "line_style": "rounded_soft_lines",
                "paper_texture": "subtle",
                "motion_intensity": "low",
                "background_density": "clean",
                "title_readability": "high",
            },
            "negative_rules": [
                "no horror anime tone",
                "no over-saturated neon",
                "no cluttered sticker collage",
                "do not force sakura unless requested",
            ],
        },
        "story_to_mv_transition": {
            "story_function": "story_to_montage_energy_shift",
            "tone": "energy_shift_controlled",
            "render_strategy": ["remotion_timeline_cuts", "remotion_text_layers", "remotion_shape_layers"],
            "visual_primitives": [
                "film_rail",
                "thumbnail_strip",
                "impact_flash",
                "phase_labels",
                "hard_cut_bars",
            ],
            "motion_primitives": [
                "thumbnail_acceleration",
                "flash_wipe",
                "beat_pulse",
                "snap_zoom",
            ],
            "controls": {
                "section_from": "story",
                "section_to": "montage",
                "pacing_shift": "slow_to_fast",
                "impact_moment_sec": 2.2,
                "thumbnail_acceleration": "medium",
                "phase_labels": ["STORY", "MONTAGE"],
            },
            "negative_rules": [
                "do not behave like a static chapter card",
                "do not hide reviewed source imagery",
                "no unreadable phase labels",
            ],
        },
        "ink_spread_reveal": {
            "story_function": "organic_title_reveal",
            "tone": "elegant_organic_mysterious",
            "render_strategy": [
                "remotion_mask_reveal",
                "remotion_noise_displacement",
                "remotion_texture_overlay",
                "remotion_text_layers",
            ],
            "visual_primitives": [
                "ink_bloom_mask",
                "paper_fiber_texture",
                "soft_edge_bleed",
                "negative_space_title",
                "monochrome_wash",
            ],
            "motion_primitives": [
                "fluid_spread",
                "edge_feather_growth",
                "title_reveal_through_mask",
                "slow_absorb",
            ],
            "controls": {
                "ink_spread_radius": "medium",
                "edge_feather_px": 42,
                "noise_scale": 0.72,
                "paper_texture_strength": "medium",
                "title_reveal_sec": 3.2,
                "palette": "black_ink_on_warm_paper",
                "readability_guard": "title_clear_after_ink_settles",
            },
            "negative_rules": [
                "no blood-like red liquid",
                "no dirty spill feeling",
                "no unreadable final title",
                "do not over-darken the frame",
            ],
        },
        "prism_glass_refraction": {
            "story_function": "crystalline_transition",
            "tone": "clean_cinematic_luminous",
            "render_strategy": [
                "remotion_refraction_layers",
                "remotion_clip_path_planes",
                "remotion_chromatic_split",
                "remotion_mask_reveal",
            ],
            "visual_primitives": [
                "glass_prism_planes",
                "rgb_spectral_split",
                "transparent_shard_edges",
                "luminous_refraction_streak",
                "next_scene_glimpse",
            ],
            "motion_primitives": [
                "refraction_sweep",
                "plane_slide",
                "chromatic_settle",
                "wipe_reveal",
            ],
            "controls": {
                "prism_plane_count": 5,
                "chromatic_aberration_px": 14,
                "refraction_strength": "medium",
                "plane_angle_deg": 18,
                "transition_duration_sec": 2.4,
                "highlight_strength": "soft",
                "readability_guard": "avoid_text_under_strong_refraction",
            },
            "negative_rules": [
                "no broken-glass injury implication",
                "no chaotic shard explosion",
                "do not hide the transition target",
                "avoid excessive rainbow clutter",
            ],
        },
        "terminal_data_reveal": {
            "story_function": "cyber_information_reveal",
            "tone": "tech_tense_readable",
            "render_strategy": [
                "remotion_text_layers",
                "remotion_canvas_glyph_stream",
                "remotion_scanline_overlay",
                "remotion_mask_reveal",
            ],
            "visual_primitives": [
                "glyph_stream_layer",
                "terminal_grid",
                "scanline_overlay",
                "monospace_title_plate",
                "cursor_blink",
                "green_or_cyan_data_glow",
            ],
            "motion_primitives": [
                "vertical_data_rain",
                "horizontal_terminal_sweep",
                "title_assembly",
                "cursor_lock",
                "glitch_decay",
            ],
            "controls": {
                "glyph_speed": "medium_fast",
                "glyph_density": "medium",
                "scanline_opacity": 0.22,
                "title_assembly_sec": 3.6,
                "readability_guard": "title_clear_after_reveal",
                "palette": "cyan_green_on_dark",
                "glitch_strength": "low_to_medium",
            },
            "negative_rules": [
                "no unreadable final title",
                "no excessive strobe",
                "no horror hacking cliché overload",
                "do not use random lightning arcs as the primary metaphor",
            ],
        },
        "vintage_film_burn_transition": {
            "story_function": "memory_to_truth_transition",
            "tone": "nostalgic_uneasy_not_horror",
            "render_strategy": [
                "remotion_mask_reveal",
                "remotion_light_leak_overlay",
                "remotion_film_grain",
                "remotion_gate_weave",
            ],
            "visual_primitives": [
                "burn_mask_edge",
                "amber_light_leak",
                "film_grain",
                "gate_weave",
                "dust_scratches",
                "exposed_frame_border",
            ],
            "motion_primitives": [
                "burn_through_wipe",
                "edge_flicker",
                "gate_weave_drift",
                "slow_exposure_bloom",
                "memory_to_truth_reveal",
            ],
            "controls": {
                "burn_edge_width": "medium",
                "burn_direction": "edge_to_center",
                "light_leak_strength": "medium",
                "grain_amount": 0.24,
                "gate_weave_strength": "low",
                "transition_duration_sec": 3.0,
                "horror_guard": "no_horror_no_gore",
            },
            "negative_rules": [
                "no gore or injury implication",
                "no horror jump scare",
                "do not fully obscure the target shot",
                "avoid modern neon glitch language",
            ],
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


def _semantic_slots(
    *,
    style_family: str,
    effect_role: str,
    request: str,
    technique: Mapping[str, Any],
    duration: float | None,
) -> dict[str, Any]:
    controls = technique.get("controls") if isinstance(technique.get("controls"), Mapping) else {}
    slots: dict[str, Any] = {
        "effect_role": effect_role,
        "story_function": technique.get("story_function") or style_family,
        "tone": technique.get("tone") or "neutral",
        "duration_sec": duration or controls.get("duration_sec"),
        "pacing": controls.get("pacing") or ("slow" if "slow" in technique.get("motion_primitives", []) else "medium"),
        "density": controls.get("density") or controls.get("background_density") or "medium",
        "reveal_mode": controls.get("reveal_mode") or "ask_or_derive",
        "camera_motion": controls.get("camera_motion") or controls.get("background_motion") or "derive_from_pacing",
        "material_relation": "material_refs_optional",
    }
    if style_family == "story_to_mv_transition":
        slots.update({
            "section_from": controls.get("section_from", "story"),
            "section_to": controls.get("section_to", "montage"),
            "pacing_shift": controls.get("pacing_shift", "slow_to_fast"),
            "material_relation": "source_and_target_segments_required",
        })
    elif style_family == "memory_photo_wall_warm":
        slots.update({
            "material_relation": "reviewed_photo_or_keyframe_refs_required",
            "pacing": controls.get("pacing", "slow"),
            "density": controls.get("density", "low"),
            "reveal_mode": controls.get("reveal_mode", "one_by_one"),
            "camera_motion": controls.get("camera_motion", "slow_push_in"),
        })
    elif style_family == "japanese_soft_storybook":
        slots.update({
            "material_relation": "generated_or_existing_scene_plate",
            "pacing": "slow",
            "density": controls.get("background_density", "clean"),
            "reveal_mode": "soft_story_reveal",
            "camera_motion": "gentle_parallax",
        })
    elif style_family == "terminal_data_reveal":
        slots.update({
            "material_relation": "abstract_generated_overlay",
            "story_function": "cyber_information_reveal",
            "pacing": "fast_then_hold",
            "density": controls.get("glyph_density", "medium"),
            "reveal_mode": "data_stream_to_title_assembly",
            "camera_motion": "static_or_micro_jitter",
        })
    elif style_family == "vintage_film_burn_transition":
        slots.update({
            "material_relation": "source_and_target_shots_required",
            "story_function": "memory_to_truth_transition",
            "pacing": "medium_slow",
            "density": "medium_texture",
            "reveal_mode": "burn_through_wipe",
            "camera_motion": "gate_weave_drift",
        })
    elif style_family == "ink_spread_reveal":
        slots.update({
            "material_relation": "abstract_or_scene_plate_optional",
            "story_function": "organic_title_reveal",
            "pacing": "slow_to_medium",
            "density": "medium_texture",
            "reveal_mode": "ink_mask_growth",
            "camera_motion": "static_or_slow_push",
        })
    elif style_family == "prism_glass_refraction":
        slots.update({
            "material_relation": "source_and_target_shots_preferred",
            "story_function": "crystalline_transition",
            "pacing": "medium",
            "density": "medium_geometry",
            "reveal_mode": "refraction_sweep",
            "camera_motion": "static_with_plane_motion",
        })
    if "結尾" in request or "closing" in request.casefold():
        slots["placement"] = "ending"
    return slots


def _remotion_capability_plan(
    *,
    style_family: str,
    effect_role: str,
    technique: Mapping[str, Any],
) -> dict[str, Any]:
    capabilities = list(technique.get("render_strategy") or [])
    primitives = ["sequence_layers", "useCurrentFrame", "interpolate_easing"]
    controls = technique.get("controls") if isinstance(technique.get("controls"), Mapping) else {}
    visual = " ".join(str(item) for item in technique.get("visual_primitives") or [])
    motion = " ".join(str(item) for item in technique.get("motion_primitives") or [])
    combined = f"{visual} {motion} {style_family} {effect_role}".casefold()
    layers: list[dict[str, Any]] = []
    api_refs = ["useCurrentFrame", "interpolate", "Easing.bezier", "Sequence"]
    timing_controls = {
        "duration_sec": controls.get("duration_sec", "required_or_derived"),
        "easing": "bezier_or_spring_by_pacing",
        "fps_conversion": "seconds_to_frames",
        "premount_for_frames": "required_for_sequences",
    }
    parameter_schema: dict[str, Any] = {
        "duration_sec": {"type": "number", "required": True, "maps_to": "composition_duration"},
        "style_family": {"type": "string", "required": True, "maps_to": "review_label"},
    }
    if effect_role == "transition" or "transition" in style_family:
        primitives.append("transition_series")
        api_refs.append("TransitionSeries.Transition")
        api_refs.append("TransitionSeries.Overlay")
        timing_controls["transition_duration_sec"] = controls.get("transition_duration_sec", "derive_from_duration")
    if any(token in combined for token in ("particle", "petal", "heart", "ember", "gold", "spark", "lightning", "dust")):
        primitives.append("particle_layer")
        layers.append({
            "role": "particle_overlay",
            "source": "generated_vector_or_canvas_particles",
            "controlled_by": ["density", "particle_count", "motion_intensity"],
        })
        parameter_schema["particle_count"] = {"type": "number|string", "required": False, "maps_to": "particle_layer.count"}
    if any(token in combined for token in ("lightning", "electric", "arc_strike", "branching_lightning_arcs", "electric_blue_glow")):
        primitives.append("electric_arc_layer")
        layers.append({
            "role": "electric_arc_layer",
            "source": "generated_svg_arc_paths",
            "controlled_by": ["strike_count", "arc_branching", "flash_intensity", "glow_strength"],
        })
        parameter_schema.update({
            "strike_count": {"type": "number", "required": False, "maps_to": "electric_arc_layer.count"},
            "arc_branching": {"type": "string", "required": False, "maps_to": "electric_arc_layer.branching"},
        })
    if any(token in combined for token in ("crack", "cracked", "surface_crack_lines", "impact_shake", "dust_rise")):
        primitives.append("crack_line_layer")
        layers.append({
            "role": "crack_line_layer",
            "source": "generated_svg_crack_paths",
            "controlled_by": ["crack_count", "crack_spread", "shake_strength", "dust_density"],
        })
        parameter_schema.update({
            "crack_count": {"type": "number", "required": False, "maps_to": "crack_line_layer.count"},
            "crack_spread": {"type": "string", "required": False, "maps_to": "crack_line_layer.spread"},
        })
    if any(token in combined for token in ("text", "title", "label", "caption")):
        primitives.append("text_layer")
        layers.append({
            "role": "text_layer",
            "source": "display_text_or_phase_labels",
            "controlled_by": ["title_readability", "safe_area", "text_reveal_speed"],
        })
        parameter_schema["display_text"] = {"type": "string", "required": False, "maps_to": "text_layer.content"}
    if any(token in combined for token in ("photo", "thumbnail", "collage", "grid")):
        primitives.append("image_layout")
        layers.append({
            "role": "image_layout",
            "source": "reviewed_material_refs",
            "controlled_by": ["material_refs", "reveal_mode", "crop_policy", "density"],
        })
        parameter_schema["material_refs"] = {"type": "array", "required": False, "maps_to": "image_layout.sources"}
    if any(token in combined for token in ("glow", "bloom", "light", "flash")):
        primitives.append("light_overlay")
        layers.append({
            "role": "light_overlay",
            "source": "generated_overlay",
            "controlled_by": ["glow_strength", "flash_intensity", "accent_light"],
        })
        parameter_schema["accent_light"] = {"type": "string", "required": False, "maps_to": "light_overlay.palette"}
    if any(token in combined for token in ("push", "parallax", "shake", "drift", "zoom", "arc_strike", "snap_scale", "impact")):
        primitives.append("camera_motion")
        layers.append({
            "role": "camera_motion",
            "source": "transform_animation",
            "controlled_by": ["camera_motion", "motion_intensity", "pacing"],
        })
        parameter_schema["camera_motion"] = {"type": "string", "required": False, "maps_to": "transform.animation"}
    if any(token in combined for token in ("glyph", "terminal", "scanline", "cursor", "data")):
        primitives.append("scanline_layer")
        layers.append({
            "role": "data_stream_layer",
            "source": "generated_terminal_glyphs",
            "controlled_by": ["glyph_speed", "glyph_density", "title_assembly_sec", "readability_guard"],
        })
        parameter_schema.update({
            "glyph_speed": {"type": "string", "required": False, "maps_to": "glyph_stream.speed"},
            "glyph_density": {"type": "string", "required": False, "maps_to": "glyph_stream.density"},
            "title_assembly_sec": {"type": "number", "required": False, "maps_to": "text_layer.assembly_time"},
            "readability_guard": {"type": "string", "required": True, "maps_to": "title_final_hold"},
        })
        timing_controls["title_assembly_sec"] = controls.get("title_assembly_sec", "derive_from_duration")
    if style_family == "vintage_film_burn_transition" or any(token in combined for token in ("burn", "gate", "film", "scratch")):
        primitives.append("mask_wipe_layer")
        layers.append({
            "role": "burn_mask_wipe",
            "source": "generated_mask_and_light_leak",
            "controlled_by": ["burn_edge_width", "burn_direction", "light_leak_strength", "transition_duration_sec"],
        })
        parameter_schema.update({
            "burn_edge_width": {"type": "string", "required": False, "maps_to": "mask_wipe.edge_width"},
            "burn_direction": {"type": "string", "required": False, "maps_to": "mask_wipe.direction"},
            "light_leak_strength": {"type": "string|number", "required": False, "maps_to": "light_overlay.intensity"},
            "grain_amount": {"type": "number", "required": False, "maps_to": "film_grain.amount"},
            "horror_guard": {"type": "string", "required": True, "maps_to": "negative_style_guard"},
        })
        timing_controls["transition_duration_sec"] = controls.get("transition_duration_sec", "derive_from_duration")
    if style_family == "ink_spread_reveal" or any(token in combined for token in ("ink_bloom", "ink spread", "paper_fiber")):
        primitives.extend(["mask_reveal_layer", "noise_displacement_layer", "texture_overlay_layer"])
        layers.append({
            "role": "ink_mask_reveal",
            "source": "generated_noise_mask",
            "controlled_by": ["ink_spread_radius", "edge_feather_px", "noise_scale", "title_reveal_sec"],
        })
        layers.append({
            "role": "paper_texture_overlay",
            "source": "generated_texture_overlay",
            "controlled_by": ["paper_texture_strength", "palette"],
        })
        parameter_schema.update({
            "ink_spread_radius": {"type": "string|number", "required": False, "maps_to": "mask_reveal.radius"},
            "edge_feather_px": {"type": "number", "required": False, "maps_to": "mask_reveal.edge_feather_px"},
            "noise_scale": {"type": "number", "required": False, "maps_to": "noise_displacement.scale"},
            "paper_texture_strength": {"type": "string|number", "required": False, "maps_to": "texture_overlay.opacity"},
            "title_reveal_sec": {"type": "number", "required": False, "maps_to": "text_layer.mask_reveal_time"},
            "readability_guard": {"type": "string", "required": True, "maps_to": "title_final_hold"},
        })
        timing_controls["title_reveal_sec"] = controls.get("title_reveal_sec", "derive_from_duration")
    if style_family == "prism_glass_refraction" or any(token in combined for token in ("prism", "refraction", "spectral", "chromatic")):
        primitives.extend(["refraction_layer", "clip_path_planes", "chromatic_split_layer", "mask_wipe_layer"])
        layers.append({
            "role": "prism_refraction",
            "source": "generated_refraction_planes",
            "controlled_by": ["prism_plane_count", "refraction_strength", "plane_angle_deg"],
        })
        layers.append({
            "role": "chromatic_split",
            "source": "rgb_channel_offset",
            "controlled_by": ["chromatic_aberration_px", "highlight_strength"],
        })
        layers.append({
            "role": "transition_mask_wipe",
            "source": "clip_path_plane_wipe",
            "controlled_by": ["transition_duration_sec", "readability_guard"],
        })
        parameter_schema.update({
            "prism_plane_count": {"type": "number", "required": False, "maps_to": "refraction.planes"},
            "chromatic_aberration_px": {"type": "number", "required": False, "maps_to": "chromatic_split.offset_px"},
            "refraction_strength": {"type": "string|number", "required": False, "maps_to": "refraction.strength"},
            "plane_angle_deg": {"type": "number", "required": False, "maps_to": "clip_path_planes.angle"},
            "highlight_strength": {"type": "string|number", "required": False, "maps_to": "light_overlay.intensity"},
            "readability_guard": {"type": "string", "required": True, "maps_to": "distortion_safe_area"},
        })
        timing_controls["transition_duration_sec"] = controls.get("transition_duration_sec", "derive_from_duration")
    if style_family == "story_to_mv_transition":
        layers.insert(0, {
            "role": "transition_overlay",
            "source": "source_target_section_boundary",
            "controlled_by": ["impact_moment_sec", "pacing_shift", "thumbnail_acceleration"],
        })
        timing_controls["impact_moment_sec"] = controls.get("impact_moment_sec", 2.2)
        parameter_schema.update({
            "section_from": {"type": "string", "required": True, "maps_to": "phase_labels.source"},
            "section_to": {"type": "string", "required": True, "maps_to": "phase_labels.target"},
            "impact_moment_sec": {"type": "number", "required": True, "maps_to": "transition_overlay.impact_frame"},
        })
    if style_family == "japanese_soft_storybook":
        parameter_schema["remotion_layered_paper"] = {
            "type": "object",
            "required": False,
            "maps_to": "background_texture_and_scene_plate",
        }
    if style_family == "memory_photo_wall_warm":
        layers = sorted(
            layers,
            key=lambda layer: 0 if layer.get("role") == "image_layout" else 1,
        )
    if not layers:
        layers.append({
            "role": "base_visual_layer",
            "source": "effect_contract_or_worker_default",
            "controlled_by": ["duration_sec", "intensity", "tone"],
        })
    return {
        "engine": "remotion",
        "timing_model": "useCurrentFrame_interpolate",
        "composition_model": "Sequence_or_TransitionSeries",
        "capabilities": capabilities,
        "primitives": list(dict.fromkeys(primitives)),
        "remotion_api_refs": list(dict.fromkeys(api_refs)),
        "layers": layers,
        "timing_controls": timing_controls,
        "parameter_schema": parameter_schema,
        "worker_contract_surface": "prompt_parameters.effect_build_spec",
        "fallback_policy": {
            "if_component_supported": "emit_effect_build_spec",
            "if_component_missing": "keep_candidate_parameters_and_require_review",
            "forbidden": "silent_template_substitution",
        },
        "review_evidence_required": ["still", "contact_sheet_or_preview", "parameter_echo"],
    }


def _effect_build_spec(
    *,
    style_family: str,
    technique: Mapping[str, Any],
    duration: float | None,
    remotion_capability_plan: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    controls = technique.get("controls") if isinstance(technique.get("controls"), Mapping) else {}
    duration_sec = float(duration or controls.get("duration_sec") or 5.0)
    if style_family == "memory_photo_wall_warm":
        return {
            "component": "MemoryPhotoWall",
            "duration_sec": duration_sec,
            "story_function": str(technique.get("story_function") or "memory_transition_or_emotional_recap"),
            "pacing": str(controls.get("pacing") or "slow"),
            "density": str(controls.get("density") or "low"),
            "reveal_mode": str(controls.get("reveal_mode") or "one_by_one"),
            "camera_motion": str(controls.get("camera_motion") or "slow_push_in"),
            "caption_mode": str(controls.get("caption_mode") or "minimal"),
        }
    if style_family == "story_to_mv_transition":
        return {
            "component": "StoryToMVTransition",
            "duration_sec": duration_sec,
            "section_from": str(controls.get("section_from") or "story"),
            "section_to": str(controls.get("section_to") or "montage"),
            "pacing_shift": str(controls.get("pacing_shift") or "slow_to_fast"),
            "impact_moment_sec": float(controls.get("impact_moment_sec") or max(0.5, duration_sec * 0.55)),
            "thumbnail_acceleration": str(controls.get("thumbnail_acceleration") or "medium"),
            "motion_grammar": [
                "film_rail",
                "thumbnail_acceleration",
                "flash_wipe",
                "hard_cut_bars",
            ],
            "phase_labels": list(controls.get("phase_labels") or ["STORY", "MONTAGE"]),
        }
    if isinstance(remotion_capability_plan, Mapping):
        layers = _generic_effect_layers(
            style_family=style_family,
            technique=technique,
            remotion_capability_plan=remotion_capability_plan,
        )
        if layers:
            return {
                "component": "GenericRemotionEffect",
                "duration_sec": duration_sec,
                "canvas": {"width": 1920, "height": 1080, "fps": 30},
                "layers": layers,
                "timing": _generic_effect_timing(
                    duration_sec=duration_sec,
                    controls=controls,
                    remotion_capability_plan=remotion_capability_plan,
                ),
                "review_required": True,
            }
    return None


def _generic_effect_layers(
    *,
    style_family: str,
    technique: Mapping[str, Any],
    remotion_capability_plan: Mapping[str, Any],
) -> list[dict[str, Any]]:
    controls = technique.get("controls") if isinstance(technique.get("controls"), Mapping) else {}
    plan_layers = [
        item for item in remotion_capability_plan.get("layers") or []
        if isinstance(item, Mapping)
    ]
    layers: list[dict[str, Any]] = []
    if any(item.get("role") == "data_stream_layer" for item in plan_layers):
        layers.append({
            "id": "data_stream",
            "type": "glyph_stream",
            "params": {
                "glyph_speed": controls.get("glyph_speed", "medium"),
                "glyph_density": controls.get("glyph_density", "medium"),
                "palette": controls.get("palette", "cyan_green_on_dark"),
                "scanline_opacity": controls.get("scanline_opacity", 0.2),
            },
        })
    if any(item.get("role") == "electric_arc_layer" for item in plan_layers):
        layers.append({
            "id": "electric_arcs",
            "type": "electric_arcs",
            "params": {
                "strike_count": controls.get("strike_count", 3),
                "arc_branching": controls.get("arc_branching", "medium"),
                "flash_intensity": controls.get("flash_intensity", "high"),
                "glow_strength": controls.get("glow_strength", "medium"),
                "palette": controls.get("palette", "electric_blue"),
            },
        })
    if any(item.get("role") == "crack_line_layer" for item in plan_layers):
        layers.append({
            "id": "crack_lines",
            "type": "crack_lines",
            "params": {
                "crack_count": controls.get("crack_count", 5),
                "crack_spread": controls.get("crack_spread", "center_out"),
                "shake_strength": controls.get("shake_strength", "medium"),
                "dust_density": controls.get("dust_density", "low"),
            },
        })
    if any(item.get("role") == "burn_mask_wipe" for item in plan_layers):
        layers.append({
            "id": "burn_mask",
            "type": "mask_wipe",
            "params": {
                "burn_edge_width": controls.get("burn_edge_width", "medium"),
                "burn_direction": controls.get("burn_direction", "edge_to_center"),
                "light_leak_strength": controls.get("light_leak_strength", "medium"),
            },
        })
        layers.append({
            "id": "film_grain",
            "type": "film_grain",
            "params": {
                "grain_amount": controls.get("grain_amount", 0.2),
                "gate_weave_strength": controls.get("gate_weave_strength", "low"),
            },
        })
    if any(item.get("role") == "ink_mask_reveal" for item in plan_layers):
        layers.append({
            "id": "ink_mask",
            "type": "mask_reveal",
            "params": {
                "mask_family": "ink_bloom",
                "ink_spread_radius": controls.get("ink_spread_radius", "medium"),
                "edge_feather_px": controls.get("edge_feather_px", 42),
                "noise_scale": controls.get("noise_scale", 0.72),
                "reveal_sec": controls.get("title_reveal_sec", 3.2),
            },
        })
        layers.append({
            "id": "paper_texture",
            "type": "texture_overlay",
            "params": {
                "texture": "paper_fiber",
                "strength": controls.get("paper_texture_strength", "medium"),
                "palette": controls.get("palette", "black_ink_on_warm_paper"),
            },
        })
    if any(item.get("role") == "prism_refraction" for item in plan_layers):
        layers.append({
            "id": "prism_refraction",
            "type": "refraction",
            "params": {
                "plane_count": controls.get("prism_plane_count", 5),
                "refraction_strength": controls.get("refraction_strength", "medium"),
                "plane_angle_deg": controls.get("plane_angle_deg", 18),
            },
        })
    if any(item.get("role") == "chromatic_split" for item in plan_layers):
        layers.append({
            "id": "chromatic_split",
            "type": "chromatic_split",
            "params": {
                "offset_px": controls.get("chromatic_aberration_px", 14),
                "highlight_strength": controls.get("highlight_strength", "soft"),
            },
        })
    if any(item.get("role") == "transition_mask_wipe" for item in plan_layers):
        layers.append({
            "id": "plane_wipe",
            "type": "mask_wipe",
            "params": {
                "wipe_family": "clip_path_planes",
                "transition_duration_sec": controls.get("transition_duration_sec", "derive_from_duration"),
                "readability_guard": controls.get("readability_guard", "avoid_text_under_strong_refraction"),
            },
        })
    if any(item.get("role") == "particle_overlay" for item in plan_layers):
        layers.append({
            "id": "particles",
            "type": "particle_overlay",
            "params": {
                "density": controls.get("density", controls.get("particle_density", "medium")),
                "motion_intensity": controls.get("motion_intensity", "medium"),
            },
        })
    if any(item.get("role") == "light_overlay" for item in plan_layers):
        layers.append({
            "id": "light_overlay",
            "type": "light_overlay",
            "params": {
                "accent_light": controls.get("accent_light", controls.get("color_mood", "default")),
                "glow_strength": controls.get("glow_strength", controls.get("flash_intensity", "medium")),
            },
        })
    if any(item.get("role") == "image_layout" for item in plan_layers):
        layers.append({
            "id": "image_layout",
            "type": "image_layout",
            "params": {
                "material_refs": controls.get("material_refs", []),
                "reveal_mode": controls.get("reveal_mode", "ask_or_derive"),
                "density": controls.get("density", "medium"),
            },
        })
    if any(item.get("role") == "camera_motion" for item in plan_layers):
        layers.append({
            "id": "camera_motion",
            "type": "camera_motion",
            "params": {
                "camera_motion": controls.get("camera_motion", "derive_from_pacing"),
                "pacing": controls.get("pacing", "medium"),
            },
        })
    if any(item.get("role") == "text_layer" for item in plan_layers):
        layers.append({
            "id": "title",
            "type": "text",
            "params": {
                "content": controls.get("display_text", "TITLE"),
                "animation": "assemble" if style_family == "terminal_data_reveal" else "fade",
                "safe_area": controls.get("title_safe_area", "center"),
                "readability_guard": controls.get("readability_guard", "safe_area_readable"),
            },
        })
    return layers


def _generic_effect_timing(
    *,
    duration_sec: float,
    controls: Mapping[str, Any],
    remotion_capability_plan: Mapping[str, Any],
) -> dict[str, Any]:
    timing = dict(remotion_capability_plan.get("timing_controls") or {})
    return {
        "duration_sec": duration_sec,
        "reveal_sec": float(controls.get("title_assembly_sec") or max(0.4, duration_sec * 0.7)),
        "hold_sec": max(0.2, duration_sec - float(controls.get("title_assembly_sec") or duration_sec * 0.7)),
        "transition_duration_sec": controls.get("transition_duration_sec", timing.get("transition_duration_sec")),
        "easing": timing.get("easing", "bezier_or_spring_by_pacing"),
    }


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
        "japanese_soft_storybook",
        "story_to_mv_transition",
        "ink_spread_reveal",
        "prism_glass_refraction",
        "terminal_data_reveal",
        "vintage_film_burn_transition",
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

    semantic_slots = _semantic_slots(
        style_family=str(technique.get("style_family") or style_family),
        effect_role=effect_role,
        request=request,
        technique=technique,
        duration=duration,
    )
    remotion_capability_plan = _remotion_capability_plan(
        style_family=str(technique.get("style_family") or style_family),
        effect_role=effect_role,
        technique=technique,
    )
    build_spec = _effect_build_spec(
        style_family=str(technique.get("style_family") or style_family),
        technique=technique,
        duration=duration,
        remotion_capability_plan=remotion_capability_plan,
    )

    result = {
        "artifact_role": "visual_technique_plan",
        "version": 1,
        "effect_role": effect_role,
        "material_state": material_state,
        "semantic_slots": semantic_slots,
        "remotion_capability_plan": remotion_capability_plan,
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
    if build_spec:
        result["effect_build_spec"] = build_spec
    return result


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

    explicit_template_id = str(technique_plan.get("template_id") or "").strip()
    has_generic_build_spec = isinstance(technique_plan.get("effect_build_spec"), Mapping)
    template_id = explicit_template_id or None
    if template_id is None and not has_generic_build_spec and role == "title_card":
        template_id = "clean_white_quote_card" if effect_role == "closing_title" else "training_opening_title"
    elif template_id is None and not has_generic_build_spec and role == "chapter_transition":
        template_id = "film_strip_transition_card"

    result = {
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
    if isinstance(technique_plan.get("effect_build_spec"), Mapping):
        build_spec = json.loads(json.dumps(technique_plan["effect_build_spec"], ensure_ascii=False))
        if build_spec.get("component") == "GenericRemotionEffect":
            for layer in build_spec.get("layers") or []:
                if not isinstance(layer, dict) or layer.get("type") != "text":
                    continue
                params = layer.setdefault("params", {})
                if isinstance(params, dict) and str(params.get("content") or "").strip().upper() in {"", "TITLE"}:
                    params["content"] = display_text or str(technique_plan.get("display_text") or "Opening")
        result["prompt_parameters"]["effect_build_spec"] = build_spec
    return result


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
