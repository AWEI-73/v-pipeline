"""Validate the evidence-carrying Stage 0-2 editorial ambiguity package.

The package is authored by an agent following ``editorial-ambiguity-loop``.
This module does not create story content or judge taste.  It only checks that
the accepted story decision, segment grammar, and evidence needs are complete,
cross-bound, and safe to hand to Stage 3.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
STORY_ROLE = "upstream_story_decision_packet"
SEGMENT_ROLE = "segment_story_contract"
EVIDENCE_ROLE = "evidence_need_map"

DECISION_MODES = {"single", "ab_comparison", "delegated"}
DECISION_STATUSES = {"accepted"}
DECISION_OWNERS = {"owner", "agent_delegated"}
UNKNOWN_IMPACTS = {"route_changing", "structural", "local"}
UNKNOWN_STATUSES = {"open", "resolved", "deferred"}
STAGE2_STATUSES = {"accepted"}
MATERIAL_TRUTH_STATUSES = {"not_started", "inventory_only", "reviewed"}
EVIDENCE_KINDS = {"visual", "speech", "text", "mixed"}
NEED_STATUSES = {"needed", "available_unverified", "verified", "deferred_due_to_material"}
MATERIAL_DEFER_REASONS = {"not_found", "not_present", "present_unusable", "excluded_by_policy"}

# A non-empty string is not necessarily a carried decision. Small workers can
# satisfy the shape contract with a generic sentence, so reject that before
# the package becomes a Stage 3 story contract.
_PLACEHOLDER_PATTERNS = (
    re.compile(r"owner[- ]approved\s+evidence\s+statement", re.IGNORECASE),
    re.compile(r"\b(?:tbd|todo|placeholder|fill\s+me|to\s+be\s+decided)\b", re.IGNORECASE),
)

DECISION_FIELDS = {
    "decision",
    "decision_reason",
    "evidence_refs",
    "owner_or_agent",
    "status",
    "remaining_unknowns",
    "allowed_downstream_interpretation",
}

SEGMENT_FIELDS = {
    "segment_id",
    "factual_claim",
    "story_change",
    "entry_state",
    "exit_state",
    "required_picture_roles",
    "allowed_source_families",
    "forbidden_substitutions",
    "minimum_unique_windows",
    "duration_policy",
    "transition_in",
    "transition_out",
    "title_card_role",
    "defer_or_shorten_rule",
    "review_question",
    "evidence_refs",
    "decision_record",
}

NEED_FIELDS = {
    "need_id",
    "segment_id",
    "picture_role",
    "factual_claim",
    "evidence_kind",
    "required_observation",
    "allowed_source_families",
    "forbidden_substitutions",
    "status",
    "evidence_refs",
}


class EditorialAmbiguityError(ValueError):
    """Input cannot be loaded as a Stage 0-2 ambiguity artifact."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_object(path: Path) -> dict[str, Any]:
    path = Path(path)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EditorialAmbiguityError("invalid_json", "cannot read JSON object: " + str(path)) from exc
    if not isinstance(value, dict):
        raise EditorialAmbiguityError("invalid_json_shape", "JSON root must be an object: " + str(path))
    return value


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _meaningful_text(value: Any) -> bool:
    """Return true only when a required semantic field carries content."""

    if not _text(value):
        return False
    text = str(value).strip()
    return not any(pattern.search(text) for pattern in _PLACEHOLDER_PATTERNS)


def _string_list(value: Any, *, allow_empty: bool = False) -> bool:
    return (
        isinstance(value, list)
        and (allow_empty or bool(value))
        and all(_text(item) for item in value)
    )


def _error(errors: list[dict[str, str]], code: str, location: str, message: str) -> None:
    errors.append({"code": code, "location": location, "message": message})


def _validate_role_and_version(
    value: dict[str, Any],
    *,
    role: str,
    location: str,
    errors: list[dict[str, str]],
) -> None:
    if value.get("artifact_role") != role:
        _error(errors, "invalid_artifact_role", location, "expected artifact_role=" + role)
    if value.get("schema_version") != SCHEMA_VERSION:
        _error(errors, "unsupported_schema_version", location, "expected schema_version=1")


def _resolve_ref(ref: dict[str, Any], owner_path: Path) -> Path | None:
    if not isinstance(ref, dict) or not _text(ref.get("path")):
        return None
    path = Path(ref["path"])
    if path.is_absolute():
        return path
    return owner_path.parent / path


def _validate_ref(
    ref: Any,
    *,
    expected_path: Path,
    owner_path: Path,
    code: str,
    location: str,
    errors: list[dict[str, str]],
) -> None:
    if not isinstance(ref, dict) or not _text(ref.get("path")) or not _text(ref.get("sha256")):
        _error(errors, code, location, "reference requires path and sha256")
        return
    resolved = _resolve_ref(ref, owner_path)
    if resolved is None or resolved.resolve() != expected_path.resolve():
        _error(errors, code, location, "reference path does not resolve to the supplied artifact")
        return
    if not expected_path.is_file() or ref["sha256"] != hash_file(expected_path):
        _error(errors, code, location, "reference hash does not match the supplied artifact")


def _validate_decision_record(
    record: Any,
    *,
    location: str,
    errors: list[dict[str, str]],
) -> None:
    if not isinstance(record, dict):
        _error(errors, "invalid_decision_record", location, "decision_record must be an object")
        return
    missing = sorted(DECISION_FIELDS - set(record))
    if missing:
        _error(errors, "incomplete_decision_record", location, "missing: " + ",".join(missing))
    for field in ("decision", "decision_reason", "allowed_downstream_interpretation"):
        if not _meaningful_text(record.get(field)):
            _error(errors, "incomplete_decision_record", location + "." + field, "field must be non-empty")
    if not _string_list(record.get("evidence_refs"), allow_empty=False):
        _error(errors, "decision_without_evidence", location + ".evidence_refs", "accepted decision requires evidence refs")
    if record.get("owner_or_agent") not in DECISION_OWNERS:
        _error(errors, "invalid_decision_owner", location + ".owner_or_agent", "owner must be owner or agent_delegated")
    if record.get("status") not in DECISION_STATUSES:
        _error(errors, "decision_not_accepted", location + ".status", "Stage 2 handoff requires accepted decisions")
    if not isinstance(record.get("remaining_unknowns"), list):
        _error(errors, "invalid_decision_record", location + ".remaining_unknowns", "must be a list")
    if record.get("owner_or_agent") == "agent_delegated" and not _text(record.get("delegation_scope")):
        _error(errors, "delegation_scope_missing", location, "delegated agent decision requires delegation_scope")


def _validate_story(
    story: dict[str, Any],
    story_path: Path,
    errors: list[dict[str, str]],
) -> None:
    _validate_role_and_version(story, role=STORY_ROLE, location="story_decision", errors=errors)
    if not _text(story.get("project_id")):
        _error(errors, "project_id_missing", "story_decision.project_id", "project_id is required")

    stage0_ref = story.get("stage0_intent_ref")
    stage0_path = _resolve_ref(stage0_ref, story_path) if isinstance(stage0_ref, dict) else None
    if stage0_path is None or not stage0_path.is_file():
        _error(errors, "stage0_intent_ref_invalid", "story_decision.stage0_intent_ref", "Stage 0 intent artifact is missing")
    elif stage0_ref.get("sha256") != hash_file(stage0_path):
        _error(errors, "stage0_intent_hash_mismatch", "story_decision.stage0_intent_ref", "Stage 0 intent hash mismatch")

    mode = story.get("decision_mode")
    if mode not in DECISION_MODES:
        _error(errors, "invalid_decision_mode", "story_decision.decision_mode", "unsupported decision mode")
    hypotheses = story.get("hypotheses")
    if not isinstance(hypotheses, list) or not hypotheses:
        _error(errors, "hypotheses_missing", "story_decision.hypotheses", "at least one story hypothesis is required")
        hypotheses = []
    hypothesis_ids: list[str] = []
    causal_promises: list[str] = []
    for index, hypothesis in enumerate(hypotheses):
        location = "story_decision.hypotheses[{}]".format(index)
        if not isinstance(hypothesis, dict):
            _error(errors, "invalid_hypothesis", location, "hypothesis must be an object")
            continue
        for field in ("hypothesis_id", "thesis", "causal_promise"):
            if not _meaningful_text(hypothesis.get(field)):
                _error(errors, "incomplete_hypothesis", location + "." + field, "field must be non-empty")
        for field in ("material_assumptions", "sacrifices", "evidence_refs"):
            if not _string_list(hypothesis.get(field), allow_empty=False):
                _error(errors, "incomplete_hypothesis", location + "." + field, "field must be a non-empty string list")
        if _text(hypothesis.get("hypothesis_id")):
            hypothesis_ids.append(hypothesis["hypothesis_id"])
        if _text(hypothesis.get("causal_promise")):
            causal_promises.append(hypothesis["causal_promise"].strip().casefold())
    if len(hypothesis_ids) != len(set(hypothesis_ids)):
        _error(errors, "duplicate_hypothesis_id", "story_decision.hypotheses", "hypothesis ids must be unique")
    if mode == "ab_comparison":
        if len(hypotheses) < 2:
            _error(errors, "ab_options_missing", "story_decision.hypotheses", "A/B comparison requires at least two options")
        if causal_promises and len(causal_promises) != len(set(causal_promises)):
            _error(errors, "ab_options_not_distinct", "story_decision.hypotheses", "A/B options must have materially distinct causal promises")
    if mode == "single" and not _text(story.get("single_option_waiver")):
        _error(errors, "single_option_waiver_missing", "story_decision.single_option_waiver", "single mode requires a reason A/B is unnecessary")
    selected = story.get("selected_hypothesis_id")
    if selected not in hypothesis_ids:
        _error(errors, "selected_hypothesis_invalid", "story_decision.selected_hypothesis_id", "selected hypothesis does not exist")
    _validate_decision_record(story.get("decision_record"), location="story_decision.decision_record", errors=errors)

    narrative = story.get("narrative_contract")
    if not isinstance(narrative, dict):
        _error(errors, "narrative_contract_missing", "story_decision.narrative_contract", "narrative contract is required")
    else:
        for field in ("subject", "audience_change", "thesis"):
            if not _meaningful_text(narrative.get(field)):
                _error(errors, "narrative_contract_incomplete", "story_decision.narrative_contract." + field, "field must be non-empty")
        arc = narrative.get("causal_arc")
        if not isinstance(arc, list) or not arc:
            _error(errors, "causal_arc_missing", "story_decision.narrative_contract.causal_arc", "causal arc is required")
        else:
            beat_ids: list[str] = []
            for index, beat in enumerate(arc):
                location = "story_decision.narrative_contract.causal_arc[{}]".format(index)
                if not isinstance(beat, dict):
                    _error(errors, "invalid_causal_beat", location, "causal beat must be an object")
                    continue
                for field in ("beat_id", "factual_claim", "story_change", "entry_state", "exit_state"):
                    if not _meaningful_text(beat.get(field)):
                        _error(errors, "incomplete_causal_beat", location + "." + field, "field must be non-empty")
                if not _string_list(beat.get("evidence_refs"), allow_empty=False):
                    _error(errors, "causal_beat_without_evidence", location + ".evidence_refs", "causal beat requires evidence refs")
                if _text(beat.get("beat_id")):
                    beat_ids.append(beat["beat_id"])
            if len(beat_ids) != len(set(beat_ids)):
                _error(errors, "duplicate_beat_id", "story_decision.narrative_contract.causal_arc", "beat ids must be unique")

    unknowns = story.get("remaining_unknowns")
    if not isinstance(unknowns, list):
        _error(errors, "remaining_unknowns_invalid", "story_decision.remaining_unknowns", "remaining_unknowns must be a list")
    else:
        for index, unknown in enumerate(unknowns):
            location = "story_decision.remaining_unknowns[{}]".format(index)
            if not isinstance(unknown, dict):
                _error(errors, "invalid_unknown", location, "unknown must be an object")
                continue
            for field in ("unknown_id", "question", "owner_or_agent"):
                if not _meaningful_text(unknown.get(field)):
                    _error(errors, "invalid_unknown", location + "." + field, "field must be non-empty")
            if unknown.get("route_impact") not in UNKNOWN_IMPACTS:
                _error(errors, "invalid_unknown_impact", location + ".route_impact", "invalid route impact")
            if unknown.get("status") not in UNKNOWN_STATUSES:
                _error(errors, "invalid_unknown_status", location + ".status", "invalid unknown status")
            if unknown.get("status") == "open" and unknown.get("route_impact") in {"route_changing", "structural"}:
                _error(errors, "unresolved_high_impact_unknown", location, "route-changing or structural unknown must be resolved before Stage 3")
            if unknown.get("status") in {"resolved", "deferred"} and not _text(unknown.get("resolution")):
                _error(errors, "unknown_resolution_missing", location + ".resolution", "resolved/deferred unknown requires resolution")
    for field in ("retired_story_intents", "deferred_due_to_material"):
        if not isinstance(story.get(field), list):
            _error(errors, "invalid_story_ledger", "story_decision." + field, "field must be a list")


def _validate_segments(
    contract: dict[str, Any],
    errors: list[dict[str, str]],
) -> dict[str, set[str]]:
    _validate_role_and_version(contract, role=SEGMENT_ROLE, location="segment_contract", errors=errors)
    if contract.get("stage2_status") not in STAGE2_STATUSES:
        _error(errors, "stage2_not_accepted", "segment_contract.stage2_status", "Stage 2 status must be accepted")
    segments = contract.get("segments")
    if not isinstance(segments, list) or not segments:
        _error(errors, "segments_missing", "segment_contract.segments", "at least one segment is required")
        return {}
    segment_roles: dict[str, set[str]] = {}
    for index, segment in enumerate(segments):
        location = "segment_contract.segments[{}]".format(index)
        if not isinstance(segment, dict):
            _error(errors, "invalid_segment", location, "segment must be an object")
            continue
        missing = sorted(SEGMENT_FIELDS - set(segment))
        if missing:
            _error(errors, "incomplete_segment_contract", location, "missing: " + ",".join(missing))
        for field in (
            "segment_id", "factual_claim", "story_change", "entry_state", "exit_state",
            "title_card_role", "defer_or_shorten_rule", "review_question",
        ):
            if not _meaningful_text(segment.get(field)):
                _error(errors, "incomplete_segment_contract", location + "." + field, "field must be non-empty")
        for field in ("required_picture_roles", "allowed_source_families", "forbidden_substitutions", "evidence_refs"):
            if not _string_list(segment.get(field), allow_empty=False):
                _error(errors, "incomplete_segment_contract", location + "." + field, "field must be a non-empty string list")
        segment_id = segment.get("segment_id")
        roles = segment.get("required_picture_roles") if isinstance(segment.get("required_picture_roles"), list) else []
        if _text(segment_id):
            if segment_id in segment_roles:
                _error(errors, "duplicate_segment_id", location + ".segment_id", "segment id must be unique")
            segment_roles[segment_id] = {role for role in roles if _text(role)}
        if len(roles) != len(set(roles)):
            _error(errors, "duplicate_picture_role", location + ".required_picture_roles", "picture roles must be unique")
        minimum = segment.get("minimum_unique_windows")
        if not isinstance(minimum, int) or isinstance(minimum, bool) or minimum < 1:
            _error(errors, "invalid_minimum_unique_windows", location + ".minimum_unique_windows", "must be an integer >= 1")
        duration = segment.get("duration_policy")
        if not isinstance(duration, dict):
            _error(errors, "invalid_duration_policy", location + ".duration_policy", "duration policy must be an object")
        else:
            values = [duration.get(name) for name in ("min_sec", "target_sec", "max_sec")]
            if not all(isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0 for value in values):
                _error(errors, "invalid_duration_policy", location + ".duration_policy", "min/target/max must be non-negative numbers")
            elif not (values[0] <= values[1] <= values[2]):
                _error(errors, "invalid_duration_policy", location + ".duration_policy", "expected min <= target <= max")
            if not isinstance(duration.get("shorten_if_material_short"), bool):
                _error(errors, "invalid_duration_policy", location + ".duration_policy.shorten_if_material_short", "field must be boolean")
        for field in ("transition_in", "transition_out"):
            transition = segment.get(field)
            if not isinstance(transition, dict) or not _text(transition.get("story_job")) or not _text(transition.get("continuity_rule")):
                _error(errors, "invalid_transition_contract", location + "." + field, "transition requires story_job and continuity_rule")
        _validate_decision_record(segment.get("decision_record"), location=location + ".decision_record", errors=errors)
    return segment_roles


def _validate_evidence(
    evidence: dict[str, Any],
    segment_roles: dict[str, set[str]],
    errors: list[dict[str, str]],
) -> None:
    _validate_role_and_version(evidence, role=EVIDENCE_ROLE, location="evidence_map", errors=errors)
    if evidence.get("material_truth_status") not in MATERIAL_TRUTH_STATUSES:
        _error(errors, "invalid_material_truth_status", "evidence_map.material_truth_status", "invalid material truth status")
    needs = evidence.get("needs")
    if not isinstance(needs, list) or not needs:
        _error(errors, "evidence_needs_missing", "evidence_map.needs", "at least one evidence need is required")
        return
    seen_need_ids: set[str] = set()
    covered_roles: dict[str, set[str]] = {segment_id: set() for segment_id in segment_roles}
    for index, need in enumerate(needs):
        location = "evidence_map.needs[{}]".format(index)
        if not isinstance(need, dict):
            _error(errors, "invalid_evidence_need", location, "evidence need must be an object")
            continue
        missing = sorted(NEED_FIELDS - set(need))
        if missing:
            _error(errors, "incomplete_evidence_need", location, "missing: " + ",".join(missing))
        for field in ("need_id", "segment_id", "picture_role", "factual_claim", "required_observation"):
            if not _meaningful_text(need.get(field)):
                _error(errors, "incomplete_evidence_need", location + "." + field, "field must be non-empty")
        for field in ("allowed_source_families", "forbidden_substitutions"):
            if not _string_list(need.get(field), allow_empty=False):
                _error(errors, "incomplete_evidence_need", location + "." + field, "field must be a non-empty string list")
        if not isinstance(need.get("evidence_refs"), list):
            _error(errors, "incomplete_evidence_need", location + ".evidence_refs", "field must be a list")
        need_id = need.get("need_id")
        if _text(need_id):
            if need_id in seen_need_ids:
                _error(errors, "duplicate_need_id", location + ".need_id", "need id must be unique")
            seen_need_ids.add(need_id)
        segment_id = need.get("segment_id")
        picture_role = need.get("picture_role")
        if segment_id not in segment_roles:
            _error(errors, "unknown_evidence_segment", location + ".segment_id", "need references unknown segment")
        elif picture_role not in segment_roles[segment_id]:
            _error(errors, "unknown_picture_role", location + ".picture_role", "need references a role not required by its segment")
        else:
            covered_roles[segment_id].add(picture_role)
        if need.get("evidence_kind") not in EVIDENCE_KINDS:
            _error(errors, "invalid_evidence_kind", location + ".evidence_kind", "unsupported evidence kind")
        status = need.get("status")
        if status not in NEED_STATUSES:
            _error(errors, "invalid_evidence_status", location + ".status", "unsupported evidence status")
        if status == "verified" and not _string_list(need.get("evidence_refs"), allow_empty=False):
            _error(errors, "verified_need_without_evidence", location + ".evidence_refs", "verified need requires evidence refs")
        if status == "deferred_due_to_material":
            defer = need.get("material_defer")
            if not isinstance(defer, dict):
                _error(errors, "material_defer_missing", location + ".material_defer", "material defer details are required")
            else:
                if defer.get("reason") not in MATERIAL_DEFER_REASONS:
                    _error(errors, "invalid_material_defer_reason", location + ".material_defer.reason", "invalid material defer reason")
                if defer.get("owner_confirmed") is not True:
                    _error(errors, "unconfirmed_material_defer", location + ".material_defer.owner_confirmed", "material ceiling must be owner-confirmed")
                if not _string_list(defer.get("evidence_refs"), allow_empty=False):
                    _error(errors, "material_defer_without_evidence", location + ".material_defer.evidence_refs", "material defer requires evidence refs")
    for segment_id, roles in segment_roles.items():
        for role in sorted(roles - covered_roles.get(segment_id, set())):
            _error(
                errors,
                "picture_role_without_evidence_need",
                "segment_contract.segments[{}].required_picture_roles".format(segment_id),
                "missing evidence need for picture role: " + role,
            )


def _validate_segment_need_bindings(
    contract: dict[str, Any],
    evidence: dict[str, Any],
    errors: list[dict[str, str]],
) -> None:
    """Reject dangling evidence-need IDs without treating file refs as need IDs."""

    need_ids = {
        need.get("need_id")
        for need in evidence.get("needs") or []
        if isinstance(need, dict) and _text(need.get("need_id"))
    }
    for index, segment in enumerate(contract.get("segments") or []):
        if not isinstance(segment, dict):
            continue
        for ref in segment.get("evidence_refs") or []:
            if not isinstance(ref, str) or not re.fullmatch(r"N_[A-Za-z0-9_:-]+", ref):
                continue
            if ref not in need_ids:
                _error(
                    errors,
                    "segment_evidence_need_ref_missing",
                    "segment_contract.segments[{}].evidence_refs".format(index),
                    "segment references an evidence need absent from evidence_map.needs: " + ref,
                )


def validate_package(
    story_decision_path: Path,
    segment_contract_path: Path,
    evidence_map_path: Path,
) -> dict[str, Any]:
    """Return a deterministic Stage 2 completion report."""

    story_path = Path(story_decision_path).resolve()
    segment_path = Path(segment_contract_path).resolve()
    evidence_path = Path(evidence_map_path).resolve()
    story = _load_object(story_path)
    segment = _load_object(segment_path)
    evidence = _load_object(evidence_path)
    errors: list[dict[str, str]] = []

    _validate_story(story, story_path, errors)
    project_ids = [story.get("project_id"), segment.get("project_id"), evidence.get("project_id")]
    if not all(_text(value) for value in project_ids) or len(set(project_ids)) != 1:
        _error(errors, "project_id_mismatch", "package", "all three artifacts must share one project_id")
    _validate_ref(
        segment.get("story_decision_ref"),
        expected_path=story_path,
        owner_path=segment_path,
        code="story_decision_hash_mismatch",
        location="segment_contract.story_decision_ref",
        errors=errors,
    )
    _validate_ref(
        evidence.get("story_decision_ref"),
        expected_path=story_path,
        owner_path=evidence_path,
        code="story_decision_hash_mismatch",
        location="evidence_map.story_decision_ref",
        errors=errors,
    )
    _validate_ref(
        evidence.get("segment_contract_ref"),
        expected_path=segment_path,
        owner_path=evidence_path,
        code="segment_contract_hash_mismatch",
        location="evidence_map.segment_contract_ref",
        errors=errors,
    )
    segment_roles = _validate_segments(segment, errors)
    _validate_evidence(evidence, segment_roles, errors)
    _validate_segment_need_bindings(segment, evidence, errors)

    ok = not errors
    return {
        "artifact_role": "stage2_ambiguity_gate_report",
        "schema_version": SCHEMA_VERSION,
        "ok": ok,
        "stage2_completion": "PASS" if ok else "FAIL",
        "ready_for_stage3": ok,
        "project_id": story.get("project_id"),
        "inputs": {
            "story_decision": {"path": str(story_path), "sha256": hash_file(story_path)},
            "segment_contract": {"path": str(segment_path), "sha256": hash_file(segment_path)},
            "evidence_map": {"path": str(evidence_path), "sha256": hash_file(evidence_path)},
        },
        "counts": {
            "hypotheses": len(story.get("hypotheses") or []),
            "causal_beats": len((story.get("narrative_contract") or {}).get("causal_arc") or []),
            "segments": len(segment.get("segments") or []),
            "evidence_needs": len(evidence.get("needs") or []),
        },
        "errors": errors,
        "warnings": [],
        "claim_boundary": "PASS proves decision completeness and cross-artifact binding only; it does not prove material availability, story quality, render quality, creative approval, or delivery.",
    }
