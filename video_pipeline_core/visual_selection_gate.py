"""Render-facing visual selection confirmation gate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


SENSITIVE_BEATS = {
    "newcomer_training_start",
    "basic_training",
    "supervisor_source_speech",
    "teacher_class_intro",
    "opening_story",
    "closing_story",
}

TOKEN_ONLY_SOURCES = {
    "token_folder_match",
    "filename_or_folder_signal",
    "path_token_match",
    "folder_token_match",
}

ACCEPTED_REVIEWERS = {"human", "agent_visual_review", "deterministic_probe"}

NEWCOMER_BASIC_BEATS = {"newcomer_training_start", "basic_training"}


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def _text(value: Any) -> str:
    return str(value or "").strip()


def _source(value: Mapping[str, Any]) -> str:
    return _text(value.get("candidate_source") or value.get("selection_source")).casefold()


def _beat_id(value: Mapping[str, Any]) -> str:
    return _text(value.get("beat_id") or value.get("module_id") or value.get("section_id"))


def _selection_path(value: Mapping[str, Any]) -> str:
    return _text(value.get("source_relative_path") or value.get("path") or value.get("asset"))


def _has_visual_evidence(value: Mapping[str, Any]) -> bool:
    if _text(value.get("representative_frame")):
        return True
    if _text(value.get("contact_sheet")):
        return True
    if _text(value.get("frame_evidence_ref")):
        return True
    if isinstance(value.get("visual_evidence"), Mapping):
        evidence = value["visual_evidence"]
        return any(_text(evidence.get(key)) for key in ("representative_frame", "contact_sheet", "frame_evidence_ref"))
    return bool(_as_list(value.get("frames")) or _as_list(value.get("frame_refs")))


def _forbidden_flags(value: Mapping[str, Any]) -> Mapping[str, Any]:
    flags = value.get("forbidden_role_flags")
    return flags if isinstance(flags, Mapping) else {}


def _flag_true(flags: Mapping[str, Any], names: set[str]) -> bool:
    return any(bool(flags.get(name)) for name in names)


def _is_token_only(value: Mapping[str, Any]) -> bool:
    source = _source(value)
    if source in TOKEN_ONLY_SOURCES:
        return True
    return bool(value.get("token_only") is True or value.get("visual_confirmation_status") == "candidate_only")


def _selection_block(rule: str, selection: Mapping[str, Any], message: str, next_action: str = "run_visual_selection_review") -> dict[str, Any]:
    return {
        "rule": rule,
        "tier": 1,
        "beat_id": _beat_id(selection),
        "source_relative_path": _selection_path(selection),
        "message": message,
        "next_action": next_action,
    }


def _selections(payload: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(payload, Mapping):
        return []
    raw = payload.get("selections")
    if raw is None:
        raw = payload.get("visual_selections")
    if raw is None:
        raw = payload.get("items")
    return [item for item in _as_list(raw) if isinstance(item, dict)]


def evaluate_visual_selection_gate(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    """Evaluate render-facing visual selections.

    Token/folder/path matches are candidate evidence only. Sensitive beat
    selections must carry explicit visual confirmation before they can be used
    as render-facing accepted selections.
    """

    blocking: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    accepted_count = 0
    token_only_blocked: list[str] = []
    sensitive_seen: set[str] = set()

    for selection in _selections(payload):
        beat = _beat_id(selection)
        if beat not in SENSITIVE_BEATS:
            continue
        sensitive_seen.add(beat)
        status = _text(selection.get("visual_confirmation_status") or selection.get("status")).casefold()
        reviewer = _text(selection.get("reviewer_type") or selection.get("reviewer")).casefold()
        token_only = _is_token_only(selection)

        if token_only:
            token_only_blocked.append(beat)
            blocking.append(_selection_block(
                "token_only_selection_not_accepted",
                selection,
                "token/folder/path match is candidate evidence only and cannot be render-facing accepted selection",
            ))
        if status == "rejected":
            blocking.append(_selection_block(
                "visual_selection_rejected",
                selection,
                "visual selection review rejected this sensitive beat",
                "repick_visual_material",
            ))
            continue
        if status == "needs_repick":
            blocking.append(_selection_block(
                "visual_selection_needs_repick",
                selection,
                "visual selection review requires repick for this sensitive beat",
                "repick_visual_material",
            ))
            continue
        if status != "accepted" or reviewer not in ACCEPTED_REVIEWERS or not _has_visual_evidence(selection):
            blocking.append(_selection_block(
                "visual_confirmation_missing",
                selection,
                "sensitive beat requires accepted visual confirmation evidence before render-facing use",
            ))
        if not bool(selection.get("forbidden_role_flags_checked")):
            blocking.append(_selection_block(
                "forbidden_role_flags_not_checked",
                selection,
                "sensitive beat must record forbidden-role flag checks",
            ))
        flags = _forbidden_flags(selection)
        if beat in NEWCOMER_BASIC_BEATS and _flag_true(flags, {"supervisor_primary", "director_primary", "portrait_primary"}):
            blocking.append(_selection_block(
                "forbidden_primary_role_for_newcomer_or_basic",
                selection,
                "newcomer/basic selections cannot use supervisor/director/portrait as primary visual",
                "repick_visual_material",
            ))
        if beat == "supervisor_source_speech":
            if not (selection.get("video_evidence") is True and selection.get("audio_evidence") is True and selection.get("speech_evidence") is True):
                blocking.append(_selection_block(
                    "supervisor_source_speech_missing_audio_speech_evidence",
                    selection,
                    "supervisor source speech requires video plus audio/speech evidence",
                    "probe_supervisor_source_speech",
                ))
        if (
            status == "accepted"
            and reviewer in ACCEPTED_REVIEWERS
            and _has_visual_evidence(selection)
            and not token_only
        ):
            accepted_count += 1

    return {
        "artifact_role": "visual_selection_gate",
        "version": 1,
        "pass": not blocking,
        "blocking": blocking,
        "warnings": warnings,
        "sensitive_beats": sorted(SENSITIVE_BEATS),
        "sensitive_beats_seen": sorted(sensitive_seen),
        "blocked_token_only_selections": sorted(set(token_only_blocked)),
        "accepted_visual_evidence_count": accepted_count,
        "next_action": None if not blocking else blocking[0]["next_action"],
    }


def build_visual_selection_candidates_from_run(run: str | Path) -> dict[str, Any]:
    root = Path(run)
    items: list[dict[str, Any]] = []
    story_map = _load_json(root / "story_to_material_map.json") or {}
    for item in _as_list(story_map.get("items")):
        if not isinstance(item, dict):
            continue
        beat = _beat_id(item)
        if beat not in SENSITIVE_BEATS:
            continue
        items.append({
            "beat_id": beat,
            "source_relative_path": _selection_path(item),
            "candidate_source": item.get("candidate_source") or item.get("assignment_reason") or "token_folder_match",
            "visual_confirmation_status": item.get("visual_confirmation_status") or "candidate_only",
            "reviewer_type": item.get("reviewer_type") or "none",
            "reason": item.get("reason") or "run story/material map candidate requires explicit visual-selection review",
        })
    return {
        "artifact_role": "visual_selection_candidates",
        "version": 1,
        "run": str(root),
        "selections": items,
    }


def write_visual_selection_gate_for_run(run: str | Path, out_dir: str | Path) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    root = Path(run)
    candidates = build_visual_selection_candidates_from_run(root)
    review = _load_json(root / "visual_selection_review.json")
    evaluated_payload = review if isinstance(review, Mapping) else candidates
    report = evaluate_visual_selection_gate(evaluated_payload)
    report["run"] = str(root)
    report["input_artifact"] = "visual_selection_review.json" if isinstance(review, Mapping) else "visual_selection_candidates.json"
    (out / "visual_selection_candidates.json").write_text(
        json.dumps(candidates, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out / "visual_selection_gate.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None
