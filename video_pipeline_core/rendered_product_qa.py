"""Rendered product QA owner checks for rehearsal/final candidates."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable


CANDIDATE_VIDEO_NAMES = (
    "final.mp4",
    "final_v7.mp4",
    "final_v6.mp4",
    "final_v5.mp4",
    "final_v4.mp4",
    "final_v3.mp4",
    "final_v2.mp4",
    "final_copyedit_rehearsal.mp4",
    "delivery_candidate.mp4",
    "verified_preview.mp4",
)


def _rel(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)


def find_rendered_candidate(run: str | Path) -> Path | None:
    root = Path(run)
    for name in CANDIDATE_VIDEO_NAMES:
        candidate = root / name
        if candidate.is_file() and candidate.stat().st_size > 0:
            return candidate
    return None


def probe_video(path: str | Path) -> dict[str, Any]:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-show_streams",
        "-of",
        "json",
        str(path),
    ]
    try:
        completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", timeout=60)
    except (OSError, subprocess.SubprocessError) as exc:
        return {"ok": False, "command": command, "error": str(exc), "raw": None}
    try:
        raw = json.loads(completed.stdout or "{}")
    except json.JSONDecodeError:
        raw = {}
    duration = 0.0
    try:
        duration = float((raw.get("format") or {}).get("duration") or 0)
    except (TypeError, ValueError):
        duration = 0.0
    return {
        "ok": completed.returncode == 0 and bool(raw),
        "command": command,
        "exit_code": completed.returncode,
        "stderr": completed.stderr,
        "duration_sec": duration,
        "streams": raw.get("streams") or [],
        "raw": raw,
    }


def sample_frames(video: str | Path, out_dir: str | Path) -> dict[str, Any]:
    out = Path(out_dir)
    frames_dir = out / "rendered_product_qa_frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    frame = frames_dir / "frame_000.jpg"
    command = [
        "ffmpeg",
        "-y",
        "-v",
        "error",
        "-i",
        str(video),
        "-frames:v",
        "1",
        str(frame),
    ]
    try:
        completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", timeout=120)
    except (OSError, subprocess.SubprocessError) as exc:
        return {"ok": False, "command": command, "error": str(exc), "frames": [], "contact_sheet": None}
    frames = [frame] if completed.returncode == 0 and frame.is_file() and frame.stat().st_size > 0 else []
    contact_sheet = out / "rendered_product_qa_contact_sheet.jpg"
    if frames:
        shutil.copyfile(frames[0], contact_sheet)
    return {
        "ok": bool(frames),
        "command": command,
        "exit_code": completed.returncode,
        "stderr": completed.stderr,
        "frames": frames,
        "contact_sheet": contact_sheet if contact_sheet.is_file() else None,
    }


def _block(rule: str, message: str, artifact: str | None = None) -> dict[str, Any]:
    return {"rule": rule, "message": message, "artifact": artifact}


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _has_rendered_evidence(payload: dict[str, Any] | None) -> bool:
    if not payload:
        return False
    for key in ("frame_evidence", "frame_evidence_refs", "rendered_frame_evidence", "sampled_frames"):
        value = payload.get(key)
        if isinstance(value, list) and value:
            return True
        if isinstance(value, str) and value.strip():
            return True
    return bool(payload.get("contact_sheet") or payload.get("representative_frame"))


def build_rendered_product_qa(
    run: str | Path,
    out_dir: str | Path,
    *,
    probe_func: Callable[[Path], dict[str, Any]] = probe_video,
    sampler_func: Callable[[Path, Path], dict[str, Any]] = sample_frames,
) -> dict[str, Any]:
    root = Path(run)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    blocking: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    candidate = find_rendered_candidate(root)
    probe: dict[str, Any] | None = None
    sampled: dict[str, Any] = {"ok": False, "frames": [], "contact_sheet": None}

    if candidate is None:
        blocking.append(_block("missing_rendered_candidate", "no rendered rehearsal/final candidate found"))
    else:
        probe = probe_func(candidate)
        streams = probe.get("streams") or []
        has_video = any(stream.get("codec_type") == "video" for stream in streams if isinstance(stream, dict))
        has_audio = any(stream.get("codec_type") == "audio" for stream in streams if isinstance(stream, dict))
        if not probe.get("ok"):
            blocking.append(_block("ffprobe_failed", "ffprobe could not inspect rendered candidate", _rel(root, candidate)))
        if probe.get("ok") and not has_video:
            blocking.append(_block("missing_video_stream", "rendered candidate lacks a video stream", _rel(root, candidate)))
        if probe.get("ok") and not has_audio:
            blocking.append(_block("missing_audio_stream", "rendered candidate lacks an audio stream", _rel(root, candidate)))
        if probe.get("ok") and float(probe.get("duration_sec") or 0) <= 0:
            blocking.append(_block("invalid_duration", "rendered candidate duration is not positive", _rel(root, candidate)))
        sampled = sampler_func(candidate, out)
        if not sampled.get("ok"):
            blocking.append(_block("missing_frame_evidence", "rendered product QA requires sampled frame/contact-sheet evidence", _rel(root, candidate)))

    title_qa = _load_json(root / "title_effect_lifecycle_qa.json")
    if title_qa is not None and title_qa.get("pass") is True and not _has_rendered_evidence(title_qa):
        blocking.append(_block(
            "title_effect_evidence_missing",
            "title/effect lifecycle QA exists but lacks rendered frame evidence",
            "title_effect_lifecycle_qa.json",
        ))
    source_speech_qa = _load_json(root / "source_speech_subtitle_qa.json")
    if source_speech_qa is not None and source_speech_qa.get("pass") is not True:
        warnings.append({
            "rule": "source_speech_subtitle_qa_not_passed",
            "artifact": "source_speech_subtitle_qa.json",
            "message": "source-speech subtitle QA is present but not passing; delivery gate may still block",
        })

    frames = [str(Path(frame).resolve()) for frame in sampled.get("frames") or []]
    contact_sheet = sampled.get("contact_sheet")
    return {
        "artifact_role": "rendered_product_qa",
        "version": 1,
        "source_tool": "tools/rendered_product_qa.py",
        "generated_by": "tools/rendered_product_qa.py",
        "run": str(root),
        "candidate": str(candidate) if candidate else None,
        "pass": not blocking,
        "blocking": blocking,
        "warnings": warnings,
        "ffprobe": probe,
        "frame_evidence": frames,
        "sampled_frames": frames,
        "contact_sheet": str(Path(contact_sheet).resolve()) if contact_sheet else None,
        "limitations": [
            "does_not_clear_creative_approval",
            "does_not_clear_legal_or_music_approval",
            "does_not_clear_human_story_approval",
        ],
    }


def write_rendered_product_qa(run: str | Path, out_dir: str | Path) -> dict[str, Any]:
    result = build_rendered_product_qa(run, out_dir)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "rendered_product_qa.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return result
