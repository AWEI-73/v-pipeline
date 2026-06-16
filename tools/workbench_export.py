#!/usr/bin/env python
"""Hermes-native workbench export (opt-in).

The workbench is a lightweight editor: its primary job is interactive preview +
proposing a ``timeline_patch``. This module adds the *optional* second path the
user asked for -- "I can use one set to actually output" -- by handing the
patched plan to the **canonical ffmpeg renderer** (`mv_cut.render_mv`). It does
**not** introduce a second renderer and it never writes a canonical artifact
(``final.mp4`` et al. are hard-blocked); export lands on ``workbench_export.mp4``.

CLI::

    python tools/workbench_export.py --artifact-root <root> --patch timeline_patch.json --out workbench_export.mp4
    python tools/workbench_export.py --artifact-root <root> --patched patched_draft_timeline.json --out workbench_export.mp4
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# Ensure the repo root is importable when run as a bare script (so the lazy
# `video_pipeline_core` render import resolves; only tools/ is on path otherwise).
_REPO_ROOT = str(Path(__file__).resolve().parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

try:
    from tools import timeline_patch as tp
except ImportError:  # pragma: no cover - direct-script fallback
    import timeline_patch as tp

# Canonical outputs the export must never produce/overwrite.
PROTECTED_OUTPUTS = set(tp.PROTECTED_OUTPUTS)
DEFAULT_OUT = "workbench_export.mp4"


def _load_json(path: Path) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _default_renderer(plan, music_path, out_path, mat_dir=None):  # pragma: no cover - thin ffmpeg shim
    from video_pipeline_core.mv_cut import render_mv  # lazy: only when truly rendering
    return render_mv(plan, music_path, out_path, mat_dir=mat_dir)


def _resolve_music(root: Path) -> Optional[str]:
    for name in ("music.wav", "bgm.webm", "narration.wav"):
        p = root / name
        if p.is_file():
            return str(p)
    return None


def prepare_export_plan(
    artifact_root: str,
    patch: Optional[Dict[str, Any]] = None,
    patched_timeline: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Resolve the plan to render, spec-aligned. Source precedence:
    explicit patch  ->  given patched_timeline dict  ->  base timeline.
    Returns ``{plan, corrections, source}``.
    """
    root = Path(artifact_root)
    if patch is not None:
        applied = tp.apply_patch(artifact_root, patch)  # validates + aligns
        return {
            "plan": tp._plan_of(applied),
            "corrections": applied.get("_spec_alignment", {}).get("corrections", []),
            "source": "patch",
        }

    timeline = patched_timeline
    source = "patched_timeline"
    if timeline is None:
        timeline, name = tp._resolve_base_timeline(root)
        source = name or "base_timeline"
    if timeline is None:
        raise ValueError("no timeline available to export")

    plan = tp._plan_of(timeline)
    material_map = _load_json(root / "project_material_map.json")
    plan, corrections = tp.align_plan_to_contract(
        plan, material_map if isinstance(material_map, dict) else None)
    return {"plan": plan, "corrections": corrections, "source": source}


def export(
    artifact_root: str,
    out: str = DEFAULT_OUT,
    patch: Optional[Dict[str, Any]] = None,
    patched_timeline: Optional[Dict[str, Any]] = None,
    music: Optional[str] = None,
    renderer: Callable = _default_renderer,
) -> Dict[str, Any]:
    """Render the (patched, spec-aligned) plan via the canonical ffmpeg renderer.

    Raises ``ValueError`` for protected output names or an empty plan; never
    overwrites a canonical artifact.
    """
    root = Path(artifact_root)
    out_path = Path(out)
    if not out_path.is_absolute():
        out_path = root / out_path
    if out_path.name in PROTECTED_OUTPUTS:
        raise ValueError(f"refusing to export onto protected canonical artifact: {out_path.name}")

    prepared = prepare_export_plan(artifact_root, patch=patch, patched_timeline=patched_timeline)
    plan: List[Dict[str, Any]] = [c for c in prepared["plan"] if c.get("source")]
    if not plan:
        raise ValueError("export plan has no renderable clips with a source")

    music_path = music or _resolve_music(root)
    mat_dir = str(root / "_work")
    os.makedirs(mat_dir, exist_ok=True)

    rendered = renderer(plan, music_path, str(out_path), mat_dir)
    return {
        "ok": True,
        "out": str(rendered or out_path),
        "rendered_clips": len(plan),
        "source": prepared["source"],
        "music": music_path,
        "corrections": prepared["corrections"],
        "note": "rendered via canonical ffmpeg (mv_cut.render_mv); final.mp4 untouched",
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Hermes-native workbench export (opt-in ffmpeg render)")
    parser.add_argument("--artifact-root", required=True)
    parser.add_argument("--patch", help="timeline_patch.json to apply before export")
    parser.add_argument("--patched", help="an existing patched_draft_timeline.json to render")
    parser.add_argument("--music", help="override music path (defaults to music.wav in root)")
    parser.add_argument("--out", default=DEFAULT_OUT)
    args = parser.parse_args(argv)

    patch = _load_json(Path(args.patch)) if args.patch else None
    patched = _load_json(Path(args.patched)) if args.patched else None

    try:
        result = export(args.artifact_root, out=args.out, patch=patch, patched_timeline=patched, music=args.music)
    except ValueError as exc:
        print(f"[workbench_export] {exc}")
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
