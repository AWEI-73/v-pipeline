"""Deterministic material-first source-folder probe orchestration."""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from tools.material_first_boundary_acceptance import run_material_first_boundary_acceptance
from tools.material_first_landing_case import _scan_source_materials

from .asset_paths import build_asset_path_audit
from .material_rough_cut import write_json


EDITED_VIDEO_MARKERS = (
    "final",
    "master",
    "export",
    "render",
    "reference",
    "ref",
    "v01",
    "v02",
    "剪輯",
    "參考",
    "完成",
    "成片",
)


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="surrogateescape")).hexdigest()


def _source_metadata(source_dir: Path) -> dict[str, Any]:
    return {
        "source_kind": "external_path",
        "basename": source_dir.name,
        "source_path_hash": _hash_text(str(source_dir.resolve())),
    }


def _safe_reset_probe_dir(path: Path) -> None:
    resolved = path.resolve()
    if resolved.exists():
        parts = {part.lower() for part in resolved.parts}
        if ".tmp" not in parts:
            raise ValueError(f"refusing to reset non-.tmp probe directory: {resolved}")
        shutil.rmtree(resolved)
    resolved.mkdir(parents=True, exist_ok=True)


def _probe_wall_verdict(db: dict[str, Any]) -> dict[str, Any]:
    roles = [
        ("opening", "probe opening visual"),
        ("training", "probe training/practice visual"),
        ("closing", "probe closing/completion visual"),
    ]
    assets = []
    for index, entry in enumerate(db.get("files") or []):
        asset_id = entry.get("id")
        if index < len(roles):
            role, evidence = roles[index]
            assets.append({
                "asset_id": asset_id,
                "coarse_status": "keep",
                "visual_role": [role],
                "quality": "probe_only",
                "usable_ranges": [{"start": 0.0, "end": 4.0}],
                "visual_evidence": [evidence],
            })
        else:
            assets.append({
                "asset_id": asset_id,
                "coarse_status": "reject",
                "quality": "probe_only",
                "why_not_selected": "bounded source intake probe keeps one asset per required role",
            })
    return {
        "artifact_role": "material_wall_review_verdict",
        "version": 1,
        "reviewer": "material_first_real_source_probe:deterministic_fixture",
        "decision_scope": "probe_only_not_human_final_review",
        "assets": assets,
    }


def _asset_examples(items: list[dict[str, Any]], *, limit: int = 5) -> list[dict[str, Any]]:
    examples = []
    for item in items[:limit]:
        path = Path(item.get("path") or "")
        examples.append({
            "asset_id": item.get("id") or item.get("asset_id"),
            "basename": path.name,
            "source_path_hash": _hash_text(str(path)),
            "reason": item.get("reason") or item.get("coarse_status"),
        })
    return examples


def _count_supported_files(source_dir: Path) -> tuple[int, int]:
    from tools.material_first_landing_case import MEDIA_EXTS

    file_count = 0
    supported_count = 0
    for path in source_dir.rglob("*"):
        if not path.is_file():
            continue
        file_count += 1
        if path.suffix.lower() in MEDIA_EXTS:
            supported_count += 1
    return file_count, supported_count


def _edited_video_like_count(source_dir: Path) -> int:
    from tools.material_first_landing_case import VIDEO_EXTS

    count = 0
    for path in source_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in VIDEO_EXTS:
            continue
        text = "/".join(path.parts).lower()
        if any(marker.lower() in text for marker in EDITED_VIDEO_MARKERS):
            count += 1
    return count


def build_material_first_real_source_probe(
    source_dir: str | Path,
    out_dir: str | Path,
    *,
    max_assets: int = 12,
) -> dict[str, Any]:
    """Run a bounded source-folder probe through boundary acceptance.

    The generated wall verdict is intentionally marked as probe-only. It exists
    to test intake mechanics and path discipline, not to replace human review.
    """

    source = Path(source_dir).resolve()
    if not source.is_dir():
        raise FileNotFoundError(f"material source folder does not exist: {source}")

    probe_dir = Path(out_dir).resolve()
    _safe_reset_probe_dir(probe_dir)
    run_dir = probe_dir / "run"
    scan_db = _scan_source_materials(source, max_assets=max_assets)
    write_json(probe_dir / "source_scan_summary.json", {
        "artifact_role": "material_first_source_scan_summary",
        "version": 1,
        "source": _source_metadata(source),
        "selected_count": len(scan_db.get("files") or []),
        "corrupt_or_unreadable_count": len(scan_db.get("rejects") or []),
        "skipped_count": len(scan_db.get("skipped") or []),
        "selected_examples": _asset_examples(scan_db.get("files") or []),
        "rejected_examples": _asset_examples(scan_db.get("rejects") or []),
    })

    verdict = _probe_wall_verdict(scan_db)
    verdict_path = probe_dir / "material_wall_review_verdict.probe.json"
    write_json(verdict_path, verdict)

    boundary_result: dict[str, Any] | None = None
    boundary_ok = False
    blocking: list[dict[str, Any]] = []
    if len(scan_db.get("files") or []) >= 3:
        boundary_result = run_material_first_boundary_acceptance(
            run_dir,
            source_dir=source,
            wall_verdict=verdict_path,
            max_assets=max_assets,
        )
        boundary_ok = bool(boundary_result.get("ok"))
        blocking = (boundary_result.get("report") or {}).get("stages") or []
    else:
        blocking = [{
            "rule": "material_source_insufficient",
            "message": "source folder probe requires at least 3 usable media files",
        }]

    intake_report_path = run_dir / "material_first_source_intake_report.json"
    intake_report = {}
    if intake_report_path.is_file():
        intake_report = json.loads(intake_report_path.read_text(encoding="utf-8-sig"))
    audit = build_asset_path_audit(run_dir, strict=True) if run_dir.exists() else {
        "ok": False,
        "strict": True,
        "strict_finding_count": None,
    }
    file_count, supported_count = _count_supported_files(source)

    copied_assets = intake_report.get("copied_assets") or []
    report = {
        "artifact_role": "material_first_real_source_probe_report",
        "version": 1,
        "route": "material-first",
        "probe_scope": "source_intake_to_project_asset_store_boundary",
        "ok": bool(boundary_ok and audit.get("ok")),
        "blocked": not bool(boundary_ok and audit.get("ok")),
        "next_action": "ready_for_render_or_human_review" if boundary_ok and audit.get("ok") else "repair:material_first_source_intake",
        "source": _source_metadata(source),
        "metrics": {
            "scanned_count": file_count,
            "supported_count": supported_count,
            "selected_for_probe_count": len(scan_db.get("files") or []),
            "accepted_count": intake_report.get("accepted_count", 0),
            "rejected_count": len([asset for asset in verdict.get("assets") or [] if asset.get("coarse_status") == "reject"]),
            "copied_count": intake_report.get("copied_count", 0),
            "corrupt_or_unreadable_count": len(scan_db.get("rejects") or []),
            "edited_video_like_count": _edited_video_like_count(source),
            "asset_path_audit_strict_ok": bool(audit.get("ok")),
            "asset_path_audit_strict_finding_count": audit.get("strict_finding_count"),
        },
        "artifacts": {
            "run_dir": "run",
            "asset_store": "run/assets/materials",
            "boundary_report": "run/material_first_boundary_acceptance_report.json",
            "source_scan_summary": "source_scan_summary.json",
            "probe_wall_verdict": "material_wall_review_verdict.probe.json",
        },
        "copied_asset_examples": copied_assets[:5],
        "rejected_examples": _asset_examples(scan_db.get("rejects") or []),
        "blocking": blocking if not boundary_ok else [],
        "notes": [
            "probe verdict is deterministic and not a human final material review",
            "external source paths are represented by basename/hash metadata in the probe report",
        ],
    }
    write_json(probe_dir / "intake_report.json", report)
    write_json(probe_dir / "asset_path_audit_strict.json", audit)
    return report
