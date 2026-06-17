#!/usr/bin/env python
"""Hermes-native ``timeline_patch`` contract.

The native workbench never overwrites canonical artifacts. Every interactive
edit (duration / source window / clip order / material replacement) is captured
as a ``timeline_patch`` op-list. This module validates a patch against the base
timeline and applies it into a *new* ``patched_draft_timeline.json`` -- it never
writes ``timeline.json``.

Official rendering still goes through Hermes / ffmpeg BUILD using the canonical
artifacts; a patch is an editorial proposal, not a render.

CLI::

    python tools/timeline_patch.py validate --artifact-root <root> --patch timeline_patch.json
    python tools/timeline_patch.py apply --artifact-root <root> --patch timeline_patch.json --out patched_draft_timeline.json
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ARTIFACT_ROLE = "timeline_patch"
SCHEMA_VERSION = 1

VALID_OPS = {"set_duration", "set_source_window", "move_clip", "replace_clip"}

# Canonical artifacts that a patch must never overwrite.
PROTECTED_OUTPUTS = {
    "timeline.json",
    "segment_contract.json",
    "revised_segment_contract.json",
    "project_material_map.json",
    "material_needs.json",
    "final.mp4",
    "review_report.json",
    "delivery_gate.json",
}

TIMELINE_CANDIDATES = ("draft_timeline.json", "timeline.json")


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #
def _load_json(path: Path) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _resolve_base_timeline(root: Path) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    for name in TIMELINE_CANDIDATES:
        p = root / name
        if p.is_file():
            data = _load_json(p)
            if isinstance(data, dict):
                return data, name
    return None, None


def _plan_of(timeline: Dict[str, Any]) -> List[Dict[str, Any]]:
    return timeline.get("plan") or timeline.get("clips") or []


def _index_by_slot(plan: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
    out: Dict[int, Dict[str, Any]] = {}
    for i, clip in enumerate(plan):
        out[clip.get("slot_index", i)] = clip
    return out


def _source_window_for(clip: Dict[str, Any], material_map: Optional[Dict[str, Any]]) -> Optional[float]:
    """Return the maximum usable source-seconds for a clip's source asset."""
    if not isinstance(material_map, dict):
        return None
    src = clip.get("source")
    if not src:
        return None
    key = os.path.normcase(os.path.normpath(str(src)))
    for asset in material_map.get("assets", []) or []:
        a_src = asset.get("source")
        if not a_src:
            continue
        if os.path.normcase(os.path.normpath(str(a_src))) == key:
            dur = asset.get("duration_sec")
            return float(dur) if dur is not None else None
    return None


def _finite_number(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return None
    if not isinstance(value, (int, float)):
        return None
    f = float(value)
    return f if math.isfinite(f) else None


def _asset_by_id(material_map: Optional[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    if not isinstance(material_map, dict):
        return {}
    out: Dict[str, Dict[str, Any]] = {}
    for asset in material_map.get("assets", []) or []:
        if isinstance(asset, dict) and isinstance(asset.get("asset_id"), str):
            out[asset["asset_id"]] = asset
    return out


def _replacement_asset_scene(
    material_map: Optional[Dict[str, Any]],
    after: Dict[str, Any],
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], Optional[int], List[str]]:
    """Resolve a replace_clip target from the canonical project material map."""
    errors: List[str] = []
    if not isinstance(after, dict):
        return None, None, None, ["replace_clip after must be an object"]
    asset_id = after.get("asset_id")
    if not isinstance(asset_id, str) or not asset_id.strip():
        return None, None, None, ["replace_clip asset_id must be a non-empty string"]
    scene_index = after.get("scene_index", 0)
    if isinstance(scene_index, bool) or not isinstance(scene_index, int) or scene_index < 0:
        return None, None, None, ["replace_clip scene_index must be a non-negative integer"]

    assets = _asset_by_id(material_map)
    asset = assets.get(asset_id)
    if asset is None:
        return None, None, None, [f"replace_clip asset_id {asset_id!r} not found in project_material_map"]
    source = asset.get("source")
    if not isinstance(source, str) or not source.strip():
        errors.append(f"replace_clip asset_id {asset_id!r} has no renderable source")
    scenes = asset.get("scenes")
    if not isinstance(scenes, list) or scene_index >= len(scenes):
        errors.append(f"replace_clip scene_index {scene_index!r} not found for asset_id {asset_id!r}")
        return asset, None, scene_index, errors
    scene = scenes[scene_index]
    if not isinstance(scene, dict):
        errors.append(f"replace_clip scene_index {scene_index!r} must refer to an object scene")
        return asset, None, scene_index, errors

    asset_type = str(asset.get("asset_type") or "").lower()
    if asset_type == "video":
        start = _finite_number(scene.get("start"))
        end = _finite_number(scene.get("end"))
        if start is None or end is None or end <= start:
            errors.append(f"replace_clip video scene {asset_id}:{scene_index} must have finite end > start")
    return asset, scene, scene_index, errors


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #
def validate_patch(
    artifact_root: str,
    patch: Dict[str, Any],
) -> Tuple[bool, List[str]]:
    """Validate a patch against the base timeline. Returns ``(ok, errors)``."""
    errors: List[str] = []
    root = Path(artifact_root)

    if not isinstance(patch, dict):
        return False, ["patch must be a JSON object"]
    if patch.get("artifact_role") != ARTIFACT_ROLE:
        errors.append(f"artifact_role must be '{ARTIFACT_ROLE}'")
    ops = patch.get("patches")
    if not isinstance(ops, list):
        return False, errors + ["'patches' must be a list"]

    timeline, _ = _resolve_base_timeline(root)
    if timeline is None:
        return False, errors + ["no base timeline (draft_timeline.json / timeline.json) found"]
    plan = _plan_of(timeline)
    by_slot = _index_by_slot(plan)
    material_map = _load_json(root / "project_material_map.json")
    n = len(plan)

    for i, op in enumerate(ops):
        prefix = f"patches[{i}]"
        if not isinstance(op, dict):
            errors.append(f"{prefix}: must be an object")
            continue
        kind = op.get("op")
        if kind not in VALID_OPS:
            errors.append(f"{prefix}: unknown op '{kind}'")
            continue
        slot_index = op.get("slot_index")
        if slot_index is None or slot_index not in by_slot:
            errors.append(f"{prefix}: slot_index {slot_index!r} does not exist in base timeline")
            continue
        clip = by_slot[slot_index]
        after = op.get("after") or {}

        if kind == "set_duration":
            dur = after.get("duration_sec")
            if dur is None or float(dur) <= 0:
                errors.append(f"{prefix}: duration_sec must be > 0 (got {dur!r})")

        elif kind == "set_source_window":
            start = after.get("source_start_sec")
            sdur = after.get("source_duration_sec")
            if start is None or float(start) < 0:
                errors.append(f"{prefix}: source_start_sec must be >= 0 (got {start!r})")
            if sdur is None or float(sdur) <= 0:
                errors.append(f"{prefix}: source_duration_sec must be > 0 (got {sdur!r})")
            if start is not None and sdur is not None and float(start) >= 0 and float(sdur) > 0:
                window = _source_window_for(clip, material_map if isinstance(material_map, dict) else None)
                if window is not None and float(start) + float(sdur) > window + 1e-6:
                    errors.append(
                        f"{prefix}: source window {float(start)}+{float(sdur)} exceeds "
                        f"source duration {window}"
                    )

        elif kind == "move_clip":
            new_index = after.get("new_index")
            if new_index is None or not isinstance(new_index, int):
                errors.append(f"{prefix}: move_clip requires integer after.new_index")
            elif new_index < 0 or new_index >= n:
                errors.append(f"{prefix}: new_index {new_index} out of range [0,{n - 1}]")

        elif kind == "replace_clip":
            _asset, _scene, _scene_index, repl_errors = _replacement_asset_scene(
                material_map if isinstance(material_map, dict) else None,
                after,
            )
            errors.extend(f"{prefix}: {e}" for e in repl_errors)

    return (len(errors) == 0), errors


# --------------------------------------------------------------------------- #
# Spec FALLBACK alignment (save-time reconciliation)
# --------------------------------------------------------------------------- #
def _is_image_source(source: Optional[str]) -> bool:
    if not source:
        return False
    return os.path.splitext(str(source))[1].lower() in {
        ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp",
    }


def align_clip_to_contract(
    clip: Dict[str, Any],
    source_window: Optional[float],
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Normalize one plan clip back onto the canonical timeline field spec.

    Fallback corrections (never raise -- this is the save-time safety net that
    *fixes* drift rather than rejecting it):
      - slot_dur / extract_dur must be > 0 (fall back to each other, else a min).
      - extract_start clamped to >= 0 and within the source window.
      - extract_start + extract_dur clamped to the source window.
      - image clips pinned to extract_start 0.
      - numeric fields rounded to 3 dp for deterministic artifacts.
    Returns ``(clip, corrections)`` where corrections lists every auto-fix.
    """
    corrections: List[Dict[str, Any]] = []
    slot = clip.get("slot_index")

    def fix(field: str, old: Any, new: Any, reason: str) -> None:
        corrections.append({"slot_index": slot, "field": field,
                            "from": old, "to": new, "reason": reason})

    is_image = _is_image_source(clip.get("source"))

    slot_dur = clip.get("slot_dur")
    extract_dur = clip.get("extract_dur")
    extract_start = clip.get("extract_start")

    # 1. slot_dur sane.
    if not isinstance(slot_dur, (int, float)) or float(slot_dur) <= 0:
        fallback = float(extract_dur) if isinstance(extract_dur, (int, float)) and extract_dur > 0 else 1.0
        fix("slot_dur", slot_dur, fallback, "non-positive slot_dur fell back")
        clip["slot_dur"] = fallback
        slot_dur = fallback

    # 2. extract_dur sane (mirror slot_dur when missing).
    if not isinstance(extract_dur, (int, float)) or float(extract_dur) <= 0:
        fix("extract_dur", extract_dur, float(slot_dur), "missing extract_dur mirrored slot_dur")
        clip["extract_dur"] = float(slot_dur)
        extract_dur = float(slot_dur)

    # 3. extract_start spec.
    if is_image:
        if extract_start not in (0, 0.0, None):
            fix("extract_start", extract_start, 0.0, "image clip pinned to source start 0")
        clip["extract_start"] = 0.0
        extract_start = 0.0
    else:
        if not isinstance(extract_start, (int, float)) or float(extract_start) < 0:
            fix("extract_start", extract_start, 0.0, "negative/missing extract_start clamped to 0")
            clip["extract_start"] = 0.0
            extract_start = 0.0

    # 4. source-window clamp (the FALLBACK alignment to material spec).
    if source_window is not None and not is_image:
        if float(extract_start) > float(source_window):
            fix("extract_start", extract_start, 0.0, "extract_start beyond source window reset to 0")
            clip["extract_start"] = 0.0
            extract_start = 0.0
        overshoot = float(extract_start) + float(extract_dur) - float(source_window)
        if overshoot > 1e-6:
            new_dur = round(max(0.0, float(source_window) - float(extract_start)), 3)
            if new_dur <= 0:
                new_dur = round(min(float(extract_dur), float(source_window)), 3)
                fix("extract_start", extract_start, 0.0, "window did not fit; reset start to 0")
                clip["extract_start"] = 0.0
            fix("extract_dur", extract_dur, new_dur, "source window clamped to material duration")
            clip["extract_dur"] = new_dur
            extract_dur = new_dur

    # 5. deterministic rounding.
    for f in ("slot_dur", "extract_dur", "extract_start"):
        if isinstance(clip.get(f), (int, float)):
            clip[f] = round(float(clip[f]), 3)

    return clip, corrections


def align_plan_to_contract(
    plan: List[Dict[str, Any]],
    material_map: Optional[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Align every clip to the contract spec; return ``(plan, corrections)``."""
    all_corrections: List[Dict[str, Any]] = []
    for clip in plan:
        window = _source_window_for(clip, material_map if isinstance(material_map, dict) else None)
        _, corr = align_clip_to_contract(clip, window)
        all_corrections.extend(corr)
    return plan, all_corrections


# --------------------------------------------------------------------------- #
# Apply
# --------------------------------------------------------------------------- #
def apply_patch(artifact_root: str, patch: Dict[str, Any]) -> Dict[str, Any]:
    """Apply a *validated* patch and return a patched-draft timeline dict.

    Deterministic. Never writes to disk and never mutates the base timeline.
    Raises ``ValueError`` if the patch does not validate.
    """
    ok, errors = validate_patch(artifact_root, patch)
    if not ok:
        raise ValueError("invalid patch: " + "; ".join(errors))

    root = Path(artifact_root)
    base, base_name = _resolve_base_timeline(root)
    result = copy.deepcopy(base)
    plan = _plan_of(result)
    by_slot = _index_by_slot(plan)
    material_map = _load_json(root / "project_material_map.json")

    for op in patch.get("patches", []):
        kind = op.get("op")
        slot_index = op.get("slot_index")
        clip = by_slot.get(slot_index)
        if clip is None:
            continue
        after = op.get("after") or {}

        if kind == "set_duration":
            clip["slot_dur"] = float(after["duration_sec"])

        elif kind == "set_source_window":
            clip["extract_start"] = float(after["source_start_sec"])
            clip["extract_dur"] = float(after["source_duration_sec"])

        elif kind == "move_clip":
            new_index = int(after["new_index"])
            cur = plan.index(clip)
            plan.insert(new_index, plan.pop(cur))

        elif kind == "replace_clip":
            asset, scene, scene_index, _errors = _replacement_asset_scene(
                material_map if isinstance(material_map, dict) else None,
                after,
            )
            if not asset or scene is None or scene_index is None:
                continue
            asset_type = str(asset.get("asset_type") or "").lower()
            is_photo = asset_type in {"photo", "image"}
            source = str(asset["source"])
            keep_dur = clip.get("slot_dur") or clip.get("duration_sec") or clip.get("extract_dur")
            duration = float(after.get("duration_sec") or keep_dur or 1.0)
            clip["source"] = source
            clip["scene_id"] = f"{asset['asset_id']}:{scene_index}"
            clip["slot_dur"] = duration
            if is_photo:
                clip["extract_start"] = 0.0
                clip["extract_dur"] = duration
            else:
                start = float(scene["start"])
                end = float(scene["end"])
                clip["extract_start"] = start
                clip["extract_dur"] = round(end - start, 3)
            for key in ("caption", "visual_family", "angle_scale", "action_family", "subject", "function"):
                if scene.get(key) is not None:
                    clip[key] = scene.get(key)
                elif key in clip:
                    clip.pop(key, None)
            clip["asset_id"] = asset["asset_id"]
            clip["asset_type"] = asset.get("asset_type")

    # Save-time FALLBACK alignment: reconcile the edited plan back onto the
    # canonical timeline field spec and clamp anything that drifted off the
    # material window. This is what makes the saved artifact contract-conformant.
    _, corrections = align_plan_to_contract(plan, material_map if isinstance(material_map, dict) else None)

    result["_patched_from"] = base_name
    result["_patch_base_ref"] = patch.get("base_timeline_ref")
    result["_patch_op_count"] = len(patch.get("patches", []))
    result["_spec_alignment"] = {
        "aligned": True,
        "correction_count": len(corrections),
        "corrections": corrections,
    }
    return result


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _cmd_validate(args: argparse.Namespace) -> int:
    patch = _load_json(Path(args.patch))
    if patch is None:
        print(f"[timeline_patch] could not read patch: {args.patch}")
        return 2
    ok, errors = validate_patch(args.artifact_root, patch)
    if ok:
        print(f"[timeline_patch] OK ({len(patch.get('patches', []))} ops valid)")
        return 0
    print("[timeline_patch] INVALID:")
    for e in errors:
        print(f"  - {e}")
    return 1


def _cmd_apply(args: argparse.Namespace) -> int:
    out_name = os.path.basename(str(args.out))
    if out_name in PROTECTED_OUTPUTS:
        print(f"[timeline_patch] refusing to write protected canonical artifact: {out_name}")
        return 2

    patch = _load_json(Path(args.patch))
    if patch is None:
        print(f"[timeline_patch] could not read patch: {args.patch}")
        return 2

    try:
        result = apply_patch(args.artifact_root, patch)
    except ValueError as exc:
        print(f"[timeline_patch] {exc}")
        return 1

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = Path(args.artifact_root) / out_path
    if out_path.name in PROTECTED_OUTPUTS:
        print(f"[timeline_patch] refusing to overwrite canonical artifact: {out_path.name}")
        return 2
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[timeline_patch] wrote {out_path}")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Hermes-native timeline_patch tool")
    sub = parser.add_subparsers(dest="command", required=True)

    val = sub.add_parser("validate", help="Validate a timeline_patch against the base timeline")
    val.add_argument("--artifact-root", required=True)
    val.add_argument("--patch", required=True)
    val.set_defaults(func=_cmd_validate)

    app = sub.add_parser("apply", help="Apply a timeline_patch into a patched-draft timeline")
    app.add_argument("--artifact-root", required=True)
    app.add_argument("--patch", required=True)
    app.add_argument("--out", default="patched_draft_timeline.json")
    app.set_defaults(func=_cmd_apply)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
