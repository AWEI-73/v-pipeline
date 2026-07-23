#!/usr/bin/env python
"""Hermes-native workbench: unified save / Agent handoff (Layer 4).

Builds ``workbench_handoff.json`` -- a single index the Agent reads to pick up a
human fine-tuning session: which draft patch artifacts exist and a per-layer edit
summary. It references only draft artifacts and never canonical files.
"""
from __future__ import annotations

import json
import hashlib
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

ARTIFACT_ROLE = "workbench_handoff"
SCHEMA_VERSION = 1
HUMAN_DECISION_ROLE = "workbench_human_decision"
HUMAN_DECISION_VERSION = 1

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
    "workbench_human_decision": "workbench_human_decision.json",
    "workbench_review_report": "workbench_review_report.json",
    "workbench_review_report_md": "workbench_review_report.md",
}

PATCH_ARTIFACTS = {
    "timeline_patch": "timeline_patch.json",
    "subtitle_patch": "subtitle_patch.json",
    "audio_cue_patch": "audio_cue_patch.json",
    "effect_patch": "effect_patch.json",
}

DECISION_CATEGORIES = {
    "picture",
    "timing",
    "subtitle",
    "audio",
    "effect",
    "story",
    "overall",
}

DURATION_POLICIES = {"flexible", "target_with_tolerance", "fixed"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

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


def _canonical_sha256(payload: Any) -> str:
    raw = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _written_payload_sha256(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _subject_binding(artifact_root: str, preview: Dict[str, Any]) -> Dict[str, Any]:
    candidate = preview.get("candidate_video")
    if isinstance(candidate, dict) and SHA256_RE.fullmatch(str(candidate.get("sha256") or "")):
        return {
            "subject_type": "current_candidate",
            "path": str(candidate.get("source_path") or ""),
            "sha256": candidate["sha256"],
            "binding_status": "bound_exact_candidate",
        }

    source = preview.get("source_artifact")
    path = Path(str(source)) if source else Path(artifact_root) / "timeline.json"
    if not path.is_absolute():
        path = Path(artifact_root) / path
    if not path.is_file():
        raise ValueError("workbench decision subject is missing")
    return {
        "subject_type": "draft_timeline",
        "path": str(path.resolve()),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "binding_status": "bound_exact_timeline",
    }


def build_human_decision(
    artifact_root: str,
    *,
    preview: Dict[str, Any],
    decision_context: Optional[Dict[str, Any]],
    provided_patches: Dict[str, Any],
) -> Dict[str, Any]:
    """Build one signed Human decision batch for the existing Brownfield route.

    The signature is a content digest and exact-subject binding. It proves what
    the local Workbench submitted; it is not an identity or creative-approval
    credential.
    """
    context = decision_context if isinstance(decision_context, dict) else {}
    notes: List[Dict[str, Any]] = []
    for index, raw in enumerate(context.get("review_notes") or []):
        if not isinstance(raw, dict):
            continue
        text = str(raw.get("text") or "").strip()
        if not text:
            continue
        window = raw.get("timeline_window") if isinstance(raw.get("timeline_window"), dict) else {}
        notes.append({
            "note_id": str(raw.get("note_id") or f"note-{index + 1:03d}"),
            "scope": "segment" if raw.get("scope") != "whole_video" else "whole_video",
            "category": str(raw.get("category") or "overall"),
            "segment_id": raw.get("segment_id"),
            "slot_index": raw.get("slot_index"),
            "timeline_window": {
                "start_sec": float(window.get("start_sec") or 0.0),
                "end_sec": float(window.get("end_sec") or 0.0),
            },
            "text": text,
        })

    duration_policy = str(context.get("duration_policy") or "flexible")
    duration_contract: Dict[str, Any] = {"mode": duration_policy}
    if duration_policy == "target_with_tolerance":
        duration_contract["target_sec"] = float(context.get("target_duration_sec") or preview.get("duration_sec") or 0.0)
        duration_contract["tolerance_sec"] = float(context.get("duration_tolerance_sec") or 2.0)
    elif duration_policy == "fixed":
        duration_contract["target_sec"] = float(context.get("target_duration_sec") or preview.get("duration_sec") or 0.0)
        duration_contract["tolerance_sec"] = 0.0

    patch_bindings = {
        key: {
            "path": PATCH_ARTIFACTS[key],
            "sha256": _written_payload_sha256(payload),
        }
        for key, payload in sorted(provided_patches.items())
        if key in PATCH_ARTIFACTS
    }
    assertion = {
        "subject": _subject_binding(artifact_root, preview),
        "decision_source": "workbench_explicit_submit",
        "identity_assurance": "self_asserted_local_ui",
        "duration_policy": duration_contract,
        "review_notes": notes,
        "patch_bindings": patch_bindings,
    }
    return {
        "artifact_role": HUMAN_DECISION_ROLE,
        "version": HUMAN_DECISION_VERSION,
        **assertion,
        "signature": {
            "algorithm": "sha256_canonical_json_v1",
            "digest": _canonical_sha256(assertion),
        },
        "human_creative_approval": False,
        "final_delivery_claimed": False,
        "must_not_claim": [
            "cryptographic_human_identity",
            "canonical_timeline_mutation",
            "creative_approval",
            "final_delivery",
        ],
    }


def validate_human_decision(payload: Any) -> List[str]:
    errors: List[str] = []
    if not isinstance(payload, dict):
        return ["human decision must be an object"]
    if payload.get("artifact_role") != HUMAN_DECISION_ROLE:
        errors.append(f"artifact_role must be {HUMAN_DECISION_ROLE}")
    if payload.get("version") != HUMAN_DECISION_VERSION:
        errors.append(f"version must be {HUMAN_DECISION_VERSION}")
    if payload.get("decision_source") != "workbench_explicit_submit":
        errors.append("decision_source must be workbench_explicit_submit")
    if payload.get("identity_assurance") != "self_asserted_local_ui":
        errors.append("identity_assurance must be self_asserted_local_ui")
    subject = payload.get("subject")
    if not isinstance(subject, dict):
        errors.append("subject must be an object")
    else:
        if subject.get("binding_status") not in {"bound_exact_candidate", "bound_exact_timeline"}:
            errors.append("subject binding_status must be exact")
        if not SHA256_RE.fullmatch(str(subject.get("sha256") or "")):
            errors.append("subject sha256 must be a lowercase SHA-256")
    duration_policy = payload.get("duration_policy")
    duration_mode = duration_policy.get("mode") if isinstance(duration_policy, dict) else None
    if duration_mode not in DURATION_POLICIES:
        errors.append("duration_policy mode is invalid")
    notes = payload.get("review_notes")
    if not isinstance(notes, list):
        errors.append("review_notes must be a list")
        notes = []
    for index, note in enumerate(notes):
        if not isinstance(note, dict):
            errors.append(f"review_notes[{index}] must be an object")
            continue
        if note.get("category") not in DECISION_CATEGORIES:
            errors.append(f"review_notes[{index}] category is invalid")
        if not str(note.get("text") or "").strip():
            errors.append(f"review_notes[{index}] text is required")
    patch_bindings = payload.get("patch_bindings")
    if not isinstance(patch_bindings, dict):
        errors.append("patch_bindings must be an object")
        patch_bindings = {}
    for key, detail in patch_bindings.items():
        if key not in PATCH_ARTIFACTS:
            errors.append(f"unknown patch binding: {key}")
            continue
        if not isinstance(detail, dict) or detail.get("path") != PATCH_ARTIFACTS[key]:
            errors.append(f"{key} patch path is invalid")
        elif not SHA256_RE.fullmatch(str(detail.get("sha256") or "")):
            errors.append(f"{key} patch sha256 is invalid")
    if not notes and not patch_bindings and duration_mode == "flexible":
        errors.append("decision must contain a review note, patch binding, or explicit duration constraint")
    if payload.get("human_creative_approval") is not False:
        errors.append("human_creative_approval must remain false")
    if payload.get("final_delivery_claimed") is not False:
        errors.append("final_delivery_claimed must remain false")

    signature = payload.get("signature")
    assertion = {
        "subject": payload.get("subject"),
        "decision_source": payload.get("decision_source"),
        "identity_assurance": payload.get("identity_assurance"),
        "duration_policy": payload.get("duration_policy"),
        "review_notes": payload.get("review_notes"),
        "patch_bindings": payload.get("patch_bindings"),
    }
    if not isinstance(signature, dict) or signature.get("algorithm") != "sha256_canonical_json_v1":
        errors.append("signature algorithm is invalid")
    elif signature.get("digest") != _canonical_sha256(assertion):
        errors.append("signature digest mismatch")
    return errors


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
                effect_patch: Optional[Dict[str, Any]],
                human_decision: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    if isinstance(human_decision, dict):
        _add_route_back(
            items,
            owner="brownfield-edit",
            artifact="workbench_human_decision",
            reason="explicit Workbench decisions must compile through the existing bounded Brownfield route",
            next_action="review_human_decision_and_compile_bounded_patch",
        )
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
    human_decision = _load_json(root / DRAFT_ARTIFACTS["workbench_human_decision"])
    active_patch_keys = None
    if isinstance(human_decision, dict) and isinstance(human_decision.get("patch_bindings"), dict):
        active_patch_keys = set(human_decision["patch_bindings"])

    present: Dict[str, str] = {}
    details: Dict[str, Dict[str, Any]] = {}
    for key, name in DRAFT_ARTIFACTS.items():
        if key in PATCH_ARTIFACTS and active_patch_keys is not None and key not in active_patch_keys:
            continue
        path = root / name
        if path.is_file():
            present[key] = name
            details[key] = _artifact_detail(path)

    def active_patch(key: str) -> Optional[Dict[str, Any]]:
        if active_patch_keys is not None and key not in active_patch_keys:
            return None
        return _load_json(root / DRAFT_ARTIFACTS[key])

    timeline_patch = active_patch("timeline_patch")
    subtitle_patch = active_patch("subtitle_patch")
    audio_cue_patch = active_patch("audio_cue_patch")
    effect_patch = active_patch("effect_patch")

    summary = {
        "timeline_edits": _count_ops(timeline_patch),
        "subtitle_edits": _count_ops(subtitle_patch),
        "audio_cues": _count_ops(audio_cue_patch, "add_cue"),
        "effect_intents": _count_ops(effect_patch, "add_effect"),
        "review_notes": len(human_decision.get("review_notes") or []) if isinstance(human_decision, dict) else 0,
    }
    route_back = _route_back(
        timeline_patch,
        subtitle_patch,
        audio_cue_patch,
        effect_patch,
        human_decision,
    )

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
        "workbench_human_decision": HUMAN_DECISION_ROLE,
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
