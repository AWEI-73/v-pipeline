"""Shared aspect-ratio intake validation."""
from __future__ import annotations

ALLOWED_ASPECT_RATIOS = {"16:9", "9:16", "1:1"}


def normalize_aspect_ratio(value):
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text


def is_supported_aspect_ratio(value) -> bool:
    text = normalize_aspect_ratio(value)
    return text in ALLOWED_ASPECT_RATIOS


def aspect_ratio_followup(value) -> str:
    allowed = ", ".join(sorted(ALLOWED_ASPECT_RATIOS))
    return (
        f"Which supported aspect ratio should this use? Choose one of: {allowed}. "
        f"The provided value {value!r} is not supported."
    )
