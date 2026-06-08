"""edit_artifacts.py — Node 9/10 build-facing JSON artifacts.

This module separates editing intent (`assembly_plan`) from concrete source
timestamps (`timeline_build`). Runtime can use these artifacts without
reinterpreting the canonical SPEC.
"""
import json
from pathlib import Path


def _resolve_seg_treatment(seg, music_structure, editing_policy):
    """Opt-in material treatment for a script segment.

    Only segments that declare editing_intent.content_pattern or an explicit
    material_treatment get a treatment block; everything else is left untouched so
    existing runs are unaffected. Returns a dict to merge into the plan segment, or
    {} when the segment opts out.
    """
    ei = seg.get("editing_intent") or {}
    mt = seg.get("material_treatment") or {}
    if not ei.get("content_pattern") and not mt.get("treatment"):
        return {}
    try:
        from . import material_treatment  # noqa: PLC0415
    except Exception:
        return {}
    beats = (music_structure or {}).get("beats") or []
    beat_count = len(beats) if beats else 8
    seg_view = {
        "editing_intent": ei,
        "material_treatment": mt,
        "core": {"section_role": seg.get("section_role") or seg.get("kind")},
        "pacing": seg.get("pacing"),
        "duration_sec": seg.get("duration_sec"),
    }
    resolved = material_treatment.resolve_treatment(seg_view, beat_count, editing_policy)
    items = mt.get("items") or []
    return {
        "treatment": resolved["treatment"],
        "n_required": resolved["n_required"],
        "items": items,
        "label_per_item": bool(mt.get("label_per_item")),
        "lane_plan": resolved["lane_plan"],
        "treatment_reason": resolved["reason"],
    }


def build_assembly_plan(script, *, music_structure=None, contract_hash=None, editing_policy=None):
    """Build Node 9 assembly_plan from generated MV payload."""
    contract_hash = contract_hash or script.get("_contract_hash")
    music_sections = (music_structure or {}).get("sections") or []
    default_music_anchor = music_sections[0].get("name") if music_sections else None
    
    beats = (music_structure or {}).get("beats") or []
    total_dur = beats[-1] if beats else 0.0
    segs = script.get("segments", [])
    weights = [max(0.1, float(s["weight"])) if s.get("weight") is not None else 1.0
               for s in segs]
    wsum = sum(weights) or 1.0
    
    current_time = 0.0
    seg_timings = []
    for s, w in zip(segs, weights):
        budget = total_dur * w / wsum
        start = current_time
        end = current_time + budget
        seg_timings.append((start, end))
        current_time = end

    segments = []
    for idx, seg in enumerate(segs):
        text = {k: seg.get(k) for k in ("label", "narrative", "subtitle", "name_super")
                if seg.get(k) is not None}
        
        start_t, end_t = seg_timings[idx]
        seg_beats = [b for b in beats if start_t - 0.01 <= b <= end_t + 0.01]

        entry = {
            "segment": seg.get("segment"),
            "contract_segment": seg.get("_from_contract"),
            "story_purpose": seg.get("visual_desc"),
            "narrative_logic": seg.get("visual_desc"),
            "audio_role": seg.get("audio_role"),
            "text_layer": text or "none",
            "needs_review": bool(seg.get("needs_review")),
            "beat_grid": seg_beats,
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
        }
        treatment_info = _resolve_seg_treatment(seg, music_structure, editing_policy)
        entry.update(treatment_info)
        if seg.get("sequence_grammar"):
            try:
                from . import shot_slots  # noqa: PLC0415
                n_req = treatment_info.get("n_required")
                entry["shot_slots"] = shot_slots.expand_shot_slots(seg, n_required=n_req)
            except Exception:
                pass
        segments.append(entry)
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


def write_editorial_qa(out_dir, editing_policy=None):
    """Run editorial QA check and write editorial_qa.json to out_dir."""
    if not editing_policy:
        return None
    out_dir = Path(out_dir)
    
    # 1. brief.json
    brief_data = {}
    for p in [out_dir / "brief.json", out_dir.parent / "brief.json", out_dir.parent / "input" / "brief.json"]:
        if p.exists():
            try:
                with p.open(encoding="utf-8") as f:
                    brief_data = json.load(f)
                break
            except Exception:
                pass

    # 2. blueprint.json
    blueprint_data = {}
    for p in [out_dir / "blueprint.json", out_dir.parent / "blueprint.json", out_dir.parent / "input" / "blueprint.json"]:
        if p.exists():
            try:
                with p.open(encoding="utf-8") as f:
                    blueprint_data = json.load(f)
                break
            except Exception:
                pass

    # 3. assembly_plan.json
    assembly_data = {}
    p_assembly = out_dir / "assembly_plan.json"
    if p_assembly.exists():
        try:
            with p_assembly.open(encoding="utf-8") as f:
                assembly_data = json.load(f)
        except Exception:
            pass

    # 4. timeline_build.json
    timeline_data = {}
    p_timeline = out_dir / "timeline_build.json"
    if p_timeline.exists():
        try:
            with p_timeline.open(encoding="utf-8") as f:
                timeline_data = json.load(f)
        except Exception:
            pass

    # 5. treatment_audit.json
    treatment_data = {}
    p_treatment = out_dir / "treatment_audit.json"
    if p_treatment.exists():
        try:
            with p_treatment.open(encoding="utf-8") as f:
                treatment_data = json.load(f)
        except Exception:
            pass

    # 6. visual_fatigue_audit.json
    fatigue_data = {}
    p_fatigue = out_dir / "visual_fatigue_audit.json"
    if p_fatigue.exists():
        try:
            with p_fatigue.open(encoding="utf-8") as f:
                fatigue_data = json.load(f)
        except Exception:
            pass

    # 7. blueprint_coverage.json
    coverage_data = {}
    p_coverage = out_dir / "blueprint_coverage.json"
    if p_coverage.exists():
        try:
            with p_coverage.open(encoding="utf-8") as f:
                coverage_data = json.load(f)
        except Exception:
            pass

    # 8. verify_result.json
    verify_data = {}
    p_verify = out_dir / "verify_result.json"
    if p_verify.exists():
        try:
            with p_verify.open(encoding="utf-8") as f:
                verify_data = json.load(f)
        except Exception:
            pass

    # contract (can find from assembly_plan or contract_adapter/segment_contract.json)
    contract_data = {}
    for p in [out_dir / "segment_contract.json", out_dir.parent / "segment_contract.json", out_dir.parent / "input" / "segment_contract.json"]:
        if p.exists():
            try:
                with p.open(encoding="utf-8") as f:
                    contract_data = json.load(f)
                break
            except Exception:
                pass

    artifacts = {
        "brief": brief_data,
        "blueprint": blueprint_data,
        "contract": contract_data,
        "assembly_plan": assembly_data,
        "timeline_build": timeline_data,
        "treatment_audit": treatment_data,
        "visual_fatigue_audit": fatigue_data,
        "blueprint_coverage": coverage_data,
        "verify_result": verify_data,
    }

    from . import editorial_qa  # noqa: PLC0415
    qa_report = editorial_qa.review_editorial(artifacts)
    
    qa_path = out_dir / "editorial_qa.json"
    with qa_path.open("w", encoding="utf-8") as f:
        json.dump(qa_report, f, ensure_ascii=False, indent=2)
    return str(qa_path)


def write_edit_artifacts(script, *, out_dir, music_structure=None, render_plan=None,
                         editing_policy=None):
    """Write assembly_plan.json and optionally timeline_build.json.

    When any segment opted into a material treatment, also writes
    treatment_audit.json (Node 11), comparing the declared treatment against the
    rendered timeline. Inert (not written) when no segment declared a treatment.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    assembly = build_assembly_plan(script, music_structure=music_structure,
                                   editing_policy=editing_policy)
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

        # Node 11 treatment-fit audit (opt-in: only when a segment declared a treatment)
        if any(s.get("treatment") for s in assembly.get("segments", [])):
            from . import treatment_audit  # noqa: PLC0415
            audit = treatment_audit.audit_treatment(assembly, timeline)
            audit_path = out_dir / "treatment_audit.json"
            with audit_path.open("w", encoding="utf-8") as f:
                json.dump(audit, f, ensure_ascii=False, indent=2)
            result["treatment_audit"] = str(audit_path)

        # Node 11 visual-fatigue audit (opt-in: only when an editing_policy is set,
        # so runs without the editorial layer are unaffected).
        if editing_policy:
            from . import visual_fatigue  # noqa: PLC0415
            vfa = visual_fatigue.audit_visual_fatigue(assembly, timeline, editing_policy)
            vfa_path = out_dir / "visual_fatigue_audit.json"
            with vfa_path.open("w", encoding="utf-8") as f:
                json.dump(vfa, f, ensure_ascii=False, indent=2)
            result["visual_fatigue_audit"] = str(vfa_path)

        # Node 12 editorial QA (opt-in: only when editing_policy is set)
        if editing_policy:
            qa_path = write_editorial_qa(out_dir, editing_policy)
            if qa_path:
                result["editorial_qa"] = qa_path
    return result

