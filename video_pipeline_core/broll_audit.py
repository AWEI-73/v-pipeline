"""broll_audit.py — Node 11 B-roll ratio / repeated-source audit (P1-A).

Reports how much of a timeline is supplementary (b-roll) footage and whether any
single source is over-reused. All thresholds are *parameterized* by the caller
(build_profile / creator profile / brief). This module intentionally ships no
creator-specific keyword map or preferred ratio — those are policy, supplied per
project, never baked in.

Source: technique inspired by https://github.com/Hao0321/video-autopilot-kit
(MIT); reimplemented for this project's artifact contracts.
"""
import json
from pathlib import Path

# Generic default for which source categories count as supplementary footage.
# Callers may override; this is a neutral structural default, not a creator rule.
_DEFAULT_BROLL_SOURCES = ("stock", "generated")


def _clips(timeline):
    if isinstance(timeline, list):
        return timeline
    if isinstance(timeline, dict):
        return timeline.get("clips") or []
    return []


def _source_id(clip):
    return clip.get("source_path") or clip.get("file") or clip.get("source")


def _is_broll(clip, broll_sources, broll_kinds):
    if "is_broll" in clip:
        return bool(clip["is_broll"])
    if clip.get("roll") in ("broll", "b-roll"):
        return True
    if clip.get("source") in broll_sources:
        return True
    if clip.get("kind") in broll_kinds:
        return True
    return False


def _finding(check, level, message, *, fix_class, value=None, limit=None,
             affected=None, next_route=None):
    return {
        "check": check,
        "level": level,
        "metric": check,
        "value": value,
        "limit": limit,
        "message": message,
        "affected": affected or [],
        "fix_class": fix_class,
        "next_route": next_route,
    }


def audit_broll(timeline, *, target_ratio=None, max_source_repeats=None,
                broll_sources=None, broll_kinds=None):
    """Audit b-roll ratio and source reuse; return the artifact payload."""
    clips = _clips(timeline)
    broll_sources = set(broll_sources) if broll_sources is not None else set(_DEFAULT_BROLL_SOURCES)
    broll_kinds = set(broll_kinds or ())

    total_dur = sum(float(c.get("duration_sec") or 0) for c in clips)
    broll_dur = sum(float(c.get("duration_sec") or 0) for c in clips
                    if _is_broll(c, broll_sources, broll_kinds))
    broll_ratio = round(broll_dur / total_dur, 4) if total_dur > 0 else 0.0

    source_ids = [_source_id(c) for c in clips if _source_id(c)]
    counts = {}
    for sid in source_ids:
        counts[sid] = counts.get(sid, 0) + 1
    unique_source_ratio = round(len(counts) / len(source_ids), 4) if source_ids else 0.0
    max_repeats = max(counts.values()) if counts else 0

    findings = []

    if max_source_repeats is not None and max_repeats > int(max_source_repeats):
        over = sorted(s for s, n in counts.items() if n > int(max_source_repeats))
        findings.append(_finding(
            "max_source_repeats", "fail",
            f"source reused {max_repeats} times exceeds ceiling {int(max_source_repeats)}",
            fix_class="material", value=max_repeats, limit=int(max_source_repeats),
            affected=over, next_route="curator",
        ))

    if target_ratio is not None and broll_ratio > float(target_ratio):
        findings.append(_finding(
            "broll_ratio", "warn",
            f"b-roll ratio {broll_ratio:.2f} exceeds target {float(target_ratio):.2f}",
            fix_class="material", value=broll_ratio, limit=float(target_ratio),
            next_route="curator",
        ))

    has_fail = any(f["level"] == "fail" for f in findings)
    next_action = "curator" if has_fail else None
    return {
        "artifact_role": "broll_audit",
        "version": 1,
        "pass": not has_fail,
        "metrics": {
            "broll_ratio": broll_ratio,
            "unique_source_ratio": unique_source_ratio,
            "max_source_repeats": max_repeats,
        },
        "findings": findings,
        "next_action": next_action,
    }


def write_broll_audit(timeline, out_path, **kwargs):
    """Audit ``timeline`` and write the stable ``broll_audit.json``."""
    result = audit_broll(timeline, **kwargs)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return {"ok": True, "broll_audit": str(out_path), "result": result}
