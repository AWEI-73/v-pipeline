"""Build and write visual_selection_review.json decisions."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from video_pipeline_core.reviewer_registry import sign_review
from video_pipeline_core.visual_selection_gate import (
    ACCEPTED_REVIEWERS,
    NEWCOMER_BASIC_BEATS,
    TOKEN_ONLY_SOURCES,
    evaluate_visual_selection_gate,
)


SUPPORTED_DECISIONS = {"accepted", "rejected", "needs_repick"}


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def _text(value: Any) -> str:
    return str(value or "").strip()


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _candidate_items(candidates: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw = candidates.get("selections") or candidates.get("items") or candidates.get("visual_selections")
    return [item for item in _as_list(raw) if isinstance(item, dict)]


def _beat_id(item: Mapping[str, Any]) -> str:
    return _text(item.get("beat_id") or item.get("module_id") or item.get("section_id"))


def _source_relative_path(item: Mapping[str, Any]) -> str:
    return _text(item.get("source_relative_path") or item.get("path") or item.get("asset"))


def _has_visual_evidence(item: Mapping[str, Any]) -> bool:
    if _text(item.get("representative_frame")):
        return True
    if _text(item.get("contact_sheet")):
        return True
    if _text(item.get("frame_evidence_ref")):
        return True
    return bool(_as_list(item.get("frames")) or _as_list(item.get("frame_refs")))


def _forbidden_flags(item: Mapping[str, Any]) -> dict[str, Any]:
    flags = item.get("forbidden_role_flags")
    return dict(flags) if isinstance(flags, Mapping) else {}


def _validate_decision(item: Mapping[str, Any]) -> None:
    beat = _beat_id(item)
    decision = _text(item.get("decision") or item.get("visual_confirmation_status")).casefold()
    reviewer = _text(item.get("reviewer_type") or item.get("reviewer")).casefold()
    reason = _text(item.get("reason") or item.get("note"))
    if decision not in SUPPORTED_DECISIONS:
        raise ValueError(f"unsupported visual selection decision for {beat}: {decision}")
    if reviewer not in ACCEPTED_REVIEWERS:
        raise ValueError(f"visual selection decision for {beat} requires reviewer_type human, agent_visual_review, or deterministic_probe")
    if not reason:
        raise ValueError(f"visual selection decision for {beat} requires reason")

    if decision in {"rejected", "needs_repick"}:
        return

    source = _text(item.get("candidate_source") or item.get("selection_source")).casefold()
    if not source or source in TOKEN_ONLY_SOURCES or item.get("token_only") is True:
        raise ValueError(f"accepted visual selection for {beat} requires non-token candidate_source")
    if not _has_visual_evidence(item):
        raise ValueError(f"accepted visual selection for {beat} requires representative frame, contact sheet, or frame evidence ref")
    if item.get("forbidden_role_flags_checked") is not True:
        raise ValueError(f"accepted visual selection for {beat} requires forbidden-role flag checks")
    flags = _forbidden_flags(item)
    if beat in NEWCOMER_BASIC_BEATS and any(bool(flags.get(name)) for name in ("supervisor_primary", "director_primary", "portrait_primary")):
        raise ValueError(f"accepted {beat} selection cannot mark supervisor/director/portrait as primary visual")
    if beat == "supervisor_source_speech":
        if not (item.get("video_evidence") is True and item.get("audio_evidence") is True and item.get("speech_evidence") is True):
            raise ValueError("accepted supervisor_source_speech requires video, audio, and speech evidence")


def build_visual_selection_review(
    candidates: Mapping[str, Any],
    decisions: list[Mapping[str, Any]],
    *,
    created_at: str = "",
) -> dict[str, Any]:
    candidate_by_beat = {_beat_id(item): item for item in _candidate_items(candidates) if _beat_id(item)}
    review_items: list[dict[str, Any]] = []
    for decision in decisions:
        beat = _beat_id(decision)
        if not beat:
            raise ValueError("visual selection decision requires beat_id")
        candidate = candidate_by_beat.get(beat, {})
        item = {
            "beat_id": beat,
            "source_relative_path": _source_relative_path(decision) or _source_relative_path(candidate),
            "candidate_source": decision.get("candidate_source") or decision.get("selection_source") or "agent_visual_review",
            "visual_confirmation_status": _text(decision.get("decision") or decision.get("visual_confirmation_status")).casefold(),
            "reviewer_type": decision.get("reviewer_type") or decision.get("reviewer"),
            "reason": decision.get("reason") or decision.get("note"),
            "representative_frame": decision.get("representative_frame") or decision.get("frame"),
            "contact_sheet": decision.get("contact_sheet"),
            "frame_evidence_ref": decision.get("frame_evidence_ref"),
            "forbidden_role_flags_checked": decision.get("forbidden_role_flags_checked") is True,
            "forbidden_role_flags": _forbidden_flags(decision),
            "video_evidence": decision.get("video_evidence") is True,
            "audio_evidence": decision.get("audio_evidence") is True,
            "speech_evidence": decision.get("speech_evidence") is True,
        }
        _validate_decision(item)
        review_items.append(item)
    summary = {
        "reviewed_count": len(review_items),
        "accepted_count": sum(1 for item in review_items if item["visual_confirmation_status"] == "accepted"),
        "rejected_count": sum(1 for item in review_items if item["visual_confirmation_status"] == "rejected"),
        "needs_repick_count": sum(1 for item in review_items if item["visual_confirmation_status"] == "needs_repick"),
    }
    result = {
        "artifact_role": "visual_selection_review",
        "version": 1,
        "created_at": created_at or _now_iso(),
        "is_final_story_approval": False,
        "is_legal_music_approval": False,
        "selections": review_items,
        "summary": summary,
    }
    result["review_signature"] = sign_review(
        "visual_selection_reviewer",
        passed=summary["rejected_count"] == 0 and summary["needs_repick_count"] == 0,
        findings=[item for item in review_items if item["visual_confirmation_status"] in {"rejected", "needs_repick"}],
    )
    return result


def write_visual_selection_review(
    candidates: Mapping[str, Any],
    decisions: list[Mapping[str, Any]],
    out_dir: str | Path,
    *,
    created_at: str = "",
) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    review = build_visual_selection_review(candidates, decisions, created_at=created_at)
    gate = evaluate_visual_selection_gate(review)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    review_path = out / "visual_selection_review.json"
    gate_path = out / "visual_selection_gate.json"
    review_path.write_text(json.dumps(review, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    gate_path.write_text(json.dumps(gate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return review_path, review, gate
