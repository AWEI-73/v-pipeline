"""Four-layer visual evidence for dense VERIFY review."""
from __future__ import annotations

import json
from pathlib import Path


def _clips(timeline):
    return timeline if isinstance(timeline, list) else (timeline or {}).get("clips") or []


def _range_timestamps(start, end, count):
    start, end = float(start), float(end)
    if end <= start or int(count) <= 0:
        return []
    return [round(start + (end - start) * (i + 0.5) / int(count), 3)
            for i in range(int(count))]


def _timeline_duration(clips):
    return max((float(item.get("timeline_out_sec") or 0) for item in clips), default=0.0)


def build_evidence_plan(timeline, *, overview_samples=48, chapter_samples=16,
                        critical_samples=32):
    clips = _clips(timeline)
    duration = _timeline_duration(clips)
    chapters = []
    for segment in dict.fromkeys(item.get("segment") for item in clips):
        grouped = [item for item in clips if item.get("segment") == segment]
        start = min(float(item.get("timeline_in_sec") or 0) for item in grouped)
        end = max(float(item.get("timeline_out_sec") or start) for item in grouped)
        chapters.append({
            "segment": segment, "start": start, "end": end,
            "sample_count": int(chapter_samples),
            "timestamps": _range_timestamps(start, end, chapter_samples),
        })
    critical = []
    for item in clips:
        if not (item.get("keep_audio") or item.get("review_required")
                or item.get("adjustment_reason")):
            continue
        start = float(item.get("timeline_in_sec") or 0)
        end = float(item.get("timeline_out_sec") or start)
        critical.append({
            "segment": item.get("segment"), "start": start, "end": end,
            "reason": item.get("adjustment_reason")
                      or ("keep_audio" if item.get("keep_audio") else "review_required"),
            "sample_count": int(critical_samples),
            "timestamps": _range_timestamps(start, end, critical_samples),
        })
    return {
        "artifact_role": "verify_evidence_plan",
        "version": 1,
        "overview": {
            "start": 0.0, "end": duration, "sample_count": int(overview_samples),
            "timestamps": _range_timestamps(0, duration, overview_samples),
        },
        "chapters": chapters,
        "critical_segments": critical,
        "rhythm_strip": {
            "clip_count": len(clips),
            "duration_sec": round(duration, 3),
            "durations_sec": [float(item.get("duration_sec") or 0) for item in clips],
        },
    }


def write_rhythm_strip(timeline, out_path, *, width=1200, height=140):
    clips = _clips(timeline)
    duration = _timeline_duration(clips) or sum(
        float(item.get("duration_sec") or 0) for item in clips)
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    blocks = []
    x = 0.0
    palette = ("#2563eb", "#16a34a", "#ea580c", "#7c3aed", "#0891b2")
    for index, item in enumerate(clips):
        clip_duration = float(item.get("duration_sec") or 0)
        block_width = (clip_duration / duration * width) if duration else 0
        blocks.append(
            f'<rect x="{x:.2f}" y="30" width="{max(1, block_width):.2f}" '
            f'height="70" fill="{palette[index % len(palette)]}">'
            f'<title>{clip_duration:.3f}s</title></rect>')
        x += block_width
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}"><rect width="100%" height="100%" fill="#111827"/>'
        + "".join(blocks)
        + f'<text x="12" y="20" fill="white" font-family="Arial" font-size="14">'
          f'{len(clips)} clips / {duration:.3f}s</text></svg>'
    )
    path.write_text(svg, encoding="utf-8")
    return {"path": str(path), "clip_count": len(clips), "duration_sec": round(duration, 3)}


def write_verify_evidence(video_path, timeline, out_dir, **kwargs):
    from .keyframe_grid import generate_keyframe_grid
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    plan = build_evidence_plan(timeline, **kwargs)
    artifacts = {"chapters": [], "critical_segments": []}
    artifacts["overview"] = generate_keyframe_grid(
        video_path, out_dir / "overview_grid.jpg", columns=8,
        timestamps=plan["overview"]["timestamps"])
    for index, chapter in enumerate(plan["chapters"]):
        artifacts["chapters"].append(generate_keyframe_grid(
            video_path, out_dir / f"chapter_{index + 1:02d}_grid.jpg",
            columns=4, timestamps=chapter["timestamps"]))
    for index, critical in enumerate(plan["critical_segments"]):
        artifacts["critical_segments"].append(generate_keyframe_grid(
            video_path, out_dir / f"critical_{index + 1:02d}_grid.jpg",
            columns=8, timestamps=critical["timestamps"]))
    artifacts["rhythm_strip"] = write_rhythm_strip(timeline, out_dir / "rhythm_strip.svg")
    result = {
        "artifact_role": "verify_evidence_bundle",
        "version": 1,
        "video": str(video_path),
        "plan": plan,
        "artifacts": artifacts,
    }
    (out_dir / "verify_evidence_bundle.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result
