"""Source video material matrix: window-level eye/ear evidence before editing."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Callable

from .keyframe_grid import probe_duration
from .montage_wall import write_image_contact_wall
from .platform_tools import resolve_ffmpeg
from .soundtrack_probe import build_soundtrack_probe


def _extract_frame(source: str | Path, timestamp_sec: float, out_path: str | Path) -> str:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [
            resolve_ffmpeg(),
            "-y",
            "-ss",
            f"{float(timestamp_sec):.3f}",
            "-i",
            str(source),
            "-frames:v",
            "1",
            "-q:v",
            "3",
            "-vf",
            "scale=512:-1",
            str(out),
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or "frame extraction failed")
    return str(out)


def _extract_audio(source: str | Path, out_path: str | Path) -> str:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [
            resolve_ffmpeg(),
            "-y",
            "-i",
            str(source),
            "-vn",
            "-ac",
            "2",
            "-ar",
            "44100",
            str(out),
        ],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or "audio extraction failed")
    return str(out)


def _is_no_audio_error(error: Exception) -> bool:
    text = str(error).lower()
    return (
        "does not contain any stream" in text
        or "output file #0 does not contain any stream" in text
        or "stream map" in text and "matches no streams" in text
    )


def _no_audio_probe(source_path: str, duration_sec: float) -> dict[str, Any]:
    return {
        "artifact_role": "soundtrack_probe_report",
        "version": 1,
        "pass": duration_sec > 0,
        "audio_file": source_path,
        "duration_sec": round(float(duration_sec), 3),
        "analysis_depth": "no_audio_stream",
        "features": {
            "has_audio": False,
            "codec": None,
            "mean_dbfs": None,
            "peak_dbfs": None,
            "silence_event_count": 0,
            "silence_total_sec": 0,
            "silence_ratio": None,
            "tempo_bpm": None,
            "beat_times": [],
            "energy_curve": [],
            "vocal_analysis": {
                "has_vocals": False,
                "method": "no_audio_stream",
            },
            "semantic_tags": ["no_audio_stream"],
        },
        "sections": [],
        "editing_fit": {
            "montage": "visual_only",
            "speech_underlay": "not_applicable",
            "ending_reflection": "visual_only",
        },
        "section_fit": [],
        "recommended_usage": [],
        "limitations": [
            "Input media has no audio stream; matrix audio fields are visual-only placeholders.",
        ],
    }


def _energy_at(probe: dict[str, Any], start: float, end: float) -> float | None:
    curve = ((probe.get("features") or {}) if isinstance(probe, dict) else {}).get("energy_curve") or []
    values = []
    for item in curve:
        try:
            item_start = float(item.get("start_sec"))
            item_end = float(item.get("end_sec"))
            energy = float(item.get("relative_energy"))
        except (TypeError, ValueError):
            continue
        if item_end <= start or item_start >= end:
            continue
        values.append(energy)
    return round(sum(values) / len(values), 3) if values else None


def _speech_overlap(probe: dict[str, Any], start: float, end: float) -> tuple[bool, list[dict[str, Any]]]:
    vocal = ((probe.get("features") or {}) if isinstance(probe, dict) else {}).get("vocal_analysis") or {}
    segments = []
    for item in vocal.get("segments") or []:
        try:
            item_start = float(item.get("start_sec"))
            item_end = float(item.get("end_sec"))
        except (TypeError, ValueError):
            continue
        if item_end <= start or item_start >= end:
            continue
        segments.append({
            "start_sec": item_start,
            "end_sec": item_end,
            "text": item.get("text"),
        })
    return bool(segments), segments


def _review_lookup(visual_review: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not isinstance(visual_review, dict):
        return {}
    decisions = visual_review.get("decisions") or []
    return {
        str(item.get("window_id")): item
        for item in decisions
        if isinstance(item, dict) and item.get("window_id")
    }


def _make_contact_sheet(windows: list[dict[str, Any]], out_path: str | Path) -> str:
    out = Path(out_path)
    items = []
    for window in windows:
        items.append({
            "window_id": window.get("window_id"),
            "shot_id": window.get("window_id"),
            "start_sec": window.get("start_sec", 0.0),
            "timestamp_sec": round((float(window.get("start_sec") or 0.0) + float(window.get("end_sec") or 0.0)) / 2.0, 3),
            "image_path": (window.get("visual") or {}).get("keyframe"),
        })
    write_image_contact_wall(items, out, out.with_suffix(".json"))
    return str(out)


def build_source_material_matrix(
    source: str | Path,
    *,
    out_dir: str | Path,
    window_sec: float = 12.0,
    duration_probe: Callable[[str | Path], float] | None = None,
    frame_extractor: Callable[[str | Path, float, str | Path], str] | None = None,
    audio_extractor: Callable[[str | Path, str | Path], str] | None = None,
    soundtrack_probe_builder: Callable[[str | Path], dict[str, Any]] | None = None,
    soundtrack_probe_path: str | Path | None = None,
    visual_review: dict[str, Any] | None = None,
) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    source_path = str(Path(source).resolve())
    duration = float((duration_probe or probe_duration)(source_path))

    audio_path = out / "source_audio.wav"
    if soundtrack_probe_path:
        soundtrack_probe = json.loads(Path(soundtrack_probe_path).read_text(encoding="utf-8-sig"))
        has_audio = ((soundtrack_probe.get("features") or {}) if isinstance(soundtrack_probe, dict) else {}).get("has_audio")
        if has_audio is False or soundtrack_probe.get("analysis_depth") == "no_audio_stream":
            audio_path = None
            audio_status = "no_audio_stream"
        else:
            audio_status = "precomputed_probe"
    else:
        try:
            (audio_extractor or _extract_audio)(source_path, audio_path)
        except RuntimeError as exc:
            if not _is_no_audio_error(exc):
                raise
            audio_path = None
            soundtrack_probe = _no_audio_probe(source_path, duration)
            audio_status = "no_audio_stream"
        else:
            soundtrack_probe = (soundtrack_probe_builder or build_soundtrack_probe)(audio_path)
            audio_status = "extracted"
    (out / "source_soundtrack_probe_report.json").write_text(
        json.dumps(soundtrack_probe, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    review = _review_lookup(visual_review)
    windows = []
    start = 0.0
    index = 0
    frames_dir = out / "source_matrix_frames"
    while start < duration:
        end = min(start + float(window_sec), duration)
        if end - start < 1.0:
            break
        midpoint = round((start + end) / 2.0, 3)
        window_id = f"win_{index:03d}"
        frame_path = frames_dir / f"{window_id}.jpg"
        frame_path.parent.mkdir(parents=True, exist_ok=True)
        (frame_extractor or _extract_frame)(source_path, midpoint, frame_path)
        decision = review.get(window_id) or {}
        has_speech, speech_segments = _speech_overlap(soundtrack_probe, start, end)
        windows.append({
            "window_id": window_id,
            "source_path": source_path,
            "start_sec": round(start, 3),
            "end_sec": round(end, 3),
            "duration_sec": round(end - start, 3),
            "visual": {
                "keyframe": str(frame_path),
                "review_status": "reviewed" if decision else "unreviewed",
                "content_type": decision.get("content_type"),
                "usable_for": decision.get("usable_for") or [],
                "note": decision.get("note"),
            },
            "audio": {
                "relative_energy": _energy_at(soundtrack_probe, start, end),
                "has_speech": has_speech,
                "speech_segments": speech_segments,
            },
            "selection": {
                "decision": decision.get("decision") or "undecided",
                "reject_reason": decision.get("reject_reason"),
            },
        })
        index += 1
        if end >= duration:
            break
        start += float(window_sec)

    contact_sheet_path = out / "source_material_matrix_contact_sheet.jpg"
    _make_contact_sheet(windows, contact_sheet_path)

    matrix = {
        "artifact_role": "source_material_matrix",
        "version": 1,
        "source_path": source_path,
        "duration_sec": round(duration, 3),
        "window_sec": float(window_sec),
        "visual": {
            "contact_sheet": "source_material_matrix_contact_sheet.jpg",
            "contact_sheet_index": "source_material_matrix_contact_sheet.json",
            "frames_dir": "source_matrix_frames",
        },
        "audio": {
            "source_audio": str(audio_path) if audio_path else None,
            "audio_status": audio_status,
            "soundtrack_probe_report": "source_soundtrack_probe_report.json",
        },
        "windows": windows,
        "next_action": "review_source_material_matrix",
        "limitations": [
            "Visual labels are unreviewed until source_material_matrix_review decisions are applied.",
            "Audio evidence comes from soundtrack_probe and should be treated as rough decision support.",
        ],
    }
    (out / "source_material_matrix.json").write_text(
        json.dumps(matrix, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return matrix
