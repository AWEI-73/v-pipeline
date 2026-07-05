"""Material-first review packet and render promotion helpers."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

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
