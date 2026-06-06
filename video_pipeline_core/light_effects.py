"""light_effects.py - ffmpeg-safe light effects plan runner.

This module turns canonical contract facets plus build_profile policy into
explicit operations. It does not call heavy motion graphics backends.
"""
import json
from pathlib import Path


SAFE_OPERATIONS = {"grade", "kenburns", "title_card", "lower_third", "xfade"}


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
    if material.get("media") == "photo" or visual.get("pace") == "hold":
        ops.append({
            "operation": "kenburns",
            "direction": visual.get("motion") or "zoom-in",
            "reason": visual.get("reason") or "photo/hold segment needs motion",
        })
    ops.extend(_text_ops(seg))
    if visual.get("layout") == "montage" or visual.get("pace") == "fast":
        ops.append({
            "operation": "xfade",
            "transition": visual.get("transition") or "fade",
            "reason": visual.get("reason") or "fast/montage segment needs light transition",
        })
    return ops


def build_light_effects_plan(contract, build_profile=None):
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


def write_light_effects_artifacts(contract, build_profile, out_dir):
    out_dir = Path(out_dir)
    plan = build_light_effects_plan(contract, build_profile)
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
