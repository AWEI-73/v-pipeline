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
import shutil
import subprocess
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
    from tools import effect_patch as ep
except ImportError:  # pragma: no cover - direct-script fallback
    import timeline_patch as tp
    import effect_patch as ep

# Canonical outputs the export must never produce/overwrite.
PROTECTED_OUTPUTS = set(tp.PROTECTED_OUTPUTS)
DEFAULT_OUT = "workbench_export.mp4"
RENDERABLE_EFFECT_PRESETS = {"flash", "title_reveal", "caption_emphasis"}


def _load_json(path: Path) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _default_renderer(plan, music_path, out_path, mat_dir=None):  # pragma: no cover - thin ffmpeg shim
    from video_pipeline_core.mv_cut import render_mv  # lazy: only when truly rendering
    return render_mv(plan, music_path, out_path, mat_dir=mat_dir)


def _resolve_ffmpeg() -> str:
    try:  # pragma: no cover - depends on local bundled runtime
        from video_pipeline_core.platform_tools import resolve_ffmpeg
        return resolve_ffmpeg()
    except Exception:
        return shutil.which("ffmpeg") or "ffmpeg"


def _effect_window(effect: Dict[str, Any]) -> Optional[Dict[str, float]]:
    try:
        start = float(effect.get("start_sec", 0.0))
        dur = float(effect.get("duration_sec", 0.0))
    except (TypeError, ValueError):
        return None
    if not (start >= 0 and dur > 0):
        return None
    return {"start": start, "end": start + dur}


def resolve_renderable_effects(
    artifact_root: str,
    effect_patch: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Return validated workbench effects that this export renderer can realize.

    The workbench may carry richer effect intents for later Node 14 / manual
    work. EF3 intentionally renders only simple ffmpeg-safe overlay flashes, and
    reports the rest as skipped instead of pretending they were applied.
    """
    root = Path(artifact_root)
    patch = effect_patch
    if patch is None:
        patch_path = root / "effect_patch.json"
        if not patch_path.is_file():
            return {"renderable": [], "skipped": [], "diagnostics": ["no effect_patch.json"]}
        try:
            patch = json.loads(patch_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ValueError(f"invalid effect_patch.json: {exc}") from exc

    applied = ep.apply_effect_patch(artifact_root, patch)
    renderable: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    for effect in applied.get("effects", []):
        preset = effect.get("preset")
        window = _effect_window(effect)
        if preset in RENDERABLE_EFFECT_PRESETS and window is not None:
            e = dict(effect)
            e["_render_window"] = window
            renderable.append(e)
        else:
            skipped.append(dict(effect))
    return {
        "renderable": renderable,
        "skipped": skipped,
        "diagnostics": applied.get("diagnostics", []),
    }


def _drawbox_filter(effect: Dict[str, Any]) -> str:
    window = effect["_render_window"]
    try:
        intensity = float(effect.get("intensity", 1.0))
    except (TypeError, ValueError):
        intensity = 1.0
    alpha = max(0.08, min(0.60, 0.12 * intensity))
    start = window["start"]
    end = window["end"]
    enable = f"between(t\\,{start:.3f}\\,{end:.3f})"
    return f"drawbox=x=0:y=0:w=iw:h=ih:color=white@{alpha:.3f}:t=fill:enable='{enable}'"


def apply_effects_to_video(
    artifact_root: str,
    input_video: str,
    output_video: str,
    *,
    ffmpeg: Optional[str] = None,
    effect_patch: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Apply supported workbench effect intents to an exported video.

    This is an official *workbench export* renderer path, not a canonical BUILD
    output. It writes only ``output_video`` and leaves final.mp4 untouched.
    """
    resolved = resolve_renderable_effects(artifact_root, effect_patch=effect_patch)
    renderable = resolved["renderable"]
    skipped = resolved["skipped"]
    output_path = Path(output_video)
    input_path = Path(input_video)
    if not renderable:
        if input_path.resolve() != output_path.resolve():
            output_path.write_bytes(input_path.read_bytes())
        return {
            "ok": True,
            "out": str(output_path),
            "applied_count": 0,
            "skipped_count": len(skipped),
            "supported_presets": sorted(RENDERABLE_EFFECT_PRESETS),
        }

    ffmpeg_bin = ffmpeg or _resolve_ffmpeg()
    filters = ",".join(_drawbox_filter(effect) for effect in renderable)
    same_path = input_path.resolve() == output_path.resolve()
    tmp_path = output_path.with_suffix(output_path.suffix + ".effects.tmp.mp4") if same_path else output_path
    if tmp_path.exists():
        tmp_path.unlink()
    cmd = [
        ffmpeg_bin, "-y", "-i", str(input_path),
        "-vf", filters,
        "-map", "0:v:0", "-map", "0:a?",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "copy",
        "-movflags", "+faststart", str(tmp_path),
    ]
    proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0 or not tmp_path.is_file():
        raise RuntimeError(f"effect render failed: {proc.stderr.strip()[:500]}")
    if same_path:
        os.replace(tmp_path, output_path)
    return {
        "ok": True,
        "out": str(output_path),
        "applied_count": len(renderable),
        "skipped_count": len(skipped),
        "supported_presets": sorted(RENDERABLE_EFFECT_PRESETS),
        "effects": [{"effect_id": e.get("effect_id"), "preset": e.get("preset")} for e in renderable],
    }


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
    render_effects: bool = False,
    effect_renderer: Callable = apply_effects_to_video,
    effect_patch: Optional[Dict[str, Any]] = None,
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
    result = {
        "ok": True,
        "out": str(rendered or out_path),
        "rendered_clips": len(plan),
        "source": prepared["source"],
        "music": music_path,
        "corrections": prepared["corrections"],
        "note": "rendered via canonical ffmpeg (mv_cut.render_mv); final.mp4 untouched",
    }
    if render_effects:
        if effect_patch is not None:
            effect_result = effect_renderer(
                artifact_root, str(rendered or out_path), str(out_path),
                effect_patch=effect_patch)
        else:
            effect_result = effect_renderer(artifact_root, str(rendered or out_path), str(out_path))
        result["out"] = effect_result.get("out", str(out_path))
        result["effect_render"] = effect_result
    return result


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Hermes-native workbench export (opt-in ffmpeg render)")
    parser.add_argument("--artifact-root", required=True)
    parser.add_argument("--patch", help="timeline_patch.json to apply before export")
    parser.add_argument("--patched", help="an existing patched_draft_timeline.json to render")
    parser.add_argument("--music", help="override music path (defaults to music.wav in root)")
    parser.add_argument("--out", default=DEFAULT_OUT)
    parser.add_argument("--effects", action="store_true", help="apply supported effect_patch.json overlays")
    args = parser.parse_args(argv)

    patch = _load_json(Path(args.patch)) if args.patch else None
    patched = _load_json(Path(args.patched)) if args.patched else None

    try:
        result = export(args.artifact_root, out=args.out, patch=patch, patched_timeline=patched,
                        music=args.music, render_effects=args.effects)
    except ValueError as exc:
        print(f"[workbench_export] {exc}")
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
