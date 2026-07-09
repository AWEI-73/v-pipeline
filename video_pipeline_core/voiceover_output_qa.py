"""Voiceover output QA for generated narration artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


CONTROL_TERMS = (
    "ClearNeration",
    "clear narration",
    "firm documentary delivery",
    "warm clear documentary delivery",
    "documentary delivery",
    "Mandarin narrator",
    "voice",
    "style",
    "prompt",
    "?桅店",
    "閮剖?",
    "?",
)

INDEPENDENT_ASR_METHODS = {
    "faster_whisper",
    "faster-whisper",
    "whisper",
    "stable_whisper",
    "independent_asr",
}


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def _text(value: Any) -> str:
    return str(value or "").strip()


def _lower(value: Any) -> str:
    return _text(value).casefold()


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None


def _probe_texts(probe: Mapping[str, Any]) -> list[tuple[str, str]]:
    texts: list[tuple[str, str]] = []
    for key in ("transcript", "recognized_text", "asr_text", "provider_output_text"):
        if _text(probe.get(key)):
            texts.append((key, _text(probe.get(key))))
    for segment in _as_list(probe.get("segments")):
        if not isinstance(segment, Mapping):
            continue
        segment_id = _text(segment.get("segment_id") or segment.get("id") or "segment")
        for key in ("transcript", "recognized_text", "asr_text", "provider_output_text"):
            if _text(segment.get(key)):
                texts.append((f"{segment_id}.{key}", _text(segment.get(key))))
    metadata = probe.get("provider_output_metadata")
    if isinstance(metadata, Mapping):
        for key, value in metadata.items():
            if isinstance(value, (str, int, float, bool)):
                texts.append((f"provider_output_metadata.{key}", _text(value)))
    return texts


def evaluate_voiceover_output_qa(artifacts: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = artifacts if isinstance(artifacts, Mapping) else {}
    probe = payload.get("voiceover_output_probe")
    blocking: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    if not isinstance(probe, Mapping):
        blocking.append({
            "rule": "needs_voiceover_output_probe",
            "tier": 1,
            "message": "voiceover output QA requires transcript/ASR/provider-output evidence",
            "next_action": "run_voiceover_output_probe",
        })
        return _report(blocking, warnings, 0)

    method = _lower(probe.get("method") or probe.get("asr_method"))
    evidence = _as_list(probe.get("evidence"))
    evidence_methods = {
        _lower(item.get("method"))
        for item in evidence
        if isinstance(item, Mapping)
    }
    if method not in INDEPENDENT_ASR_METHODS and not (evidence_methods & INDEPENDENT_ASR_METHODS):
        blocking.append({
            "rule": "independent_asr_required",
            "tier": 1,
            "message": "voiceover output QA requires independent ASR evidence; provider manifest text alone cannot pass",
            "next_action": "run_independent_voiceover_asr",
        })

    checked = 0
    for field, value in _probe_texts(probe):
        checked += 1
        folded = _lower(value)
        for term in CONTROL_TERMS:
            if term.casefold() in folded:
                blocking.append({
                    "rule": "voiceover_control_text_leak",
                    "tier": 1,
                    "field": field,
                    "term": term,
                    "message": "generated voiceover output contains style/control leakage text",
                    "next_action": "repair_voiceover_output",
                })

    if checked == 0 or not evidence:
        blocking.append({
            "rule": "voiceover_output_probe_evidence_missing",
            "tier": 1,
            "message": "voiceover output probe must include checked text and evidence refs",
            "next_action": "run_voiceover_output_probe",
        })

    return _report(blocking, warnings, checked)


def _report(blocking: list[dict[str, Any]], warnings: list[dict[str, Any]], checked_text_count: int) -> dict[str, Any]:
    return {
        "artifact_role": "voiceover_output_qa",
        "version": 1,
        "pass": not blocking,
        "blocking": blocking,
        "warnings": warnings,
        "checked_text_count": checked_text_count,
        "control_terms": list(CONTROL_TERMS),
        "next_action": None if not blocking else blocking[0]["next_action"],
    }


def write_voiceover_output_qa_for_run(run: str | Path, out_name: str = "voiceover_output_qa.json") -> dict[str, Any]:
    root = Path(run)
    probe = _load_json(root / "voiceover_output_probe.json")
    report = evaluate_voiceover_output_qa({"voiceover_output_probe": probe} if isinstance(probe, Mapping) else {})
    report["run"] = str(root)
    (root / out_name).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report
