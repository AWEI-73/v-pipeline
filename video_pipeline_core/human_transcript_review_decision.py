"""Contract for human transcript review decision artifacts."""

from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


DECISIONS = {"approved", "revision_requested", "rejected"}
SHA256_RE = re.compile(r"[0-9A-Fa-f]{64}")
V2_INPUT_FIELDS = {"source_binding", "approved_cues", "reviewed_draft_sha256"}


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


def _sha256_file(path: Path) -> str:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise ValueError(f"unable to hash bound file: {path}") from exc
    return digest.hexdigest().upper()


def _sha256(value: Any, label: str) -> str:
    result = _text(value)
    if not SHA256_RE.fullmatch(result):
        raise ValueError(f"{label} must be a SHA-256 hex digest")
    return result.upper()


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a finite number")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a finite number") from exc
    if not math.isfinite(result):
        raise ValueError(f"{label} must be a finite number")
    return result


def _v2_requested(payload: Mapping[str, Any]) -> bool:
    raw_version = payload.get("version")
    version = _text(raw_version)
    if raw_version is not None and version not in {"1", "2"}:
        raise ValueError(f"unsupported transcript review decision version: {version}")
    return version == "2" or any(field in payload for field in V2_INPUT_FIELDS)


def _source_binding(payload: Mapping[str, Any]) -> dict[str, Any]:
    raw = payload.get("source_binding")
    if not isinstance(raw, Mapping):
        raise ValueError("v2 transcript review requires a complete source binding")
    source_path = _text(raw.get("source_path"))
    source_relative_path = _text(raw.get("source_relative_path"))
    if not source_path or not source_relative_path:
        raise ValueError("v2 transcript review source binding requires source paths")
    window_start_sec = _number(raw.get("window_start_sec"), "source binding window_start_sec")
    window_end_sec = _number(raw.get("window_end_sec"), "source binding window_end_sec")
    if window_start_sec < 0 or window_end_sec <= window_start_sec:
        raise ValueError("source binding window must be non-negative and increasing")
    return {
        "source_path": source_path,
        "source_relative_path": source_relative_path,
        "source_sha256": _sha256(raw.get("source_sha256"), "source binding source_sha256"),
        "window_start_sec": window_start_sec,
        "window_end_sec": window_end_sec,
    }


def _approved_cues(
    payload: Mapping[str, Any],
    source_binding: Mapping[str, Any],
    reviewed_cue_ids: list[str],
) -> list[dict[str, Any]]:
    raw_cues = payload.get("approved_cues")
    if not isinstance(raw_cues, list) or not raw_cues:
        raise ValueError("v2 transcript review requires approved cues")
    cues: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, raw in enumerate(raw_cues, start=1):
        if not isinstance(raw, Mapping):
            raise ValueError("approved cue must be an object")
        cue_id = _text(raw.get("cue_id"))
        approved_text = _text(raw.get("approved_text"))
        if not cue_id or not approved_text:
            raise ValueError("approved cue requires cue_id and approved_text")
        if cue_id in seen_ids:
            raise ValueError(f"duplicate approved cue id: {cue_id}")
        start_sec = _number(raw.get("start_sec"), f"approved cue {index} start_sec")
        end_sec = _number(raw.get("end_sec"), f"approved cue {index} end_sec")
        if end_sec <= start_sec:
            raise ValueError(f"approved cue {cue_id} must have increasing timing")
        if start_sec < source_binding["window_start_sec"] or end_sec > source_binding["window_end_sec"]:
            raise ValueError(f"approved cue {cue_id} is outside the source binding window")
        seen_ids.add(cue_id)
        cues.append({
            "cue_id": cue_id,
            "start_sec": start_sec,
            "end_sec": end_sec,
            "approved_text": approved_text,
        })
    cues.sort(key=lambda cue: (cue["start_sec"], cue["end_sec"], cue["cue_id"]))
    cue_ids = [cue["cue_id"] for cue in cues]
    if reviewed_cue_ids and reviewed_cue_ids != cue_ids:
        raise ValueError("reviewed cue ids must match the ordered approved cue ids")
    return cues


def build_human_transcript_review_decision(payload: Mapping[str, Any]) -> dict[str, Any]:
    decision = _text(payload.get("decision"))
    reviewer = _text(payload.get("reviewer") or payload.get("reviewer_type"))
    notes = [_text(item) for item in _as_list(payload.get("notes") or payload.get("note")) if _text(item)]
    reviewed_draft = _text(payload.get("reviewed_draft") or payload.get("draft_subtitles"))
    reviewed_cue_ids = [_text(item) for item in _as_list(payload.get("reviewed_cue_ids")) if _text(item)]
    v2 = _v2_requested(payload)

    if decision not in DECISIONS:
        raise ValueError(f"unsupported transcript review decision: {decision}")
    if reviewer.casefold() != "human":
        raise ValueError("human transcript review decision requires reviewer=human")
    if decision == "approved":
        if not reviewed_draft:
            raise ValueError("approved transcript review requires reviewed draft path")
        if not v2 and not reviewed_cue_ids:
            raise ValueError("approved transcript review requires reviewed cue ids")
        if v2:
            source_binding = _source_binding(payload)
            approved_cues = _approved_cues(payload, source_binding, reviewed_cue_ids)
            reviewed_cue_ids = [cue["cue_id"] for cue in approved_cues]
    elif not notes:
        raise ValueError(f"{decision} transcript review requires at least one note")
    elif v2:
        raise ValueError("v2 transcript review bindings require an approved decision")

    artifact = {
        "artifact_role": "human_transcript_review_decision",
        "version": 2 if v2 else 1,
        "decision": decision,
        "reviewer": "human",
        "reviewed_draft": reviewed_draft,
        "reviewed_cue_ids": reviewed_cue_ids,
        "notes": notes,
        "clears_human_transcript_review": decision == "approved",
        "created_at": _text(payload.get("created_at")) or _now_iso(),
    }
    if v2:
        artifact["source_binding"] = source_binding
        artifact["approved_cues"] = approved_cues
        if "reviewed_draft_sha256" in payload:
            _sha256(payload.get("reviewed_draft_sha256"), "reviewed_draft_sha256")
    return artifact


def write_human_transcript_review_decision_for_run(
    run: str | Path,
    payload: Mapping[str, Any],
    out_name: str = "human_transcript_review_decision.json",
) -> dict[str, Any]:
    root = Path(run)
    out_path = root / out_name
    decision = build_human_transcript_review_decision(payload)
    if decision["version"] == 2:
        source_path = Path(decision["source_binding"]["source_path"])
        if not source_path.is_absolute():
            source_path = root / source_path
        actual_source_sha256 = _sha256_file(source_path)
        if actual_source_sha256 != decision["source_binding"]["source_sha256"]:
            raise ValueError("source binding SHA-256 does not match the source file")
        reviewed_draft_path = Path(decision["reviewed_draft"])
        if not reviewed_draft_path.is_absolute():
            reviewed_draft_path = root / reviewed_draft_path
        actual_reviewed_draft_sha256 = _sha256_file(reviewed_draft_path)
        if "reviewed_draft_sha256" in payload and actual_reviewed_draft_sha256 != _sha256(payload.get("reviewed_draft_sha256"), "reviewed_draft_sha256"):
            raise ValueError("reviewed draft SHA-256 does not match the reviewed draft")
        decision["reviewed_draft_sha256"] = actual_reviewed_draft_sha256
    out_path.write_text(json.dumps(decision, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    decision["path"] = str(out_path)
    return decision
