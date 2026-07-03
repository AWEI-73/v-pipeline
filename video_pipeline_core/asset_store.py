"""Run-local asset ingest and garbage collection helpers."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Any, Iterable

from .asset_paths import is_absolute_path_string, resolve_asset_ref, to_asset_ref


MEDIA_SUFFIXES = {
    ".mp4", ".mov", ".m4v", ".webm", ".avi", ".mkv",
    ".mp3", ".wav", ".m4a", ".aac", ".flac",
    ".jpg", ".jpeg", ".png", ".webp", ".heic",
}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _media_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".mp4", ".mov", ".m4v", ".webm", ".avi", ".mkv"}:
        return "video"
    if suffix in {".mp3", ".wav", ".m4a", ".aac", ".flac"}:
        return "audio"
    if suffix in {".jpg", ".jpeg", ".png", ".webp", ".heic"}:
        return "photo"
    return "asset"


def _iter_source_files(source_dir: Path) -> Iterable[Path]:
    for path in sorted(source_dir.rglob("*")):
        if path.is_file() and path.suffix.lower() in MEDIA_SUFFIXES:
            yield path


def _copy_or_link(source: Path, dest: Path) -> str:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        if dest.stat().st_size != source.stat().st_size or _sha256(dest) != _sha256(source):
            raise ValueError(f"destination exists with different content: {dest}")
        return "existing"
    try:
        os.link(source, dest)
        return "hardlink"
    except OSError:
        shutil.copy2(source, dest)
        return "copy"


def _load_project_map(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "artifact_role": "project_material_map",
            "version": 1,
            "assets": [],
            "needs": [],
            "satisfaction_summary": {},
            "metrics": {"asset_count": 0, "scene_count": 0},
        }
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict) or payload.get("artifact_role") != "project_material_map":
        raise ValueError(f"not a project_material_map artifact: {path}")
    payload.setdefault("assets", [])
    return payload


def _asset_id_for(path: Path, existing: set[str]) -> str:
    base = path.stem.replace(" ", "_") or "asset"
    candidate = base
    index = 2
    while candidate in existing:
        candidate = f"{base}_{index}"
        index += 1
    return candidate


def _upsert_asset(project_map: dict[str, Any], *, run_dir: Path, dest: Path) -> dict[str, Any]:
    ref = to_asset_ref(run_dir, dest).ref
    assets = project_map.setdefault("assets", [])
    for asset in assets:
        if asset.get("source") == ref or asset.get("path") == ref:
            asset["source"] = ref
            asset["path"] = ref
            asset.setdefault("asset_type", _media_type(dest))
            return asset
    existing_ids = {str(asset.get("asset_id")) for asset in assets if asset.get("asset_id")}
    asset = {
        "asset_id": _asset_id_for(dest, existing_ids),
        "asset_type": _media_type(dest),
        "source": ref,
        "path": ref,
        "scenes": [],
        "speech": [],
    }
    assets.append(asset)
    return asset


def _write_project_map(path: Path, payload: dict[str, Any]) -> None:
    metrics = payload.setdefault("metrics", {})
    metrics["asset_count"] = len(payload.get("assets") or [])
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def ingest_assets(run_dir: str | Path, source_dir: str | Path) -> dict[str, Any]:
    run_path = Path(run_dir)
    source_path = Path(source_dir)
    if not run_path.exists() or not run_path.is_dir():
        raise ValueError(f"run_dir must exist: {run_path}")
    if not source_path.exists() or not source_path.is_dir():
        raise ValueError(f"--from must be an existing directory: {source_path}")
    if source_path.resolve() == (run_path / "assets").resolve():
        raise ValueError("source directory is already the run assets directory")

    project_map_path = run_path / "project_material_map.json"
    project_map = _load_project_map(project_map_path)
    ingested = []
    for source in _iter_source_files(source_path):
        dest = run_path / "assets" / source.name
        method = _copy_or_link(source, dest)
        asset = _upsert_asset(project_map, run_dir=run_path, dest=dest)
        ingested.append({
            "source": str(source),
            "asset": to_asset_ref(run_path, dest).ref,
            "method": method,
            "asset_id": asset["asset_id"],
            "size_bytes": dest.stat().st_size,
        })
    _write_project_map(project_map_path, project_map)
    return {
        "ok": True,
        "run_dir": str(run_path),
        "assets_dir": str(run_path / "assets"),
        "project_material_map": str(project_map_path),
        "ingested_count": len(ingested),
        "ingested": ingested,
    }


def _iter_json_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _iter_json_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_json_strings(item)


def _referenced_assets(run_dir: Path) -> set[Path]:
    assets_dir = run_dir / "assets"
    refs: set[Path] = set()
    for json_path in sorted(run_dir.rglob("*.json")):
        try:
            payload = json.loads(json_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            continue
        for value in _iter_json_strings(payload):
            if is_absolute_path_string(value):
                candidate = Path(value)
            else:
                candidate = Path(resolve_asset_ref(run_dir, value))
            try:
                resolved = candidate.resolve()
                resolved.relative_to(assets_dir.resolve())
            except (OSError, ValueError):
                continue
            refs.add(resolved)
    return refs


def gc_assets(run_dir: str | Path, *, delete: bool = False) -> dict[str, Any]:
    run_path = Path(run_dir)
    assets_dir = run_path / "assets"
    if not run_path.exists() or not run_path.is_dir():
        raise ValueError(f"run_dir must exist: {run_path}")
    if not assets_dir.exists():
        return {"ok": True, "run_dir": str(run_path), "orphan_count": 0, "orphan_bytes": 0, "orphans": []}
    referenced = _referenced_assets(run_path)
    orphans = []
    for path in sorted(item for item in assets_dir.rglob("*") if item.is_file()):
        resolved = path.resolve()
        if resolved in referenced:
            continue
        size = path.stat().st_size
        rel = path.relative_to(run_path).as_posix()
        orphans.append({"path": rel, "size_bytes": size, "deleted": False})
        if delete:
            path.unlink()
            orphans[-1]["deleted"] = True
    return {
        "ok": True,
        "run_dir": str(run_path),
        "orphan_count": len(orphans),
        "orphan_bytes": sum(item["size_bytes"] for item in orphans),
        "deleted": bool(delete),
        "orphans": orphans,
    }
