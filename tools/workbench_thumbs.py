#!/usr/bin/env python
"""Hermes-native workbench: timeline thumbnail strips (NPE5, Tier B).

Generates one filmstrip thumbnail per video clip using the **already-present
ffmpeg** (no WebCodecs, no npm, no Remotion/mediabunny dependency). Thumbnails are
a derived cache written under ``<root>/workbench_thumbs/`` -- never a canonical
artifact. Image clips reuse their own ``src_url`` directly.

The frontend overlays each thumbnail as a clip-block background so the editor can
see what each segment contains, the way an NLE review timeline does.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import urllib.parse
from pathlib import Path
from typing import Any, Callable, Dict, Optional

try:
    from tools import preview_timeline as pt
except ImportError:  # pragma: no cover - direct-script fallback
    import preview_timeline as pt

THUMBS_DIRNAME = "workbench_thumbs"
_FFMPEG = shutil.which("ffmpeg") or "ffmpeg"


def _media_url(abs_path: str, base_url: str) -> str:
    base = (base_url or "").rstrip("/")
    return f"{base}/media?src={urllib.parse.quote(str(abs_path), safe='')}"


def default_ffmpeg_runner(source: str, start_sec: float, out_path: str) -> bool:
    """Extract a single JPEG frame at ``start_sec``. Returns True on success."""
    try:
        r = subprocess.run(
            [_FFMPEG, "-y", "-ss", f"{max(0.0, float(start_sec)):.3f}", "-i", source,
             "-frames:v", "1", "-vf", "scale=320:-2", "-q:v", "5", out_path],
            capture_output=True, timeout=30,
        )
        return r.returncode == 0 and os.path.exists(out_path)
    except (OSError, subprocess.SubprocessError):
        return False


def build_thumbnails(
    artifact_root: str,
    base_url: str,
    runner: Callable[[str, float, str], bool] = default_ffmpeg_runner,
) -> Dict[str, Any]:
    """Build (cached) one thumbnail per video clip. Returns a manifest dict.

    ``thumbnails`` maps ``str(slot_index) -> media URL``. Existing thumbnails are
    reused (cache); a failed extraction is simply omitted (no crash).
    """
    root = Path(artifact_root)
    preview = pt.build_preview_timeline(str(root), base_url)
    thumbs_dir = root / THUMBS_DIRNAME
    thumbs_dir.mkdir(exist_ok=True)

    manifest: Dict[str, str] = {}
    built = 0
    for clip in preview.get("clips", []):
        slot = clip.get("slot_index")
        if clip.get("type") == "image":
            if clip.get("src_url"):
                manifest[str(slot)] = clip["src_url"]
            continue
        source = clip.get("source_path")
        if not source or not Path(source).exists():
            continue
        out = thumbs_dir / f"slot-{slot}.jpg"
        if not out.exists():
            if runner(source, float(clip.get("source_start_sec") or 0.0), str(out)):
                built += 1
            else:
                continue
        manifest[str(slot)] = _media_url(str(out.resolve()), base_url)

    return {
        "artifact_role": "workbench_thumbnails",
        "version": 1,
        "thumbs_dir": THUMBS_DIRNAME,
        "built": built,
        "thumbnails": manifest,
    }
