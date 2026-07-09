"""Canonical reviewer montage wall renderer.

This module renders observable frame walls and machine-readable cell indexes.
It does not judge coverage quality, promote assets, or claim whole-video
reviewability when coverage evidence is missing or failing.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Mapping

from PIL import Image, ImageDraw


VERSION = 1
PROFILES = {"material_wall", "timeline_wall", "segment_strip"}


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _placeholder(size: tuple[int, int], text: str) -> Image.Image:
    img = Image.new("RGB", size, "#d9dee8")
    draw = ImageDraw.Draw(img)
    draw.text((10, size[1] // 2 - 8), text[:28], fill="#526070")
    return img


def _extract_frame(video_path: str | Path, timestamp_sec: float, size: tuple[int, int]) -> Image.Image:
    try:
        import cv2  # type: ignore
    except Exception:
        return _placeholder(size, "preview unavailable")
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return _placeholder(size, "preview unavailable")
    try:
        cap.set(cv2.CAP_PROP_POS_MSEC, max(0.0, timestamp_sec) * 1000.0)
        ok, frame = cap.read()
        if not ok:
            return _placeholder(size, "preview unavailable")
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(rgb)
        image.thumbnail(size)
        canvas = Image.new("RGB", size, "#101820")
        canvas.paste(image, ((size[0] - image.width) // 2, (size[1] - image.height) // 2))
        return canvas
    finally:
        cap.release()


def _draw_cell(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, shot_id: str, timestamp: float) -> None:
    label = f"{shot_id}  {timestamp:.2f}s"
    draw.rectangle([x, y + h - 24, x + w - 1, y + h - 1], fill="#000000")
    draw.text((x + 6, y + h - 18), label[:32], fill="#ffe66d")
    draw.rectangle([x, y, x + w - 1, y + h - 1], outline="#ffffff")


def _load_coverage(path: str | Path | None) -> tuple[dict[str, Any] | None, list[str]]:
    if not path:
        return None, ["Coverage report missing; whole-video judgment is not supported."]
    try:
        payload = _load_json(path)
    except Exception:
        return None, ["Coverage report unreadable; whole-video judgment is not supported."]
    if not isinstance(payload, dict) or payload.get("artifact_role") != "sampling_coverage_report":
        return None, ["Coverage report has an unexpected contract; whole-video judgment is not supported."]
    if not payload.get("pass"):
        return payload, ["Coverage report is failing; whole-video judgment is not supported."]
    return payload, []


def _ordered_samples(plan: Mapping[str, Any]) -> list[dict[str, Any]]:
    samples = [
        dict(sample) for sample in (plan.get("samples") or [])
        if isinstance(sample, Mapping) and sample.get("shot_id") is not None
    ]
    samples.sort(key=lambda item: (str(item.get("shot_id")), _float(item.get("timestamp_sec"))))
    return samples


def _geometry(profile: str, samples: list[dict[str, Any]]) -> tuple[int, int, int, int, int]:
    cell_w, cell_h = (240, 140) if profile != "segment_strip" else (180, 104)
    if profile == "material_wall":
        shot_count = max(1, len({str(item.get("shot_id")) for item in samples}))
        max_per_shot = max(
            1,
            max(
                sum(1 for item in samples if str(item.get("shot_id")) == shot_id)
                for shot_id in {str(item.get("shot_id")) for item in samples}
            ) if samples else 1,
        )
        return cell_w, cell_h, max_per_shot, shot_count, 32
    cols = min(6, max(1, len(samples)))
    rows = max(1, math.ceil(len(samples) / cols))
    spark_h = 24 if profile == "timeline_wall" else 0
    return cell_w, cell_h, cols, rows, spark_h


def _render_wall(
    video_path: str | Path,
    samples: list[dict[str, Any]],
    out_path: str | Path,
    *,
    profile: str,
) -> list[dict[str, Any]]:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    if not samples:
        Image.new("RGB", (640, 180), "#f6f7fb").save(out)
        return []

    cell_w, cell_h, cols, rows, spark_h = _geometry(profile, samples)
    row_h = cell_h + spark_h
    sheet = Image.new("RGB", (cols * cell_w, rows * row_h), "#f6f7fb")
    draw = ImageDraw.Draw(sheet)
    cells: list[dict[str, Any]] = []
    row_offsets: dict[str, int] = {}
    shot_positions: dict[str, int] = {}

    for index, sample in enumerate(samples):
        shot_id = str(sample.get("shot_id"))
        timestamp = _float(sample.get("timestamp_sec"))
        if profile == "material_wall":
            row = row_offsets.setdefault(shot_id, len(row_offsets))
            col = shot_positions.get(shot_id, 0)
            shot_positions[shot_id] = col + 1
        else:
            row = index // cols
            col = index % cols
        x = col * cell_w
        y = row * row_h
        frame = _extract_frame(video_path, timestamp, (cell_w, cell_h))
        sheet.paste(frame, (x, y))
        _draw_cell(draw, x, y, cell_w, cell_h, shot_id, timestamp)
        if spark_h:
            baseline = y + cell_h + spark_h // 2
            draw.line([x + 4, baseline, x + cell_w - 4, baseline], fill="#94a3b8", width=1)
            tick = x + int((col + 0.5) * cell_w / max(1, cols))
            draw.line([tick, y + cell_h + 4, tick, y + cell_h + spark_h - 4], fill="#ef4444", width=2)
        cells.append({
            "cell_id": f"cell_{len(cells) + 1:04d}",
            "row": row,
            "column": col,
            "shot_id": shot_id,
            "timestamp_sec": round(timestamp, 3),
            "source_path": str(video_path),
            "reason": sample.get("reason"),
        })

    sheet.save(out)
    return cells


def build_montage_wall(
    video_path: str | Path,
    sampling_plan: Mapping[str, Any],
    coverage_report_path: str | Path | None,
    wall_image_path: str | Path,
    *,
    profile: str = "material_wall",
) -> dict[str, Any]:
    if profile not in PROFILES:
        raise ValueError(f"unknown montage wall profile: {profile}")
    coverage, limitations = _load_coverage(coverage_report_path)
    samples = _ordered_samples(sampling_plan)
    cells = _render_wall(video_path, samples, wall_image_path, profile=profile)
    return {
        "artifact_role": "montage_wall",
        "version": VERSION,
        "profile": profile,
        "source_video": str(video_path),
        "sampling_plan_path": sampling_plan.get("artifact_path"),
        "coverage_report_path": str(coverage_report_path) if coverage_report_path else None,
        "wall_image_path": str(wall_image_path),
        "coverage_pass": bool(coverage and coverage.get("pass")),
        "cells": cells,
        "limitations": limitations,
    }


def write_montage_wall(
    video_path: str | Path,
    sampling_plan_path: str | Path,
    coverage_report_path: str | Path | None,
    wall_image_path: str | Path,
    sidecar_path: str | Path,
    *,
    profile: str = "material_wall",
) -> dict[str, Any]:
    plan = _load_json(sampling_plan_path)
    if not isinstance(plan, dict) or plan.get("artifact_role") != "sampling_plan":
        raise ValueError("sampling plan must be a sampling_plan artifact")
    plan["artifact_path"] = str(sampling_plan_path)
    payload = build_montage_wall(
        video_path,
        plan,
        coverage_report_path,
        wall_image_path,
        profile=profile,
    )
    _write_json(Path(sidecar_path), payload)
    return payload


def write_image_contact_wall(
    image_items: list[Mapping[str, Any]],
    wall_image_path: str | Path,
    sidecar_path: str | Path | None = None,
    *,
    profile: str = "material_wall",
    coverage_report_path: str | Path | None = None,
) -> dict[str, Any]:
    """Render existing still/keyframe items through the canonical sidecar shape."""
    out = Path(wall_image_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    items = [dict(item) for item in image_items if item.get("image_path")]
    cell_w, cell_h = 220, 124
    cols = min(5, max(1, len(items)))
    rows = max(1, math.ceil(len(items) / cols))
    sheet = Image.new("RGB", (cols * cell_w, rows * cell_h), "#f6f7fb")
    draw = ImageDraw.Draw(sheet)
    cells = []
    for index, item in enumerate(items):
        x = (index % cols) * cell_w
        y = (index // cols) * cell_h
        try:
            image = Image.open(item["image_path"]).convert("RGB")
            image.thumbnail((cell_w, cell_h))
            sheet.paste(image, (x + (cell_w - image.width) // 2, y + (cell_h - image.height) // 2))
        except Exception:
            sheet.paste(_placeholder((cell_w, cell_h), "preview unavailable"), (x, y))
        shot_id = str(item.get("shot_id") or item.get("asset_id") or item.get("window_id") or f"cell_{index + 1:04d}")
        timestamp = _float(item.get("timestamp_sec", item.get("start_sec", 0.0)))
        _draw_cell(draw, x, y, cell_w, cell_h, shot_id, timestamp)
        cells.append({
            "cell_id": f"cell_{index + 1:04d}",
            "row": index // cols,
            "column": index % cols,
            "shot_id": shot_id,
            "timestamp_sec": round(timestamp, 3),
            "source_path": str(item.get("image_path")),
            "reason": item.get("reason") or "still_contact",
        })
    if not items:
        Image.new("RGB", (640, 180), "#f6f7fb").save(out)
    else:
        sheet.save(out)
    payload = {
        "artifact_role": "montage_wall",
        "version": VERSION,
        "profile": profile,
        "source_video": None,
        "sampling_plan_path": None,
        "coverage_report_path": str(coverage_report_path) if coverage_report_path else None,
        "wall_image_path": str(out),
        "coverage_pass": False,
        "cells": cells,
        "limitations": ["Still contact wall does not verify whole-video coverage."],
    }
    if sidecar_path:
        _write_json(Path(sidecar_path), payload)
    return payload
