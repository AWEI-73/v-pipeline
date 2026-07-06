"""Material-first review packet and render promotion helpers."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from .asset_paths import build_asset_path_audit
from .material_rough_cut import write_json


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _source_meta(entry: dict[str, Any]) -> dict[str, Any]:
    meta = entry.get("original_source") or {}
    return {
        "basename": meta.get("basename"),
        "source_kind": meta.get("source_kind"),
        "source_path_hash": meta.get("source_path_hash"),
        "content_sha256": meta.get("content_sha256"),
        "size_bytes": meta.get("size_bytes"),
    }


def _reviewed_assets(materials_db: dict[str, Any]) -> list[dict[str, Any]]:
    assets = []
    for entry in materials_db.get("files") or []:
        review = entry.get("material_wall_review") or {}
        asset_ref = entry.get("asset_store_ref") or entry.get("path")
        assets.append({
            "asset_id": entry.get("id"),
            "type": entry.get("type"),
            "asset_ref": asset_ref,
            "asset_store_ref": asset_ref,
            "format": entry.get("format"),
            "role_hints": review.get("visual_role") or [],
            "quality": review.get("quality"),
            "usable_ranges": review.get("usable_ranges") or [],
            "visual_evidence": review.get("visual_evidence") or [],
            "caption": entry.get("vlm_caption"),
            "original_source": _source_meta(entry),
        })
    return assets


def _rejected_summary(materials_db: dict[str, Any], handoff: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    out = []
    for bucket, reason_key in (("rejects", "reason"), ("skipped", "reason")):
        for entry in materials_db.get(bucket) or []:
            meta = entry.get("original_source") or {}
            out.append({
                "asset_id": entry.get("asset_id") or entry.get("id"),
                "bucket": bucket,
                "basename": meta.get("basename") or entry.get("path"),
                "source_kind": meta.get("source_kind"),
                "source_path_hash": meta.get("source_path_hash"),
                "reason": entry.get(reason_key),
            })
    handoff = handoff or {}
    for bucket, ids in (
        ("wall_rejected", handoff.get("rejected_asset_ids") or []),
        ("wall_duplicate", handoff.get("duplicate_asset_ids") or []),
    ):
        for asset_id in ids:
            out.append({
                "asset_id": asset_id,
                "bucket": bucket,
                "basename": None,
                "source_kind": None,
                "source_path_hash": None,
                "reason": bucket,
            })
    return out


def build_material_first_review_packet(run_dir: str | Path) -> dict[str, Any]:
    """Write a compact human/agent review packet for material-first promotion."""

    root = Path(run_dir).resolve()
    materials_db = _load_json(root / "materials_db.json")
    handoff = _load_json(root / "material_wall_handoff_report.json") if (root / "material_wall_handoff_report.json").exists() else {}
    packet = {
        "artifact_role": "material_review_packet",
        "version": 1,
        "route": "material-first",
        "next_action": "await_material_wall_review",
        "review_scope": "material_first_review_to_render_promotion",
        "asset_store": materials_db.get("asset_store") or "assets/materials",
        "accepted_candidate_assets": _reviewed_assets(materials_db),
        "rejected_corrupt_or_skipped": _rejected_summary(materials_db, handoff),
        "material_wall_summary": {
            "selected_asset_ids": handoff.get("selected_asset_ids") or [],
            "rejected_asset_ids": handoff.get("rejected_asset_ids") or [],
            "duplicate_asset_ids": handoff.get("duplicate_asset_ids") or [],
            "need_coverage": handoff.get("need_coverage") or {},
            "ready_for_mapping": bool(handoff.get("ready_for_mapping")),
        },
        "verdict_instructions": {
            "write_artifact": "material_wall_review_verdict.json",
            "required_statuses": ["keep", "maybe", "reject", "duplicate"],
            "keep_or_maybe_requires": ["visual_evidence"],
            "reject_or_duplicate_requires": ["why_not_selected"],
            "do_not_use_external_absolute_paths": True,
            "final_delivery_claim": False,
        },
        "warnings": [
            "This packet is a review/promotion surface only; it does not claim final delivery.",
        ],
    }
    write_json(root / "material_review_packet.json", packet)
    return packet


def _decision_counts(verdict: dict[str, Any]) -> tuple[int, int]:
    accepted = 0
    rejected = 0
    for asset in verdict.get("assets") or []:
        status = asset.get("coarse_status")
        if status in {"keep", "maybe"}:
            accepted += 1
        elif status in {"reject", "duplicate"}:
            rejected += 1
    return accepted, rejected


def _reviewable_asset_ids(packet: dict[str, Any]) -> set[str]:
    ids = set()
    for asset in packet.get("accepted_candidate_assets") or []:
        asset_id = asset.get("asset_id")
        if asset_id:
            ids.add(asset_id)
    return ids


def _known_packet_asset_ids(packet: dict[str, Any]) -> set[str]:
    ids = _reviewable_asset_ids(packet)
    for asset in packet.get("rejected_corrupt_or_skipped") or []:
        asset_id = asset.get("asset_id")
        if asset_id:
            ids.add(asset_id)
    return ids


def _verdict_asset_ids(verdict: dict[str, Any]) -> set[str]:
    ids = set()
    for asset in verdict.get("assets") or []:
        asset_id = asset.get("asset_id")
        if asset_id:
            ids.add(asset_id)
    return ids


def _blocked_verdict_acceptance(root: Path, rule: str, message: str, **extra) -> dict[str, Any]:
    blocking = [{"rule": rule, "message": message, **extra}]
    report = {
        "artifact_role": "material_first_review_verdict_acceptance",
        "version": 1,
        "ok": False,
        "next_action": "blocked",
        "decision_source": "human_or_agent_review",
        "blocking": blocking,
    }
    write_json(root / "material_first_review_verdict_acceptance.json", report)
    return report


def accept_material_first_review_verdict(
    run_dir: str | Path,
    verdict_path: str | Path,
) -> dict[str, Any]:
    """Validate and persist an explicit human/agent material wall verdict."""

    root = Path(run_dir).resolve()
    packet_path = root / "material_review_packet.json"
    if not packet_path.exists():
        build_material_first_review_packet(root)
    packet = _load_json(packet_path)
    verdict = _load_json(Path(verdict_path))
    expected = _reviewable_asset_ids(packet)
    known = _known_packet_asset_ids(packet)
    actual = _verdict_asset_ids(verdict)
    missing = sorted(expected - actual)
    if missing:
        return _blocked_verdict_acceptance(
            root,
            "missing_review_decision",
            "material wall verdict is missing decisions for review packet assets",
            asset_ids=missing,
        )
    unknown = sorted(actual - known)
    if unknown:
        return _blocked_verdict_acceptance(
            root,
            "unknown_review_asset",
            "material wall verdict references assets outside the review packet",
            asset_ids=unknown,
        )

    accepted_count, rejected_count = _decision_counts(verdict)
    destination = root / "material_wall_review_verdict.json"
    if Path(verdict_path).resolve() != destination.resolve():
        shutil.copy2(verdict_path, destination)
    report = {
        "artifact_role": "material_first_review_verdict_acceptance",
        "version": 1,
        "ok": True,
        "next_action": "ready_for_render_promotion_gate",
        "decision_source": "human_or_agent_review",
        "review_packet": "material_review_packet.json",
        "accepted_verdict": "material_wall_review_verdict.json",
        "accepted_asset_count": accepted_count,
        "rejected_asset_count": rejected_count,
        "blocking": [],
    }
    write_json(root / "material_first_review_verdict_acceptance.json", report)
    return report


def _block(rule: str, message: str, **extra) -> dict[str, Any]:
    out = {"rule": rule, "message": message}
    out.update(extra)
    return out


def _timeline_refs(timeline: dict[str, Any]) -> list[dict[str, Any]]:
    refs = []
    for clip in timeline.get("clips") or []:
        refs.append({
            "segment": clip.get("segment"),
            "asset_id": clip.get("asset_id"),
            "source_path": clip.get("source_path"),
            "start_sec": clip.get("start_sec"),
            "duration_sec": clip.get("duration_sec"),
            "scene_id": clip.get("scene_id"),
        })
    return refs


def _asset_ref_blocks(
    root: Path,
    materials_db: dict[str, Any],
    timeline: dict[str, Any],
    rough_cut: dict[str, Any],
) -> list[dict[str, Any]]:
    blocks = []
    refs = [
        entry.get("asset_store_ref") or entry.get("path")
        for entry in materials_db.get("files") or []
    ]
    refs.extend(clip.get("source_path") for clip in timeline.get("clips") or [])
    refs.extend(clip.get("source_path") for clip in rough_cut.get("clips") or [])
    for ref in sorted({str(value or "") for value in refs if value}):
        if not ref.startswith("assets/materials/"):
            blocks.append(_block(
                "non_asset_store_ref",
                "material-first render promotion requires run-local asset store refs",
                asset_ref=ref,
            ))
            continue
        if not (root / ref).is_file():
            blocks.append(_block(
                "missing_asset_store_file",
                "material-first render promotion requires copied asset store files",
                asset_ref=ref,
            ))
    return blocks


def build_material_first_render_promotion(run_dir: str | Path) -> dict[str, Any]:
    """Write render readiness and handoff artifacts for a reviewed material run."""

    root = Path(run_dir).resolve()
    materials_db = _load_json(root / "materials_db.json") if (root / "materials_db.json").exists() else {}
    material_delta = _load_json(root / "material_delta.json") if (root / "material_delta.json").exists() else {}
    timeline = _load_json(root / "timeline_build.json") if (root / "timeline_build.json").exists() else {}
    rough_cut = _load_json(root / "rough_cut_plan.json") if (root / "rough_cut_plan.json").exists() else {}
    verdict_acceptance = (
        _load_json(root / "material_first_review_verdict_acceptance.json")
        if (root / "material_first_review_verdict_acceptance.json").exists()
        else {}
    )
    asset_audit = build_asset_path_audit(root, strict=False)

    blocking: list[dict[str, Any]] = []
    if not material_delta.get("ok") or not material_delta.get("ready_for_build"):
        blocking.append(_block(
            "material_delta_not_ready",
            "material_delta.json must be ok and ready_for_build before render promotion",
        ))
    if not timeline.get("clips"):
        blocking.append(_block("missing_timeline_build", "timeline_build.json must contain clips"))
    if rough_cut.get("ok") is False or rough_cut.get("gaps"):
        blocking.append(_block("rough_cut_not_ready", "rough_cut_plan.json still has gaps"))
    if verdict_acceptance.get("ok") is not True:
        blocking.append(_block(
            "review_verdict_not_accepted",
            "material_first_review_verdict_acceptance.json must pass before render promotion",
        ))
    render_ref_blocks = _asset_ref_blocks(root, materials_db, timeline, rough_cut)
    blocking.extend(render_ref_blocks)

    ready = not blocking
    warning_count = int(asset_audit.get("finding_count") or 0)
    warnings = []
    if warning_count:
        warnings.append({
            "rule": "non_render_critical_absolute_paths",
            "message": "absolute provenance/evidence paths are preserved as warnings and do not block render handoff",
            "finding_count": warning_count,
        })
    report = {
        "artifact_role": "render_readiness_report",
        "version": 1,
        "route": "material-first",
        "ok": ready,
        "next_action": "ready_for_render" if ready else "blocked",
        "final_delivery_claimed": False,
        "checks": {
            "material_delta_ready": bool(material_delta.get("ok") and material_delta.get("ready_for_build")),
            "timeline_clip_count": len(timeline.get("clips") or []),
            "review_verdict_accepted": verdict_acceptance.get("ok") is True,
            "render_critical_asset_refs_ok": not render_ref_blocks,
            "asset_path_warning_count": warning_count,
            "asset_path_audit_finding_count": asset_audit.get("finding_count"),
            "asset_path_audit_strict_finding_count": asset_audit.get("strict_finding_count"),
        },
        "asset_path_warning_summary": {
            "finding_count": warning_count,
            "families": asset_audit.get("families") or {},
        },
        "warnings": warnings,
        "blocking": blocking,
        "read": [
            "materials_db.json",
            "material_delta.json",
            "timeline_build.json",
            "rough_cut_plan.json",
            "material_first_review_verdict_acceptance.json",
        ],
    }
    write_json(root / "render_readiness_report.json", report)
    if not ready:
        handoff = root / "render_handoff.json"
        if handoff.exists():
            handoff.unlink()
        return report

    handoff = {
        "artifact_role": "render_handoff",
        "version": 1,
        "route": "material-first",
        "ok": True,
        "next_action": "ready_for_render",
        "final_delivery_claimed": False,
        "render_inputs": {
            "timeline_build": "timeline_build.json",
            "rough_cut_plan": "rough_cut_plan.json",
            "project_material_map": "project_material_map.json",
            "material_delta": "material_delta.json",
        },
        "timeline_refs": _timeline_refs(timeline),
        "notes": [
            "Render handoff is not final delivery; final.mp4 promotion still requires delivery validation.",
        ],
    }
    write_json(root / "render_handoff.json", handoff)
    return report
