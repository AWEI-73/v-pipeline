"""Deterministic reviewer sampling planner.

This module is an observation layer. It proposes frames for reviewer evidence
from shots, motion, and audio anchors; it does not judge quality, mark coverage
as sufficient, or promote any asset.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping


VERSION = 1
REASONS = {"baseline", "motion_peak", "audio_beat", "energy_event", "speech_start"}
REASON_PRIORITY = {
    "speech_start": 0,
    "audio_beat": 1,
    "energy_event": 2,
    "motion_peak": 3,
    "baseline": 4,
}


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_shots(shots: Iterable[Any]) -> list[dict[str, Any]]:
    normalized = []
    for index, shot in enumerate(shots or [], start=1):
        if isinstance(shot, Mapping):
            start = _float(shot.get("start_sec", shot.get("start", 0.0)))
            end = _float(shot.get("end_sec", shot.get("end", start)))
            shot_id = str(shot.get("shot_id") or shot.get("id") or f"shot_{index:03d}")
        elif isinstance(shot, (list, tuple)) and len(shot) >= 2:
            start = _float(shot[0])
            end = _float(shot[1], start)
            shot_id = f"shot_{index:03d}"
        else:
            continue
        if end < start:
            start, end = end, start
        normalized.append({"shot_id": shot_id, "start_sec": round(start, 3), "end_sec": round(end, 3)})
    return normalized


def _shot_for_time(shots: list[dict[str, Any]], timestamp: float) -> dict[str, Any] | None:
    for shot in shots:
        if shot["start_sec"] <= timestamp <= shot["end_sec"]:
            return shot
    return shots[-1] if shots else None


def _baseline_targets(shots: list[dict[str, Any]], *, gap_fill_sec: float = 4.0) -> list[tuple[str, float, str]]:
    targets = []
    # Sharpness selection may move a target within +/-0.2s, so leave margin.
    fill_step = max(0.5, gap_fill_sec - 0.5)
    for shot in shots:
        start = float(shot["start_sec"])
        end = float(shot["end_sec"])
        if end <= start:
            points = [start]
        else:
            points = [start, (start + end) / 2.0, end]
            if gap_fill_sec > 0:
                cursor = start + fill_step
                while cursor < end:
                    points.append(cursor)
                    cursor += fill_step
        for timestamp in points:
            targets.append((shot["shot_id"], timestamp, "baseline"))
    return targets


def _anchor_values(value: Any) -> list[float]:
    if not isinstance(value, list):
        return []
    out = []
    for item in value:
        if isinstance(item, Mapping):
            out.append(_float(item.get("timestamp_sec", item.get("time_sec", item.get("start_sec"))), -1.0))
        else:
            out.append(_float(item, -1.0))
    return [round(item, 3) for item in out if item >= 0]


def _audio_targets(shots: list[dict[str, Any]], audio_anchors: Mapping[str, Any] | None) -> list[tuple[str, float, str]]:
    if not audio_anchors:
        return []
    mapping = [
        ("beat_times", "audio_beat"),
        ("beats", "audio_beat"),
        ("energy_peaks", "energy_event"),
        ("energy_drops", "energy_event"),
        ("speech_starts", "speech_start"),
        ("speech_segment_starts", "speech_start"),
    ]
    targets = []
    for key, reason in mapping:
        for timestamp in _anchor_values(audio_anchors.get(key)):
            shot = _shot_for_time(shots, timestamp)
            if shot:
                targets.append((shot["shot_id"], timestamp, reason))
    return targets


def _motion_targets(video_path: Path, shots: list[dict[str, Any]], *, threshold: float = 18.0) -> list[tuple[str, float, str]]:
    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore
    except Exception:
        return []

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return []
    fps = cap.get(cv2.CAP_PROP_FPS) or 1.0
    metrics: list[tuple[float, float]] = []
    previous = None
    frame_index = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if frame_index % max(1, int(round(fps / 4.0))) != 0:
                frame_index += 1
                continue
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.resize(gray, (96, 54))
            if previous is not None:
                diff = float(np.mean(cv2.absdiff(gray, previous)))
                metrics.append((round(frame_index / fps, 3), diff))
            previous = gray
            frame_index += 1
    finally:
        cap.release()

    targets: list[tuple[str, float, str]] = []
    if len(metrics) < 3:
        return targets
    values = [value for _ts, value in metrics]
    dynamic_threshold = max(threshold, (sum(values) / len(values)) * 1.4)
    for index in range(1, len(metrics) - 1):
        ts, value = metrics[index]
        prev_value = metrics[index - 1][1]
        next_value = metrics[index + 1][1]
        is_peak = value >= dynamic_threshold and value >= prev_value and value >= next_value
        direction_change = value >= dynamic_threshold and (value - prev_value) * (next_value - value) < 0
        if is_peak or direction_change:
            shot = _shot_for_time(shots, ts)
            if shot:
                targets.append((shot["shot_id"], ts, "motion_peak"))
    return targets[:24]


def _sharpest_timestamp(video_path: Path, target: float, shot: Mapping[str, Any], *, window_sec: float = 0.2) -> float:
    return _sharpest_timestamps(video_path, [(target, shot)], window_sec=window_sec)[0]


def _sharpest_timestamps(video_path: Path, requests: list[tuple[float, Mapping[str, Any]]], *, window_sec: float = 0.2) -> list[float]:
    try:
        import cv2  # type: ignore
    except Exception:
        return [round(float(target), 3) for target, _shot in requests]

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return [round(float(target), 3) for target, _shot in requests]
    best: list[float] = []
    try:
        for target, shot in requests:
            start = max(float(shot["start_sec"]), float(target) - window_sec)
            end = min(float(shot["end_sec"]), float(target) + window_sec)
            candidates = [start, float(target), end]
            best_ts = float(target)
            best_score = -1.0
            for ts in candidates:
                cap.set(cv2.CAP_PROP_POS_MSEC, max(0.0, ts) * 1000.0)
                ok, frame = cap.read()
                if not ok:
                    continue
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
                if score > best_score:
                    best_score = score
                    best_ts = ts
            best.append(round(float(best_ts), 3))
    finally:
        cap.release()
    return best


def build_sampling_plan(
    video_path: str | Path,
    shots: Iterable[Any],
    *,
    audio_anchors: Mapping[str, Any] | None = None,
    motion_threshold: float = 18.0,
    gap_fill_sec: float = 4.0,
    merge_window_sec: float = 0.3,
) -> dict[str, Any]:
    video = Path(video_path)
    normalized_shots = normalize_shots(shots)
    targets = _baseline_targets(normalized_shots, gap_fill_sec=gap_fill_sec)
    targets.extend(_motion_targets(video, normalized_shots, threshold=motion_threshold))
    targets.extend(_audio_targets(normalized_shots, audio_anchors))

    prepared: list[tuple[str, float, str, Mapping[str, Any]]] = []
    samples: list[dict[str, Any]] = []
    for shot_id, timestamp, reason in targets:
        if reason not in REASONS:
            continue
        shot = next((item for item in normalized_shots if item["shot_id"] == shot_id), None)
        if not shot:
            continue
        timestamp = min(max(float(timestamp), float(shot["start_sec"])), float(shot["end_sec"]))
        prepared.append((shot_id, timestamp, reason, shot))
    sharp_timestamps = _sharpest_timestamps(video, [(timestamp, shot) for _shot_id, timestamp, _reason, shot in prepared])
    for (shot_id, timestamp, reason, _shot), sharp_ts in zip(prepared, sharp_timestamps):
        _merge_or_append_sample(samples, {
            "shot_id": shot_id,
            "timestamp_sec": round(sharp_ts, 3),
            "target_timestamp_sec": round(float(timestamp), 3),
            "reason": reason,
            "reasons": [reason],
        }, merge_window_sec=merge_window_sec)

    samples.sort(key=lambda item: (str(item["shot_id"]), float(item["timestamp_sec"]), str(item["reason"])))
    for index, sample in enumerate(samples, start=1):
        sample["sample_id"] = f"s{index:04d}"
    return {
        "artifact_role": "sampling_plan",
        "version": VERSION,
        "source_video": str(video),
        "shot_count": len(normalized_shots),
        "shots": normalized_shots,
        "samples": samples,
        "limitations": [
            "Motion events are downscaled frame-difference observations, not quality judgments.",
            "Sharpness only chooses an observable frame near requested timestamps.",
        ],
    }


def _merge_or_append_sample(samples: list[dict[str, Any]], sample: dict[str, Any], *, merge_window_sec: float) -> None:
    shot_id = str(sample["shot_id"])
    timestamp = float(sample["timestamp_sec"])
    for existing in samples:
        if str(existing.get("shot_id")) != shot_id:
            continue
        if abs(float(existing.get("timestamp_sec", 0.0)) - timestamp) > merge_window_sec:
            continue
        reasons = list(existing.get("reasons") or [existing.get("reason")])
        reason = str(sample["reason"])
        if reason not in reasons:
            reasons.append(reason)
        existing["reasons"] = [item for item in reasons if item]
        existing["reason"] = min(existing["reasons"], key=lambda item: REASON_PRIORITY.get(str(item), 99))
        existing["target_timestamp_sec"] = round(min(float(existing.get("target_timestamp_sec", timestamp)), float(sample["target_timestamp_sec"])), 3)
        return
    samples.append(sample)


def write_sampling_plan(
    video_path: str | Path,
    shots: Iterable[Any],
    out_path: str | Path,
    *,
    audio_anchors: Mapping[str, Any] | None = None,
    motion_threshold: float = 18.0,
    gap_fill_sec: float = 4.0,
    merge_window_sec: float = 0.3,
) -> dict[str, Any]:
    payload = build_sampling_plan(
        video_path,
        shots,
        audio_anchors=audio_anchors,
        motion_threshold=motion_threshold,
        gap_fill_sec=gap_fill_sec,
        merge_window_sec=merge_window_sec,
    )
    _write_json(Path(out_path), payload)
    return payload
