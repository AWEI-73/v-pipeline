"""Tier-1 semantic-novelty audit: perceptual de-duplication of timeline clips.

`new_visual_information_audit` dedups by file/window identity, so "different
file, same visible idea" (the 2026-06-13 graduation montage's repeated muster
shots) still passed with unique_source_ratio=1.0. This audit hashes a
representative frame per clip and clusters perceptually-similar compositions,
then fails long runs or low distinct ratio. Deterministic dHash, no model —
CLIP stays opt-in. Frame hashing is injectable so clustering is testable
without a real render.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path


def dhash(image_path, *, size=8):
    """64-bit difference hash of one image. Pure pixels, deterministic."""
    from PIL import Image
    with Image.open(image_path) as img:
        small = img.convert("L").resize((size + 1, size), Image.BILINEAR)
        pixels = list(small.getdata())
    bits = 0
    for row in range(size):
        base = row * (size + 1)
        for col in range(size):
            bits = (bits << 1) | int(pixels[base + col] < pixels[base + col + 1])
    return bits


def hamming(a, b):
    return bin(int(a) ^ int(b)).count("1")


def cluster_by_similarity(hashes, *, max_distance=10):
    """Greedy clustering: each hash joins the first cluster within max_distance."""
    representatives = []
    cluster_ids = []
    for value in hashes:
        if value is None:
            cluster_ids.append(None)
            continue
        assigned = None
        for cid, rep in enumerate(representatives):
            if rep is not None and hamming(value, rep) <= max_distance:
                assigned = cid
                break
        if assigned is None:
            representatives.append(value)
            assigned = len(representatives) - 1
        cluster_ids.append(assigned)
    return cluster_ids


def _extract_frame_dhash(video_path, timestamp, *, ffmpeg=None):
    if ffmpeg is None:
        try:
            from .platform_tools import resolve_ffmpeg
            ffmpeg = resolve_ffmpeg()
        except Exception:
            ffmpeg = "ffmpeg"
    with tempfile.TemporaryDirectory() as tmp:
        frame = os.path.join(tmp, "f.png")
        result = subprocess.run(
            [ffmpeg, "-y", "-ss", f"{float(timestamp):.3f}", "-i", str(video_path),
             "-frames:v", "1", "-vf", "scale=64:64", frame],
            capture_output=True, timeout=120,
        )
        if result.returncode != 0 or not os.path.exists(frame):
            return None
        return dhash(frame)


def audit_semantic_novelty(timeline, *, video_path=None, frame_hasher=None,
                           max_distance=10, min_distinct_ratio=0.5,
                           max_similar_run_sec=6.0):
    """Cluster perceptually-similar clips; fail long runs / low distinct ratio."""
    clips = timeline if isinstance(timeline, list) else (timeline or {}).get("clips") or []
    if not clips:
        return _result(True, [], {}, reason="no_clips")

    hasher = frame_hasher
    if hasher is None:
        if not video_path:
            # planning replay without a render cannot evaluate pixels
            return _result(True, [], {"clips": len(clips)}, reason="no_render")
        hasher = lambda ts: _extract_frame_dhash(video_path, ts)

    hashes = []
    for clip in clips:
        mid = (float(clip.get("timeline_in_sec") or 0)
               + float(clip.get("timeline_out_sec") or clip.get("timeline_in_sec") or 0)) / 2
        try:
            hashes.append(hasher(mid))
        except Exception:
            hashes.append(None)

    if all(value is None for value in hashes):
        return _result(True, [], {"clips": len(clips)}, reason="hash_unavailable")

    cluster_ids = cluster_by_similarity(hashes, max_distance=max_distance)
    distinct = len({cid for cid in cluster_ids if cid is not None})
    hashed = sum(1 for cid in cluster_ids if cid is not None)
    distinct_ratio = round(distinct / hashed, 4) if hashed else 1.0

    # longest consecutive run of the same perceptual cluster
    longest = 0.0
    run = 0.0
    prev = object()
    affected = set()
    for clip, cid in zip(clips, cluster_ids):
        dur = float(clip.get("duration_sec") or 0)
        if cid is not None and cid == prev:
            run += dur
        else:
            run = dur
        if run > longest:
            longest = run
        if cid is not None and cid == prev:
            affected.add(cid)
        prev = cid

    findings = []
    if distinct_ratio < float(min_distinct_ratio):
        findings.append({
            "check": "distinct_composition_ratio", "level": "fail",
            "value": distinct_ratio, "limit": float(min_distinct_ratio),
            "message": (f"only {distinct} distinct compositions across {hashed} clips "
                        f"(ratio {distinct_ratio}); different files repeat the same visible idea"),
            "fix_class": "material", "next_route": "curator",
        })
    if longest > float(max_similar_run_sec):
        findings.append({
            "check": "max_similar_composition_run_sec", "level": "fail",
            "value": round(longest, 3), "limit": float(max_similar_run_sec),
            "affected": sorted(affected),
            "message": (f"{longest:.1f}s of perceptually-similar compositions in a row "
                        f"exceeds {max_similar_run_sec}s"),
            "fix_class": "material", "next_route": "curator",
        })
    return _result(not findings, findings, {
        "clips": len(clips),
        "hashed_clips": hashed,
        "distinct_compositions": distinct,
        "distinct_composition_ratio": distinct_ratio,
        "max_similar_composition_run_sec": round(longest, 3),
    })


def _result(passed, findings, metrics, *, reason=None):
    out = {
        "artifact_role": "semantic_novelty_audit",
        "version": 1,
        "pass": bool(passed),
        "metrics": metrics,
        "findings": findings,
        "next_action": "curator" if findings else None,
    }
    if reason:
        out["reason"] = reason
    return out


def write_semantic_novelty_audit(timeline, out_path, **kwargs):
    result = audit_semantic_novelty(timeline, **kwargs)
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "semantic_novelty_audit": str(path), "result": result}
