#!/usr/bin/env python
"""Assemble a final video stream with the selected pipeline audio.

This tool is intentionally small: it codifies the last ffmpeg glue used by the
pipeline after visual BUILD and audio arrangement have both produced bounded
artifacts. It does not choose clips or music.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


def _escape_drawtext(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def parse_label(value: str) -> dict[str, Any]:
    parts = value.split(":", 2)
    if len(parts) != 3:
        raise argparse.ArgumentTypeError("--label must be start:end:text")
    try:
        start = float(parts[0])
        end = float(parts[1])
    except ValueError as exc:
        raise argparse.ArgumentTypeError("--label start/end must be numbers") from exc
    if end <= start:
        raise argparse.ArgumentTypeError("--label end must be greater than start")
    return {"start_sec": start, "end_sec": end, "text": parts[2]}


def build_video_filter(*, title: str | None = None, labels: list[dict[str, Any]] | None = None,
                       effects: bool = True) -> str:
    filters = ["scale=1280:720", "format=yuv420p"]
    if effects:
        filters.extend([
            "eq=contrast=1.07:saturation=1.08:brightness=0.015",
            "vignette=PI/6",
            "drawbox=x=0:y=0:w=iw:h=ih:color=black@0.08:t=fill",
        ])
    if title:
        filters.append("drawbox=x=0:y=0:w=iw:h=70:color=black@0.35:t=fill")
        filters.append(
            "drawtext=text='{}':x=40:y=24:fontsize=28:fontcolor=white:"
            "box=1:boxcolor=black@0.35:enable='between(t,0,5)'".format(_escape_drawtext(title))
        )
    for label in labels or []:
        text = _escape_drawtext(str(label.get("text") or "SECTION"))
        start = float(label["start_sec"])
        end = float(label["end_sec"])
        filters.append(
            "drawtext=text='{}':x=40:y=h-62:fontsize=24:fontcolor=white:"
            "box=1:boxcolor=black@0.35:enable='between(t,{:.3f},{:.3f})'".format(text, start, end)
        )
    return ",".join(filters)


def assemble_final_av(
    *,
    video: str | Path,
    audio: str | Path,
    out: str | Path,
    report: str | Path | None = None,
    title: str | None = None,
    labels: list[dict[str, Any]] | None = None,
    source_audio_policy: str = "replace_with_music",
    effects: bool = True,
    ffmpeg: str = "ffmpeg",
) -> dict[str, Any]:
    video_path = Path(video)
    audio_path = Path(audio)
    out_path = Path(out)
    if not video_path.is_file():
        raise FileNotFoundError(video_path)
    if not audio_path.is_file():
        raise FileNotFoundError(audio_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    video_filter = build_video_filter(title=title, labels=labels, effects=effects)
    cmd = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-i", str(video_path),
        "-i", str(audio_path),
        "-filter_complex", f"[0:v]{video_filter}[v]",
        "-map", "[v]",
        "-map", "1:a:0",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-c:a", "aac",
        "-b:a", "160k",
        "-movflags", "+faststart",
        str(out_path),
    ]
    subprocess.run(cmd, check=True)
    payload = {
        "artifact_role": "assembly_report",
        "version": 1,
        "source_video": str(video_path),
        "selected_audio": str(audio_path),
        "final_video": str(out_path),
        "source_audio_policy": source_audio_policy,
        "source_audio_mapped": False,
        "video_map": "-map [v]",
        "audio_map": "-map 1:a:0",
        "effects_applied": bool(effects or title or labels),
        "title": title,
        "labels": labels or [],
        "command_tool": "tools/final_av_assemble.py",
    }
    report_path = Path(report) if report else out_path.with_name("assembly_report.json")
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    payload["assembly_report"] = str(report_path)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Assemble final video with selected pipeline audio")
    parser.add_argument("--video", required=True)
    parser.add_argument("--audio", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--report")
    parser.add_argument("--title")
    parser.add_argument("--label", action="append", type=parse_label, default=[])
    parser.add_argument("--source-audio-policy", default="replace_with_music")
    parser.add_argument("--no-effects", action="store_true")
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    payload = assemble_final_av(
        video=args.video,
        audio=args.audio,
        out=args.out,
        report=args.report,
        title=args.title,
        labels=args.label,
        source_audio_policy=args.source_audio_policy,
        effects=not args.no_effects,
        ffmpeg=args.ffmpeg,
    )
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"[final_av_assemble] wrote {payload['final_video']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
