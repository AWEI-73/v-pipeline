#!/usr/bin/env python3
"""Validate that a run folder is minimally usable by Dashboard and Workbench."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.dashboard_server import build_control_status, build_material_map_view
from video_pipeline_core.delivery_gate import evaluate_complete_video_delivery
from video_pipeline_core.project_workspace import validate_run_layout


REQUIRED_FILES = [
    "video_intent.json",
    "run_layout.json",
    "project_material_map.json",
    "reviewed_project_material_map.json",
    "material_delta.json",
    "segment_contract.json",
    "timeline.json",
    "timeline_build.json",
    "workbench_handoff.json",
    "workbench_review_report.json",
    "artifact_manifest.json",
    "verify_result.json",
    "final.mp4",
    "HONEST_REVIEW.md",
    "agent_interaction_log.md",
]


def validate_run_folder(root: Path, complete_video: bool = False) -> dict:
    root = root.resolve()
    errors = []
    warnings = []
    files = {}

    if not root.is_dir():
        return {
            "artifact_role": "pipeline_run_folder_validation",
            "ok": False,
            "root": str(root),
            "errors": [f"run folder does not exist: {root}"],
            "warnings": [],
        }

    for rel in REQUIRED_FILES:
        path = root / rel
        exists = path.exists()
        files[rel] = {
            "exists": exists,
            "size_bytes": path.stat().st_size if exists and path.is_file() else None,
        }
        if not exists:
            errors.append(f"missing required file: {rel}")
        elif path.is_file() and path.stat().st_size <= 0:
            errors.append(f"empty required file: {rel}")

    layout = validate_run_layout(root)
    if not layout.get("ok"):
        errors.append("run_layout validation failed")

    try:
        material_view = build_material_map_view(root)
    except Exception as exc:  # pragma: no cover - CLI guard
        errors.append(f"material map dashboard view failed: {exc}")
        material_view = None

    try:
        control = build_control_status(root)
    except Exception as exc:  # pragma: no cover - CLI guard
        errors.append(f"control status failed: {exc}")
        control = None

    if material_view:
        if not material_view.get("ready_for_build"):
            warnings.append("material view is not ready_for_build")
        if not material_view.get("stages"):
            errors.append("material view has no stages")
        if not material_view.get("intent"):
            errors.append("material view has no normalized intent summary")

    if control:
        draft_summary = ((control.get("workbench") or {}).get("draft_summary") or {})
        if not draft_summary.get("agent_ready"):
            warnings.append("workbench draft package is not agent_ready")

    final_path = root / "final.mp4"
    if final_path.is_file() and final_path.stat().st_size < 1024:
        warnings.append("final.mp4 exists but is very small")

    delivery_gate = None
    if complete_video:
        delivery_gate = evaluate_complete_video_delivery(root)
        if not delivery_gate.get("pass"):
            for item in delivery_gate.get("blocking") or []:
                errors.append(
                    "complete video delivery failed: "
                    f"{item.get('artifact')} / {item.get('rule')} - {item.get('message')}"
                )
        warnings.extend(delivery_gate.get("warnings") or [])

    if complete_video and warnings:
        errors.extend(f"complete video warning promoted to error: {warning}" for warning in warnings)
        warnings = []

    return {
        "artifact_role": "pipeline_run_folder_validation",
        "ok": not errors,
        "root": str(root),
        "errors": errors,
        "warnings": warnings,
        "files": files,
        "run_layout_ok": bool(layout.get("ok")),
        "material_view": {
            "video_type": material_view.get("video_type") if material_view else None,
            "route": material_view.get("route") if material_view else None,
            "ready_for_build": material_view.get("ready_for_build") if material_view else None,
            "stage_count": len(material_view.get("stages") or []) if material_view else 0,
        },
        "workbench_agent_ready": bool(
            (((control or {}).get("workbench") or {}).get("draft_summary") or {}).get("agent_ready")
        ),
        "complete_video_required": bool(complete_video),
        "complete_video_delivery_gate": delivery_gate,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_folder")
    parser.add_argument(
        "--complete-video",
        action="store_true",
        help="enforce final delivery requirements: audio, narration, music, subtitles, and media streams",
    )
    args = parser.parse_args()
    report = validate_run_folder(Path(args.run_folder), complete_video=args.complete_video)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
