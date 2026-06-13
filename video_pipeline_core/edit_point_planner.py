"""Meaningful edit-point planning from speech, scene, and motion evidence."""
from __future__ import annotations

import copy


def _intersecting_speech(start, end, speech_runs):
    return [
        run for run in speech_runs or []
        if run.get("kind") == "speech"
        and float(run.get("start") or 0) < end
        and start < float(run.get("end") or 0)
    ]


def plan_edit_window(start, duration, *, keep_audio=False, speech_runs=None,
                     scene_cuts=None, motion_peaks=None, tolerance=0.5):
    """Choose one edit window with priority speech > scene > motion."""
    start = float(start)
    duration = float(duration)
    end = start + duration
    speech = _intersecting_speech(start, end, speech_runs)
    if keep_audio and speech:
        return {
            "start": min(float(run["start"]) for run in speech),
            "end": max(float(run["end"]) for run in speech),
            "adjusted": True,
            "reason": "speech_boundary",
        }
    for reason, points in (("scene_boundary", scene_cuts), ("motion_peak", motion_peaks)):
        for point in sorted(float(value) for value in points or []):
            if start + tolerance < point < end - tolerance:
                return {
                    "start": point,
                    "end": point + duration,
                    "adjusted": True,
                    "reason": reason,
                }
    return {"start": start, "end": end, "adjusted": False, "reason": None}


def derive_motion_phases(scene, *, rise_lead_sec=1.0, settle_tail_sec=1.0):
    """Derive action phases from mapped peaks, bounded by the scene."""
    if scene.get("bridge"):
        return []
    start = float(scene.get("start") or 0)
    end = float(scene.get("end") or 0)
    return [{
        "rise": round(max(start, float(peak) - float(rise_lead_sec)), 3),
        "peak": round(float(peak), 3),
        "settle": round(min(end, float(peak) + float(settle_tail_sec)), 3),
    } for peak in scene.get("motion_peaks") or []]


def plan_action_window(scene, *, phase_index=0, rise_lead_sec=1.0, settle_tail_sec=1.0):
    phases = derive_motion_phases(
        scene, rise_lead_sec=rise_lead_sec, settle_tail_sec=settle_tail_sec,
    )
    if not phases or phase_index >= len(phases):
        return None
    phase = phases[phase_index]
    return {
        "start": phase["rise"],
        "end": phase["settle"],
        "duration": round(phase["settle"] - phase["rise"], 3),
        "reason": "motion_phase",
        "phase": phase,
    }


def plan_render_edit_points(render_plan, material_maps, *, rise_lead_sec=1.0,
                            settle_tail_sec=1.0):
    """Apply mapped M3 edit points to a concrete render plan."""
    maps_by_source = {str(item.get("source")): item for item in material_maps or []}
    maps_by_id = {str(item.get("asset_id")): item for item in material_maps or []}
    result = []
    for item in render_plan or []:
        planned = copy.deepcopy(item)
        source = str(item.get("source") or item.get("source_path") or "")
        material_map = maps_by_source.get(source)
        scene = None
        scene_id = item.get("scene_id")
        if scene_id and ":" in str(scene_id):
            asset_id, raw_index = str(scene_id).rsplit(":", 1)
            material_map = maps_by_id.get(asset_id) or material_map
            try:
                scene = (material_map or {}).get("scenes", [])[int(raw_index)]
            except (ValueError, IndexError):
                scene = None
        if item.get("keep_audio") and material_map:
            window = plan_edit_window(
                item.get("extract_start") or item.get("start_sec") or 0,
                item.get("extract_dur") or item.get("duration_sec") or 0,
                keep_audio=True,
                speech_runs=material_map.get("speech"),
            )
            if window["adjusted"]:
                planned["original_extract_start"] = float(
                    item.get("extract_start") or item.get("start_sec") or 0
                )
                planned["extract_start"] = window["start"]
                planned["extract_dur"] = round(window["end"] - window["start"], 3)
                planned["adjustment_reason"] = window["reason"]
        elif scene and item.get("beat_alignment") == "action":
            window = plan_action_window(
                scene, rise_lead_sec=rise_lead_sec, settle_tail_sec=settle_tail_sec,
            )
            if window:
                planned["original_extract_start"] = float(
                    item.get("extract_start") or item.get("start_sec") or 0
                )
                planned["extract_start"] = window["start"]
                planned["extract_dur"] = window["duration"]
                planned["adjustment_reason"] = window["reason"]
                planned["motion_phase"] = window["phase"]
        result.append(planned)
    return result
