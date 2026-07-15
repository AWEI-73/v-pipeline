"""Persistent, versioned material-pool truth shared across campaigns.

Campaign maps remain story-specific projections.  This store keeps only
source-bound scene understanding and review provenance; campaign-specific
``satisfies`` edges never leak into the reusable pool truth.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


_POOL_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,95}$")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON artifact must be an object: {path}")
    return payload


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".writing")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def _validate_pool_root(pool_root: str | Path) -> Path:
    root = Path(pool_root)
    if any(part.lower() == ".tmp" for part in root.parts):
        raise ValueError("canonical material-pool root must live outside .tmp")
    return root


def _pool_dir(pool_root: str | Path, pool_id: str) -> Path:
    if not isinstance(pool_id, str) or not _POOL_ID.fullmatch(pool_id):
        raise ValueError("pool_id must be a stable filesystem-safe identifier")
    return _validate_pool_root(pool_root) / pool_id


def _empty_pool_map(pool_id: str) -> dict[str, Any]:
    return {
        "artifact_role": "project_material_map",
        "version": 1,
        "material_pool_id": pool_id,
        "assets": [],
        "needs": [],
        "satisfaction_summary": {},
        "metrics": {"asset_count": 0, "scene_count": 0},
    }


def _strip_campaign_truth(project_map: Mapping[str, Any], pool_id: str) -> dict[str, Any]:
    if project_map.get("artifact_role") != "project_material_map":
        raise ValueError("campaign map must be a project_material_map artifact")
    assets = copy.deepcopy(project_map.get("assets") or [])
    if not isinstance(assets, list):
        raise ValueError("project_material_map.assets must be a list")
    scene_count = 0
    for asset in assets:
        if not isinstance(asset, dict):
            raise ValueError("project_material_map asset must be an object")
        if not asset.get("asset_id"):
            raise ValueError("project_material_map asset requires asset_id")
        scenes = asset.get("scenes") or []
        if not isinstance(scenes, list):
            raise ValueError("project_material_map asset scenes must be a list")
        scene_count += len(scenes)
        for scene in scenes:
            if isinstance(scene, dict):
                scene.pop("satisfies", None)
    return {
        "artifact_role": "project_material_map",
        "version": 1,
        "material_pool_id": pool_id,
        "assets": assets,
        "needs": [],
        "satisfaction_summary": {},
        "metrics": {"asset_count": len(assets), "scene_count": scene_count},
    }


def _deep_merge(existing: Any, incoming: Any) -> Any:
    if isinstance(existing, dict) and isinstance(incoming, dict):
        merged = copy.deepcopy(existing)
        for key, value in incoming.items():
            if value is None:
                continue
            merged[key] = _deep_merge(merged.get(key), value) if key in merged else copy.deepcopy(value)
        return merged
    return copy.deepcopy(incoming)


def _scene_identity(scene: Mapping[str, Any], index: int) -> tuple[Any, ...]:
    return (
        round(float(scene.get("start") or 0), 3),
        round(float(scene.get("end") or 0), 3),
        str(scene.get("kind") or ""),
        index,
    )


def _merge_scenes(existing: list[Any], incoming: list[Any]) -> list[Any]:
    out = copy.deepcopy(existing)
    identities = {
        _scene_identity(scene, index): index
        for index, scene in enumerate(out)
        if isinstance(scene, dict)
    }
    for index, scene in enumerate(incoming):
        if not isinstance(scene, dict):
            continue
        identity = _scene_identity(scene, index)
        target = identities.get(identity)
        if target is None and index < len(out) and isinstance(out[index], dict):
            target = index
        if target is None:
            out.append(copy.deepcopy(scene))
        else:
            out[target] = _deep_merge(out[target], scene)
    return out


def _asset_key(asset: Mapping[str, Any]) -> tuple[str, str]:
    source_hash = str(asset.get("source_hash") or "").strip().lower()
    if source_hash:
        return "source_hash", source_hash
    return "asset_id", str(asset.get("asset_id") or "").strip()


def _merge_pool_maps(base: Mapping[str, Any], incoming: Mapping[str, Any], pool_id: str) -> dict[str, Any]:
    merged = _empty_pool_map(pool_id)
    assets = [copy.deepcopy(asset) for asset in (base.get("assets") or [])]
    index = {_asset_key(asset): pos for pos, asset in enumerate(assets)}
    for asset in incoming.get("assets") or []:
        key = _asset_key(asset)
        if not key[1]:
            raise ValueError("pool asset requires source_hash or asset_id")
        if key not in index:
            index[key] = len(assets)
            assets.append(copy.deepcopy(asset))
            continue
        pos = index[key]
        combined = _deep_merge(assets[pos], asset)
        combined["scenes"] = _merge_scenes(
            assets[pos].get("scenes") or [], asset.get("scenes") or [])
        assets[pos] = combined
    assets.sort(key=lambda asset: (str(asset.get("source_hash") or ""), str(asset.get("asset_id") or "")))
    scene_count = sum(len(asset.get("scenes") or []) for asset in assets)
    merged["assets"] = assets
    merged["metrics"] = {"asset_count": len(assets), "scene_count": scene_count}
    return merged


def _load_manifest(pool_dir: Path) -> dict[str, Any] | None:
    path = pool_dir / "pool_manifest.json"
    if not path.is_file():
        return None
    payload = _read_json(path)
    if payload.get("artifact_role") != "material_pool_manifest":
        raise ValueError(f"not a material_pool_manifest: {path}")
    return payload


def _latest(pool_dir: Path, manifest: Mapping[str, Any] | None) -> tuple[dict[str, Any], str]:
    if not manifest:
        return {}, "EMPTY"
    ref = manifest.get("latest_map")
    expected = str(manifest.get("latest_sha256") or "")
    path = pool_dir / str(ref or "")
    if not path.is_file() or not expected:
        raise ValueError("material-pool manifest has no readable latest version")
    actual = _sha256(path)
    if actual != expected:
        raise ValueError("material-pool latest version hash mismatch")
    return _read_json(path), actual


def checkout_pool_map(*, pool_root: str | Path, pool_id: str, campaign_id: str,
                      out_path: str | Path) -> dict[str, Any]:
    pool_dir = _pool_dir(pool_root, pool_id)
    manifest = _load_manifest(pool_dir)
    payload, base_hash = _latest(pool_dir, manifest)
    if not payload:
        payload = _empty_pool_map(pool_id)
    out = Path(out_path)
    _write_json(out, payload)
    return {
        "ok": True,
        "artifact_role": "material_pool_checkout_receipt",
        "version": 1,
        "material_pool_id": pool_id,
        "campaign_id": campaign_id,
        "base_sha256": base_hash,
        "pool_version": int((manifest or {}).get("latest_version") or 0),
        "project_material_map": str(out),
        "project_material_map_sha256": _sha256(out),
    }


def commit_campaign_map(*, pool_root: str | Path, pool_id: str, campaign_id: str,
                        campaign_map_path: str | Path,
                        expected_base_sha256: str) -> dict[str, Any]:
    pool_dir = _pool_dir(pool_root, pool_id)
    manifest = _load_manifest(pool_dir)
    base, actual_base_hash = _latest(pool_dir, manifest)
    expected = str(expected_base_sha256 or "")
    if expected != actual_base_hash:
        raise ValueError(
            f"stale material-pool base: expected {expected!r}, current {actual_base_hash!r}")

    campaign_path = Path(campaign_map_path)
    incoming = _strip_campaign_truth(_read_json(campaign_path), pool_id)
    base = base or _empty_pool_map(pool_id)
    merged = _merge_pool_maps(base, incoming, pool_id)
    next_version = int((manifest or {}).get("latest_version") or 0) + 1
    rel = Path("versions") / f"project_material_map.v{next_version:04d}.json"
    version_path = pool_dir / rel
    _write_json(version_path, merged)
    version_hash = _sha256(version_path)
    now = datetime.now(timezone.utc).isoformat()
    history = list((manifest or {}).get("versions") or [])
    history.append({
        "version": next_version,
        "map": rel.as_posix(),
        "sha256": version_hash,
        "campaign_id": campaign_id,
        "committed_at": now,
        "campaign_map": str(campaign_path),
        "campaign_map_sha256": _sha256(campaign_path),
    })
    new_manifest = {
        "artifact_role": "material_pool_manifest",
        "version": 1,
        "material_pool_id": pool_id,
        "latest_version": next_version,
        "latest_map": rel.as_posix(),
        "latest_sha256": version_hash,
        "versions": history,
    }
    _write_json(pool_dir / "pool_manifest.json", new_manifest)
    return {
        "ok": True,
        "artifact_role": "material_pool_commit_receipt",
        "version": next_version,
        "material_pool_id": pool_id,
        "campaign_id": campaign_id,
        "base_sha256": actual_base_hash,
        "committed_map": str(version_path),
        "committed_sha256": version_hash,
        "asset_count": merged["metrics"]["asset_count"],
        "scene_count": merged["metrics"]["scene_count"],
    }
