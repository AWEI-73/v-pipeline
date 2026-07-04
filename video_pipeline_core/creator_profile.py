"""creator_profile.py — P2 stable creator/channel defaults.

A creator profile holds preferences that are stable across many projects (brand,
platform, subtitle/editing/audio defaults), separate from a single project's
``brief.json``. Precedence is strict and recorded:

    segment_contract.json   (project-specific, never touched here)
    brief.json              (always overrides creator-profile defaults)
    creator_profile.json    (fills in defaults the brief did not set)

``resolve_defaults`` returns both the effective settings and a provenance map so
the runtime can record exactly which defaults were applied.

Source: concept inspired by https://github.com/Hao0321/video-autopilot-kit
(MIT) brand/voice profiles; reimplemented generically with no creator-specific
values baked in.
"""
import copy
import json
from pathlib import Path

from .aspect_ratio import aspect_ratio_followup, is_supported_aspect_ratio


DEFAULT_CREATOR_PROFILE = {
    "artifact_role": "creator_profile",
    "profile_version": 1,
    "brand": {"name": None, "colors": [], "fonts": [], "logo": None},
    "platform_defaults": {"platform": None, "aspect_ratio": None, "target_length": None},
    "subtitle_defaults": {"style": None, "max_chars_per_line": None},
    "editing_defaults": {"render_profile": None, "broll_ratio_target": None,
                         "max_source_repeats": None},
    "audio_defaults": {"music_style": None, "ducking": None},
    "outro_defaults": {},
}

# Flat setting key -> (section, field) in the creator profile.
_DEFAULT_MAP = {
    "platform": ("platform_defaults", "platform"),
    "aspect_ratio": ("platform_defaults", "aspect_ratio"),
    "target_length": ("platform_defaults", "target_length"),
    "subtitle_style": ("subtitle_defaults", "style"),
    "max_chars_per_line": ("subtitle_defaults", "max_chars_per_line"),
    "render_profile": ("editing_defaults", "render_profile"),
    "broll_ratio_target": ("editing_defaults", "broll_ratio_target"),
    "max_source_repeats": ("editing_defaults", "max_source_repeats"),
    "music_style": ("audio_defaults", "music_style"),
    "ducking": ("audio_defaults", "ducking"),
}


def default_creator_profile():
    return copy.deepcopy(DEFAULT_CREATOR_PROFILE)


def validate_creator_profile(profile):
    if not isinstance(profile, dict):
        raise ValueError("creator_profile must be an object")
    if profile.get("profile_version") != 1:
        raise ValueError("profile_version must be 1")
    return profile


def load_creator_profile(path=None, overrides=None):
    profile = default_creator_profile()
    if path:
        with Path(path).open(encoding="utf-8") as f:
            incoming = json.load(f)
        if not isinstance(incoming, dict):
            raise ValueError("creator_profile override must be an object")
        for k, v in incoming.items():
            if isinstance(v, dict) and isinstance(profile.get(k), dict):
                profile[k] = {**profile[k], **v}
            else:
                profile[k] = v
    if overrides:
        for k, v in overrides.items():
            if isinstance(v, dict) and isinstance(profile.get(k), dict):
                profile[k] = {**profile[k], **v}
            else:
                profile[k] = v
    profile.setdefault("artifact_role", "creator_profile")
    profile.setdefault("profile_version", 1)
    return validate_creator_profile(profile)


def write_creator_profile(path, profile=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = validate_creator_profile(profile or default_creator_profile())
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return str(path)


def resolve_defaults(creator_profile, brief=None):
    """Overlay ``brief`` over creator-profile defaults and record provenance.

    Returns ``{resolved, sources, applied}`` where:
      * resolved — effective settings (omits keys nobody set)
      * sources  — per-key origin ("brief" or "creator_profile")
      * applied  — keys whose value came from the creator profile (the defaults
                   actually applied because the brief did not set them)
    """
    cp = creator_profile or {}
    brief = brief or {}
    resolved, sources, applied = {}, {}, []
    required_followup_questions = []
    for key, (section, field) in _DEFAULT_MAP.items():
        brief_val = brief.get(key)
        cp_val = (cp.get(section) or {}).get(field)
        if brief_val is not None:
            if key == "aspect_ratio" and not is_supported_aspect_ratio(brief_val):
                sources[key] = "invalid"
                required_followup_questions.append(aspect_ratio_followup(brief_val))
                continue
            resolved[key] = brief_val
            sources[key] = "brief"
        elif cp_val is not None:
            if key == "aspect_ratio" and not is_supported_aspect_ratio(cp_val):
                sources[key] = "invalid"
                required_followup_questions.append(aspect_ratio_followup(cp_val))
                continue
            resolved[key] = cp_val
            sources[key] = "creator_profile"
            applied.append(key)
    return {
        "resolved": resolved,
        "sources": sources,
        "applied": applied,
        "required_followup_questions": required_followup_questions,
    }
