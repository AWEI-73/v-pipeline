"""Agent-draft ASR transcript repair suggestions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


SOURCE_TYPES = {
    "source_speech",
    "voiceover",
    "generated_subtitle",
    "interview",
    "original_audio",
}

KNOWN_REPAIRS = (
    ("第六四七七楊成班學人們", "第六十七期養成班學員們", "known graduation source-speech ASR confusion"),
    ("順利節", "順利結訓", "known source-speech ASR ending confusion"),
    ("五個班院成成", "五個半月養成", "known training-duration ASR confusion"),
)


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def _text(value: Any) -> str:
    return str(value or "").strip()


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _segments(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw = payload.get("segments") or payload.get("items") or payload.get("cues") or []
    return [item for item in _as_list(raw) if isinstance(item, dict)]


def _source_type(payload: Mapping[str, Any], default: str = "source_speech") -> str:
    value = _text(payload.get("source_type") or payload.get("subtitle_source_type") or default)
    return value if value in SOURCE_TYPES else default


def _repair_text(original: str) -> tuple[str, list[dict[str, str]], list[str], str]:
    suggested = original
    uncertain_spans: list[dict[str, str]] = []
    reasons: list[str] = []
    for wrong, replacement, reason in KNOWN_REPAIRS:
        if wrong in suggested:
            suggested = suggested.replace(wrong, replacement)
            uncertain_spans.append({"original": wrong, "suggested": replacement})
            reasons.append(reason)
    if "電力雄兵" in suggested and not reasons:
        uncertain_spans.append({"original": "電力雄兵", "suggested": "電力雄兵"})
        reasons.append("plausible phrase but still requires human transcript confirmation")
    confidence = "medium" if reasons else "low"
    if reasons and all(span["original"] != span["suggested"] for span in uncertain_spans):
        confidence = "medium"
    return suggested, uncertain_spans, reasons, confidence


def build_agent_transcript_repair(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    data = payload if isinstance(payload, Mapping) else {}
    source_type = _source_type(data)
    suggestions: list[dict[str, Any]] = []
    for index, cue in enumerate(_segments(data), start=1):
        cue_id = _text(cue.get("cue_id") or cue.get("segment_id") or cue.get("id") or f"cue{index:02d}")
        original = _text(cue.get("text") or cue.get("recognized_text") or cue.get("asr_text"))
        suggested, uncertain_spans, reasons, confidence = _repair_text(original)
        suggestions.append({
            "cue_id": cue_id,
            "source_type": _source_type(cue, source_type),
            "start_sec": _float(cue.get("start_sec") if "start_sec" in cue else cue.get("start")),
            "end_sec": _float(cue.get("end_sec") if "end_sec" in cue else cue.get("end")),
            "original_asr": original,
            "suggested_text": suggested,
            "confidence": confidence,
            "uncertain_spans": uncertain_spans,
            "reason": "; ".join(reasons) if reasons else "agent draft normalization only; human transcript review required",
            "requires_human_transcript_review": True,
            "approval_status": "agent_draft_not_approved",
        })

    return {
        "artifact_role": "agent_transcript_repair_suggestions",
        "version": 1,
        "source_type": source_type,
        "requires_human_transcript_review": True,
        "approval_status": "agent_draft_not_approved",
        "suggestion_count": len(suggestions),
        "suggestions": suggestions,
        "next_action": "human_transcript_review",
    }


def _srt_timestamp(seconds: float) -> str:
    seconds = max(0.0, seconds)
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    if millis == 1000:
        secs += 1
        millis = 0
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def render_draft_srt(report: Mapping[str, Any]) -> str:
    blocks: list[str] = []
    for index, suggestion in enumerate(_as_list(report.get("suggestions")), start=1):
        if not isinstance(suggestion, Mapping):
            continue
        start = _float(suggestion.get("start_sec"))
        end = _float(suggestion.get("end_sec"), start + 2.0)
        if end <= start:
            end = start + 2.0
        text = _text(suggestion.get("suggested_text"))
        blocks.append(f"{index}\n{_srt_timestamp(start)} --> {_srt_timestamp(end)}\n{text}")
    return "\n\n".join(blocks) + ("\n" if blocks else "")


def _raw_from_source_speech_probe(probe: Mapping[str, Any]) -> dict[str, Any]:
    probe_segments = _segments(probe)
    if not probe_segments:
        features = probe.get("features")
        vocal_analysis = features.get("vocal_analysis") if isinstance(features, Mapping) else None
        nested_segments = vocal_analysis.get("segments") if isinstance(vocal_analysis, Mapping) else []
        probe_segments = [item for item in _as_list(nested_segments) if isinstance(item, dict)]
    segments = []
    for index, item in enumerate(probe_segments, start=1):
        segments.append({
            "id": _text(item.get("id") or item.get("segment_id") or f"cue{index:02d}"),
            "start_sec": _float(item.get("start_sec") if "start_sec" in item else item.get("start")),
            "end_sec": _float(item.get("end_sec") if "end_sec" in item else item.get("end")),
            "text": _text(item.get("text") or item.get("recognized_text")),
            "source_type": "source_speech",
        })
    return {
        "artifact_role": "asr_raw_transcript",
        "version": 1,
        "source_type": "source_speech",
        "segments": segments,
        "source_probe": "source_speech_asr_probe.json",
    }


def write_agent_transcript_repair_for_run(run: str | Path) -> dict[str, Any]:
    root = Path(run)
    raw_path = root / "asr_raw_transcript.json"
    raw = _load_json(raw_path)
    if not isinstance(raw, Mapping):
        probe = _load_json(root / "source_speech_asr_probe.json")
        if isinstance(probe, Mapping):
            raw = _raw_from_source_speech_probe(probe)
            raw_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        else:
            raw = {"source_type": "source_speech", "segments": []}
    report = build_agent_transcript_repair(raw)
    report["run"] = str(root)
    suggestions_path = root / "agent_transcript_repair_suggestions.json"
    draft_path = root / "subtitles.draft.srt"
    suggestions_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    draft_path.write_text(render_draft_srt(report), encoding="utf-8")
    report["suggestions_path"] = str(suggestions_path)
    report["draft_subtitles_path"] = str(draft_path)
    return report
