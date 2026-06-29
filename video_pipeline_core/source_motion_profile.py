"""Local source-video motion/transition profile for edit-point discovery."""
from __future__ import annotations

import json
import math
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter, ImageStat

from .keyframe_grid import probe_duration
from .platform_tools import resolve_ffmpeg


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _audio_at(audio_curve: list[dict[str, Any]], time_sec: float) -> float | None:
    values = [
        _float(item.get("relative_energy"))
        for item in audio_curve or []
        if _float(item.get("start_sec")) <= time_sec < _float(item.get("end_sec"))
        and item.get("relative_energy") is not None
    ]
    if not values:
        return None
    return round(sum(values) / len(values), 3)


def _near(values: list[float], target: float, max_distance: float) -> bool:
    return any(abs(float(value) - target) <= max_distance for value in values or [])


def _point_tags(point: dict[str, Any], audio_energy: float | None, near_shot: bool) -> list[str]:
    tags = []
    if _float(point.get("diff_score")) >= 0.45 or _float(point.get("hist_score")) >= 0.35:
        tags.append("high_visual_change")
    if _float(point.get("blur_score")) >= 0.65:
        tags.append("blur_transition")
    if _float(point.get("black_score")) >= 0.70:
        tags.append("black_or_fade")
    if audio_energy is not None and audio_energy <= 0.22:
        tags.append("low_audio")
    if near_shot:
        tags.append("shot_boundary_nearby")
    return tags


def _classify_point(point: dict[str, Any], tags: list[str]) -> str | None:
    if "blur_transition" in tags and "high_visual_change" in tags:
        return "blur_transition"
    if "black_or_fade" in tags and "high_visual_change" in tags:
        return "fade_or_black_transition"
    if "shot_boundary_nearby" in tags and "high_visual_change" in tags and _float(point.get("blur_score")) < 0.45:
        return "scene_entry"
    if "high_visual_change" in tags:
        return "motion_peak"
    return None


def build_motion_profile_from_samples(
    *,
    duration_sec: float,
    samples: list[dict[str, Any]],
    audio_curve: list[dict[str, Any]] | None = None,
    shot_boundaries: list[float] | None = None,
) -> dict[str, Any]:
    enriched = []
    ranked = []
    for point in samples or []:
        time_sec = round(_float(point.get("time_sec")), 3)
        audio_energy = _audio_at(audio_curve or [], time_sec)
        near_shot = _near(shot_boundaries or [], time_sec, 1.5)
        tags = _point_tags(point, audio_energy, near_shot)
        item = {
            "time_sec": time_sec,
            "diff_score": round(_float(point.get("diff_score")), 4),
            "hist_score": round(_float(point.get("hist_score")), 4),
            "blur_score": round(_float(point.get("blur_score")), 4),
            "black_score": round(_float(point.get("black_score")), 4),
            "audio_energy": audio_energy,
            "tags": tags,
            "frame_path": point.get("frame_path"),
        }
        enriched.append(item)
        point_type = _classify_point(item, tags)
        if point_type:
            confidence = min(
                1.0,
                item["diff_score"] * 0.45
                + item["hist_score"] * 0.25
                + item["blur_score"] * 0.20
                + (0.10 if near_shot else 0.0),
            )
            ranked.append({
                "time_sec": time_sec,
                "type": point_type,
                "confidence": round(confidence, 3),
                "tags": tags,
                "reason": ", ".join(tags),
                "frame_path": point.get("frame_path"),
            })
    ranked.sort(key=lambda item: (item["confidence"], item["time_sec"]), reverse=True)
    return {
        "artifact_role": "source_motion_profile",
        "version": 1,
        "duration_sec": round(float(duration_sec or 0), 3),
        "sample_count": len(enriched),
        "points": enriched,
        "ranked_edit_points": ranked,
        "limitations": [
            "Local numeric signal only; semantic labels require material-map review.",
            "Use dense sampling only around candidate sections to control artifact volume.",
        ],
    }


def _extract_frame(video: str | Path, time_sec: float, out_path: str | Path) -> bool:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [
            resolve_ffmpeg(),
            "-y",
            "-ss",
            f"{float(time_sec):.3f}",
            "-i",
            str(video),
            "-frames:v",
            "1",
            "-q:v",
            "3",
            "-vf",
            "scale=320:-1",
            str(out),
        ],
        capture_output=True,
        timeout=90,
    )
    return proc.returncode == 0 and out.exists()


def _blur_score(img: Image.Image) -> float:
    gray = img.convert("L")
    w, h = gray.size
    if w < 3 or h < 3:
        return 1.0
    # Cheap high-frequency proxy: compare neighboring pixels. Low variance means blur.
    small = gray.resize((max(2, w // 4), max(2, h // 4)))
    stat = ImageStat.Stat(small.filter(ImageFilter.FIND_EDGES))
    edge_mean = stat.mean[0] if stat.mean else 0.0
    return round(max(0.0, min(1.0, 1.0 - edge_mean / 24.0)), 4)


def _black_score(img: Image.Image) -> float:
    stat = ImageStat.Stat(img.convert("L"))
    mean = stat.mean[0] if stat.mean else 0.0
    return round(max(0.0, min(1.0, 1.0 - mean / 40.0)), 4) if mean < 40 else 0.0


def _diff_score(prev: Image.Image | None, img: Image.Image) -> tuple[float, float]:
    if prev is None:
        return 0.0, 0.0
    a = prev.convert("RGB").resize((96, 54))
    b = img.convert("RGB").resize((96, 54))
    ap = list(a.getdata())
    bp = list(b.getdata())
    if not ap or not bp:
        return 0.0, 0.0
    diffs = [sum(abs(x - y) for x, y in zip(px, py)) / 765.0 for px, py in zip(ap, bp)]
    diff = sum(diffs) / len(diffs)
    ah = a.histogram()
    bh = b.histogram()
    hist = sum(abs(x - y) for x, y in zip(ah, bh)) / max(1.0, sum(ah) + sum(bh))
    return round(diff, 4), round(hist, 4)


def sample_video_motion(
    video: str | Path,
    *,
    out_dir: str | Path,
    start_sec: float = 0.0,
    end_sec: float | None = None,
    sample_sec: float = 1.0,
) -> list[dict[str, Any]]:
    out = Path(out_dir)
    frames_dir = out / "motion_frames"
    duration = probe_duration(video)
    end = min(float(end_sec) if end_sec is not None else duration, duration)
    samples = []
    prev = None
    index = 0
    time_sec = float(start_sec)
    while time_sec <= end:
        frame = frames_dir / f"motion_{index:04d}_{time_sec:.1f}.jpg"
        if _extract_frame(video, time_sec, frame):
            img = Image.open(frame).convert("RGB")
            diff, hist = _diff_score(prev, img)
            samples.append({
                "time_sec": round(time_sec, 3),
                "diff_score": diff,
                "hist_score": hist,
                "blur_score": _blur_score(img),
                "black_score": _black_score(img),
                "frame_path": str(frame),
            })
            prev = img
        index += 1
        time_sec += float(sample_sec)
    return samples


def _make_points_sheet(points: list[dict[str, Any]], out_path: str | Path, *, max_points: int = 24) -> str:
    selected = [p for p in points if p.get("frame_path")][:max_points]
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    if not selected:
        Image.new("RGB", (640, 180), "#f6f7fb").save(out)
        return str(out)
    cell_w, cell_h = 220, 124
    label_h = 42
    cols = 4
    rows = math.ceil(len(selected) / cols)
    sheet = Image.new("RGB", (cols * cell_w, rows * (cell_h + label_h)), "#f6f7fb")
    draw = ImageDraw.Draw(sheet)
    for idx, point in enumerate(selected):
        x = (idx % cols) * cell_w
        y = (idx // cols) * (cell_h + label_h)
        try:
            img = Image.open(point["frame_path"]).convert("RGB")
            img.thumbnail((cell_w, cell_h))
            sheet.paste(img, (x + (cell_w - img.width) // 2, y + (cell_h - img.height) // 2))
        except Exception:
            draw.rectangle([x, y, x + cell_w - 1, y + cell_h - 1], fill="#d9dee8")
        draw.rectangle([x, y + cell_h, x + cell_w - 1, y + cell_h + label_h - 1], fill="#ffffff")
        label = f"{point.get('time_sec', 0):.1f}s {point.get('type') or ''}"
        conf = point.get("confidence")
        if conf is not None:
            label += f" c={float(conf):.2f}"
        draw.text((x + 8, y + cell_h + 8), label[:42], fill="#172033")
    sheet.save(out, quality=90)
    return str(out)


def build_source_motion_profile(
    video: str | Path,
    *,
    out_dir: str | Path,
    audio_curve: list[dict[str, Any]] | None = None,
    shot_boundaries: list[float] | None = None,
    start_sec: float = 0.0,
    end_sec: float | None = None,
    sample_sec: float = 1.0,
) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    samples = sample_video_motion(video, out_dir=out, start_sec=start_sec, end_sec=end_sec, sample_sec=sample_sec)
    duration = probe_duration(video)
    profile = build_motion_profile_from_samples(
        duration_sec=duration,
        samples=samples,
        audio_curve=audio_curve,
        shot_boundaries=shot_boundaries,
    )
    sheet = _make_points_sheet(profile["ranked_edit_points"], out / "source_motion_points.jpg")
    profile["visual"] = {"motion_points_sheet": Path(sheet).name}
    (out / "source_motion_profile.json").write_text(
        json.dumps(profile, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return profile
