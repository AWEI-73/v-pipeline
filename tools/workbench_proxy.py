#!/usr/bin/env python
"""Hermes-native workbench video proxy cache.

Builds browser-friendly, low-bitrate MP4 clips for interactive preview only.
The proxies are derived cache files under ``<root>/workbench_proxy/``; they are
not canonical artifacts and never replace the original media used by the ffmpeg
BUILD. Each proxy is trimmed to the approved clip window, so browser playback
can start at 0 instead of seeking into a large .MOV file.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import urllib.parse
from pathlib import Path
from typing import Any, Callable, Dict

try:
    from tools import preview_timeline as pt
except ImportError:  # pragma: no cover
    import preview_timeline as pt

PROXY_DIRNAME = "workbench_proxy"
_FFMPEG = shutil.which("ffmpeg") or "ffmpeg"


def _media_url(abs_path: str, base_url: str) -> str:
    base = (base_url or "").rstrip("/")
    return f"{base}/media?src={urllib.parse.quote(str(abs_path), safe='')}"


def _proxy_name(clip: Dict[str, Any]) -> str:
    source = str(clip.get("source_path") or "")
    try:
        stat = Path(source).stat()
        stamp = f"{stat.st_mtime_ns}:{stat.st_size}"
    except OSError:
        stamp = "missing"
    key = "|".join([
        str(clip.get("slot_index")),
        source,
        stamp,
        str(clip.get("source_start_sec")),
        str(clip.get("source_duration_sec")),
        str(clip.get("duration_sec")),
    ])
    h = hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]
    return f"slot-{clip.get('slot_index')}-{h}.mp4"


def default_ffmpeg_runner(source: str, start_sec: float, duration_sec: float, out_path: str) -> bool:
    """Transcode a trimmed preview MP4. Returns True on success."""
    try:
        r = subprocess.run(
            [
                _FFMPEG, "-y",
                "-ss", f"{max(0.0, float(start_sec)):.3f}",
                "-t", f"{max(0.05, float(duration_sec)):.3f}",
                "-i", source,
                "-vf", "scale=960:-2",
                "-an",
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "28",
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
                out_path,
            ],
            capture_output=True,
            timeout=90,
        )
        return r.returncode == 0 and os.path.exists(out_path) and os.path.getsize(out_path) > 0
    except (OSError, subprocess.SubprocessError, ValueError):
        return False


def build_proxies(
    artifact_root: str,
    base_url: str,
    runner: Callable[[str, float, float, str], bool] = default_ffmpeg_runner,
) -> Dict[str, Any]:
    """Build/cache one trimmed preview proxy per video clip.

    Returns a manifest mapping ``slot_index`` to ``{src_url, source_start_sec,
    source_duration_sec}``. Image clips are omitted. Failed proxy extraction is
    non-fatal; the frontend can keep using the original source.
    """
    root = Path(artifact_root)
    preview = pt.build_preview_timeline(str(root), base_url)
    proxy_dir = root / PROXY_DIRNAME
    proxy_dir.mkdir(exist_ok=True)

    proxies: Dict[str, Dict[str, Any]] = {}
    built = 0
    for clip in preview.get("clips", []):
        if clip.get("type") != "video":
            continue
        source = clip.get("source_path")
        if not source or not Path(source).is_file():
            continue
        duration = float(clip.get("source_duration_sec") or clip.get("duration_sec") or 0.0)
        if duration <= 0:
            continue
        out = proxy_dir / _proxy_name(clip)
        if not out.exists():
            if runner(source, float(clip.get("source_start_sec") or 0.0), duration, str(out)):
                built += 1
            else:
                continue
        proxies[str(clip.get("slot_index"))] = {
            "src_url": _media_url(str(out.resolve()), base_url),
            "source_start_sec": 0.0,
            "source_duration_sec": round(duration, 6),
            "proxy_ref": str(out.relative_to(root)),
        }

    return {
        "artifact_role": "workbench_proxies",
        "version": 1,
        "proxy_dir": PROXY_DIRNAME,
        "built": built,
        "proxies": proxies,
    }
