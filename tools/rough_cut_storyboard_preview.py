"""Build a fast rough-cut storyboard preview from material matrix keyframes.

This is a bounded review renderer. It does not decode source videos and does
not claim to be the canonical final render. Use it when large source files make
motion preview too expensive for material-first review.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image, ImageDraw  # noqa: E402

from video_pipeline_core.platform_tools import resolve_ffmpeg, resolve_ffprobe  # noqa: E402


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, payload: dict[str, Any]):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _asset_keyframes(matrix: dict[str, Any]) -> dict[str, Path]:
    refs: dict[str, Path] = {}
    for asset in matrix.get("assets") or []:
        if not isinstance(asset, dict):
            continue
        asset_id = str(asset.get("asset_id") or "")
        keyframes = ((asset.get("visual_evidence") or {}).get("keyframes") or [])
        first = next((item for item in keyframes if isinstance(item, dict) and item.get("image_path")), None)
        if asset_id and first:
            refs[asset_id] = Path(str(first["image_path"]))
    return refs


def _render_frame(source: Path, target: Path, *, width: int, height: int, label: str):
    with Image.open(source) as img:
        img = img.convert("RGB")
        img.thumbnail((width, height), Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", (width, height), (12, 16, 24))
        x = (width - img.width) // 2
        y = (height - img.height) // 2
        canvas.paste(img, (x, y))
        draw = ImageDraw.Draw(canvas)
        draw.rectangle((0, height - 28, width, height), fill=(0, 0, 0))
        draw.text((10, height - 21), label[:80], fill=(255, 255, 255))
        canvas.save(target, quality=90)


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
    return json.loads(result.stdout)


def build_storyboard_preview(
    *,
    matrix_path: str | Path,
    rough_cut_plan_path: str | Path,
    out_path: str | Path,
    report_path: str | Path,
    seconds_per_clip: float = 1.5,
    width: int = 854,
    height: int = 480,
    fps: int = 2,
) -> dict[str, Any]:
    matrix_path = Path(matrix_path)
    rough_cut_plan_path = Path(rough_cut_plan_path)
    out = Path(out_path)
    report = Path(report_path)
    matrix = _load_json(matrix_path)
    plan = _load_json(rough_cut_plan_path)
    refs = _asset_keyframes(matrix)
    clips = [item for item in (plan.get("clips") or []) if isinstance(item, dict)]
    if not clips:
        raise ValueError("rough cut plan has no clips")
    if seconds_per_clip <= 0:
        raise ValueError("seconds_per_clip must be positive")
    if fps <= 0:
        raise ValueError("fps must be positive")

    frame_dir = out.parent / "_storyboard_preview_frames"
    frame_dir.mkdir(parents=True, exist_ok=True)
    for old in frame_dir.glob("frame_*.jpg"):
        old.unlink()

    frame_index = 0
    used: list[dict[str, Any]] = []
    repeats = max(1, int(round(seconds_per_clip * fps)))
    for clip in clips:
        asset_id = str(clip.get("asset_id") or "")
        source = refs.get(asset_id)
        if not source or not source.is_file():
            continue
        label = f"{clip.get('segment', '')} {clip.get('role', '')} {asset_id}".strip()
        rendered_once = frame_dir / f"_src_{frame_index:04d}.jpg"
        _render_frame(source, rendered_once, width=width, height=height, label=label)
        for _ in range(repeats):
            target = frame_dir / f"frame_{frame_index:04d}.jpg"
            rendered_once.replace(target)
            frame_index += 1
            if _ < repeats - 1:
                _render_frame(source, rendered_once, width=width, height=height, label=label)
        used.append({
            "asset_id": asset_id,
            "source_keyframe": str(source),
            "segment": clip.get("segment"),
            "role": clip.get("role"),
            "seconds": seconds_per_clip,
        })

    if not used:
        raise ValueError("no clips could be matched to matrix keyframes")

    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        resolve_ffmpeg(),
        "-y",
        "-hide_banner",
        "-framerate",
        str(fps),
        "-i",
        str(frame_dir / "frame_%04d.jpg"),
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(out),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr)

    output_probe = _probe(out)
    payload = {
        "artifact_role": "rough_cut_storyboard_preview_report",
        "version": 1,
        "ok": True,
        "source_mode": "matrix_keyframes",
        "source_matrix": str(matrix_path.resolve()),
        "source_rough_cut_plan": str(rough_cut_plan_path.resolve()),
        "output_video": str(out.resolve()),
        "clip_count": len(used),
        "seconds_per_clip": seconds_per_clip,
        "fps": fps,
        "used_clips": used,
        "output_probe": output_probe,
        "limitations": [
            "This preview is built from keyframes only and does not show source motion.",
            "Use it for material/storyboard review when decoding large source videos is too slow.",
        ],
        "next_action": "human_review_or_motion_preview",
    }
    _write_json(report, payload)
    return payload


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", required=True)
    parser.add_argument("--rough-cut-plan", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--seconds-per-clip", type=float, default=1.5)
    parser.add_argument("--width", type=int, default=854)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument("--fps", type=int, default=2)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    payload = build_storyboard_preview(
        matrix_path=args.matrix,
        rough_cut_plan_path=args.rough_cut_plan,
        out_path=args.out,
        report_path=args.report,
        seconds_per_clip=args.seconds_per_clip,
        width=args.width,
        height=args.height,
        fps=args.fps,
    )
    if args.json:
        print(json.dumps({"ok": True, "output_video": payload["output_video"], "clip_count": payload["clip_count"]}, ensure_ascii=False, indent=2))
    else:
        print(f"ok=True output={payload['output_video']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
