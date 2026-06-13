"""keyframe_grid.py — Node 12 deterministic contact-sheet generation (P1-B).

Produces a stable keyframe grid (contact sheet) from a Render Candidate so a
human or an optional VLM can review visual coverage cheaply. Timestamp selection
is pure and deterministic; image tiling uses ffmpeg only. No model is required —
this is mechanical evidence.

Source: technique inspired by https://github.com/Hao0321/video-autopilot-kit
(MIT); reimplemented for this project's artifact contracts.
"""
import math
import os
import subprocess
import tempfile
from pathlib import Path


def select_timestamps(duration_sec, sample_count):
    """Deterministic, evenly spaced sample midpoints across ``duration_sec``.

    Avoids the very first/last frame by sampling the midpoint of each of
    ``sample_count`` equal segments.
    """
    duration_sec = float(duration_sec or 0)
    n = int(sample_count)
    if duration_sec <= 0 or n <= 0:
        return []
    return [round(duration_sec * (i + 0.5) / n, 3) for i in range(n)]


def scene_midpoints(shots, max_count):
    """純函式:場景區間 [(start,end)…] → 每景中點時間戳(最多 max_count 個)。

    景比 max_count 多時等距抽景(保持時間軸覆蓋)。比均勻取樣更有劇情代表性:
    每一格對應一個真實換幕段落,而不是落在隨機位置(時間軸蒙太奇設計,2026-06-12)。"""
    pts = [round((s + e) / 2.0, 3) for s, e in (shots or []) if e > s]
    if not pts:
        return []
    n = int(max_count)
    if n <= 0 or len(pts) <= n:
        return pts
    step = len(pts) / n
    return [pts[min(len(pts) - 1, int(i * step))] for i in range(n)]


def _ts_label(seconds):
    m, s = divmod(int(round(float(seconds))), 60)
    return f"[{m:02d}:{s:02d}]"


def resolve_grid_timestamps(duration_sec, sample_count, *, explicit=None, shots=None):
    """Resolve explicit, scene-aligned, or evenly-spaced grid timestamps."""
    if explicit is not None:
        return [round(float(value), 3) for value in explicit], "explicit"
    scene_points = scene_midpoints(shots or [], sample_count)
    if scene_points:
        return scene_points, "scene_midpoints"
    return select_timestamps(duration_sec, sample_count), "even"


def grid_dimensions(sample_count, columns):
    """Return ``(columns, rows)`` needed to hold ``sample_count`` cells."""
    n = int(sample_count)
    cols = max(1, int(columns))
    cols = min(cols, n) if n > 0 else cols
    rows = max(1, math.ceil(n / cols)) if n > 0 else 1
    return cols, rows


def probe_duration(video_path, ffprobe=None):
    """(I/O) Return the media duration in seconds via ffprobe."""
    if ffprobe is None:
        from .platform_tools import resolve_ffprobe
        ffprobe = resolve_ffprobe()
    r = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)],
        capture_output=True, text=True, timeout=60,
    )
    try:
        return float((r.stdout or "").strip())
    except (ValueError, AttributeError):
        return 0.0


def generate_keyframe_grid(video_path, out_path, *, sample_count=12, columns=4,
                           cell_width=480, cell_height=270, duration_sec=None,
                           ffmpeg=None, ffprobe=None, timestamps=None):
    """(I/O) Build a keyframe grid image and return its metadata.

    Returns a metadata dict suitable for ``visual_audit.json``::

        {grid, columns, rows, sample_count, cell_size, duration_sec, samples}
    """
    if ffmpeg is None:
        from .platform_tools import resolve_ffmpeg
        ffmpeg = resolve_ffmpeg()

    if duration_sec is None:
        duration_sec = probe_duration(video_path, ffprobe=ffprobe)

    # Scene-aligned sampling first (one cell per real cut = story-representative);
    # even spacing is the fallback when detection finds <2 scenes or is unavailable.
    sampling = "explicit" if timestamps is not None else "even"
    timestamps = [round(float(value), 3) for value in timestamps or []]
    if sampling == "explicit":
        cols, rows = grid_dimensions(len(timestamps), columns)
    else:
        timestamps = []
    try:
        if sampling == "explicit":
            raise RuntimeError("explicit timestamps supplied")
        from .mv_cut import detect_shots  # noqa: PLC0415 — lazy (scenedetect)
        shots = detect_shots(str(video_path))
        if len(shots) >= 2:
            timestamps = scene_midpoints(shots, sample_count)
            sampling = "scene_midpoints"
    except Exception:
        if sampling != "explicit":
            timestamps = []
    if not timestamps and sampling != "explicit":
        timestamps = select_timestamps(duration_sec, sample_count)
        sampling = "even"
    cols, rows = grid_dimensions(len(timestamps), columns)

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    samples = []
    with tempfile.TemporaryDirectory() as tmp:
        frame_paths = []
        scale_vf = f"scale={cell_width}:{cell_height}:force_original_aspect_ratio=decrease," \
                   f"pad={cell_width}:{cell_height}:(ow-iw)/2:(oh-ih)/2,setsar=1"
        # Burn the timestamp onto each cell (black box, yellow text) so the
        # reviewing agent/human can cite exact times straight off the montage.
        font_arg = ""
        try:
            from .platform_tools import resolve_font  # noqa: PLC0415
            fp = resolve_font()
            if fp and os.path.exists(fp):
                fp = fp.replace("\\", "/").replace(":", "\\:")
                font_arg = f"fontfile='{fp}':"
        except Exception:
            font_arg = ""
        fontsize = max(14, int(cell_height * 0.12))
        for i, ts in enumerate(timestamps):
            frame = os.path.join(tmp, f"frame_{i:03d}.jpg")
            label = _ts_label(ts).replace(":", "\\:")
            cell_vf = (f"{scale_vf},drawtext={font_arg}text='{label}':x=6:y=6:"
                       f"fontsize={fontsize}:fontcolor=yellow:box=1:"
                       f"boxcolor=black@0.7:boxborderw=5")
            r = subprocess.run(
                [ffmpeg, "-y", "-ss", f"{ts:.3f}", "-i", str(video_path),
                 "-frames:v", "1", "-q:v", "3", "-vf", cell_vf, frame],
                capture_output=True, timeout=120,
            )
            if r.returncode != 0:
                # drawtext can fail on exotic font setups — the grid itself is
                # the load-bearing evidence, so retry without the burn.
                r = subprocess.run(
                    [ffmpeg, "-y", "-ss", f"{ts:.3f}", "-i", str(video_path),
                     "-frames:v", "1", "-q:v", "3", "-vf", scale_vf, frame],
                    capture_output=True, timeout=120,
                )
            if r.returncode == 0 and os.path.exists(frame):
                frame_paths.append(frame)
                samples.append({"timestamp_sec": ts, "cell": len(frame_paths)})

        if frame_paths:
            # Re-number contiguous frames so the %03d pattern is gap-free.
            for new_idx, src in enumerate(frame_paths):
                dst = os.path.join(tmp, f"seq_{new_idx:03d}.jpg")
                if src != dst:
                    os.replace(src, dst)
            tile_cols, tile_rows = grid_dimensions(len(frame_paths), columns)
            cols, rows = tile_cols, tile_rows
            subprocess.run(
                [ffmpeg, "-y", "-framerate", "1", "-i", os.path.join(tmp, "seq_%03d.jpg"),
                 "-vf", f"tile={tile_cols}x{tile_rows}:padding=4", "-frames:v", "1", str(out_path)],
                capture_output=True, timeout=120, check=True,
            )

    return {
        "grid": out_path.name,
        "grid_path": str(out_path),
        "columns": cols,
        "rows": rows,
        "sample_count": len(samples),
        "sampling": sampling,
        "cell_size": [int(cell_width), int(cell_height)],
        "duration_sec": round(float(duration_sec), 3),
        "samples": samples,
    }
