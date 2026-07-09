"""Sampling coverage verification for reviewer perception artifacts.

This module observes whether a sampling plan covers declared shots and
anchors. It does not judge whether the sampled frames are good, sufficient for
creative approval, or fit for asset promotion.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from .sampling_planner import normalize_shots


VERSION = 1


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


def _anchor_targets(audio_anchors: Mapping[str, Any] | None) -> list[tuple[str, float]]:
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
        targets.extend((reason, value) for value in _anchor_values(audio_anchors.get(key)))
    return targets


def _failing_report(reason: str, *, sampling_plan_path: str | None = None) -> dict[str, Any]:
    return {
        "artifact_role": "sampling_coverage_report",
        "version": VERSION,
        "pass": False,
        "sampling_plan_path": sampling_plan_path,
        "checks": [{"check": reason, "pass": False, "details": reason}],
        "gaps": [],
        "limitations": ["Coverage could not be verified because required inputs were missing or malformed."],
    }


def verify_sampling_coverage(
    sampling_plan: Mapping[str, Any] | None,
    shots: Iterable[Any] | None,
    audio_anchors: Mapping[str, Any] | None = None,
    *,
    tolerance_sec: float = 0.35,
    max_gap_sec: float = 4.0,
    sampling_plan_path: str | None = None,
) -> dict[str, Any]:
    if not isinstance(sampling_plan, Mapping) or sampling_plan.get("artifact_role") != "sampling_plan":
        return _failing_report("missing_sampling_plan", sampling_plan_path=sampling_plan_path)
    normalized_shots = normalize_shots(shots or sampling_plan.get("shots") or [])
    if not normalized_shots:
        return _failing_report("missing_shot_list", sampling_plan_path=sampling_plan_path)

    samples = [
        sample for sample in (sampling_plan.get("samples") or [])
        if isinstance(sample, Mapping) and sample.get("shot_id") is not None
    ]
    if not samples:
        return _failing_report("empty_samples", sampling_plan_path=sampling_plan_path)

    checks: list[dict[str, Any]] = []
    gaps: list[dict[str, float | str]] = []
    all_pass = True

    for shot in normalized_shots:
        shot_samples = sorted(
            _float(sample.get("timestamp_sec"))
            for sample in samples
            if str(sample.get("shot_id")) == str(shot["shot_id"])
        )
        has_sample = bool(shot_samples)
        checks.append({
            "check": "shot_has_sample",
            "shot_id": shot["shot_id"],
            "pass": has_sample,
            "sample_count": len(shot_samples),
        })
        all_pass = all_pass and has_sample
        if not shot_samples:
            gaps.append({
                "shot_id": shot["shot_id"],
                "start_sec": float(shot["start_sec"]),
                "end_sec": float(shot["end_sec"]),
                "reason": "shot_without_samples",
            })
            continue
        boundaries = [float(shot["start_sec"]), *shot_samples, float(shot["end_sec"])]
        for start, end in zip(boundaries, boundaries[1:]):
            if end - start > max_gap_sec:
                gaps.append({
                    "shot_id": shot["shot_id"],
                    "start_sec": round(start, 3),
                    "end_sec": round(end, 3),
                    "reason": "unsampled_gap",
                })

    for reason, timestamp in _anchor_targets(audio_anchors):
        nearest = min((_float(sample.get("timestamp_sec")) for sample in samples), key=lambda item: abs(item - timestamp))
        ok = abs(nearest - timestamp) <= tolerance_sec
        checks.append({
            "check": "anchor_within_tolerance",
            "reason": reason,
            "timestamp_sec": timestamp,
            "nearest_sample_sec": round(nearest, 3),
            "tolerance_sec": tolerance_sec,
            "pass": ok,
        })
        all_pass = all_pass and ok

    if gaps:
        all_pass = False
    checks.append({
        "check": "max_unsampled_gap",
        "pass": not gaps,
        "max_gap_sec": max_gap_sec,
        "gap_count": len(gaps),
    })
    return {
        "artifact_role": "sampling_coverage_report",
        "version": VERSION,
        "pass": bool(all_pass),
        "sampling_plan_path": sampling_plan_path,
        "shot_count": len(normalized_shots),
        "sample_count": len(samples),
        "checks": checks,
        "gaps": gaps,
        "limitations": [
            "Coverage verifies declared sampling proximity only; it does not judge visual quality or narrative sufficiency.",
        ],
    }


def write_sampling_coverage_report(
    sampling_plan_path: str | Path,
    shots: Iterable[Any] | str | Path | None,
    out_path: str | Path,
    *,
    audio_anchors: Mapping[str, Any] | str | Path | None = None,
    tolerance_sec: float = 0.35,
    max_gap_sec: float = 4.0,
) -> dict[str, Any]:
    try:
        plan = _load_json(sampling_plan_path)
    except Exception:
        payload = _failing_report("missing_sampling_plan", sampling_plan_path=str(sampling_plan_path))
        _write_json(Path(out_path), payload)
        return payload

    if isinstance(shots, (str, Path)):
        try:
            shots_payload = _load_json(shots)
        except Exception:
            shots_payload = None
    else:
        shots_payload = shots
    if isinstance(audio_anchors, (str, Path)):
        try:
            anchors_payload = _load_json(audio_anchors)
        except Exception:
            anchors_payload = None
    else:
        anchors_payload = audio_anchors

    payload = verify_sampling_coverage(
        plan,
        shots_payload,
        anchors_payload if isinstance(anchors_payload, Mapping) else None,
        tolerance_sec=tolerance_sec,
        max_gap_sec=max_gap_sec,
        sampling_plan_path=str(sampling_plan_path),
    )
    _write_json(Path(out_path), payload)
    return payload
