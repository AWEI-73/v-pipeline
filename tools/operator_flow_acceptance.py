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
import sys
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

ARTIFACT_ROLE = "operator_flow_acceptance"
VERSION = 1
DEFAULT_REPORT = "operator_flow_acceptance.json"
DEFAULT_RERENDER = "operator_flow_rerender.mp4"
DEFAULT_RERENDER_REPORT = "operator_flow_rerender_report.json"


def _load_json(path: Path) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


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
) -> Dict[str, Any]:
    """Run bounded operator-flow acceptance over an artifact root."""
    root = Path(artifact_root)
    report_path = Path(report_out) if report_out else root / DEFAULT_REPORT
    report = _base_report(root)

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
    args = parser.parse_args(argv)

    report = run_operator_flow_acceptance(
        args.artifact_root,
        report_out=args.out,
        rerender_out=args.rerender_out,
        rerender_report_out=args.rerender_report_out,
        render_effects=args.effects,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
