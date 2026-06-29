"""Safe highlight cutter for precise multi-window video cuts.

This tool is intentionally conservative: it re-encodes with a filtergraph
instead of stream-copying cuts. That avoids non-keyframe boundary stutter from
yt-dlp / VP9 / Opus / WebM-style sources.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from video_pipeline_core.platform_tools import resolve_ffmpeg, resolve_ffprobe  # noqa: E402


def _load_windows(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    windows = payload.get("windows") if isinstance(payload, dict) else payload
    if not isinstance(windows, list) or not windows:
        raise ValueError("windows must be a non-empty list or {windows:[...]}")
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(windows):
        if not isinstance(item, dict):
            raise ValueError(f"window {index} must be an object")
        start = item.get("start")
        end = item.get("end")
        if isinstance(start, bool) or isinstance(end, bool) or not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
            raise ValueError(f"window {index} start/end must be numbers")
        if end <= start:
            raise ValueError(f"window {index} end must be greater than start")
        normalized.append({
            "index": index,
            "start": float(start),
            "end": float(end),
            "duration_sec": float(end) - float(start),
            "label": str(item.get("label") or f"window_{index + 1}"),
        })
    return normalized


def _load_rough_cut_plan(path: Path) -> tuple[Path, list[dict[str, Any]]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    clips = payload.get("clips") or []
    if not isinstance(clips, list) or not clips:
        raise ValueError("rough_cut_plan clips must be a non-empty list")

    source_paths: set[Path] = set()
    windows: list[dict[str, Any]] = []
    for item in clips:
        if not isinstance(item, dict) or item.get("track", "video") != "video":
            continue
        source_path = item.get("source_path")
        start = item.get("source_in_sec")
        end = item.get("source_out_sec")
        if start is None or end is None:
            start = item.get("start_sec")
            duration = item.get("duration_sec")
            if isinstance(start, (int, float)) and not isinstance(start, bool) and isinstance(duration, (int, float)) and not isinstance(duration, bool):
                end = float(start) + float(duration)
        if not source_path:
            raise ValueError("rough_cut_plan video clip is missing source_path")
        if isinstance(start, bool) or isinstance(end, bool) or not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
            raise ValueError("rough_cut_plan video clip source_in_sec/source_out_sec or start_sec/duration_sec must be numbers")
        if end <= start:
            raise ValueError("rough_cut_plan video clip source_out_sec must be greater than source_in_sec")
        source_paths.add(Path(source_path).resolve())
        windows.append({
            "index": len(windows),
            "start": float(start),
            "end": float(end),
            "duration_sec": float(end) - float(start),
            "label": str(item.get("segment_id") or item.get("segment") or item.get("role") or f"window_{len(windows) + 1}"),
        })

    if not windows:
        raise ValueError("rough_cut_plan has no video clips")
    if len(source_paths) != 1:
        raise ValueError("safe_highlight_cut rough-cut mode supports one source video; use a multi-clip preset instead")
    return next(iter(source_paths)), windows


def _probe(path: Path) -> dict[str, Any]:
    result = subprocess.run([
        resolve_ffprobe(),
        "-v", "error",
        "-show_entries", "format=duration:stream=codec_name,codec_type,width,height,r_frame_rate",
        "-of", "json",
        str(path),
    ], check=True, capture_output=True, text=True)
    data = json.loads(result.stdout)
    streams = data.get("streams") or []
    video = next((item for item in streams if item.get("codec_type") == "video"), {})
    audio = next((item for item in streams if item.get("codec_type") == "audio"), {})
    duration = float((data.get("format") or {}).get("duration") or 0)
    return {"duration_sec": duration, "video": video, "audio": audio}


def _build_filter(windows: list[dict[str, Any]], *, has_audio: bool) -> tuple[str, list[str]]:
    parts: list[str] = []
    labels: list[str] = []
    for index, window in enumerate(windows):
        start = window["start"]
        end = window["end"]
        parts.append(f"[0:v]trim=start={start}:end={end},setpts=PTS-STARTPTS[v{index}]")
        labels.append(f"[v{index}]")
        if has_audio:
            parts.append(f"[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[a{index}]")
            labels.append(f"[a{index}]")
    if has_audio:
        parts.append("".join(labels) + f"concat=n={len(windows)}:v=1:a=1[v][a]")
        maps = ["[v]", "[a]"]
    else:
        parts.append("".join(labels) + f"concat=n={len(windows)}:v=1:a=0[v]")
        maps = ["[v]"]
    return ";".join(parts), maps


def cut_highlight(source: Path, windows_path: Path, out: Path, report: Path) -> dict[str, Any]:
    source = source.resolve()
    out = out.resolve()
    report = report.resolve()
    windows = _load_windows(windows_path)
    return _cut_highlight_windows(
        source,
        windows,
        out,
        report,
        source_artifact="windows",
        source_artifact_path=windows_path,
    )


def cut_highlight_from_rough_cut(rough_cut_plan: Path, out: Path, report: Path) -> dict[str, Any]:
    source, windows = _load_rough_cut_plan(rough_cut_plan)
    return _cut_highlight_windows(
        source,
        windows,
        out,
        report,
        source_artifact="rough_cut_plan",
        source_artifact_path=rough_cut_plan,
    )


def _cut_highlight_windows(
    source: Path,
    windows: list[dict[str, Any]],
    out: Path,
    report: Path,
    *,
    source_artifact: str,
    source_artifact_path: Path,
) -> dict[str, Any]:
    source = source.resolve()
    out = out.resolve()
    report = report.resolve()
    source_probe = _probe(source)
    has_audio = bool(source_probe.get("audio"))
    filtergraph, maps = _build_filter(windows, has_audio=has_audio)

    out.parent.mkdir(parents=True, exist_ok=True)
    report.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        resolve_ffmpeg(),
        "-y",
        "-hide_banner",
        "-i", str(source),
        "-filter_complex", filtergraph,
        "-map", maps[0],
    ]
    if has_audio:
        cmd += ["-map", maps[1]]
    cmd += [
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
    ]
    if has_audio:
        cmd += ["-c:a", "aac", "-b:a", "160k"]
    cmd += ["-movflags", "+faststart", str(out)]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr)

    output_probe = _probe(out)
    payload = {
        "artifact_role": "highlight_cut_report",
        "version": 1,
        "cut_mode": "reencode_filtergraph",
        "strategy": "safe_reencode_highlight",
        "stream_copy": False,
        "source_artifact": source_artifact,
        "source_artifact_path": str(Path(source_artifact_path).resolve()),
        "source": str(source),
        "out": str(out),
        "window_count": len(windows),
        "windows": windows,
        "duration_sec": output_probe["duration_sec"],
        "source_probe": source_probe,
        "output_probe": output_probe,
        "ffmpeg": {
            "video_codec": "libx264",
            "audio_codec": "aac" if has_audio else None,
            "pixel_format": "yuv420p",
            "movflags": "+faststart",
        },
    }
    report.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Safe re-encoded highlight cutter")
    parser.add_argument("--source", help="source video")
    parser.add_argument("--windows", help="JSON list or {windows:[...]}")
    parser.add_argument("--rough-cut-plan", help="single-source rough_cut_plan.json")
    parser.add_argument("--out", required=True, help="output mp4")
    parser.add_argument("--report", required=True, help="highlight_cut_report.json")
    args = parser.parse_args()
    if args.rough_cut_plan:
        if args.source or args.windows:
            parser.error("--rough-cut-plan cannot be combined with --source/--windows")
        payload = cut_highlight_from_rough_cut(Path(args.rough_cut_plan), Path(args.out), Path(args.report))
    else:
        if not args.source or not args.windows:
            parser.error("--source and --windows are required unless --rough-cut-plan is provided")
        payload = cut_highlight(Path(args.source), Path(args.windows), Path(args.out), Path(args.report))
    print(json.dumps({
        "ok": True,
        "out": payload["out"],
        "report": str(Path(args.report).resolve()),
        "duration_sec": payload["duration_sec"],
        "cut_mode": payload["cut_mode"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
