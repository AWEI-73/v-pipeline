"""Immutable, hash-bound global editorial state revisions.

This module owns the state contract. The command adapter in ``tools/`` only
loads inputs, calls these functions, and serializes the result.
"""

from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


SCHEMA_VERSION = 1
STATE_ROLE = "global_editorial_state"
DELTA_ROLE = "global_editorial_state_delta"
ALLOWED_MATERIAL_ORIGINS = {"raw", "curated", "generated", "reference"}
ALLOWED_ANNOTATION_STATES = {"intent_annotated", "metadata_only", "unannotated"}
DECISION_COMPLETENESS = {"PASS", "UNKNOWN"}


class EditorialStateError(ValueError):
    """A fail-closed state contract error with a stable machine code."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _canonical_json(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _payload_without_integrity_and_receipt(state: dict) -> dict:
    payload = copy.deepcopy(state)
    payload.pop("integrity", None)
    payload.pop("last_updated_by_receipt", None)
    return payload


def _hash_payload(state: dict) -> str:
    return hashlib.sha256(
        _canonical_json(_payload_without_integrity_and_receipt(state)).encode("utf-8")
    ).hexdigest()


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_exclusive(path: Path, value: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise EditorialStateError(
            "immutable_artifact_exists", "immutable artifact already exists: " + str(path)
        )
    text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
    except FileExistsError as exc:
        raise EditorialStateError(
            "immutable_artifact_exists", "immutable artifact already exists: " + str(path)
        ) from exc


def _relative_or_absolute(path: Path, root: Path | None = None) -> str:
    path = Path(path).resolve()
    if root is not None:
        try:
            return path.relative_to(Path(root).resolve()).as_posix()
        except ValueError:
            pass
    return str(path)


def _find_repo_root(start: Path) -> Path:
    for candidate in [Path(start).resolve(), *Path(start).resolve().parents]:
        if (candidate / "video_pipeline_core").is_dir() and (candidate / "skills").is_dir():
            return candidate
    return Path(start).resolve()


def _resolve_ref(path_value: str, state_path: Path, repo_root: Path) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    candidate = repo_root / path
    if candidate.exists():
        return candidate
    return state_path.parent / path


def _validate_axes(material_context: dict) -> None:
    origin = material_context.get("material_origin")
    if origin not in ALLOWED_MATERIAL_ORIGINS:
        raise EditorialStateError(
            "invalid_material_origin", "invalid material_origin: " + repr(origin)
        )
    annotation = material_context.get("annotation_state")
    if annotation not in ALLOWED_ANNOTATION_STATES:
        raise EditorialStateError(
            "invalid_annotation_state", "invalid annotation_state: " + repr(annotation)
        )


def _validate_segments(state: dict) -> None:
    operational = state.get("operational_state")
    if not isinstance(operational, dict):
        raise EditorialStateError("invalid_operational_state", "operational_state must be an object")
    segments = operational.get("segments")
    if not isinstance(segments, dict):
        raise EditorialStateError("invalid_operational_state", "operational_state.segments must be an object")
    for segment_id, segment in segments.items():
        if not isinstance(segment, dict):
            raise EditorialStateError("invalid_segment_record", "segment must be an object: " + str(segment_id))
        completeness = segment.get("decision_completeness")
        if completeness not in DECISION_COMPLETENESS:
            raise EditorialStateError(
                "invalid_decision_completeness",
                "invalid decision_completeness for " + str(segment_id),
            )
        refs = segment.get("source_window_refs")
        if completeness == "PASS" and not isinstance(refs, list):
            raise EditorialStateError(
                "pass_without_source_window_refs",
                "PASS segment has no source_window_refs list: " + str(segment_id),
            )
        if completeness == "PASS" and not refs:
            raise EditorialStateError(
                "pass_without_source_window_refs",
                "PASS segment has no source-window references: " + str(segment_id),
            )


def _validate_shape(state: dict) -> None:
    required = [
        "artifact_role",
        "schema_version",
        "project_id",
        "revision_id",
        "created_at",
        "base_state",
        "last_updated_by_receipt",
        "source_artifacts",
        "material_context",
        "operational_state",
        "editorial_intent",
        "open_story_risks",
        "retired_story_intents",
        "verification_state",
        "human_creative_approval",
        "final_delivery_claimed",
        "integrity",
    ]
    missing = [key for key in required if key not in state]
    if missing:
        raise EditorialStateError("invalid_state_shape", "missing required state fields: " + ",".join(missing))
    if state.get("artifact_role") != STATE_ROLE:
        raise EditorialStateError("invalid_state_shape", "artifact_role is not global_editorial_state")
    if state.get("schema_version") != SCHEMA_VERSION:
        raise EditorialStateError("invalid_state_shape", "unsupported schema_version")
    if state.get("human_creative_approval") is not False:
        raise EditorialStateError("human_creative_approval_forbidden", "human_creative_approval must remain false")
    if state.get("final_delivery_claimed") is not False:
        raise EditorialStateError("final_delivery_forbidden", "final_delivery_claimed must remain false")
    if not isinstance(state.get("material_context"), dict):
        raise EditorialStateError("invalid_state_shape", "material_context must be an object")
    _validate_axes(state["material_context"])
    intent = state.get("editorial_intent")
    if not isinstance(intent, dict) or intent.get("enforceable") is not False:
        raise EditorialStateError("editorial_intent_must_be_non_enforceable", "editorial_intent.enforceable must be false")
    _validate_segments(state)


def _validate_source_refs(state: dict, state_path: Path, repo_root: Path) -> None:
    refs = state.get("source_artifacts")
    if not isinstance(refs, list):
        raise EditorialStateError("invalid_source_artifacts", "source_artifacts must be a list")
    for ref in refs:
        if not isinstance(ref, dict) or not ref.get("path") or not ref.get("sha256"):
            raise EditorialStateError("invalid_source_artifacts", "source artifact reference is incomplete")
        source_path = _resolve_ref(str(ref["path"]), state_path, repo_root)
        if not source_path.is_file() or hash_file(source_path) != ref["sha256"]:
            raise EditorialStateError(
                "source_artifact_hash_mismatch", "source artifact hash mismatch: " + str(ref["path"])
            )


def validate_state_file(state_path: Path, repo_root: Path | None = None) -> dict:
    state_path = Path(state_path)
    if not state_path.is_file():
        raise EditorialStateError("state_not_found", "state file does not exist: " + str(state_path))
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EditorialStateError("invalid_state_json", "state JSON cannot be read: " + str(state_path)) from exc
    if not isinstance(state, dict):
        raise EditorialStateError("invalid_state_shape", "state JSON must be an object")
    _validate_shape(state)
    actual_payload_hash = _hash_payload(state)
    expected_payload_hash = ((state.get("integrity") or {}).get("state_payload_sha256"))
    if actual_payload_hash != expected_payload_hash:
        raise EditorialStateError("state_payload_hash_mismatch", "state payload hash mismatch")
    repo_root = Path(repo_root).resolve() if repo_root else _find_repo_root(state_path.parent)
    _validate_source_refs(state, state_path, repo_root)

    revision_id = state["revision_id"]
    receipt_ref = state.get("last_updated_by_receipt")
    if revision_id == 0:
        if state.get("base_state") is not None:
            raise EditorialStateError("invalid_revision_zero", "revision 0 cannot point to a base state")
        if not isinstance(receipt_ref, dict) or not receipt_ref.get("path") or not receipt_ref.get("sha256"):
            raise EditorialStateError("invalid_genesis_receipt", "revision 0 must point to a genesis receipt")
        receipt_path = _resolve_ref(str(receipt_ref["path"]), state_path, repo_root)
        if not receipt_path.is_file() or hash_file(receipt_path) != receipt_ref["sha256"]:
            raise EditorialStateError("state_receipt_hash_mismatch", "state genesis receipt hash does not match receipt file")
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise EditorialStateError("invalid_receipt", "genesis receipt JSON cannot be read") from exc
        if receipt.get("base_state_file_sha256") is not None or receipt.get("delta_path") is not None:
            raise EditorialStateError("invalid_genesis_receipt", "genesis receipt cannot carry a base or delta")
        if receipt.get("new_state_payload_sha256") != actual_payload_hash:
            raise EditorialStateError("receipt_payload_hash_mismatch", "genesis receipt payload hash does not match state")
    else:
        base_ref = state.get("base_state")
        if not isinstance(base_ref, dict) or not base_ref.get("path") or not base_ref.get("sha256"):
            raise EditorialStateError("invalid_base_state", "revision must carry base_state path and hash")
        base_path = _resolve_ref(str(base_ref["path"]), state_path, repo_root)
        if not base_path.is_file() or hash_file(base_path) != base_ref["sha256"]:
            raise EditorialStateError("stale_base_state", "base state file hash does not match")
        if not isinstance(receipt_ref, dict) or not receipt_ref.get("path") or not receipt_ref.get("sha256"):
            raise EditorialStateError("invalid_receipt", "revision must carry receipt path and hash")
        receipt_path = _resolve_ref(str(receipt_ref["path"]), state_path, repo_root)
        if not receipt_path.is_file() or hash_file(receipt_path) != receipt_ref["sha256"]:
            raise EditorialStateError("state_receipt_hash_mismatch", "state receipt hash does not match receipt file")
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise EditorialStateError("invalid_receipt", "receipt JSON cannot be read") from exc
        delta_path_value = receipt.get("delta_path")
        delta_hash = receipt.get("delta_sha256")
        if not isinstance(delta_path_value, str) or not delta_path_value or not isinstance(delta_hash, str):
            raise EditorialStateError("invalid_receipt", "transition receipt must carry delta path and hash")
        delta_path = _resolve_ref(delta_path_value, state_path, repo_root)
        if not delta_path.is_file() or hash_file(delta_path) != delta_hash:
            raise EditorialStateError("receipt_delta_hash_mismatch", "receipt delta hash does not match delta file")
        try:
            delta = json.loads(delta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise EditorialStateError("invalid_delta", "receipt delta JSON cannot be read") from exc
        if delta.get("base_state_sha256") != base_ref["sha256"]:
            raise EditorialStateError("receipt_base_hash_mismatch", "delta base hash does not match state base")
        if receipt.get("new_state_payload_sha256") != actual_payload_hash:
            raise EditorialStateError("receipt_payload_hash_mismatch", "receipt payload hash does not match state")
        if receipt.get("base_state_file_sha256") != base_ref["sha256"]:
            raise EditorialStateError("receipt_base_hash_mismatch", "receipt base hash does not match state")

    return {
        "status": "PASS",
        "artifact_role": state["artifact_role"],
        "revision_id": revision_id,
        "project_id": state["project_id"],
        "state_payload_sha256": actual_payload_hash,
        "state_file_sha256": hash_file(state_path),
        "path": str(state_path),
    }


def _make_state(project_id: str, revision_id: int, seed: dict, source_artifacts: list, base_state=None) -> dict:
    state = {
        "artifact_role": STATE_ROLE,
        "schema_version": SCHEMA_VERSION,
        "project_id": project_id,
        "revision_id": revision_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "base_state": base_state,
        "last_updated_by_receipt": None,
        "source_artifacts": copy.deepcopy(source_artifacts),
        "material_context": copy.deepcopy(seed.get("material_context", {})),
        "operational_state": copy.deepcopy(seed.get("operational_state", {})),
        "editorial_intent": copy.deepcopy(seed.get("editorial_intent", {})),
        "open_story_risks": copy.deepcopy(seed.get("open_story_risks", [])),
        "retired_story_intents": copy.deepcopy(seed.get("retired_story_intents", [])),
        "verification_state": copy.deepcopy(seed.get("verification_state", {})),
        "human_creative_approval": False,
        "final_delivery_claimed": False,
    }
    _validate_shape({**state, "integrity": {"state_payload_sha256": "pending"}})
    state["integrity"] = {"state_payload_sha256": _hash_payload(state)}
    return state


def create_revision_zero(output_dir: Path, project_id: str, seed: dict, source_artifacts: list) -> Path:
    output_dir = Path(output_dir)
    state_path = output_dir / "revision_0000.json"
    receipt_path = output_dir / "receipt_genesis.json"
    if state_path.exists() or receipt_path.exists():
        raise EditorialStateError("immutable_artifact_exists", "genesis state or receipt already exists")
    state = _make_state(project_id, 0, seed, source_artifacts)
    receipt = {
        "artifact_role": "global_editorial_state_transition_receipt",
        "schema_version": SCHEMA_VERSION,
        "revision_id": 0,
        "base_state_file_sha256": None,
        "delta_path": None,
        "delta_sha256": None,
        "new_state_payload_sha256": state["integrity"]["state_payload_sha256"],
        "source_artifact_hashes": [ref.get("sha256") for ref in source_artifacts],
        "operation_result": "genesis",
    }
    _write_exclusive(receipt_path, receipt)
    state["last_updated_by_receipt"] = {
        "path": receipt_path.name,
        "sha256": hash_file(receipt_path),
    }
    _write_exclusive(state_path, state)
    return state_path


def _deep_merge(target: dict, patch: dict) -> None:
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_merge(target[key], value)
        else:
            target[key] = copy.deepcopy(value)


def _default_forward_delta(state: dict, repo_root: Path, base_state_name: str) -> dict:
    base_revision_id = int(state["revision_id"])
    next_revision_id = base_revision_id + 1
    decision_path = repo_root / "docs" / "decisions" / "2026-07-14-canon67-teacher-all-or-none-memory-ending.md"
    if decision_path.is_file():
        decision_ref = {
            "path": _relative_or_absolute(decision_path, repo_root),
            "sha256": hash_file(decision_path),
        }
    else:
        refs = state.get("source_artifacts") or []
        decision_ref = refs[0] if refs else {"path": "unavailable", "sha256": ""}
    return {
        "artifact_role": DELTA_ROLE,
        "schema_version": SCHEMA_VERSION,
        "base_state_path": base_state_name,
        "base_state_sha256": "",
        "change_kind": "accepted_teacher_coverage_deferral_confirmation",
        "changes": {
            "operational_state": {
                "coverage_ledger": {
                    "teacher_adviser_sequence": {
                        "forward_test_confirmation": {
                            "status": "deferred_due_to_incomplete_all_or_none_roster",
                            "required_roster_count": 13,
                            "decision_artifact": decision_ref,
                            "reason": "the accepted all-or-none roster is incomplete",
                        }
                    }
                }
            }
        },
        "operation_result": "accepted_operational_fact",
    }


def build_forward_delta(base_state_path: Path, repo_root: Path) -> Path:
    base_state_path = Path(base_state_path)
    result = validate_state_file(base_state_path, repo_root=repo_root)
    state = json.loads(base_state_path.read_text(encoding="utf-8"))
    next_revision_id = int(result["revision_id"]) + 1
    delta = _default_forward_delta(state, Path(repo_root).resolve(), base_state_path.name)
    delta["base_state_sha256"] = hash_file(base_state_path)
    delta_path = base_state_path.parent / (
        "delta_{:04d}_to_{:04d}.json".format(result["revision_id"], next_revision_id)
    )
    _write_exclusive(delta_path, delta)
    return delta_path


def apply_delta(base_state_path: Path, delta_path: Path, output_dir: Path) -> Path:
    base_state_path = Path(base_state_path)
    delta_path = Path(delta_path)
    output_dir = Path(output_dir)
    base_result = validate_state_file(base_state_path)
    try:
        delta = json.loads(delta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EditorialStateError("invalid_delta", "delta JSON cannot be read") from exc
    if hash_file(base_state_path) != delta.get("base_state_sha256"):
        raise EditorialStateError("stale_base_state", "delta base hash does not match supplied base state")
    if delta.get("artifact_role") != DELTA_ROLE or delta.get("schema_version") != SCHEMA_VERSION:
        raise EditorialStateError("invalid_delta", "delta role or schema version is invalid")
    if not isinstance(delta.get("changes"), dict):
        raise EditorialStateError("invalid_delta", "delta changes must be an object")
    current = json.loads(base_state_path.read_text(encoding="utf-8"))
    next_state = copy.deepcopy(current)
    _deep_merge(next_state, delta["changes"])
    next_revision_id = int(base_result["revision_id"]) + 1
    next_state["revision_id"] = next_revision_id
    next_state["created_at"] = datetime.now(timezone.utc).isoformat()
    next_state["base_state"] = {
        "path": base_state_path.name,
        "sha256": hash_file(base_state_path),
    }
    next_state["last_updated_by_receipt"] = None
    next_state["integrity"] = {"state_payload_sha256": _hash_payload(next_state)}
    _validate_shape(next_state)

    base_revision_id = int(base_result["revision_id"])
    revision_path = output_dir / "revision_{:04d}.json".format(next_revision_id)
    receipt_path = output_dir / (
        "receipt_{:04d}_to_{:04d}.json".format(base_revision_id, next_revision_id)
    )
    if revision_path.exists() or receipt_path.exists():
        raise EditorialStateError("immutable_artifact_exists", "revision 1 or receipt already exists")
    receipt = {
        "artifact_role": "global_editorial_state_transition_receipt",
        "schema_version": SCHEMA_VERSION,
        "revision_id": next_revision_id,
        "base_state_file_sha256": hash_file(base_state_path),
        "delta_path": delta_path.name,
        "delta_sha256": hash_file(delta_path),
        "new_state_payload_sha256": next_state["integrity"]["state_payload_sha256"],
        "source_artifact_hashes": [ref.get("sha256") for ref in next_state["source_artifacts"]],
        "operation_result": delta.get("operation_result", "accepted_delta"),
    }
    _write_exclusive(receipt_path, receipt)
    next_state["last_updated_by_receipt"] = {
        "path": receipt_path.name,
        "sha256": hash_file(receipt_path),
    }
    _write_exclusive(revision_path, next_state)
    return revision_path


def validate_worker_context(context: dict, current_state_path: Path) -> dict:
    current_state_path = Path(current_state_path)
    current = validate_state_file(current_state_path)
    pinned_path = context.get("pinned_state_path") if isinstance(context, dict) else None
    pinned_hash = context.get("pinned_state_sha256") if isinstance(context, dict) else None
    if not pinned_path or not pinned_hash:
        raise EditorialStateError("stale_base_state", "worker context has no pinned state path/hash")
    if Path(pinned_path).resolve() != current_state_path.resolve() or pinned_hash != current["state_file_sha256"]:
        raise EditorialStateError("stale_base_state", "worker context is pinned to a stale state")
    return {"status": "PASS", "pinned_state_sha256": pinned_hash, "current_state": current["path"]}


def write_worker_context(state_path: Path, output_path: Path) -> Path:
    state_path = Path(state_path)
    current = validate_state_file(state_path)
    context = {
        "artifact_role": "global_editorial_worker_context",
        "schema_version": SCHEMA_VERSION,
        "pinned_state_path": str(state_path),
        "pinned_state_sha256": current["state_file_sha256"],
    }
    _write_exclusive(Path(output_path), context)
    return Path(output_path)


def _load_json(path: Path) -> dict:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EditorialStateError("invalid_json_input", "cannot read JSON input: " + str(path)) from exc
    if not isinstance(data, dict):
        raise EditorialStateError("invalid_json_input", "JSON input must be an object: " + str(path))
    return data


def _canon67_source_paths(repo_root: Path) -> dict:
    return {
        "story_soul_blueprint": repo_root / ".tmp/canon67_540s_route_acceptance/stage1/story_soul_blueprint.json",
        "screenplay_beats": repo_root / ".tmp/canon67_540s_route_acceptance/stage1/screenplay_beats.json",
        "material_map": repo_root / ".tmp/canon67_540s_route_acceptance/stage3/project_material_map_l0_v1.json",
        "picture_plan_v3": repo_root / ".tmp/canon67_540s_route_acceptance/stage5/l1_revision_v3/l1_picture_plan_v3.proposed.json",
        "teacher_decision": repo_root / "docs/decisions/2026-07-14-canon67-teacher-all-or-none-memory-ending.md",
    }


def build_canon67_seed(repo_root: Path) -> tuple[dict, list]:
    repo_root = Path(repo_root).resolve()
    paths = _canon67_source_paths(repo_root)
    for path in paths.values():
        if not path.is_file():
            raise EditorialStateError("canon67_source_missing", "required Canon 67 source is missing: " + str(path))
    blueprint = _load_json(paths["story_soul_blueprint"])
    screenplay = _load_json(paths["screenplay_beats"])
    material_map = _load_json(paths["material_map"])
    plan = _load_json(paths["picture_plan_v3"])
    teacher_text = paths["teacher_decision"].read_text(encoding="utf-8")
    if "13/13" not in teacher_text and "all-or-none" not in teacher_text:
        raise EditorialStateError("canon67_source_mismatch", "teacher decision does not contain the accepted roster rule")

    blueprint_by_segment = {}
    for beat in blueprint.get("beats", []):
        beat_id = beat.get("id", "")
        if beat_id.startswith("b"):
            segment_id = "seg" + beat_id[1:3] + "_" + beat_id[4:]
            blueprint_by_segment[segment_id] = beat
    screenplay_by_id = {beat.get("beat_id"): beat for beat in screenplay.get("beats", [])}
    clips_by_segment = {}
    for clip in plan.get("clips", []):
        clips_by_segment.setdefault(clip.get("segment"), []).append(clip)
    sections = plan.get("sections", [])
    segment_order = [section.get("segment") for section in sections]
    calibrated_segments = {
        "seg01_time_moves_people_begin",
        "seg02_first_gathering",
    }
    family_segments = {}
    segment_records = {}
    for section in sections:
        segment_id = section.get("segment")
        beat = blueprint_by_segment.get(segment_id, {})
        screenplay_beat = screenplay_by_id.get("b" + segment_id[3:], {})
        clips = clips_by_segment.get(segment_id, [])
        movement = str(beat.get("emotional_movement", "unknown"))
        movement_parts = movement.split("到", 1)
        windows = []
        families = []
        for clip in clips:
            window = {
                "clip_id": clip.get("clip_id"),
                "asset_id": clip.get("asset_id"),
                "source_path": clip.get("source_path"),
                "source_sha256": clip.get("source_sha256"),
                "start_sec": clip.get("start_sec"),
                "duration_sec": clip.get("planned_duration_sec", clip.get("duration_sec")),
                "window_evidence": copy.deepcopy(clip.get("window_evidence", {})),
            }
            windows.append(window)
            family = clip.get("visual_family")
            if family and family not in families:
                families.append(family)
                family_segments.setdefault(family, []).append(segment_id)
        status = section.get("status")
        if segment_id in calibrated_segments and windows and status != "deferred_all_or_none":
            completeness = "PASS"
            reason = "direct v3 source windows and resolved story function"
        elif status == "deferred_all_or_none":
            completeness = "UNKNOWN"
            reason = "deferred_due_to_incomplete_all_or_none_roster"
        else:
            completeness = "UNKNOWN"
            reason = "not_calibrated_in_v0_forward_test"
        segment_records[segment_id] = {
            "factual_purpose": beat.get("summary") or screenplay_beat.get("story_function"),
            "story_function": section.get("story_function") or beat.get("story_function"),
            "entry_state": movement_parts[0],
            "exit_state": movement_parts[-1],
            "new_information": beat.get("conflict_or_turn") or screenplay_beat.get("story_function"),
            "source_window_refs": windows,
            "review_caption": beat.get("review_caption_draft"),
            "selected_visual_families": sorted(families),
            "reuse_justifications": [
                {"visual_family": family, "reason": "v3 plan selected direct story evidence"}
                for family in sorted(families)
            ],
            "cross_segment_repetition_risks": [],
            "decision_completeness": completeness,
            "decision_reason": reason,
        }
    for segment_id, record in segment_records.items():
        risks = []
        for family in record["selected_visual_families"]:
            others = sorted(set(family_segments.get(family, [])) - {segment_id})
            if others:
                risks.append({"visual_family": family, "other_segments": others})
        record["cross_segment_repetition_risks"] = risks

    source_artifacts = [
        {"role": role, "path": _relative_or_absolute(path, repo_root), "sha256": hash_file(path)}
        for role, path in paths.items()
    ]
    story_world = blueprint.get("story_world", {})
    creative = blueprint.get("creative_concept", {})
    seed = {
        "material_context": {
            "material_origin": "curated",
            "annotation_state": "unannotated",
            "intent_notes_available": False,
            "known_input_limits": [
                "Canon 67 source package was pre-curated and has no capture-intent notes",
                "teacher/adviser coverage is deferred until a complete 13/13 roster exists",
            ],
        },
        "operational_state": {
            "segment_order": segment_order,
            "segments": segment_records,
            "coverage_ledger": {
                "teacher_adviser_sequence": {
                    "status": "deferred_due_to_incomplete_all_or_none_roster",
                    "required_roster_count": 13,
                    "reason": "complete owner-approved roster and evidence packet are not available",
                    "decision_artifact": source_artifacts[-1],
                }
            },
            "visual_family_ledger": {key: sorted(set(value)) for key, value in family_segments.items()},
            "people_ledger": {
                "collective_protagonist": story_world.get("collective_protagonist"),
                "human_witnesses": story_world.get("human_witnesses", []),
                "fact_boundary": story_world.get("fact_boundary"),
            },
            "motif_ledger": {
                "thesis_anchor": blueprint.get("thesis_anchor"),
                "visual_motifs": creative.get("visual_motifs", []),
                "anti_motifs": creative.get("anti_motifs", []),
            },
        },
        "editorial_intent": {
            "enforceable": False,
            "thesis": blueprint.get("thesis"),
            "logline": blueprint.get("logline"),
            "motif_guidance": creative.get("visual_motifs", []),
            "entry_intent": (blueprint.get("beats") or [{}])[0].get("summary"),
            "exit_intent": (blueprint.get("beats") or [{}])[-1].get("summary"),
        },
        "open_story_risks": [
            {
                "risk_id": "full_candidate_creative_quality",
                "status": "UNKNOWN",
                "reason": "current evidence is a Stage 5 proposal; no full candidate is certified",
            }
        ],
        "retired_story_intents": [],
        "verification_state": {
            "focused_tests": {
                "status": "UNKNOWN",
                "evidence": [],
                "reason": "focused verification is recorded by the operator after implementation",
            },
            "full_suite": {
                "status": "STALE",
                "last_green_count": 2786,
                "evidence_path": "docs/hermes-v-pipeline-honest-capability-map.md#16",
                "stale_because": "the historical green run predates the current CapCut backend patch and dirty-tree changes",
            },
        },
    }
    return seed, source_artifacts
