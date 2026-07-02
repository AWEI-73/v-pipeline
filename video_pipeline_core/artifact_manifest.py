from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _load_manifest(manifest_path: Path) -> dict[str, Any]:
    if not manifest_path.is_file():
        return {}
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)


def handoff_manifest_key(artifact_path: str | Path) -> str:
    path = Path(artifact_path)
    if path.suffix.lower() != ".json":
        raise ValueError(f"handoff artifact must be JSON: {artifact_path}")
    return path.stem


def register_handoff(
    run_dir: str | Path,
    *,
    artifact_path: str | Path,
    owner_branch: str,
    status: str,
    updated_by: str,
    interface_id: str | None = None,
    next_action: str | None = None,
    key: str | None = None,
) -> dict[str, Any]:
    root = Path(run_dir)
    manifest_path = root / "artifact_manifest.json"
    artifact = Path(artifact_path)
    if not artifact.is_absolute():
        artifact = root / artifact
    manifest = _load_manifest(manifest_path)
    manifest.setdefault("artifact_role", "artifact_manifest")
    manifest.setdefault("artifact_manifest_version", 1)

    artifact_key = key or handoff_manifest_key(artifact)
    rel_path = _rel(artifact, root)
    manifest.setdefault(artifact_key, rel_path)

    artifacts = manifest.setdefault("artifacts", {})
    if not isinstance(artifacts, dict):
        artifacts = {}
        manifest["artifacts"] = artifacts
    record = {
        "path": rel_path,
        "artifact_class": "handoff",
        "owner_branch": owner_branch,
        "status": status,
        "updated_by": updated_by,
    }
    if interface_id:
        record["interface_id"] = interface_id
    if next_action:
        record["next_action"] = next_action
    existing_artifact = artifacts.get(artifact_key)
    if not isinstance(existing_artifact, dict):
        existing_artifact = {}
    merged_artifact = dict(existing_artifact)
    merged_artifact.update(record)
    artifacts[artifact_key] = merged_artifact

    handoffs = manifest.setdefault("handoffs", {})
    if not isinstance(handoffs, dict):
        handoffs = {}
        manifest["handoffs"] = handoffs
    handoffs[artifact_key] = dict(merged_artifact)

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest
