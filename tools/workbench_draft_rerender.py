#!/usr/bin/env python
"""Validated Workbench draft rerender.

This is the backend handoff path from a human-edited Workbench draft back to an
ffmpeg preview candidate. It never writes canonical ``final.mp4`` and it does
not interpret Workbench artifacts unless ``workbench_handoff.json`` validates
against the current files on disk.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Optional

_REPO_ROOT = str(Path(__file__).resolve().parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

try:
    from tools import workbench_export as wx
    from tools.workbench_handoff import validate_handoff
except ImportError:  # pragma: no cover - direct-script fallback
    import workbench_export as wx
    from workbench_handoff import validate_handoff

ARTIFACT_ROLE = "workbench_draft_rerender"
SCHEMA_VERSION = 1
DEFAULT_OUT = "workbench_rerender.mp4"
DEFAULT_REPORT = "workbench_rerender_report.json"


def _load_json(path: Path) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _artifact_ref(validation: Dict[str, Any], key: str) -> Optional[str]:
    handoff_path = Path(validation["artifact_root"]) / "workbench_handoff.json"
    handoff = _load_json(handoff_path)
    if not isinstance(handoff, dict):
        return None
    artifacts = handoff.get("artifacts")
    if not isinstance(artifacts, dict):
        return None
    rel = artifacts.get(key)
    return rel if isinstance(rel, str) and rel.strip() else None


def _write_report(root: Path, report: Dict[str, Any], report_out: Optional[str]) -> str:
    out_path = Path(report_out) if report_out else root / DEFAULT_REPORT
    if not out_path.is_absolute():
        out_path = root / out_path
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(out_path)


def rerender_from_handoff(
    artifact_root: str,
    *,
    out: str = DEFAULT_OUT,
    report_out: Optional[str] = None,
    music: Optional[str] = None,
    render_effects: bool = False,
    renderer: Callable = wx._default_renderer,
    effect_renderer: Callable = wx.apply_effects_to_video,
) -> Dict[str, Any]:
    """Validate Workbench handoff and render a non-canonical preview candidate."""
    root = Path(artifact_root)
    validation = validate_handoff(str(root))
    if not validation.get("ok"):
        raise ValueError(f"workbench handoff validation failed: {len(validation.get('errors') or [])} error(s)")

    patched_ref = _artifact_ref(validation, "patched_draft_timeline")
    patch_ref = _artifact_ref(validation, "timeline_patch")
    patched = _load_json(root / patched_ref) if patched_ref else None
    patch = _load_json(root / patch_ref) if patch_ref else None
    if patched_ref and not isinstance(patched, dict):
        raise ValueError("patched_draft_timeline referenced by handoff is not valid JSON object")
    if patch_ref and not isinstance(patch, dict):
        raise ValueError("timeline_patch referenced by handoff is not valid JSON object")
    if not patched_ref and not patch_ref:
        raise ValueError("workbench handoff has no timeline draft artifact to rerender")

    export_result = wx.export(
        str(root),
        out=out,
        patch=None if patched is not None else patch,
        patched_timeline=patched,
        music=music,
        renderer=renderer,
        render_effects=render_effects,
        effect_renderer=effect_renderer,
    )
    report = {
        "artifact_role": ARTIFACT_ROLE,
        "version": SCHEMA_VERSION,
        "ok": True,
        "artifact_root": str(root),
        "handoff_validation": {
            "ok": True,
            "error_count": 0,
            "warning_count": len(validation.get("warnings") or []),
        },
        "export": export_result,
        "canonical_changed": False,
        "note": "validated Workbench draft rerender; canonical final.mp4 untouched",
    }
    report["report_path"] = _write_report(root, report, report_out)
    return report


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Workbench handoff and render a draft preview candidate")
    parser.add_argument("artifact_root")
    parser.add_argument("--out", default=DEFAULT_OUT)
    parser.add_argument("--report-out")
    parser.add_argument("--music")
    parser.add_argument("--effects", action="store_true")
    args = parser.parse_args(argv)

    try:
        report = rerender_from_handoff(
            args.artifact_root,
            out=args.out,
            report_out=args.report_out,
            music=args.music,
            render_effects=args.effects,
        )
    except ValueError as exc:
        print(f"[workbench_draft_rerender] {exc}")
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
