"""Deterministic per-asset evidence maps for material-supply planning."""
from __future__ import annotations

import json
import multiprocessing
import os
import re
import subprocess
import traceback
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError


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


def build_fast_asset_map(entry):
    """Build a coarse per-asset map without expensive video detectors."""
    asset_id = entry.get("id") or entry.get("asset_id") or os.path.basename(str(entry.get("path") or ""))
    source = entry.get("path") or entry.get("source") or entry.get("display_path")
    kind = _asset_type(entry)
    duration = _duration(entry)
    if kind == "photo":
        scenes = [{
            "start": 0.0,
            "end": 0.0,
            "midpoint": 0.0,
            "kind": "still",
            "motion_peaks": [],
            "map_mode": "fast",
        }]
    else:
        scenes = [{
            "start": 0.0,
            "end": round(duration, 3),
            "midpoint": round(duration / 2.0, 3),
            "kind": "video",
            "motion_peaks": [],
            "map_mode": "fast",
        }]
    return {
        "artifact_role": "material_map",
        "version": 1,
        "asset_id": asset_id,
        "asset_type": kind,
        "source": source,
        "duration_sec": duration,
        "map_mode": "fast",
        "scenes": scenes,
        "speech": [],
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


def _build_asset_map_process(queue, entry):
    try:
        queue.put({"ok": True, "value": build_asset_map(entry)})
    except BaseException as exc:  # pragma: no cover - defensive child process path.
        queue.put({
            "ok": False,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        })


def _build_with_thread_timeout(entry, map_builder, timeout_sec):
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(map_builder, entry)
    try:
        return future.result(timeout=float(timeout_sec))
    except FutureTimeoutError as exc:
        future.cancel()
        raise TimeoutError(f"material map timed out after {timeout_sec}s") from exc
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


def _build_with_process_timeout(entry, timeout_sec):
    queue = multiprocessing.Queue()
    process = multiprocessing.Process(target=_build_asset_map_process, args=(queue, entry))
    process.start()
    process.join(float(timeout_sec))
    if process.is_alive():
        process.terminate()
        process.join(5)
        raise TimeoutError(f"material map timed out after {timeout_sec}s")
    if queue.empty():
        raise RuntimeError("material map worker exited without a result")
    payload = queue.get()
    if payload.get("ok"):
        return payload["value"]
    raise RuntimeError(payload.get("error") or "material map worker failed")


def _build_asset_map_guarded(entry, *, asset_timeout_sec=None, map_builder=None, fast=False):
    builder = map_builder or (build_fast_asset_map if fast else build_asset_map)
    if asset_timeout_sec is None or float(asset_timeout_sec) <= 0:
        return builder(entry)
    if builder is build_asset_map:
        return _build_with_process_timeout(entry, asset_timeout_sec)
    return _build_with_thread_timeout(entry, builder, asset_timeout_sec)


def _write_update_db(path, materials_db):
    if not path:
        return
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(materials_db, handle, ensure_ascii=False, indent=2)


def _mark_material_map_error(entry, reason, message):
    entry.pop("material_map", None)
    entry["material_map_status"] = "skipped"
    entry["material_map_error"] = {
        "reason": reason,
        "message": str(message),
    }


def write_material_maps(materials_db, maps_dir, *, limit=None, selected_only=False,
                        asset_timeout_sec=None, update_db_path=None, map_builder=None,
                        fast=False):
    """Write maps and record their paths on materials_db entries."""
    maps_dir = os.path.abspath(os.fspath(maps_dir))
    os.makedirs(maps_dir, exist_ok=True)
    maps = []
    entries = list(materials_db.get("files") or [])
    if selected_only:
        entries = [entry for entry in entries if entry.get("selected_for_material_map") is True]
    if limit is not None:
        entries = entries[:max(0, int(limit))]
    for entry in entries:
        try:
            material_map = _build_asset_map_guarded(
                entry,
                asset_timeout_sec=asset_timeout_sec,
                map_builder=map_builder,
                fast=fast,
            )
        except TimeoutError as exc:
            _mark_material_map_error(entry, "timeout", exc)
            _write_update_db(update_db_path, materials_db)
            continue
        except Exception as exc:  # Keep bounded operator passes moving.
            _mark_material_map_error(entry, "error", exc)
            _write_update_db(update_db_path, materials_db)
            continue
        path = os.path.join(maps_dir, f"{material_map['asset_id']}.map.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(material_map, handle, ensure_ascii=False, indent=2)
        entry["material_map"] = path
        entry["material_map_status"] = "mapped"
        entry.pop("material_map_error", None)
        maps.append(material_map)
        _write_update_db(update_db_path, materials_db)
    return maps
