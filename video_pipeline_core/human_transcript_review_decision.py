"""Contract for human transcript review decision artifacts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


DECISIONS = {"approved", "revision_requested", "rejected"}


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


def build_human_transcript_review_decision(payload: Mapping[str, Any]) -> dict[str, Any]:
    decision = _text(payload.get("decision"))
    reviewer = _text(payload.get("reviewer") or payload.get("reviewer_type"))
    notes = [_text(item) for item in _as_list(payload.get("notes") or payload.get("note")) if _text(item)]
    reviewed_draft = _text(payload.get("reviewed_draft") or payload.get("draft_subtitles"))
    reviewed_cue_ids = [_text(item) for item in _as_list(payload.get("reviewed_cue_ids")) if _text(item)]

    if decision not in DECISIONS:
        raise ValueError(f"unsupported transcript review decision: {decision}")
    if reviewer.casefold() != "human":
        raise ValueError("human transcript review decision requires reviewer=human")
    if decision == "approved":
        if not reviewed_draft:
            raise ValueError("approved transcript review requires reviewed draft path")
        if not reviewed_cue_ids:
            raise ValueError("approved transcript review requires reviewed cue ids")
    elif not notes:
        raise ValueError(f"{decision} transcript review requires at least one note")

    return {
        "artifact_role": "human_transcript_review_decision",
        "version": 1,
        "decision": decision,
        "reviewer": "human",
        "reviewed_draft": reviewed_draft,
        "reviewed_cue_ids": reviewed_cue_ids,
        "notes": notes,
        "clears_human_transcript_review": decision == "approved",
        "created_at": _text(payload.get("created_at")) or _now_iso(),
    }


def write_human_transcript_review_decision_for_run(
    run: str | Path,
    payload: Mapping[str, Any],
    out_name: str = "human_transcript_review_decision.json",
) -> dict[str, Any]:
    out_path = Path(run) / out_name
    decision = build_human_transcript_review_decision(payload)
    out_path.write_text(json.dumps(decision, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    decision["path"] = str(out_path)
    return decision
