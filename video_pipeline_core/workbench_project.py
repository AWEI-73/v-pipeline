"""Hash-bound landing contract from the V Pipeline into Workbench.

``workbench_project.json`` is deliberately not the Brownfield
``workbench_handoff.json``.  The former exposes canonical pipeline artifacts as
read-only inputs; the latter carries draft edits back to their owning stages.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


ARTIFACT_ROLE = "workbench_project"
SCHEMA_VERSION = 1
MANIFEST_NAME = "workbench_project.json"
REQUIRED_ARTIFACTS = {"timeline", "material_map", "candidate_video"}
OPTIONAL_ARTIFACTS = {
    "subtitles",
    "audio_mix_report",
    "effect_intent_plan",
    "effect_render_verification",
    "verify_bundle",
}
ALLOWED_ARTIFACTS = REQUIRED_ARTIFACTS | OPTIONAL_ARTIFACTS


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _error(errors: list[dict[str, Any]], code: str, message: str, **details: Any) -> None:
    item = {"code": code, "message": message}
    item.update(details)
    errors.append(item)


def _artifact_detail(path: str | Path) -> dict[str, Any]:
    resolved = Path(path).expanduser().resolve()
    if not resolved.is_file():
        raise ValueError(f"workbench project artifact is missing: {resolved}")
    stat = resolved.stat()
    return {
        "path": str(resolved),
        "sha256": _sha256(resolved),
        "size_bytes": stat.st_size,
    }


def build_workbench_project(
    *,
    project_root: str | Path,
    project_id: str,
    display_name: str,
    artifact_paths: Mapping[str, str | Path],
) -> dict[str, Any]:
    """Build a read-only pipeline landing manifest without copying media."""
    del project_root  # The root owns future draft writes, not canonical reads.
    missing = sorted(REQUIRED_ARTIFACTS - set(artifact_paths))
    unknown = sorted(set(artifact_paths) - ALLOWED_ARTIFACTS)
    if missing:
        raise ValueError("missing required Workbench project artifacts: " + ", ".join(missing))
    if unknown:
        raise ValueError("unknown Workbench project artifacts: " + ", ".join(unknown))
    if not str(project_id).strip():
        raise ValueError("project_id is required")
    if not str(display_name).strip():
        raise ValueError("display_name is required")

    details = {
        key: _artifact_detail(value)
        for key, value in sorted(artifact_paths.items())
    }
    return {
        "artifact_role": ARTIFACT_ROLE,
        "version": SCHEMA_VERSION,
        "project_id": str(project_id).strip(),
        "display_name": str(display_name).strip(),
        "pipeline_route": "video-pipeline-route",
        "artifacts": details,
        "policy": {
            "canonical_artifacts_read_only": True,
            "draft_write_root": ".",
            "large_media_copied": False,
        },
    }


def write_workbench_project(
    project_root: str | Path,
    manifest: Mapping[str, Any],
    *,
    overwrite: bool = False,
) -> Path:
    """Write one landing manifest; immutable by default."""
    root = Path(project_root).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    path = root / MANIFEST_NAME
    if path.exists() and not overwrite:
        raise FileExistsError(f"Workbench project already exists: {path}")
    path.write_text(
        json.dumps(dict(manifest), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def validate_workbench_project(project_root: str | Path) -> dict[str, Any]:
    """Validate exact artifact paths and hashes; never repair or fall back."""
    root = Path(project_root).expanduser().resolve()
    path = root / MANIFEST_NAME
    errors: list[dict[str, Any]] = []
    manifest: Any = None
    if not path.is_file():
        _error(errors, "missing_workbench_project", f"{MANIFEST_NAME} is missing")
    else:
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            _error(errors, "malformed_workbench_project", str(exc))

    if not isinstance(manifest, dict):
        if path.is_file() and not errors:
            _error(errors, "invalid_workbench_project_shape", "manifest must be an object")
        manifest = {}

    if manifest.get("artifact_role") != ARTIFACT_ROLE:
        _error(errors, "invalid_workbench_project_role", f"artifact_role must be {ARTIFACT_ROLE}")
    if manifest.get("version") != SCHEMA_VERSION:
        _error(errors, "invalid_workbench_project_version", f"version must be {SCHEMA_VERSION}")
    if not isinstance(manifest.get("project_id"), str) or not manifest.get("project_id", "").strip():
        _error(errors, "missing_project_id", "project_id is required")
    if not isinstance(manifest.get("display_name"), str) or not manifest.get("display_name", "").strip():
        _error(errors, "missing_display_name", "display_name is required")

    policy = manifest.get("policy")
    if not isinstance(policy, dict):
        _error(errors, "invalid_workbench_project_policy", "policy must be an object")
        policy = {}
    if policy.get("canonical_artifacts_read_only") is not True:
        _error(errors, "canonical_write_policy_forbidden", "canonical artifacts must be read-only")
    if policy.get("draft_write_root") != ".":
        _error(errors, "invalid_draft_write_root", "draft_write_root must be '.'")

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict):
        _error(errors, "invalid_workbench_project_artifacts", "artifacts must be an object")
        artifacts = {}
    for key in sorted(REQUIRED_ARTIFACTS - set(artifacts)):
        _error(errors, "missing_required_artifact", f"required artifact is missing: {key}", artifact=key)
    for key in sorted(set(artifacts) - ALLOWED_ARTIFACTS):
        _error(errors, "unknown_artifact", f"artifact key is not supported: {key}", artifact=key)

    resolved: dict[str, str] = {}
    for key, detail in sorted(artifacts.items()):
        if not isinstance(detail, dict):
            _error(errors, "invalid_artifact_detail", "artifact detail must be an object", artifact=key)
            continue
        raw_path = detail.get("path")
        recorded_hash = detail.get("sha256")
        if not isinstance(raw_path, str) or not raw_path:
            _error(errors, "missing_artifact_path", "artifact path is required", artifact=key)
            continue
        artifact_path = Path(raw_path).expanduser()
        if not artifact_path.is_absolute():
            _error(errors, "artifact_path_not_absolute", "artifact path must be absolute", artifact=key)
            continue
        artifact_path = artifact_path.resolve()
        if not artifact_path.is_file():
            _error(errors, "artifact_missing", "referenced artifact does not exist", artifact=key, path=str(artifact_path))
            continue
        actual_hash = _sha256(artifact_path)
        if recorded_hash != actual_hash:
            _error(
                errors,
                "artifact_hash_mismatch",
                "referenced artifact hash changed",
                artifact=key,
                path=str(artifact_path),
                expected=recorded_hash,
                actual=actual_hash,
            )
            continue
        if detail.get("size_bytes") != artifact_path.stat().st_size:
            _error(errors, "artifact_size_mismatch", "referenced artifact size changed", artifact=key)
            continue
        resolved[key] = str(artifact_path)

    return {
        "artifact_role": "workbench_project_validation",
        "version": 1,
        "ok": not errors,
        "project_root": str(root),
        "manifest_path": str(path),
        "project_id": manifest.get("project_id"),
        "display_name": manifest.get("display_name"),
        "resolved_artifacts": resolved,
        "errors": errors,
    }


def resolve_workbench_project(project_root: str | Path) -> tuple[dict[str, Any], dict[str, Path]]:
    """Load a valid manifest and return its exact resolved artifact paths."""
    root = Path(project_root).expanduser().resolve()
    validation = validate_workbench_project(root)
    if not validation["ok"]:
        codes = ", ".join(item["code"] for item in validation["errors"])
        raise ValueError(f"invalid Workbench project: {codes}")
    manifest = json.loads((root / MANIFEST_NAME).read_text(encoding="utf-8"))
    refs = {key: Path(value) for key, value in validation["resolved_artifacts"].items()}
    return manifest, refs
