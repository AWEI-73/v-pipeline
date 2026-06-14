"""Tier-1 technical defect audit: black and blank/flat frame runs.

The 2026-06-13 graduation montage shipped a pure-black frame (~03:13) and a
near-all-white caption card (~09:13) that the existing VERIFY never caught.
This audit samples rendered luma deterministically and fails on sustained
black or blank runs. Pure run-detection is separated from the ffmpeg probe so
the decision logic is testable without a real video.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path


_YMIN = re.compile(r"lavfi\.signalstats\.YMIN=([0-9.]+)")
_YMAX = re.compile(r"lavfi\.signalstats\.YMAX=([0-9.]+)")
_YAVG = re.compile(r"lavfi\.signalstats\.YAVG=([0-9.]+)")


def _classify(sample, *, black_luma_max, blank_luma_min, flat_range_max):
    """Return 'black', 'blank', or None for one luma sample."""
    avg = float(sample.get("luma_avg", 128.0))
    spread = float(sample.get("luma_range", 255.0))
    if avg <= black_luma_max:
        return "black"
    if avg >= blank_luma_min and spread <= flat_range_max:
        return "blank"
    return None


def find_defect_runs(samples, *, interval_sec=0.5, black_luma_max=16.0,
                     blank_luma_min=235.0, flat_range_max=12.0, min_run_sec=0.4):
    """Group consecutive black/blank luma samples into runs >= min_run_sec."""
    ordered = sorted(samples or [], key=lambda item: float(item.get("t", 0.0)))
    interval = float(interval_sec)
    runs = []
    current = None
    for sample in ordered:
        kind = _classify(
            sample,
            black_luma_max=black_luma_max,
            blank_luma_min=blank_luma_min,
            flat_range_max=flat_range_max,
        )
        t = float(sample.get("t", 0.0))
        if kind and current and current["kind"] == kind:
            current["end"] = t
            current["_count"] += 1
        elif kind:
            if current:
                runs.append(current)
            current = {"kind": kind, "start": t, "end": t, "_count": 1}
        else:
            if current:
                runs.append(current)
            current = None
    if current:
        runs.append(current)

    finished = []
    for run in runs:
        # one sample covers `interval` seconds of footage
        duration = round((run["end"] - run["start"]) + interval, 3)
        if duration + 1e-6 >= float(min_run_sec):
            finished.append({
                "kind": run["kind"],
                "start_sec": round(run["start"], 3),
                "end_sec": round(run["end"] + interval, 3),
                "duration_sec": duration,
            })
    return finished


def probe_luma_samples(video_path, *, fps=2.0, ffmpeg=None):
    """Sample per-frame luma via ffmpeg signalstats. Decode failure -> []."""
    if ffmpeg is None:
        try:
            from .platform_tools import resolve_ffmpeg
            ffmpeg = resolve_ffmpeg()
        except Exception:
            ffmpeg = "ffmpeg"
    try:
        result = subprocess.run(
            [ffmpeg, "-hide_banner", "-i", str(video_path),
             "-vf", f"fps={float(fps)},signalstats,metadata=print",
             "-f", "null", "-"],
            capture_output=True, text=True, check=False,
        )
    except (OSError, ValueError):
        return []
    # signalstats prints one metric per line; YMIN..YAVG..YMAX repeat per frame.
    # Accumulate a frame block and flush it when the next YMIN opens a new frame.
    samples = []
    index = 0
    ymin = ymax = yavg = None

    def flush():
        nonlocal index
        if yavg is None:
            return
        spread = (ymax - ymin) if (ymin is not None and ymax is not None) else 255.0
        samples.append({
            "t": round(index / float(fps), 3),
            "luma_avg": yavg,
            "luma_range": spread,
        })
        index += 1

    for line in (result.stderr or "").splitlines():
        m = _YMIN.search(line)
        if m:
            flush()
            ymin, ymax, yavg = float(m.group(1)), None, None
            continue
        m = _YMAX.search(line)
        if m:
            ymax = float(m.group(1))
            continue
        m = _YAVG.search(line)
        if m:
            yavg = float(m.group(1))
    flush()
    return samples


def audit_black_frames(video_path, *, sampler=None, fps=2.0, black_luma_max=16.0,
                       blank_luma_min=235.0, flat_range_max=12.0, min_run_sec=0.4):
    """Deterministic tier-1 audit over a rendered video's luma profile."""
    sample_fn = sampler or (lambda path: probe_luma_samples(path, fps=fps))
    samples = sample_fn(video_path)
    if not samples:
        return {
            "artifact_role": "black_frame_audit",
            "version": 1,
            "pass": False,
            "reason": "sample_unavailable",
            "metrics": {"defect_run_count": 0, "sampled_frames": 0},
            "findings": [{
                "check": "luma_sample_unavailable",
                "level": "fail",
                "message": "rendered video could not be sampled for black/blank frames",
                "fix_class": "verify",
                "next_route": "verify_failed",
            }],
            "next_action": "verify_failed",
        }
    runs = find_defect_runs(
        samples,
        interval_sec=1.0 / float(fps),
        black_luma_max=black_luma_max,
        blank_luma_min=blank_luma_min,
        flat_range_max=flat_range_max,
        min_run_sec=min_run_sec,
    )
    findings = [{
        "check": f"{run['kind']}_frame_run",
        "level": "fail",
        "kind": run["kind"],
        "start_sec": run["start_sec"],
        "end_sec": run["end_sec"],
        "duration_sec": run["duration_sec"],
        "message": (f"{run['kind']} frames for {run['duration_sec']:.2f}s "
                    f"at {run['start_sec']:.2f}-{run['end_sec']:.2f}s"),
        "fix_class": "render",
        "next_route": "fix_timeline_or_assembly",
    } for run in runs]
    return {
        "artifact_role": "black_frame_audit",
        "version": 1,
        "pass": not findings,
        "metrics": {
            "defect_run_count": len(runs),
            "sampled_frames": len(samples),
        },
        "findings": findings,
        "next_action": "fix_timeline_or_assembly" if findings else None,
    }


def write_black_frame_audit(video_path, out_path, **kwargs):
    result = audit_black_frames(video_path, **kwargs)
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "black_frame_audit": str(path), "result": result}
