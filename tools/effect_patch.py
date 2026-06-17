#!/usr/bin/env python
"""Hermes-native workbench: effect_patch contract (Layer 3).

Effect *intent* markers/presets on clips (title_reveal / zoom_punch / …). This is
intent only -- it does NOT run Node14, does NOT render effects, and produces no
final video. The Agent / Node14 pipeline may later consume the intent.

Out-of-clip effect windows are **fail-closed** (chosen over clamping for an
unambiguous contract); the error names the offending clip window.

CLI::

    python tools/effect_patch.py validate --artifact-root <root> --patch effect_patch.json
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from tools import preview_timeline as pt
except ImportError:  # pragma: no cover - direct-script fallback
    import preview_timeline as pt

ARTIFACT_ROLE = "effect_patch"
SCHEMA_VERSION = 1
EFFECT_OPS = {"add_effect", "delete_effect"}
PRESETS = {
    "title_reveal", "zoom_punch", "flash", "speed_ramp_hint",
    "freeze_frame_hint", "shake_light", "caption_emphasis",
}
EFFECT_ASSET_TYPES = {"effect_overlay", "motion_asset"}
EPS = 1e-6


def _is_finite(x: Any) -> bool:
    try:
        return math.isfinite(float(x))
    except (TypeError, ValueError):
        return False


def _clip_windows(artifact_root: str) -> Dict[Any, Tuple[float, float]]:
    """slot_index -> (timeline_start_sec, timeline_end_sec)."""
    preview = pt.build_preview_timeline(artifact_root, "", include_effect_patch=False)
    out: Dict[Any, Tuple[float, float]] = {}
    for c in preview.get("clips", []):
        start = float(c.get("timeline_start_sec") or 0.0)
        out[c["slot_index"]] = (start, start + float(c.get("duration_sec") or 0.0))
    return out


def _effect_assets(artifact_root: str) -> Dict[str, Dict[str, Any]]:
    project_map = Path(artifact_root) / "project_material_map.json"
    if not project_map.is_file():
        return {}
    try:
        payload = json.loads(project_map.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    out: Dict[str, Dict[str, Any]] = {}
    for asset in payload.get("assets") or []:
        if not isinstance(asset, dict):
            continue
        aid = asset.get("asset_id")
        if isinstance(aid, str) and aid.strip():
            out[aid] = asset
    return out


def validate_effect_patch(
    artifact_root: str, patch: Dict[str, Any]
) -> Tuple[bool, List[str], List[Dict[str, Any]]]:
    errors: List[str] = []
    diagnostics: List[Dict[str, Any]] = []

    if not isinstance(patch, dict):
        return False, ["patch must be a JSON object"], diagnostics
    if patch.get("artifact_role") != ARTIFACT_ROLE:
        errors.append(f"artifact_role must be '{ARTIFACT_ROLE}'")
    ops = patch.get("patches")
    if not isinstance(ops, list):
        return False, errors + ["'patches' must be a list"], diagnostics

    windows = _clip_windows(artifact_root)
    effect_assets = _effect_assets(artifact_root)
    live: set = set()

    for i, op in enumerate(ops):
        prefix = f"patches[{i}]"
        if not isinstance(op, dict):
            errors.append(f"{prefix}: must be an object")
            continue
        kind = op.get("op")
        if kind not in EFFECT_OPS:
            errors.append(f"{prefix}: unknown op '{kind}'")
            continue
        eid = op.get("effect_id")
        if not eid:
            errors.append(f"{prefix}: effect_id is required")
            continue
        after = op.get("after") or {}

        if kind == "add_effect":
            preset = after.get("preset")
            if preset not in PRESETS:
                errors.append(f"{prefix}: preset {preset!r} not in {sorted(PRESETS)}")
            asset_id = after.get("asset_id")
            if asset_id is not None:
                if not isinstance(asset_id, str) or not asset_id.strip():
                    errors.append(f"{prefix}: asset_id must be a non-empty string when present")
                elif asset_id not in effect_assets:
                    errors.append(f"{prefix}: effect asset_id {asset_id!r} not found in project_material_map")
                elif effect_assets[asset_id].get("asset_type") not in EFFECT_ASSET_TYPES:
                    errors.append(
                        f"{prefix}: asset_id {asset_id!r} is not an effect asset "
                        f"(asset_type must be one of {sorted(EFFECT_ASSET_TYPES)})")
            target = after.get("target_slot_index")
            if target not in windows:
                errors.append(f"{prefix}: target_slot_index {target!r} not found")
            intensity = after.get("intensity")
            if not isinstance(intensity, int) or isinstance(intensity, bool) or not (1 <= intensity <= 5):
                errors.append(f"{prefix}: intensity must be int 1..5 (got {intensity!r})")
            start = after.get("start_sec")
            dur = after.get("duration_sec")
            if not _is_finite(start) or float(start) < 0:
                errors.append(f"{prefix}: start_sec must be finite >= 0 (got {start!r})")
            if not _is_finite(dur) or float(dur) <= 0:
                errors.append(f"{prefix}: duration_sec must be finite > 0 (got {dur!r})")
            # window must fit inside the target clip
            if target in windows and _is_finite(start) and _is_finite(dur):
                lo, hi = windows[target]
                if float(start) < lo - EPS or float(start) + float(dur) > hi + EPS:
                    errors.append(
                        f"{prefix}: effect window [{float(start)},{float(start) + float(dur)}] "
                        f"outside target clip window [{lo},{hi}]")
            live.add(eid)

        elif kind == "delete_effect":
            if eid not in live:
                errors.append(f"{prefix}: delete_effect target {eid!r} does not exist")
            else:
                live.discard(eid)

    return (len(errors) == 0), errors, diagnostics


def apply_effect_patch(artifact_root: str, patch: Dict[str, Any]) -> Dict[str, Any]:
    ok, errors, diagnostics = validate_effect_patch(artifact_root, patch)
    if not ok:
        raise ValueError("invalid effect patch: " + "; ".join(errors))

    effects: Dict[str, Dict[str, Any]] = {}
    for op in patch.get("patches", []):
        kind = op.get("op")
        eid = op.get("effect_id")
        after = op.get("after") or {}
        if kind == "add_effect":
            effects[eid] = {
                "effect_id": eid,
                "preset": after["preset"],
                "target_slot_index": after["target_slot_index"],
                "start_sec": round(float(after["start_sec"]), 3),
                "duration_sec": round(float(after["duration_sec"]), 3),
                "intensity": int(after["intensity"]),
            }
            if after.get("asset_id") is not None:
                effects[eid]["asset_id"] = after["asset_id"]
        elif kind == "delete_effect":
            effects.pop(eid, None)

    ordered = sorted(effects.values(), key=lambda e: e["start_sec"])
    return {
        "artifact_role": "effects_intent_draft",
        "version": SCHEMA_VERSION,
        "effects": ordered,
        "diagnostics": diagnostics,
        "note": "intent only; Node14 consumption deferred; no effect rendered",
    }


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _load_json(path: Path) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _cmd_validate(args: argparse.Namespace) -> int:
    patch = _load_json(Path(args.patch))
    if patch is None:
        print(f"[effect_patch] could not read patch: {args.patch}")
        return 2
    ok, errors, _ = validate_effect_patch(args.artifact_root, patch)
    if ok:
        print(f"[effect_patch] OK ({len(patch.get('patches', []))} ops)")
        return 0
    for e in errors:
        print(f"  - {e}")
    return 1


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Hermes-native effect_patch tool (intent only)")
    sub = parser.add_subparsers(dest="command", required=True)
    v = sub.add_parser("validate")
    v.add_argument("--artifact-root", required=True)
    v.add_argument("--patch", required=True)
    v.set_defaults(func=_cmd_validate)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
