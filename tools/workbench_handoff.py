#!/usr/bin/env python
"""Hermes-native workbench: unified save / Agent handoff (Layer 4).

Builds ``workbench_handoff.json`` -- a single index the Agent reads to pick up a
human fine-tuning session: which draft patch artifacts exist and a per-layer edit
summary. It references only draft artifacts and never canonical files.
"""
from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional

ARTIFACT_ROLE = "workbench_handoff"
SCHEMA_VERSION = 1

# draft artifact name -> handoff key
DRAFT_ARTIFACTS = {
    "preview_timeline": "preview_timeline.json",
    "workbench_revision_request": "workbench_revision_request.json",
    "timeline_patch": "timeline_patch.json",
    "patched_draft_timeline": "patched_draft_timeline.json",
    "workbench_contract_patch": "workbench_contract_patch.json",
    "subtitle_patch": "subtitle_patch.json",
    "audio_cue_patch": "audio_cue_patch.json",
    "effect_patch": "effect_patch.json",
    "workbench_review_report": "workbench_review_report.json",
    "workbench_review_report_md": "workbench_review_report.md",
}

CANONICAL_ARTIFACTS = {
    "timeline.json",
    "segment_contract.json",
    "revised_segment_contract.json",
    "project_material_map.json",
    "material_needs.json",
    "materials_db.json",
    "final.mp4",
    "state.json",
    "delivery_gate.json",
}


def _load_json(path: Path) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _artifact_detail(path: Path) -> Dict[str, Any]:
    data = path.read_bytes()
    return {
        "path": path.name,
        "size_bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def _count_ops(patch: Optional[Dict[str, Any]], op_filter: Optional[str] = None) -> int:
    if not isinstance(patch, dict):
        return 0
    ops = patch.get("patches") or []
    if op_filter is None:
        return len(ops)
    return sum(1 for o in ops if isinstance(o, dict) and o.get("op") == op_filter)


def _add_route_back(items: List[Dict[str, Any]], *, owner: str, artifact: str, reason: str, next_action: str) -> None:
    if any(item.get("owner") == owner and item.get("artifact") == artifact for item in items):
        return
    items.append({
        "owner": owner,
        "artifact": artifact,
        "reason": reason,
        "next_action": next_action,
    })


def _route_back(timeline_patch: Optional[Dict[str, Any]],
                subtitle_patch: Optional[Dict[str, Any]],
                audio_cue_patch: Optional[Dict[str, Any]],
                effect_patch: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    if isinstance(timeline_patch, dict):
        ops = [op for op in timeline_patch.get("patches") or [] if isinstance(op, dict)]
        if any(op.get("op") in {"replace_clip", "insert_clip"} for op in ops):
            _add_route_back(
                items,
                owner="material-map",
                artifact="timeline_patch",
                reason="timeline replacement changes material truth",
                next_action="review_material_map_or_rough_cut_patch",
            )
        if any(op.get("op") in {"set_duration", "set_source_window", "move_clip"} for op in ops):
            _add_route_back(
                items,
                owner="build-planning",
                artifact="timeline_patch",
                reason="timeline timing/order patch changes BUILD plan only",
                next_action="review_build_timeline_patch",
            )
    if _count_ops(subtitle_patch):
        _add_route_back(
            items,
            owner="subtitle-director",
            artifact="subtitle_patch",
            reason="subtitle patch must preserve readability and language policy",
            next_action="review_subtitle_patch",
        )
    if _count_ops(audio_cue_patch):
        _add_route_back(
            items,
            owner="audio-director",
            artifact="audio_cue_patch",
            reason="audio cue patch must preserve mix, ducking, and license policy",
            next_action="review_audio_patch",
        )
    if _count_ops(effect_patch):
        _add_route_back(
            items,
            owner="effect-factory",
            artifact="effect_patch",
            reason="effect patch must return to effect contract/review",
            next_action="review_effect_patch",
        )
    return items


def build_handoff(artifact_root: str) -> Dict[str, Any]:
    """Scan the root for draft artifacts and produce the handoff index."""
    root = Path(artifact_root)
    present: Dict[str, str] = {}
    details: Dict[str, Dict[str, Any]] = {}
    for key, name in DRAFT_ARTIFACTS.items():
        path = root / name
        if path.is_file():
            present[key] = name
            details[key] = _artifact_detail(path)

    timeline_patch = _load_json(root / DRAFT_ARTIFACTS["timeline_patch"])
    subtitle_patch = _load_json(root / DRAFT_ARTIFACTS["subtitle_patch"])
    audio_cue_patch = _load_json(root / DRAFT_ARTIFACTS["audio_cue_patch"])
    effect_patch = _load_json(root / DRAFT_ARTIFACTS["effect_patch"])

    summary = {
        "timeline_edits": _count_ops(timeline_patch),
        "subtitle_edits": _count_ops(subtitle_patch),
        "audio_cues": _count_ops(audio_cue_patch, "add_cue"),
        "effect_intents": _count_ops(effect_patch, "add_effect"),
    }
    route_back = _route_back(timeline_patch, subtitle_patch, audio_cue_patch, effect_patch)

    return {
        "artifact_role": ARTIFACT_ROLE,
        "version": SCHEMA_VERSION,
        "artifacts": present,
        "artifact_details": details,
        "summary": summary,
        "route_back": route_back,
        "next_action": "review_workbench_route_back" if route_back else "agent_review_and_render_preview",
    }


def _error(errors: List[Dict[str, Any]], code: str, message: str, **extra: Any) -> None:
    item = {"code": code, "message": message}
    item.update(extra)
    errors.append(item)


def _safe_handoff_path(value: Any) -> Optional[str]:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip().replace("\\", "/")
    if text.startswith("/") or ":" in text or ".." in Path(text).parts:
        return None
    return text


def _json_role_for(key: str) -> Optional[str]:
    roles = {
        "timeline_patch": "timeline_patch",
        "subtitle_patch": "subtitle_patch",
        "audio_cue_patch": "audio_cue_patch",
        "effect_patch": "effect_patch",
        "workbench_contract_patch": "workbench_contract_patch",
        "preview_timeline": "preview_timeline",
        "workbench_revision_request": "workbench_revision_request",
        "workbench_review_report": "workbench_review_report",
    }
    return roles.get(key)


def _validate_referenced_json(path: Path, key: str, errors: List[Dict[str, Any]]) -> None:
    if path.suffix.lower() not in {".json"}:
        return
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        _error(errors, "malformed_referenced_json", f"{key} JSON is malformed", key=key, path=path.name, detail=str(exc))
        return
    if not isinstance(payload, dict):
        _error(errors, "invalid_referenced_json_shape", f"{key} JSON must be an object", key=key, path=path.name)
        return
    expected_role = _json_role_for(key)
    if expected_role and payload.get("artifact_role") not in (expected_role, None):
        _error(
            errors,
            "unexpected_artifact_role",
            f"{key} artifact_role does not match the referenced draft artifact",
            key=key,
            path=path.name,
            expected=expected_role,
            actual=payload.get("artifact_role"),
        )


def validate_handoff(artifact_root: str) -> Dict[str, Any]:
    """Validate workbench_handoff.json before an Agent consumes draft artifacts."""
    root = Path(artifact_root)
    handoff_path = root / "workbench_handoff.json"
    errors: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []
    present: List[str] = []
    missing: List[str] = []

    if not handoff_path.is_file():
        _error(errors, "missing_handoff", "workbench_handoff.json is missing")
        return {
            "artifact_role": "workbench_handoff_validation",
            "version": 1,
            "ok": False,
            "artifact_root": str(root),
            "errors": errors,
            "warnings": warnings,
            "present_artifacts": present,
            "missing_artifacts": missing,
        }

    try:
        handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        _error(errors, "malformed_handoff", f"workbench_handoff.json is malformed: {exc}")
        handoff = None

    if not isinstance(handoff, dict):
        if handoff is not None:
            _error(errors, "invalid_handoff_shape", "workbench_handoff.json must be an object")
        return {
            "artifact_role": "workbench_handoff_validation",
            "version": 1,
            "ok": False,
            "artifact_root": str(root),
            "errors": errors,
            "warnings": warnings,
            "present_artifacts": present,
            "missing_artifacts": missing,
        }

    if handoff.get("artifact_role") != ARTIFACT_ROLE:
        _error(errors, "invalid_handoff_role", "artifact_role must be workbench_handoff")
    if handoff.get("version") != SCHEMA_VERSION:
        _error(errors, "invalid_handoff_version", "workbench_handoff version must be 1")

    artifacts = handoff.get("artifacts")
    details = handoff.get("artifact_details")
    if not isinstance(artifacts, dict):
        _error(errors, "invalid_artifacts_shape", "artifacts must be an object")
        artifacts = {}
    if not isinstance(details, dict):
        _error(errors, "invalid_artifact_details_shape", "artifact_details must be an object")
        details = {}

    allowed_names = set(DRAFT_ARTIFACTS.values())
    for key, raw_rel in sorted(artifacts.items()):
        rel = _safe_handoff_path(raw_rel)
        if rel is None:
            _error(errors, "unsafe_artifact_reference", "handoff artifact path must be a safe relative path", key=key, value=raw_rel)
            continue
        name = Path(rel).name
        if name in CANONICAL_ARTIFACTS or rel not in allowed_names:
            _error(errors, "canonical_artifact_reference", "handoff may only reference Workbench draft artifacts", key=key, path=rel)
        path = root / rel
        if not path.is_file():
            missing.append(str(key))
            _error(errors, "missing_referenced_artifact", "handoff references a missing draft artifact", key=key, path=rel)
            continue
        present.append(str(key))

        detail = details.get(key)
        if not isinstance(detail, dict):
            _error(errors, "missing_artifact_detail", "artifact_details entry is missing or invalid", key=key)
            continue
        recorded_path = _safe_handoff_path(detail.get("path"))
        if recorded_path != rel:
            _error(errors, "artifact_detail_path_mismatch", "artifact detail path differs from artifacts entry", key=key, path=rel, detail_path=detail.get("path"))

        actual = _artifact_detail(path)
        if detail.get("size_bytes") != actual["size_bytes"]:
            _error(errors, "size_mismatch", "artifact size differs from handoff detail", key=key, path=rel)
        if detail.get("sha256") != actual["sha256"]:
            _error(errors, "hash_mismatch", "artifact hash differs from handoff detail", key=key, path=rel)
        _validate_referenced_json(path, str(key), errors)

    return {
        "artifact_role": "workbench_handoff_validation",
        "version": 1,
        "ok": not errors,
        "artifact_root": str(root),
        "errors": errors,
        "warnings": warnings,
        "present_artifacts": sorted(set(present)),
        "missing_artifacts": sorted(set(missing)),
    }
