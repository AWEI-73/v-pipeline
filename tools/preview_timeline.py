#!/usr/bin/env python
"""Hermes-native preview_timeline builder.

This is *not* a Remotion adapter. It borrows the Remotion-like preview model
(fps / frame / duration / composition props / per-clip media timing) and emits a
single Hermes-native artifact -- ``preview_timeline.json`` -- that the native
workbench frontend consumes for *interactive* preview.

It never renders. ffmpeg BUILD stays canonical. This module only translates the
already-built editorial artifacts (``draft_timeline.json`` /
``preview_rough_cut_plan.json`` / ``timeline.json`` / ``timeline_build.json`` +
``project_material_map.json`` + ``review_subtitles.srt`` / ``subtitles.srt``)
into a browser-ready, seconds-first timeline state.

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

try:
    from tools import effect_patch as ep
except ImportError:  # pragma: no cover - direct-script fallback
    import effect_patch as ep

ARTIFACT_ROLE = "preview_timeline"
SCHEMA_VERSION = 1
DEFAULT_FPS = 30

VIDEO_EXTS = {".mp4", ".mov", ".webm", ".m4v", ".mkv"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}

# Editorial source artifacts, in priority order (first hit wins). Draft edits
# are highest priority; rough-cut preview plans are the reviewed candidate a
# Workbench user is usually revising, so they must win over dry/canonical build
# placeholders when both exist.
TIMELINE_CANDIDATES = (
    "draft_timeline.json",
    "preview_rough_cut_plan.json",
    "rough_cut_plan.json",
    "timeline.json",
    "timeline_build.json",
)


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


def _resolve_artifact_ref(root: Path, value: Any) -> Path:
    path = Path(str(value))
    if path.is_absolute():
        return path
    root_candidate = root / path
    if root_candidate.exists():
        return root_candidate
    cwd_candidate = Path.cwd() / path
    if cwd_candidate.exists():
        return cwd_candidate
    return root_candidate


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


def _build_effect_assets(material_map: Optional[Dict[str, Any]], base_url: str) -> List[Dict[str, Any]]:
    """Project-map effect library assets exposed to the Workbench."""
    if not isinstance(material_map, dict):
        return []
    out: List[Dict[str, Any]] = []
    for asset in material_map.get("assets", []) or []:
        if not isinstance(asset, dict):
            continue
        if asset.get("asset_type") not in ("effect_overlay", "motion_asset"):
            continue
        src = asset.get("source")
        aid = asset.get("asset_id")
        if not isinstance(src, str) or not src.strip() or not isinstance(aid, str) or not aid.strip():
            continue
        scene0 = ((asset.get("scenes") or [{}])[0] or {})
        out.append({
            "asset_id": aid,
            "asset_type": asset.get("asset_type"),
            "source_path": src,
            "src_url": path_to_url(str(Path(src).resolve()), base_url),
            "duration_sec": asset.get("duration_sec"),
            "visual_family": scene0.get("visual_family"),
        })
    return sorted(out, key=lambda a: a["asset_id"])


def _build_material_assets(material_map: Optional[Dict[str, Any]], base_url: str) -> List[Dict[str, Any]]:
    """Project-map main visual assets exposed to the Workbench browser.

    This is a projection for review/search/replacement. It is not a second
    material-map schema and it intentionally excludes effect/sfx-only assets.
    Replacement still re-resolves ``asset_id`` / ``scene_index`` from the
    canonical project material map on the Python side.
    """
    if not isinstance(material_map, dict):
        return []
    out: List[Dict[str, Any]] = []
    for asset in material_map.get("assets", []) or []:
        if not isinstance(asset, dict):
            continue
        atype = asset.get("asset_type")
        if atype not in ("video", "photo", "image"):
            continue
        src = asset.get("source")
        aid = asset.get("asset_id")
        if not isinstance(src, str) or not src.strip() or not isinstance(aid, str) or not aid.strip():
            continue
        scenes = asset.get("scenes") if isinstance(asset.get("scenes"), list) else []
        scene0 = scenes[0] if scenes and isinstance(scenes[0], dict) else {}
        projected_scenes: List[Dict[str, Any]] = []
        for scene_index, scene in enumerate(scenes):
            if not isinstance(scene, dict):
                continue
            satisfies = [
                item for item in (scene.get("satisfies") or [])
                if isinstance(item, dict) and item.get("need_id")
            ]
            need_ids = [
                str(item.get("need_id")) for item in satisfies
                if isinstance(item.get("need_id"), str)
            ]
            statuses = [
                str(item.get("status") or "candidate") for item in satisfies
            ]
            start = scene.get("start")
            end = scene.get("end")
            projected_scenes.append({
                "scene_index": scene_index,
                "start_sec": start,
                "end_sec": end,
                "satisfies": satisfies,
                "need_ids": need_ids,
                "statuses": statuses,
                "visual_family": scene.get("visual_family"),
                "angle_scale": scene.get("angle_scale"),
                "action_family": scene.get("action_family"),
                "subject": scene.get("subject"),
                "caption": scene.get("caption"),
            })
        out.append({
            "asset_id": aid,
            "asset_type": atype,
            "source_path": src,
            "src_url": path_to_url(str(Path(src).resolve()), base_url),
            "duration_sec": asset.get("duration_sec"),
            "scene_count": len(scenes),
            "visual_family": scene0.get("visual_family"),
            "angle_scale": scene0.get("angle_scale"),
            "action_family": scene0.get("action_family"),
            "subject": scene0.get("subject"),
            "caption": scene0.get("caption"),
            "scenes": projected_scenes,
        })
    return sorted(out, key=lambda a: a["asset_id"])


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
    include_effect_patch: bool = True,
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
    material_map = material_map if isinstance(material_map, dict) else None
    asset_index = _build_asset_index(material_map)
    effect_assets = _build_effect_assets(material_map, base_url)
    material_assets = _build_material_assets(material_map, base_url)

    # Order clips deterministically by slot_index (stable for equal/missing).
    ordered = sorted(
        list(enumerate(plan)),
        key=lambda pair: (pair[1].get("slot_index", pair[0]), pair[0]),
    )

    clips: List[Dict[str, Any]] = []
    durations: List[float] = []
    for fallback_idx, (_, raw) in enumerate(ordered):
        slot_index = raw.get("slot_index", fallback_idx)
        source_path = raw.get("source") or raw.get("source_path")
        asset = _asset_for(source_path, asset_index)
        clip_type = classify_clip_type(source_path, asset.get("asset_type"))

        duration_sec = float(raw.get("slot_dur") or raw.get("extract_dur") or raw.get("duration_sec") or 0.0)
        if clip_type == "video":
            source_start_sec = float(raw.get("extract_start") or raw.get("start_sec") or 0.0)
            source_duration_sec = float(raw.get("extract_dur") or raw.get("duration_sec") or duration_sec or 0.0)
        else:
            source_start_sec = 0.0
            source_duration_sec = float(raw.get("extract_dur") or raw.get("duration_sec") or duration_sec or 0.0)

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
            "timeline_start_sec": float(raw.get("timeline_in_sec") or 0.0),
            "duration_sec": round(duration_sec, 3),
            "source_start_sec": round(source_start_sec, 3),
            "source_duration_sec": round(source_duration_sec, 3),
            "source_asset_duration_sec": asset.get("duration_sec"),
            "scene_id": raw.get("scene_id"),
            "need_id": raw.get("need_id") or raw.get("need_ref"),
            "visual_family": raw.get("visual_family"),
            "angle_scale": raw.get("angle_scale"),
            "caption": raw.get("caption"),
            "status": status,
        })

    starts = compute_timeline_starts(durations)
    for clip, start in zip(clips, starts):
        if not clip.get("timeline_start_sec"):
            clip["timeline_start_sec"] = start

    total_duration = round(sum(durations), 3)

    # Subtitles (SRT -> overlay).
    subtitles: List[Dict[str, Any]] = []
    srt_path = next((root / name for name in ("review_subtitles.srt", "subtitles.srt")
                     if (root / name).is_file()), None)
    if srt_path is not None:
        try:
            subtitles = parse_srt(srt_path.read_text(encoding="utf-8"))
        except OSError:
            diagnostics.append({
                "level": "warning",
                "code": "srt_unreadable",
                "message": f"{srt_path.name} present but could not be read.",
            })

    # Track summaries (audio/effect are first-version markers only).
    video_track = [c["id"] for c in clips]
    subtitle_track = [s["id"] for s in subtitles]

    audio: List[Dict[str, Any]] = []
    audio_mix_report = _load_json(root / "audio_mix_report.json")
    if isinstance(audio_mix_report, dict):
        output_audio = audio_mix_report.get("output_audio")
        output_audio_path = _resolve_artifact_ref(root, output_audio) if output_audio else root / "final_audio.wav"
        source_audio_policy = audio_mix_report.get("source_audio_policy")
        placements = audio_mix_report.get("placements") if isinstance(audio_mix_report.get("placements"), list) else []
        if output_audio_path.is_file() and placements:
            for placement in placements:
                if not isinstance(placement, dict):
                    continue
                audio.append({
                    "id": f"audio-{len(audio) + 1}",
                    "label": placement.get("section_id") or placement.get("role") or "audio_mix",
                    "src_url": path_to_url(str(output_audio_path.resolve()), base_url),
                    "source_path": str(output_audio_path),
                    "section_id": placement.get("section_id"),
                    "role": placement.get("role"),
                    "ducking_policy": placement.get("ducking_policy"),
                    "ducking_applied": bool(placement.get("ducking_applied")),
                    "start_sec": float(placement.get("start_sec") or 0.0),
                    "duration_sec": float(placement.get("duration_sec") or total_duration),
                    "source_start_sec": float(placement.get("start_sec") or 0.0),
                    "marker_only": False,
                    "source_audio_policy": source_audio_policy if isinstance(source_audio_policy, dict) else {},
                })
        elif output_audio_path.is_file():
            audio.append({
                "id": "audio-1",
                "label": "final_audio",
                "src_url": path_to_url(str(output_audio_path.resolve()), base_url),
                "source_path": str(output_audio_path),
                "start_sec": 0.0,
                "duration_sec": total_duration,
                "source_start_sec": 0.0,
                "marker_only": False,
                "source_audio_policy": source_audio_policy if isinstance(source_audio_policy, dict) else {},
            })

    if not audio:
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

    effect_patch_path = root / "effect_patch.json"
    if include_effect_patch and effect_patch_path.is_file():
        try:
            patch = json.loads(effect_patch_path.read_text(encoding="utf-8"))
            draft = ep.apply_effect_patch(str(root), patch)
            for effect in draft.get("effects", []):
                item = dict(effect)
                item["id"] = item.get("effect_id")
                item["marker_only"] = False
                effects.append(item)
        except (OSError, TypeError, ValueError) as exc:
            diagnostics.append({
                "level": "warning",
                "code": "effect_patch_unreadable",
                "message": f"effect_patch.json present but could not be applied: {exc}",
            })

    effect_intent_plan = _load_json(root / "effect_intent_plan.json")
    effect_render_verification = _load_json(root / "effect_render_verification.json")
    verified_by_id: Dict[str, Dict[str, Any]] = {}
    if isinstance(effect_render_verification, dict):
        for item in effect_render_verification.get("verified_effects") or []:
            if isinstance(item, dict) and item.get("effect_id"):
                verified_by_id[str(item["effect_id"])] = item
    if isinstance(effect_intent_plan, dict):
        for raw in effect_intent_plan.get("effects") or []:
            if not isinstance(raw, dict):
                continue
            effect_id = raw.get("effect_id")
            if not effect_id or any(item.get("id") == effect_id for item in effects):
                continue
            verified = verified_by_id.get(str(effect_id), {})
            effects.append({
                "id": str(effect_id),
                "effect_id": str(effect_id),
                "label": raw.get("role") or raw.get("type") or str(effect_id),
                "role": raw.get("role"),
                "type": raw.get("type"),
                "story_function": raw.get("story_function"),
                "required_for_story": bool(raw.get("required_for_story", raw.get("render_required", False))),
                "rendered": verified.get("rendered") is True,
                "evidence_refs": verified.get("evidence_refs") or verified.get("sampled_frames") or [],
                "start_sec": float(raw.get("start_sec") or 0.0),
                "duration_sec": float(raw.get("duration_sec") or total_duration),
                "marker_only": True,
                "source": "effect_intent_plan",
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
        "effect_assets": effect_assets,
        "material_assets": material_assets,
        "diagnostics": diagnostics,
    }


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
# Canonical artifacts the build CLI must never overwrite (defence-in-depth; the
# server path never writes here, but the CLI accepts an arbitrary --out).
_PROTECTED_OUTPUTS = {
    "timeline.json", "draft_timeline.json", "segment_contract.json",
    "revised_segment_contract.json", "project_material_map.json",
    "material_needs.json", "final.mp4", "review_report.json", "delivery_gate.json",
}


def _cmd_build(args: argparse.Namespace) -> int:
    if os.path.basename(str(args.out)) in _PROTECTED_OUTPUTS:
        print(f"[preview_timeline] refusing to overwrite canonical artifact: {args.out}")
        return 2
    preview = build_preview_timeline(args.artifact_root, args.base_url, fps=args.fps)
    out_path = Path(args.out)
    if not out_path.is_absolute():
        root_path = Path(args.artifact_root)
        root_abs = root_path.resolve()
        out_abs = (Path.cwd() / out_path).resolve()
        try:
            out_abs.relative_to(root_abs)
            out_path = out_abs
        except ValueError:
            out_path = root_path / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
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
