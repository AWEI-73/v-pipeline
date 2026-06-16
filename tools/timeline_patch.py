#!/usr/bin/env python
"""Hermes-native ``timeline_patch`` contract.

The native workbench never overwrites canonical artifacts. Every interactive
edit (duration / source window / clip order) is captured as a ``timeline_patch``
op-list. This module validates a patch against the base timeline and applies it
into a *new* ``patched_draft_timeline.json`` -- it never writes ``timeline.json``.

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
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ARTIFACT_ROLE = "timeline_patch"
SCHEMA_VERSION = 1

VALID_OPS = {"set_duration", "set_source_window", "move_clip"}

# Canonical artifacts that a patch must never overwrite.
PROTECTED_OUTPUTS = {
    "timeline.json",
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

    return (len(errors) == 0), errors


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

    result["_patched_from"] = base_name
    result["_patch_base_ref"] = patch.get("base_timeline_ref")
    result["_patch_op_count"] = len(patch.get("patches", []))
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
