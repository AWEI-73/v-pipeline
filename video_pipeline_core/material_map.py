"""Deterministic per-asset evidence maps for material-supply planning."""
from __future__ import annotations

import json
import os
import re
import subprocess


_SILENCE_START = re.compile(r"silence_start:\s*([0-9.]+)")
_SILENCE_END = re.compile(r"silence_end:\s*([0-9.]+)")


def parse_silencedetect_runs(stderr, duration_sec):
    """Convert ffmpeg silencedetect output into ordered speech/silence runs."""
    duration = max(0.0, float(duration_sec or 0))
    silence = []
    open_start = None
    for line in str(stderr or "").splitlines():
        start = _SILENCE_START.search(line)
        if start:
            open_start = float(start.group(1))
        end = _SILENCE_END.search(line)
        if end and open_start is not None:
            silence.append((open_start, float(end.group(1))))
            open_start = None
    if open_start is not None:
        silence.append((open_start, duration))

    runs = []
    cursor = 0.0
    for start, end in sorted(silence):
        start = max(cursor, min(duration, start))
        end = max(start, min(duration, end))
        if start > cursor:
            runs.append({"start": round(cursor, 3), "end": round(start, 3), "kind": "speech"})
        if end > start:
            runs.append({"start": round(start, 3), "end": round(end, 3), "kind": "silence"})
        cursor = end
    if cursor < duration:
        runs.append({"start": round(cursor, 3), "end": round(duration, 3), "kind": "speech"})
    return runs


def detect_speech_runs(source, duration_sec):
    """Run ffmpeg silencedetect. Decode failures return no speech evidence."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-hide_banner", "-i", str(source), "-af",
             "silencedetect=noise=-35dB:d=0.4", "-f", "null", "-"],
            capture_output=True,
            text=True,
            check=False,
        )
        return parse_silencedetect_runs(result.stderr, duration_sec)
    except (OSError, ValueError):
        return []


def _asset_type(entry):
    value = str(entry.get("type") or entry.get("asset_type") or "").lower()
    if value in ("photo", "image", "still"):
        return "photo"
    return "video" if value == "video" else value


def _duration(entry):
    metadata = entry.get("metadata") or {}
    return float(entry.get("duration_sec") or metadata.get("duration_sec") or 0)


def build_asset_map(entry, *, shot_detector=None, motion_detector=None, speech_detector=None,
                    transcript_detector=None):
    """Build one asset map. Injectable detectors keep the planning logic testable."""
    asset_id = entry.get("id") or entry.get("asset_id") or os.path.basename(str(entry.get("path") or ""))
    source = entry.get("path") or entry.get("source") or entry.get("display_path")
    kind = _asset_type(entry)
    duration = _duration(entry)

    if kind == "photo":
        scenes = [{
            "start": 0.0, "end": 0.0, "midpoint": 0.0, "kind": "still",
            "motion_peaks": [],
        }]
        speech = []
    else:
        if shot_detector is None:
            from .mv_cut import detect_shots
            shot_detector = detect_shots
        if motion_detector is None:
            from .edit_artifacts import detect_motion_peaks
            motion_detector = detect_motion_peaks
        speech_detector = speech_detector or detect_speech_runs
        spans = shot_detector(source)
        peaks = [float(value) for value in motion_detector(source)]
        scenes = []
        for start, end in spans:
            start, end = float(start), float(end)
            scenes.append({
                "start": round(start, 3),
                "end": round(end, 3),
                "midpoint": round((start + end) / 2, 3),
                "kind": "video",
                "motion_peaks": [round(p, 3) for p in peaks if start <= p < end],
            })
        speech = speech_detector(source, duration)
        if transcript_detector:
            for run in speech:
                if run.get("kind") == "speech":
                    text = transcript_detector(source, run)
                    if text:
                        run["text"] = str(text)

    return {
        "artifact_role": "material_map",
        "version": 1,
        "asset_id": asset_id,
        "asset_type": kind,
        "source": source,
        "duration_sec": duration,
        "scenes": scenes,
        "speech": speech,
    }


def apply_scene_review_verdict(material_map, verdict):
    """Apply agent/VLM scene captions without requiring a model dependency."""
    scenes = material_map.get("scenes") or []
    shallow_labels = ("visual_family", "angle_scale", "action_family", "subject")
    for item in verdict.get("scenes") or []:
        index = item.get("scene_index")
        if not isinstance(index, int) or index < 0 or index >= len(scenes):
            continue
        if item.get("caption"):
            scenes[index]["caption"] = str(item["caption"]).strip()
        if "bridge" in item:
            scenes[index]["bridge"] = bool(item["bridge"])
        if item.get("functions"):
            scenes[index]["functions"] = list(item["functions"])
        for field in shallow_labels:
            if item.get(field):
                scenes[index][field] = str(item[field]).strip()
    return material_map


def write_material_maps(materials_db, maps_dir):
    """Write maps and record their paths on materials_db entries."""
    os.makedirs(maps_dir, exist_ok=True)
    maps = []
    for entry in materials_db.get("files") or []:
        material_map = build_asset_map(entry)
        path = os.path.join(maps_dir, f"{material_map['asset_id']}.map.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(material_map, handle, ensure_ascii=False, indent=2)
        entry["material_map"] = path
        maps.append(material_map)
    return maps
