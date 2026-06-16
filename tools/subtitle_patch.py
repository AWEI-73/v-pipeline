#!/usr/bin/env python
"""Hermes-native workbench: subtitle_patch contract (Layer 1).

Human subtitle fine-tuning (text / start / duration) captured as a draft patch.
It never rewrites the source SRT; the canonical subtitle file stays untouched and
official rendering still runs through the Agent / FFmpeg pipeline.

CLI::

    python tools/subtitle_patch.py validate --artifact-root <root> --patch subtitle_patch.json
    python tools/subtitle_patch.py apply --artifact-root <root> --patch subtitle_patch.json --out patched_draft_subtitles.json
"""
from __future__ import annotations

import argparse
import copy
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from tools import preview_timeline as pt
except ImportError:  # pragma: no cover - direct-script fallback
    import preview_timeline as pt

ARTIFACT_ROLE = "subtitle_patch"
SCHEMA_VERSION = 1
SUB_OPS = {"set_subtitle_text", "set_subtitle_timing"}
SRT_CANDIDATES = ("review_subtitles.srt", "subtitles.srt")


def _is_finite(x: Any) -> bool:
    try:
        return math.isfinite(float(x))
    except (TypeError, ValueError):
        return False


def load_base_subtitles(artifact_root: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Return ``(subtitles, source_name)`` parsed from the SRT (ids ``sub-N``)."""
    root = Path(artifact_root)
    for name in SRT_CANDIDATES:
        p = root / name
        if p.is_file():
            try:
                return pt.parse_srt(p.read_text(encoding="utf-8")), name
            except OSError:
                return [], name
    return [], None


def validate_subtitle_patch(
    artifact_root: str, patch: Dict[str, Any]
) -> Tuple[bool, List[str], List[Dict[str, Any]]]:
    """Return ``(ok, errors, diagnostics)``. Overlap is a warning, not a failure."""
    errors: List[str] = []
    diagnostics: List[Dict[str, Any]] = []

    if not isinstance(patch, dict):
        return False, ["patch must be a JSON object"], diagnostics
    if patch.get("artifact_role") != ARTIFACT_ROLE:
        errors.append(f"artifact_role must be '{ARTIFACT_ROLE}'")
    ops = patch.get("patches")
    if not isinstance(ops, list):
        return False, errors + ["'patches' must be a list"], diagnostics

    subs, _ = load_base_subtitles(artifact_root)
    by_id = {s["id"]: s for s in subs}

    # working copy to compute overlaps after timing edits
    working = {s["id"]: dict(s) for s in subs}

    for i, op in enumerate(ops):
        prefix = f"patches[{i}]"
        if not isinstance(op, dict):
            errors.append(f"{prefix}: must be an object")
            continue
        kind = op.get("op")
        if kind not in SUB_OPS:
            errors.append(f"{prefix}: unknown op '{kind}'")
            continue
        sid = op.get("subtitle_id")
        if sid not in by_id:
            errors.append(f"{prefix}: subtitle_id {sid!r} does not exist")
            continue
        after = op.get("after") or {}

        if kind == "set_subtitle_text":
            if not isinstance(after.get("text"), str):
                errors.append(f"{prefix}: set_subtitle_text requires after.text (string)")

        elif kind == "set_subtitle_timing":
            start = after.get("start_sec")
            dur = after.get("duration_sec")
            if not _is_finite(start) or float(start) < 0:
                errors.append(f"{prefix}: start_sec must be finite >= 0 (got {start!r})")
            if not _is_finite(dur) or float(dur) <= 0:
                errors.append(f"{prefix}: duration_sec must be finite > 0 (got {dur!r})")
            if _is_finite(start) and _is_finite(dur):
                working[sid]["start_sec"] = float(start)
                working[sid]["duration_sec"] = float(dur)

    # overlap diagnostics (warning only)
    ordered = sorted(working.values(), key=lambda s: s["start_sec"])
    for a, b in zip(ordered, ordered[1:]):
        if a["start_sec"] + a["duration_sec"] > b["start_sec"] + 1e-6:
            diagnostics.append({
                "level": "warning", "code": "subtitle_overlap",
                "between": [a["id"], b["id"]],
                "message": f"{a['id']} overlaps {b['id']}",
            })

    return (len(errors) == 0), errors, diagnostics


def apply_subtitle_patch(artifact_root: str, patch: Dict[str, Any]) -> Dict[str, Any]:
    """Apply a *validated* subtitle patch, returning a draft subtitle list.

    Never writes the SRT. Raises ``ValueError`` if the patch is invalid.
    """
    ok, errors, diagnostics = validate_subtitle_patch(artifact_root, patch)
    if not ok:
        raise ValueError("invalid subtitle patch: " + "; ".join(errors))

    subs, base_name = load_base_subtitles(artifact_root)
    by_id = {s["id"]: dict(s) for s in subs}

    for op in patch.get("patches", []):
        sid = op.get("subtitle_id")
        clip = by_id.get(sid)
        if clip is None:
            continue
        after = op.get("after") or {}
        if op.get("op") == "set_subtitle_text":
            clip["text"] = after["text"]
        elif op.get("op") == "set_subtitle_timing":
            clip["start_sec"] = round(float(after["start_sec"]), 3)
            clip["duration_sec"] = round(float(after["duration_sec"]), 3)

    return {
        "artifact_role": "patched_draft_subtitles",
        "version": SCHEMA_VERSION,
        "base_subtitle_ref": base_name,
        "subtitles": [by_id[s["id"]] for s in subs],
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
        print(f"[subtitle_patch] could not read patch: {args.patch}")
        return 2
    ok, errors, diagnostics = validate_subtitle_patch(args.artifact_root, patch)
    if ok:
        print(f"[subtitle_patch] OK ({len(patch.get('patches', []))} ops, "
              f"{len(diagnostics)} diagnostics)")
        return 0
    for e in errors:
        print(f"  - {e}")
    return 1


def _cmd_apply(args: argparse.Namespace) -> int:
    patch = _load_json(Path(args.patch))
    if patch is None:
        print(f"[subtitle_patch] could not read patch: {args.patch}")
        return 2
    try:
        result = apply_subtitle_patch(args.artifact_root, patch)
    except ValueError as exc:
        print(f"[subtitle_patch] {exc}")
        return 1
    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = Path(args.artifact_root) / out_path
    if out_path.name in SRT_CANDIDATES:
        print(f"[subtitle_patch] refusing to overwrite source subtitle file: {out_path.name}")
        return 2
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[subtitle_patch] wrote {out_path}")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Hermes-native subtitle_patch tool")
    sub = parser.add_subparsers(dest="command", required=True)
    v = sub.add_parser("validate")
    v.add_argument("--artifact-root", required=True)
    v.add_argument("--patch", required=True)
    v.set_defaults(func=_cmd_validate)
    a = sub.add_parser("apply")
    a.add_argument("--artifact-root", required=True)
    a.add_argument("--patch", required=True)
    a.add_argument("--out", default="patched_draft_subtitles.json")
    a.set_defaults(func=_cmd_apply)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
