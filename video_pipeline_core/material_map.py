"""Deterministic per-asset evidence maps for material-supply planning."""
from __future__ import annotations

import json
import multiprocessing
import os
import re
import subprocess
import traceback
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from pathlib import Path

from .asset_paths import to_asset_ref


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


def _source_hash(entry):
    """Return a declared source binding without hashing media during map construction."""
    metadata = entry.get("metadata") or {}
    value = (
        entry.get("source_hash")
        or entry.get("sha256")
        or metadata.get("source_hash")
        or metadata.get("sha256")
    )
    return str(value).strip().lower() if value else None


def _filename_prior(source, entry):
    """Return a weak filename/folder prior; never treat it as observed truth."""
    path = Path(str(source or ""))
    tags = entry.get("tags_from_path") or []
    values = [path.stem, path.parent.name]
    if isinstance(tags, list):
        values.extend(str(tag) for tag in tags if str(tag).strip())
    return {
        "filename": path.name,
        "folder": path.parent.name,
        "text": " / ".join(value for value in values if value),
        "basis": "filename_folder_prior_only",
    }


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

    result = {
        "artifact_role": "material_map",
        "version": 1,
        "asset_id": asset_id,
        "asset_type": kind,
        "source": source,
        "duration_sec": duration,
        "scenes": scenes,
        "speech": speech,
    }
    source_hash = _source_hash(entry)
    if source_hash:
        result["source_hash"] = source_hash
    result["filename_prior"] = _filename_prior(source, entry)
    return result


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
    result = {
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
    source_hash = _source_hash(entry)
    if source_hash:
        result["source_hash"] = source_hash
    result["filename_prior"] = _filename_prior(source, entry)
    return result


def apply_scene_review_verdict(material_map, verdict):
    """Apply reviewed scene truth and its provenance without a model dependency.

    Filename/folder hints may help a reviewer find a scene, but only this
    reviewed payload becomes persistent material truth. Story assignment stays
    separate from observed content so later campaigns can reuse the same pool.
    """
    scenes = material_map.get("scenes") or []
    shallow_labels = ("visual_family", "angle_scale", "action_family", "subject")
    semantic_labels = (
        "observed_content", "assigned_story_function", "support_subtype",
    )
    default_reviewer = verdict.get("reviewer")
    default_at = verdict.get("at")
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
        for field in semantic_labels:
            if item.get(field):
                scenes[index][field] = str(item[field]).strip()
        if "direct_story_evidence" in item:
            scenes[index]["direct_story_evidence"] = bool(item["direct_story_evidence"])

        evidence = [
            str(value).strip()
            for value in (item.get("visual_evidence") or [])
            if isinstance(value, str) and value.strip()
        ]
        state = item.get("prior_disposition") or item.get("review_state")
        if state is not None:
            state = str(state).strip().lower()
            if state not in {"observed", "confirmed", "corrected"}:
                raise ValueError(
                    "scene review state must be observed, confirmed, or corrected")
        confidence = item.get("confidence")
        if confidence is not None:
            try:
                confidence = float(confidence)
            except (TypeError, ValueError):
                raise ValueError("scene review confidence must be a number from 0 to 1") from None
            if not 0.0 <= confidence <= 1.0:
                raise ValueError("scene review confidence must be a number from 0 to 1")

        has_review = bool(
            state or confidence is not None or evidence
            or item.get("evidence_basis") or item.get("reviewer") or default_reviewer
        )
        if has_review:
            review = dict(scenes[index].get("review") or {})
            review["state"] = state or review.get("state") or "observed"
            reviewer = item.get("reviewer") or default_reviewer
            at = item.get("at") or default_at
            if reviewer:
                review["reviewer"] = str(reviewer).strip()
            if at:
                review["at"] = str(at).strip()
            if confidence is not None:
                review["confidence"] = confidence
            if item.get("evidence_basis"):
                review["evidence_basis"] = str(item["evidence_basis"]).strip()
            if evidence:
                review["visual_evidence"] = evidence
            scenes[index]["review"] = review
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


def _run_dir_for_persisted_refs(maps_dir, update_db_path=None):
    if update_db_path:
        return os.path.dirname(os.path.abspath(os.fspath(update_db_path)))
    return os.path.dirname(os.path.abspath(os.fspath(maps_dir)))


def _material_map_for_persist(material_map, run_dir):
    payload = json.loads(json.dumps(material_map))
    source = payload.get("source")
    if isinstance(source, str) and source.strip():
        payload["source"] = to_asset_ref(run_dir, source).ref
    return payload


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
    run_dir = _run_dir_for_persisted_refs(maps_dir, update_db_path)
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
            json.dump(_material_map_for_persist(material_map, run_dir), handle, ensure_ascii=False, indent=2)
        entry["material_map"] = to_asset_ref(run_dir, path).ref
        entry["material_map_status"] = "mapped"
        entry.pop("material_map_error", None)
        maps.append(material_map)
        _write_update_db(update_db_path, materials_db)
    return maps
