from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


API_ENDPOINTS: list[dict[str, Any]] = [
    {
        "method": "GET",
        "path": "/",
        "owner_branch": "main-pipeline",
        "mode": "read_only",
        "allowed_writes": [],
        "forbidden_writes": ["timeline.json", "segment_contract.json", "final.mp4"],
        "response_shape": "html",
        "next_action": None,
        "source": "tools/dashboard_server.py",
        "notes": "SPA index page"
    },
    {
        "method": "GET",
        "path": "/dashboard",
        "owner_branch": "main-pipeline",
        "mode": "read_only",
        "allowed_writes": [],
        "forbidden_writes": ["timeline.json", "segment_contract.json", "final.mp4"],
        "response_shape": "html",
        "next_action": None,
        "source": "tools/dashboard_server.py",
        "notes": "SPA dashboard route"
    },
    {
        "method": "GET",
        "path": "/workbench",
        "owner_branch": "workbench-brownfield",
        "mode": "read_only",
        "allowed_writes": [],
        "forbidden_writes": ["timeline.json", "segment_contract.json", "final.mp4"],
        "response_shape": "html",
        "next_action": None,
        "source": "tools/dashboard_server.py",
        "notes": "SPA workbench route"
    },
    {
        "method": "GET",
        "path": "/api/artifacts",
        "owner_branch": "main-pipeline",
        "mode": "read_only",
        "allowed_writes": [],
        "forbidden_writes": ["timeline.json", "segment_contract.json", "final.mp4"],
        "response_shape": "raw_json",
        "next_action": None,
        "source": "tools/dashboard_server.py",
        "notes": "Retrieve aggregated artifact list and health statuses"
    },
    {
        "method": "GET",
        "path": "/api/projects",
        "owner_branch": "main-pipeline",
        "mode": "read_only",
        "allowed_writes": [],
        "forbidden_writes": ["timeline.json", "segment_contract.json", "final.mp4"],
        "response_shape": "raw_json",
        "next_action": None,
        "source": "tools/dashboard_server.py",
        "notes": "Scan workspace and list run project folders"
    },
    {
        "method": "GET",
        "path": "/api/material-map-view",
        "owner_branch": "material-map",
        "mode": "read_only",
        "allowed_writes": [],
        "forbidden_writes": ["timeline.json", "segment_contract.json", "final.mp4"],
        "response_shape": "raw_json",
        "next_action": None,
        "source": "tools/dashboard_server.py",
        "notes": "Get material mapping configuration details"
    },
    {
        "method": "GET",
        "path": "/api/available_materials",
        "owner_branch": "material-map",
        "mode": "read_only",
        "allowed_writes": [],
        "forbidden_writes": ["timeline.json", "segment_contract.json", "final.mp4"],
        "response_shape": "raw_json",
        "next_action": None,
        "source": "tools/dashboard_server.py",
        "notes": "Scans materials folder and returns list of source assets"
    },
    {
        "method": "GET",
        "path": "/api/control/status",
        "owner_branch": "main-pipeline",
        "mode": "read_only",
        "allowed_writes": [],
        "forbidden_writes": ["timeline.json", "segment_contract.json", "final.mp4"],
        "response_shape": "pipeline_result",
        "next_action": None,
        "source": "tools/dashboard_server.py",
        "notes": "Expose dashboard/workbench handoff readiness without mutating artifacts"
    },
    {
        "method": "GET",
        "path": "/api/control/workbench-health",
        "owner_branch": "workbench-brownfield",
        "mode": "read_only",
        "allowed_writes": [],
        "forbidden_writes": ["timeline.json", "segment_contract.json", "final.mp4"],
        "response_shape": "pipeline_result",
        "next_action": None,
        "source": "tools/dashboard_server.py",
        "notes": "Dashboard control proxy for Workbench health"
    },
    {
        "method": "POST",
        "path": "/api/control/promote",
        "owner_branch": "workbench-brownfield",
        "mode": "request_only",
        "allowed_writes": ["workbench_promotion_request.json"],
        "forbidden_writes": ["timeline.json", "segment_contract.json", "final.mp4"],
        "response_shape": "pipeline_result",
        "next_action": "review_workbench_route_back",
        "source": "tools/dashboard_server.py",
        "notes": "Write workbench promotion request for agent review. Direct mutation is forbidden."
    },
    {
        "method": "GET",
        "path": "/api/workbench/health",
        "owner_branch": "workbench-brownfield",
        "mode": "read_only",
        "allowed_writes": [],
        "forbidden_writes": ["timeline.json", "segment_contract.json", "final.mp4"],
        "response_shape": "raw_json",
        "next_action": None,
        "source": "tools/workbench_server.py",
        "notes": "Inspect workbench availability and check file structure"
    },
    {
        "method": "GET",
        "path": "/api/workbench/preview-timeline",
        "owner_branch": "workbench-brownfield",
        "mode": "read_only",
        "allowed_writes": [],
        "forbidden_writes": ["timeline.json", "segment_contract.json", "final.mp4"],
        "response_shape": "raw_json",
        "next_action": None,
        "source": "tools/workbench_server.py",
        "notes": "Compute temporary preview timeline details"
    },
    {
        "method": "GET",
        "path": "/api/workbench/thumbnails",
        "owner_branch": "workbench-brownfield",
        "mode": "derived_cache_write",
        "allowed_writes": ["workbench_thumbs/"],
        "forbidden_writes": ["timeline.json", "segment_contract.json", "final.mp4"],
        "response_shape": "raw_json",
        "next_action": None,
        "source": "tools/workbench_server.py",
        "notes": "Build/cache derived thumbnail JPEGs for editor preview only"
    },
    {
        "method": "GET",
        "path": "/api/workbench/proxies",
        "owner_branch": "workbench-brownfield",
        "mode": "derived_cache_write",
        "allowed_writes": ["workbench_proxy/"],
        "forbidden_writes": ["timeline.json", "segment_contract.json", "final.mp4"],
        "response_shape": "raw_json",
        "next_action": None,
        "source": "tools/workbench_server.py",
        "notes": "Build/cache browser-friendly proxy clips for editor preview only"
    },
    {
        "method": "POST",
        "path": "/api/workbench/patch",
        "owner_branch": "workbench-brownfield",
        "mode": "draft_write",
        "allowed_writes": ["timeline_patch.json", "patched_draft_timeline.json", "preview_timeline.json"],
        "forbidden_writes": ["timeline.json", "segment_contract.json", "final.mp4"],
        "response_shape": "pipeline_result",
        "next_action": "agent_decide_repair",
        "source": "tools/workbench_server.py",
        "notes": "Draft-only patch validation and timeline assembly"
    },
    {
        "method": "POST",
        "path": "/api/workbench/export",
        "owner_branch": "workbench-brownfield",
        "mode": "draft_write",
        "allowed_writes": ["workbench_export.mp4", "timeline_patch.json"],
        "forbidden_writes": ["timeline.json", "segment_contract.json", "final.mp4"],
        "response_shape": "pipeline_result",
        "next_action": None,
        "source": "tools/workbench_server.py",
        "notes": "Dry-run ffmpeg export for local previews"
    },
    {
        "method": "POST",
        "path": "/api/workbench/sync-contract",
        "owner_branch": "workbench-brownfield",
        "mode": "draft_write",
        "allowed_writes": ["workbench_contract_patch.json", "patched_draft_timeline.json"],
        "forbidden_writes": ["timeline.json", "segment_contract.json", "final.mp4"],
        "response_shape": "pipeline_result",
        "next_action": None,
        "source": "tools/workbench_server.py",
        "notes": "Aligns workbench timeline adjustments with contract draft suggestions"
    },
    {
        "method": "POST",
        "path": "/api/workbench/subtitle-patch",
        "owner_branch": "workbench-brownfield",
        "mode": "draft_write",
        "allowed_writes": ["subtitle_patch.json"],
        "forbidden_writes": ["timeline.json", "segment_contract.json", "final.mp4"],
        "response_shape": "pipeline_result",
        "next_action": None,
        "source": "tools/workbench_server.py",
        "notes": "Saves draft subtitle track revisions"
    },
    {
        "method": "POST",
        "path": "/api/workbench/audio-cue-patch",
        "owner_branch": "workbench-brownfield",
        "mode": "draft_write",
        "allowed_writes": ["audio_cue_patch.json"],
        "forbidden_writes": ["timeline.json", "segment_contract.json", "final.mp4"],
        "response_shape": "pipeline_result",
        "next_action": None,
        "source": "tools/workbench_server.py",
        "notes": "Saves draft audio cues/volume track revisions"
    },
    {
        "method": "POST",
        "path": "/api/workbench/effect-patch",
        "owner_branch": "workbench-brownfield",
        "mode": "draft_write",
        "allowed_writes": ["effect_patch.json"],
        "forbidden_writes": ["timeline.json", "segment_contract.json", "final.mp4"],
        "response_shape": "pipeline_result",
        "next_action": None,
        "source": "tools/workbench_server.py",
        "notes": "Saves draft visual effect track revisions"
    },
    {
        "method": "POST",
        "path": "/api/workbench/save-all",
        "owner_branch": "workbench-brownfield",
        "mode": "draft_write",
        "allowed_writes": [
            "timeline_patch.json",
            "subtitle_patch.json",
            "audio_cue_patch.json",
            "effect_patch.json",
            "patched_draft_timeline.json",
            "workbench_handoff.json"
        ],
        "forbidden_writes": ["timeline.json", "segment_contract.json", "final.mp4"],
        "response_shape": "pipeline_result",
        "next_action": None,
        "source": "tools/workbench_server.py",
        "notes": "Atomic draft save for all timeline and track edits"
    },
    {
        "method": "POST",
        "path": "/api/workbench/review-report",
        "owner_branch": "workbench-brownfield",
        "mode": "draft_write",
        "allowed_writes": ["workbench_review_report.json", "workbench_review_report.md"],
        "forbidden_writes": ["timeline.json", "segment_contract.json", "final.mp4"],
        "response_shape": "pipeline_result",
        "next_action": None,
        "source": "tools/workbench_server.py",
        "notes": "Generates temporary local review reports"
    }
]


def audit_api_surface(manifest: list[dict[str, Any]], branch_registry_path: Path) -> list[str]:
    errors: list[str] = []

    # Load branch registry
    if not branch_registry_path.exists():
        errors.append(f"Branch registry file not found at: {branch_registry_path}")
        return errors

    try:
        registry_data = json.loads(branch_registry_path.read_text(encoding="utf-8"))
        branches = registry_data.get("branches", [])
        valid_branch_ids = {b.get("branch_id") for b in branches if isinstance(b, dict)}
    except Exception as exc:
        errors.append(f"Failed to parse branch contract registry: {exc}")
        return errors

    for idx, endpoint in enumerate(manifest):
        path = endpoint.get("path")
        method = endpoint.get("method")
        identifier = f"{method} {path} (index {idx})"

        # 1. owner_branch check
        owner = endpoint.get("owner_branch")
        if not owner or not isinstance(owner, str) or not owner.strip():
            errors.append(f"{identifier}: missing owner_branch")
        elif owner not in valid_branch_ids:
            errors.append(f"{identifier}: owner_branch '{owner}' is not a valid branch ID in registry")

        # 2. allowed_writes for write endpoints
        mode = endpoint.get("mode")
        if mode in ("draft_write", "request_only", "canonical_write", "derived_cache_write"):
            writes = endpoint.get("allowed_writes")
            if not isinstance(writes, list) or not writes:
                errors.append(f"{identifier}: write endpoint mode '{mode}' must have allowed_writes list")

        # 3. canonical_write checks
        if mode == "canonical_write":
            notes = str(endpoint.get("notes") or "")
            if not notes or "canonical" not in notes.lower():
                errors.append(f"{identifier}: canonical_write endpoint must document notes containing 'canonical'")

        # 4. /api/control/promote checks
        if path == "/api/control/promote":
            if owner != "workbench-brownfield":
                errors.append(f"{identifier}: must be owned by workbench-brownfield, got {owner}")
            if mode != "request_only":
                errors.append(f"{identifier}: mode must be request_only, got {mode}")
            
            allowed = endpoint.get("allowed_writes") or []
            if allowed != ["workbench_promotion_request.json"]:
                errors.append(f"{identifier}: allowed_writes must be exactly ['workbench_promotion_request.json']")
            
            forbidden = endpoint.get("forbidden_writes") or []
            for essential in ("timeline.json", "segment_contract.json", "final.mp4"):
                if essential not in forbidden:
                    errors.append(f"{identifier}: forbidden_writes must contain {essential}")

        # 5. /api/workbench/patch checks
        if path == "/api/workbench/patch":
            if mode != "draft_write":
                errors.append(f"{identifier}: mode must be draft_write, got {mode}")
            
            forbidden = endpoint.get("forbidden_writes") or []
            for essential in ("timeline.json", "segment_contract.json", "final.mp4"):
                if essential not in forbidden:
                    errors.append(f"{identifier}: forbidden_writes must contain {essential}")

        # 6. Response shape business checks
        response_shape = endpoint.get("response_shape")
        if mode in ("draft_write", "request_only") and response_shape != "pipeline_result":
            errors.append(f"{identifier}: write endpoint must return response_shape 'pipeline_result', got '{response_shape}'")

        if mode == "derived_cache_write":
            forbidden = endpoint.get("forbidden_writes") or []
            for essential in ("timeline.json", "segment_contract.json", "final.mp4"):
                if essential not in forbidden:
                    errors.append(f"{identifier}: derived cache endpoint must forbid {essential}")
            allowed = endpoint.get("allowed_writes") or []
            if not all(str(item).endswith("/") for item in allowed):
                errors.append(f"{identifier}: derived cache allowed_writes should be directories ending with '/'")

    return errors


def analyze(branch_registry_path: Path) -> dict[str, Any]:
    errors = audit_api_surface(API_ENDPOINTS, branch_registry_path)
    return {
        "artifact_role": "api_surface_audit_report",
        "version": 1,
        "ok": not errors,
        "endpoint_count": len(API_ENDPOINTS),
        "errors": errors,
        "manifest": API_ENDPOINTS
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit Hermes API surface manifest.")
    parser.add_argument("--registry", default="docs/branch-contract-registry.json", help="Path to branch registry")
    parser.add_argument("--json", action="store_true", help="Write manifest JSON to stdout")
    parser.add_argument("--out", help="Write manifest JSON to this path")
    args = parser.parse_args(argv)

    if args.json:
        print(json.dumps(API_ENDPOINTS, ensure_ascii=False, indent=2))
        return 0

    if args.out:
        Path(args.out).write_text(
            json.dumps(API_ENDPOINTS, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8"
        )
        return 0

    report = analyze(Path(args.registry))
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if report["ok"]:
        print("API Surface Audit: OK")
        return 0
    else:
        print("API Surface Audit: FAILED", file=sys.stderr)
        for err in report["errors"]:
            print(f"  - {err}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
