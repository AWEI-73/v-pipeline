#!/usr/bin/env python
"""Hermes-native workbench: patch -> pipeline contract *draft* sync.

This is NOT an editor and NOT a canonical-contract writer. It translates a
``timeline_patch`` (the workbench's only edit channel) into a **draft**
``workbench_contract_patch.json`` that *describes what the workbench would like
the pipeline contract to change* -- without ever touching the canonical
``segment_contract.json`` / ``timeline.json`` / ``project_material_map.json`` /
``material_needs.json``. Official rendering still runs through the Agent / ffmpeg
pipeline, which can consume the draft/patch and then build.

Sync rules (see docs/decisions/2026-06-16-native-preview-engine.md):
  - set_duration       -> per-segment duration suggestion (draft only)
  - set_source_window  -> material window override (draft), validated to stay
                          inside the project_material_map scene bounds
  - move_clip          -> stays in the timeline draft; intra-segment reorder is
                          info-only, cross-segment is diagnosed
                          ``unsupported_for_contract_sync`` (never silently
                          rewrites segment order)

Fail-closed: unknown slot, non-finite / non-positive duration, or a source
window beyond the material scene bounds aborts the whole sync with no artifact
written. Soft "can't align to contract" cases are diagnosed but still yield a
timeline draft.

CLI::

    python tools/workbench_patch_to_contract.py sync \
        --artifact-root <root> --patch timeline_patch.json \
        [--out-contract workbench_contract_patch.json] \
        [--out-timeline patched_draft_timeline.json]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:  # works as `tools.workbench_patch_to_contract` (tests) and as a script
    from tools import timeline_patch as tp
except ImportError:  # pragma: no cover - direct-script fallback
    import timeline_patch as tp

ARTIFACT_ROLE = "workbench_contract_patch"
SCHEMA_VERSION = 1

OUT_CONTRACT = "workbench_contract_patch.json"
OUT_TIMELINE = "patched_draft_timeline.json"

# Files this tool is permitted to write. Everything canonical is excluded.
WRITABLE_OUTPUTS = {OUT_CONTRACT, OUT_TIMELINE}
PROTECTED_OUTPUTS = set(tp.PROTECTED_OUTPUTS)

CONTRACT_CANDIDATES = ("revised_segment_contract.json", "segment_contract.json")


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _load_json(path: Path) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _is_finite_number(x: Any) -> bool:
    try:
        return math.isfinite(float(x))
    except (TypeError, ValueError):
        return False


def _resolve_contract(root: Path) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    for name in CONTRACT_CANDIDATES:
        data = _load_json(root / name)
        if isinstance(data, dict):
            return data, name
    return None, None


def _normalize(p: str) -> str:
    return os.path.normcase(os.path.normpath(str(p)))


def _find_asset(source: Optional[str], material_map: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not source or not isinstance(material_map, dict):
        return None
    key = _normalize(source)
    for asset in material_map.get("assets", []) or []:
        if asset.get("source") and _normalize(asset["source"]) == key:
            return asset
    return None


def _scene_index(scene_id: Optional[str]) -> Optional[int]:
    if not scene_id:
        return None
    m = re.search(r":(\d+)$", str(scene_id))
    return int(m.group(1)) if m else None


def scene_bounds(clip: Dict[str, Any], material_map: Optional[Dict[str, Any]]) -> Optional[Tuple[float, float]]:
    """Return ``(start, end)`` source-seconds for the clip's scene, or None."""
    asset = _find_asset(clip.get("source"), material_map)
    if not asset:
        return None
    scenes = asset.get("scenes") or []
    idx = _scene_index(clip.get("scene_id"))
    if idx is not None and 0 <= idx < len(scenes):
        s = scenes[idx]
        if s.get("start") is not None and s.get("end") is not None:
            return float(s["start"]), float(s["end"])
    return None


def _index_by_slot(plan: List[Dict[str, Any]]) -> Dict[Any, Dict[str, Any]]:
    out: Dict[Any, Dict[str, Any]] = {}
    for i, clip in enumerate(plan):
        out[clip.get("slot_index", i)] = clip
    return out


def _segment_block_contiguous(plan: List[Dict[str, Any]], segment: Any) -> bool:
    """True iff every clip of ``segment`` forms one contiguous run in ``plan``."""
    positions = [i for i, c in enumerate(plan) if c.get("segment") == segment]
    if not positions:
        return True
    return positions == list(range(positions[0], positions[0] + len(positions)))


def _segment_durations(plan: List[Dict[str, Any]]) -> Dict[Any, float]:
    totals: Dict[Any, float] = {}
    for c in plan:
        seg = c.get("segment")
        totals[seg] = round(totals.get(seg, 0.0) + float(c.get("slot_dur") or 0.0), 3)
    return totals


# --------------------------------------------------------------------------- #
# Core
# --------------------------------------------------------------------------- #
def _preflight(artifact_root: str, patch: Dict[str, Any], base_plan: List[Dict[str, Any]],
               by_slot: Dict[Any, Dict[str, Any]], material_map: Optional[Dict[str, Any]]) -> List[str]:
    """Fail-closed structural validation beyond timeline_patch.validate_patch:
    finite numbers and material *scene* bounds (tighter than asset duration)."""
    errors: List[str] = []
    ok, base_errors = tp.validate_patch(artifact_root, patch)
    errors.extend(base_errors)

    for i, op in enumerate(patch.get("patches", []) or []):
        if not isinstance(op, dict):
            continue
        kind = op.get("op")
        after = op.get("after") or {}
        prefix = f"patches[{i}]"

        if kind == "set_duration":
            d = after.get("duration_sec")
            if not _is_finite_number(d) or float(d) <= 0:
                errors.append(f"{prefix}: duration_sec must be a finite positive number")

        elif kind == "set_source_window":
            ss = after.get("source_start_sec")
            sd = after.get("source_duration_sec")
            if not _is_finite_number(ss) or float(ss) < 0:
                errors.append(f"{prefix}: source_start_sec must be finite >= 0")
            if not _is_finite_number(sd) or float(sd) <= 0:
                errors.append(f"{prefix}: source_duration_sec must be finite > 0")
            clip = by_slot.get(op.get("slot_index"))
            if clip and _is_finite_number(ss) and _is_finite_number(sd):
                bounds = scene_bounds(clip, material_map)
                if bounds is not None:
                    lo, hi = bounds
                    if float(ss) < lo - 1e-6 or float(ss) + float(sd) > hi + 1e-6:
                        errors.append(
                            f"{prefix}: source window [{float(ss)},{float(ss) + float(sd)}] "
                            f"exceeds scene bounds [{lo},{hi}]")
    # de-dup, keep order
    seen = set()
    deduped = []
    for e in errors:
        if e not in seen:
            seen.add(e)
            deduped.append(e)
    return deduped


def sync_patch_to_contract(artifact_root: str, patch: Dict[str, Any]) -> Dict[str, Any]:
    """Translate a timeline_patch into a draft contract patch + timeline draft.

    Returns ``{ok, workbench_contract_patch, patched_draft_timeline, diagnostics,
    errors}``. On fail-closed errors, both draft payloads are ``None``.
    """
    root = Path(artifact_root)
    diagnostics: List[Dict[str, Any]] = []

    base_timeline, base_name = tp._resolve_base_timeline(root)
    if base_timeline is None:
        return {"ok": False, "errors": ["no base timeline found"],
                "workbench_contract_patch": None, "patched_draft_timeline": None,
                "diagnostics": diagnostics}

    base_plan = tp._plan_of(base_timeline)
    by_slot = _index_by_slot(base_plan)
    material_map = _load_json(root / "project_material_map.json")
    material_map = material_map if isinstance(material_map, dict) else None

    errors = _preflight(artifact_root, patch, base_plan, by_slot, material_map)
    if errors:
        return {"ok": False, "errors": errors,
                "workbench_contract_patch": None, "patched_draft_timeline": None,
                "diagnostics": diagnostics}

    # Timeline draft (validated + spec-aligned; slot_index identity preserved).
    patched = tp.apply_patch(artifact_root, patch)
    patched_plan = tp._plan_of(patched)
    seg_durations = _segment_durations(patched_plan)

    contract, contract_name = _resolve_contract(root)
    changes: List[Dict[str, Any]] = []

    for op in patch.get("patches", []) or []:
        kind = op.get("op")
        slot = op.get("slot_index")
        clip = by_slot.get(slot)
        after = op.get("after") or {}
        if clip is None:
            continue

        if kind == "set_duration":
            seg = clip.get("segment")
            if seg is not None:
                changes.append({
                    "op": "segment_duration_suggestion",
                    "segment": seg,
                    "slot_index": slot,
                    "from": {"duration_sec": clip.get("slot_dur")},
                    "to": {
                        "requested_duration_sec": float(after["duration_sec"]),
                        "implied_segment_duration_sec": seg_durations.get(seg),
                    },
                    "reason": "workbench clip duration adjustment",
                })
                diagnostics.append({"level": "info", "code": "synced_to_contract",
                                    "op": kind, "slot_index": slot, "segment": seg})
            else:
                diagnostics.append({"level": "info", "code": "no_segment_for_clip",
                                    "op": kind, "slot_index": slot,
                                    "message": "duration change stays in timeline draft only"})

        elif kind == "set_source_window":
            if clip.get("source") and clip.get("scene_id"):
                changes.append({
                    "op": "material_window_override",
                    "segment": clip.get("segment"),
                    "slot_index": slot,
                    "scene_id": clip.get("scene_id"),
                    "source": clip.get("source"),
                    "from": {"source_start_sec": clip.get("extract_start"),
                             "source_duration_sec": clip.get("extract_dur")},
                    "to": {"source_start_sec": float(after["source_start_sec"]),
                           "source_duration_sec": float(after["source_duration_sec"])},
                    "reason": "workbench material window override",
                })
                diagnostics.append({"level": "info", "code": "synced_to_contract",
                                    "op": kind, "slot_index": slot})
            else:
                diagnostics.append({"level": "warning", "code": "missing_scene_or_source",
                                    "op": kind, "slot_index": slot,
                                    "message": "no scene_id/source; override stays in timeline draft only"})

        elif kind == "move_clip":
            seg = clip.get("segment")
            if _segment_block_contiguous(patched_plan, seg):
                diagnostics.append({"level": "info", "code": "intra_segment_reorder",
                                    "op": kind, "slot_index": slot, "segment": seg,
                                    "message": "clip ordering kept in timeline draft only"})
            else:
                diagnostics.append({"level": "warning", "code": "unsupported_for_contract_sync",
                                    "op": kind, "slot_index": slot, "segment": seg,
                                    "message": "cross-segment move not synced to contract; "
                                               "timeline draft only, segment order unchanged"})

    contract_patch = {
        "artifact_role": ARTIFACT_ROLE,
        "version": SCHEMA_VERSION,
        "base_contract_ref": contract_name,
        "base_timeline_ref": base_name,
        "changes": changes,
        "diagnostics": diagnostics,
    }
    return {"ok": True, "errors": [],
            "workbench_contract_patch": contract_patch,
            "patched_draft_timeline": patched,
            "diagnostics": diagnostics}


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _safe_out(root: Path, out: str, allowed: str) -> Path:
    name = os.path.basename(str(out))
    if name in PROTECTED_OUTPUTS or name not in WRITABLE_OUTPUTS:
        raise ValueError(f"refusing to write non-whitelisted/canonical artifact: {name}")
    p = Path(out)
    return p if p.is_absolute() else root / p


def _cmd_sync(args: argparse.Namespace) -> int:
    root = Path(args.artifact_root)
    patch = _load_json(Path(args.patch))
    if patch is None:
        print(f"[contract_sync] could not read patch: {args.patch}")
        return 2

    result = sync_patch_to_contract(args.artifact_root, patch)
    if not result["ok"]:
        print("[contract_sync] FAIL (no artifact written):")
        for e in result["errors"]:
            print(f"  - {e}")
        return 1

    try:
        out_contract = _safe_out(root, args.out_contract, OUT_CONTRACT)
        out_timeline = _safe_out(root, args.out_timeline, OUT_TIMELINE)
    except ValueError as exc:
        print(f"[contract_sync] {exc}")
        return 2

    out_contract.write_text(json.dumps(result["workbench_contract_patch"], ensure_ascii=False, indent=2),
                            encoding="utf-8")
    out_timeline.write_text(json.dumps(result["patched_draft_timeline"], ensure_ascii=False, indent=2),
                            encoding="utf-8")
    print(json.dumps({
        "ok": True,
        "written": [out_contract.name, out_timeline.name],
        "changes": len(result["workbench_contract_patch"]["changes"]),
        "diagnostics": len(result["diagnostics"]),
    }, ensure_ascii=False, indent=2))
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Workbench patch -> pipeline contract draft sync")
    sub = parser.add_subparsers(dest="command", required=True)
    s = sub.add_parser("sync", help="Translate a timeline_patch into a draft contract patch")
    s.add_argument("--artifact-root", required=True)
    s.add_argument("--patch", required=True)
    s.add_argument("--out-contract", default=OUT_CONTRACT)
    s.add_argument("--out-timeline", default=OUT_TIMELINE)
    s.set_defaults(func=_cmd_sync)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
