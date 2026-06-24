"""Build Remotion collage media refs from reviewed material artifacts.

This module is intentionally a thin adapter. It does not decide material truth,
extract frames, or mutate material maps; it only converts already-reviewed still
or thumbnail evidence into the `collage_media_refs` shape consumed by Remotion
effect templates.
"""

from __future__ import annotations

import json
import urllib.parse
from pathlib import Path
from typing import Any, Mapping


DEFAULT_ALLOWED_ROLES = ("opening", "hero", "training", "closing")
IMAGE_TYPES = {"image", "photo", "still"}
KEEP_STATUSES = {"keep", "accepted", "maybe"}
REJECT_STATUSES = {"reject", "rejected", "duplicate"}


def _load_json(path: str | Path | None) -> Any:
    if path is None:
        return None
    with Path(path).open(encoding="utf-8-sig") as f:
        return json.load(f)


def _write_json(path: str | Path, payload: Mapping[str, Any]) -> str:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _status(value: Any) -> str:
    return str(value or "").strip().lower()


def _roles(value: Any) -> list[str]:
    return [str(item).strip().lower() for item in _as_list(value) if str(item).strip()]


def _path_to_file_uri(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.startswith("file://"):
        return text
    if "/media?src=" in text:
        parsed = urllib.parse.urlparse(text)
        query = urllib.parse.parse_qs(parsed.query)
        src_values = query.get("src") or []
        if src_values:
            return _path_to_file_uri(src_values[0])
    if text.startswith("http://") or text.startswith("https://"):
        return text
    return Path(text).resolve().as_uri()


def _assets_by_id(material_map: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    if not isinstance(material_map, dict) or material_map.get("artifact_role") != "project_material_map":
        raise ValueError("material_map must be project_material_map")
    assets = material_map.get("assets")
    if not isinstance(assets, list):
        raise ValueError("project_material_map.assets must be list")
    return {
        str(asset.get("asset_id")): asset
        for asset in assets
        if isinstance(asset, dict) and asset.get("asset_id")
    }


def _review_assets(verdict: Mapping[str, Any] | None,
                   material_map: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    if isinstance(verdict, dict) and isinstance(verdict.get("assets"), list):
        return [asset for asset in verdict["assets"] if isinstance(asset, dict)]

    # Fallback: use accepted material-map scenes when no wall verdict exists.
    assets = []
    for asset in material_map.get("assets") or []:
        if not isinstance(asset, dict):
            continue
        roles = set()
        for scene in asset.get("scenes") or []:
            for sat in scene.get("satisfies") or []:
                if _status(sat.get("status")) == "accepted":
                    need_id = str(sat.get("need_id") or "").lower()
                    for role in DEFAULT_ALLOWED_ROLES:
                        if role in need_id:
                            roles.add(role)
        if roles:
            assets.append({
                "asset_id": asset.get("asset_id"),
                "coarse_status": "keep",
                "visual_role": sorted(roles),
            })
    return assets


def _thumbnail_lookup(workbench_thumbnails: Mapping[str, Any] | None) -> dict[str, str]:
    if not isinstance(workbench_thumbnails, dict):
        return {}
    thumbs = workbench_thumbnails.get("thumbnails") or {}
    if not isinstance(thumbs, dict):
        return {}
    return {str(key): str(value) for key, value in thumbs.items()}


def _wall_keyframe_lookup(material_wall_request: Mapping[str, Any] | None) -> dict[str, str]:
    if not isinstance(material_wall_request, dict):
        return {}
    lookup: dict[str, str] = {}
    for batch in material_wall_request.get("batches") or []:
        if not isinstance(batch, dict):
            continue
        for asset in batch.get("assets") or []:
            if not isinstance(asset, dict):
                continue
            asset_id = str(asset.get("asset_id") or "")
            if not asset_id or asset_id in lookup:
                continue
            frames = asset.get("frames") or []
            if not frames or not isinstance(frames[0], dict):
                continue
            image_path = frames[0].get("image_path")
            if isinstance(image_path, str) and image_path.strip():
                lookup[asset_id] = image_path
    return lookup


def _caption(asset: Mapping[str, Any]) -> str:
    scenes = asset.get("scenes") or []
    if scenes and isinstance(scenes[0], dict):
        caption = scenes[0].get("caption")
        if isinstance(caption, str) and caption.strip():
            return caption.strip()
    return str(asset.get("asset_id") or "")


def _media_path(review_asset: Mapping[str, Any], map_asset: Mapping[str, Any],
                thumbnails: Mapping[str, str],
                wall_keyframes: Mapping[str, str]) -> tuple[str, str] | tuple[None, None]:
    for key in ("collage_ref_path", "thumbnail_path", "still_path", "preview_path"):
        uri = _path_to_file_uri(review_asset.get(key))
        if uri:
            return uri, key
    asset_id = str(review_asset.get("asset_id") or map_asset.get("asset_id") or "")
    if asset_id and thumbnails.get(asset_id):
        return _path_to_file_uri(thumbnails[asset_id]), "workbench_thumbnail"
    if asset_id and wall_keyframes.get(asset_id):
        return _path_to_file_uri(wall_keyframes[asset_id]), "material_wall_keyframe"
    asset_type = str(map_asset.get("asset_type") or "").strip().lower()
    if asset_type in IMAGE_TYPES:
        return _path_to_file_uri(map_asset.get("source")), "source_image"
    return None, None


def build_collage_media_refs(material_map: Mapping[str, Any], *,
                             material_wall_review_verdict: Mapping[str, Any] | None = None,
                             workbench_thumbnails: Mapping[str, Any] | None = None,
                             material_wall_request: Mapping[str, Any] | None = None,
                             allowed_roles: tuple[str, ...] = DEFAULT_ALLOWED_ROLES,
                             max_refs: int = 6) -> dict[str, Any]:
    by_id = _assets_by_id(material_map)
    allowed = {role.lower() for role in allowed_roles}
    thumbnails = _thumbnail_lookup(workbench_thumbnails)
    wall_keyframes = _wall_keyframe_lookup(material_wall_request)
    refs: list[dict[str, Any]] = []
    skipped_rejected = 0
    skipped_missing_visual = 0
    skipped_unmatched = 0

    for review_asset in _review_assets(material_wall_review_verdict, material_map):
        asset_id = str(review_asset.get("asset_id") or "")
        coarse = _status(review_asset.get("coarse_status") or review_asset.get("status"))
        if coarse in REJECT_STATUSES:
            skipped_rejected += 1
            continue
        if coarse and coarse not in KEEP_STATUSES:
            continue
        roles = _roles(review_asset.get("visual_role") or review_asset.get("roles"))
        if roles and not (set(roles) & allowed):
            continue
        map_asset = by_id.get(asset_id)
        if not map_asset:
            skipped_unmatched += 1
            continue
        media_uri, evidence_kind = _media_path(review_asset, map_asset, thumbnails, wall_keyframes)
        if not media_uri:
            skipped_missing_visual += 1
            continue
        label = str(review_asset.get("label") or _caption(map_asset) or asset_id).strip()
        refs.append({
            "ref_id": asset_id,
            "path": media_uri,
            "label": label,
            "source_asset_id": asset_id,
            "visual_role": roles,
            "evidence_kind": evidence_kind,
        })
        if len(refs) >= max_refs:
            break

    return {
        "artifact_role": "effect_collage_media_refs",
        "version": 1,
        "ok": bool(refs),
        "collage_media_refs": refs,
        "diagnostics": {
            "selected_count": len(refs),
            "skipped_rejected_count": skipped_rejected,
            "skipped_missing_visual_count": skipped_missing_visual,
            "skipped_unmatched_count": skipped_unmatched,
            "allowed_roles": sorted(allowed),
        },
        "next_action": "attach_to_remotion_effect_build_spec" if refs else "provide_reviewed_stills_or_thumbnails",
    }


def write_collage_media_refs(material_map_path: str | Path,
                             out_path: str | Path, *,
                             material_wall_review_verdict_path: str | Path | None = None,
                             workbench_thumbnails_path: str | Path | None = None,
                             material_wall_request_path: str | Path | None = None,
                             max_refs: int = 6) -> dict[str, Any]:
    artifact = build_collage_media_refs(
        _load_json(material_map_path),
        material_wall_review_verdict=_load_json(material_wall_review_verdict_path),
        workbench_thumbnails=_load_json(workbench_thumbnails_path),
        material_wall_request=_load_json(material_wall_request_path),
        max_refs=max_refs,
    )
    _write_json(out_path, artifact)
    return artifact
