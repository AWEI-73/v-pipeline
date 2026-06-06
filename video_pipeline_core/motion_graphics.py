"""motion_graphics.py — Node 14 effects contract scaffold.

The core edit flow should not require a heavy motion graphics stack. This module
keeps title/lower-third/name-list effects as explicit artifacts that can be
rendered by a safe ffmpeg/libass backend first, then upgraded to Remotion,
HTML/Playwright, Blender, or external compositors when the route allows it.
"""
import json
from pathlib import Path


ALLOWED_BACKENDS = {
    "ffmpeg_libass",
    "html_playwright",
    "remotion",
    "mlt",
    "blender",
    "external_ae",
}

HEAVY_BACKENDS = {"blender", "external_ae"}

ALLOWED_EFFECT_TYPES = {
    "title_sequence",
    "name_list",
    "lower_third",
    "chapter_card",
    "info_card",
    "logo_intro",
}


def _finding(level, field, message):
    return {"level": level, "field": field, "message": message}


def validate_motion_graphics_contract(contract):
    errors = []
    warnings = []
    if not isinstance(contract, dict):
        return {"ok": False, "errors": [_finding("error", "$", "contract must be object")], "warnings": []}
    if contract.get("motion_graphics_version") != 1:
        errors.append(_finding("error", "motion_graphics_version", "must be 1"))
    items = contract.get("items")
    if not isinstance(items, list) or not items:
        errors.append(_finding("error", "items", "must be non-empty list"))
        return {"ok": False, "errors": errors, "warnings": warnings}
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(_finding("error", f"items[{i}]", "item must be object"))
            continue
        if not item.get("id"):
            errors.append(_finding("error", f"items[{i}].id", "required"))
        effect_type = item.get("effect_type")
        if effect_type not in ALLOWED_EFFECT_TYPES:
            errors.append(_finding("error", f"items[{i}].effect_type", "unknown effect type"))
        backend = item.get("backend")
        if backend and backend not in ALLOWED_BACKENDS:
            errors.append(_finding("error", f"items[{i}].backend", "unknown backend"))
        timing = item.get("timing") or {}
        if not isinstance(timing, dict):
            errors.append(_finding("error", f"items[{i}].timing", "must be object"))
            continue
        if not isinstance(timing.get("start_sec"), (int, float)):
            errors.append(_finding("error", f"items[{i}].timing.start_sec", "required number"))
        duration = timing.get("duration_sec")
        if not isinstance(duration, (int, float)) or duration <= 0:
            errors.append(_finding("error", f"items[{i}].timing.duration_sec", "required positive number"))
        text = item.get("text") or {}
        if not isinstance(text, dict) or not any(text.get(k) for k in ("main", "subtitle", "names")):
            warnings.append(_finding("warn", f"items[{i}].text", "no visible text payload"))
        if not item.get("reason"):
            warnings.append(_finding("warn", f"items[{i}].reason", "missing effect reason"))
    return {"ok": not errors, "errors": errors, "warnings": warnings}


def _backend_for(item, policy):
    backend = item.get("backend") or policy.get("default_backend") or "ffmpeg_libass"
    if backend not in ALLOWED_BACKENDS:
        raise ValueError(f"unknown motion graphics backend: {backend}")
    if backend in HEAVY_BACKENDS and not policy.get("allow_heavy_backend"):
        raise ValueError(f"heavy backend requires allow_heavy_backend=true: {backend}")
    return backend


def build_motion_graphics_render_plan(contract, backend_policy=None):
    v = validate_motion_graphics_contract(contract)
    if not v["ok"]:
        raise ValueError(f"invalid motion graphics contract: {v['errors']}")
    policy = {
        "default_backend": "ffmpeg_libass",
        "fallback_backend": "ffmpeg_libass",
        "allow_heavy_backend": False,
        **(backend_policy or {}),
    }
    items = []
    for item in contract["items"]:
        timing = item["timing"]
        style = item.get("style") or {}
        backend = _backend_for(item, policy)
        output_mode = item.get("output_mode") or "overlay"
        items.append({
            "id": item["id"],
            "segment": item.get("segment"),
            "effect_type": item["effect_type"],
            "backend": backend,
            "fallback_backend": policy["fallback_backend"],
            "template": item.get("template"),
            "start_sec": float(timing["start_sec"]),
            "duration_sec": float(timing["duration_sec"]),
            "end_sec": float(timing["start_sec"]) + float(timing["duration_sec"]),
            "output_mode": output_mode,
            "text": item.get("text") or {},
            "style": {
                "motion": style.get("motion", "fade"),
                "safe_area": style.get("safe_area", "title_safe"),
                "font_role": style.get("font_role", "bold_cjk"),
                "color_role": style.get("color_role", "utility_clean"),
            },
            "reason": item.get("reason"),
        })
    return {
        "artifact_role": "motion_graphics_render_plan",
        "motion_graphics_render_plan_version": 1,
        "contract_hash": contract.get("contract_hash"),
        "backend_policy": policy,
        "items": items,
    }


def _write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return str(path)


def write_motion_graphics_artifacts(contract, out_dir, backend_policy=None):
    out_dir = Path(out_dir)
    v = validate_motion_graphics_contract(contract)
    if not v["ok"]:
        return {"ok": False, "errors": v["errors"], "warnings": v["warnings"]}
    plan = build_motion_graphics_render_plan(contract, backend_policy=backend_policy)
    contract_path = _write_json(out_dir / "motion_graphics_contract.json", contract)
    plan_path = _write_json(out_dir / "motion_graphics_render_plan.json", plan)
    manifest = {
        "artifact_role": "motion_graphics_manifest",
        "motion_graphics_manifest_version": 1,
        "contract_hash": contract.get("contract_hash"),
        "motion_graphics_contract": contract_path,
        "motion_graphics_render_plan": plan_path,
        "render_outputs": [],
    }
    manifest_path = _write_json(out_dir / "motion_graphics_manifest.json", manifest)
    return {
        "ok": True,
        "errors": [],
        "warnings": v["warnings"],
        "contract": contract_path,
        "render_plan": plan_path,
        "manifest": manifest_path,
    }
