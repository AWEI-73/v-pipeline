"""Material-first source intake helpers for run-local asset storage."""
from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Any


def _sha256_bytes(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="surrogateescape")).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _source_metadata(source: Path) -> dict[str, Any]:
    return {
        "basename": source.name,
        "source_kind": "external_path",
        "source_path_hash": _sha256_bytes(str(source.resolve())),
        "content_sha256": _sha256_file(source),
        "size_bytes": source.stat().st_size,
    }


def _asset_store_ref(run_dir: Path, asset_id: str, source: Path) -> tuple[Path, str]:
    suffix = source.suffix.lower() or ".asset"
    relative = Path("assets") / "materials" / f"{asset_id}{suffix}"
    return run_dir / relative, relative.as_posix()


def import_material_first_assets(run_dir: str | Path, materials_db: dict[str, Any]) -> dict[str, Any]:
    """Copy accepted material-first files into ``assets/materials``.

    ``materials_db`` is returned as a JSON-compatible copy whose primary
    material refs are run-relative. External absolute source paths are retained
    only as hashed metadata.
    """

    root = Path(run_dir).resolve()
    imported_files: list[dict[str, Any]] = []
    copied = []
    for entry in materials_db.get("files") or []:
        source = Path(entry.get("path") or "")
        if not source.is_file():
            raise ValueError(f"material source file does not exist: {source}")
        asset_id = str(entry.get("id") or entry.get("asset_id") or "").strip()
        if not asset_id:
            raise ValueError(f"material source is missing stable id: {source}")
        dest, ref = _asset_store_ref(root, asset_id, source)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            shutil.copy2(source, dest)
            method = "copy"
        else:
            if _sha256_file(dest) != _sha256_file(source):
                raise ValueError(f"asset store destination exists with different content: {dest}")
            method = "existing"
        updated = dict(entry)
        updated["path"] = ref
        updated["asset_store_ref"] = ref
        updated["original_source"] = _source_metadata(source)
        imported_files.append(updated)
        copied.append({
            "asset_id": asset_id,
            "asset": ref,
            "method": method,
            "size_bytes": dest.stat().st_size,
            "source_path_hash": updated["original_source"]["source_path_hash"],
        })

    sanitized = sanitize_source_candidate_db(materials_db)
    imported = dict(materials_db)
    imported["source_kind"] = "external_path"
    imported.pop("source_dir", None)
    imported["asset_store"] = "assets/materials"
    imported["files"] = imported_files
    imported["rejects"] = sanitized.get("rejects") or []
    imported["skipped"] = sanitized.get("skipped") or []
    imported["import_report"] = {
        "artifact_role": "material_first_source_intake_report",
        "version": 1,
        "asset_store": "assets/materials",
        "accepted_count": len(imported_files),
        "copied_count": len(copied),
        "rejected_count": len(materials_db.get("rejects") or []),
        "copied_assets": copied,
    }
    return imported


def sanitize_source_candidate_db(materials_db: dict[str, Any]) -> dict[str, Any]:
    """Return intake metadata without absolute source paths as primary refs."""

    out = dict(materials_db)
    out.pop("source_dir", None)
    files = []
    for entry in materials_db.get("files") or []:
        item = dict(entry)
        source = Path(item.get("path") or "")
        if source:
            item["original_source"] = _source_metadata(source) if source.is_file() else {
                "basename": source.name,
                "source_kind": "external_path",
                "source_path_hash": _sha256_bytes(str(source)),
                "size_bytes": item.get("size_bytes"),
            }
            item["path"] = item["original_source"]["basename"]
        files.append(item)
    out["files"] = files
    rejects = []
    for reject in materials_db.get("rejects") or []:
        item = dict(reject)
        source = Path(item.get("path") or "")
        if source:
            item["original_source"] = {
                "basename": source.name,
                "source_kind": "external_path",
                "source_path_hash": _sha256_bytes(str(source)),
            }
            item["path"] = source.name
        rejects.append(item)
    out["rejects"] = rejects
    skipped = []
    for skipped_item in materials_db.get("skipped") or []:
        item = dict(skipped_item)
        source = Path(item.get("path") or "")
        if source:
            item["original_source"] = {
                "basename": source.name,
                "source_kind": "external_path",
                "source_path_hash": _sha256_bytes(str(source)),
            }
            item["path"] = source.name
        skipped.append(item)
    out["skipped"] = skipped
    return out
