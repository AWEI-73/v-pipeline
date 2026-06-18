#!/usr/bin/env python
"""Operator-flow blackbox acceptance for an existing run/artifact root.

This tool is intentionally a harness, not a new pipeline stage. It verifies that
an artifact root is complete enough for the material lifecycle and Workbench
handoff/rerender path, then writes a report. It never writes canonical
``final.mp4``.
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
import wave
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

_REPO_ROOT = str(Path(__file__).resolve().parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

try:
    from tools.workbench_draft_rerender import rerender_from_handoff
    from tools.workbench_handoff import build_handoff, validate_handoff
except ImportError:  # pragma: no cover - direct-script fallback
    from workbench_draft_rerender import rerender_from_handoff
    from workbench_handoff import build_handoff, validate_handoff

from video_pipeline_core import material_map_lifecycle
from video_pipeline_core.project_material_map import build_project_material_map

ARTIFACT_ROLE = "operator_flow_acceptance"
VERSION = 1
DEFAULT_REPORT = "operator_flow_acceptance.json"
DEFAULT_RERENDER = "operator_flow_rerender.mp4"
DEFAULT_RERENDER_REPORT = "operator_flow_rerender_report.json"
DEMO_NEED_ID = "nd_operator_demo"



def _load_json(path: Path) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _resolve_ffmpeg() -> Optional[str]:
    try:
        from video_pipeline_core.platform_tools import resolve_ffmpeg
        return resolve_ffmpeg()
    except Exception:
        return shutil.which("ffmpeg")


def _write_demo_video(path: Path, duration_sec: float = 2.0) -> None:
    ffmpeg = _resolve_ffmpeg()
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required to initialize the operator-flow demo package")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(path.stem + ".tmp" + path.suffix)
    if tmp_path.exists():
        tmp_path.unlink()
    cmd = [
        ffmpeg, "-y", "-f", "lavfi",
        "-i", f"testsrc2=size=320x180:rate=30:duration={duration_sec}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(tmp_path),
    ]
    try:
        proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                              text=True, timeout=180)
        if proc.returncode != 0 or not tmp_path.is_file() or tmp_path.stat().st_size <= 0:
            raise RuntimeError(f"failed to create demo video: {proc.stderr.strip()[:500]}")
        tmp_path.replace(path)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink()
        if path.exists() and path.stat().st_size <= 128:
            path.unlink()
        raise


def _write_demo_wav(path: Path, duration_sec: float = 2.0, sample_rate: int = 16000) -> None:
    frames = int(duration_sec * sample_rate)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        for i in range(frames):
            sample = int(12000 * math.sin(2 * math.pi * 440 * i / sample_rate))
            handle.writeframesraw(sample.to_bytes(2, byteorder="little", signed=True))


def _demo_needs() -> Dict[str, Any]:
    return {
        "artifact_role": "material_needs",
        "version": 1,
        "project": "operator-flow-demo",
        "needs": [{
            "need_id": DEMO_NEED_ID,
            "category": "training",
            "type": "video",
            "purpose": "show a concrete training visual for the operator-flow demo",
            "count": 1,
            "fallback_tier": 1,
            "must_have": True,
        }],
    }


def _demo_map(source: Path) -> Dict[str, Any]:
    return {
        "artifact_role": "material_map",
        "version": 1,
        "asset_id": "operator_demo_clip",
        "asset_type": "video",
        "source": str(source),
        "duration_sec": 2.0,
        "scenes": [{
            "start": 0.0,
            "end": 2.0,
            "caption": "operator flow demo training visual",
            "visual_family": "demo_training",
            "angle_scale": "wide",
            "satisfies": [{"need_id": DEMO_NEED_ID, "status": "accepted"}],
        }],
        "speech": [],
    }


def _demo_segment(num: int) -> Dict[str, Any]:
    return {
        "segment": num,
        "core": {
            "section_role": "montage",
            "story_purpose": f"operator-flow demo segment {num}",
            "timeline_source": "beat",
        },
        "material_fit": {
            "visual_desc": "operator flow demo training visual",
            "reason": "accepted demo material satisfies the material need",
            "need_refs": [DEMO_NEED_ID],
        },
        "audio": {"role": "music", "reason": "demo music bed"},
        "visual_style": {
            "layout": "full_frame",
            "pace": "steady",
            "reason": "simple demo frame for backend flow verification",
        },
        "text_layer": {"mode": "subtitle", "text": f"Demo segment {num}"},
    }


def initialize_demo_package(artifact_root: str) -> Dict[str, Any]:
    """Create a deterministic, complete Node0-13 demo package.

    The package is intentionally tiny but real: it has material needs, a
    material map, a material DB, a valid contract, a valid WAV, Workbench draft
    artifacts, and a handoff. It never creates canonical ``final.mp4``.
    """
    root = Path(artifact_root)
    root.mkdir(parents=True, exist_ok=True)
    source = root / "operator_demo_clip.mp4"
    _write_demo_video(source)
    music = root / "music.wav"
    _write_demo_wav(music)

    needs = _demo_needs()
    material_map = _demo_map(source)
    contract = {
        "style": "mv",
        "music": {"brief": "operator-flow demo music"},
        "material_needs_ref": "material_needs.json",
        "segments": [_demo_segment(1), _demo_segment(2)],
    }
    timeline_plan = [
        {
            "slot_index": 0,
            "segment": 1,
            "source": str(source),
            "slot_dur": 1.0,
            "extract_start": 0.0,
            "extract_dur": 1.0,
            "scene_id": "operator_demo_clip:0",
            "caption": "operator flow demo training visual",
        },
        {
            "slot_index": 1,
            "segment": 2,
            "source": str(source),
            "slot_dur": 1.0,
            "extract_start": 0.0,
            "extract_dur": 1.0,
            "scene_id": "operator_demo_clip:0",
            "caption": "operator flow demo training visual",
        },
    ]

    _write_json(root / "node0_brief.json", {
        "artifact_role": "operator_flow_demo_brief",
        "version": 1,
        "goal": "prove backend Node0-13 artifact flow can complete on a tiny generic package",
    })
    _write_json(root / "material_needs.json", needs)
    _write_json(root / "operator_demo_clip.map.json", material_map)
    _write_json(root / "materials_db.json", {
        "files": [{"path": str(source), "material_map": "operator_demo_clip.map.json"}],
    })
    _write_json(root / "project_material_map.json", build_project_material_map([material_map], needs=needs))
    _write_json(root / "segment_contract.json", contract)
    _write_json(root / "timeline.json", {"artifact_role": "timeline", "plan": timeline_plan})
    _write_json(root / "patched_draft_timeline.json", {
        "artifact_role": "patched_draft_timeline",
        "plan": timeline_plan,
    })
    _write_json(root / "workbench_review_report.json", {
        "artifact_role": "workbench_review_report",
        "ok": True,
        "note": "demo package starts with a draft identical to the canonical timeline",
    })
    _write_json(root / "workbench_handoff.json", build_handoff(str(root)))
    return {
        "ok": True,
        "artifact_root": str(root),
        "created": [
            "node0_brief.json",
            "material_needs.json",
            "operator_demo_clip.map.json",
            "materials_db.json",
            "project_material_map.json",
            "segment_contract.json",
            "timeline.json",
            "patched_draft_timeline.json",
            "workbench_review_report.json",
            "workbench_handoff.json",
            "music.wav",
        ],
    }


def _project_map_has_satisfies(project_map: Any) -> bool:
    if not isinstance(project_map, dict):
        return False
    for asset in project_map.get("assets") or []:
        if not isinstance(asset, dict):
            continue
        for scene in asset.get("scenes") or []:
            if isinstance(scene, dict) and scene.get("satisfies"):
                return True
    return False


def _base_report(root: Path) -> Dict[str, Any]:
    return {
        "artifact_role": ARTIFACT_ROLE,
        "version": VERSION,
        "ok": False,
        "stage": "started",
        "artifact_root": str(root),
        "errors": [],
        "warnings": [],
        "material_lifecycle": None,
        "workbench_handoff_validation": None,
        "workbench_rerender": None,
        "demo_package_initialized": False,
        "canonical_changed": False,
    }


def _fail(report: Dict[str, Any], report_path: Path, stage: str, code: str, message: str) -> Dict[str, Any]:
    report["ok"] = False
    report["stage"] = stage
    report["errors"].append({"code": code, "message": message})
    _write_json(report_path, report)
    return report


def _material_lifecycle(root: Path) -> Dict[str, Any]:
    out_dir = root / "operator_material_lifecycle"
    kwargs: Dict[str, Any] = {"out_dir": out_dir}
    needs = root / "material_needs.json"
    project_map = root / "project_material_map.json"
    material_db = root / "materials_db.json"
    contract = root / "segment_contract.json"
    decisions = root / "revision_decisions.json"
    if needs.is_file():
        kwargs["needs_ref"] = str(needs)
    if material_db.is_file():
        kwargs["material_db_ref"] = str(material_db)
    elif project_map.is_file():
        kwargs["project_map_ref"] = str(project_map)
    if contract.is_file():
        kwargs["contract_ref"] = str(contract)
    if decisions.is_file():
        kwargs["decisions_ref"] = str(decisions)
    result = material_map_lifecycle.run_lifecycle(**kwargs)
    _write_json(out_dir / "material_map_lifecycle.json", result)
    return result


def run_operator_flow_acceptance(
    artifact_root: str,
    *,
    report_out: Optional[str] = None,
    rerender_out: str = DEFAULT_RERENDER,
    rerender_report_out: str = DEFAULT_RERENDER_REPORT,
    renderer: Callable = None,
    render_effects: bool = False,
    init_demo_package: bool = False,
    require_build_ready: bool = False,
) -> Dict[str, Any]:
    """Run bounded operator-flow acceptance over an artifact root."""
    root = Path(artifact_root)
    if init_demo_package:
        initialize_demo_package(str(root))
    report_path = Path(report_out) if report_out else root / DEFAULT_REPORT
    report = _base_report(root)
    report["demo_package_initialized"] = bool(init_demo_package)

    if not root.exists() or not root.is_dir():
        return _fail(report, report_path, "incomplete_replay_package", "missing_artifact_root",
                     f"artifact root does not exist or is not a directory: {root}")

    project_map_path = root / "project_material_map.json"
    needs_path = root / "material_needs.json"
    project_map = _load_json(project_map_path) if project_map_path.is_file() else None
    if _project_map_has_satisfies(project_map) and not needs_path.is_file():
        return _fail(
            report,
            report_path,
            "incomplete_replay_package",
            "missing_material_needs",
            "project_material_map.json has satisfies edges, but material_needs.json is missing",
        )

    lifecycle = _material_lifecycle(root)
    report["material_lifecycle"] = {
        "exit": "ok" if lifecycle.get("stage") != "invalid" else "invalid",
        "stage": lifecycle.get("stage"),
        "can_build": lifecycle.get("can_build"),
        "next_action": lifecycle.get("next_action"),
        "blocking": lifecycle.get("blocking") or [],
    }
    if lifecycle.get("stage") == "invalid":
        return _fail(
            report,
            report_path,
            "material_lifecycle_invalid",
            "material_lifecycle_invalid",
            "; ".join(lifecycle.get("blocking") or ["material-map lifecycle invalid"]),
        )
    if require_build_ready and lifecycle.get("stage") != "build_ready":
        return _fail(
            report,
            report_path,
            "material_lifecycle_not_build_ready",
            "material_lifecycle_not_build_ready",
            f"material lifecycle stage is {lifecycle.get('stage')!r}, expected 'build_ready'",
        )

    _write_json(root / "workbench_handoff.json", build_handoff(str(root)))
    validation = validate_handoff(str(root))
    report["workbench_handoff_validation"] = validation
    if not validation.get("ok"):
        return _fail(
            report,
            report_path,
            "workbench_handoff_invalid",
            "workbench_handoff_invalid",
            f"workbench handoff has {len(validation.get('errors') or [])} error(s)",
        )

    rerender_kwargs: Dict[str, Any] = {
        "out": rerender_out,
        "report_out": rerender_report_out,
        "render_effects": render_effects,
    }
    if renderer is not None:
        rerender_kwargs["renderer"] = renderer
    rerender = rerender_from_handoff(str(root), **rerender_kwargs)
    report["workbench_rerender"] = rerender
    report["ok"] = True
    report["stage"] = "passed"
    _write_json(report_path, report)
    return report


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run bounded operator-flow acceptance over an artifact root")
    parser.add_argument("artifact_root")
    parser.add_argument("--out", default=DEFAULT_REPORT, help="operator_flow_acceptance.json output")
    parser.add_argument("--rerender-out", default=DEFAULT_RERENDER)
    parser.add_argument("--rerender-report-out", default=DEFAULT_RERENDER_REPORT)
    parser.add_argument("--effects", action="store_true")
    parser.add_argument("--init-demo-package", action="store_true",
                        help="initialize a deterministic complete demo package under artifact_root before validating")
    parser.add_argument("--require-build-ready", action="store_true",
                        help="fail unless material-map lifecycle reaches build_ready")
    args = parser.parse_args(argv)

    report = run_operator_flow_acceptance(
        args.artifact_root,
        report_out=args.out,
        rerender_out=args.rerender_out,
        rerender_report_out=args.rerender_report_out,
        render_effects=args.effects,
        init_demo_package=args.init_demo_package,
        require_build_ready=args.require_build_ready,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
