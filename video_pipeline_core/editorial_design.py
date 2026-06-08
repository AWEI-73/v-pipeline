"""editorial_design.py — Editorial design (Node 0A) management.

Defines default whole-video editorial designs and validates them.
All functions are pure (no I/O, no print).
"""
from __future__ import annotations

import re
from typing import Any


def default_editorial_design(blueprint: dict | None = None) -> dict:
    """Create a default editorial design configuration.

    If a blueprint is provided, carry over the mode hint and energy curve
    (based on the intended feelings of each beat).
    """
    blueprint = blueprint or {}

    video_mode = blueprint.get("mode_hint") or "training_recap"

    # Map energy curve from beats
    beats = blueprint.get("beats") or []
    energy_curve = [
        b.get("intended_feeling")
        for b in beats
        if b and isinstance(b, dict) and b.get("intended_feeling")
    ]
    if not energy_curve:
        energy_curve = ["opening_calm", "training_active", "achievement_proud", "closing_emotional"]

    return {
        "artifact_role": "editorial_design",
        "version": 1,
        "video_mode": video_mode,
        "editorial_intent": {
            "tone": "warm_reflective",
            "energy_curve": energy_curve,
            "attention_strategy": "story_progression_with_visual_variety",
            "continuity_priority": "high",
            "visual_variety_priority": "medium",
        },
        "narration_strategy": {
            "mode": "voiceover",
            "density": "medium",
            "purpose": ["context"],
            "speaker": "neutral_narrator",
        },
        "subtitle_strategy": {
            "mode": "full_subtitle",
            "placement": "bottom_safe",
            "density": "full",
            "avoid": ["logo"],
            "style": "clean",
        },
        "text_layer_strategy": {
            "subtitle": "full",
            "chapter_titles": True,
            "name_supers": "speakers",
            "callouts": "training_terms_only",
            "max_simultaneous_text_layers": 2,
        },
        "music_strategy": {
            "mode": "single_theme",
            "duck_under_speech": True,
            "chapter_music": [],
        },
        "effects_strategy": {
            "intensity": "restrained",
            "allowed_roles": ["chapter_transition", "photo_motion"],
            "avoid": ["over_animation"],
            "reason_required": True,
        },
        "still_image_strategy": {
            "use_case": "fallback",
            "treatment": ["slow_push", "pan"],
            "max_static_hold_sec": 5,
            "allow_long_hold_when": ["group_photo"],
        },
    }


def validate_editorial_design(d: dict) -> dict:
    """Validate the editorial design structure and values.

    Returns:
        dict: {"ok": bool, "errors": list[str], "warnings": list[str]}

    Validation rules:
      - Required top-level fields must be present and match structure.
      - String fields must not contain provider names, templates, file paths,
        or file names (no pexels, capcut, remotion, blender, .mp4, .png, etc.).
    """
    errors: list[str] = []
    warnings: list[str] = []

    # 1. Structure validation
    required_sections = (
        "video_mode",
        "editorial_intent",
        "narration_strategy",
        "subtitle_strategy",
        "text_layer_strategy",
        "music_strategy",
        "effects_strategy",
        "still_image_strategy",
    )

    for section in required_sections:
        if section not in d:
            errors.append(f"Missing required section: '{section}'")

    # 2. Provider / Path / File Blocklist validation
    blocklist_words = {
        "pexels",
        "pixabay",
        "unsplash",
        "capcut",
        "remotion",
        "blender",
        "template",
        "provider",
    }

    # Matches file paths/extensions and filenames
    file_pattern = re.compile(
        r"\.(mp4|mov|avi|mkv|mp3|wav|png|jpg|jpeg|webp|gif|json|xml|draft)$",
        re.IGNORECASE,
    )
    path_pattern = re.compile(r"(/|\\|:\\|:/)")

    def walk_and_validate(val: Any, path: str):
        if isinstance(val, str):
            # Check blocklist words
            for word in blocklist_words:
                if word in val.lower():
                    errors.append(
                        f"Field '{path}' contains blocked provider/template keyword: '{word}' (value: '{val}')"
                    )

            # Check file extensions
            if file_pattern.search(val) or any(val.lower().endswith(ext) for ext in (".mp4", ".mov", ".png", ".jpg", ".jpeg")):
                errors.append(
                    f"Field '{path}' contains blocked filename pattern: '{val}'"
                )

            # Check paths
            if path_pattern.search(val) or val.startswith("/") or val.startswith("."):
                # Exception: "bottom_safe", "lower_third", "dynamic_by_scene" or normal strings containing "/"
                # but let's block slash if it looks like a path.
                # If a string contains slash, starts with ./ or ../ or is an absolute path
                if (
                    val.startswith("/")
                    or val.startswith("./")
                    or val.startswith("../")
                    or ":/" in val
                    or ":\\" in val
                ):
                    errors.append(
                        f"Field '{path}' contains blocked path pattern: '{val}'"
                    )
        elif isinstance(val, dict):
            for k, v in val.items():
                walk_and_validate(v, f"{path}.{k}" if path else k)
        elif isinstance(val, list):
            for i, v in enumerate(val):
                walk_and_validate(v, f"{path}[{i}]")

    walk_and_validate(d, "")

    return {
        "ok": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }
