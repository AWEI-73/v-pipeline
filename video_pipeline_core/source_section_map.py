"""Fuse visual shot boundaries and audio energy changes into source sections."""
from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Any


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _shot_boundaries(shots: list[tuple[float, float]]) -> list[float]:
    values = set()
    for start, end in shots or []:
        if end > start:
            values.add(round(float(start), 3))
            values.add(round(float(end), 3))
    return sorted(values)


def _energy_changes(energy_curve: list[dict[str, Any]], threshold: float = 0.22) -> list[dict[str, Any]]:
    peaks: list[dict[str, Any]] = []
    prev = None
    for item in energy_curve or []:
        energy = item.get("relative_energy")
        if energy is None:
            continue
        energy = _float(energy)
        if prev is not None:
            delta = abs(energy - prev["energy"])
            if delta >= threshold:
                peaks.append({
                    "time_sec": round(_float(item.get("start_sec")), 3),
                    "delta": round(delta, 3),
                    "from": round(prev["energy"], 3),
                    "to": round(energy, 3),
                })
        prev = {"energy": energy, "time_sec": _float(item.get("start_sec"))}
    return peaks


def _nearest(values: list[float], target: float, max_distance: float) -> float | None:
    if not values:
        return None
    value = min(values, key=lambda item: abs(item - target))
    return value if abs(value - target) <= max_distance else None


def _avg_energy(energy_curve: list[dict[str, Any]], start: float, end: float) -> float | None:
    values = [
        _float(item.get("relative_energy"))
        for item in energy_curve or []
        if _float(item.get("end_sec")) > start and _float(item.get("start_sec")) < end
        and item.get("relative_energy") is not None
    ]
    return round(mean(values), 3) if values else None


def _shot_count(shots: list[tuple[float, float]], start: float, end: float) -> int:
    return sum(1 for shot_start, shot_end in shots or [] if shot_end > start and shot_start < end)


def _merge_boundaries(
    candidates: list[dict[str, Any]],
    *,
    duration_sec: float,
    min_section_sec: float,
) -> list[dict[str, Any]]:
    ordered = sorted(candidates, key=lambda item: float(item["time_sec"]))
    merged: list[dict[str, Any]] = []
    for item in ordered:
        t = round(_float(item.get("time_sec")), 3)
        if t <= 0 or t >= duration_sec:
            continue
        if merged and abs(t - merged[-1]["time_sec"]) < min_section_sec:
            existing = merged[-1]
            existing["reasons"] = sorted(set(existing["reasons"]) | set(item.get("reasons") or []))
            existing["evidence"] = sorted(set(existing.get("evidence") or []) | set(item.get("evidence") or []))
            if "audio_energy_change" in item.get("reasons", []) and "audio_energy_change" not in existing["reasons"]:
                existing["time_sec"] = t
            continue
        merged.append({
            "time_sec": t,
            "reasons": sorted(set(item.get("reasons") or [])),
            "evidence": sorted(set(item.get("evidence") or [])),
        })
    return merged


def build_source_section_map(
    *,
    duration_sec: float,
    energy_curve: list[dict[str, Any]] | None = None,
    shots: list[tuple[float, float]] | None = None,
    target_section_sec: float = 80.0,
    min_section_sec: float = 24.0,
) -> dict[str, Any]:
    duration = float(duration_sec or 0)
    energy_curve = energy_curve or []
    shots = shots or []
    shot_boundaries = _shot_boundaries(shots)
    changes = _energy_changes(energy_curve)
    candidates: list[dict[str, Any]] = []

    for target in [target_section_sec * index for index in range(1, int(duration // target_section_sec) + 1)]:
        snapped = _nearest(shot_boundaries, target, max_distance=18.0)
        candidates.append({
            "time_sec": snapped if snapped is not None else round(target, 3),
            "reasons": ["target_section_spacing"] + (["visual_shot_boundary"] if snapped is not None else []),
            "evidence": [f"target={target:.1f}s"],
        })

    for change in changes:
        t = float(change["time_sec"])
        snapped = _nearest(shot_boundaries, t, max_distance=8.0)
        candidates.append({
            "time_sec": snapped if snapped is not None else t,
            "reasons": ["audio_energy_change"] + (["visual_shot_boundary"] if snapped is not None else []),
            "evidence": [f"energy_delta={change['delta']}", f"audio_time={t:.1f}s"],
        })

    boundaries = _merge_boundaries(
        candidates,
        duration_sec=duration,
        min_section_sec=float(min_section_sec),
    )
    points = [0.0] + [item["time_sec"] for item in boundaries] + [round(duration, 3)]
    sections = []
    for index, (start, end) in enumerate(zip(points, points[1:]), 1):
        if end <= start:
            continue
        sections.append({
            "section_id": f"sec_{index:02d}",
            "start_sec": round(start, 3),
            "end_sec": round(end, 3),
            "duration_sec": round(end - start, 3),
            "avg_relative_energy": _avg_energy(energy_curve, start, end),
            "shot_count": _shot_count(shots, start, end),
        })
    return {
        "artifact_role": "source_section_map",
        "version": 1,
        "duration_sec": round(duration, 3),
        "boundary_strategy": "audio_energy_change + visual_shot_boundary + target_spacing",
        "boundaries": boundaries,
        "sections": sections,
        "limitations": [
            "This is structural evidence, not semantic content recognition.",
            "Use scene/keyframe review to label section content before final highlight selection.",
        ],
    }


def write_source_section_map(
    out_path: str | Path,
    *,
    duration_sec: float,
    energy_curve: list[dict[str, Any]] | None = None,
    shots: list[tuple[float, float]] | None = None,
    target_section_sec: float = 80.0,
    min_section_sec: float = 24.0,
) -> dict[str, Any]:
    result = build_source_section_map(
        duration_sec=duration_sec,
        energy_curve=energy_curve,
        shots=shots,
        target_section_sec=target_section_sec,
        min_section_sec=min_section_sec,
    )
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result
