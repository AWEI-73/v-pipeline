"""Execute a material rough_cut_plan.json into a review video candidate.

This is a bounded preview renderer for material-first review. It is not the
canonical final renderer: it only proves selected clips, timing, and optional
approved audio can be viewed together before the full BUILD/render route.
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


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, payload: dict[str, Any]):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _probe(path: Path) -> dict[str, Any]:
    result = subprocess.run(
        [
            resolve_ffprobe(),
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=codec_type,codec_name,width,height",
            "-of",
            "json",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    return {
        "duration_sec": _float((data.get("format") or {}).get("duration")),
        "streams": data.get("streams") or [],
    }


def _clips(payload: dict[str, Any]) -> list[dict[str, Any]]:
    clips = []
    for index, item in enumerate(payload.get("clips") or []):
        if not isinstance(item, dict) or item.get("track", "video") != "video":
            continue
        source = item.get("source_path")
        duration = _float(item.get("duration_sec"))
        start = _float(item.get("start_sec"))
        if not source:
            raise ValueError(f"clip {index} is missing source_path")
        if duration <= 0:
            raise ValueError(f"clip {index} duration_sec must be positive")
        path = Path(source)
        if not path.is_file():
            raise FileNotFoundError(f"clip {index} source does not exist: {path}")
        clips.append({
            "index": index,
            "source_path": str(path),
            "start_sec": start,
            "duration_sec": duration,
            "segment": item.get("segment"),
            "asset_id": item.get("asset_id"),
            "need_id": item.get("need_id"),
        })
    if not clips:
        raise ValueError("rough_cut_plan has no video clips")
    return clips


def _filtergraph(clips: list[dict[str, Any]], *, width: int, height: int) -> str:
    parts = []
    labels = []
    for index, clip in enumerate(clips):
        start = clip["start_sec"]
        end = start + clip["duration_sec"]
        label = f"v{index}"
        parts.append(
            f"[{index}:v]trim=start={start:.3f}:end={end:.3f},"
            "setpts=PTS-STARTPTS,"
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,"
            "setsar=1,"
            f"format=yuv420p[{label}]"
        )
        labels.append(f"[{label}]")
    parts.append("".join(labels) + f"concat=n={len(labels)}:v=1:a=0[v]")
    return ";".join(parts)


def execute_rough_cut_plan(
    plan_path: str | Path,
    out_path: str | Path,
    report_path: str | Path,
    *,
    audio_path: str | Path | None = None,
    width: int = 1280,
    height: int = 720,
) -> dict[str, Any]:
    plan = _load_json(Path(plan_path))
    clips = _clips(plan)
    out = Path(out_path)
    report = Path(report_path)
    audio = Path(audio_path) if audio_path else None
    if audio and not audio.is_file():
        raise FileNotFoundError(f"audio file does not exist: {audio}")

    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [resolve_ffmpeg(), "-y", "-hide_banner"]
    for clip in clips:
        cmd += ["-i", clip["source_path"]]
    if audio:
        cmd += ["-i", str(audio)]

    total_duration = round(sum(clip["duration_sec"] for clip in clips), 3)
    cmd += [
        "-filter_complex",
        _filtergraph(clips, width=width, height=height),
        "-map",
        "[v]",
    ]
    if audio:
        audio_index = len(clips)
        cmd += ["-map", f"{audio_index}:a:0", "-t", f"{total_duration:.3f}", "-shortest"]
    cmd += [
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
    ]
    if audio:
        cmd += ["-c:a", "aac", "-b:a", "160k"]
    cmd += ["-movflags", "+faststart", str(out)]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr)

    output_probe = _probe(out)
    payload = {
        "artifact_role": "rough_cut_preview_report",
        "version": 1,
        "ok": True,
        "source_artifact": str(plan_path),
        "output_video": str(out),
        "audio_file": str(audio) if audio else None,
        "clip_count": len(clips),
        "duration_sec": output_probe["duration_sec"],
        "planned_duration_sec": total_duration,
        "clips": clips,
        "streams": output_probe["streams"],
        "next_action": "human_review_or_final_product_verify",
    }
    _write_json(report, payload)
    return payload


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rough-cut-plan", required=True)
    parser.add_argument("--audio", default=None, help="optional approved final_audio.wav")
    parser.add_argument("--out", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    args = parser.parse_args(argv)

    payload = execute_rough_cut_plan(
        args.rough_cut_plan,
        args.out,
        args.report,
        audio_path=args.audio,
        width=args.width,
        height=args.height,
    )
    print(json.dumps({"ok": True, "output_video": payload["output_video"], "duration_sec": payload["duration_sec"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
