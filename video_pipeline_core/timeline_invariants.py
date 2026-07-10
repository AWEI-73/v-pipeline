"""timeline_invariants.py — Node 11 deterministic timeline audit (P1-A).

Verifies structural invariants of a Node 10 ``timeline_build`` before the
expensive render/review loop. All checks are pure and deterministic; no media is
decoded. Output follows the ``timeline_invariants.json`` contract in
``docs/video-autopilot-tool-integration-spec.md``.

This is VERIFY evidence, not SPEC truth: it never invents requirements, it only
reports whether the compiled timeline honors the contract it was built from.

Source: techniques inspired by https://github.com/Hao0321/video-autopilot-kit
(MIT); reimplemented for this project's artifact contracts.
"""
import json
from pathlib import Path


def _check(name, status, affected_segments=None, details=""):
    return {
        "name": name,
        "status": status,
        "affected_segments": affected_segments or [],
        "details": details,
    }


def _clips(timeline):
    if isinstance(timeline, list):
        return timeline
    if isinstance(timeline, dict):
        return timeline.get("clips") or []
    return []


def _has_trace(clip):
    if clip.get("trace") or clip.get("source_path") or clip.get("file"):
        return True
    lineage = clip.get("source_lineage")
    generated = isinstance(lineage, dict) and lineage.get("generated") is True
    descriptor = clip.get("generated_background")
    return generated and isinstance(descriptor, dict) and bool(descriptor)


def audit_timeline(timeline, *, must_include_segments=None,
                   expected_duration_sec=None, duration_tolerance_sec=1.0,
                   overlap_tolerance_sec=0.05):
    """Audit timeline structural invariants and return the artifact payload."""
    clips = _clips(timeline)
    checks = []

    # 1. Trace presence: every timeline item must trace back to a source.
    missing_trace = [c.get("segment") for c in clips if not _has_trace(c)]
    checks.append(_check(
        "clip_trace_present",
        "fail" if missing_trace else "pass",
        missing_trace,
        "all clips have source trace" if not missing_trace
        else f"{len(missing_trace)} clip(s) missing source trace",
    ))

    # 2. Non-negative duration: reject negative/inverted ranges.
    bad_duration = []
    for c in clips:
        dur = float(c.get("duration_sec") or 0)
        start = c.get("start_sec")
        end = c.get("end_sec")
        inverted = start is not None and end is not None and float(end) < float(start)
        if dur < 0 or inverted:
            bad_duration.append(c.get("segment"))
    checks.append(_check(
        "non_negative_duration",
        "fail" if bad_duration else "pass",
        bad_duration,
        "all clip durations are valid" if not bad_duration
        else f"{len(bad_duration)} clip(s) have invalid/negative duration",
    ))

    # 3. Track overlap: timeline positions must not overlap on a single track.
    overlap_segments = []
    ordered = [c for c in clips if c.get("timeline_in_sec") is not None]
    ordered = sorted(ordered, key=lambda c: float(c.get("timeline_in_sec") or 0))
    for prev, cur in zip(ordered, ordered[1:]):
        prev_out = float(prev.get("timeline_out_sec")
                         or (float(prev.get("timeline_in_sec") or 0)
                             + float(prev.get("duration_sec") or 0)))
        cur_in = float(cur.get("timeline_in_sec") or 0)
        overlap = prev_out - cur_in
        transition = cur.get("transition")
        declared_overlap = float(cur.get("transition_duration_sec") or 0.0)
        intentional = (
            transition in {"dissolve", "crossfade", "xfade"}
            and overlap <= declared_overlap + overlap_tolerance_sec
        )
        if cur_in + overlap_tolerance_sec < prev_out and not intentional:
            overlap_segments.append(cur.get("segment"))
    checks.append(_check(
        "track_overlap_free",
        "fail" if overlap_segments else "pass",
        overlap_segments,
        "no unintended track overlap" if not overlap_segments
        else f"{len(overlap_segments)} clip(s) overlap the previous clip on the timeline",
    ))

    # 4. Duration compatibility with brief/contract expectation (advisory).
    actual_total = 0.0
    for c in clips:
        out = c.get("timeline_out_sec")
        if out is not None:
            actual_total = max(actual_total, float(out))
        else:
            actual_total += float(c.get("duration_sec") or 0)
    if expected_duration_sec is None:
        checks.append(_check(
            "duration_compatible", "pass", [],
            f"no target duration provided (actual {actual_total:.2f}s)",
        ))
    else:
        diff = abs(actual_total - float(expected_duration_sec))
        compatible = diff <= float(duration_tolerance_sec)
        checks.append(_check(
            "duration_compatible",
            "pass" if compatible else "warn",
            [],
            f"actual {actual_total:.2f}s vs target {float(expected_duration_sec):.2f}s"
            f" (tolerance {float(duration_tolerance_sec):.2f}s)",
        ))

    # 5. Must-include coverage: required segments must remain represented.
    present_segments = {c.get("segment") for c in clips}
    if must_include_segments:
        missing_required = [s for s in must_include_segments if s not in present_segments]
        checks.append(_check(
            "must_include_present",
            "fail" if missing_required else "pass",
            missing_required,
            "all must-include segments represented" if not missing_required
            else f"{len(missing_required)} must-include segment(s) absent from timeline",
        ))

    has_fail = any(c["status"] == "fail" for c in checks)
    next_action = "fix_timeline_or_assembly" if has_fail else None
    return {
        "artifact_role": "timeline_invariants",
        "version": 1,
        "pass": not has_fail,
        "checks": checks,
        "next_action": next_action,
    }


def write_timeline_invariants(timeline, out_path, **kwargs):
    """Audit ``timeline`` and write the stable ``timeline_invariants.json``."""
    result = audit_timeline(timeline, **kwargs)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return {"ok": True, "timeline_invariants": str(out_path), "result": result}
