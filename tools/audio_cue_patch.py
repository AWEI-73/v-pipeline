#!/usr/bin/env python
"""Hermes-native workbench: audio_cue_patch contract (Layer 2).

Marks sound-effect *cues* on the timeline (hit / whoosh / riser / …). This is an
intent/marker layer -- not a mixer and not an audio renderer. Cues are captured
as a draft patch the Agent / FFmpeg / Node14 pipeline can later honour.

CLI::

    python tools/audio_cue_patch.py validate --artifact-root <root> --patch audio_cue_patch.json
    python tools/audio_cue_patch.py apply --artifact-root <root> --patch audio_cue_patch.json --out audio_cues_draft.json
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

ARTIFACT_ROLE = "audio_cue_patch"
SCHEMA_VERSION = 1
CUE_OPS = {"add_cue", "move_cue", "delete_cue"}
CUE_TYPES = {"hit", "whoosh", "riser", "impact", "bell", "transition", "title_pop"}
TIME_SLACK_SEC = 1.0  # cues may sit up to 1s past the end (tail accents)


def _is_finite(x: Any) -> bool:
    try:
        return math.isfinite(float(x))
    except (TypeError, ValueError):
        return False


def _timeline_context(artifact_root: str) -> Tuple[float, set]:
    """Return ``(duration_sec, {slot_index,...})`` from the built preview."""
    preview = pt.build_preview_timeline(artifact_root, "")
    slots = {c["slot_index"] for c in preview.get("clips", [])}
    return float(preview.get("duration_sec") or 0.0), slots


def validate_audio_cue_patch(
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

    duration, slots = _timeline_context(artifact_root)
    max_time = duration + TIME_SLACK_SEC
    live: set = set()  # cue_ids defined so far in this patch

    for i, op in enumerate(ops):
        prefix = f"patches[{i}]"
        if not isinstance(op, dict):
            errors.append(f"{prefix}: must be an object")
            continue
        kind = op.get("op")
        if kind not in CUE_OPS:
            errors.append(f"{prefix}: unknown op '{kind}'")
            continue
        cue_id = op.get("cue_id")
        if not cue_id:
            errors.append(f"{prefix}: cue_id is required")
            continue
        after = op.get("after") or {}

        if kind == "add_cue":
            ct = after.get("cue_type")
            if ct not in CUE_TYPES:
                errors.append(f"{prefix}: cue_type {ct!r} not in {sorted(CUE_TYPES)}")
            t = after.get("time_sec")
            if not _is_finite(t) or float(t) < 0 or float(t) > max_time:
                errors.append(f"{prefix}: time_sec must be finite in [0,{max_time}] (got {t!r})")
            strength = after.get("strength")
            if not isinstance(strength, int) or isinstance(strength, bool) or not (1 <= strength <= 5):
                errors.append(f"{prefix}: strength must be int 1..5 (got {strength!r})")
            anchor = after.get("anchor_clip_slot_index")
            if anchor is not None and anchor not in slots:
                errors.append(f"{prefix}: anchor_clip_slot_index {anchor!r} not found")
            live.add(cue_id)

        elif kind == "move_cue":
            if cue_id not in live:
                errors.append(f"{prefix}: move_cue target {cue_id!r} does not exist")
            t = after.get("time_sec")
            if not _is_finite(t) or float(t) < 0 or float(t) > max_time:
                errors.append(f"{prefix}: time_sec must be finite in [0,{max_time}] (got {t!r})")

        elif kind == "delete_cue":
            if cue_id not in live:
                errors.append(f"{prefix}: delete_cue target {cue_id!r} does not exist")
            else:
                live.discard(cue_id)

    return (len(errors) == 0), errors, diagnostics


def apply_audio_cue_patch(artifact_root: str, patch: Dict[str, Any]) -> Dict[str, Any]:
    """Apply a *validated* cue patch into a resolved cue list (draft)."""
    ok, errors, diagnostics = validate_audio_cue_patch(artifact_root, patch)
    if not ok:
        raise ValueError("invalid audio cue patch: " + "; ".join(errors))

    cues: Dict[str, Dict[str, Any]] = {}
    for op in patch.get("patches", []):
        kind = op.get("op")
        cue_id = op.get("cue_id")
        after = op.get("after") or {}
        if kind == "add_cue":
            cues[cue_id] = {
                "cue_id": cue_id,
                "time_sec": round(float(after["time_sec"]), 3),
                "cue_type": after["cue_type"],
                "strength": int(after["strength"]),
                "anchor_clip_slot_index": after.get("anchor_clip_slot_index"),
            }
        elif kind == "move_cue" and cue_id in cues:
            cues[cue_id]["time_sec"] = round(float(after["time_sec"]), 3)
        elif kind == "delete_cue":
            cues.pop(cue_id, None)

    ordered = sorted(cues.values(), key=lambda c: c["time_sec"])
    return {
        "artifact_role": "audio_cues_draft",
        "version": SCHEMA_VERSION,
        "cues": ordered,
        "diagnostics": diagnostics,
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
        print(f"[audio_cue_patch] could not read patch: {args.patch}")
        return 2
    ok, errors, _ = validate_audio_cue_patch(args.artifact_root, patch)
    if ok:
        print(f"[audio_cue_patch] OK ({len(patch.get('patches', []))} ops)")
        return 0
    for e in errors:
        print(f"  - {e}")
    return 1


def _cmd_apply(args: argparse.Namespace) -> int:
    patch = _load_json(Path(args.patch))
    if patch is None:
        print(f"[audio_cue_patch] could not read patch: {args.patch}")
        return 2
    try:
        result = apply_audio_cue_patch(args.artifact_root, patch)
    except ValueError as exc:
        print(f"[audio_cue_patch] {exc}")
        return 1
    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = Path(args.artifact_root) / out_path
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[audio_cue_patch] wrote {out_path}")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Hermes-native audio_cue_patch tool")
    sub = parser.add_subparsers(dest="command", required=True)
    v = sub.add_parser("validate")
    v.add_argument("--artifact-root", required=True)
    v.add_argument("--patch", required=True)
    v.set_defaults(func=_cmd_validate)
    a = sub.add_parser("apply")
    a.add_argument("--artifact-root", required=True)
    a.add_argument("--patch", required=True)
    a.add_argument("--out", default="audio_cues_draft.json")
    a.set_defaults(func=_cmd_apply)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
