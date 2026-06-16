#!/usr/bin/env python
"""Hermes-native preview_timeline builder.

This is *not* a Remotion adapter. It borrows the Remotion-like preview model
(fps / frame / duration / composition props / per-clip media timing) and emits a
single Hermes-native artifact -- ``preview_timeline.json`` -- that the native
workbench frontend consumes for *interactive* preview.

It never renders. ffmpeg BUILD stays canonical. This module only translates the
already-built editorial artifacts (``timeline.json`` / ``draft_timeline.json`` +
``project_material_map.json`` + ``review_subtitles.srt``) into a browser-ready,
seconds-first timeline state.

CLI::

    python tools/preview_timeline.py build \
        --artifact-root <root> \
        --base-url http://localhost:<port> \
        --out preview_timeline.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ARTIFACT_ROLE = "preview_timeline"
SCHEMA_VERSION = 1
DEFAULT_FPS = 30

VIDEO_EXTS = {".mp4", ".mov", ".webm", ".m4v", ".mkv"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}

# Editorial source artifacts, in priority order (first hit wins).
TIMELINE_CANDIDATES = ("draft_timeline.json", "timeline.json")


# --------------------------------------------------------------------------- #
# Pure helpers (unit-tested directly)
# --------------------------------------------------------------------------- #
def classify_clip_type(source_path: Optional[str], asset_type: Optional[str] = None) -> str:
    """Return ``"image"`` or ``"video"`` for a clip source.

    Material-map ``asset_type`` wins when present; otherwise we fall back to the
    file extension. Unknown extensions default to ``video`` (the editorial
    pipeline treats stills explicitly, so an unknown is more likely a clip).
    """
    if asset_type:
        at = asset_type.strip().lower()
        if at in ("image", "video"):
            return at
    ext = os.path.splitext(source_path or "")[1].lower()
    if ext in IMAGE_EXTS:
        return "image"
    if ext in VIDEO_EXTS:
        return "video"
    return "video"


def path_to_url(source_path: Optional[str], base_url: str) -> Optional[str]:
    """Convert an absolute (often Windows) source path into a browser-safe URL.

    The workbench server exposes a single ``/media`` resolver that gates reads
    against the preview_timeline allow-list, so we never embed a raw filesystem
    path into ``src_url``. The path is URL-encoded as a query parameter, which
    escapes ``\\`` and ``:`` so no literal Windows path leaks into the document.
    """
    if not source_path:
        return None
    base = (base_url or "").rstrip("/")
    encoded = urllib.parse.quote(str(source_path), safe="")
    return f"{base}/media?src={encoded}"


def seconds_to_frame(seconds: float, fps: int = DEFAULT_FPS) -> int:
    """Round seconds to the nearest whole frame (preview math stays in seconds)."""
    return int(round(float(seconds) * int(fps)))


def compute_timeline_starts(durations: List[float]) -> List[float]:
    """Deterministic cumulative start times from an ordered duration list."""
    starts: List[float] = []
    acc = 0.0
    for d in durations:
        starts.append(round(acc, 6))
        acc += float(d or 0.0)
    return starts


def parse_srt(text: str) -> List[Dict[str, Any]]:
    """Parse SRT content into ``{id,text,start_sec,duration_sec}`` overlays."""
    subs: List[Dict[str, Any]] = []
    blocks = re.split(r"\n\s*\n", text.strip().replace("\r\n", "\n"))
    for block in blocks:
        lines = [ln for ln in block.split("\n") if ln.strip() != ""]
        if len(lines) < 2:
            continue
        # Optional numeric index line.
        idx = 0
        if re.fullmatch(r"\d+", lines[0].strip()):
            idx = 1
        if idx >= len(lines):
            continue
        m = re.search(
            r"(\d{2}):(\d{2}):(\d{2})[,.](\d{1,3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{1,3})",
            lines[idx],
        )
        if not m:
            continue
        g = list(map(int, m.groups()))
        start = g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000.0
        end = g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000.0
        body = " ".join(lines[idx + 1:]).strip()
        subs.append({
            "id": f"sub-{len(subs) + 1}",
            "text": body,
            "start_sec": round(start, 3),
            "duration_sec": round(max(0.0, end - start), 3),
        })
    return subs


# --------------------------------------------------------------------------- #
# Artifact loading
# --------------------------------------------------------------------------- #
def _load_json(path: Path) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _resolve_timeline(root: Path) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    for name in TIMELINE_CANDIDATES:
        p = root / name
        if p.is_file():
            data = _load_json(p)
            if isinstance(data, dict):
                return data, name
    return None, None


def _build_asset_index(material_map: Optional[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Map normalized source path -> {asset_type, duration_sec}."""
    index: Dict[str, Dict[str, Any]] = {}
    if not isinstance(material_map, dict):
        return index
    for asset in material_map.get("assets", []) or []:
        src = asset.get("source")
        if not src:
            continue
        key = os.path.normcase(os.path.normpath(str(src)))
        index[key] = {
            "asset_type": asset.get("asset_type"),
            "duration_sec": asset.get("duration_sec"),
        }
    return index


def _asset_for(source_path: Optional[str], index: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    if not source_path:
        return {}
    return index.get(os.path.normcase(os.path.normpath(str(source_path))), {})


# --------------------------------------------------------------------------- #
# Build
# --------------------------------------------------------------------------- #
def build_preview_timeline(
    artifact_root: str,
    base_url: str,
    fps: int = DEFAULT_FPS,
) -> Dict[str, Any]:
    """Translate editorial artifacts into a preview_timeline contract dict.

    Pure with respect to the filesystem read side -- it never writes, and never
    touches ``timeline.json`` itself.
    """
    root = Path(artifact_root)
    diagnostics: List[Dict[str, Any]] = []

    timeline, timeline_source = _resolve_timeline(root)
    if timeline is None:
        diagnostics.append({
            "level": "error",
            "code": "no_timeline",
            "message": "No draft_timeline.json or timeline.json found under artifact root.",
        })
        plan: List[Dict[str, Any]] = []
    else:
        plan = timeline.get("plan") or timeline.get("clips") or []

    material_map = _load_json(root / "project_material_map.json")
    asset_index = _build_asset_index(material_map if isinstance(material_map, dict) else None)

    # Order clips deterministically by slot_index (stable for equal/missing).
    ordered = sorted(
        list(enumerate(plan)),
        key=lambda pair: (pair[1].get("slot_index", pair[0]), pair[0]),
    )

    clips: List[Dict[str, Any]] = []
    durations: List[float] = []
    for fallback_idx, (_, raw) in enumerate(ordered):
        slot_index = raw.get("slot_index", fallback_idx)
        source_path = raw.get("source")
        asset = _asset_for(source_path, asset_index)
        clip_type = classify_clip_type(source_path, asset.get("asset_type"))

        duration_sec = float(raw.get("slot_dur") or raw.get("extract_dur") or 0.0)
        if clip_type == "video":
            source_start_sec = float(raw.get("extract_start") or 0.0)
            source_duration_sec = float(raw.get("extract_dur") or duration_sec or 0.0)
        else:
            source_start_sec = 0.0
            source_duration_sec = float(raw.get("extract_dur") or duration_sec or 0.0)

        status = "matched"
        if not source_path:
            status = "gap"
            diagnostics.append({
                "level": "warning",
                "code": "missing_source",
                "slot_index": slot_index,
                "message": f"Slot {slot_index} has no source path.",
            })
        elif not Path(source_path).exists():
            status = "render_failed"
            diagnostics.append({
                "level": "warning",
                "code": "source_not_found",
                "slot_index": slot_index,
                "message": f"Slot {slot_index} source does not exist: {source_path}",
            })

        durations.append(duration_sec)
        clips.append({
            "id": f"slot-{slot_index}",
            "slot_index": slot_index,
            "segment": raw.get("segment"),
            "type": clip_type,
            "src_url": path_to_url(source_path, base_url),
            "source_path": source_path,
            "timeline_start_sec": 0.0,  # filled below
            "duration_sec": round(duration_sec, 3),
            "source_start_sec": round(source_start_sec, 3),
            "source_duration_sec": round(source_duration_sec, 3),
            "scene_id": raw.get("scene_id"),
            "need_id": raw.get("need_id"),
            "visual_family": raw.get("visual_family"),
            "angle_scale": raw.get("angle_scale"),
            "caption": raw.get("caption"),
            "status": status,
        })

    starts = compute_timeline_starts(durations)
    for clip, start in zip(clips, starts):
        clip["timeline_start_sec"] = start

    total_duration = round(sum(durations), 3)

    # Subtitles (SRT -> overlay).
    subtitles: List[Dict[str, Any]] = []
    srt_path = root / "review_subtitles.srt"
    if srt_path.is_file():
        try:
            subtitles = parse_srt(srt_path.read_text(encoding="utf-8"))
        except OSError:
            diagnostics.append({
                "level": "warning",
                "code": "srt_unreadable",
                "message": "review_subtitles.srt present but could not be read.",
            })

    # Track summaries (audio/effect are first-version markers only).
    video_track = [c["id"] for c in clips]
    subtitle_track = [s["id"] for s in subtitles]

    audio: List[Dict[str, Any]] = []
    for name in ("music.wav", "bgm.webm", "narration.wav", "voiceover.wav"):
        if (root / name).is_file():
            audio.append({
                "id": f"audio-{len(audio) + 1}",
                "label": name,
                "src_url": path_to_url(str((root / name).resolve()), base_url),
                "start_sec": 0.0,
                "duration_sec": total_duration,
                "marker_only": True,
            })

    effects: List[Dict[str, Any]] = []
    for clip in clips:
        if clip["type"] == "image":
            effects.append({
                "id": f"fx-{clip['slot_index']}",
                "label": "still_treatment",
                "slot_index": clip["slot_index"],
                "start_sec": clip["timeline_start_sec"],
                "duration_sec": clip["duration_sec"],
                "marker_only": True,
            })

    return {
        "artifact_role": ARTIFACT_ROLE,
        "version": SCHEMA_VERSION,
        "fps": int(fps),
        "duration_sec": total_duration,
        "duration_frames": seconds_to_frame(total_duration, fps),
        "source_artifact": timeline_source,
        "tracks": {
            "video": video_track,
            "subtitle": subtitle_track,
            "audio": [a["id"] for a in audio],
            "effect": [e["id"] for e in effects],
        },
        "clips": clips,
        "subtitles": subtitles,
        "audio": audio,
        "effects": effects,
        "diagnostics": diagnostics,
    }


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _cmd_build(args: argparse.Namespace) -> int:
    preview = build_preview_timeline(args.artifact_root, args.base_url, fps=args.fps)
    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = Path(args.artifact_root) / out_path
    out_path.write_text(
        json.dumps(preview, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    errors = [d for d in preview["diagnostics"] if d.get("level") == "error"]
    print(
        f"[preview_timeline] wrote {out_path} "
        f"({len(preview['clips'])} clips, {len(preview['subtitles'])} subtitles, "
        f"{len(preview['diagnostics'])} diagnostics)"
    )
    return 1 if errors else 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Hermes-native preview_timeline builder")
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build", help="Build preview_timeline.json from editorial artifacts")
    build.add_argument("--artifact-root", required=True)
    build.add_argument("--base-url", default="http://localhost:8770")
    build.add_argument("--out", default="preview_timeline.json")
    build.add_argument("--fps", type=int, default=DEFAULT_FPS)
    build.set_defaults(func=_cmd_build)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
