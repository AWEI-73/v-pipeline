"""build_profile.py — BUILD-layer tool/provider profile artifact.

The canonical segment contract says what is allowed. The build profile says
which concrete provider/backend a run should use.
"""
import copy
import json
from pathlib import Path


ALLOWED_RENDER_PROFILES = {"no_effects", "light_effects", "motion_graphics", "debug"}
ALLOWED_VISUAL_PROVIDERS = {
    "pexels",
    "pixabay",
    "antigravity",
    "assistant_imagegen",
    "codex_imagegen",
    "gemini_veo",
}
ALLOWED_FALLBACK_MODES = {"stock_video", "generated_image", "generated_video", "text_bridge"}
ALLOWED_MOTION_BACKENDS = {"ffmpeg_libass", "html_playwright", "remotion", "mlt", "blender"}


DEFAULT_BUILD_PROFILE = {
    "artifact_role": "build_profile",
    "build_profile_version": 1,
    "render_profile": "no_effects",
    "fallback_visual_provider": "assistant_imagegen",
    "provider_priority": ["assistant_imagegen", "antigravity", "pexels", "pixabay"],
    "fallback_visual_mode": "generated_image",
    "effects_enabled": False,
    "motion_graphics_backend": "ffmpeg_libass",
    "model_routes": "model_routes.json",
    "quality_baseline": "no_effects_quality",
}


def default_build_profile():
    return copy.deepcopy(DEFAULT_BUILD_PROFILE)


def _validate_choice(payload, field, allowed):
    value = payload.get(field)
    if value not in allowed:
        raise ValueError(f"{field} must be one of {sorted(allowed)}")


def validate_build_profile(profile):
    if not isinstance(profile, dict):
        raise ValueError("build_profile must be object")
    if profile.get("build_profile_version") != 1:
        raise ValueError("build_profile_version must be 1")
    _validate_choice(profile, "render_profile", ALLOWED_RENDER_PROFILES)
    _validate_choice(profile, "fallback_visual_provider", ALLOWED_VISUAL_PROVIDERS)
    _validate_choice(profile, "fallback_visual_mode", ALLOWED_FALLBACK_MODES)
    _validate_choice(profile, "motion_graphics_backend", ALLOWED_MOTION_BACKENDS)
    priority = profile.get("provider_priority")
    if not isinstance(priority, list) or not priority:
        raise ValueError("provider_priority must be non-empty list")
    for provider in priority:
        if provider not in ALLOWED_VISUAL_PROVIDERS:
            raise ValueError(f"unsupported provider in provider_priority: {provider}")
    if profile["fallback_visual_provider"] not in priority:
        raise ValueError("fallback_visual_provider must appear in provider_priority")
    if "comfyui" in priority or profile.get("fallback_visual_provider") == "comfyui":
        raise ValueError("comfyui is deprecated/disabled and cannot be active provider")
    return profile


def load_build_profile(path=None, overrides=None):
    profile = default_build_profile()
    if path:
        with Path(path).open(encoding="utf-8") as f:
            incoming = json.load(f)
        if not isinstance(incoming, dict):
            raise ValueError("build_profile override must be object")
        profile.update(incoming)
    if overrides:
        profile.update(overrides)
    profile.setdefault("artifact_role", "build_profile")
    profile.setdefault("build_profile_version", 1)
    return validate_build_profile(profile)


def write_build_profile(path, profile=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = validate_build_profile(profile or default_build_profile())
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return str(path)
