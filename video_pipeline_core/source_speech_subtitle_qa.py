"""Source-speech subtitle completeness QA."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


DEFAULT_END_TOLERANCE_SEC = 1.0
PLACEHOLDER_PHRASES = (
    "主任勉勵原音",
    "後段逐字稿需人工確認",
    "review marker",
    "coverage marker",
    "?",
    "?鈭箏極蝣箄?",
)


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def _float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _text(value: Any) -> str:
    return str(value or "").strip()


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None


def _segments(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw = payload.get("source_speech_segments") or payload.get("segments")
    return [item for item in _as_list(raw) if isinstance(item, dict)]


def _cues(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw = payload.get("subtitle_cues") or payload.get("cues")
    return [item for item in _as_list(raw) if isinstance(item, dict)]


def _block(rule: str, segment: Mapping[str, Any] | None, message: str) -> dict[str, Any]:
    return {
        "rule": rule,
        "tier": 1,
        "segment_id": _text((segment or {}).get("segment_id") or (segment or {}).get("id")),
        "message": message,
        "next_action": "repair_source_speech_subtitles",
    }


def _placeholder_block(segment: Mapping[str, Any] | None, text: str) -> dict[str, Any]:
    return {
        "rule": "source_speech_placeholder_subtitles",
        "tier": 1,
        "segment_id": _text((segment or {}).get("segment_id") or (segment or {}).get("id")),
        "text": text,
        "message": "placeholder/review-marker subtitle text cannot satisfy source-speech subtitle QA",
        "next_action": "human_transcript_review",
    }


def evaluate_source_speech_subtitle_qa(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    data = payload if isinstance(payload, Mapping) else {}
    blocking: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    segments = _segments(data)
    cues = _cues(data)
    tolerance = _float(data.get("end_tolerance_sec"))
    if tolerance is None:
        tolerance = DEFAULT_END_TOLERANCE_SEC

    if not segments:
        blocking.append(_block("source_speech_segment_missing", None, "source speech subtitle QA requires source speech segment timing"))
    if not cues:
        blocking.append(_block("source_speech_subtitle_evidence_missing", None, "source speech subtitle QA requires subtitle cue evidence"))

    for segment in segments:
        start = _float(segment.get("start_sec"))
        end = _float(segment.get("end_sec"))
        if start is None or end is None or end <= start:
            blocking.append(_block("source_speech_segment_timing_invalid", segment, "source speech segment must have valid start/end times"))
            continue
        relevant: list[dict[str, Any]] = []
        for cue in cues:
            cue_start = _float(cue.get("start_sec"))
            cue_end = _float(cue.get("end_sec"))
            if cue_start is None or cue_end is None or cue_end <= cue_start:
                blocking.append(_block("source_speech_subtitle_timing_invalid", segment, "subtitle cue must have valid start/end times"))
                continue
            if cue_start < start - tolerance or cue_end > end + tolerance:
                blocking.append(_block("source_speech_subtitle_timing_outside_segment", segment, "subtitle cue timing falls outside source speech segment"))
            cue_text = _text(cue.get("text") or cue.get("subtitle") or cue.get("caption"))
            if any(phrase.casefold() in cue_text.casefold() for phrase in PLACEHOLDER_PHRASES):
                blocking.append(_placeholder_block(segment, cue_text))
            if cue_end >= start and cue_start <= end:
                relevant.append(cue)
        if relevant:
            last_end = max(float(cue["end_sec"]) for cue in relevant)
            midpoint = start + ((end - start) / 2.0)
            later_covered = any(
                _float(cue.get("start_sec")) is not None
                and _float(cue.get("end_sec")) is not None
                and float(cue["start_sec"]) <= end
                and float(cue["end_sec"]) >= midpoint
                for cue in relevant
            )
            if (last_end < end - tolerance or not later_covered) and not bool(data.get("needs_human_transcript_review")):
                blocking.append(_block("source_speech_later_subtitle_coverage_missing", segment, "later portion of source speech lacks subtitle coverage"))
            elif last_end < end - tolerance or not later_covered:
                warnings.append({
                    "rule": "source_speech_later_subtitle_coverage_marked_for_human_review",
                    "tier": 2,
                    "segment_id": _text(segment.get("segment_id") or segment.get("id")),
                    "message": "later subtitle coverage is incomplete and explicitly routed for human transcript review",
                    "next_action": "human_transcript_review",
                })

    needs_human = bool(data.get("needs_human_transcript_review"))
    if _text(data.get("subtitle_source")).casefold() == "asr" and not bool(data.get("human_transcript_present")):
        needs_human = True
        warnings.append({
            "rule": "needs_human_transcript_review",
            "tier": 2,
            "message": "ASR-derived source-speech subtitles require human transcript review",
            "next_action": "human_transcript_review",
        })

    return {
        "artifact_role": "source_speech_subtitle_qa",
        "version": 1,
        "pass": not blocking,
        "blocking": blocking,
        "warnings": warnings,
        "checked_segment_count": len(segments),
        "checked_cue_count": len(cues),
        "needs_human_transcript_review": needs_human,
        "next_action": None if not blocking else blocking[0]["next_action"],
    }


def write_source_speech_subtitle_qa_for_run(run: str | Path, out_name: str = "source_speech_subtitle_qa.json") -> dict[str, Any]:
    root = Path(run)
    evidence = _load_json(root / "source_speech_subtitle_evidence.json")
    report = evaluate_source_speech_subtitle_qa(evidence if isinstance(evidence, Mapping) else None)
    report["run"] = str(root)
    (root / out_name).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report
