"""Deterministic, accepted-catalog-only beat-cut composition and verification."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence


class BeatCutCompositionError(ValueError):
    """Raised when a montage cannot meet its declared beat/material contract."""


def _number(value: Any, field: str, *, positive: bool = False) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise BeatCutCompositionError(f"{field} must be numeric") from exc
    if positive and result <= 0:
        raise BeatCutCompositionError(f"{field} must be positive")
    return result


def _beat_values(beat_grid: Sequence[Any] | Mapping[str, Any]) -> list[float]:
    value: Any = beat_grid
    if isinstance(value, Mapping):
        value = value.get("beat_grid") or value.get("beats")
        if value is None and isinstance(beat_grid.get("features"), Mapping):
            value = beat_grid["features"].get("beat_times")
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise BeatCutCompositionError("beat grid is missing")
    beats = sorted({_number(item, "beat anchor") for item in value})
    if not beats:
        raise BeatCutCompositionError("beat grid is empty")
    return beats


def _is_photo(asset: Mapping[str, Any]) -> bool:
    kind = str(asset.get("kind") or asset.get("source_type") or "").lower()
    return bool(asset.get("is_photo")) or kind in {"image", "photo", "still"}


def _accepted_assets(approved_material: Sequence[Mapping[str, Any]], min_distinct_assets: int) -> list[dict[str, Any]]:
    if not isinstance(approved_material, Sequence) or isinstance(approved_material, (str, bytes)):
        raise BeatCutCompositionError("approved material list is required")
    unique: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, raw in enumerate(approved_material):
        if not isinstance(raw, Mapping):
            raise BeatCutCompositionError(f"approved material {index} is not an object")
        if raw.get("accepted") is not True:
            raise BeatCutCompositionError(f"approved material {index} is not accepted")
        asset_id = str(raw.get("asset_id") or "").strip()
        source = str(raw.get("source_relative_path") or raw.get("source_path") or "").strip()
        if not asset_id or not source:
            raise BeatCutCompositionError(f"approved material {index} lacks asset_id or source lineage")
        if asset_id in seen_ids:
            continue
        item = dict(raw)
        item["asset_id"] = asset_id
        item["source_relative_path"] = source
        item["is_photo"] = _is_photo(item)
        if not item["is_photo"]:
            item["media_duration_sec"] = _number(item.get("media_duration_sec"), f"media duration for {asset_id}", positive=True)
        seen_ids.add(asset_id)
        unique.append(item)
    if len(unique) < int(min_distinct_assets):
        raise BeatCutCompositionError(
            f"insufficient distinct accepted material: {len(unique)} < {int(min_distinct_assets)}"
        )
    return unique


def _evenly_spaced_anchors(anchors: Sequence[float], count: int) -> list[float]:
    if len(anchors) < count:
        raise BeatCutCompositionError(f"missing beat coverage: {len(anchors)} anchors for {count} internal cuts")
    selected: list[float] = []
    last_index = -1
    for ordinal in range(1, count + 1):
        index = round((ordinal * (len(anchors) + 1) / (count + 1)) - 1)
        index = max(last_index + 1, min(index, len(anchors) - (count - ordinal) - 1))
        selected.append(float(anchors[index]))
        last_index = index
    return selected


def compose_beat_cut_montage(
    approved_material: Sequence[Mapping[str, Any]],
    beat_grid: Sequence[Any] | Mapping[str, Any],
    *,
    window_start: float,
    window_end: float,
    fps: float,
    min_distinct_assets: int,
) -> dict[str, Any]:
    """Build an exact montage only from explicitly accepted asset records.

    Internal boundaries are sampled from the provided beat grid. The function
    does not inspect filenames or the filesystem, so source selection remains
    bounded by the accepted material catalog supplied by the caller.
    """
    start = _number(window_start, "window_start")
    end = _number(window_end, "window_end")
    frame_rate = _number(fps, "fps", positive=True)
    if end <= start:
        raise BeatCutCompositionError("window_end must be after window_start")
    required = int(min_distinct_assets)
    if required < 1:
        raise BeatCutCompositionError("min_distinct_assets must be at least one")
    assets = _accepted_assets(approved_material, required)
    beats = _beat_values(beat_grid)
    internal_anchors = [beat for beat in beats if start < beat < end]
    boundaries = [start, *_evenly_spaced_anchors(internal_anchors, required - 1), end]
    clips: list[dict[str, Any]] = []
    for index, (asset, cut_in, cut_out) in enumerate(zip(assets[:required], boundaries, boundaries[1:])):
        duration = cut_out - cut_in
        if not asset["is_photo"] and float(asset["media_duration_sec"]) + (1.0 / frame_rate) < duration:
            raise BeatCutCompositionError(
                f"target overflow: {asset['asset_id']} duration {asset['media_duration_sec']} < required {duration:.6f}"
            )
        lineage = {
            "asset_id": asset["asset_id"],
            "source_relative_path": asset["source_relative_path"],
            "accepted": True,
            "human_review_status": asset.get("human_review_status"),
            "catalog_artifact": asset.get("catalog_artifact"),
        }
        clips.append({
            "id": f"montage_{index + 1:03d}",
            "section": "montage",
            "asset_id": asset["asset_id"],
            "source_path": asset.get("source_path") or asset["source_relative_path"],
            "source_relative_path": asset["source_relative_path"],
            "source_type": "image" if asset["is_photo"] else "video",
            "is_photo": asset["is_photo"],
            "in_seconds": 0.0,
            "out_seconds": round(duration, 6),
            "timeline_in_sec": round(cut_in, 6),
            "timeline_out_sec": round(cut_out, 6),
            "duration_sec": round(duration, 6),
            "beat_anchor_sec": None if index == required - 1 else round(cut_out, 6),
            "source_lineage": lineage,
        })
    return {
        "artifact_role": "beat_cut_montage",
        "version": 1,
        "window_start_sec": start,
        "window_end_sec": end,
        "fps": frame_rate,
        "minimum_distinct_assets": required,
        "montage_distinct_asset_count": len({clip["asset_id"] for clip in clips}),
        "beat_grid": beats,
        "clips": clips,
    }


def verify_beat_cut_alignment(
    timeline: Mapping[str, Any],
    beat_grid: Sequence[Any] | Mapping[str, Any],
    *,
    window_start: float,
    window_end: float,
    fps: float,
) -> dict[str, Any]:
    """Audit intended montage cut positions without changing the timeline."""
    start = _number(window_start, "window_start")
    end = _number(window_end, "window_end")
    frame_rate = _number(fps, "fps", positive=True)
    beats = _beat_values(beat_grid)
    raw_clips = timeline.get("clips") if isinstance(timeline, Mapping) else None
    clips = [
        clip for clip in (raw_clips or [])
        if isinstance(clip, Mapping) and clip.get("section") == "montage"
    ]
    clips.sort(key=lambda clip: float(clip.get("timeline_in_sec") or 0.0))
    intended = clips[:-1] if len(clips) > 1 else []
    tolerance = 1.0 / frame_rate
    boundaries: list[dict[str, Any]] = []
    for clip in intended:
        boundary = _number(clip.get("timeline_out_sec"), "montage cut boundary")
        nearest = min(beats, key=lambda beat: abs(beat - boundary))
        delta = abs(nearest - boundary)
        boundaries.append({
            "clip_id": clip.get("id"),
            "boundary_sec": round(boundary, 6),
            "nearest_beat_sec": round(nearest, 6),
            "delta_sec": round(delta, 6),
            "delta_frames": round(delta * frame_rate, 6),
            "within_one_frame": delta <= tolerance + 1e-9,
        })
    within = sum(1 for boundary in boundaries if boundary["within_one_frame"])
    ratio = (within / len(boundaries)) if boundaries else 0.0
    target_end = float(clips[-1].get("timeline_out_sec") or 0.0) if clips else 0.0
    target_delta = abs(target_end - end)
    return {
        "artifact_role": "beat_cut_alignment_report",
        "version": 1,
        "window_start_sec": start,
        "window_end_sec": end,
        "fps": frame_rate,
        "frame_tolerance_sec": tolerance,
        "intended_boundary_count": len(boundaries),
        "within_one_frame_count": within,
        "within_one_frame_ratio": ratio,
        "target_end_sec": target_end,
        "target_end_delta_sec": target_delta,
        "target_end_within_one_frame": target_delta <= tolerance + 1e-9,
        "boundaries": boundaries,
        "pass": bool(boundaries) and ratio == 1.0 and target_delta <= tolerance + 1e-9,
    }


def write_beat_cut_alignment_report(
    timeline: Mapping[str, Any],
    beat_grid: Sequence[Any] | Mapping[str, Any],
    *,
    window_start: float,
    window_end: float,
    fps: float,
    out_path: str | Path,
) -> dict[str, Any]:
    report = verify_beat_cut_alignment(
        timeline,
        beat_grid,
        window_start=window_start,
        window_end=window_end,
        fps=fps,
    )
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report
