"""Pure still-image motion policy shared by MV and bounded rough-cut renders."""
from __future__ import annotations

from pathlib import Path
from typing import Any


STILL_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".heic", ".tif", ".tiff"}
STILL_TREATMENT_MODES = ("slow_push", "pan_right", "detail_push", "pan_left")


def is_still_source(source_path: str | Path, source_type: str | None = None) -> bool:
    declared = str(source_type or "").casefold()
    return declared in {"photo", "image", "still"} or Path(source_path).suffix.casefold() in STILL_SUFFIXES


def still_motion_strength(duration_sec: float) -> dict[str, float]:
    """Cap long still motion so extended photo holds do not overpush."""
    seconds = float(duration_sec or 0.0)
    if seconds >= 12:
        return {"slow": 0.05, "detail": 0.12, "pan_zoom": 1.08}
    if seconds >= 8:
        return {"slow": 0.08, "detail": 0.16, "pan_zoom": 1.10}
    return {"slow": 0.22, "detail": 0.32, "pan_zoom": 1.18}


def build_still_motion_filter(
    duration_sec: float,
    *,
    treatment: dict[str, Any] | None = None,
    kenburns: bool = True,
    width: int = 1920,
    height: int = 1080,
    fps: int = 30,
) -> str:
    hold = (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps},format=yuv420p"
    )
    if not kenburns or (treatment or {}).get("mode") == "hold":
        return hold
    frames = max(1, round((duration_sec or 1.0) * fps))
    progress = max(1, frames - 1)
    t = f"(n/{progress})"
    mode = (treatment or {}).get("mode", "slow_push")
    strength = still_motion_strength(duration_sec)
    work_width, work_height = width * 2, height * 2
    if mode in {"pan_right", "pan_left"}:
        zoom = f"{strength['pan_zoom']:.2f}"
        x = f"(iw-ow)*{t}" if mode == "pan_right" else f"(iw-ow)*(1-{t})"
        return (
            f"fps={fps},"
            f"scale=w='{work_width}*{zoom}':h='{work_height}*{zoom}':force_original_aspect_ratio=increase:eval=frame,"
            f"crop={work_width}:{work_height}:x='{x}':y='(ih-oh)/2',"
            f"scale={width}:{height},setsar=1,format=yuv420p"
        )
    delta = strength["detail"] if mode == "detail_push" else strength["slow"]
    zoom = f"(1+{delta:.2f}*{t})"
    return (
        f"fps={fps},"
        f"scale=w='{work_width}*{zoom}':h='{work_height}*{zoom}':force_original_aspect_ratio=increase:eval=frame,"
        f"crop={work_width}:{work_height}:x='(iw-ow)/2':y='(ih-oh)/2',"
        f"scale={width}:{height},setsar=1,format=yuv420p"
    )
