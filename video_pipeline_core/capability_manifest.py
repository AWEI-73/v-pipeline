"""Deterministic runtime capability manifest for pre-BUILD enforcement."""
from __future__ import annotations

import json
from pathlib import Path


PATCH_TYPES = ("crop", "treatment", "window")
UNSUPPORTED = (
    "arbitrary_effects",
    "cloud_vlm_default",
    "full_nle_ui",
    "multi_track_music",
    "remotion_backend",
)


def build_capability_manifest():
    from video_pipeline import ALLOWED_TRANSITIONS
    from . import build_profile, edit_artifacts, sfx, spec_contract

    providers = set(build_profile.ALLOWED_VISUAL_PROVIDERS)
    providers.update(("local", "stock", "generated"))
    return {
        "artifact_role": "capability_manifest",
        "capability_manifest_version": 1,
        "generated": True,
        "capabilities": {
            "transitions": sorted(ALLOWED_TRANSITIONS),
            "still_treatments": sorted(edit_artifacts._STILL_TREATMENT_MODES),
            "sfx_cues": sorted(sfx.ASSET_COUNTS),
            "patch_types": sorted(PATCH_TYPES),
            "audio_policies": sorted(spec_contract.AUDIO_ROLES),
            "render_profiles": sorted(build_profile.ALLOWED_RENDER_PROFILES),
            "render_backends": sorted(build_profile.ALLOWED_RENDER_BACKENDS),
            "providers": sorted(providers),
            "judge_modes": sorted(build_profile.ALLOWED_VISUAL_JUDGES),
        },
        "unsupported": list(UNSUPPORTED),
    }


def supported_capabilities(manifest=None):
    manifest = manifest or build_capability_manifest()
    values = set()
    for items in (manifest.get("capabilities") or {}).values():
        values.update(items or [])
    return values


def write_capability_manifest(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(build_capability_manifest(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return str(path)

