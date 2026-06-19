"""light_effects.py - ffmpeg-safe light effects plan runner.

This module turns canonical contract facets plus build_profile policy into
explicit operations. It does not call heavy motion graphics backends.
"""
import json
from pathlib import Path

from .effect_contract import validate_effect_intent_plan


SAFE_OPERATIONS = {"grade", "kenburns", "title_card", "lower_third", "xfade", "external_effect"}


def _profile_enabled(profile):
    return (
        (profile or {}).get("render_profile") == "light_effects"
        or bool((profile or {}).get("effects_enabled"))
    )


def _segment_id(seg, fallback):
    return seg.get("segment") or fallback


def _text_ops(seg):
    text = seg.get("text_layer")
    if not isinstance(text, dict):
        return []
    ops = []
    if text.get("label") or text.get("narrative"):
        ops.append({
            "operation": "title_card",
            "text": text.get("label") or text.get("narrative"),
            "subtitle": text.get("subtitle"),
            "reason": text.get("reason") or "text layer requested by contract",
        })
    name_super = text.get("name_super")
    if name_super:
        ops.append({
            "operation": "lower_third",
            "text": name_super.get("text") if isinstance(name_super, dict) else name_super,
            "reason": text.get("reason") or "name super requested by contract",
        })
    return ops


def _segment_operations(seg):
    visual = seg.get("visual_style") or {}
    material = seg.get("material_fit") or {}
    ops = []
    grade = visual.get("grade")
    if grade:
        ops.append({
            "operation": "grade",
            "preset": grade,
            "reason": visual.get("reason") or "visual grade requested by contract",
        })
    if material.get("media") == "photo":
        ops.append({
            "operation": "kenburns",
            "direction": visual.get("motion") or "zoom-in",
            "reason": visual.get("reason") or "photo segment needs motion",
        })
    ops.extend(_text_ops(seg))
    transition = visual.get("transition")
    if transition in {"dissolve", "crossfade", "xfade"}:
        ops.append({
            "operation": "xfade",
            "transition": transition,
            "reason": visual.get("reason") or "explicit light transition requested by contract",
        })
    return ops


def _segment_from_effect(effect):
    target = effect.get("target") or {}
    segment = target.get("segment_id") or target.get("segment") or target.get("segment_ref")
    if isinstance(segment, str) and segment.strip().isdigit():
        return int(segment.strip())
    return segment


def _effect_operation(effect):
    role = effect.get("role")
    intent = effect.get("intent") or role
    visual_language = effect.get("visual_language") or []
    base = {
        "source_effect_id": effect.get("effect_id"),
        "effect_role": role,
        "required_for_story": bool(effect.get("required_for_story")),
        "must_preserve_proof": bool(effect.get("must_preserve_proof")),
        "visual_language": visual_language,
        "reason": intent,
    }
    if "ffmpeg_light_effects" not in (effect.get("allowed_backends") or []):
        return {
            **base,
            "operation": "external_effect",
            "status": "pending_backend",
            "next_action": "route_to_node14_or_remotion_adapter",
        }
    if role == "title_card":
        return {
            **base,
            "operation": "title_card",
            "text": intent,
            "subtitle": ", ".join(visual_language) if visual_language else None,
        }
    if role == "lower_third":
        return {
            **base,
            "operation": "lower_third",
            "text": intent,
        }
    if role == "color_grade":
        return {
            **base,
            "operation": "grade",
            "preset": "warm" if effect.get("intensity") in {"medium", "high"} else "neutral",
        }
    if role in {"chapter_transition", "transition_plate"}:
        return {
            **base,
            "operation": "xfade",
            "transition": "xfade",
        }
    return {
        **base,
        "operation": "external_effect",
        "status": "pending_backend",
        "next_action": "route_to_node14_or_remotion_adapter",
    }


def _effect_intent_operations(effect_intent_plan):
    if not effect_intent_plan:
        return []
    validate_effect_intent_plan(effect_intent_plan)
    ops = []
    for effect in effect_intent_plan.get("effects") or []:
        op = _effect_operation(effect)
        op["segment"] = _segment_from_effect(effect)
        ops.append(op)
    return ops


def build_light_effects_plan(contract, build_profile=None, *, effect_intent_plan=None):
    if not _profile_enabled(build_profile):
        return {
            "artifact_role": "light_effects_plan",
            "light_effects_plan_version": 1,
            "status": "skipped",
            "backend": "ffmpeg",
            "items": [],
        }
    items = []
    for idx, seg in enumerate((contract or {}).get("segments", []), start=1):
        if not isinstance(seg, dict):
            continue
        segment = _segment_id(seg, idx)
        for op_idx, operation in enumerate(_segment_operations(seg), start=1):
            op = dict(operation)
            if op["operation"] not in SAFE_OPERATIONS:
                raise ValueError(f"unsafe light effect operation: {op['operation']}")
            op.update({
                "id": f"seg{segment}_{op['operation']}_{op_idx}",
                "segment": segment,
                "backend": "ffmpeg",
                "status": "planned",
            })
            items.append(op)
    for op_idx, operation in enumerate(_effect_intent_operations(effect_intent_plan), start=1):
        op = dict(operation)
        if op["operation"] not in SAFE_OPERATIONS:
            raise ValueError(f"unsafe light effect operation: {op['operation']}")
        segment = op.get("segment") or "global"
        op.setdefault("backend", "ffmpeg")
        op.setdefault("status", "planned")
        op["id"] = f"fxintent_{segment}_{op['operation']}_{op_idx}"
        items.append(op)
    return {
        "artifact_role": "light_effects_plan",
        "light_effects_plan_version": 1,
        "status": "planned" if items else "skipped",
        "backend": "ffmpeg",
        "items": items,
    }


def _write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return str(path)


def write_light_effects_artifacts(contract, build_profile, out_dir, *, effect_intent_plan=None):
    out_dir = Path(out_dir)
    plan = build_light_effects_plan(contract, build_profile, effect_intent_plan=effect_intent_plan)
    plan_path = _write_json(out_dir / "light_effects_plan.json", plan)
    manifest = {
        "artifact_role": "light_effects_manifest",
        "light_effects_manifest_version": 1,
        "light_effects_plan": plan_path,
        "backend": "ffmpeg",
        "render_outputs": [],
    }
    manifest_path = _write_json(out_dir / "light_effects_manifest.json", manifest)
    return {
        "ok": True,
        "plan": plan_path,
        "manifest": manifest_path,
        "status": plan["status"],
    }


def record_motion_graphics_outputs(plan, manifest, motion_outputs):
    """Record ffmpeg/libass text recipe outputs against matching light-effect items."""
    effect_to_operation = {
        "title_sequence": "title_card",
        "chapter_card": "title_card",
        "info_card": "title_card",
        "lower_third": "lower_third",
    }
    recorded = (manifest or {}).setdefault("render_outputs", [])
    recorded_ids = {item.get("effect_id") for item in recorded}
    planned = (plan or {}).get("items") or []
    for output in motion_outputs or []:
        operation = effect_to_operation.get(output.get("effect_type"))
        if not operation or output.get("status") != "composited":
            continue
        match = next((
            item for item in planned
            if item.get("segment") == output.get("segment")
            and item.get("operation") == operation
            and item.get("id") not in recorded_ids
        ), None)
        if not match:
            continue
        recorded.append({
            "effect_id": match.get("id"),
            "segment": match.get("segment"),
            "operation": operation,
            "status": "composited",
            "path": output.get("path"),
            "renderer": "motion_graphics.ffmpeg_libass",
            "source_effect_id": output.get("effect_id"),
        })
        recorded_ids.add(match.get("id"))
    return manifest


def record_mv_render_outputs(plan, manifest, mv_plan, *, final_video=None):
    """Record effects that the MV renderer actually applied while building clips."""
    recorded = (manifest or {}).setdefault("render_outputs", [])
    recorded_ids = {item.get("effect_id") for item in recorded}
    planned = (plan or {}).get("items") or []
    for slot in mv_plan or []:
        operations = []
        if slot.get("is_photo") and slot.get("kenburns", True):
            operations.append(("kenburns", "mv_cut.photo_zoompan"))
        if slot.get("transition") in {"dissolve", "crossfade", "xfade"}:
            operations.append(("xfade", "mv_cut.ffmpeg_xfade"))
        for operation, renderer in operations:
            match = next((
                item for item in planned
                if item.get("segment") == slot.get("segment")
                and item.get("operation") == operation
                and item.get("id") not in recorded_ids
            ), None)
            if not match:
                continue
            output = {
                "effect_id": match.get("id"),
                "segment": match.get("segment"),
                "operation": operation,
                "status": "rendered",
                "path": str(final_video) if final_video else None,
                "renderer": renderer,
                "source_slot_index": slot.get("slot_index"),
            }
            if operation == "xfade":
                output["transition_duration"] = float(slot.get("transition_duration") or 0.5)
            recorded.append(output)
            recorded_ids.add(match.get("id"))
    return manifest


def build_light_effects_baseline_review(plan, manifest, *, final_video=None, audit_paths=None):
    """Measure whether planned light effects reached render and review evidence."""
    items = (plan or {}).get("items") or []
    outputs = (manifest or {}).get("render_outputs") or []
    rendered_ids = {
        output.get("effect_id")
        for output in outputs
        if output.get("status") in {"rendered", "composited"} and output.get("effect_id")
    }
    gaps = [
        {
            "effect_id": item.get("id"),
            "segment": item.get("segment"),
            "operation": item.get("operation"),
            "reason": "no_render_output",
            "next_action": "implement_or_wire_effect_recipe",
        }
        for item in items
        if item.get("id") not in rendered_ids
    ]
    audits = audit_paths or {}
    evidence = {
        "final_video": str(final_video) if final_video else None,
        "final_video_present": bool(final_video),
        "keyframe_grid": str(audits.get("keyframe_grid")) if audits.get("keyframe_grid") else None,
        "keyframe_review_ready": bool(audits.get("keyframe_grid")),
        "visual_audit": str(audits.get("visual_audit")) if audits.get("visual_audit") else None,
        "visual_audit_ready": bool(audits.get("visual_audit")),
        "p1_audits": {
            role: str(path)
            for role, path in audits.items()
            if path
        },
    }
    planned_count = len(items)
    rendered_count = len(items) - len(gaps)
    coverage_ratio = round(rendered_count / planned_count, 3) if planned_count else 1.0
    evidence_ready = (
        evidence["final_video_present"]
        and evidence["keyframe_review_ready"]
        and evidence["visual_audit_ready"]
    )
    if gaps:
        status = "gaps_found"
    elif planned_count and not evidence_ready:
        status = "visual_review_required"
    else:
        status = "pass"
    return {
        "artifact_role": "light_effects_baseline_review",
        "light_effects_baseline_review_version": 1,
        "status": status,
        "metrics": {
            "planned_count": planned_count,
            "rendered_count": rendered_count,
            "gap_count": len(gaps),
            "coverage_ratio": coverage_ratio,
        },
        "gaps": gaps,
        "evidence": evidence,
        "next_action": gaps[0]["next_action"] if gaps else (
            "complete_keyframe_and_visual_review" if not evidence_ready and planned_count else None
        ),
    }


def write_light_effects_baseline_review(plan, manifest, out_path, *, final_video=None, audit_paths=None):
    review = build_light_effects_baseline_review(
        plan,
        manifest,
        final_video=final_video,
        audit_paths=audit_paths,
    )
    return _write_json(out_path, review)
