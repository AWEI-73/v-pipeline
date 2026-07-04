"""music_structure.py — V3 P1 music timing artifact.

Turn detected tempo/beats into a small JSON artifact that Node 5/7/9/10 can
consume without re-running audio analysis or rereading long logs.
"""
import json
import re
import subprocess
from pathlib import Path


def _segment_role(segment):
    return (
        segment.get("section_role")
        or (segment.get("core") or {}).get("section_role")
        or (segment.get("editing_intent") or {}).get("segment_role")
        or segment.get("title")
        or ""
    ).lower()


def plan_music_alignment(script, timing, music_structure):
    """Align a narrative climax to the highest-energy music section."""
    timing_by_segment = {
        item.get("segment"): item for item in (timing or {}).get("segments", [])
    }
    climax = next((seg for seg in script or [] if _segment_role(seg) == "climax"), None)
    sections = (music_structure or {}).get("sections") or []
    energy_sections = [
        section for section in sections
        if isinstance(section.get("energy_score"), (int, float))
        and isinstance(section.get("start_sec"), (int, float))
    ]
    if not climax or not energy_sections or climax.get("segment") not in timing_by_segment:
        return {
            "artifact_role": "music_alignment_plan",
            "version": 1,
            "bgm_offset_sec": 0.0,
            "reason": "no_climax_or_energy_section",
        }

    climax_start = float(timing_by_segment[climax["segment"]].get("start_sec") or 0.0)
    energy = max(energy_sections, key=lambda section: float(section["energy_score"]))
    energy_start = float(energy["start_sec"])
    target_offset = max(0.0, energy_start - climax_start)
    structure_points = [
        float(section["start_sec"]) for section in sections
        if isinstance(section.get("start_sec"), (int, float))
    ] or [0.0]
    offset = min(structure_points, key=lambda point: (abs(point - target_offset), point))
    return {
        "artifact_role": "music_alignment_plan",
        "version": 1,
        "bgm_offset_sec": round(offset, 3),
        "climax_segment": climax["segment"],
        "climax_start_sec": round(climax_start, 3),
        "energy_section_index": energy.get("index"),
        "energy_section_start_sec": round(energy_start, 3),
        "alignment_error_sec": round(abs((energy_start - offset) - climax_start), 3),
        "reason": "climax_aligned_to_highest_energy_section",
    }


def write_music_alignment_plan(script, timing, music_structure, out_path):
    plan = plan_music_alignment(script, timing, music_structure)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
    return plan


def _detect_section_mean_volume(audio_path, start_sec, duration_sec):
    from .vt_core import FFMPEG  # noqa: PLC0415

    result = subprocess.run([
        FFMPEG, "-hide_banner", "-ss", f"{start_sec:.3f}", "-t", f"{duration_sec:.3f}",
        "-i", str(audio_path), "-af", "volumedetect", "-f", "null", "-",
    ], capture_output=True, text=True)
    match = re.search(r"mean_volume:\s*(-?\d+(?:\.\d+)?)\s*dB", result.stderr or "")
    return float(match.group(1)) if result.returncode == 0 and match else None


def _probe_audio_duration(audio_path):
    from .vt_core import FFPROBE  # noqa: PLC0415

    result = subprocess.run([
        FFPROBE,
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(audio_path),
    ], capture_output=True, text=True)
    if result.returncode != 0:
        return None
    try:
        duration = float((result.stdout or "").strip())
    except (TypeError, ValueError):
        return None
    return duration if duration > 0 else None


def annotate_section_energy(structure, audio_path, detector=None):
    """Populate existing sections with deterministic mean-volume energy scores."""
    if detector is None:
        if not Path(audio_path).exists():
            return structure
        detector = _detect_section_mean_volume
    for section in structure.get("sections") or []:
        start = section.get("start_sec")
        duration = section.get("duration_sec")
        if not isinstance(start, (int, float)) or not isinstance(duration, (int, float)):
            continue
        score = detector(str(audio_path), float(start), float(duration))
        if isinstance(score, (int, float)):
            section["energy_score"] = round(float(score), 3)
    return structure


def _fmt_mmss(seconds):
    seconds = max(0.0, float(seconds))
    total_tenths = int(round(seconds * 10))
    tenths = total_tenths % 10
    total_secs = total_tenths // 10
    mm = total_secs // 60
    ss = total_secs % 60
    return f"{mm:02d}:{ss:02d}.{tenths}"


def _density_hint(duration, beats):
    if duration <= 0:
        return "low"
    bps = max(0, len(beats) - 1) / duration
    if bps >= 2.2:
        return "high"
    if bps >= 1.0:
        return "medium"
    return "low"


def build_music_structure(tempo_bpm, beat_times, *, source_audio=None, every_n_beats=4):
    """Pure builder: tempo/beats -> normalized music_structure.json shape."""
    beats = [round(float(b), 3) for b in sorted(beat_times or [])]
    step = max(1, int(every_n_beats))
    sections = []
    for idx, start_i in enumerate(range(0, max(0, len(beats) - 1), step), 1):
        end_i = min(start_i + step, len(beats) - 1)
        start = beats[start_i]
        end = beats[end_i]
        if end <= start:
            continue
        sec_beats = beats[start_i:end_i + 1]
        dur = round(end - start, 3)
        sections.append({
            "index": idx,
            "name": f"Section {idx}",
            "description": "beat-derived music section",
            "Start_Time": _fmt_mmss(start),
            "End_Time": _fmt_mmss(end),
            "start_sec": start,
            "end_sec": end,
            "duration_sec": dur,
            "beat_count": len(sec_beats),
            "energy_score": None,
            "cut_density_hint": _density_hint(dur, sec_beats),
            "source": "beat_grid",
            "confidence": 0.6,
        })

    return {
        "music_structure_version": 1,
        "source_audio": str(source_audio) if source_audio is not None else None,
        "source": "librosa",
        "tempo_bpm": round(float(tempo_bpm), 3),
        "beat_count": len(beats),
        "beats": beats,
        "every_n_beats": step,
        "sections": sections,
    }


def _short_audio_fallback_section(duration):
    duration = round(float(duration), 3)
    return {
        "index": 1,
        "name": "Full track",
        "description": "short audio fallback section",
        "Start_Time": _fmt_mmss(0.0),
        "End_Time": _fmt_mmss(duration),
        "start_sec": 0.0,
        "end_sec": duration,
        "duration_sec": duration,
        "beat_count": 0,
        "energy_score": None,
        "cut_density_hint": "low",
        "source": "short_audio_fallback",
        "confidence": 0.3,
    }


def write_music_structure(audio_path, out_path, *, detector=None, every_n_beats=4,
                          duration_detector=None):
    """Detect beats and write music_structure.json. Detector is injectable for tests."""
    if detector is None:
        from .mv_cut import detect_beats  # noqa: PLC0415
        detector = detect_beats
    if duration_detector is None:
        duration_detector = _probe_audio_duration
    tempo, beats = detector(str(audio_path))
    structure = build_music_structure(
        tempo,
        beats,
        source_audio=str(audio_path),
        every_n_beats=every_n_beats,
    )
    if not structure.get("sections"):
        duration = duration_detector(str(audio_path))
        if isinstance(duration, (int, float)) and 0 < float(duration) <= 10.0:
            structure["sections"] = [_short_audio_fallback_section(float(duration))]
    annotate_section_energy(structure, audio_path)
    ok = bool(structure.get("sections"))
    errors = []
    next_action = None
    if not ok:
        errors = [{
            "rule": "music_structure_empty_sections",
            "message": "music_structure.json has no sections; rerun soundtrack probe or replace the selected music before BUILD",
            "beat_count": structure.get("beat_count"),
            "source_audio": structure.get("source_audio"),
        }]
        next_action = "repair_or_rerun_soundtrack_probe"
        structure["status"] = "blocked"
        structure["errors"] = errors
        structure["next_action"] = next_action
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(structure, f, ensure_ascii=False, indent=2)
    result = {"ok": ok, "music_structure": str(out_path), "structure": structure}
    if not ok:
        result.update({
            "stage": "music_structure",
            "errors": errors,
            "next_action": next_action,
        })
    return result
