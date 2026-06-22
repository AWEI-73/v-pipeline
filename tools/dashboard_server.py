#!/usr/bin/env python3
"""
Review Dashboard V1 Server
Lightweight HTTP server for viewing Hermes video pipeline artifacts.
"""

import argparse
import hashlib
import json
import os
import sys
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
from pathlib import Path
from typing import Any

try:
    from tools.workbench_server import WorkbenchHandler, WORKBENCH_DIR
except ImportError:  # pragma: no cover - direct-script fallback
    from workbench_server import WorkbenchHandler, WORKBENCH_DIR

# Files for Profile A (review_demo)
PROFILE_A_FILES = {
    "timeline": "timeline.json",
    "review_report": "review_report.json",
    "project_material_map": "project_material_map.json",
    "state": "state.json",
    "contact_sheet": "contact_sheet.jpg"
}

# Files for Profile B (verify_bundle)
PROFILE_B_FILES = {
    "delivery_gate": "delivery_gate.json",
    "timeline_invariants": "timeline_invariants.json",
    "caption_audit": "caption_audit.json",
    "broll_audit": "broll_audit.json",
    "black_frame_audit": "black_frame_audit.json",
    "verify_evidence_bundle": "verify_evidence_bundle.json",
    "contact_sheet": "contact_sheet.jpg",
    "overview_grid": "overview_grid.jpg"
}


def resolve_artifact_path(root_dir: Path, filename: str) -> Path:
    """Find a file in the root directory or common subdirectories (verify/, m5_verify_evidence/)."""
    direct_path = root_dir / filename
    if direct_path.exists():
        return direct_path
    
    subdirs = ["verify", "m5_verify_evidence", "verify_evidence"]
    for sd in subdirs:
        subdir_path = root_dir / sd / filename
        if subdir_path.exists():
            return subdir_path
            
    return direct_path


def detect_profile(root_dir: Path) -> str:
    """Detect the artifact profile based on existing files in root_dir."""
    has_review_report = resolve_artifact_path(root_dir, "review_report.json").exists()
    has_timeline = resolve_artifact_path(root_dir, "timeline.json").exists() or resolve_artifact_path(root_dir, "timeline_build.json").exists()
    has_verify_bundle = resolve_artifact_path(root_dir, "verify_evidence_bundle.json").exists()
    has_delivery_gate = resolve_artifact_path(root_dir, "delivery_gate.json").exists()

    if has_review_report and has_timeline:
        return "review_demo"
    elif has_verify_bundle or has_delivery_gate:
        return "verify_bundle"
    else:
        return "unknown"


PROJECT_RUN_SIGNAL_FILES = {
    "final_video": ("final.mp4",),
    "workbench_handoff": ("workbench_handoff.json",),
    "workbench_review": ("workbench_review_report.json",),
    "timeline": ("timeline.json", "timeline_build.json", "draft_timeline.json", "timeline.plan"),
    "video_intent": ("video_intent.json",),
    "material_map_reviewed": ("reviewed_project_material_map.json",),
    "material_delta": ("fresh_material_delta.json", "material_delta.json"),
    "material_map_raw": ("project_material_map.json",),
    "verify_bundle": ("verify_evidence_bundle.json", "delivery_gate.json"),
    "run_layout": ("run_layout.json",),
}

PROJECT_RUN_SIGNAL_SCORES = {
    "final_video": 500,
    "workbench_handoff": 120,
    "workbench_review": 80,
    "timeline": 70,
    "material_map_reviewed": 60,
    "material_delta": 45,
    "video_intent": 40,
    "verify_bundle": 35,
    "run_layout": 25,
    "material_map_raw": 10,
}

CURRENT_ROUTE_SIGNALS = {
    "workbench_handoff",
    "workbench_review",
    "video_intent",
    "material_map_reviewed",
    "material_delta",
    "run_layout",
}


def _run_has_file(run_path: Path, filenames: tuple[str, ...]) -> bool:
    for filename in filenames:
        if (run_path / filename).is_file():
            return True
        for subdir in ("verify", "m5_verify_evidence", "verify_evidence", "review", "artifacts"):
            if (run_path / subdir / filename).is_file():
                return True
    return False


def classify_project_run(run_path: Path) -> dict[str, Any]:
    """Return dashboard metadata for a run folder candidate."""
    resolved = run_path.resolve()
    signals = [
        signal
        for signal, filenames in PROJECT_RUN_SIGNAL_FILES.items()
        if _run_has_file(resolved, filenames)
    ]
    signal_set = set(signals)
    score = sum(PROJECT_RUN_SIGNAL_SCORES[signal] for signal in signals)

    has_material_map = bool(signal_set & {"material_map_reviewed", "material_delta", "material_map_raw"})
    usable = (
        "final_video" in signal_set
        or "workbench_handoff" in signal_set
        or "verify_bundle" in signal_set
        or ("timeline" in signal_set and has_material_map)
        or bool(signal_set & {"material_map_reviewed"}) and "material_delta" in signal_set
        or ("video_intent" in signal_set and bool(signal_set & {"material_map_reviewed", "material_delta"}))
    )

    if "final_video" in signal_set:
        reason = "已有成片，可檢視交付結果"
    elif "workbench_handoff" in signal_set:
        reason = "已有剪輯工作台交接檔，可繼續剪輯"
    elif "timeline" in signal_set and has_material_map:
        reason = "已有素材地圖與時間線，可接續審查或剪輯"
    elif "material_map_reviewed" in signal_set and "material_delta" in signal_set:
        reason = "已有素材地圖審查與缺口清單，可接續補強"
    elif "video_intent" in signal_set and bool(signal_set & {"material_map_reviewed", "material_delta"}):
        reason = "已有意圖與素材判讀，可接續路線"
    elif "verify_bundle" in signal_set:
        reason = "已有驗收證據，可檢視結果"
    else:
        reason = "產物不足，暫不列入主要案例"

    try:
        last_modified = max(
            [resolved.stat().st_mtime]
            + [path.stat().st_mtime for path in resolved.rglob("*") if path.is_file()]
        )
    except OSError:
        last_modified = 0.0

    return {
        "name": resolved.name,
        "path": str(resolved),
        "profile": detect_profile(resolved),
        "usable": usable,
        "score": score,
        "signals": signals,
        "reason": reason,
        "last_modified": last_modified,
    }


def scan_project_runs(candidate_roots: list[Path], max_depth: int = 4, limit: int = 80) -> list[dict[str, Any]]:
    """Scan candidate roots and return usable pipeline run folders first."""
    projects_by_path: dict[str, dict[str, Any]] = {}

    source_priorities = {Path(root).resolve(): len(candidate_roots) - index for index, root in enumerate(candidate_roots)}

    for candidate_root in candidate_roots:
        root = Path(candidate_root)
        if not root.is_dir():
            continue
        root_resolved = root.resolve()

        roots_to_check = [root]
        for current_root, dirs, _files in os.walk(root):
            current = Path(current_root)
            try:
                depth = len(current.relative_to(root).parts)
            except ValueError:
                depth = 0
            if depth >= max_depth:
                dirs.clear()
            if depth > 0:
                roots_to_check.append(current)

        for run_path in roots_to_check:
            project = classify_project_run(run_path)
            if not project["usable"]:
                continue
            if not (set(project["signals"]) & CURRENT_ROUTE_SIGNALS):
                continue
            project["source_priority"] = source_priorities.get(root_resolved, 0)
            projects_by_path[project["path"]] = project

    projects = list(projects_by_path.values())
    projects.sort(
        key=lambda project: (
            project.get("source_priority", 0),
            project["last_modified"],
            project["score"],
        ),
        reverse=True,
    )
    return projects[:limit]


def load_json_file(file_path: Path):
    """Load JSON from a file, returning errors gracefully if malformed or missing."""
    if not file_path.exists():
        return None
    try:
        content = file_path.read_text(encoding="utf-8")
        return json.loads(content)
    except json.JSONDecodeError as e:
        return {"error": f"Malformed JSON: {str(e)}"}
    except Exception as e:
        return {"error": f"Failed to read file: {str(e)}"}


WORKBENCH_DRAFT_ARTIFACTS = {
    "timeline_patch": "timeline_patch.json",
    "patched_draft_timeline": "patched_draft_timeline.json",
    "workbench_contract_patch": "workbench_contract_patch.json",
    "workbench_handoff": "workbench_handoff.json",
    "subtitle_patch": "subtitle_patch.json",
    "audio_cue_patch": "audio_cue_patch.json",
    "effect_patch": "effect_patch.json",
    "workbench_review_report": "workbench_review_report.json",
    "workbench_review_report_md": "workbench_review_report.md",
}


def _json_patch_op_count(path: Path) -> int:
    data = load_json_file(path)
    if not isinstance(data, dict):
        return 0
    patches = data.get("patches")
    if not isinstance(patches, list):
        return 0
    return len([p for p in patches if isinstance(p, dict)])


def collect_workbench_draft_status(root_dir: Path):
    """Return read-only status for draft artifacts produced by the Workbench."""
    artifacts = {}
    present_count = 0
    for key, filename in WORKBENCH_DRAFT_ARTIFACTS.items():
        path = root_dir / filename
        detail = {
            "filename": filename,
            "exists": False,
            "path": None,
            "size_bytes": 0,
            "sha256": None,
        }
        if path.is_file():
            data = path.read_bytes()
            detail.update({
                "exists": True,
                "path": filename,
                "size_bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            })
            present_count += 1
        artifacts[key] = detail

    summary = {
        "present_count": present_count,
        "timeline_edits": _json_patch_op_count(root_dir / "timeline_patch.json"),
        "contract_edits": _json_patch_op_count(root_dir / "workbench_contract_patch.json"),
        "subtitle_edits": _json_patch_op_count(root_dir / "subtitle_patch.json"),
        "audio_cues": _json_patch_op_count(root_dir / "audio_cue_patch.json"),
        "effect_intents": _json_patch_op_count(root_dir / "effect_patch.json"),
    }
    summary["has_handoff"] = artifacts["workbench_handoff"]["exists"]
    summary["has_review_report"] = artifacts["workbench_review_report"]["exists"]
    if summary["has_handoff"]:
        from tools.workbench_handoff import validate_handoff
        validation = validate_handoff(str(root_dir))
        summary["handoff_validation"] = {
            "ok": bool(validation.get("ok")),
            "error_count": len(validation.get("errors") or []),
            "warning_count": len(validation.get("warnings") or []),
            "errors": validation.get("errors") or [],
            "warnings": validation.get("warnings") or [],
        }
    else:
        summary["handoff_validation"] = {
            "ok": None,
            "status": "not_present",
            "error_count": 0,
            "warning_count": 0,
            "errors": [],
            "warnings": [],
        }
    summary["agent_ready"] = (
        summary["has_handoff"]
        and summary["has_review_report"]
        and bool(summary["handoff_validation"].get("ok"))
    )
    return artifacts, summary


def collect_run_layout_status(root_dir: Path):
    """Return a small read-only summary of run_layout.json for frontend routing."""
    path = root_dir / "run_layout.json"
    if not path.is_file():
        return {
            "exists": False,
            "path": None,
        }

    payload = load_json_file(path)
    base = {
        "exists": True,
        "path": "run_layout.json",
    }
    if not isinstance(payload, dict):
        return {**base, "error": "run_layout.json must be a JSON object"}
    if payload.get("error"):
        return {**base, "error": payload["error"]}

    from video_pipeline_core.project_workspace import validate_run_layout
    validation = validate_run_layout(root_dir)

    return {
        **base,
        "artifact_role": payload.get("artifact_role"),
        "version": payload.get("version"),
        "folders": payload.get("folders") if isinstance(payload.get("folders"), dict) else {},
        "artifact_classes": (
            payload.get("artifact_classes")
            if isinstance(payload.get("artifact_classes"), dict)
            else {}
        ),
        "policy": payload.get("policy") if isinstance(payload.get("policy"), dict) else {},
        "validation": {
            "ok": bool(validation.get("ok")),
            "error_count": len(validation.get("errors") or []),
            "warning_count": len(validation.get("warnings") or []),
            "errors": validation.get("errors") or [],
            "warnings": validation.get("warnings") or [],
        },
    }


def scan_available_projects():
    """Scan `.tmp` and `C:/Users/user/Desktop/video_project` to list all valid runs."""
    projects = []

    # 1. Add default temp folders if they exist
    default_runs = [
        ("預設展示 (srp_real67_review_demo)", Path(".tmp/srp_real67_review_demo")),
        ("67 期完整回放 (srp_real67_fuller_replay)", Path(".tmp/srp_real67_fuller_replay")),
        ("預設驗收 (srp_acceptance)", Path(".tmp/srp_acceptance")),
    ]
    for name, run_path in default_runs:
        if run_path.is_dir():
            projects.append({
                "name": name,
                "path": str(run_path.resolve())
            })

    # 2. Scan C:/Users/user/Desktop/video_project
    vp_dir = Path("C:/Users/user/Desktop/video_project")
    if vp_dir.is_dir():
        # Search for state.json files up to 4 sublevels deep
        for root, dirs, files in os.walk(str(vp_dir)):
            # Limit depth to avoid walking forever
            depth = len(Path(root).relative_to(vp_dir).parts)
            if depth > 4:
                dirs.clear()  # Don't go deeper
                continue
            
            if "state.json" in files or "verify_evidence_bundle.json" in files or "delivery_gate.json" in files:
                parent_path = Path(root).resolve()
                # Skip duplicate entries
                if any(p["path"] == str(parent_path) for p in projects):
                    continue
                
                rel = parent_path.relative_to(vp_dir)
                projects.append({
                    "name": f"專案: {rel}",
                    "path": str(parent_path)
                })
    
    return projects


def scan_available_projects():
    """Scan known workspace roots and list usable pipeline run folders."""
    return scan_project_runs([
        Path(".tmp"),
    ], max_depth=1)


def parse_srt(srt_content: str):
    import re
    cues = []
    # Split by double newline (or similar) to parse blocks
    blocks = re.split(r'\n\s*\n', srt_content.strip())
    for block in blocks:
        lines = [l.strip() for l in block.split('\n') if l.strip()]
        if len(lines) >= 3:
            # First line is index, second line is timestamps, third+ is text
            time_match = re.match(r'(\d+:\d+:\d+,\d+)\s*-->\s*(\d+:\d+:\d+,\d+)', lines[1])
            if time_match:
                start_str, end_str = time_match.groups()
                def to_secs(t_str):
                    parts = t_str.replace(',', '.').split(':')
                    return float(parts[0])*3600 + float(parts[1])*60 + float(parts[2])
                try:
                    start_sec = to_secs(start_str)
                    end_sec = to_secs(end_str)
                    text = " ".join(lines[2:])
                    cues.append({
                        "start_sec": start_sec,
                        "end_sec": end_sec,
                        "text": text
                    })
                except Exception:
                    pass
    return cues


def _timeline_slots_for_summary(active_root: Path):
    """Return normalized minimal timeline slots for the control status API."""
    timeline_data = None
    for filename in ("timeline.plan", "timeline.json", "timeline_build.json"):
        loaded = load_json_file(resolve_artifact_path(active_root, filename))
        if loaded:
            timeline_data = loaded
            break

    plan_list = []
    if isinstance(timeline_data, list):
        plan_list = timeline_data
    elif isinstance(timeline_data, dict):
        for key in ("plan", "clips", "slots"):
            if isinstance(timeline_data.get(key), list):
                plan_list = timeline_data[key]
                break

    slots = []
    accumulated = 0.0
    for idx, raw_slot in enumerate(plan_list):
        if not isinstance(raw_slot, dict):
            continue
        duration = raw_slot.get("duration_sec") or raw_slot.get("extract_dur") or raw_slot.get("target_duration_sec") or raw_slot.get("duration") or 0.0
        try:
            duration = float(duration)
        except (TypeError, ValueError):
            duration = 0.0
        start = raw_slot.get("start_sec") or raw_slot.get("start")
        try:
            start = float(start) if start is not None else accumulated
        except (TypeError, ValueError):
            start = accumulated
        end = raw_slot.get("end_sec") or raw_slot.get("end")
        try:
            end = float(end) if end is not None else start + duration
        except (TypeError, ValueError):
            end = start + duration
        accumulated = end
        slots.append({
            "slot_index": raw_slot.get("slot_index", idx),
            "start_sec": start,
            "end_sec": end,
            "duration_sec": max(0.0, duration),
            "window_quality_fallback": bool(raw_slot.get("window_quality_fallback")),
        })
    return slots


def build_control_status(active_root: Path):
    """Small frontend manifest shared by the SPA dashboard shell."""
    slots = _timeline_slots_for_summary(active_root)
    duration = max([s["end_sec"] for s in slots], default=0.0)
    final_path = resolve_artifact_path(active_root, "final.mp4")
    drafts, summary = collect_workbench_draft_status(active_root)
    run_layout = collect_run_layout_status(active_root)
    agent_ready = bool(summary.get("agent_ready"))
    final_exists = final_path.is_file()

    if agent_ready:
        next_action = "review_workbench_drafts"
    elif not final_exists:
        next_action = "run_pipeline_or_open_dashboard"
    else:
        next_action = "open_dashboard_or_workbench"

    return {
        "artifact_role": "frontend_control_status",
        "version": 1,
        "artifact_root": str(active_root.resolve()),
        "dashboard": {
            "url": "/dashboard",
            "mode": "read_only_review",
        },
        "workbench": {
            "url": "/workbench",
            "health_url": "/api/workbench/health",
            "mode": "write_limited_draft_editor",
            "command": (
                f"python tools/dashboard_server.py --artifact-root "
                f"\"{active_root.resolve()}\" --port 8765"
            ),
            "draft_artifacts": drafts,
            "draft_summary": summary,
        },
        "run_layout": run_layout,
        "final_video": {
            "exists": final_exists,
            "path": "final.mp4" if final_exists else None,
        },
        "timeline": {
            "slot_count": len(slots),
            "duration_sec": duration,
            "quality_fallback_slots": sum(
                1 for slot in slots if slot.get("window_quality_fallback")),
        },
        "recommended_next_action": next_action,
    }


def _first_existing_artifact(root_dir: Path, names):
    for name in names:
        path = resolve_artifact_path(root_dir, name)
        if path.exists():
            return name, path, load_json_file(path)
    return names[0], resolve_artifact_path(root_dir, names[0]), None


def _safe_list(value):
    return value if isinstance(value, list) else []


def _count_satisfaction_edges(assets, status):
    count = 0
    for asset in assets:
        for scene in _safe_list(asset.get("scenes")):
            for item in _safe_list(scene.get("satisfies")):
                if item.get("status") == status:
                    count += 1
    return count


def build_material_map_view(active_root: Path):
    intent = load_json_file(resolve_artifact_path(active_root, "video_intent.json"))
    if not isinstance(intent, dict):
        intent = {}

    map_name, map_path, material_map = _first_existing_artifact(active_root, [
        "project_material_map.json",
        "reviewed_project_material_map.json",
    ])
    if not isinstance(material_map, dict):
        material_map = {}

    delta_name, delta_path, material_delta = _first_existing_artifact(active_root, [
        "material_delta.json",
        "fresh_material_delta.json",
    ])
    if not isinstance(material_delta, dict):
        material_delta = {}

    delta_by_need = {
        item.get("need_id"): item
        for item in _safe_list(material_delta.get("deltas"))
        if isinstance(item, dict) and item.get("need_id")
    }

    assets = []
    scene_count = 0
    for asset in _safe_list(material_map.get("assets")):
        if not isinstance(asset, dict):
            continue
        scenes = []
        for index, scene in enumerate(_safe_list(asset.get("scenes"))):
            if not isinstance(scene, dict):
                continue
            satisfies = [
                item for item in _safe_list(scene.get("satisfies"))
                if isinstance(item, dict)
            ]
            need_ids = [
                item.get("need_id") for item in satisfies
                if item.get("need_id")
            ]
            statuses = [
                item.get("status") for item in satisfies
                if item.get("status")
            ]
            scenes.append({
                "scene_index": index,
                "caption": scene.get("caption") or "",
                "start": scene.get("start"),
                "end": scene.get("end"),
                "visual_family": scene.get("visual_family"),
                "angle_scale": scene.get("angle_scale"),
                "action_family": scene.get("action_family"),
                "subject": scene.get("subject"),
                "quality_score": scene.get("quality_score"),
                "source_type": scene.get("source_type"),
                "need_ids": need_ids,
                "statuses": statuses,
            })
            scene_count += 1
        assets.append({
            "asset_id": asset.get("asset_id") or Path(str(asset.get("source") or "")).stem or "unnamed_asset",
            "asset_type": asset.get("asset_type") or "unknown",
            "source": asset.get("source"),
            "duration_sec": asset.get("duration_sec"),
            "scene_count": len(scenes),
            "scenes": scenes,
        })

    needs = []
    for need in _safe_list(material_map.get("needs")):
        if not isinstance(need, dict):
            continue
        delta = delta_by_need.get(need.get("need_id"), {})
        evidence = delta.get("evidence") if isinstance(delta.get("evidence"), dict) else {}
        needs.append({
            "need_id": need.get("need_id"),
            "purpose": need.get("purpose") or need.get("category") or "",
            "count": need.get("count"),
            "must_have": bool(need.get("must_have")),
            "fallback_options": _safe_list(need.get("fallback_options")),
            "outcome": delta.get("outcome") or "unknown",
            "route": delta.get("route"),
            "reason": delta.get("reason"),
            "accepted": evidence.get("accepted", 0),
            "candidate": evidence.get("candidate", 0),
            "rejected": evidence.get("rejected", 0),
        })

    def first_present(names):
        for name in names:
            path = active_root / name
            if path.exists():
                return name, path
            resolved = resolve_artifact_path(active_root, name)
            if resolved.exists():
                return name, resolved
        return names[0], active_root / names[0]

    def stage(label, names, *, ready=False):
        artifact, path = first_present(names)
        if ready:
            status = "ready"
        elif path.exists():
            status = "present"
        else:
            status = "missing"
        return {
            "label": label,
            "artifact": artifact,
            "status": status,
        }

    stages = [
        stage("Intent", ["video_intent.json", "project_brief.json"]),
        stage("Material Ingest", [
            "media",
            "materials",
            "materials/raw",
            "generated_real_imagegen",
            "generated_materials",
            "real_provider_packet",
        ]),
        stage("Material Map", [map_name, "reviewed_project_material_map.json", "project_material_map.json"]),
        stage("Coverage Delta", [delta_name, "material_delta.json", "fresh_material_delta.json"]),
        stage("Structure", [
            "story_blueprint",
            "story_blueprint/screenplay_beats.json",
            "material_needs.json",
            "assembly_plan.json",
            "project_brief.json",
        ]),
        stage("Contract", ["segment_contract.json", "revised_segment_contract.json"]),
        stage("Timeline", ["timeline.json", "timeline_build.json", "preview_timeline.json"]),
        stage("Review Gates", [
            "reviewer_aggregation.json",
            "review_report.json",
            "workbench_review_report.json",
            "editor_review.json",
            "spec_review.json",
            "supply_review.json",
        ]),
        stage("Verify", [
            "verify_evidence_bundle.json",
            "delivery_gate.json",
            "verify_result.json",
            "contact_sheet.jpg",
        ]),
    ]

    return {
        "artifact_role": "material_map_dashboard_view",
        "version": 1,
        "artifact_root": str(active_root.resolve()),
        "entry_path": intent.get("entry_path") or "unknown",
        "route": intent.get("route") or "unknown",
        "video_type": intent.get("video_type") or "unknown",
        "audience": intent.get("audience") or "unknown",
        "intent": {
            "artifact_role": intent.get("artifact_role") or "video_intent",
            "version": intent.get("version"),
            "video_type": intent.get("video_type") or "unknown",
            "audience": intent.get("audience") or "unknown",
            "goal": intent.get("goal") or "",
            "material_availability": intent.get("material_availability") or "unknown",
            "text_availability": intent.get("text_availability") or "unknown",
            "input_state": intent.get("input_state") or "unknown",
            "entry_path": intent.get("entry_path") or "unknown",
            "route": intent.get("route") or "unknown",
            "gap_strategy": intent.get("gap_strategy") or "unknown",
            "required_followup_questions": _safe_list(intent.get("required_followup_questions")),
            "assumptions": _safe_list(intent.get("assumptions")),
            "handoff_to": intent.get("handoff_to") or "unknown",
            "expected_outputs": _safe_list(intent.get("expected_outputs")),
        },
        "ready_for_build": bool(material_delta.get("ready_for_build")),
        "stats": {
            "assets": len(assets),
            "scenes": scene_count,
            "needs": len(needs),
            "accepted_edges": _count_satisfaction_edges(_safe_list(material_map.get("assets")), "accepted"),
            "candidate_edges": _count_satisfaction_edges(_safe_list(material_map.get("assets")), "candidate"),
            "rejected_edges": _count_satisfaction_edges(_safe_list(material_map.get("assets")), "rejected"),
        },
        "delta_summary": material_delta.get("summary") if isinstance(material_delta.get("summary"), dict) else {},
        "stages": stages,
        "assets": assets,
        "needs": needs,
    }


class DashboardHandler(WorkbenchHandler):
    artifact_root: Path = Path(".")
    dashboard_dir: Path = Path(".")

    def log_message(self, format, *args):
        pass

    def sync_workbench_context(self, active_root: Path):
        self.artifact_root = active_root
        host = self.headers.get("Host")
        if host:
            self.base_url = f"http://{host}"

    def send_error_response(self, status_code, message):
        self.send_response(status_code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(message.encode("utf-8"))










    def get_validated_root(self, query_params) -> Path:
        """Extract and validate the root path from query parameters, fallback to Referer, and then default."""
        root_val = query_params.get("root", [None])[0]
        if not root_val:
            # Fallback to Referer header
            referer = self.headers.get("Referer")
            if referer:
                try:
                    parsed_ref = urllib.parse.urlparse(referer)
                    ref_query = urllib.parse.parse_qs(parsed_ref.query)
                    root_val = ref_query.get("root", [None])[0]
                except Exception:
                    pass

        if not root_val:
            return self.artifact_root

        candidate_root = Path(root_val).resolve()
        
        # Security Boundary Check: must reside within C:/Users/user/Desktop/video_project
        # or the workspace's .tmp directory, or the current workspace root.
        allowed_roots = [
            Path("C:/Users/user/Desktop/video_project").resolve(),
            Path(".tmp").resolve(),
            Path(".").resolve()
        ]
        
        is_allowed = False
        for allowed in allowed_roots:
            if allowed in candidate_root.parents or candidate_root == allowed:
                is_allowed = True
                break

        if not is_allowed or not candidate_root.is_dir():
            return self.artifact_root
            
        return candidate_root

    def _send_json(self, code: int, payload: Any) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def serve_file(self, file_path: Path, content_type: str):
        """Helper to serve a local file, supporting range requests for video playback."""
        if not file_path.is_file():
            self.send_error_response(404, "File Not Found")
            return

        file_size = file_path.stat().st_size
        range_header = self.headers.get("Range")

        if range_header and range_header.startswith("bytes="):
            try:
                ranges = range_header.replace("bytes=", "").split("-")
                start = int(ranges[0])
                end = int(ranges[1]) if ranges[1] else file_size - 1
                if start >= file_size or end >= file_size or start > end:
                    raise ValueError("Range out of bounds")
            except Exception:
                self.send_error_response(416, "Requested Range Not Satisfiable")
                return

            length = end - start + 1
            self.send_response(206)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
            self.send_header("Content-Length", str(length))
            self.send_header("Accept-Ranges", "bytes")
            self.end_headers()

            try:
                with open(file_path, "rb") as f:
                    f.seek(start)
                    remaining = length
                    while remaining > 0:
                        chunk_size = min(remaining, 64 * 1024)
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        remaining -= len(chunk)
            except Exception:
                pass
        else:
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(file_size))
            self.send_header("Accept-Ranges", "bytes")
            self.end_headers()
            try:
                with open(file_path, "rb") as f:
                    while True:
                        chunk = f.read(64 * 1024)
                        if not chunk:
                            break
                        self.wfile.write(chunk)
            except Exception:
                pass

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path_str = parsed_url.path
        query_params = urllib.parse.parse_qs(parsed_url.query)

        # Formal SPA routes. The SPA router chooses the active view from path.
        if path_str in ("/", "/index.html", "/dashboard", "/dashboard/", "/material-map", "/material-map/", "/workbench", "/workbench/"):
            html_path = self.dashboard_dir / "index.html"
            if not html_path.exists():
                html_path = self.dashboard_dir / "dashboard_v1.html"
            self.serve_file(html_path, "text/html; charset=utf-8")
            return
        # Serve 3D whiteboard dashboard
        if path_str in ("/3d", "/3d/", "/dashboard3d"):
            html_path = self.dashboard_dir / "material_map_canvas_3d.html"
            self.serve_file(html_path, "text/html; charset=utf-8")
            return
        # Serve Physics whiteboard dashboard
        if path_str in ("/physics", "/physics/", "/dashboard-physics"):
            html_path = self.dashboard_dir / "material_map_canvas_physics.html"
            self.serve_file(html_path, "text/html; charset=utf-8")
            return

        if path_str in ("/dashboard/legacy", "/dashboard/legacy/"):
            html_path = self.dashboard_dir / "dashboard_v1.html"
            self.serve_file(html_path, "text/html; charset=utf-8")
            return

        if path_str.startswith("/src/"):
            rel = path_str[len("/src/"):]
            if not rel or "\\" in rel or rel.startswith(".") or ".." in rel.split("/"):
                self.send_error_response(403, "Access Denied")
                return
            file_path = self.dashboard_dir / "src" / rel
            suffix = file_path.suffix.lower()
            content_type = {
                ".js": "application/javascript; charset=utf-8",
                ".css": "text/css; charset=utf-8",
                ".json": "application/json; charset=utf-8",
            }.get(suffix, "application/octet-stream")
            self.serve_file(file_path, content_type)
            return

        if path_str.startswith("/workbench-native/"):
            rel = path_str[len("/workbench-native/"):]
            if not rel or "/" in rel or "\\" in rel or rel.startswith("."):
                self.send_error_response(403, "Access Denied")
                return
            suffix = Path(rel).suffix.lower()
            content_type = {
                ".html": "text/html; charset=utf-8",
                ".css": "text/css; charset=utf-8",
                ".js": "application/javascript; charset=utf-8",
            }.get(suffix, "application/octet-stream")
            self.serve_file(WORKBENCH_DIR / rel, content_type)
            return

        if path_str.startswith("/workbench/"):
            rel = path_str[len("/workbench/"):]
            if not rel or "/" in rel or "\\" in rel or rel.startswith("."):
                self.send_error_response(403, "Access Denied")
                return
            suffix = Path(rel).suffix.lower()
            content_type = {
                ".html": "text/html; charset=utf-8",
                ".css": "text/css; charset=utf-8",
                ".js": "application/javascript; charset=utf-8",
            }.get(suffix, "application/octet-stream")
            self.serve_file(WORKBENCH_DIR / rel, content_type)
            return

        if path_str == "/media" or path_str.startswith("/api/workbench/"):
            active_root = self.get_validated_root(query_params)
            self.sync_workbench_context(active_root)
            WorkbenchHandler.do_GET(self)
            return

        # Legacy static dashboard assets
        if path_str == "/index.css":
            css_path = self.dashboard_dir / "index.css"
            self.serve_file(css_path, "text/css; charset=utf-8")
            return

        if path_str == "/index.js":
            js_path = self.dashboard_dir / "index.js"
            self.serve_file(js_path, "application/javascript; charset=utf-8")
            return

        if path_str == "/dashboard_v1.css":
            css_path = self.dashboard_dir / "dashboard_v1.css"
            self.serve_file(css_path, "text/css; charset=utf-8")
            return

        if path_str == "/dashboard_v1.js":
            js_path = self.dashboard_dir / "dashboard_v1.js"
            self.serve_file(js_path, "application/javascript; charset=utf-8")
            return

        if path_str == "/dashboard_v1.html":
            html_path = self.dashboard_dir / "dashboard_v1.html"
            self.serve_file(html_path, "text/html; charset=utf-8")
            return

        if path_str == "/material_map_review.css":
            css_path = self.dashboard_dir / "material_map_review.css"
            self.serve_file(css_path, "text/css; charset=utf-8")
            return

        if path_str == "/material_map_review.js":
            js_path = self.dashboard_dir / "material_map_review.js"
            self.serve_file(js_path, "application/javascript; charset=utf-8")
            return

        # Route /api/projects -> list scanned folders containing runs
        if path_str == "/api/projects":
            projects = scan_available_projects()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(projects, ensure_ascii=False, indent=2).encode("utf-8"))
            return

        if path_str == "/api/control/status":
            active_root = self.get_validated_root(query_params)
            payload = build_control_status(active_root)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"))
            return
        if path_str == "/api/control/workbench-health":
            active_root = self.get_validated_root(query_params)
            payload = {
                "ok": True,
                "status": "ok",
                "url": "/api/workbench/health",
                "payload": {
                    "artifact_role": "workbench_health",
                    "version": 1,
                    "status": "ok",
                    "artifact_root": str(active_root.resolve()),
                    "can_preview": any((active_root / name).is_file() for name in ("draft_timeline.json", "timeline.json", "timeline.plan")),
                    "write_limited": True,
                },
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"))
            return

        if path_str == "/api/material-map-view":
            active_root = self.get_validated_root(query_params)
            self._send_json(200, build_material_map_view(active_root))
            return

        # Route /api/artifacts -> aggregate JSON data
        if path_str == "/api/artifacts":
            active_root = self.get_validated_root(query_params)
            profile = detect_profile(active_root)
            artifact_errors = []

            # 1. Resolve Media URLs
            final_mp4_resolved = resolve_artifact_path(active_root, "final.mp4")
            if final_mp4_resolved.exists():
                rel_path = final_mp4_resolved.relative_to(active_root).as_posix()
                final_video_url = f"/static/{rel_path}?root={urllib.parse.quote(str(active_root))}"
            else:
                final_video_url = None

            contact_sheet_resolved = resolve_artifact_path(active_root, "contact_sheet.jpg")
            if contact_sheet_resolved.exists():
                rel_path = contact_sheet_resolved.relative_to(active_root).as_posix()
                contact_sheet_url = f"/static/{rel_path}?root={urllib.parse.quote(str(active_root))}"
            else:
                contact_sheet_url = None

            # Helper to load optional JSON and log error if malformed
            def load_optional_json(filename):
                p = resolve_artifact_path(active_root, filename)
                if p.exists() and p.is_file():
                    try:
                        return json.loads(p.read_text(encoding="utf-8"))
                    except Exception as e:
                        err_msg = f"Malformed JSON: {str(e)}"
                        artifact_errors.append({
                            "file": filename,
                            "error": err_msg
                        })
                        return {"error": err_msg}
                return None

            # Load Raw files
            timeline_data = load_optional_json("timeline.plan")
            if not timeline_data:
                timeline_data = load_optional_json("timeline.json")
            if not timeline_data:
                timeline_data = load_optional_json("timeline_build.json")

            review_report = load_optional_json("review_report.json")
            delivery_gate = load_optional_json("delivery_gate.json")
            state = load_optional_json("state.json")
            black_frame_audit = load_optional_json("black_frame_audit.json")
            broll_audit = load_optional_json("broll_audit.json")
            caption_audit = load_optional_json("caption_audit.json")
            verify_evidence_bundle = load_optional_json("verify_evidence_bundle.json")

            # Extract timeline slots list
            plan_list = []
            if timeline_data:
                if isinstance(timeline_data, list):
                    plan_list = timeline_data
                elif isinstance(timeline_data, dict):
                    if "plan" in timeline_data and isinstance(timeline_data["plan"], list):
                        plan_list = timeline_data["plan"]
                    elif "clips" in timeline_data and isinstance(timeline_data["clips"], list):
                        plan_list = timeline_data["clips"]
                    elif "slots" in timeline_data and isinstance(timeline_data["slots"], list):
                        plan_list = timeline_data["slots"]

            # 2. Normalize timeline_slots
            timeline_slots = []
            accumulated_time = 0.0
            for idx, raw_slot in enumerate(plan_list):
                slot = dict(raw_slot)
                if "slot_index" not in slot:
                    slot["slot_index"] = idx

                duration = slot.get("duration_sec") or slot.get("extract_dur") or slot.get("target_duration_sec") or slot.get("duration") or 0.0
                try:
                    duration = float(duration)
                except (ValueError, TypeError):
                    duration = 0.0

                start = slot.get("start_sec") or slot.get("start")
                if start is None:
                    start = accumulated_time
                else:
                    try:
                        start = float(start)
                    except (ValueError, TypeError):
                        start = accumulated_time

                end = slot.get("end_sec") or slot.get("end")
                if end is None:
                    end = start + duration
                else:
                    try:
                        end = float(end)
                    except (ValueError, TypeError):
                        end = start + duration

                slot["start_sec"] = start
                slot["duration_sec"] = duration
                slot["end_sec"] = end
                accumulated_time = end
                timeline_slots.append(slot)

            # 3. Read semantic_alignment
            semantic_alignment = None
            if review_report and isinstance(review_report, dict):
                semantic_alignment = review_report.get("semantic_alignment")

            # 4. Map Segment & Slot status
            seg_status_map = {}
            if isinstance(semantic_alignment, list):
                for align in semantic_alignment:
                    seg_id = align.get("segment") or align.get("segment_id")
                    status = align.get("status")
                    if seg_id is not None:
                        seg_status_map[str(seg_id)] = status
            elif isinstance(semantic_alignment, dict):
                for seg_id, align in semantic_alignment.items():
                    if isinstance(align, dict):
                        status = align.get("status")
                    else:
                        status = align
                    seg_status_map[str(seg_id)] = status

            # Collect failed slots
            failed_slots = set()
            if review_report and isinstance(review_report, dict):
                src = review_report.get("slot_render_check")
                if isinstance(src, dict) and "failed_slots" in src:
                    for s in src["failed_slots"]:
                        failed_slots.add(int(s))
            verify_result = load_optional_json("verify_result.json")
            if verify_result and isinstance(verify_result, dict):
                src = verify_result.get("slot_render_check")
                if isinstance(src, dict) and "failed_slots" in src:
                    for s in src["failed_slots"]:
                        failed_slots.add(int(s))

            for slot in timeline_slots:
                slot_idx = slot.get("slot_index")
                seg_id = slot.get("segment") or slot.get("segment_id")
                status = slot.get("status") or "matched"

                if seg_id is not None:
                    align_status = seg_status_map.get(str(seg_id))
                    if align_status in ["drift", "wrong_need", "gap"]:
                        status = align_status
                    elif align_status:
                        status = align_status

                if slot_idx is not None and int(slot_idx) in failed_slots:
                    status = "render_failed"

                slot["status"] = status

            # 5. Load subtitles
            subtitles = []
            srt_path = resolve_artifact_path(active_root, "review_subtitles.srt")
            if not srt_path.exists():
                srt_path = resolve_artifact_path(active_root, "subtitles.srt")
            if srt_path.exists():
                try:
                    subtitles = parse_srt(srt_path.read_text(encoding="utf-8"))
                except Exception as e:
                    artifact_errors.append({
                        "file": srt_path.name,
                        "error": f"Failed to parse SRT: {str(e)}"
                    })

            # 6. Extract Issues
            issues = []
            if isinstance(semantic_alignment, list):
                for align in semantic_alignment:
                    status = align.get("status")
                    if status in ["drift", "wrong_need", "gap"]:
                        issues.append({
                            "type": "semantic",
                            "severity": "error",
                            "segment": align.get("segment") or align.get("segment_id"),
                            "message": f"Segment {align.get('segment')}: Semantic {status} - {align.get('reason') or 'unmatched'}"
                        })
            elif isinstance(semantic_alignment, dict):
                for seg_id, align in semantic_alignment.items():
                    if isinstance(align, dict):
                        status = align.get("status")
                        reason = align.get("reason") or align.get("message") or "unmatched"
                    else:
                        status = align
                        reason = "unmatched"
                    if status in ["drift", "wrong_need", "gap"]:
                        issues.append({
                            "type": "semantic",
                            "severity": "error",
                            "segment": seg_id,
                            "message": f"Segment {seg_id}: Semantic {status} - {reason}"
                        })

            for f_slot in failed_slots:
                seg_num = None
                for slot in timeline_slots:
                    if slot.get("slot_index") == f_slot:
                        seg_num = slot.get("segment") or slot.get("segment_id")
                        break
                issues.append({
                    "type": "render",
                    "severity": "warning",
                    "slot_index": f_slot,
                    "segment": seg_num,
                    "message": f"Slot {f_slot} (Seg {seg_num or 'N/A'}): Render check failed (black frame or low visual quality)"
                })

            if review_report and isinstance(review_report, dict):
                gaps = review_report.get("material_gaps") or review_report.get("gaps")
                if isinstance(gaps, list):
                    for gap in gaps:
                        issues.append({
                            "type": "material_gap",
                            "severity": "error",
                            "message": str(gap)
                        })
                elif isinstance(gaps, dict):
                    for k, v in gaps.items():
                        issues.append({
                            "type": "material_gap",
                            "severity": "error",
                            "message": f"Gap in {k}: {v}"
                        })




            # Read review markdown if available
            review_report_md = None
            review_md_path = resolve_artifact_path(active_root, "review_report.md")
            if review_md_path.exists():
                try:
                    review_report_md = review_md_path.read_text(encoding="utf-8")
                except Exception:
                    pass

            workbench_draft_artifacts, workbench_draft_summary = collect_workbench_draft_status(active_root)
            run_layout = collect_run_layout_status(active_root)

            aggregated = {
                "profile": profile,
                "artifact_root": str(active_root.resolve()),
                "run_layout": run_layout,
                "workbench": {
                    "mode": "merged_dashboard_server",
                    "url": "/workbench",
                    "command": (
                        f"python tools/dashboard_server.py --artifact-root "
                        f"\"{active_root.resolve()}\" --port 8765"
                    ),
                    "note": "Workbench is merged into the Dashboard server under write-limited draft APIs.",
                    "draft_artifacts": workbench_draft_artifacts,
                    "draft_summary": workbench_draft_summary,
                },
                "final_video_url": final_video_url,
                "contact_sheet_url": contact_sheet_url,
                "timeline_slots": timeline_slots,
                "issues": issues,
                "semantic_alignment": semantic_alignment,
                "subtitles": subtitles,
                "artifact_errors": artifact_errors,
                "raw_paths": {
                    "timeline": str(resolve_artifact_path(active_root, "timeline.json").resolve()) if resolve_artifact_path(active_root, "timeline.json").exists() else None,
                    "review_report": str(resolve_artifact_path(active_root, "review_report.json").resolve()) if resolve_artifact_path(active_root, "review_report.json").exists() else None,
                    "state": str(resolve_artifact_path(active_root, "state.json").resolve()) if resolve_artifact_path(active_root, "state.json").exists() else None,
                },
                # Raw/original fields for compatibility
                "timeline": timeline_data,
                "review_report": review_report,
                "delivery_gate": delivery_gate,
                "state": state,
                "black_frame_audit": black_frame_audit,
                "broll_audit": broll_audit,
                "caption_audit": caption_audit,
                "verify_evidence_bundle": verify_evidence_bundle,
                "review_report_md": review_report_md
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(aggregated, ensure_ascii=False, indent=2).encode("utf-8"))
            return

        # Route /static/<path> -> serve static artifacts under artifact_root securely
        if path_str.startswith("/static/"):
            active_root = self.get_validated_root(query_params)
            
            relative_subpath = path_str[8:]
            relative_subpath = urllib.parse.unquote(relative_subpath)

            if not relative_subpath or relative_subpath.startswith("/") or relative_subpath.startswith("\\"):
                self.send_error_response(403, "Access Denied")
                return

            try:
                resolved_root = active_root.resolve()
                candidate_path = (resolved_root / relative_subpath).resolve()
            except Exception:
                self.send_error_response(400, "Invalid Path")
                return

            # Path Traversal Check
            if resolved_root not in candidate_path.parents and candidate_path != resolved_root:
                self.send_error_response(403, "Access Denied")
                return

            ext = candidate_path.suffix.lower()
            mime_types = {
                ".mp4": "video/mp4",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".svg": "image/svg+xml",
                ".srt": "text/plain; charset=utf-8",
                ".json": "application/json; charset=utf-8",
                ".md": "text/markdown; charset=utf-8"
            }
            content_type = mime_types.get(ext, "application/octet-stream")

            self.serve_file(candidate_path, content_type)
            return

        # Route /api/available_materials -> list files in materials/ and map
        if path_str == "/api/available_materials":
            active_root = self.get_validated_root(query_params)
            materials = []
            seen_paths = set()

            # 1. Scan active_root / materials
            materials_dir = active_root / "materials"
            if materials_dir.is_dir():
                for root, _, files in os.walk(str(materials_dir)):
                    for f in files:
                        ext = Path(f).suffix.lower()
                        path_obj = Path(root) / f
                        abs_path = str(path_obj.resolve())
                        if abs_path in seen_paths:
                            continue
                        
                        m_type = "unknown"
                        if ext in [".mp4", ".mov", ".webm"]:
                            m_type = "video"
                        elif ext in [".png", ".jpg", ".jpeg", ".gif"]:
                            m_type = "image"
                        elif ext in [".mp3", ".wav", ".m4a", ".ogg"]:
                            m_type = "audio"
                        else:
                            continue

                        materials.append({
                            "name": f,
                            "path": abs_path,
                            "type": m_type
                        })
                        seen_paths.add(abs_path)

            # 2. Scan project_material_map.json
            pmap_path = resolve_artifact_path(active_root, "project_material_map.json")
            if pmap_path.exists() and pmap_path.is_file():
                pmap = load_json_file(pmap_path)
                if pmap and isinstance(pmap, dict) and "assets" in pmap:
                    for asset in pmap["assets"]:
                        source = asset.get("source")
                        if source:
                            path_obj = Path(source)
                            abs_path = str(path_obj.resolve()) if path_obj.is_absolute() else str((active_root / source).resolve())
                            if abs_path in seen_paths:
                                continue

                            ext = path_obj.suffix.lower()
                            m_type = asset.get("asset_type") or "video"
                            if not m_type:
                                if ext in [".mp3", ".wav"]:
                                    m_type = "audio"
                                elif ext in [".png", ".jpg", ".jpeg"]:
                                    m_type = "image"
                                else:
                                    m_type = "video"

                            materials.append({
                                "name": path_obj.name,
                                "path": abs_path,
                                "type": m_type
                            })
                            seen_paths.add(abs_path)

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(materials, ensure_ascii=False, indent=2).encode("utf-8"))
            return

        self.send_error_response(404, "Not Found")
    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        if parsed_url.path.startswith("/api/workbench/"):
            query_params = urllib.parse.parse_qs(parsed_url.query)
            active_root = self.get_validated_root(query_params)
            self.sync_workbench_context(active_root)
            WorkbenchHandler.do_POST(self)
            return
        self.send_error_response(
            405,
            "Review Dashboard is read-only. Write-back endpoints are disabled."
        )

def run_server(artifact_root: str, port: int):
    resolved_root = Path(artifact_root).resolve()
    if not resolved_root.is_dir():
        print(f"Error: Artifact root '{artifact_root}' is not a directory.", file=sys.stderr)
        sys.exit(1)

    script_dir = Path(__file__).resolve().parent
    dashboard_dir = script_dir.parent / "dashboard"

    print(f"Starting Hermes Review Dashboard Server V1...")
    print(f"Artifact Root : {resolved_root}")
    print(f"Dashboard Dir : {dashboard_dir}")
    print(f"Port          : {port}")
    print(f"Detected Profile: {detect_profile(resolved_root)}")
    print(f"Access URL    : http://localhost:{port}")

    class BoundDashboardHandler(DashboardHandler):
        artifact_root = resolved_root
        dashboard_dir = script_dir.parent / "dashboard"
        base_url = f"http://localhost:{port}"

    server = ThreadingHTTPServer(("localhost", port), BoundDashboardHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hermes Review Dashboard V1 Server")
    parser.add_argument("--artifact-root", required=True, help="Path to project output artifacts directory")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the server on (default: 8000)")
    args = parser.parse_args()

    run_server(args.artifact_root, args.port)
