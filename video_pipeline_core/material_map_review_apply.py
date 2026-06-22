"""Apply material-map review decisions to canonical material-map artifacts.

This is the bridge from an agent/director review gate back into the deterministic
material-map lifecycle: reviewers write decisions, this module validates and
persists the scene->need satisfies edges.
"""
from __future__ import annotations

import json
from pathlib import Path

from .material_needs import apply_satisfaction_verdict, need_ids
from .project_material_map import build_project_material_map


def _load_json(path):
    with Path(path).open(encoding="utf-8-sig") as handle:
        return json.load(handle)


def _write_json(path, payload):
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_asset_maps(maps_dir):
    rows = []
    for path in sorted(Path(maps_dir).glob("*.map.json")):
        payload = _load_json(path)
        asset_id = payload.get("asset_id")
        if not isinstance(asset_id, str) or not asset_id.strip():
            raise ValueError(f"{path} asset_id must be a non-empty string")
        rows.append((path, payload))
    if not rows:
        raise ValueError(f"no *.map.json files found under {maps_dir}")
    return rows


def _decisions_from_verdict(verdict):
    if isinstance(verdict.get("decisions"), list):
        return verdict["decisions"]
    decisions = []
    for asset in verdict.get("assets") or []:
        asset_id = asset.get("asset_id")
        for scene in asset.get("scenes") or []:
            for edge in scene.get("satisfies") or []:
                decisions.append({
                    "asset_id": asset_id,
                    "scene_index": scene.get("scene_index"),
                    "need_id": edge.get("need_id"),
                    "status": edge.get("status", "candidate"),
                    "note": edge.get("note"),
                    "reviewer": edge.get("reviewer"),
                    "at": edge.get("at"),
                })
    return decisions


def _skipped_assets_from_material_db(material_db):
    return {
        entry.get("id"): entry
        for entry in (material_db or {}).get("files") or []
        if entry.get("id") and entry.get("material_map_status") == "skipped"
    }


def _group_decisions(asset_maps, verdict, *, skipped_assets=None, skipped_policy=None):
    by_asset = {payload["asset_id"]: payload for _path, payload in asset_maps}
    grouped = {}
    ignored = []
    skipped_assets = skipped_assets or {}
    for index, decision in enumerate(_decisions_from_verdict(verdict)):
        if not isinstance(decision, dict):
            raise ValueError(f"decision {index} must be an object")
        asset_id = decision.get("asset_id")
        if asset_id not in by_asset:
            if skipped_policy == "ignore-with-report" and asset_id in skipped_assets:
                ignored.append({
                    "decision_index": index,
                    "asset_id": asset_id,
                    "need_id": decision.get("need_id"),
                    "reason": "skipped_asset",
                    "material_map_error": skipped_assets[asset_id].get("material_map_error"),
                })
                continue
            raise ValueError(f"decision {index} references unknown asset_id {asset_id!r}")
        scene_index = decision.get("scene_index")
        scenes = by_asset[asset_id].get("scenes") or []
        if not isinstance(scene_index, int) or not (0 <= scene_index < len(scenes)):
            raise ValueError(
                f"decision {index} references invalid scene_index {scene_index!r} "
                f"for asset_id {asset_id!r}")
        status = decision.get("status", "candidate")
        visual_evidence = decision.get("visual_evidence")
        if status == "accepted":
            if not (
                isinstance(visual_evidence, list)
                and any(isinstance(item, str) and item.strip() for item in visual_evidence)
            ):
                raise ValueError(
                    f"decision {index} accepted edge requires non-empty visual_evidence "
                    f"(folder/source path is only a hint)")
            if decision.get("evidence_basis") == "source_path_only":
                raise ValueError(
                    f"decision {index} accepted edge cannot use evidence_basis=source_path_only")
        grouped.setdefault(asset_id, []).append({
            "scene_index": scene_index,
            "satisfies": [{
                "need_id": decision.get("need_id"),
                "status": status,
                "note": decision.get("note"),
                "reviewer": decision.get("reviewer"),
                "at": decision.get("at"),
                "visual_evidence": visual_evidence,
            }],
        })
    return grouped, ignored


def apply_review_to_maps(maps_dir, needs_path, verdict_path, out_path, *,
                         material_db_path=None, skipped_policy=None):
    asset_maps = _load_asset_maps(maps_dir)
    needs = _load_json(needs_path)
    verdict = _load_json(verdict_path)
    valid_need_ids = need_ids(needs)
    if not valid_need_ids:
        raise ValueError("material_needs must declare at least one need_id")

    if skipped_policy not in (None, "ignore-with-report"):
        raise ValueError(f"unsupported skipped_policy {skipped_policy!r}")
    material_db = _load_json(material_db_path) if material_db_path else None
    skipped_assets = _skipped_assets_from_material_db(material_db)
    grouped, ignored = _group_decisions(
        asset_maps,
        verdict,
        skipped_assets=skipped_assets,
        skipped_policy=skipped_policy,
    )
    reviewer = verdict.get("reviewer")
    at = verdict.get("at")
    updated_count = 0
    edge_count = 0
    updated_maps = []
    for path, material_map in asset_maps:
        scenes = grouped.get(material_map["asset_id"], [])
        if scenes:
            material_map = apply_satisfaction_verdict(
                material_map,
                {"reviewer": reviewer, "at": at, "scenes": scenes},
                valid_need_ids=valid_need_ids,
            )
            _write_json(path, material_map)
            updated_count += 1
            edge_count += sum(len(item.get("satisfies") or []) for item in scenes)
        updated_maps.append(material_map)

    project_map = build_project_material_map(updated_maps, needs=needs)
    _write_json(out_path, project_map)
    return {
        "ok": True,
        "artifact_role": "material_map_review_apply_result",
        "version": 1,
        "updated_asset_maps": updated_count,
        "applied_edges": edge_count,
        "ignored_decisions": len(ignored),
        "ignored": ignored,
        "project_material_map": str(Path(out_path)),
        "metrics": project_map["metrics"],
    }
