"""Deterministic material-first render handoff execution."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from .asset_paths import is_absolute_path_string
from .material_rough_cut import write_json
from .platform_tools import resolve_ffmpeg, resolve_ffprobe


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _block(root: Path, rule: str, message: str, **extra) -> dict[str, Any]:
    report = {
        "artifact_role": "material_first_final_artifact_acceptance",
        "version": 1,
        "route": "material-first",
        "ok": False,
        "next_action": "blocked",
        "final_delivery_claimed": False,
        "blocking": [{"rule": rule, "message": message, **extra}],
    }
    write_json(root / "material_first_final_artifact_acceptance.json", report)
    return report


def _timeline_refs(handoff: dict[str, Any]) -> list[dict[str, Any]]:
    refs = []
    for item in handoff.get("timeline_refs") or []:
        ref = str(item.get("source_path") or "")
        if ref:
            refs.append(item)
    return refs


def _resolve_render_inputs(root: Path, handoff: dict[str, Any]) -> tuple[list[tuple[str, Path, float]], list[dict[str, Any]]]:
    inputs: list[tuple[str, Path, float]] = []
    blocking: list[dict[str, Any]] = []
    for item in _timeline_refs(handoff):
        ref = str(item.get("source_path") or "")
        if is_absolute_path_string(ref) or not ref.startswith("assets/materials/"):
            blocking.append({
                "rule": "non_run_local_render_ref",
                "message": "material-first render requires run-local asset store refs from render_handoff.json",
                "asset_ref": ref,
            })
            continue
        path = root / ref
        if not path.is_file():
            blocking.append({
                "rule": "missing_render_input",
                "message": "render_handoff.json references a missing run-local asset",
                "asset_ref": ref,
            })
            continue
        duration = item.get("duration_sec")
        try:
            duration_sec = max(0.25, float(duration))
        except (TypeError, ValueError):
            duration_sec = 1.0
        inputs.append((ref, path, duration_sec))
    if not inputs and not blocking:
        blocking.append({
            "rule": "missing_render_handoff_refs",
            "message": "render_handoff.json must contain timeline_refs with source_path values",
        })
    return inputs, blocking


def _render_mp4(inputs: list[tuple[str, Path, float]], final_mp4: Path, ffmpeg: str) -> None:
    command = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error"]
    filter_parts = []
    labels = []
    for index, (_ref, path, duration_sec) in enumerate(inputs):
        command.extend(["-loop", "1", "-t", f"{duration_sec:.3f}", "-i", str(path)])
        label = f"v{index}"
        filter_parts.append(
            f"[{index}:v]scale=320:180:force_original_aspect_ratio=decrease,"
            f"pad=320:180:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=24[{label}]"
        )
        labels.append(f"[{label}]")
    filter_parts.append(f"{''.join(labels)}concat=n={len(inputs)}:v=1:a=0,format=yuv420p[outv]")
    command.extend([
        "-filter_complex",
        ";".join(filter_parts),
        "-map",
        "[outv]",
        "-an",
        "-movflags",
        "+faststart",
        str(final_mp4),
    ])
    result = subprocess.run(command, text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "ffmpeg failed").strip())


def probe_final_mp4(final_mp4: str | Path, *, ffprobe: str | None = None) -> dict[str, Any]:
    probe_bin = ffprobe or resolve_ffprobe()
    result = subprocess.run(
        [
            probe_bin,
            "-v",
            "error",
            "-show_entries",
            "stream=codec_type,codec_name,width,height,duration",
            "-of",
            "json",
            str(final_mp4),
        ],
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        return {
            "ok": False,
            "error": (result.stderr or result.stdout or "ffprobe failed").strip(),
            "streams": [],
            "video_stream_count": 0,
        }
    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError as exc:
        return {"ok": False, "error": f"ffprobe returned invalid json: {exc}", "streams": [], "video_stream_count": 0}
    streams = payload.get("streams") or []
    video_streams = [stream for stream in streams if stream.get("codec_type") == "video"]
    return {
        "ok": bool(video_streams),
        "streams": streams,
        "video_stream_count": len(video_streams),
    }


def render_material_first_handoff(run_dir: str | Path) -> dict[str, Any]:
    """Render ``render_handoff.json`` to run-local ``final.mp4`` and probe it."""

    root = Path(run_dir).resolve()
    handoff_path = root / "render_handoff.json"
    if not handoff_path.exists():
        return _block(root, "missing_render_handoff", "render_handoff.json is required before actual render")
    handoff = _load_json(handoff_path)
    if handoff.get("ok") is not True:
        return _block(root, "render_handoff_not_ready", "render_handoff.json must be ok=true before actual render")

    inputs, blocking = _resolve_render_inputs(root, handoff)
    if blocking:
        report = {
            "artifact_role": "material_first_final_artifact_acceptance",
            "version": 1,
            "route": "material-first",
            "ok": False,
            "next_action": "blocked",
            "final_delivery_claimed": False,
            "render_handoff": "render_handoff.json",
            "input_refs": [ref for ref, _path, _duration in inputs],
            "blocking": blocking,
        }
        write_json(root / "material_first_final_artifact_acceptance.json", report)
        return report

    final_mp4 = root / "final.mp4"
    try:
        _render_mp4(inputs, final_mp4, resolve_ffmpeg())
    except RuntimeError as exc:
        return _block(root, "ffmpeg_render_failed", "ffmpeg failed to render material-first final.mp4", error=str(exc))

    probe = probe_final_mp4(final_mp4)
    ok = bool(final_mp4.is_file() and probe.get("ok"))
    report = {
        "artifact_role": "material_first_final_artifact_acceptance",
        "version": 1,
        "route": "material-first",
        "ok": ok,
        "next_action": "ready_for_delivery_gate" if ok else "blocked",
        "final_delivery_claimed": False,
        "render_handoff": "render_handoff.json",
        "final_mp4_ref": "final.mp4",
        "input_refs": [ref for ref, _path, _duration in inputs],
        "ffprobe": probe,
        "blocking": [] if ok else [{
            "rule": "ffprobe_video_stream_missing",
            "message": "ffprobe did not find a playable video stream in final.mp4",
        }],
    }
    write_json(root / "material_first_final_artifact_acceptance.json", report)
    return report
