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
# P3: optional Node 13 render-candidate backends. ffmpeg stays the canonical
# unattended MVP backend; the others are opt-in and may require a human/Computer
# Use step (CapCut GUI export, etc.).
ALLOWED_RENDER_BACKENDS = {"ffmpeg", "capcut_draft", "remotion", "html_playwright"}
ALLOWED_VISUAL_JUDGES = {"agent", "ollama", "none"}


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
    # P3: Node 13 render-candidate backend. Default ffmpeg = fully unattended.
    "render_backend": "ffmpeg",
    "requires_human_or_computer_use": False,
    "visual_judge": "agent",
    # P1 verification tool pack. Default OFF so existing runs are unchanged;
    # enable per project to make contract-run auto-produce audit evidence.
    "verification_tools": {
        "timeline_invariants": False,
        "broll_audit": False,
        "caption_audit": False,
        "keyframe_grid": False,
        "visual_audit": False,
    },
    "broll_policy": {"target_ratio": None, "max_source_repeats": None},
    "keyframe_grid": {"sample_count": 12, "columns": 4},
    "editing_policy": None,
}

VERIFICATION_TOOL_NAMES = (
    "timeline_invariants", "broll_audit", "caption_audit",
    "keyframe_grid", "visual_audit",
)


def verification_tools(profile):
    """Return the enabled-state of each P1 verification tool.

    Missing keys default to False so older profiles (and partial overrides) read
    safely without enabling anything.
    """
    vt = (profile or {}).get("verification_tools") or {}
    return {name: bool(vt.get(name, False)) for name in VERIFICATION_TOOL_NAMES}


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
    if "render_backend" in profile:
        _validate_choice(profile, "render_backend", ALLOWED_RENDER_BACKENDS)
    _validate_choice(profile, "visual_judge", ALLOWED_VISUAL_JUDGES)
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
