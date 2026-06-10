"""editor_review.py — Node 11/12 lightweight clip review checks.

These checks are deterministic and cheap. They catch timeline mistakes before
expensive review/render loops: duration mismatch, duplicate/overlapping source
footage, too-short clips, and invalid stitched gaps.
"""
import json
from pathlib import Path


def _finding(check, level, message, next_route="node_10_timeline_build"):
    return {"check": check, "level": level, "message": message, "next_route": next_route}


def _overlap(a, b):
    return a["source_path"] == b["source_path"] and a["start_sec"] < b["end_sec"] and b["start_sec"] < a["end_sec"]


def review_timeline_build(timeline, *, duration_tolerance_sec=0.5,
                          max_stitch_gap_sec=2.0, min_duration_sec=0.5):
    clips = timeline.get("clips") or []
    checks = []
    for i, clip in enumerate(clips):
        findings = []
        dur = float(clip.get("duration_sec") or 0)
        target = clip.get("target_duration_sec")
        duration_match = True
        if target is not None and abs(dur - float(target)) > duration_tolerance_sec:
            duration_match = False
            findings.append(_finding(
                "duration_match", "fail",
                f"duration {dur:.3f}s differs from target {float(target):.3f}s",
            ))

        min_duration_ok = dur >= min_duration_sec
        if not min_duration_ok:
            findings.append(_finding(
                "min_duration_ok", "warn",
                f"clip duration {dur:.3f}s is shorter than {min_duration_sec:.3f}s",
            ))

        overlap_free = True
        duplicate_footage = True
        for prev in clips[:i]:
            if _overlap(clip, prev):
                is_exact_dup = (clip.get("start_sec") == prev.get("start_sec") and 
                                clip.get("end_sec") == prev.get("end_sec"))
                duplicate_footage = False
                findings.append(_finding(
                    "duplicate_footage", "warn",
                    f"same source range reused near segment {prev.get('segment')}",
                ))
                if not is_exact_dup:
                    overlap_free = False
                    findings.append(_finding(
                        "overlap_free", "fail",
                        f"source overlaps previous segment {prev.get('segment')}",
                    ))
                break

        stitch_gap = clip.get("stitch_gap_sec")
        stitch_gap_ok = True
        if clip.get("is_stitched") and stitch_gap is not None and float(stitch_gap) > max_stitch_gap_sec:
            stitch_gap_ok = False
            findings.append(_finding(
                "stitch_gap_ok", "fail",
                f"stitched gap {float(stitch_gap):.3f}s exceeds {max_stitch_gap_sec:.3f}s",
            ))

        status = "fail" if any(f["level"] == "fail" for f in findings) else (
            "warn" if findings else "pass"
        )
        checks.append({
            "segment": clip.get("segment"),
            "shot_idx": clip.get("shot_idx"),
            "status": status,
            "checks": {
                "time_range_parseable": clip.get("start_sec") is not None and clip.get("end_sec") is not None,
                "duration_match": duration_match,
                "overlap_free": overlap_free,
                "duplicate_footage": duplicate_footage,
                "stitch_gap_ok": stitch_gap_ok,
                "min_duration_ok": min_duration_ok,
            },
            "findings": findings,
            "next_route": "node_10_timeline_build" if findings else None,
        })

    status = "fail" if any(c["status"] == "fail" for c in checks) else (
        "warn" if any(c["status"] == "warn" for c in checks) else "pass"
    )
    return {
        "editor_review_version": 1,
        "status": status,
        "contract_hash": timeline.get("contract_hash"),
        "clip_checks": checks,
    }


def write_editor_review(timeline, out_path, **kwargs):
    review = review_timeline_build(timeline, **kwargs)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(review, f, ensure_ascii=False, indent=2)
    return {"ok": True, "editor_review": str(out_path), "review": review}
