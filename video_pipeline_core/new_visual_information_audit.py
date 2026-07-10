"""Audit whether timeline duration delivers genuinely new visual information."""
from __future__ import annotations

import json
from pathlib import Path


def _clips(timeline):
    return timeline if isinstance(timeline, list) else (timeline or {}).get("clips") or []


def _visual_identity(item):
    explicit = item.get("scene_id") or item.get("visual_id")
    if explicit:
        return explicit
    source = item.get("source_path") or item.get("source")
    if not source:
        return None
    start = item.get("source_in_sec")
    if start is None:
        start = item.get("extract_start")
    if start is None:
        start = item.get("original_start_sec")
    if start is None:
        return source
    return f"{source}@{round(float(start), 2):.2f}"


def _duration_sec(item):
    for field in ("duration_sec", "extract_dur", "target_duration_sec"):
        value = item.get(field)
        if value is None:
            continue
        try:
            duration = float(value)
        except (TypeError, ValueError):
            continue
        if duration > 0:
            return duration
    timeline_in = item.get("timeline_in_sec")
    timeline_out = item.get("timeline_out_sec")
    if timeline_in is None or timeline_out is None:
        return 0.0
    try:
        return max(0.0, float(timeline_out) - float(timeline_in))
    except (TypeError, ValueError):
        return 0.0


def audit_new_visual_information(timeline, *, min_new_visual_ratio=0.6,
                                 max_repeated_hold_sec=3.0):
    clips = _clips(timeline)
    total = sum(_duration_sec(item) for item in clips)
    seen = set()
    new_duration = 0.0
    repeated_duration = 0.0
    repeated_ids = set()
    for item in clips:
        duration = _duration_sec(item)
        identity = _visual_identity(item)
        if not identity or identity not in seen:
            new_duration += duration
            if identity:
                seen.add(identity)
        else:
            repeated_duration += duration
            repeated_ids.add(identity)
    ratio = round(new_duration / total, 4) if total else 0.0
    findings = []
    if ratio < float(min_new_visual_ratio):
        findings.append({
            "check": "new_visual_information_ratio", "level": "fail",
            "value": ratio, "limit": float(min_new_visual_ratio),
            "affected": sorted(repeated_ids), "fix_class": "material",
            "next_route": "curator",
        })
    if repeated_duration > float(max_repeated_hold_sec):
        findings.append({
            "check": "repeated_visual_hold_sec", "level": "fail",
            "value": round(repeated_duration, 3), "limit": float(max_repeated_hold_sec),
            "affected": sorted(repeated_ids), "fix_class": "material",
            "next_route": "curator",
        })
    return {
        "artifact_role": "new_visual_information_audit",
        "version": 1,
        "pass": not findings,
        "metrics": {
            "new_visual_information_ratio": ratio,
            "repeated_visual_hold_sec": round(repeated_duration, 3),
        },
        "findings": findings,
        "next_action": "curator" if findings else None,
    }


def write_new_visual_information_audit(timeline, out_path, **kwargs):
    result = audit_new_visual_information(timeline, **kwargs)
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "new_visual_information_audit": str(path), "result": result}
