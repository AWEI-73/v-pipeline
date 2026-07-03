"""edit_artifacts.py — Node 9/10 build-facing JSON artifacts.

This module separates editing intent (`assembly_plan`) from concrete source
timestamps (`timeline_build`). Runtime can use these artifacts without
reinterpreting the canonical SPEC.
"""
import json
import math
import os
from pathlib import Path

from .asset_paths import to_asset_ref


_STILL_TREATMENT_MODES = ("slow_push", "pan_right", "detail_push", "pan_left")


def _resolve_anti_presentation_plan(seg, duration_sec, editing_policy):
    """Plan deterministic prevention for common presentation-like treatments."""
    policy = editing_policy or {}
    material_fit = seg.get("material_fit") or {}
    media = seg.get("media_pref") or seg.get("media") or material_fit.get("media")
    is_photo = media in {"photo", "image", "still"}
    narrative = seg.get("narrative")
    raw_text = seg.get("raw_text_layer") or {}
    if not isinstance(raw_text, dict):
        raw_text = {}
    placement = raw_text.get("placement")

    plan = {}
    if is_photo:
        mode = policy.get("default_mode") or "warm_documentary"
        max_still = (
            policy.get("max_still_hold_sec_by_mode", {}).get(mode)
            or policy.get("max_still_hold_sec")
            or 5.0
        )
        duration = float(duration_sec or 0.0)
        if duration > float(max_still):
            plan["min_shots"] = max(2, min(3, math.ceil(duration / float(max_still))))
        offset = int(seg.get("segment") or 0) % len(_STILL_TREATMENT_MODES)
        plan["still_treatment_modes"] = [
            _STILL_TREATMENT_MODES[(offset + index) % len(_STILL_TREATMENT_MODES)]
            for index in range(3)
        ]
    if narrative and placement in {None, "center", "centered", "middle"}:
        plan["text_placement"] = "lower_third"
    return plan


def _resolve_seg_treatment(seg, music_structure, editing_policy, duration_sec=None):
    """Opt-in material treatment for a script segment.

    Only segments that declare editing_intent.content_pattern or an explicit
    material_treatment get a treatment block; everything else is left untouched so
    existing runs are unaffected. ``duration_sec`` is the allocated timeline budget
    (used for the pacing-consistency check when the segment doesn't carry its own
    duration). Returns a dict to merge into the plan segment, or {} when the
    segment opts out.
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
        "duration_sec": seg.get("duration_sec") or duration_sec,
    }
    resolved = material_treatment.resolve_treatment(seg_view, beat_count, editing_policy)
    items = mt.get("items") or []
    out = {
        "treatment": resolved["treatment"],
        "n_required": resolved["n_required"],
        "items": items,
        "label_per_item": bool(mt.get("label_per_item")),
        "lane_plan": resolved["lane_plan"],
        "treatment_reason": resolved["reason"],
    }
    if resolved.get("pacing_conflict"):
        out["pacing_conflict"] = True
    return out


def build_assembly_plan(script, *, music_structure=None, contract_hash=None, editing_policy=None,
                        timeline_duration_sec=None):
    """Build Node 9 assembly_plan from generated MV payload."""
    contract_hash = contract_hash or script.get("_contract_hash")
    music_sections = (music_structure or {}).get("sections") or []
    default_music_anchor = music_sections[0].get("name") if music_sections else None
    
    beats = (music_structure or {}).get("beats") or []
    if timeline_duration_sec is not None:
        beats = [beat for beat in beats if float(beat) <= float(timeline_duration_sec)]
    total_dur = float(timeline_duration_sec) if timeline_duration_sec is not None else (
        beats[-1] if beats else 0.0
    )
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

        # Resolve segment-level raw facets
        raw_audio = seg.get("raw_audio") or {}
        raw_vis = seg.get("raw_visual_style") or {}
        raw_txt = seg.get("raw_text_layer") or {}
        if not isinstance(raw_txt, dict):
            raw_txt = {}
        
        # Narration
        narr_mode = raw_audio.get("mode")
        if not narr_mode:
            voiceover_policy = raw_audio.get("voiceover_policy")
            if voiceover_policy and voiceover_policy not in ("none", "no_speech"):
                narr_mode = "voiceover"
            elif raw_audio.get("role") == "duck":
                narr_mode = "original_speech"
            else:
                narr_mode = "none"
        narr_src = raw_audio.get("source") or ("tts" if narr_mode == "voiceover" else "none")
        narr_duck = bool(raw_audio.get("duck_music") or raw_audio.get("role") in ("duck", "diegetic"))
        if editing_policy:
            policy_ns = editing_policy.get("narration_strategy") or {}
            if narr_mode == "none" and policy_ns.get("mode"):
                narr_mode = policy_ns.get("mode")
            if narr_duck is None or raw_audio.get("duck_music") is None:
                narr_duck = bool(policy_ns.get("duck_under_speech", True))

        # Subtitles
        sub_mode = raw_txt.get("mode") or ("full_subtitle" if seg.get("subtitle") else "none")
        sub_placement = raw_txt.get("placement") or "bottom_safe"
        sub_avoid = raw_txt.get("avoid") or []
        if editing_policy:
            policy_ss = editing_policy.get("subtitle_strategy") or {}
            if sub_placement == "bottom_safe" and policy_ss.get("placement"):
                sub_placement = policy_ss.get("placement")
            if not sub_avoid and policy_ss.get("avoid"):
                sub_avoid = policy_ss.get("avoid")

        # Music
        mus_section = seg.get("music_anchor") or default_music_anchor or "none"
        mus_mood = raw_audio.get("mood") or "none"
        mus_intensity = raw_audio.get("intensity") or "medium"
        if editing_policy:
            policy_ms = editing_policy.get("music_strategy") or {}
            if mus_mood == "none" and policy_ms.get("mode"):
                mus_mood = policy_ms.get("mode")

        # Effects
        fx_intensity = raw_vis.get("effects_intensity") or "none"
        fx_allowed = raw_vis.get("allowed_effects_roles") or []
        if editing_policy:
            policy_es = editing_policy.get("effects_strategy") or {}
            if fx_intensity == "none" and policy_es.get("intensity"):
                fx_intensity = policy_es.get("intensity")
            if not fx_allowed and policy_es.get("allowed_roles"):
                fx_allowed = policy_es.get("allowed_roles")

        entry = {
            "segment": seg.get("segment"),
            "contract_segment": seg.get("_from_contract"),
            "creative_exception": seg.get("creative_exception"),
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
            "execution_plan": {
                "narration": {
                    "mode": narr_mode,
                    "source": narr_src,
                    "duck_music": narr_duck,
                },
                "subtitles": {
                    "mode": sub_mode,
                    "placement": sub_placement,
                    "avoid": sub_avoid,
                },
                "music": {
                    "section": mus_section,
                    "mood": mus_mood,
                    "intensity": mus_intensity,
                },
                "effects": {
                    "intensity": fx_intensity,
                    "allowed_roles": fx_allowed,
                }
            }
        }
        treatment_info = _resolve_seg_treatment(
            seg, music_structure, editing_policy,
            duration_sec=round(end_t - start_t, 3) if end_t > start_t else None)
        entry.update(treatment_info)
        anti_presentation_plan = _resolve_anti_presentation_plan(
            seg,
            round(end_t - start_t, 3) if end_t > start_t else None,
            editing_policy,
        )
        if anti_presentation_plan:
            entry["anti_presentation_plan"] = anti_presentation_plan
        from .attention_budget import resolve_attention_budget
        entry["attention_budget"] = resolve_attention_budget(
            entry,
            mode=(editing_policy or {}).get("default_mode", script.get("style") or "warm_documentary"),
        )
        
        if seg.get("sequence_grammar"):
            try:
                from . import shot_slots  # noqa: PLC0415
                import math  # noqa: PLC0415
                n_req = treatment_info.get("n_required")
                # Density-aware (lexicon §3): a fast/montage segment must fill its time
                # budget at the target pace, not cap at the function-list length. Without
                # this a fast 70s chapter renders ~6 shots (~12s each) instead of a real
                # montage. Only fires for fast/montage segments that declare pacing.
                pacing = seg.get("pacing") or {}
                pref = pacing.get("preferred_shot_sec")
                is_fast = seg.get("pace") == "fast" or seg.get("layout") == "montage"
                if is_fast and pref:
                    upper = pref[1] if isinstance(pref, (list, tuple)) and len(pref) >= 2 else float(pref)
                    budget = end_t - start_t
                    if upper and budget > 0:
                        n_density = max(1, math.ceil(budget / float(upper)))
                        n_req = max(int(n_req or 1), n_density)
                entry["shot_slots"] = shot_slots.expand_shot_slots(seg, n_required=n_req)
            except Exception:
                pass
        
        # Resolve segment-level transition_plan between slots
        slots = entry.get("shot_slots") or []
        seg_trans_plan = []
        trans_type = seg.get("transition_philosophy") or raw_vis.get("transition_type") or "direct_cut"
        for s_idx in range(len(slots) - 1):
            from_slot = slots[s_idx]["slot"]
            to_slot = slots[s_idx + 1]["slot"]
            seg_trans_plan.append({
                "from_slot": from_slot,
                "to_slot": to_slot,
                "type": trans_type,
                "reason": f"slot sequence transition: {from_slot} -> {to_slot}"
            })
        entry["transition_plan"] = seg_trans_plan
        segments.append(entry)

    # Compile root-level execution_plan lists
    narration_tasks = []
    subtitle_tasks = []
    effects_tasks = []
    
    # Compile music_sections mapping
    sections_map = {}
    for entry in segments:
        seg_num = entry["segment"]
        mus_sec = entry["execution_plan"]["music"]["section"]
        if mus_sec and mus_sec != "none":
            if mus_sec not in sections_map:
                sections_map[mus_sec] = []
            sections_map[mus_sec].append(seg_num)
    
    music_sections_list = []
    for ms in music_sections:
        name = ms.get("name")
        music_sections_list.append({
            "section": name,
            "segments": sections_map.get(name, [])
        })
    for name, seg_nums in sections_map.items():
        if not any(ms["section"] == name for ms in music_sections_list):
            music_sections_list.append({
                "section": name,
                "segments": seg_nums
            })

    for entry, seg in zip(segments, segs):
        seg_num = entry["segment"]
        exec_plan = entry["execution_plan"]
        
        # Narration task
        narr_text = seg.get("narrative") or seg.get("subtitle") or ""
        if narr_text and exec_plan["narration"]["mode"] != "none":
            narration_tasks.append({
                "segment": seg_num,
                "text": narr_text,
                "mode": exec_plan["narration"]["mode"],
                "source": exec_plan["narration"]["source"]
            })
            
        # Subtitle task
        sub_text = seg.get("subtitle")
        if sub_text and exec_plan["subtitles"]["mode"] != "none":
            subtitle_tasks.append({
                "segment": seg_num,
                "text": sub_text,
                "placement": exec_plan["subtitles"]["placement"]
            })
            
        # Effects task
        if exec_plan["effects"]["intensity"] != "none" or exec_plan["effects"]["allowed_roles"]:
            effects_tasks.append({
                "segment": seg_num,
                "intensity": exec_plan["effects"]["intensity"],
                "allowed_roles": exec_plan["effects"]["allowed_roles"]
            })

    # Root-level transition_plan
    root_trans_plan = []
    for s_idx in range(len(segments) - 1):
        from_seg = segments[s_idx]["segment"]
        to_seg = segments[s_idx + 1]["segment"]
        trans_type = script.get("transition_philosophy") or "direct_cut"
        root_trans_plan.append({
            "from_segment": from_seg,
            "to_segment": to_seg,
            "type": trans_type,
            "reason": f"segment boundary transition: {from_seg} -> {to_seg}"
        })

    return {
        "assembly_plan_version": 1,
        "contract_hash": contract_hash,
        "music_section": {
            "source": "music_structure.json" if music_structure else None,
            "sections": [s.get("name") for s in music_sections],
        },
        "execution_plan": {
            "narration_tasks": narration_tasks,
            "subtitle_tasks": subtitle_tasks,
            "music_sections": music_sections_list,
            "effects_tasks": effects_tasks,
            "transition_plan": root_trans_plan
        },
        "segments": segments,
    }


def _audio_policy(item):
    if item.get("audio_policy"):
        return item["audio_policy"]
    if item.get("keep_audio"):
        return "duck"
    return "music"


def local_motion_peaks(energy_samples, min_energy=5.0, min_gap_sec=0.5):
    """Return stable local maxima from ``[(timestamp_sec, frame_diff_energy)]``."""
    samples = [(float(ts), float(energy)) for ts, energy in (energy_samples or [])]
    candidates = []
    for index in range(1, len(samples) - 1):
        timestamp, energy = samples[index]
        if energy < float(min_energy):
            continue
        if energy > samples[index - 1][1] and energy >= samples[index + 1][1]:
            candidates.append((timestamp, energy))
    selected = []
    for timestamp, energy in sorted(candidates, key=lambda item: (-item[1], item[0])):
        if all(abs(timestamp - kept[0]) >= float(min_gap_sec) for kept in selected):
            selected.append((timestamp, energy))
    return [timestamp for timestamp, _energy in sorted(selected)]


def detect_motion_peaks(source, sample_fps=4.0, min_energy=5.0, min_gap_sec=0.5):
    """Detect local frame-difference energy peaks. Decode failures return no peaks."""
    if not source or not os.path.exists(source):
        return []
    try:
        import cv2  # noqa: PLC0415
        capture = cv2.VideoCapture(str(source))
        source_fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
        if not capture.isOpened() or source_fps <= 0:
            capture.release()
            return []
        step = max(1, round(source_fps / float(sample_fps)))
        samples = []
        previous = None
        frame_index = 0
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            if frame_index % step == 0:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                if previous is not None:
                    energy = float(cv2.absdiff(gray, previous).mean())
                    samples.append((frame_index / source_fps, energy))
                previous = gray
            frame_index += 1
        capture.release()
        return local_motion_peaks(samples, min_energy=min_energy, min_gap_sec=min_gap_sec)
    except Exception:
        return []


def _video_duration(source):
    if not source or not os.path.exists(source):
        return None
    try:
        import cv2  # noqa: PLC0415
        capture = cv2.VideoCapture(str(source))
        fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
        frames = float(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0)
        capture.release()
        return frames / fps if fps > 0 and frames > 0 else None
    except Exception:
        return None


def _timeline_for_persist(timeline, run_dir):
    persisted = json.loads(json.dumps(timeline, ensure_ascii=False))
    for clip in persisted.get("clips") or []:
        source_path = clip.get("source_path")
        if source_path:
            clip["source_path"] = to_asset_ref(run_dir, source_path).ref
    return persisted


def snap_to_edit_point(start, duration, scene_cuts=None, motion_peaks=None, tolerance=0.5):
    """Snap a source window to a scene boundary first, then to a motion peak."""
    for reason, points in (
        ("snapped_to_scene_cut", scene_cuts),
        ("snapped_to_motion_peak", motion_peaks),
    ):
        for point in sorted(float(value) for value in (points or [])):
            if start + tolerance < point < start + duration - tolerance:
                return point, point + duration, True, reason
    return start, start + duration, False, None


def _snap_to_scene_cut(start, duration, cuts, tolerance):
    return snap_to_edit_point(start, duration, scene_cuts=cuts, tolerance=tolerance)


def snap_render_plan_to_motion(render_plan, *, motion_peak_detector=None,
                               source_duration_probe=None, tolerance=0.5):
    """Return a copy of a concrete render plan snapped to source motion peaks."""
    detector = motion_peak_detector or detect_motion_peaks
    duration_probe = source_duration_probe or _video_duration
    peaks_by_source = {}
    durations_by_source = {}
    snapped_plan = []
    original_ranges = [
        (
            item.get("source") or item.get("source_path"),
            float(item.get("extract_start") or item.get("start_sec") or 0.0),
            float(item.get("extract_start") or item.get("start_sec") or 0.0)
            + float(item.get("extract_dur") or item.get("duration_sec") or 0.0),
        )
        for item in (render_plan or [])
    ]
    for index, item in enumerate(render_plan or []):
        snapped = dict(item)
        source = snapped.get("source") or snapped.get("source_path")
        start = float(snapped.get("extract_start") or snapped.get("start_sec") or 0.0)
        duration = float(snapped.get("extract_dur") or snapped.get("duration_sec") or 0.0)
        if index == 0 or snapped.get("keep_audio") or snapped.get("adjustment_reason"):
            snapped_plan.append(snapped)
            continue
        if source not in peaks_by_source:
            try:
                peaks_by_source[source] = detector(source)
            except Exception:
                peaks_by_source[source] = []
        if source not in durations_by_source:
            try:
                durations_by_source[source] = duration_probe(source)
            except Exception:
                durations_by_source[source] = None
        source_duration = durations_by_source.get(source)
        usable_peaks = [
            peak for peak in peaks_by_source.get(source, [])
            if source_duration is None or float(peak) + duration <= float(source_duration)
        ]
        usable_peaks = [
            peak for peak in usable_peaks
            if not any(
                other_source == source
                and other_index != index
                and float(peak) < other_end
                and other_start < float(peak) + duration
                for other_index, (other_source, other_start, other_end)
                in enumerate(original_ranges)
            )
        ]
        new_start, _end, adjusted, reason = snap_to_edit_point(
            start,
            duration,
            motion_peaks=usable_peaks,
            tolerance=tolerance,
        )
        if adjusted:
            snapped["original_extract_start"] = start
            snapped["extract_start"] = round(new_start, 3)
            snapped["adjustment_reason"] = reason
        snapped_plan.append(snapped)
    return snapped_plan


def build_timeline_build(render_plan, *, contract_hash=None, fps=30, resolution="1920x1080",
                         scene_cuts_by_source=None, motion_peaks_by_source=None,
                         scene_cut_tolerance_sec=0.5):
    """Build Node 10 timeline_build from concrete render plan clips."""
    clips = []
    cursor = 0.0
    for item in render_plan or []:
        dur = float(item.get("extract_dur") or item.get("duration_sec") or 0)
        source = item.get("source") or item.get("source_path")
        start = float(item.get("extract_start") or item.get("start_sec") or 0)
        original_start = float(item.get("original_extract_start", start))
        adjustment_reason = item.get("adjustment_reason")
        adjusted = bool(adjustment_reason or original_start != start)
        end = start + dur
        if not adjusted:
            start, end, adjusted, adjustment_reason = snap_to_edit_point(
                original_start,
                dur,
                scene_cuts=(scene_cuts_by_source or {}).get(source),
                motion_peaks=(motion_peaks_by_source or {}).get(source),
                tolerance=scene_cut_tolerance_sec,
            )
        transition = item.get("transition") or "cut"
        transition_duration = float(item.get("transition_duration") or 0.0)
        if item.get("timeline_in") is not None:
            timeline_in = float(item["timeline_in"])
        elif transition in {"dissolve", "crossfade", "xfade"}:
            timeline_in = max(0.0, cursor - min(transition_duration, dur))
        else:
            timeline_in = cursor
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
            "scene_id": item.get("scene_id"),
            "asset_id": item.get("asset_id"),
            "material_map_id": item.get("material_map_id") or item.get("asset_id"),
            "need_id": item.get("need_id") or item.get("need_ref"),
            "caption": item.get("caption"),
            "function": item.get("function") or item.get("shot_function"),
            "beat_alignment": item.get("beat_alignment"),
            "keep_audio": bool(item.get("keep_audio")),
            "motion_phase": item.get("motion_phase"),
            "review_required": item.get("review_required"),
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
            "transition": transition,
            "transition_duration_sec": round(transition_duration, 3) if transition_duration else None,
            "attention_budget": item.get("attention_budget"),
            "creative_exception": item.get("creative_exception"),
            "hold_reason": item.get("hold_reason"),
            "text_overlay": item.get("text") or "none",
            "composition_layers": item.get("composition_layers"),
            "text_area_ratio": item.get("text_area_ratio"),
            "effect_overlays": item.get("effect_overlays"),
            "photo_variant": item.get("photo_variant"),
            "still_treatment": item.get("still_treatment"),
            "source_repeat_count": item.get("source_repeat_count"),
            "trace": {
                "segment_contract_segment": segment,
                "assembly_plan_segment": segment,
            },
            "shot_reason": item.get("shot_reason") or item.get("reason"),
            "reason": item.get("reason"),
            "cut_reason": item.get("cut_reason"),
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
    timeline_duration_sec = None
    if render_plan is not None:
        timeline_duration_sec = sum(
            float(item.get("extract_dur") or item.get("duration_sec") or 0.0)
            for item in render_plan
        )
    assembly = build_assembly_plan(
        script,
        music_structure=music_structure,
        editing_policy=editing_policy,
        timeline_duration_sec=timeline_duration_sec,
    )
    assembly_path = out_dir / "assembly_plan.json"
    with assembly_path.open("w", encoding="utf-8") as f:
        json.dump(assembly, f, ensure_ascii=False, indent=2)

    result = {"assembly_plan": str(assembly_path)}
    if render_plan is not None:
        timeline = build_timeline_build(render_plan, contract_hash=script.get("_contract_hash"))
        timeline_path = out_dir / "timeline_build.json"
        with timeline_path.open("w", encoding="utf-8") as f:
            json.dump(_timeline_for_persist(timeline, out_dir), f, ensure_ascii=False, indent=2)
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
