"""edit_artifacts.py — Node 9/10 build-facing JSON artifacts.

This module separates editing intent (`assembly_plan`) from concrete source
timestamps (`timeline_build`). Runtime can use these artifacts without
reinterpreting the canonical SPEC.
"""
import json
from pathlib import Path


def build_assembly_plan(script, *, music_structure=None, contract_hash=None):
    """Build Node 9 assembly_plan from generated MV payload."""
    contract_hash = contract_hash or script.get("_contract_hash")
    music_sections = (music_structure or {}).get("sections") or []
    default_music_anchor = music_sections[0].get("name") if music_sections else None
    segments = []
    for seg in script.get("segments", []):
        text = {k: seg.get(k) for k in ("label", "narrative", "subtitle", "name_super")
                if seg.get(k) is not None}
        segments.append({
            "segment": seg.get("segment"),
            "contract_segment": seg.get("_from_contract"),
            "story_purpose": seg.get("visual_desc"),
            "narrative_logic": seg.get("visual_desc"),
            "audio_role": seg.get("audio_role"),
            "text_layer": text or "none",
            "needs_review": bool(seg.get("needs_review")),
            "candidate_policy": {
                "required_traits": [seg["material_hint"]] if seg.get("material_hint") else [],
                "reject_traits": [],
                "must_include": seg.get("must_include"),
            },
            "shot_plan": {
                "target_duration_sec": None,
                "shots": [{
                    "candidate_class": seg.get("kind") or seg.get("layout") or seg.get("pace"),
                    "source_hint": seg.get("material_hint") or seg.get("search_query"),
                    "music_anchor": default_music_anchor,
                    "selection_reason": seg.get("visual_desc"),
                }],
            },
        })
    return {
        "assembly_plan_version": 1,
        "contract_hash": contract_hash,
        "music_section": {
            "source": "music_structure.json" if music_structure else None,
            "sections": [s.get("name") for s in music_sections],
        },
        "segments": segments,
    }


def _audio_policy(item):
    if item.get("audio_policy"):
        return item["audio_policy"]
    if item.get("keep_audio"):
        return "duck"
    return "music"


def _snap_to_scene_cut(start, duration, cuts, tolerance):
    for cut in sorted(float(c) for c in (cuts or [])):
        if start + tolerance < cut < start + duration - tolerance:
            return cut, cut + duration, True, "snapped_to_scene_cut"
    return start, start + duration, False, None


def build_timeline_build(render_plan, *, contract_hash=None, fps=30, resolution="1920x1080",
                         scene_cuts_by_source=None, scene_cut_tolerance_sec=0.5):
    """Build Node 10 timeline_build from concrete render plan clips."""
    clips = []
    cursor = 0.0
    for item in render_plan or []:
        dur = float(item.get("extract_dur") or item.get("duration_sec") or 0)
        source = item.get("source") or item.get("source_path")
        original_start = float(item.get("extract_start") or item.get("start_sec") or 0)
        start, end, adjusted, adjustment_reason = _snap_to_scene_cut(
            original_start,
            dur,
            (scene_cuts_by_source or {}).get(source),
            scene_cut_tolerance_sec,
        )
        timeline_in = float(item.get("timeline_in", cursor))
        timeline_out = timeline_in + dur
        segment = item.get("segment")
        crop_center = item.get("crop_center") or {}
        clips.append({
            "segment": segment,
            "provider": item.get("provider"),
            "shot_idx": item.get("slot_index"),
            "source_path": source,
            "original_start_sec": round(original_start, 3),
            "original_end_sec": round(original_start + dur, 3),
            "start_sec": round(start, 3),
            "end_sec": round(end, 3),
            "duration_sec": round(dur, 3),
            "adjusted": adjusted,
            "adjustment_reason": adjustment_reason,
            "target_duration_sec": item.get("slot_dur") or item.get("target_duration_sec"),
            "timeline_in_sec": round(timeline_in, 3),
            "timeline_out_sec": round(timeline_out, 3),
            "is_stitched": False,
            "crop": {
                "ratio": item.get("crop_ratio") or "16:9",
                "center_x": crop_center.get("x"),
                "center_y": crop_center.get("y"),
                "source": crop_center.get("source") or "center",
            },
            "audio_policy": _audio_policy(item),
            "transition": item.get("transition") or "cut",
            "text_overlay": item.get("text") or "none",
            "trace": {
                "segment_contract_segment": segment,
                "assembly_plan_segment": segment,
            },
        })
        cursor = timeline_out
    return {
        "timeline_build_version": 1,
        "contract_hash": contract_hash,
        "settings": {"fps": fps, "resolution": resolution},
        "clips": clips,
    }


def write_edit_artifacts(script, *, out_dir, music_structure=None, render_plan=None):
    """Write assembly_plan.json and optionally timeline_build.json."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    assembly = build_assembly_plan(script, music_structure=music_structure)
    assembly_path = out_dir / "assembly_plan.json"
    with assembly_path.open("w", encoding="utf-8") as f:
        json.dump(assembly, f, ensure_ascii=False, indent=2)

    result = {"assembly_plan": str(assembly_path)}
    if render_plan is not None:
        timeline = build_timeline_build(render_plan, contract_hash=script.get("_contract_hash"))
        timeline_path = out_dir / "timeline_build.json"
        with timeline_path.open("w", encoding="utf-8") as f:
            json.dump(timeline, f, ensure_ascii=False, indent=2)
        result["timeline_build"] = str(timeline_path)
    return result
