"""Generic Effect Factory layer vocabulary and worker support metadata."""

from __future__ import annotations

from typing import Any


GENERIC_LAYER_MANIFEST: dict[str, dict[str, Any]] = {
    "camera_motion": {
        "purpose": "bounded scale, shake, or drift on the effect layer group",
        "worker_supported": True,
        "renderer_marker": "genericCameraMotionLayer",
    },
    "chromatic_split": {
        "purpose": "RGB/spectral split treatment",
        "worker_supported": True,
        "renderer_marker": "genericChromaticSplitLayer",
    },
    "crack_lines": {
        "purpose": "stylized impact or crack line paths",
        "worker_supported": True,
        "renderer_marker": "genericCrackLineLayer",
    },
    "electric_arcs": {
        "purpose": "stylized lightning or electric arc paths",
        "worker_supported": True,
        "renderer_marker": "genericElectricArcLayer",
    },
    "film_grain": {
        "purpose": "film grain or gate texture",
        "worker_supported": True,
        "renderer_marker": "genericFilmGrainLayer",
    },
    "glyph_stream": {
        "purpose": "terminal or data-stream rows",
        "worker_supported": True,
        "renderer_marker": "genericGlyphStreamLayer",
    },
    "image_layout": {
        "purpose": "reviewed image or photo placement",
        "worker_supported": True,
        "renderer_marker": "genericImageLayoutLayer",
    },
    "radial_current": {
        "purpose": "outer-ring current, orbit, or energy-flow accents around a reviewed focal image",
        "worker_supported": True,
        "renderer_marker": "genericRadialCurrentLayer",
    },
    "light_overlay": {
        "purpose": "glow, wash, flare, or accent light plates",
        "worker_supported": True,
        "renderer_marker": "genericLightOverlayLayer",
    },
    "mask_reveal": {
        "purpose": "ink, organic, or simple reveal mask",
        "worker_supported": True,
        "renderer_marker": "genericInkMaskLayer",
    },
    "mask_wipe": {
        "purpose": "plane wipe, burn edge, or transition mask",
        "worker_supported": True,
        "renderer_marker": "genericPlaneWipeLayer",
    },
    "particle_overlay": {
        "purpose": "sparks, dust, petals, embers, or simple particles",
        "worker_supported": True,
        "renderer_marker": "genericParticleLayer",
    },
    "refraction": {
        "purpose": "prism or glass plane treatment",
        "worker_supported": True,
        "renderer_marker": "genericRefractionLayer",
    },
    "text": {
        "purpose": "main title or subtitle typography",
        "worker_supported": True,
        "renderer_marker": "genericTextLayer",
    },
    "texture_overlay": {
        "purpose": "paper, grain, scanline, or material texture",
        "worker_supported": True,
        "renderer_marker": "genericTextureOverlayLayer",
    },
}


def generic_layer_types() -> set[str]:
    return set(GENERIC_LAYER_MANIFEST)


def generic_worker_supported_layer_types() -> set[str]:
    return {
        layer_type
        for layer_type, meta in GENERIC_LAYER_MANIFEST.items()
        if meta.get("worker_supported") is True
    }


def generic_worker_renderer_markers() -> dict[str, str]:
    return {
        layer_type: str(meta["renderer_marker"])
        for layer_type, meta in GENERIC_LAYER_MANIFEST.items()
        if meta.get("worker_supported") is True
    }
