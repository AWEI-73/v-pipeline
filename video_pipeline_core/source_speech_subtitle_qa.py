"""Source-speech subtitle completeness QA."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from video_pipeline_core.caption_audit import parse_srt
from video_pipeline_core.human_transcript_review_decision import build_human_transcript_review_decision


DEFAULT_END_TOLERANCE_SEC = 1.0
APPROVED_TEXT_TIMING_TOLERANCE_SEC = 0.002
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


def _binding_block(rule: str, message: str) -> dict[str, Any]:
    return {
        "rule": rule,
        "tier": 1,
        "message": message,
        "next_action": "repair_source_speech_subtitles",
    }


def _normalized_subtitle_text(value: Any) -> str:
    return " ".join(_text(value).split())


def _source_binding_matches(expected: Any, actual: Any) -> bool:
    if not isinstance(expected, Mapping) or not isinstance(actual, Mapping):
        return False
    for field in ("source_path", "source_relative_path"):
        expected_path = _text(expected.get(field)).replace("\\", "/").casefold()
        actual_path = _text(actual.get(field)).replace("\\", "/").casefold()
        if not expected_path or expected_path != actual_path:
            return False
    if _text(expected.get("source_sha256")).casefold() != _text(actual.get("source_sha256")).casefold():
        return False
    for field in ("window_start_sec", "window_end_sec"):
        expected_value = _float(expected.get(field))
        actual_value = _float(actual.get(field))
        if expected_value is None or actual_value is None or abs(expected_value - actual_value) > APPROVED_TEXT_TIMING_TOLERANCE_SEC:
            return False
    return True


def _validated_v2_decision(decision: Mapping[str, Any]) -> Mapping[str, Any] | None:
    if _text(decision.get("artifact_role")) != "human_transcript_review_decision":
        return None
    if not bool(decision.get("clears_human_transcript_review")):
        return None
    if not _text(decision.get("reviewed_draft_sha256")):
        return None
    try:
        normalized = build_human_transcript_review_decision(decision)
    except ValueError:
        return None
    return normalized if normalized.get("version") == 2 else None


def _approved_text_binding_report(
    root: Path,
    evidence: Mapping[str, Any],
    require_approved_text_binding: bool = False,
) -> dict[str, Any]:
    decision = _load_json(root / "human_transcript_review_decision.json")
    is_v2 = isinstance(decision, Mapping) and _text(decision.get("version")) == "2"
    if not is_v2:
        if require_approved_text_binding:
            rule = "approved_text_binding_decision_legacy" if isinstance(decision, Mapping) else "approved_text_binding_decision_missing"
            message = (
                "required approved-text binding needs a v2 human transcript decision"
                if isinstance(decision, Mapping)
                else "required approved-text binding needs human_transcript_review_decision.json"
            )
            return {
                "required": True,
                "checked": False,
                "actual_cue_count": 0,
                "actual_cues": None,
                "blocking": [_binding_block(rule, message)],
            }
        return {
            "required": False,
            "checked": False,
            "actual_cue_count": 0,
            "actual_cues": None,
            "blocking": [],
        }

    validated_decision = _validated_v2_decision(decision)
    if validated_decision is None:
        return {
            "required": True,
            "checked": False,
            "actual_cue_count": 0,
            "actual_cues": None,
            "blocking": [
                _binding_block(
                    "approved_text_binding_decision_invalid",
                    "v2 transcript decision is not a complete human-approved transcript binding",
                ),
            ],
        }

    blocking: list[dict[str, Any]] = []
    decision = validated_decision
    if not _source_binding_matches(decision.get("source_binding"), evidence.get("source_binding")):
        blocking.append(_binding_block(
            "approved_text_binding_source_mismatch",
            "v2 transcript decision source binding does not match source-speech subtitle evidence",
        ))

    srt_path = root / "subtitles.srt"
    try:
        actual_cues = parse_srt(srt_path.read_text(encoding="utf-8-sig"))
    except OSError:
        return {
            "required": True,
            "checked": False,
            "actual_cue_count": 0,
            "actual_cues": None,
            "blocking": [
                *blocking,
                _binding_block(
                    "approved_text_binding_srt_missing",
                    "v2 transcript decision requires the actual run-local subtitles.srt",
                ),
            ],
        }

    approved_cues = decision.get("approved_cues")
    reviewed_cue_ids = decision.get("reviewed_cue_ids")
    if not isinstance(approved_cues, list) or not approved_cues or not isinstance(reviewed_cue_ids, list):
        blocking.append(_binding_block(
            "approved_text_binding_cue_set_mismatch",
            "v2 transcript decision is missing an ordered approved cue set",
        ))
        return {
            "required": True,
            "checked": False,
            "actual_cue_count": len(actual_cues),
            "actual_cues": actual_cues,
            "blocking": blocking,
        }

    approved_ids = [_text(cue.get("cue_id")) for cue in approved_cues if isinstance(cue, Mapping)]
    if len(approved_ids) != len(approved_cues) or not all(approved_ids) or approved_ids != [_text(value) for value in reviewed_cue_ids]:
        blocking.append(_binding_block(
            "approved_text_binding_cue_set_mismatch",
            "v2 transcript decision approved cue ids are missing or out of order",
        ))
    if len(actual_cues) != len(approved_cues):
        blocking.append(_binding_block(
            "approved_text_binding_cue_set_mismatch",
            "actual subtitles.srt cue count does not match the approved cue set",
        ))
    if blocking and len(actual_cues) != len(approved_cues):
        return {
            "required": True,
            "checked": True,
            "actual_cue_count": len(actual_cues),
            "actual_cues": actual_cues,
            "blocking": blocking,
        }

    text_mismatch = False
    timing_mismatch = False
    for approved, actual in zip(approved_cues, actual_cues):
        if not isinstance(approved, Mapping):
            text_mismatch = True
            timing_mismatch = True
            continue
        if _normalized_subtitle_text(approved.get("approved_text")) != _normalized_subtitle_text(actual.get("text")):
            text_mismatch = True
        approved_start = _float(approved.get("start_sec"))
        approved_end = _float(approved.get("end_sec"))
        if (
            approved_start is None
            or approved_end is None
            or abs(approved_start - float(actual["start_sec"])) > APPROVED_TEXT_TIMING_TOLERANCE_SEC
            or abs(approved_end - float(actual["end_sec"])) > APPROVED_TEXT_TIMING_TOLERANCE_SEC
        ):
            timing_mismatch = True
    if text_mismatch:
        blocking.append(_binding_block(
            "approved_text_binding_text_mismatch",
            "actual subtitles.srt text does not equal the human-approved transcript text",
        ))
    if timing_mismatch:
        blocking.append(_binding_block(
            "approved_text_binding_timing_mismatch",
            "actual subtitles.srt timing does not equal the approved cue timing within 0.002s",
        ))
    return {
        "required": True,
        "checked": True,
        "actual_cue_count": len(actual_cues),
        "actual_cues": actual_cues,
        "blocking": blocking,
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


def write_source_speech_subtitle_qa_for_run(
    run: str | Path,
    out_name: str = "source_speech_subtitle_qa.json",
    require_approved_text_binding: bool = False,
) -> dict[str, Any]:
    root = Path(run)
    evidence = _load_json(root / "source_speech_subtitle_evidence.json")
    evidence_payload = evidence if isinstance(evidence, Mapping) else {}
    binding = _approved_text_binding_report(root, evidence_payload, require_approved_text_binding)
    evaluation_payload = dict(evidence_payload)
    if binding["required"]:
        evaluation_payload["subtitle_cues"] = binding["actual_cues"] or []
    report = evaluate_source_speech_subtitle_qa(evaluation_payload)
    report["approved_text_binding_required"] = binding["required"]
    report["approved_text_equality_checked"] = binding["checked"]
    report["actual_subtitle_cue_count"] = binding["actual_cue_count"]
    report["blocking"].extend(binding["blocking"])
    report["pass"] = not report["blocking"]
    report["next_action"] = None if report["pass"] else report["blocking"][0]["next_action"]
    if binding["required"]:
        report["version"] = 2
    report["run"] = str(root)
    (root / out_name).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report
